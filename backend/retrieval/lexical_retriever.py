"""retrieval/lexical_retriever.py — Postgres tsvector full-text search retriever."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.source import SourceChunk
from backend.repositories.chunk_repo import ChunkRepository
from backend.retrieval.base import Retriever

logger = structlog.get_logger(__name__)


class LexicalRetriever(Retriever):
    """Retrieves chunks using Postgres full-text (tsvector/BM25) search.

    Best for queries containing specific names, product names, or exact phrases
    that pure embedding search can miss.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._repo = ChunkRepository(db)

    async def retrieve(self, query: str, top_k: int = 10) -> list[SourceChunk]:
        chunks = await self._repo.fulltext_search(query, top_k=top_k)

        results = []
        for i, chunk in enumerate(chunks):
            # Assign descending scores based on rank position
            score = max(0.0, 1.0 - (i / max(len(chunks), 1)) * 0.5)
            results.append(
                SourceChunk(
                    chunk_id=chunk.id,
                    episode_title=chunk.episode_title,
                    chunk_index=chunk.chunk_index,
                    similarity_score=round(score, 3),
                    source_url=chunk.source_url,
                    chunk_text=chunk.chunk_text,
                )
            )

        logger.info("lexical_retrieval", query_len=len(query), results=len(results))
        return results
