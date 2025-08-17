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

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 4000,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
                response.raise_for_status()

                data = response.json()
                # Robust handling: some errors return 200 with an error payload
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
                content = msg.get("content")
                # Support content as either a string or a list of text parts
                if isinstance(content, list):
                    parts = []
                    for part in content:
                        # Common shapes: {"type":"text","text":"..."} or {"text":"..."}
                        if isinstance(part, dict):
                            txt = part.get("text") or part.get("content")
                            if txt:
                                parts.append(str(txt))
                        elif isinstance(part, str):
                            parts.append(part)
                    content = "\n".join(parts).strip()

                if not content or not isinstance(content, str):
                    raise RuntimeError("OpenRouter choice missing message content")
                return content.strip()

            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"OpenRouter API error: {e.response.status_code} - {e.response.text}"
                )
            except Exception as e:
                raise RuntimeError(f"OpenRouter API error: {e!s}")

    def is_available(self) -> bool:
        """Check if OpenRouter API is available."""
        return bool(self.api_key)
