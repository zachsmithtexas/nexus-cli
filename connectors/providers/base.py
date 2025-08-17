"""Base provider interface for AI model connections."""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract base class for AI model providers."""

    def __init__(self, model_name: str, api_key: str | None = None):
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Complete a prompt and return the response."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""

    def get_name(self) -> str:
        """Get the provider name."""
        return self.__class__.__name__.replace("Provider", "").lower()
