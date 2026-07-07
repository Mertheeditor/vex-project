from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import ChatRequest
from app.services.brain_service import ask

router = APIRouter()


@router.post("/brain/ask")
def brain_ask(request: ChatRequest):
    """JARVIS tarzı tek giriş: doğal dil -> doğru yeteneğe yönlendir."""
    return ask(request.message, request.history)
