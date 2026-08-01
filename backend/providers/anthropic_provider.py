"""
providers/anthropic_provider.py — Anthropic Claude SDK implementation.

Uses the official `anthropic` Python package (NOT a raw HTTP wrapper).
"""

from collections.abc import AsyncIterator

import anthropic
import structlog

from backend.providers.base import LLMProvider

logger = structlog.get_logger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        logger.info("anthropic_provider_init", model=model)

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt or anthropic.NOT_GIVEN,
            messages=messages,
        )
        return response.content[0].text

    async def generate_stream(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt or anthropic.NOT_GIVEN,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model=self._model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as e:
            logger.warning("anthropic_health_check_failed", error=str(e))
            return False
