from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import AI_PROVIDER_MODE
from app.schemas.ai_provider import ProviderHealth, ProviderSettings
from app.services.ai_provider_router import get_provider_health, initialize_router, get_router

router = APIRouter(prefix="/ai", tags=["AI Providers"])


class ProviderSettingsUpdate(BaseModel):
    mode: str | None = None
    manual_provider: str | None = None
    fallback_order: list[str] | None = None


async def get_initialized_router():
    return await initialize_router()


@router.get("/providers/status", response_model=dict[str, ProviderHealth])
async def get_providers_status():
    """Get health status of all configured AI providers."""
    return await get_provider_health()


@router.get("/provider/settings", response_model=ProviderSettings)
async def get_provider_settings():
    """Get current AI provider settings."""
    router = await initialize_router()
    return ProviderSettings(
        mode=AI_PROVIDER_MODE,
        manual_provider=router._config.manual_provider,
        fallback_order=router._config.fallback_order,
        available_providers=list(router._providers.keys()),
    )


@router.patch("/provider/settings", response_model=ProviderSettings)
async def update_provider_settings(update: ProviderSettingsUpdate, router=Depends(get_initialized_router)):
    """Update AI provider settings."""
    if update.mode is not None:
        if update.mode not in ("auto", "manual"):
            raise HTTPException(400, "Mode must be 'auto' or 'manual'")
        router.configure(mode=update.mode)

    if update.manual_provider is not None:
        if update.manual_provider and update.manual_provider not in router._providers:
            raise HTTPException(400, f"Unknown provider: {update.manual_provider}")
        router.configure(manual_provider=update.manual_provider)

    if update.fallback_order is not None:
        for p in update.fallback_order:
            if p not in router._providers:
                raise HTTPException(400, f"Unknown provider in fallback_order: {p}")
        router.configure(fallback_order=update.fallback_order)

    return ProviderSettings(
        mode=router._config.mode.value,
        manual_provider=router._config.manual_provider,
        fallback_order=router._config.fallback_order,
        available_providers=list(router._providers.keys()),
    )