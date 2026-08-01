"""repositories/dependencies.py — FastAPI Depends for all repositories."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.repositories.session_repo import SessionRepository
from backend.repositories.message_repo import MessageRepository
from backend.repositories.artifact_repo import ArtifactRepository
from backend.repositories.chunk_repo import ChunkRepository


async def get_session_repo(db: AsyncSession = Depends(get_db)) -> SessionRepository:
    return SessionRepository(db)


async def get_message_repo(db: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)


async def get_artifact_repo(db: AsyncSession = Depends(get_db)) -> ArtifactRepository:
    return ArtifactRepository(db)


async def get_chunk_repo(db: AsyncSession = Depends(get_db)) -> ChunkRepository:
    return ChunkRepository(db)
