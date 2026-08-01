"""Initial schema — sessions, messages, artifacts, transcript_chunks with pgvector.

Revision ID: 0001
Revises: 
Create Date: 2026-07-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False, server_default="New Chat"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("llm_provider", sa.String(50), nullable=False, server_default="anthropic"),
        sa.Column("embedding_model", sa.String(100), nullable=False, server_default="ollama"),
    )

    # messages
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("skill_used", sa.String(50), nullable=True),
        sa.Column("routing_intent", sa.String(100), nullable=True),
        sa.Column("sources_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])

    # artifacts
    op.create_table(
        "artifacts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "message_id",
            UUID(as_uuid=False),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_artifacts_session_id", "artifacts", ["session_id"])
    op.create_index("ix_artifacts_message_id", "artifacts", ["message_id"])

    # transcript_chunks
    op.create_table(
        "transcript_chunks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("episode_title", sa.String(500), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("source_url", sa.Text, nullable=False, server_default=""),
        sa.UniqueConstraint("episode_title", "chunk_index", name="uq_episode_chunk"),
    )
    # HNSW index for fast approximate nearest-neighbour search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding "
        "ON transcript_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    # GIN index for full-text search (lexical retrieval)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_fulltext "
        "ON transcript_chunks USING gin (to_tsvector('english', chunk_text))"
    )


def downgrade() -> None:
    op.drop_table("transcript_chunks")
    op.drop_table("artifacts")
    op.drop_table("messages")
    op.drop_table("sessions")
