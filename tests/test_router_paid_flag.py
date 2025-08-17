"""Tests for paid model gating in router."""

from unittest.mock import Mock, patch

import pytest

from core.config import ConfigManager
from core.router import ProviderRouter


class TestRouterPaidFlag:
    """Test paid model gating functionality in router."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_manager = Mock(spec=ConfigManager)
        self.router = ProviderRouter(self.config_manager)

        # Mock config data
        self.config_manager.config = {
            "models": {
                "paid_model": {"is_paid": True},
                "free_model": {"is_paid": False},
            },
            "provider_routes": [
                {
                    "id": "paid_route_model",
                    "provider": "test_provider",
                    "is_paid": True,
                },
                {
                    "id": "free_route_model",
                    "provider": "test_provider",
                    "is_paid": False,
                },
                {
                    "id": "unspecified_model",
                    "provider": "test_provider",
                },  # No is_paid field
            ],
        }

    @patch.dict("os.environ", {"USE_PAID_MODELS": "false"})
    def test_skip_paid_model_legacy_config(self):
        """Test skipping paid models from legacy models config."""
        result = self.router._should_skip_paid_provider("test_provider", "paid_model")
        assert result is True

        result = self.router._should_skip_paid_provider("test_provider", "free_model")
        assert result is False

    @patch.dict("os.environ", {"USE_PAID_MODELS": "false"})
    def test_skip_paid_model_provider_routes(self):
        """Test skipping paid models from provider routes config."""
        result = self.router._should_skip_paid_provider(
            "test_provider", "paid_route_model"
        )
        assert result is True

        result = self.router._should_skip_paid_provider(
            "test_provider", "free_route_model"
        )
        assert result is False

        # Models without is_paid field should be treated as free
        result = self.router._should_skip_paid_provider(
            "test_provider", "unspecified_model"
        )
        assert result is False

    @patch.dict("os.environ", {"USE_PAID_MODELS": "true"})
    def test_allow_paid_models_when_enabled(self):
        """Test that paid models are allowed when USE_PAID_MODELS=true."""
        result = self.router._should_skip_paid_provider("test_provider", "paid_model")
        assert result is False

        result = self.router._should_skip_paid_provider(
            "test_provider", "paid_route_model"
        )
        assert result is False

    @patch.dict("os.environ", {}, clear=True)
    def test_default_allows_paid_models(self):
        """Test that paid models are allowed by default when env var not set."""
        result = self.router._should_skip_paid_provider("test_provider", "paid_model")
        assert result is False

    @patch.dict("os.environ", {"USE_PAID_MODELS": "false"})
    def test_unknown_model_treated_as_free(self):
        """Test that unknown models are treated as free."""
        result = self.router._should_skip_paid_provider(
            "test_provider", "unknown_model"
        )
        assert result is False

    @patch.dict("os.environ", {"USE_PAID_MODELS": "FALSE"})  # Test case insensitivity
    def test_case_insensitive_env_var(self):
        """Test that environment variable is case insensitive."""
        result = self.router._should_skip_paid_provider("test_provider", "paid_model")
        assert result is True

    @patch.dict("os.environ", {"USE_PAID_MODELS": "0"})
    def test_falsy_values_disable_paid_models(self):
        """Test that falsy values disable paid models."""
        result = self.router._should_skip_paid_provider("test_provider", "paid_model")
        assert result is True

    @patch.dict("os.environ", {"USE_PAID_MODELS": "false"})
    @patch("core.router.console")
    @pytest.mark.asyncio
    async def test_complete_skips_paid_model_in_chain(self, mock_console):
        """Test that complete() skips paid models in provider chain."""
        # Mock role config
        role_config = Mock()
        role_config.model = "paid_model"
        role_config.providers = ["provider1", "provider2"]

        self.config_manager.get_role_config.return_value = role_config

        # Mock provider creation to avoid actual provider instantiation
        with patch.object(self.router, "_get_provider", return_value=None):
            result = await self.router.complete("test_role", "test prompt")

        # Should return None and log that paid model was skipped
        assert result is None
        mock_console.log.assert_called()

        # Check that "Skipping paid model" message was logged
        log_calls = [call.args[0] for call in mock_console.log.call_args_list]
        assert any("Skipping paid model" in msg for msg in log_calls)

    @patch.dict("os.environ", {"USE_PAID_MODELS": "false"})
    @patch("core.router.console")
    @pytest.mark.asyncio
    async def test_complete_with_model_skips_paid_direct_routing(self, mock_console):
        """Test that _complete_with_model() skips paid models in direct routing."""
        result = await self.router._complete_with_model(
            "paid_route_model", "test prompt"
        )

        # Should return None and log that paid model was skipped
        assert result is None
        mock_console.log.assert_called_with(
            "Skipping paid model paid_route_model (USE_PAID_MODELS=false)"
        )

    @patch.dict("os.environ", {"USE_PAID_MODELS": "true"})
    @pytest.mark.asyncio
    async def test_complete_with_model_allows_paid_when_enabled(self):
        """Test that paid models are processed when enabled."""
        # Mock successful provider flow
        mock_provider = Mock()
        mock_provider.is_available.return_value = True
        # Need to make it an async coroutine
        async def mock_complete(prompt):
            return "test response"
        mock_provider.complete = mock_complete

        with patch.object(self.router, "_get_provider", return_value=mock_provider):
            with patch.object(
                self.router.rate_limiter, "check_limits", return_value=(True, None)
            ):
                with patch.object(self.router.rate_limiter, "record_request"):
                    with patch("core.router.console"):
                        result = await self.router._complete_with_model(
                            "paid_route_model", "test prompt"
                        )

        # Should complete successfully
        assert result == "test response"
