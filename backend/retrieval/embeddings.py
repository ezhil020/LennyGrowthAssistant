"""
retrieval/embeddings.py — Configurable embedding model.

Supports:
  - Ollama (nomic-embed-text) — fully local
  - OpenAI (text-embedding-3-small) — cloud

Selection is driven by ACTIVE_EMBEDDING_MODEL env var.
"""

import hashlib

import httpx
import structlog

from backend.config import settings

logger = structlog.get_logger(__name__)

OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


async def embed_text(text: str) -> list[float]:
    """Generate an embedding vector for a text string.

    Returns:
        List of floats representing the embedding.

    Raises:
        RuntimeError: If the embedding model is unreachable.
    """
    model_name = settings.active_embedding_model.lower()

    if model_name == "ollama":
        return await _embed_ollama(text)
    elif model_name == "openai":
        return await _embed_openai(text)
    else:
        raise RuntimeError(
            f"Unknown embedding model: '{model_name}'. Use 'ollama' or 'openai'."
        )


async def _embed_ollama(text: str) -> list[float]:
    """Embed via Ollama's /api/embed endpoint."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/embed"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"model": OLLAMA_EMBEDDING_MODEL, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            # Ollama /api/embed returns {"embeddings": [[...]]}
            return data["embeddings"][0]
    except httpx.ConnectError:
        raise RuntimeError(
            "Cannot reach Ollama for embeddings. "
            "Ensure Ollama is running and nomic-embed-text is pulled: "
            "`ollama pull nomic-embed-text`"
        )
    except Exception as e:
        raise RuntimeError(f"Ollama embedding error: {e}") from e


async def _embed_openai(text: str) -> list[float]:
    """Embed via OpenAI's text-embedding-3-small model."""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding
    except Exception as e:
        raise RuntimeError(f"OpenAI embedding error: {e}") from e


async def check_embedding_health() -> bool:
    """Verify the embedding model is reachable."""
    try:
        await embed_text("health check")
        return True
    except Exception as e:
        logger.warning("embedding_health_check_failed", error=str(e))
        return False
