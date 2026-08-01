"""
database.py — Async SQLAlchemy engine and session factory.

Usage (FastAPI Depends):
    async def endpoint(db: AsyncSession = Depends(get_db)):
        ...
"""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

logger = structlog.get_logger(__name__)

# Engine — asyncpg driver for Postgres
engine = create_async_engine(
    settings.database_url,
    echo=False,          # set True to see SQL in dev
    pool_pre_ping=True,  # detect stale connections
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Ping the database — used by the health endpoint."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("db_health_check_failed", error=str(e))
        return False
