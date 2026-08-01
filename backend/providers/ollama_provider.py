"""
providers/ollama_provider.py — Ollama local LLM implementation.

Uses the `ollama` Python client library with async httpx fallback for streaming.
"""

from collections.abc import AsyncIterator

import httpx
import structlog

from backend.providers.base import LLMProvider

logger = structlog.get_logger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url, timeout=httpx.Timeout(120.0)
        )
        logger.info("ollama_provider_init", model=model, base_url=base_url)

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def _build_ollama_messages(
        self, messages: list[dict], system_prompt: str
    ) -> list[dict]:
        """Prepend system prompt as a system message if provided."""
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        result.extend(messages)
        return result

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": self._build_ollama_messages(messages, system_prompt),
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    async def generate_stream(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        import json

        payload = {
            "model": self._model,
            "messages": self._build_ollama_messages(messages, system_prompt),
            "stream": True,
            "options": {"num_predict": max_tokens},
        }
        async with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/api/tags", timeout=5.0)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning("ollama_health_check_failed", error=str(e))
            return False
