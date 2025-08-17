"""Rate limiting system for model requests."""

import logging
import time
from collections import defaultdict, deque
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class RateLimiter:
    """Per-model rate limiter with RPM and TPM tracking."""

    def __init__(self, limits_config_path: str = "config/limits.yaml"):
        self.limits_config_path = Path(limits_config_path)
        self.limits = self._load_limits()

        # Track requests and tokens per model
        # Format: {model_id: deque([(timestamp, token_count), ...])}
        self.request_history: dict[str, deque] = defaultdict(lambda: deque())
        self.token_history: dict[str, deque] = defaultdict(lambda: deque())

        # Window size for rate limiting (60 seconds)
        self.window_size = 60.0

    def _load_limits(self) -> dict:
        """Load rate limits from configuration file."""
        if not self.limits_config_path.exists():
            logger.warning(
                f"Limits config not found at {self.limits_config_path}, using defaults"
            )
            return {}

        try:
            with open(self.limits_config_path) as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded rate limits from {self.limits_config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load limits config: {e}")
            return {}

    def _get_model_limits(self, provider: str, model_id: str) -> tuple[int, int]:
        """Get RPM and TPM limits for a specific model."""
        # Check provider-specific model limits
        provider_config = self.limits.get("providers", {}).get(provider, {})
        model_limits = provider_config.get("models", {}).get(model_id)

        if model_limits:
            rpm = model_limits.get("rpm", 0)
            tpm = model_limits.get("tpm", 0)
            return rpm, tpm

        # Fall back to default limits
        defaults = self.limits.get("default_limits", {})
        rpm = defaults.get("rpm", 60)
        tpm = defaults.get("tpm", 10000)

        return rpm, tpm

    def _cleanup_old_entries(self, history: deque, current_time: float):
        """Remove entries older than the window size."""
        cutoff_time = current_time - self.window_size
        while history and history[0][0] < cutoff_time:
            history.popleft()

    def _count_requests_in_window(self, model_id: str, current_time: float) -> int:
        """Count requests for a model in the current window."""
        history = self.request_history[model_id]
        self._cleanup_old_entries(history, current_time)
        return len(history)

    def _count_tokens_in_window(self, model_id: str, current_time: float) -> int:
        """Count tokens for a model in the current window."""
        history = self.token_history[model_id]
        self._cleanup_old_entries(history, current_time)
        return sum(entry[1] for entry in history)

    def check_limits(
        self, provider: str, model_id: str, estimated_tokens: int = 1000
    ) -> tuple[bool, float | None]:
        """Check if a request would exceed rate limits.

        Returns:
            (allowed, sleep_time):
            - allowed: True if request is allowed
            - sleep_time: Seconds to wait if request is not allowed

        """
        current_time = time.time()
        rpm_limit, tpm_limit = self._get_model_limits(provider, model_id)

        # Skip rate limiting if limits are 0 or not configured
        if rpm_limit <= 0 and tpm_limit <= 0:
            return True, None

        # Check RPM limit
        if rpm_limit > 0:
            current_requests = self._count_requests_in_window(model_id, current_time)
            if current_requests >= rpm_limit:
                # Calculate sleep time until oldest request falls out of window
                oldest_request_time = self.request_history[model_id][0][0]
                sleep_time = (oldest_request_time + self.window_size) - current_time
                logger.warning(
                    f"RPM limit exceeded for {model_id}: {current_requests}/{rpm_limit}"
                )
                return False, max(0, sleep_time)

        # Check TPM limit
        if tpm_limit > 0:
            current_tokens = self._count_tokens_in_window(model_id, current_time)
            if current_tokens + estimated_tokens > tpm_limit:
                # Calculate sleep time until enough tokens fall out of window
                # This is a simplified approach - we'll wait for the oldest entry
                oldest_token_time = (
                    self.token_history[model_id][0][0]
                    if self.token_history[model_id]
                    else current_time
                )
                sleep_time = (oldest_token_time + self.window_size) - current_time
                logger.warning(
                    f"TPM limit would be exceeded for {model_id}: {current_tokens + estimated_tokens}/{tpm_limit}"
                )
                return False, max(0, sleep_time)

        return True, None

    def record_request(self, provider: str, model_id: str, token_count: int):
        """Record a successful request and its token usage."""
        current_time = time.time()

        # Record the request
        self.request_history[model_id].append((current_time, 1))

        # Record the token usage
        self.token_history[model_id].append((current_time, token_count))

        # Log current usage
        rpm_limit, tpm_limit = self._get_model_limits(provider, model_id)
        current_requests = self._count_requests_in_window(model_id, current_time)
        current_tokens = self._count_tokens_in_window(model_id, current_time)

        logger.debug(
            f"Rate limiter - {model_id}: {current_requests}/{rpm_limit} RPM, {current_tokens}/{tpm_limit} TPM"
        )

    def get_current_usage(self, provider: str, model_id: str) -> dict[str, int]:
        """Get current usage statistics for a model."""
        current_time = time.time()
        current_requests = self._count_requests_in_window(model_id, current_time)
        current_tokens = self._count_tokens_in_window(model_id, current_time)
        rpm_limit, tpm_limit = self._get_model_limits(provider, model_id)

        return {
            "current_requests": current_requests,
            "rpm_limit": rpm_limit,
            "current_tokens": current_tokens,
            "tpm_limit": tpm_limit,
        }
