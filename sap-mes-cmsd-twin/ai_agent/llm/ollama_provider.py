"""
Ollama Provider — wraps Ollama's REST API (/api/chat, /api/embeddings, /api/tags).
Supports both local Ollama instances (http://localhost:11434) and Ollama Cloud (https://ollama.com).
"""
import json
import logging
from typing import Any

import httpx

from .base import LLMProvider

logger = logging.getLogger("ai-agent.llm.ollama")


class OllamaProvider(LLMProvider):
    """Provider for Ollama (local or cloud). Supports chat + embeddings."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        api_key: str = "",
        chat_model: str = "qwen3.5:397b-cloud",
        embed_model: str = "nomic-embed-text:latest",
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
            f"OllamaProvider configured: host={self.host}, chat={self.chat_model}, embed={self.embed_model}"
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
                base_url=f"{self.host}/api",
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    def test_connection(self) -> dict[str, Any]:
        try:
            resp = self.client.get("/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return {
                    "ok": True,
                    "host": self.host,
                    "models_available": len(models),
                    "models": models[:10],
                    "message": f"Connected to Ollama at {self.host}",
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
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        resp = self.client.post("/chat", json=payload)
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
        raw = self._chat_structured(json_system, user_prompt, temperature=temperature)

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

    def _chat_structured(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.1
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages, temperature=temperature)

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Use /api/embed (newer Ollama endpoint) — /api/embeddings returns
        # empty results for some models like qwen3-embedding.
        payload = {
            "model": self.embed_model,
            "input": texts,
        }
        resp = self.client.post("/embed", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "embeddings" in data:
            return data["embeddings"]
        return []

    def list_models(self) -> list[dict[str, str]]:
        """List available models from Ollama via /api/tags."""
        resp = self.client.get("/tags")
        resp.raise_for_status()
        data = resp.json()
        return [{"id": m.get("name", ""), "name": m.get("name", "")}
                for m in data.get("models", [])]

    def close(self) -> None:
        self._reset_client()
