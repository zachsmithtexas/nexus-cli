"""OpenRouter API provider."""

import os

import httpx

from .base import BaseProvider


class OpenrouterProvider(BaseProvider):
    """Provider for OpenRouter API."""

    def __init__(self, model_name: str, api_key: str | None = None):
        super().__init__(model_name, api_key or os.getenv("OPENROUTER_API_KEY"))
        self.base_url = "https://openrouter.ai/api/v1"

    async def complete(self, prompt: str) -> str:
        """Complete a prompt using OpenRouter API."""
        if not self.api_key:
            raise RuntimeError("OpenRouter API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://nexus-cli.local",
            "X-Title": "Nexus CLI",
        }

        max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "800"))
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            last_err = None
            for attempt in range(3):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions", headers=headers, json=payload
                    )
                    response.raise_for_status()

                    data = response.json()
                    # Robust handling: some errors return 2xx with an error payload
                    if not isinstance(data, dict) or "choices" not in data:
                        err = None
                        if isinstance(data, dict):
                            err = data.get("error") or data.get("message")
                        raise RuntimeError(
                            f"Unexpected response from OpenRouter: {err or str(data)[:200]}"
                        )

                    choices = data.get("choices") or []
                    if not choices:
                        raise RuntimeError("OpenRouter returned no choices")

                    msg = choices[0].get("message") or {}

                    # Extract text robustly from nested structures
                    def collect_text(node):
                        texts = []
                        if isinstance(node, str):
                            texts.append(node)
                        elif isinstance(node, dict):
                            # Prefer common fields first
                            for key in ("content", "text", "reasoning", "output_text"):
                                v = node.get(key)
                                if isinstance(v, str):
                                    texts.append(v)
                            # Recurse other values
                            for v in node.values():
                                texts.extend(collect_text(v))
                        elif isinstance(node, list):
                            for item in node:
                                texts.extend(collect_text(item))
                        return texts

                    texts = collect_text(msg)
                    content = "\n".join([t for t in texts if isinstance(t, str) and t.strip()])
                    content = content.strip()

                    if not content:
                        raise RuntimeError("OpenRouter choice missing message content")
                    return content

                except httpx.HTTPStatusError as e:
                    # Retry on transient 5xx
                    if 500 <= e.response.status_code < 600 and attempt < 2:
                        last_err = e
                        continue
                    raise RuntimeError(
                        f"OpenRouter API error: {e.response.status_code} - {e.response.text}"
                    )
                except (httpx.ConnectError, httpx.ReadTimeout) as e:
                    # Retry network hiccups
                    last_err = e
                    if attempt < 2:
                        continue
                    raise RuntimeError(f"OpenRouter API error: {e!s}")
                except Exception as e:
                    raise RuntimeError(f"OpenRouter API error: {e!s}")
            # If we exhausted retries
            if last_err:
                raise RuntimeError(f"OpenRouter API error after retries: {last_err!s}")

    def is_available(self) -> bool:
        """Check if OpenRouter API is available."""
        return bool(self.api_key)
