"""
providers/base.py — LLMProvider abstract base class.

Both AnthropicProvider and OllamaProvider implement this interface.
Skills and LLMService call only these methods — never SDK-specific types.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMProvider(ABC):
    """Common interface for all LLM backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. 'anthropic', 'ollama')."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Active model identifier."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """Generate a complete response.

        Args:
            messages: List of {"role": str, "content": str} dicts.
            system_prompt: System/instruction prompt.
            max_tokens: Maximum tokens in the response.

        Returns:
            The assistant's response as a plain string.
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream a response token-by-token.

        Yields:
            String fragments as they arrive from the model.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        ...
