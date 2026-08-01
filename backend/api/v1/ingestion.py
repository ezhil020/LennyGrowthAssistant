"""api/v1/ingestion.py — Transcript ingestion trigger endpoint."""

from fastapi import APIRouter, BackgroundTasks

from backend.ingestion.ingest import run_ingestion
from backend.models.schemas import IngestRequest, IngestResponse

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("", response_model=IngestResponse, status_code=202)
async def trigger_ingestion(
    body: IngestRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger async transcript ingestion as a background task.

    Returns immediately with 202 Accepted.
    Upgrade path: replace BackgroundTasks with Celery for distributed ingestion.
    """
    background_tasks.add_task(run_ingestion, limit=body.limit)
    return IngestResponse(
        status="accepted",
        message=f"Ingestion started for up to {body.limit} transcripts. Check server logs for progress.",
    )
