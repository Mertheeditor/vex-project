from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from app.services import evolution_service

router = APIRouter()

class EvolutionPromptRequest(BaseModel):
    prompt: str = ""
    message: str = ""

@router.get("/evolution/logs")
def evolution_logs():
    return evolution_service.get_logs()

@router.get("/evolution/status")
def evolution_status():
    return evolution_service.status()

@router.get("/evolution/pending-actions")
def evolution_pending_actions():
    return evolution_service.pending_actions()

@router.post("/evolution/reset-logs")
def evolution_reset_logs():
    return evolution_service.reset_logs()

@router.post("/evolution/prompt")
def evolution_prompt(request: EvolutionPromptRequest):
    return evolution_service.start_prompt(request.prompt or request.message)

@router.post("/evolution/approve-action/{action_id}")
def evolution_approve(action_id: str):
    return evolution_service.approve(action_id)

@router.post("/evolution/reject-action/{action_id}")
def evolution_reject(action_id: str):
    return evolution_service.reject(action_id)
