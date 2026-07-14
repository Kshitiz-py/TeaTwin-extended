"""
OpenAI-compatible Provider — supports OpenAI, DeepSeek, Grok, Together AI,
and any provider that implements the OpenAI REST API format.
Uses /v1/chat/completions for chat and /v1/embeddings for embeddings.
"""
import json
import logging
from typing import Any

import httpx

from .base import LLMProvider

logger = logging.getLogger("ai-agent.llm.openai")


# Known OpenAI-compatible endpoints that DON'T support embeddings
NO_EMBED_PROVIDERS = [
    "api.deepseek.com",
    "api.x.ai",
    "api.together.xyz",
]


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs (OpenAI, DeepSeek, Grok, Together, etc.)."""

    def __init__(
        self,
        host: str = "https://api.openai.com",
        api_key: str = "",
        chat_model: str = "gpt-4o",
        embed_model: str = "text-embedding-3-small",
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
            f"OpenAIProvider configured: host={self.host}, chat={self.chat_model}, embed={self.embed_model}"
        )

    def _reset_client(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.Client(
                base_url=self.host,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    def test_connection(self) -> dict[str, Any]:
        """Test by sending a minimal chat completion — validates API key + model access."""
        try:
            payload = {
                "model": self.chat_model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
                "temperature": 0,
            }
            # Use a short timeout so connection test fails fast
            resp = self.client.post("/v1/chat/completions", json=payload, timeout=10)
            if resp.status_code == 200:
                return {
                    "ok": True,
                    "host": self.host,
                    "chat_model": self.chat_model,
                    "message": f"Authenticated — chat model '{self.chat_model}' responding",
                }
            body = resp.text[:300] if resp.text else "(empty)"
            return {
                "ok": False,
                "host": self.host,
                "message": f"HTTP {resp.status_code}: {body}",
            }
        except Exception as e:
            return {"ok": False, "host": self.host, "message": str(e)}

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        stream: bool = False,
        max_tokens: int = 8192,  # was 4096 — truncated structured JSON (recommender covering sets); 8192 = DeepSeek max output
    ) -> str:
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        resp = self.client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()

        if stream:
            full_response = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    chunk_str = line[6:]
                    if chunk_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(chunk_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            full_response += delta["content"]
                    except json.JSONDecodeError:
                        continue
            return full_response
        else:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")

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
            {"role": "system", "content": json_system},
            {"role": "user", "content": user_prompt},
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
        # Check if this provider supports embeddings
        for no_embed in NO_EMBED_PROVIDERS:
            if no_embed in self.host:
                raise NotImplementedError(
                    f"{self.host} does not support embeddings. Use Ollama or OpenAI for embeddings."
                )

        payload = {
            "model": self.embed_model,
            "input": texts,
        }
        resp = self.client.post("/v1/embeddings", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data.get("data", [])]

    def list_models(self) -> list[dict[str, str]]:
        """List available models from OpenAI-compatible /v1/models endpoint."""
        resp = self.client.get("/v1/models")
        resp.raise_for_status()
        data = resp.json()
        return [{"id": m.get("id", ""), "name": m.get("id", "")}
                for m in data.get("data", [])]

    def close(self) -> None:
        self._reset_client()
