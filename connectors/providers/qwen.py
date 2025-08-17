"""Qwen API provider."""

import os

import httpx

from .base import BaseProvider


class QwenProvider(BaseProvider):
    """Provider for Qwen API."""

    def __init__(self, model_name: str, api_key: str | None = None):
        super().__init__(model_name, api_key or os.getenv("QWEN_API_KEY"))
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"

    async def complete(self, prompt: str) -> str:
        """Complete a prompt using Qwen API."""
        if not self.api_key:
            raise RuntimeError("Qwen API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {"temperature": 0.1, "max_tokens": 4000},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/services/aigc/text-generation/generation",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

                data = response.json()
                return data["output"]["choices"][0]["message"]["content"].strip()

            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"Qwen API error: {e.response.status_code} - {e.response.text}"
                )
            except Exception as e:
                raise RuntimeError(f"Qwen API error: {e!s}")

    def is_available(self) -> bool:
        """Check if Qwen API is available."""
        return bool(self.api_key)
