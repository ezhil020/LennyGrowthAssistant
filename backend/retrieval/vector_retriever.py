"""retrieval/vector_retriever.py — pgvector cosine similarity retriever."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.source import SourceChunk
from backend.repositories.chunk_repo import ChunkRepository
from backend.retrieval.base import Retriever
from backend.retrieval.embeddings import embed_text

logger = structlog.get_logger(__name__)


class VectorRetriever(Retriever):
    """Retrieves chunks using pgvector cosine similarity search."""

    def __init__(self, db: AsyncSession) -> None:
        self._repo = ChunkRepository(db)

    async def retrieve(self, query: str, top_k: int = 10) -> list[SourceChunk]:
        query_embedding = await embed_text(query)
        chunks = await self._repo.vector_search(query_embedding, top_k=top_k * 2)

        # Score = 1 - cosine_distance (approximate; pgvector returns by distance)
        results = []
        for i, chunk in enumerate(chunks[:top_k]):
            score = max(0.0, 1.0 - (i / max(len(chunks), 1)))  # rank-based approximation
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

        logger.info("vector_retrieval", query_len=len(query), results=len(results))
        return results
