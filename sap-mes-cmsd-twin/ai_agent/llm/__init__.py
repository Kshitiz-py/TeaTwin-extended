"""
Generic LLM Client — single class supporting all major providers via configuration.
Uses ProviderManager internally for separate chat + embedding provider support.
"""
from .provider_manager import (
    ProviderManager,
    ProviderConfig,
    PROVIDER_PRESETS,
    provider_manager,
)


class LLMClient:
    """Thin compatibility wrapper around ProviderManager.
    Presents the simple API that routes.py expects:
      get_config() → dict
      configure(api_style, host, api_key, chat_model, embed_model) → dict
      test_connection() → dict
      disconnect() → dict
    """

    def __init__(self, manager: ProviderManager | None = None):
        self._manager = manager or provider_manager

    def get_config(self) -> dict:
        """Return current connection state (for GET /agent/status)."""
        return self._manager.get_status()

    def configure(
        self,
        api_style: str = "ollama",
        host: str = "",
        api_key: str = "",
        chat_model: str = "",
        embed_model: str = "",
    ) -> dict:
        """Configure the chat provider (and embed if model given).
        Returns test results for the connection.
        """
        chat_cfg = ProviderConfig(
            provider_type=api_style,
            host=host,
            api_key=api_key,
            chat_model=chat_model,
            embed_model=embed_model,
        )
        return self._manager.configure(chat_cfg)

    def test_connection(self) -> dict:
        """Test the currently configured provider(s)."""
        return self._manager.test()

    def configure_embed(self, api_style: str, host: str, api_key: str = "", embed_model: str = ""):
        """Configure a separate embedding provider."""
        embed_cfg = ProviderConfig(
            provider_type=api_style,
            host=host,
            api_key=api_key,
            chat_model="",
            embed_model=embed_model,
        )
        self._manager.configure_embed(embed_cfg)

    def test_embed_connection(self) -> dict:
        """Test the embedding provider connection."""
        return self._manager.test_embed()

    def disconnect(self) -> dict:
        """Disconnect / close current provider connections."""
        self._manager.close()
        return {"connected": False, "message": "All provider connections closed"}

    # ── Delegate chat/embed to manager ──────────────────────
    def chat(self, messages, temperature=0.1, stream=False, max_tokens=4096):
        return self._manager.chat(messages, temperature, stream, max_tokens)

    def chat_json(self, system_prompt, user_prompt, temperature=0.0):
        return self._manager.chat_json(system_prompt, user_prompt, temperature)

    def list_models(self) -> list[dict[str, str]]:
        """List models from the currently configured chat provider."""
        return self._manager.list_models()

    def embed(self, texts):
        return self._manager.embed(texts)


# ── Module-level singleton ────────────────────────────────
llm_client = LLMClient(provider_manager)


def get_preset(provider_type: str, api_key: str = "") -> ProviderConfig:
    """Convenience: create a ProviderConfig from built-in presets."""
    return ProviderConfig.from_preset(provider_type, api_key)


__all__ = [
    "LLMClient",
    "llm_client",
    "PROVIDER_PRESETS",
    "get_preset",
    "ProviderManager",
    "ProviderConfig",
]
