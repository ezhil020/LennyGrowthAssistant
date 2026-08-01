"""
repositories/base.py — Generic async CRUD base repository.
"""

from typing import Any, Generic, TypeVar
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id: str) -> ModelT | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> ModelT:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        obj = self.model(**kwargs)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: str) -> bool:
        obj = await self.get(id)
        if obj is None:
            return False
        await self.db.delete(obj)
        await self.db.flush()
        return True
