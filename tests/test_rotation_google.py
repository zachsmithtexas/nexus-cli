"""Tests for Google AI Studio key rotation."""

import json
from unittest.mock import Mock, mock_open, patch

import httpx
import pytest

from connectors.providers.google_ai_studio import GoogleAiStudioProvider


class TestGoogleAiStudioRotation:
    """Test Google AI Studio key rotation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_keys = ["key1", "key2", "key3"]
        self.provider = GoogleAiStudioProvider("gemini-2.5-pro", self.api_keys)

    @patch("builtins.open", new_callable=mock_open, read_data='{"current_index": 1}')
    @patch("pathlib.Path.exists")
    def test_load_key_index_from_cache(self, mock_exists, mock_file):
        """Test loading key index from cache file."""
        mock_exists.return_value = True

        provider = GoogleAiStudioProvider("test-model", self.api_keys)
        assert provider.current_key_index == 1

    @patch("pathlib.Path.exists")
    def test_load_key_index_no_cache(self, mock_exists):
        """Test default key index when no cache exists."""
        mock_exists.return_value = False

        provider = GoogleAiStudioProvider("test-model", self.api_keys)
        assert provider.current_key_index == 0

    def test_get_current_api_key(self):
        """Test getting current API key."""
        self.provider.current_key_index = 1
        key = self.provider._get_current_api_key()
        assert key == "key2"

    def test_get_current_api_key_wraps_around(self):
        """Test key index wraps around when out of bounds."""
        self.provider.current_key_index = 5  # Out of bounds
        key = self.provider._get_current_api_key()
        assert key == "key3"  # Should wrap to index 2 (5 % 3 = 2)
        assert self.provider.current_key_index == 2

    @patch("builtins.open", new_callable=mock_open)
    def test_save_key_index(self, mock_file):
        """Test saving key index to cache."""
        self.provider.current_key_index = 2
        self.provider._save_key_index()

        mock_file.assert_called_once()
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        data = json.loads(written_data)
        assert data["current_index"] == 2

    @patch("builtins.open", new_callable=mock_open)
    def test_rotate_to_next_key(self, mock_file):
        """Test rotating to next key."""
        self.provider.current_key_index = 0
        self.provider.cooldown_seconds = 0  # Skip sleep for testing

        self.provider._rotate_to_next_key()

        assert self.provider.current_key_index == 1
        mock_file.assert_called_once()  # Should save new index

    @patch("builtins.open", new_callable=mock_open)
    def test_rotate_wraps_around(self, mock_file):
        """Test key rotation wraps around to beginning."""
        self.provider.current_key_index = 2  # Last key
        self.provider.cooldown_seconds = 0  # Skip sleep for testing

        self.provider._rotate_to_next_key()

        assert self.provider.current_key_index == 0  # Should wrap to first key

    def test_rotate_single_key_no_op(self):
        """Test rotation does nothing with single key."""
        single_key_provider = GoogleAiStudioProvider("test", ["single_key"])
        single_key_provider.current_key_index = 0

        single_key_provider._rotate_to_next_key()

        assert single_key_provider.current_key_index == 0  # Should not change

    @patch("httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open)
    @pytest.mark.asyncio
    async def test_http_429_triggers_rotation(self, mock_file, mock_client):
        """Test that HTTP 429 triggers key rotation."""
        # Mock HTTP 429 response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        mock_http_error = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response
        )

        # Create a mock response for the successful call
        success_response = Mock()
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Success"}]}}]
        }

        # First call raises 429, second call succeeds
        mock_client_instance = Mock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client_instance.post.side_effect = [
            mock_http_error,  # First call fails with 429
            success_response,  # Second call succeeds
        ]

        self.provider.cooldown_seconds = 0  # Skip sleep for testing
        initial_index = self.provider.current_key_index

        result = await self.provider.complete("test prompt")

        # Should have rotated to next key
        assert self.provider.current_key_index == (initial_index + 1) % len(
            self.api_keys
        )
        assert result == "Success"

    @patch("httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open)
    @pytest.mark.asyncio
    async def test_all_keys_exhausted(self, mock_file, mock_client):
        """Test behavior when all keys return 429."""
        # Mock HTTP 429 response for all attempts
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        mock_http_error = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response
        )

        mock_client_instance = Mock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client_instance.post.side_effect = mock_http_error

        self.provider.cooldown_seconds = 0  # Skip sleep for testing

        with pytest.raises(RuntimeError, match="All Google API keys exhausted"):
            await self.provider.complete("test prompt")

    @patch.dict("os.environ", {"USE_PAID_MODELS": "false"})
    @pytest.mark.asyncio
    async def test_paid_models_disabled(self):
        """Test that paid models are skipped when disabled."""
        with pytest.raises(RuntimeError, match="Paid models disabled"):
            await self.provider.complete("test prompt")

    def test_no_api_keys_configured(self):
        """Test behavior when no API keys are configured."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="No Google API keys configured"):
                GoogleAiStudioProvider("test-model")
