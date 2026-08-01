"""
services/provider_service.py — Provider configuration and health checks.
"""

import asyncio
import structlog

from backend.config import settings
from backend.providers.factory import get_provider
from backend.retrieval.embeddings import check_embedding_health
from backend.database import check_db_health
from backend.repositories.chunk_repo import ChunkRepository

logger = structlog.get_logger(__name__)

# In-memory active provider (can be overridden per-request via API)
_active_provider_name: str = settings.active_llm_provider


def get_active_provider_name() -> str:
    return _active_provider_name


def set_active_provider_name(name: str) -> None:
    global _active_provider_name
    _active_provider_name = name
    logger.info("provider_switched", provider=name)


class ProviderService:
    async def list_providers(self) -> list[dict]:
        active = get_active_provider_name()
        providers = []
        for name in ("anthropic", "ollama"):
            try:
                p = get_provider(name)
                providers.append({
                    "name": name,
                    "model": p.model,
                    "is_active": name == active,
                })
            except Exception:
                providers.append({
                    "name": name,
                    "model": "unavailable",
                    "is_active": name == active,
                })
        return providers

    async def set_provider(self, name: str) -> None:
        # Validate
        get_provider(name)  # Raises ValueError if unknown
        set_active_provider_name(name)

    async def health_check(self, chunk_repo: ChunkRepository | None = None) -> dict:
        """Run all health checks with a 5-second timeout each."""
        results = {}

        # Database
        try:
            ok = await asyncio.wait_for(check_db_health(), timeout=5.0)
            results["database"] = "ok" if ok else "error"
        except asyncio.TimeoutError:
            results["database"] = "timeout"

        # LLM provider
        try:
            provider = get_provider(get_active_provider_name())
            ok = await asyncio.wait_for(provider.health_check(), timeout=5.0)
            results["llm_provider"] = "ok" if ok else "error"
        except Exception as e:
            results["llm_provider"] = f"error: {str(e)[:50]}"

        # Embedding model
        try:
            ok = await asyncio.wait_for(check_embedding_health(), timeout=5.0)
            results["embedding_model"] = "ok" if ok else "error"
        except asyncio.TimeoutError:
            results["embedding_model"] = "timeout"

        # Vector store (check chunk count)
        try:
            if chunk_repo:
                count = await asyncio.wait_for(chunk_repo.count(), timeout=5.0)
                results["vector_store"] = f"ok ({count} chunks)"
            else:
                results["vector_store"] = "ok"
        except Exception:
            results["vector_store"] = "error"

        overall = "ok" if all(v == "ok" or v.startswith("ok") for v in results.values()) else "degraded"
        return {"status": overall, "checks": results}
