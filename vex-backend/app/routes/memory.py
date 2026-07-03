from __future__ import annotations

from fastapi import APIRouter
from app.schemas.common import MessageRequest
from app.storage.memory_store import add_rule_from_message, load_memory

router = APIRouter()

@router.get("/memory")
def get_memory():
    return load_memory()

@router.post("/memory/rules/from-chat")
def memory_from_chat(request: MessageRequest):
    return add_rule_from_message(request.message)
