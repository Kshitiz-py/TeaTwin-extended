"""
Ollama Cloud API Client — wraps ollama Python SDK for chat and embeddings.
Uses qwen3.5:397b-cloud for reasoning, nomic-embed-text for embeddings.
"""

import os
import json
import logging
from typing import Any, Generator

import httpx

from .config import (
    OLLAMA_HOST,
    OLLAMA_API_KEY,
    OLLAMA_CHAT_MODEL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_TIMEOUT,
)

logger = logging.getLogger("ai-agent.ollama")


class OllamaClient:
    """Wrapper around Ollama's REST API for chat and embedding operations."""

    def __init__(self):
        self.host = OLLAMA_HOST.rstrip("/")
        self.api_key = OLLAMA_API_KEY
        self.chat_model = OLLAMA_CHAT_MODEL
        self.embed_model = OLLAMA_EMBED_MODEL
        self.timeout = OLLAMA_TIMEOUT
        self._client: httpx.Client | None = None

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

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        stream: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send a chat completion request.
        Returns the full response text.
        """
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

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        Returns a list of embedding vectors.
        """
        embeddings = []
        for text in texts:
            payload = {
                "model": self.embed_model,
                "input": text,
            }
            resp = self.client.post("/embed", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "embeddings" in data and len(data["embeddings"]) > 0:
                embeddings.append(data["embeddings"][0])
        return embeddings

    def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        """Convenience method: system + user message, returns full response."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages, temperature=temperature)

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """
        Chat with the model and attempt to parse the response as JSON.
        For structured agent outputs (Writer, Reviewer).
        """
        # Add JSON instruction to system prompt
        json_system = (
            system_prompt
            + "\n\nIMPORTANT: Your response MUST be valid JSON. Do not include any text outside the JSON object. "
            "Do not wrap it in markdown code blocks. Output raw JSON only."
        )
        raw = self.chat_structured(json_system, user_prompt, temperature=temperature)

        # Try to extract JSON from the response (handle markdown code blocks gracefully)
        raw = raw.strip()
        if raw.startswith("```"):
            # Remove markdown code fences
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Attempt to find JSON object within the response
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse chat response as JSON. Raw: {raw[:300]}...")
            raise ValueError(f"Model did not return valid JSON: {raw[:200]}")

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


# Singleton for easy import
ollama_client = OllamaClient()