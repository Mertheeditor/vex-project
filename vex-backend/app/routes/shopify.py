from __future__ import annotations

from fastapi import APIRouter
from app.schemas.common import ShopifyContentFromChatRequest
from app.services.shopify_service import create_content_from_chat

router = APIRouter()

@router.post("/shopify/content-from-chat")
def shopify_content_from_chat(request: ShopifyContentFromChatRequest):
    return create_content_from_chat(request.message, request.project_id, request.task_id, request.language)
