"""repositories/chunk_repo.py — TranscriptChunk CRUD and vector upsert."""

import uuid

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.models.orm import TranscriptChunk
from backend.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[TranscriptChunk]):
    model = TranscriptChunk

    async def upsert_chunk(
        self,
        episode_title: str,
        chunk_index: int,
        chunk_text: str,
        embedding: list[float],
        source_url: str,
    ) -> str:
        """Insert or update a chunk by (episode_title, chunk_index)."""
        chunk_id = str(uuid.uuid4())
        stmt = (
            pg_insert(TranscriptChunk)
            .values(
                id=chunk_id,
                episode_title=episode_title,
                chunk_index=chunk_index,
                chunk_text=chunk_text,
                embedding=embedding,
                source_url=source_url,
            )
            .on_conflict_do_update(
                constraint="uq_episode_chunk",
                set_={
                    "chunk_text": chunk_text,
                    "embedding": embedding,
                    "source_url": source_url,
                },
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return chunk_id

    async def vector_search(
        self, query_embedding: list[float], top_k: int = 20
    ) -> list[TranscriptChunk]:
        """Cosine similarity search via pgvector."""
        result = await self.db.execute(
            select(TranscriptChunk)
            .order_by(TranscriptChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def fulltext_search(
        self, query: str, top_k: int = 20
    ) -> list[TranscriptChunk]:
        """Full-text search using Postgres tsvector."""
        result = await self.db.execute(
            select(TranscriptChunk)
            .where(
                text(
                    "to_tsvector('english', chunk_text) @@ plainto_tsquery('english', :q)"
                ).bindparams(q=query)
            )
            .order_by(
                text(
                    "ts_rank(to_tsvector('english', chunk_text), plainto_tsquery('english', :q)) DESC"
                ).bindparams(q=query)
            )
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.db.execute(text("SELECT COUNT(*) FROM transcript_chunks"))
        row = result.one()
        return row[0]
