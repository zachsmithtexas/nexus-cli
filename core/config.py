"""Configuration management."""

import os
import re
import tomllib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    """Provider configuration."""

    name: str
    providers: list[str]
    model: str
    budgets: dict[str, float]


class DiscordSettings(BaseModel):
    """Discord-specific settings."""

    bot_token: str | None = None
    app_id: str | None = None
    guild_id: str | None = None
    commands_channel_id: str | None = None
    updates_channel_id: str | None = None
    webhooks: dict[str, str | None] = {}


class Settings(BaseModel):
    """Application settings."""

    project_name: str = "Nexus CLI"
    log_level: str = "INFO"
    discord: DiscordSettings = DiscordSettings()
    obsidian_path: str | None = None
    use_paid_models: bool = True
    watch_interval: float = 1.0
    max_concurrent_tasks: int = 5
    timeout: float = 30.0
    max_retries: int = 3


class ConfigManager:
    """Configuration manager with environment variable expansion."""

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self._settings: Settings | None = None
        self._roles: dict[str, ProviderConfig] | None = None
        self._models: dict[str, dict[str, Any]] | None = None

    def _expand_env_vars(self, value: Any) -> Any:
        """Expand environment variables in configuration values."""
        if isinstance(value, str):
            # Replace ${VAR} and ${VAR:-default} patterns
            def replace_var(match):
                var_expr = match.group(1)
                if ":-" in var_expr:
                    var_name, default = var_expr.split(":-", 1)
                    return os.getenv(var_name, default)
                else:
                    return os.getenv(var_expr, match.group(0))

            return re.sub(r"\$\{([^}]+)\}", replace_var, value)
        elif isinstance(value, dict):
            return {k: self._expand_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._expand_env_vars(item) for item in value]
        else:
            return value

    def get_settings(self) -> Settings:
        """Get application settings."""
        if self._settings is None:
            settings_file = self.config_dir / "settings.toml"
            if settings_file.exists():
                with open(settings_file, "rb") as f:
                    data = tomllib.load(f)

                # Expand environment variables
                data = self._expand_env_vars(data)

                # Handle nested configuration properly
                settings_data = {}

                # Extract top-level settings
                for key in [
                    "project_name",
                    "log_level",
                    "obsidian_path",
                    "use_paid_models",
                    "watch_interval",
                    "max_concurrent_tasks",
                    "timeout",
                    "max_retries",
                ]:
                    if key in data.get("general", {}):
                        settings_data[key] = data["general"][key]
                    for section_data in data.values():
                        if isinstance(section_data, dict) and key in section_data:
                            settings_data[key] = section_data[key]

                # Handle Discord configuration
                if "discord" in data:
                    discord_data = data["discord"].copy()
                    # Handle nested webhooks
                    if "webhooks" not in discord_data and "discord.webhooks" in data:
                        discord_data["webhooks"] = data["discord.webhooks"]
                    settings_data["discord"] = discord_data

                self._settings = Settings(**settings_data)
            else:
                self._settings = Settings()

        return self._settings

    def get_roles(self) -> dict[str, ProviderConfig]:
        """Get role configurations."""
        if self._roles is None:
            roles_file = self.config_dir / "roles.yaml"
            if roles_file.exists():
                with open(roles_file) as f:
                    data = yaml.safe_load(f)

                self._roles = {}
                for role_name, role_data in data.get("roles", {}).items():
                    self._roles[role_name] = ProviderConfig(name=role_name, **role_data)
            else:
                self._roles = {}

        return self._roles

    def get_models(self) -> dict[str, dict[str, Any]]:
        """Get model configurations."""
        if self._models is None:
            models_file = self.config_dir / "models.yaml"
            if models_file.exists():
                with open(models_file) as f:
                    data = yaml.safe_load(f)
                self._models = data.get("models", {})
            else:
                self._models = {}

        return self._models

    def get_role_config(self, role: str) -> ProviderConfig | None:
        """Get configuration for a specific role."""
        return self.get_roles().get(role)

    def get_model_config(self, model_name: str) -> dict[str, Any] | None:
        """Get configuration for a specific model."""
        return self.get_models().get(model_name)
