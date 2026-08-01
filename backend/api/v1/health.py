"""api/v1/health.py — System health check endpoint."""

from fastapi import APIRouter, Depends

from backend.models.schemas import HealthCheck
from backend.repositories.dependencies import get_chunk_repo
from backend.repositories.chunk_repo import ChunkRepository
from backend.services.dependencies import get_provider_service
from backend.services.provider_service import ProviderService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheck)
async def health_check(
    svc: ProviderService = Depends(get_provider_service),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
):
    result = await svc.health_check(chunk_repo)
    return HealthCheck(status=result["status"], checks=result["checks"])
