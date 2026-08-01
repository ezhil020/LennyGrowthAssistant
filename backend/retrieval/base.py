"""
retrieval/base.py — Retriever abstract interface.

Any retrieval backend (pgvector, Pinecone, Weaviate, BM25, etc.)
implements this interface. The RetrievalService selects the correct
implementation from configuration — no other code changes needed.
"""

from abc import ABC, abstractmethod

from backend.models.source import SourceChunk


class Retriever(ABC):
    """Common interface for all retrieval backends."""

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 10) -> list[SourceChunk]:
        """Retrieve the top-k most relevant chunks for a query.

        Args:
            query: Natural language search query.
            top_k: Maximum number of chunks to return.

        Returns:
            List of SourceChunk objects ordered by relevance (highest first).
        """
        ...
