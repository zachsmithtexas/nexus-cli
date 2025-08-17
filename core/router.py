"""Provider routing with fallback logic."""

import logging
import os
import time

from rich.console import Console

from connectors.providers import (
    BaseProvider,
    ClaudeCodeProvider,
    CodexCliProvider,
    DeepseekProvider,
    GoogleAiStudioProvider,
    GroqProvider,
    OpenrouterProvider,
    QwenProvider,
    TogetherProvider,
)

from .config import ConfigManager
from .rate_limiter import RateLimiter

console = Console()
logger = logging.getLogger(__name__)


class ProviderRouter:
    """Routes requests to appropriate providers with fallback logic."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._provider_cache: dict[str, BaseProvider] = {}
        self.rate_limiter = RateLimiter()

    def _get_provider(self, provider_name: str, model_name: str) -> BaseProvider | None:
        """Get a provider instance."""
        cache_key = f"{provider_name}:{model_name}"

        if cache_key not in self._provider_cache:
            provider_class_map = {
                "claude_code": ClaudeCodeProvider,
                "codex_cli": CodexCliProvider,
                "deepseek": DeepseekProvider,
                "google_ai_studio": GoogleAiStudioProvider,
                "groq": GroqProvider,
                "openrouter": OpenrouterProvider,
                "qwen": QwenProvider,
                "together": TogetherProvider,
            }

            provider_class = provider_class_map.get(provider_name)
            if not provider_class:
                console.log(f"Unknown provider: {provider_name}")
                return None

            try:
                # Special handling for Google AI Studio provider
                if provider_name == "google_ai_studio":
                    provider = provider_class(
                        model_name
                    )  # Uses environment variables internally
                else:
                    provider = provider_class(model_name)
                self._provider_cache[cache_key] = provider
            except Exception as e:
                console.log(f"Failed to create provider {provider_name}: {e}")
                return None

        return self._provider_cache[cache_key]

    def _should_skip_paid_provider(self, provider_name: str, model_id: str) -> bool:
        """Check if paid providers should be skipped."""
        use_paid_models = os.getenv("USE_PAID_MODELS", "true").lower() == "true"
        if use_paid_models:
            return False

        # Check if this is a paid model from our configuration
        models_config = self.config_manager.config.get("models", {})
        provider_routes = self.config_manager.config.get("provider_routes", [])

        # Check legacy models config
        if model_id in models_config:
            model_config = models_config[model_id]
            if model_config.get("is_paid", False):
                return True

        # Check provider routes config
        for route in provider_routes:
            if route.get("id") == model_id and route.get("provider") == provider_name:
                if route.get("is_paid", False):
                    return True

        return False

    async def complete(
        self, role: str, prompt: str, model_id: str = None
    ) -> str | None:
        """Complete a prompt using the role's provider chain."""
        if model_id:
            # Direct model routing
            return await self._complete_with_model(model_id, prompt)

        # Role-based routing (legacy)
        role_config = self.config_manager.get_role_config(role)
        if not role_config:
            console.log(f"No configuration found for role: {role}")
            return None

        model_name = role_config.model

        # Try each provider in order
        for provider_name in role_config.providers:
            try:
                # Skip if paid models are disabled and this is a paid model
                if self._should_skip_paid_provider(provider_name, model_name):
                    console.log(
                        f"Skipping paid model {model_name} on {provider_name} (USE_PAID_MODELS=false)"
                    )
                    continue

                provider = self._get_provider(provider_name, model_name)
                if not provider:
                    continue

                if not provider.is_available():
                    console.log(
                        f"Provider {provider_name} not available, trying next..."
                    )
                    continue

                # Check rate limits
                allowed, sleep_time = self.rate_limiter.check_limits(
                    provider_name, model_name
                )
                if not allowed:
                    if sleep_time and sleep_time > 0:
                        logger.warning(
                            f"Rate limit hit for {model_name}, sleeping {sleep_time:.1f}s"
                        )
                        time.sleep(sleep_time)
                        # Re-check after sleep
                        allowed, _ = self.rate_limiter.check_limits(
                            provider_name, model_name
                        )
                        if not allowed:
                            console.log(
                                f"Rate limit still exceeded for {model_name}, trying next provider..."
                            )
                            continue
                    else:
                        console.log(
                            f"Rate limit exceeded for {model_name}, trying next provider..."
                        )
                        continue

                start_time = time.time()
                console.log(f"Using provider {provider_name} for role {role}")
                result = await provider.complete(prompt)
                latency = time.time() - start_time

                # Record successful request
                estimated_tokens = (
                    len(prompt.split()) + len(result.split()) * 1.3
                )  # Rough estimate
                self.rate_limiter.record_request(
                    provider_name, model_name, int(estimated_tokens)
                )

                # Log routing trace
                console.log(f"✓ {provider_name} → {model_name} → {latency:.2f}s")

                # Update budget tracking (simplified)
                self._update_budget(role, int(estimated_tokens))

                return result

            except Exception as e:
                console.log(f"Provider {provider_name} failed: {e}, trying next...")
                continue

        console.log(f"All providers failed for role {role}")
        return None

    async def _complete_with_model(self, model_id: str, prompt: str) -> str | None:
        """Complete a prompt with a specific model ID from provider routes."""
        provider_routes = self.config_manager.config.get("provider_routes", [])

        # Find the route for this model
        route = None
        for r in provider_routes:
            if r.get("id") == model_id:
                route = r
                break

        if not route:
            console.log(f"No route found for model: {model_id}")
            return None

        provider_name = route.get("provider")
        if not provider_name:
            console.log(f"No provider specified for model: {model_id}")
            return None

        # Skip if paid models are disabled and this is a paid model
        if self._should_skip_paid_provider(provider_name, model_id):
            console.log(f"Skipping paid model {model_id} (USE_PAID_MODELS=false)")
            return None

        try:
            provider = self._get_provider(provider_name, model_id)
            if not provider:
                return None

            if not provider.is_available():
                console.log(
                    f"Provider {provider_name} not available for model {model_id}"
                )
                return None

            # Check rate limits
            allowed, sleep_time = self.rate_limiter.check_limits(
                provider_name, model_id
            )
            if not allowed:
                if sleep_time and sleep_time > 0:
                    logger.warning(
                        f"Rate limit hit for {model_id}, sleeping {sleep_time:.1f}s"
                    )
                    time.sleep(sleep_time)
                    # Re-check after sleep
                    allowed, _ = self.rate_limiter.check_limits(provider_name, model_id)
                    if not allowed:
                        console.log(f"Rate limit still exceeded for {model_id}")
                        return None
                else:
                    console.log(f"Rate limit exceeded for {model_id}")
                    return None

            start_time = time.time()
            console.log(f"Using {provider_name} for model {model_id}")
            result = await provider.complete(prompt)
            latency = time.time() - start_time

            # Record successful request
            estimated_tokens = (
                len(prompt.split()) + len(result.split()) * 1.3
            )  # Rough estimate
            self.rate_limiter.record_request(
                provider_name, model_id, int(estimated_tokens)
            )

            # Log routing trace
            console.log(f"✓ {provider_name} → {model_id} → {latency:.2f}s")

            return result

        except Exception as e:
            console.log(f"Provider {provider_name} failed for model {model_id}: {e}")
            return None

    def _update_budget(self, role: str, token_count: int):
        """Update budget usage for a role (simplified implementation)."""
        # In a real implementation, this would update the budget in roles.yaml
        # For now, just log the usage
        estimated_cost = token_count * 0.001 / 1000  # Rough estimate
        console.log(f"Role {role} used ~{token_count} tokens (${estimated_cost:.4f})")

    def get_available_providers(self) -> list[str]:
        """Get list of available providers."""
        available = []

        # Check each provider type
        providers = [
            ("claude_code", ClaudeCodeProvider),
            ("codex_cli", CodexCliProvider),
            ("deepseek", DeepseekProvider),
            ("google_ai_studio", GoogleAiStudioProvider),
            ("groq", GroqProvider),
            ("openrouter", OpenrouterProvider),
            ("qwen", QwenProvider),
            ("together", TogetherProvider),
        ]

        for name, provider_class in providers:
            try:
                provider = provider_class("test-model")
                if provider.is_available():
                    available.append(name)
            except Exception:
                pass

        return available
