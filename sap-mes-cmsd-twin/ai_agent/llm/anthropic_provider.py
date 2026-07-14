"""
Anthropic Provider — wraps Anthropic's Messages API.
Uses /v1/messages for chat.
Does NOT support embeddings (users can configure a separate embedding provider).
"""
import json
import logging
from typing import Any

import httpx

from .base import LLMProvider

logger = logging.getLogger("ai-agent.llm.anthropic")


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude API (chat only — no embeddings)."""

    def __init__(
        self,
        host: str = "https://api.anthropic.com",
        api_key: str = "",
        chat_model: str = "claude-sonnet-4-20250514",
        embed_model: str = "",  # Anthropic doesn't do embeddings
    ):
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.timeout = 120
        self._client: httpx.Client | None = None

    def configure(
        self,
        host: str | None = None,
        api_key: str | None = None,
        chat_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
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
            f"AnthropicProvider configured: host={self.host}, chat={self.chat_model}"
        )

    def _reset_client(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }
            self._client = httpx.Client(
                base_url=self.host,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    def test_connection(self) -> dict[str, Any]:
        """Test by sending a minimal message to Claude."""
        try:
            # Lightweight test: just check if the endpoint is reachable
            resp = self.client.get("/v1/models", headers={"x-api-key": self.api_key})
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("data", [])]
                return {
                    "ok": True,
                    "host": self.host,
                    "models_available": len(models),
                    "models": models[:10],
                    "message": f"Connected to Anthropic at {self.host}",
                }
            else:
                return {
                    "ok": False,
                    "host": self.host,
                    "message": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }
        except Exception as e:
            return {"ok": False, "host": self.host, "message": str(e)}

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        stream: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        # Convert OpenAI-style messages to Anthropic format
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        payload = {
            "model": self.chat_model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        if system_msg:
            payload["system"] = system_msg

        if stream:
            payload["stream"] = True

        resp = self.client.post("/v1/messages", json=payload)
        resp.raise_for_status()

        if stream:
            full_response = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if "text" in delta:
                            full_response += delta["text"]
                except json.JSONDecodeError:
                    continue
            return full_response
        else:
            data = resp.json()
            content_blocks = data.get("content", [])
            return "".join(
                block.get("text", "") for block in content_blocks if block.get("type") == "text"
            )

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        json_system = (
            system_prompt
            + "\n\nIMPORTANT: Your response MUST be valid JSON. Do not include any text outside the JSON object. "
            "Do not wrap it in markdown code blocks. Output raw JSON only."
        )
        messages = [
            {"role": "user", "content": f"{json_system}\n\n{user_prompt}"},
        ]
        raw = self.chat(messages, temperature=temperature)

        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse chat response as JSON. Raw: {raw[:300]}...")
            raise ValueError(f"Model did not return valid JSON: {raw[:200]}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Anthropic does not support embeddings. Configure a separate embedding provider (Ollama or OpenAI)."
        )

    def close(self) -> None:
        self._reset_client()
