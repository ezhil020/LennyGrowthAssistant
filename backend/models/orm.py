"""
models/orm.py — SQLAlchemy ORM models.

Tables:
  sessions        — chat sessions with provider + title
  messages        — per-turn messages with routing metadata and sources
  artifacts       — typed (markdown|html) artifacts with versioning
  transcript_chunks — ingested podcast transcript chunks with embeddings
"""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

EMBEDDING_DIM = 768  # nomic-embed-text / text-embedding-3-small output dim


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    llm_provider: Mapped[str] = mapped_column(String(50), default="anthropic")
    embedding_model: Mapped[str] = mapped_column(String(100), default="ollama")

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))          # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    skill_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    routing_intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sources_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="messages")
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("messages.id", ondelete="CASCADE")
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(20))          # "markdown" | "html"
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # Relationships
    message: Mapped["Message"] = relationship(back_populates="artifacts")


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    episode_title: Mapped[str] = mapped_column(String(500))
    chunk_index: Mapped[int] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
    source_url: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (
        UniqueConstraint("episode_title", "chunk_index", name="uq_episode_chunk"),
    )
