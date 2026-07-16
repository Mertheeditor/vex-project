from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.common import ChatRequest
from app.services import scheduler_service, self_knowledge_service
from app.services.brain_service import ask, system_status

router = APIRouter()


class SelfReadRequest(BaseModel):
    path: str = ""
    subdir: str = ""


@router.post("/brain/ask")
async def brain_ask(request: ChatRequest):
    """JARVIS tarzı tek giriş: doğal dil -> çok adımlı akıl yürütme."""
    return await ask(request.message, request.history)


@router.get("/brain/status")
async def brain_status():
    """Vex kendi halini doğal dille özetler."""
    return system_status()


@router.get("/brain/self/overview")
def brain_self_overview():
    return self_knowledge_service.project_overview()


@router.post("/brain/self/read")
def brain_self_read(request: SelfReadRequest):
    if request.path:
        return self_knowledge_service.read_file(request.path)
    return self_knowledge_service.list_files(request.subdir)


@router.get("/brain/notifications")
def brain_notifications():
    return scheduler_service.pending_notifications()


@router.post("/brain/notifications/seen")
def brain_notifications_seen():
    return scheduler_service.mark_notifications_seen()


@router.get("/scheduler/status")
def scheduler_status():
    return scheduler_service.status()
