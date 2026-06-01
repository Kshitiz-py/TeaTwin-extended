"""
Provider Manager — factory that creates and manages LLM provider instances.
Supports separate chat and embedding providers.
Maintains the singleton used throughout the application.
"""
import logging
from typing import Any

from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider

logger = logging.getLogger("ai-agent.llm.manager")

# Registry of available provider types
PROVIDER_REGISTRY = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    # OpenAI-compatible aliases
    "deepseek": OpenAIProvider,       # DeepSeek is OpenAI-compatible
    "together": OpenAIProvider,       # Together AI is OpenAI-compatible
    "grok": OpenAIProvider,           # xAI Grok is OpenAI-compatible
    "openrouter": OpenAIProvider,     # OpenRouter is OpenAI-compatible
    "perplexity": OpenAIProvider,     # Perplexity is OpenAI-compatible
    "github-models": OpenAIProvider,  # GitHub Models is OpenAI-compatible
    "custom": OpenAIProvider,         # Generic OpenAI-compatible endpoint
}

# Default configuration presets
# These are the source of truth — served by GET /agent/providers
PROVIDER_PRESETS = {
    "ollama": {
        "host": "http://localhost:11434",
        "chat_model": "qwen3.5:397b-cloud",
        "embed_model": "nomic-embed-text:latest",
        "api_style": "ollama",
    },
    "openai": {
        "host": "https://api.openai.com",
        "chat_model": "gpt-4o",
        "embed_model": "text-embedding-3-small",
        "api_style": "openai",
    },
    "anthropic": {
        "host": "https://api.anthropic.com",
        "chat_model": "claude-sonnet-4-20250514",
        "embed_model": "",
        "api_style": "anthropic",
    },
    "deepseek": {
        "host": "https://api.deepseek.com",
        "chat_model": "deepseek-chat",
        "embed_model": "",
        "api_style": "openai",
    },
    "together": {
        "host": "https://api.together.xyz",
        "chat_model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "embed_model": "",
        "api_style": "openai",
    },
    "grok": {
        "host": "https://api.x.ai",
        "chat_model": "grok-2",
        "embed_model": "",
        "api_style": "openai",
    },
    "openrouter": {
        "host": "https://openrouter.ai/api",
        "chat_model": "openai/gpt-4o",
        "embed_model": "",
        "api_style": "openai",
    },
    "perplexity": {
        "host": "https://api.perplexity.ai",
        "chat_model": "sonar-pro",
        "embed_model": "",
        "api_style": "openai",
    },
    "github-models": {
        "host": "https://models.inference.ai.azure.com",
        "chat_model": "gpt-4o",
        "embed_model": "",
        "api_style": "openai",
    },
    "custom": {
        "host": "",
        "chat_model": "",
        "embed_model": "",
        "api_style": "openai",
    },
}


class ProviderConfig:
    """Runtime configuration for a single provider."""

    def __init__(
        self,
        provider_type: str = "ollama",
        host: str = "",
        api_key: str = "",
        chat_model: str = "",
        embed_model: str = "",
    ):
        self.provider_type = provider_type
        self.host = host
        self.api_key = api_key
        self.chat_model = chat_model
        self.embed_model = embed_model

    @classmethod
    def from_preset(cls, provider_type: str, api_key: str = "") -> "ProviderConfig":
        """Create a config from built-in presets."""
        preset = PROVIDER_PRESETS.get(provider_type, {})
        return cls(
            provider_type=provider_type,
            host=preset.get("host", ""),
            api_key=api_key,
            chat_model=preset.get("chat_model", ""),
            embed_model=preset.get("embed_model", ""),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "provider_type": self.provider_type,
            "host": self.host,
            "chat_model": self.chat_model,
            "embed_model": self.embed_model,
            "has_api_key": bool(self.api_key),
        }


def _create_provider(config: ProviderConfig) -> LLMProvider:
    """Create a provider instance from a config."""
    provider_cls = PROVIDER_REGISTRY.get(config.provider_type)
    if not provider_cls:
        raise ValueError(f"Unknown provider type: {config.provider_type}. "
                         f"Available: {list(PROVIDER_REGISTRY.keys())}")

    provider = provider_cls()
    provider.configure(
        host=config.host or None,
        api_key=config.api_key or None,
        chat_model=config.chat_model or None,
        embed_model=config.embed_model or None,
    )
    return provider


