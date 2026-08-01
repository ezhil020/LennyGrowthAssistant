"""api/v1/config_api.py — LLM provider configuration endpoints."""

from fastapi import APIRouter, Depends

from backend.models.schemas import ProvidersResponse, SetProviderRequest
from backend.services.dependencies import get_provider_service
from backend.services.provider_service import ProviderService

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers(svc: ProviderService = Depends(get_provider_service)):
    providers = await svc.list_providers()
    active = next((p["name"] for p in providers if p["is_active"]), "anthropic")
    return ProvidersResponse(
        providers=[
            {"name": p["name"], "is_active": p["is_active"], "model": p["model"]}
            for p in providers
        ],
        active=active,
    )


@router.post("/providers")
async def set_provider(
    body: SetProviderRequest,
    svc: ProviderService = Depends(get_provider_service),
):
    await svc.set_provider(body.provider)
    return {"status": "ok", "active_provider": body.provider}
