"""Tests for rate limiting functionality."""

import tempfile
import time
from pathlib import Path

import yaml

from core.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test rate limiting functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary limits config file
        self.temp_limits = {
            "providers": {
                "test_provider": {
                    "models": {
                        "test_model": {
                            "rpm": 1,
                            "tpm": 100,
                        }  # Very restrictive for testing
                    }
                }
            },
            "default_limits": {"rpm": 60, "tpm": 10000},
        }

        # Create temporary config file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        yaml.dump(self.temp_limits, self.temp_file)
        self.temp_file.close()

        self.rate_limiter = RateLimiter(self.temp_file.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_load_limits_from_config(self):
        """Test loading limits from configuration file."""
        rpm, tpm = self.rate_limiter._get_model_limits("test_provider", "test_model")
        assert rpm == 1
        assert tpm == 100

    def test_get_default_limits(self):
        """Test fallback to default limits for unconfigured models."""
        rpm, tpm = self.rate_limiter._get_model_limits(
            "unknown_provider", "unknown_model"
        )
        assert rpm == 60  # From default_limits
        assert tpm == 10000  # From default_limits

    def test_no_limits_configured(self):
        """Test behavior when no limits are configured."""
        # Create rate limiter with non-existent config
        limiter = RateLimiter("nonexistent.yaml")
        rpm, tpm = limiter._get_model_limits("provider", "model")
        assert rpm == 60  # Should fall back to hardcoded defaults
        assert tpm == 10000

    def test_first_request_allowed(self):
        """Test that first request is always allowed."""
        allowed, sleep_time = self.rate_limiter.check_limits(
            "test_provider", "test_model", estimated_tokens=50  # Lower token count
        )
        assert allowed is True
        assert sleep_time is None

    def test_rpm_limit_enforcement(self):
        """Test that RPM limits are enforced."""
        provider = "test_provider"
        model = "test_model"

        # First request should be allowed
        allowed, sleep_time = self.rate_limiter.check_limits(provider, model, estimated_tokens=50)
        assert allowed is True

        # Record the request
        self.rate_limiter.record_request(provider, model, 50)

        # Second request should be blocked (RPM limit is 1)
        allowed, sleep_time = self.rate_limiter.check_limits(provider, model, estimated_tokens=50)
        assert allowed is False
        assert sleep_time is not None
        assert sleep_time > 0

    def test_tpm_limit_enforcement(self):
        """Test that TPM limits are enforced."""
        provider = "test_provider"
        model = "test_model"

        # Request with tokens that would exceed TPM limit (100)
        allowed, sleep_time = self.rate_limiter.check_limits(
            provider, model, estimated_tokens=150
        )
        assert allowed is False
        assert sleep_time is not None

    def test_window_cleanup(self):
        """Test that old entries are cleaned up after window expires."""
        provider = "test_provider"
        model = "test_model"

        # Record a request
        self.rate_limiter.record_request(provider, model, 50)

        # Should be blocked immediately
        allowed, _ = self.rate_limiter.check_limits(provider, model, estimated_tokens=50)
        assert allowed is False

        # Manually advance time by manipulating history
        # (In real tests, you'd use time mocking, but this is simpler for now)
        current_time = time.time()
        old_time = current_time - 61  # 61 seconds ago (outside window)

        # Replace the recent request with an old one
        self.rate_limiter.request_history[model].clear()
        self.rate_limiter.request_history[model].append((old_time, 1))
        # Also clear token history since both RPM and TPM limits apply
        self.rate_limiter.token_history[model].clear()
        self.rate_limiter.token_history[model].append((old_time, 50))

        # Should now be allowed since old request is outside window
        allowed, _ = self.rate_limiter.check_limits(provider, model, estimated_tokens=50)
        assert allowed is True

    def test_zero_limits_bypass(self):
        """Test that zero limits are bypassed (no limiting)."""
        # Create a config with zero limits
        zero_limits = {
            "providers": {
                "unlimited_provider": {
                    "models": {"unlimited_model": {"rpm": 0, "tpm": 0}}
                }
            }
        }

        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(zero_limits, temp_file)
        temp_file.close()

        try:
            limiter = RateLimiter(temp_file.name)

            # Multiple requests should all be allowed
            for i in range(10):
                allowed, _ = limiter.check_limits(
                    "unlimited_provider", "unlimited_model", 1000
                )
                assert allowed is True
                limiter.record_request("unlimited_provider", "unlimited_model", 1000)
        finally:
            Path(temp_file.name).unlink(missing_ok=True)

    def test_current_usage_tracking(self):
        """Test that current usage is tracked correctly."""
        provider = "test_provider"
        model = "test_model"

        # Initially no usage
        usage = self.rate_limiter.get_current_usage(provider, model)
        assert usage["current_requests"] == 0
        assert usage["current_tokens"] == 0
        assert usage["rpm_limit"] == 1
        assert usage["tpm_limit"] == 100

        # Record some usage
        self.rate_limiter.record_request(provider, model, 75)

        # Check updated usage
        usage = self.rate_limiter.get_current_usage(provider, model)
        assert usage["current_requests"] == 1
        assert usage["current_tokens"] == 75

    def test_multiple_models_isolated(self):
        """Test that different models have isolated rate limits."""
        provider = "test_provider"
        model1 = "test_model"
        model2 = "other_model"

        # Record request for model1
        self.rate_limiter.record_request(provider, model1, 50)

        # model1 should be blocked
        allowed, _ = self.rate_limiter.check_limits(provider, model1)
        assert allowed is False

        # model2 should still be allowed (different model)
        allowed, _ = self.rate_limiter.check_limits(provider, model2)
        assert allowed is True
