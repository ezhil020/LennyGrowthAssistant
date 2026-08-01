"""
providers/factory.py — LLM provider factory function.

Adding a new provider:
  1. Create a new class in providers/ implementing LLMProvider
  2. Add one new case to get_provider()
  No other files need to change.
"""

import structlog

from backend.config import settings
from backend.providers.base import LLMProvider

logger = structlog.get_logger(__name__)


def get_provider(name: str | None = None) -> LLMProvider:
    """Construct and return the LLM provider for the given name.

    Args:
        name: Provider name ('anthropic' or 'ollama').
              Defaults to settings.active_llm_provider if None.

    Returns:
        An LLMProvider instance ready for use.

    Raises:
        ValueError: If the provider name is unknown.
        RuntimeError: If the provider cannot be constructed (e.g. missing key).
    """
    provider_name = (name or settings.active_llm_provider).lower().strip()
    logger.info("provider_factory_called", provider=provider_name)

    match provider_name:
        case "anthropic":
            from backend.providers.anthropic_provider import AnthropicProvider
            return AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
            )
        case "ollama":
            from backend.providers.ollama_provider import OllamaProvider
            return OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
            )
        case _:
            raise ValueError(
                f"Unknown LLM provider: '{provider_name}'. "
                f"Supported providers: 'anthropic', 'ollama'."
            )