class ProviderManager:
    """Manages chat and embedding provider instances.
    Uses separate providers so you can chat with Claude and embed with Ollama.
    """

    def __init__(self):
        self._chat_provider: LLMProvider | None = None
        self._embed_provider: LLMProvider | None = None
        self._chat_config: ProviderConfig | None = None
        self._embed_config: ProviderConfig | None = None

    @property
    def chat_provider(self) -> LLMProvider:
        if self._chat_provider is None:
            # Create default from presets
            self._chat_config = ProviderConfig.from_preset("ollama")
            self._chat_provider = _create_provider(self._chat_config)
        return self._chat_provider

    @property
    def embed_provider(self) -> LLMProvider:
        if self._embed_provider is None:
            # Default: use same as chat provider
            return self.chat_provider
        return self._embed_provider

    def configure(
        self,
        chat_config: ProviderConfig,
        embed_config: ProviderConfig | None = None,
    ) -> dict[str, Any]:
        """Configure chat and (optionally) embedding providers.

        Args:
            chat_config: Configuration for the chat/LLM provider.
            embed_config: Configuration for the embedding provider.
                If None, uses chat_config for both (if the provider supports it).

        Returns:
            Dict with test results for chat (and embed if configured separately).
        """
        # Close existing providers
        if self._chat_provider:
            self._chat_provider.close()
        if self._embed_provider and self._embed_provider is not self._chat_provider:
            self._embed_provider.close()

        # Create chat provider
        self._chat_config = chat_config
        self._chat_provider = _create_provider(chat_config)

        # Create or reuse embed provider
        if embed_config and (
            embed_config.provider_type != chat_config.provider_type
            or embed_config.host != chat_config.host
        ):
            self._embed_config = embed_config
            self._embed_provider = _create_provider(embed_config)
        else:
            self._embed_config = None
            self._embed_provider = None  # Will fall back to chat_provider

        # Test connections
        chat_test = self._chat_provider.test_connection()

        embed_test = None
        if self._embed_provider:
            try:
                embed_test = self._embed_provider.test_connection()
            except Exception as e:
                embed_test = {"ok": False, "message": str(e)}

        result = {
            "configured": True,
            "chat_provider": chat_config.provider_type,
            "chat_model": chat_config.chat_model,
            "chat_test": chat_test,
        }
        if embed_config:
            result["embed_provider"] = embed_config.provider_type
            result["embed_model"] = embed_config.embed_model
            result["embed_test"] = embed_test
        else:
            result["embed_provider"] = chat_config.provider_type
            result["embed_model"] = chat_config.embed_model

        return result

    def test(self) -> dict[str, Any]:
        """Test current provider connections."""
        chat_test = self.chat_provider.test_connection()

        embed_test = None
        if self._embed_provider:
            try:
                embed_test = self._embed_provider.test_connection()
            except Exception as e:
                embed_test = {"ok": False, "message": str(e)}

        result = {
            "chat": chat_test,
        }
        if embed_test:
            result["embed"] = embed_test

        return result

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        stream: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        return self.chat_provider.chat(messages, temperature, stream, max_tokens)

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        return self.chat_provider.chat_json(system_prompt, user_prompt, temperature, max_tokens)

    @property
    def last_usage(self) -> dict[str, int]:
        """Return token usage from the most recent chat completion (if available)."""
        provider = self._chat_provider
        if provider and hasattr(provider, 'last_usage'):
            return provider.last_usage
        return {}

    def list_models(self) -> list[dict[str, str]]:
        """List available models from the currently configured chat provider."""
        try:
            return self.chat_provider.list_models()
        except NotImplementedError:
            return []
        except Exception:
            return []

    def configure_embed(self, embed_config: ProviderConfig):
        """Configure just the embedding provider (keeps chat provider as-is)."""
        if self._embed_provider and self._embed_provider is not self._chat_provider:
            self._embed_provider.close()
        self._embed_config = embed_config
        self._embed_provider = _create_provider(embed_config)
        logger.info(f"Embed provider configured: {embed_config.provider_type} @ {embed_config.host}")

    def test_embed(self) -> dict[str, Any]:
        """Test the embedding provider connection."""
        if not self._embed_provider or self._embed_provider is self._chat_provider:
            return {"ok": False, "message": "No separate embed provider configured"}
        try:
            return self._embed_provider.test_connection()
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.embed_provider.embed(texts)

    def get_status(self) -> dict[str, Any]:
        """Return current configuration status (no live test — fast)."""
        status = {"connected": self._chat_config is not None}
        if self._chat_config:
            status.update(self._chat_config.to_dict())
        if self._embed_config:
            status["embed_provider"] = self._embed_config.to_dict()
        else:
            status["embed_provider"] = status.get("provider_type", "ollama")
        return status

    def close(self) -> None:
        if self._chat_provider:
            self._chat_provider.close()
        if self._embed_provider and self._embed_provider is not self._chat_provider:
            self._embed_provider.close()
        # Clear config so get_status reports disconnected after close
        self._chat_config = None
        self._embed_config = None
        self._chat_provider = None
        self._embed_provider = None


# Singleton
provider_manager = ProviderManager()
