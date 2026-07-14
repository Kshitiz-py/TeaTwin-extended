"""
Generic LLM Client — single class supporting all major LLM providers via configuration.

API shapes supported:
  - "openai":   OpenAI-compatible (OpenAI, DeepSeek, Together, Grok, OpenRouter, etc.)
                POST /v1/chat/completions, POST /v1/embeddings, auth: Bearer token
  - "anthropic": Anthropic Claude
                POST /v1/messages, no embeddings, auth: x-api-key header
  - "ollama":   Ollama (local or cloud)
                POST /api/chat, POST /api/embeddings, auth: optional Bearer token

Usage:
    client = LLMClient(api_style="openai", host="https://api.openai.com",
                       api_key="sk-...", chat_model="gpt-4o")
    client.test_connection()
    client.chat([{"role": "user", "content": "Hello"}])
    client.chat_json(system_prompt, user_prompt)
    client.embed(["some text"])        # raises on anthropic
    client.configure(host="...", api_key="...")  # runtime reconfig
"""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("ai-agent.llm.client")


# ─── Provider Presets ───────────────────────────────────────────
# Each preset defines the shape and sensible defaults for a provider.
# Users can override any field at runtime.

PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "ollama": {
        "api_style": "ollama",
        "host": "http://localhost:11434",
        "chat_model": "qwen3.5:397b-cloud",
        "embed_model": "nomic-embed-text:latest",
    },
    "openai": {
        "api_style": "openai",
        "host": "https://api.openai.com",
        "chat_model": "gpt-4o",
        "embed_model": "text-embedding-3-small",
    },
    "anthropic": {
        "api_style": "anthropic",
        "host": "https://api.anthropic.com",
        "chat_model": "claude-sonnet-4-20250514",
        "embed_model": "",
    },
    "deepseek": {
        "api_style": "openai",
        "host": "https://api.deepseek.com",
        "chat_model": "deepseek-chat",
        "embed_model": "",
    },
    "together": {
        "api_style": "openai",
        "host": "https://api.together.xyz",
        "chat_model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "embed_model": "",
    },
    "grok": {
        "api_style": "openai",
        "host": "https://api.x.ai",
        "chat_model": "grok-2",
        "embed_model": "",
    },
    "openrouter": {
        "api_style": "openai",
        "host": "https://openrouter.ai/api",
        "chat_model": "openai/gpt-4o",
        "embed_model": "",
    },
    "perplexity": {
        "api_style": "openai",
        "host": "https://api.perplexity.ai",
        "chat_model": "sonar-pro",
        "embed_model": "",
    },
    "github-models": {
        "api_style": "openai",
        "host": "https://models.inference.ai.azure.com",
        "chat_model": "gpt-4o",
        "embed_model": "",
    },
    "custom": {
        "api_style": "openai",
        "host": "",
        "chat_model": "",
        "embed_model": "",
    },
}


def get_preset(name: str) -> dict[str, str]:
    """Return a copy of the preset, or the custom template if unknown."""
    return dict(PROVIDER_PRESETS.get(name, PROVIDER_PRESETS["custom"]))


