"""
retrieval/retrieval_service.py — Selects and runs the correct Retriever from config.
Called by skills (QA, Ship30) — not by ChatService.
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.source import SourceChunk, SourceAttribution
from backend.retrieval.base import Retriever

logger = structlog.get_logger(__name__)


class RetrievalService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._mode = settings.retrieval_mode

    def _get_retriever(self) -> Retriever:
        match self._mode:
            case "vector":
                from backend.retrieval.vector_retriever import VectorRetriever
                return VectorRetriever(self._db)
            case "lexical":
                from backend.retrieval.lexical_retriever import LexicalRetriever
                return LexicalRetriever(self._db)
            case "hybrid" | _:
                from backend.retrieval.hybrid_retriever import HybridRetriever
                return HybridRetriever(self._db)

    async def retrieve(
        self, query: str, top_k: int | None = None
    ) -> SourceAttribution:
        """Run retrieval and return a SourceAttribution with structured chunks."""
        k = top_k or settings.retrieval_top_k
        retriever = self._get_retriever()
        chunks = await retriever.retrieve(query, top_k=k)
        return SourceAttribution(chunks=chunks, retrieval_mode=self._mode)


# ── Dependencies ──────────────────────────────────────────────────────────────
from fastapi import Depends
from backend.database import get_db


async def get_retrieval_service(db: AsyncSession = Depends(get_db)) -> RetrievalService:
    return RetrievalService(db)
