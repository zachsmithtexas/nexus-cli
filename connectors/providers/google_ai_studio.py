"""Google AI Studio API provider with multi-key rotation."""

import json
import logging
import os
import time
from pathlib import Path

import httpx

from .base import BaseProvider

logger = logging.getLogger(__name__)


class GoogleAiStudioProvider(BaseProvider):
    """Provider for Google AI Studio API with key rotation."""

    def __init__(self, model_name: str, api_keys: list[str] | None = None):
        # Don't use single api_key, use key rotation instead
        super().__init__(model_name, None)
        self.base_url = "https://generativelanguage.googleapis.com"

        # Load API keys from environment or provided list
        self.api_keys = api_keys or self._load_api_keys()

        # Key rotation settings
        self.rotation_strategy = "round_robin"
        self.cooldown_seconds = 60

        # Cache directory for key index persistence
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.key_index_file = self.cache_dir / "google_ai_studio.keyidx"

        # Load current key index
        self.current_key_index = self._load_key_index()

    def _load_api_keys(self) -> list[str]:
        """Load API keys from environment variables."""
        keys = []
        for i in range(1, 6):  # GOOGLE_API_KEY_1 through GOOGLE_API_KEY_5
            key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if key and key.strip():
                keys.append(key.strip())

        if not keys:
            raise RuntimeError("No Google API keys configured")

        return keys

    def _load_key_index(self) -> int:
        """Load the current key index from cache."""
        if self.key_index_file.exists():
            try:
                with open(self.key_index_file) as f:
                    data = json.load(f)
                    return data.get("current_index", 0)
            except (OSError, json.JSONDecodeError):
                pass
        return 0

    def _save_key_index(self):
        """Save the current key index to cache."""
        try:
            with open(self.key_index_file, "w") as f:
                json.dump({"current_index": self.current_key_index}, f)
        except OSError as e:
            logger.warning(f"Failed to save key index: {e}")

    def _get_current_api_key(self) -> str:
        """Get the current API key based on rotation index."""
        if not self.api_keys:
            raise RuntimeError("No API keys available")

        # Ensure index is within bounds
        self.current_key_index = self.current_key_index % len(self.api_keys)
        key = self.api_keys[self.current_key_index]

        logger.info(f"Using Google API key index: {self.current_key_index + 1}")
        return key

    def _rotate_to_next_key(self):
        """Rotate to the next available API key."""
        if len(self.api_keys) <= 1:
            logger.warning("Only one API key available, cannot rotate")
            return

        old_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._save_key_index()

        logger.info(
            f"Rotated Google API key from index {old_index + 1} to {self.current_key_index + 1}"
        )

        # Apply cooldown
        if self.cooldown_seconds > 0:
            logger.info(f"Applying cooldown of {self.cooldown_seconds} seconds")
            time.sleep(self.cooldown_seconds)

    async def complete(self, prompt: str) -> str:
        """Complete a prompt using Google AI Studio API with key rotation."""
        if not self.api_keys:
            raise RuntimeError("No Google API keys configured")

        # Google AI Studio often has a free tier; do not gate on USE_PAID_MODELS

        max_retries = len(self.api_keys)

        for attempt in range(max_retries):
            api_key = self._get_current_api_key()

            try:
                return await self._make_request(prompt, api_key)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit / quota exceeded
                    logger.warning(
                        f"HTTP 429 from Google AI Studio (key index {self.current_key_index + 1}), rotating key"
                    )
                    self._rotate_to_next_key()
                    if attempt < max_retries - 1:
                        continue
                    else:
                        raise RuntimeError(
                            "All Google API keys exhausted due to rate limits"
                        )
                else:
                    raise RuntimeError(
                        f"Google AI Studio API error: {e.response.status_code} - {e.response.text}"
                    )

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Request failed with key index {self.current_key_index + 1}, trying next key: {e}"
                    )
                    self._rotate_to_next_key()
                    continue
                else:
                    raise RuntimeError(f"Google AI Studio API error: {e!s}")

        raise RuntimeError("All Google API keys failed")

    async def _make_request(self, prompt: str, api_key: str) -> str:
        """Make the actual API request to Google AI Studio."""
        headers = {"Content-Type": "application/json"}

        # Use Google AI Studio's REST API format
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4000},
        }

        url = f"{self.base_url}/v1beta/models/{self.model_name}:generateContent"
        params = {"key": api_key}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url, headers=headers, json=payload, params=params
            )
            response.raise_for_status()

            data = response.json()

            # Extract content from Google AI Studio response format
            if data.get("candidates"):
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()

            raise RuntimeError("Unexpected response format from Google AI Studio")

    def is_available(self) -> bool:
        """Check if Google AI Studio API is available."""
        return bool(self.api_keys)