class LLMClient:
    """Single generic LLM client that works with any provider.

    Configure via constructor or ``configure()``. The ``api_style`` field
    switches between the three API shapes:
      - ``"openai"``   → OpenAI-compatible (covers DeepSeek, Together, etc.)
      - ``"anthropic"`` → Anthropic Claude
      - ``"ollama"``   → Ollama local/cloud
    """

    def __init__(
        self,
        api_style: str = "ollama",
        host: str = "",
        api_key: str = "",
        chat_model: str = "",
        embed_model: str = "",
    ):
        self.api_style = api_style
        self.host = host.rstrip("/") if host else ""
        self.api_key = api_key
        self.chat_model = chat_model
        self.embed_model = embed_model
        self._client: httpx.Client | None = None
        # Separate embedding provider (different host from chat)
        self._embed_style: str = ""
        self._embed_host: str = ""
        self._embed_key: str = ""
        self._embed_client: httpx.Client | None = None

    # ── Factory helpers ─────────────────────────────────────────

    @classmethod
    def from_preset(cls, name: str, api_key: str = "", **overrides) -> "LLMClient":
        """Create a client from a named preset, with optional overrides.

        Example:
            client = LLMClient.from_preset("openai", api_key="sk-...")
            client = LLMClient.from_preset("deepseek", api_key="sk-...",
                                           chat_model="deepseek-coder")
        """
        preset = get_preset(name)
        preset.update(overrides)
        if api_key:
            preset["api_key"] = api_key
        return cls(
            api_style=preset.get("api_style", "openai"),
            host=preset.get("host", ""),
            api_key=preset.get("api_key", ""),
            chat_model=preset.get("chat_model", ""),
            embed_model=preset.get("embed_model", ""),
        )

    # ── Runtime configuration ───────────────────────────────────

    def configure(
        self,
        api_style: str | None = None,
        host: str | None = None,
        api_key: str | None = None,
        chat_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        """Update connection parameters at runtime. Resets the HTTP client."""
        if api_style is not None:
            self.api_style = api_style
        if host is not None:
            self.host = host.rstrip("/")
        if api_key is not None:
            self.api_key = api_key
        if chat_model is not None:
            self.chat_model = chat_model
        if embed_model is not None:
            self.embed_model = embed_model
        self._reset_client()
        logger.info(
            f"LLMClient reconfigured: style={self.api_style}, "
            f"host={self.host}, chat={self.chat_model}, embed={self.embed_model}"
        )

    def configure_embed(
        self,
        api_style: str,
        host: str,
        api_key: str = "",
        embed_model: str = "",
    ) -> None:
        """Configure a separate embedding provider (different host from chat)."""
        self._embed_style = api_style
        self._embed_host = host.rstrip("/")
        self._embed_key = api_key
        self.embed_model = embed_model
        self._embed_client = None  # reset client
        logger.info(f"Embed provider configured: style={api_style}, host={host}, model={embed_model}")

    def load_preset(self, name: str, api_key: str = "") -> None:
        """Load a preset configuration at runtime."""
        preset = get_preset(name)
        self.configure(
            api_style=preset.get("api_style"),
            host=preset.get("host"),
            chat_model=preset.get("chat_model"),
            embed_model=preset.get("embed_model"),
        )
        if api_key:
            self.api_key = api_key

    # ── HTTP client management ──────────────────────────────────

    def _reset_client(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _get_client(self, base_path: str = "") -> httpx.Client:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                if self.api_style == "anthropic":
                    headers["x-api-key"] = self.api_key
                    headers["anthropic-version"] = "2023-06-01"
                else:
                    headers["Authorization"] = f"Bearer {self.api_key}"
            base_url = f"{self.host}/{base_path}".rstrip("/") + "/"
            self._client = httpx.Client(
                base_url=base_url,
                headers=headers,
                timeout=120,
            )
        return self._client

    @property
    def client(self) -> httpx.Client:
        return self._get_client()

    # ── Connection testing ──────────────────────────────────────

    def test_connection(self) -> dict[str, Any]:
        """Test connectivity to the configured provider endpoint.

        Returns:
            Dict with ``ok`` (bool), ``provider``, ``host``, and optional ``message``.
        """
        try:
            if self.api_style == "ollama":
                resp = self._get_client("api").get("/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    return {
                        "ok": True,
                        "provider": "ollama",
                        "host": self.host,
                        "model": self.chat_model,
                        "models_available": len(models),
                    }
                else:
                    return {
                        "ok": False,
                        "provider": "ollama",
                        "host": self.host,
                        "message": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    }

            elif self.api_style == "anthropic":
                # Lightweight test: list models
                resp = self._get_client("v1").get("/models")
                if resp.status_code == 200:
                    return {
                        "ok": True,
                        "provider": "anthropic",
                        "host": self.host,
                        "model": self.chat_model,
                    }
                else:
                    return {
                        "ok": False,
                        "provider": "anthropic",
                        "host": self.host,
                        "message": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    }

            else:  # openai-compatible
                resp = self._get_client("v1").get("/models")
                if resp.status_code == 200:
                    return {
                        "ok": True,
                        "provider": "openai-compatible",
                        "host": self.host,
                        "model": self.chat_model,
                    }
                else:
                    return {
                        "ok": False,
                        "provider": "openai-compatible",
                        "host": self.host,
                        "message": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    }

        except Exception as e:
            return {
                "ok": False,
                "host": self.host,
                "message": str(e),
            }

    # ── Chat ────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        stream: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request. Returns the full response text."""
        if self.api_style == "anthropic":
            return self._chat_anthropic(messages, temperature, max_tokens)
        elif self.api_style == "ollama":
            return self._chat_ollama(messages, temperature, stream, max_tokens)
        else:
            return self._chat_openai(messages, temperature, stream, max_tokens)

    def _chat_openai(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        stream: bool,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        resp = self._get_client("v1").post("/chat/completions", json=payload)
        resp.raise_for_status()

        if stream:
            full_response = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            full_response += delta["content"]
                    except json.JSONDecodeError:
                        continue
            return full_response
        else:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _chat_anthropic(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        # Anthropic uses "system" as a top-level field, not in messages
        system_msg = ""
        filtered_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                filtered_messages.append(m)

        payload = {
            "model": self.chat_model,
            "messages": filtered_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            payload["system"] = system_msg

        resp = self._get_client("v1").post("/messages", json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Extract text from content blocks
        content = data.get("content", [])
        if isinstance(content, list):
            return "".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            )
        return str(content)

    def _chat_ollama(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        stream: bool,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        resp = self._get_client("api").post("/chat", json=payload)
        resp.raise_for_status()

        if stream:
            full_response = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    if "message" in chunk and "content" in chunk["message"]:
                        full_response += chunk["message"]["content"]
                except json.JSONDecodeError:
                    continue
            return full_response
        else:
            data = resp.json()
            return data.get("message", {}).get("content", "")

    # ── Chat JSON (structured output) ───────────────────────────

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Chat with the model and parse the response as JSON.

        For structured agent outputs (mapping proposals, reviews, etc.).
        """
        json_instruction = (
            "\n\nIMPORTANT: Your response MUST be valid JSON. "
            "Do not include any text outside the JSON object. "
            "Do not wrap it in markdown code blocks. Output raw JSON only."
        )
        messages = [
            {"role": "system", "content": system_prompt + json_instruction},
            {"role": "user", "content": user_prompt},
        ]

        raw = self.chat(messages, temperature=temperature).strip()

        # Handle markdown code fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```") and not l.startswith("```json")]
            raw = "\n".join(lines)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Attempt to find JSON object within the response
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start: end + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse chat response as JSON. Raw: {raw[:300]}...")
            raise ValueError(f"Model did not return valid JSON: {raw[:200]}")

    # ── Embeddings ──────────────────────────────────────────────

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.
        Uses separate embed provider if configured, otherwise falls back to chat provider.
        """
        # Use separate embed provider if configured
        if self._embed_host:
            return self._embed_with(texts, self._embed_style, self._embed_host,
                                    self._embed_key, self.embed_model)
        # Fall back to chat provider
        if self.api_style == "anthropic":
            raise NotImplementedError(
                "Anthropic does not support embeddings. "
                "Use a separate provider (e.g., Ollama or OpenAI) for embedding."
            )
        elif self.api_style == "ollama":
            return self._embed_ollama(texts)
        else:
            return self._embed_openai(texts)

    def _embed_with(self, texts: list[str], style: str, host: str,
                    api_key: str, model: str) -> list[list[float]]:
        """Generate embeddings using a specific provider."""
        if not model:
            raise NotImplementedError("No embedding model configured")
        if style == "ollama":
            return self._embed_ollama_at(texts, host)
        else:
            return self._embed_openai_at(texts, host, api_key, model)

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        if not self.embed_model:
            raise NotImplementedError("No embedding model configured")
        return self._embed_openai_at(texts, self.host, self.api_key, self.embed_model)

    def _embed_openai_at(self, texts: list[str], host: str, api_key: str, model: str) -> list[list[float]]:
        if not model:
            raise NotImplementedError("No embedding model configured")
        embeddings = []
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        base = host.rstrip("/") + "/"
        for text in texts:
            payload = {"model": model, "input": text}
            client = httpx.Client(timeout=30.0)
            resp = client.post(base + "embeddings", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            emb_data = data.get("data", [])
            if emb_data:
                embeddings.append(emb_data[0].get("embedding", []))
            client.close()
        return embeddings

    def _embed_ollama_at(self, texts: list[str], host: str) -> list[list[float]]:
        embeddings = []
        for text in texts:
            payload = {"model": self.embed_model, "input": text[:4000]}
            client = httpx.Client(timeout=30.0)
            resp = client.post(host.rstrip("/") + "/api/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "embeddings" in data and len(data["embeddings"]) > 0:
                embeddings.append(data["embeddings"][0])
            client.close()
        return embeddings

    def test_embed_connection(self) -> dict[str, Any]:
        """Test connectivity to the separate embedding provider."""
        if not self._embed_host:
            return {"ok": False, "message": "No separate embed provider configured"}
        try:
            if self._embed_style == "ollama":
                client = httpx.Client(timeout=5.0)
                resp = client.get(self._embed_host.rstrip("/") + "/api/tags")
                client.close()
                if resp.status_code == 200:
                    return {"ok": True, "provider": "ollama", "host": self._embed_host}
                return {"ok": False, "message": f"HTTP {resp.status_code}"}
            else:
                # OpenAI-compatible: just check the host is reachable
                client = httpx.Client(timeout=5.0)
                resp = client.get(self._embed_host.rstrip("/") + "/models")
                client.close()
                return {"ok": resp.status_code < 500, "host": self._embed_host}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            payload = {
                "model": self.embed_model,
                "input": text,
            }
            resp = self._get_client("api").post("/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "embeddings" in data and len(data["embeddings"]) > 0:
                embeddings.append(data["embeddings"][0])
        return embeddings

    # ── Utility ─────────────────────────────────────────────────

    def get_config(self) -> dict[str, Any]:
        """Return the current configuration (safe version, no API key)."""
        return {
            "api_style": self.api_style,
            "provider": self._detect_provider_name(),
            "host": self.host,
            "chat_model": self.chat_model,
            "embed_model": self.embed_model,
            "has_api_key": bool(self.api_key),
        }

    def _detect_provider_name(self) -> str:
        """Map current config to a known provider name."""
        for name, preset in PROVIDER_PRESETS.items():
            if preset.get("host", "").rstrip("/") == self.host.rstrip("/"):
                return name
        return self.api_style

    def close(self) -> None:
        self._reset_client()

    def __del__(self):
        self.close()


# ── Singleton ────────────────────────────────────────────────────
# Single global instance, reconfigured at runtime via configure() or
# from_preset(). Defaults to Ollama until the user changes it.
llm_client = LLMClient.from_preset("ollama")
