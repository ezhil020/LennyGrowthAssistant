"""
retrieval/hybrid_retriever.py — Reciprocal Rank Fusion over Vector + Lexical results.

RRF merges two ranked lists into a single unified ranking without needing
score normalization. Best recall for mixed queries (semantic + keyword).

RRF formula: score(d) = Σ 1 / (k + rank(d))   where k=60 (standard constant)
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.source import SourceChunk
from backend.retrieval.base import Retriever
from backend.retrieval.vector_retriever import VectorRetriever
from backend.retrieval.lexical_retriever import LexicalRetriever

logger = structlog.get_logger(__name__)

RRF_K = 60  # Standard constant; dampens the impact of high rankings


class HybridRetriever(Retriever):
    """Combines VectorRetriever + LexicalRetriever via Reciprocal Rank Fusion.

    Returns the top-k chunks by fused RRF score.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._vector = VectorRetriever(db)
        self._lexical = LexicalRetriever(db)

    async def retrieve(self, query: str, top_k: int = 10) -> list[SourceChunk]:
        logger.info(
            "retrieval_query",
            module="hybrid_retriever",
            query=query,
            top_k=top_k,
        )

        # Fetch from both retrievers sequentially
        vector_results = await self._vector.retrieve(query, top_k=top_k * 2)
        lexical_results = await self._lexical.retrieve(query, top_k=top_k * 2)

        logger.info(
            "retrieval_raw_counts",
            module="hybrid_retriever",
            vector_results=len(vector_results),
            lexical_results=len(lexical_results),
            top_vector=[
                f"{c.episode_title[:50]} (score={c.similarity_score:.3f})"
                for c in vector_results[:3]
            ],
            top_lexical=[
                f"{c.episode_title[:50]}" for c in lexical_results[:3]
            ],
        )

        # Build RRF scores
        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, SourceChunk] = {}

        for rank, chunk in enumerate(vector_results):
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0) + 1 / (RRF_K + rank + 1)
            chunk_map[chunk.chunk_id] = chunk

        for rank, chunk in enumerate(lexical_results):
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0) + 1 / (RRF_K + rank + 1)
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk

        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)
        top_ids = sorted_ids[:top_k]

        max_score = rrf_scores[top_ids[0]] if top_ids else 1.0
        results = []
        for chunk_id in top_ids:
            chunk = chunk_map[chunk_id]
            normalised = round(rrf_scores[chunk_id] / max_score, 3)
            results.append(
                SourceChunk(
                    chunk_id=chunk.chunk_id,
                    episode_title=chunk.episode_title,
                    chunk_index=chunk.chunk_index,
                    similarity_score=normalised,
                    source_url=chunk.source_url,
                    chunk_text=chunk.chunk_text,
                )
            )

        logger.info(
            "retrieval_fused_results",
            module="hybrid_retriever",
            query=query,
            fused_count=len(results),
            top_chunks=[
                {
                    "episode": r.episode_title[:60],
                    "chunk_index": r.chunk_index,
                    "rrf_score": r.similarity_score,
                    "text_preview": r.chunk_text[:100].replace("\n", " "),
                }
                for r in results[:5]
            ],
        )
        return results
