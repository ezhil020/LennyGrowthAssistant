"""
ingestion/ingest.py — Async transcript ingestion pipeline.

Steps:
  1. Fetch transcript filenames from GitHub API
  2. Download each transcript file
  3. Chunk text (512 tokens, 50-token overlap)
  4. Embed each chunk via the configured embedding model
  5. Upsert into transcript_chunks table

Run standalone:
  python -m backend.ingestion.ingest

Or trigger via POST /api/v1/ingest (FastAPI BackgroundTasks).

Upgrade path: replace asyncio.gather with Celery/RQ for distributed ingestion.
"""

import asyncio
import re
import uuid
from urllib.parse import urljoin

import aiohttp
import structlog

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.repositories.chunk_repo import ChunkRepository
from backend.retrieval.embeddings import embed_text

logger = structlog.get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"
CHUNK_SIZE = 512      # tokens (approximate)
CHUNK_OVERLAP = 50    # tokens


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by approximate word count (token proxy)."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap  # slide with overlap

    return chunks


def _extract_episode_title(filename: str, content: str) -> str:
    """Extract episode title from filename or first non-empty line of content."""
    # Try to get from first line
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and len(line) > 5:
            return line[:200]
    # Fallback: clean filename
    name = filename.replace(".txt", "").replace(".md", "").replace("-", " ").replace("_", " ")
    return name.strip()[:200]


async def _get_transcript_file_urls(session: aiohttp.ClientSession, limit: int) -> list[tuple[str, str]]:
    """Fetch list of transcript files from the GitHub repo.

    Returns:
        List of (filename, raw_url) tuples.
    """
    # Parse repo owner/name from URL
    repo_url = settings.transcript_repo_url
    # e.g. https://github.com/ChatPRD/lennys-podcast-transcripts
    parts = repo_url.rstrip("/").split("/")
    owner, repo = parts[-2], parts[-1]

    api_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/"
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "LennyGrowthAssistant/1.0"}

    async with session.get(api_url, headers=headers) as response:
        if response.status != 200:
            logger.error("github_api_error", status=response.status)
            return []
        items = await response.json()

    files = []
    for item in items:
        if item.get("type") == "file" and item.get("name", "").endswith((".txt", ".md")):
            files.append((item["name"], item["download_url"]))

    if limit > 0:
        files = files[:limit]

    logger.info("transcript_files_found", count=len(files))
    return files


async def _ingest_file(
    session: aiohttp.ClientSession,
    filename: str,
    raw_url: str,
    chunk_repo: ChunkRepository,
) -> int:
    """Download, chunk, embed, and store a single transcript file.

    Returns:
        Number of chunks ingested.
    """
    try:
        async with session.get(raw_url) as response:
            if response.status != 200:
                logger.warning("transcript_download_failed", filename=filename, status=response.status)
                return 0
            content = await response.text()
    except Exception as e:
        logger.warning("transcript_download_error", filename=filename, error=str(e))
        return 0

    episode_title = _extract_episode_title(filename, content)
    chunks = _chunk_text(content)
    ingested = 0

    for i, chunk_text in enumerate(chunks):
        if not chunk_text.strip():
            continue
        try:
            embedding = await embed_text(chunk_text)
            await chunk_repo.upsert_chunk(
                episode_title=episode_title,
                chunk_index=i,
                chunk_text=chunk_text,
                embedding=embedding,
                source_url=raw_url,
            )
            ingested += 1
        except Exception as e:
            logger.warning(
                "chunk_embed_error",
                episode=episode_title,
                chunk_index=i,
                error=str(e),
            )

    logger.info("file_ingested", filename=filename, chunks=ingested)
    return ingested


async def run_ingestion(limit: int | None = None) -> dict:
    """Main ingestion entry point — called by BackgroundTasks or CLI.

    Args:
        limit: Max files to ingest. Defaults to settings.ingest_limit.

    Returns:
        {"files_processed": int, "chunks_ingested": int}
    """
    effective_limit = limit if limit is not None else settings.ingest_limit
    logger.info("ingestion_started", limit=effective_limit)

    total_files = 0
    total_chunks = 0

    async with aiohttp.ClientSession() as http_session:
        file_list = await _get_transcript_file_urls(http_session, effective_limit)

        async with AsyncSessionLocal() as db_session:
            chunk_repo = ChunkRepository(db_session)

            # Process files sequentially to avoid overwhelming the embedding model
            for filename, raw_url in file_list:
                chunks_added = await _ingest_file(
                    http_session, filename, raw_url, chunk_repo
                )
                total_files += 1
                total_chunks += chunks_added
                await db_session.commit()  # Commit after each file

    logger.info(
        "ingestion_complete",
        files_processed=total_files,
        chunks_ingested=total_chunks,
    )
    return {"files_processed": total_files, "chunks_ingested": total_chunks}


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    result = asyncio.run(run_ingestion(limit))
    print(f"Ingestion complete: {result}")
