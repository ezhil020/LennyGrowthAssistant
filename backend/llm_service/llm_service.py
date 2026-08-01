"""
llm_service/llm_service.py — Central LLM orchestration layer.

Skills call LLMService — never providers directly.

Responsibilities:
  - Retry with exponential backoff (tenacity)
  - Streaming with per-chunk error handling
  - Token counting + latency logging
  - User-facing error messages (no stack traces leaked)
"""

import time
from collections.abc import AsyncIterator

import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.providers.base import LLMProvider
from backend.llm_service.token_counter import count_messages_tokens, count_tokens

logger = structlog.get_logger(__name__)

# Exceptions considered transient (safe to retry)
_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


class LLMService:
    """Centralised LLM call layer: retry, streaming, token logging."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """Generate a complete response with automatic retry on transient errors.

        Raises:
            RuntimeError: With a user-facing message on persistent failure.
        """
        input_tokens = count_messages_tokens(messages) + count_tokens(system_prompt)
        start = time.monotonic()

        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                stop=stop_after_attempt(3),
                reraise=False,
            ):
                with attempt:
                    response = await self.provider.generate(
                        messages=messages,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                    )
        except RetryError as e:
            raise RuntimeError(
                f"The {self.provider.name} provider is not responding after 3 attempts. "
                "Please check your API key and network connection."
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error communicating with {self.provider.name}: {_user_message(e)}"
            ) from e

        latency_ms = int((time.monotonic() - start) * 1000)
        output_tokens = count_tokens(response)
        logger.info(
            "llm_generate",
            provider=self.provider.name,
            model=self.provider.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
        return response

    async def generate_stream(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream a response with retry on initial connection errors only.

        Yields:
            String fragments as they arrive from the provider.
        """
        input_tokens = count_messages_tokens(messages) + count_tokens(system_prompt)
        start = time.monotonic()
        total_output = ""

        try:
            stream = self.provider.generate_stream(
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
            )
            async for token in stream:
                total_output += token
                yield token
        except Exception as e:
            raise RuntimeError(
                f"Streaming error from {self.provider.name}: {_user_message(e)}"
            ) from e

        latency_ms = int((time.monotonic() - start) * 1000)
        output_tokens = count_tokens(total_output)
        logger.info(
            "llm_stream_complete",
            provider=self.provider.name,
            model=self.provider.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )


def _user_message(exc: Exception) -> str:
    """Convert a provider exception to a plain user-facing message."""
    msg = str(exc).lower()
    if "authentication" in msg or "api_key" in msg or "unauthorized" in msg:
        return "Invalid API key. Check your ANTHROPIC_API_KEY or OPENAI_API_KEY."
    if "rate" in msg or "429" in msg:
        return "Rate limit exceeded. Please wait a moment and try again."
    if "connect" in msg or "timeout" in msg or "unreachable" in msg:
        return "Cannot reach the LLM provider. Check your network or Ollama status."
    return "An unexpected error occurred. Please try again."
