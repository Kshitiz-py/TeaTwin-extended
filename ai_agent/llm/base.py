"""
Abstract base class for all LLM providers.
Each provider implements chat, chat_json, embed, and test_connection.
"""
from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for LLM backends (Ollama, OpenAI, Anthropic, etc.)."""

    @abstractmethod
    def configure(
        self,
        host: str | None = None,
        api_key: str | None = None,
        chat_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        """Update connection parameters at runtime."""
        ...

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """Test connectivity to the provider endpoint.
        Returns {"ok": bool, "host": str, "message": str, ...}.
        """
        ...

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        stream: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request. Returns the full response text."""
        ...

    @abstractmethod
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Chat with the model and parse the response as JSON.
        Uses a JSON-enforcing system prompt wrapper.
        """
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings. May raise NotImplementedError."""
        raise NotImplementedError(f"{type(self).__name__} does not support embeddings")

    def list_models(self) -> list[dict[str, str]]:
        """List available models from the provider. Returns [{"id": str, "name": str}, ...].
        May raise NotImplementedError for providers that don't support model listing.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support listing models")

    @abstractmethod
    def close(self) -> None:
        """Clean up HTTP client resources."""
        ...
