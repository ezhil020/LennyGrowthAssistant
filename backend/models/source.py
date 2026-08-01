"""
models/source.py — Structured source attribution model.

SourceChunk represents a single retrieved transcript chunk.
SourceAttribution is the full attribution payload stored in messages.sources_json
and returned to the frontend for the Sources panel.
"""

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    """A single retrieved transcript chunk with full provenance metadata."""

    chunk_id: str = Field(description="UUID of the TranscriptChunk row")
    episode_title: str = Field(description="Name of the podcast episode")
    chunk_index: int = Field(description="Position of this chunk within the episode")
    similarity_score: float = Field(
        description="Relevance score (0.0–1.0); from cosine similarity or RRF"
    )
    source_url: str = Field(description="GitHub raw URL to the original transcript")
    chunk_text: str = Field(description="The actual text of the chunk")


class SourceAttribution(BaseModel):
    """Full attribution payload attached to a grounded assistant message."""

    chunks: list[SourceChunk]
    retrieval_mode: str = Field(
        description="Retrieval strategy used: 'vector', 'lexical', or 'hybrid'"
    )
