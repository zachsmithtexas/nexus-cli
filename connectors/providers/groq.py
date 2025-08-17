"""Groq API provider."""

import os

import httpx

from .base import BaseProvider


class GroqProvider(BaseProvider):
    """Provider for Groq API."""

    def __init__(self, model_name: str, api_key: str | None = None):
        super().__init__(model_name, api_key or os.getenv("GROQ_API_KEY"))
        self.base_url = "https://api.groq.com/openai/v1"

    async def complete(self, prompt: str) -> str:
        """Complete a prompt using Groq API."""
        if not self.api_key:
            raise RuntimeError("Groq API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
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
                return data["choices"][0]["message"]["content"].strip()

            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"Groq API error: {e.response.status_code} - {e.response.text}"
                )
            except Exception as e:
                raise RuntimeError(f"Groq API error: {e!s}")

    def is_available(self) -> bool:
        """Check if Groq API is available."""
        return bool(self.api_key)
