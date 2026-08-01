import asyncio
from sqlalchemy import select, func
from backend.database import AsyncSessionLocal
from backend.models.orm import TranscriptChunk

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(func.count(TranscriptChunk.id)))
        count = res.scalar()
        print(f"Total chunks in DB: {count}")

asyncio.run(check())
