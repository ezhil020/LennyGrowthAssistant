"""llm_service/dependencies.py — FastAPI Depends for LLMService."""

from fastapi import Depends

from backend.config import settings
from backend.providers.factory import get_provider
from backend.llm_service.llm_service import LLMService


def get_active_provider():
    """Return the currently active LLM provider from config."""
    return get_provider(settings.active_llm_provider)


def get_llm_service(
    provider=Depends(get_active_provider),
) -> LLMService:
    return LLMService(provider=provider)
