from __future__ import annotations

from fastapi import APIRouter
from app.core.paths import APPROVALS_PATH
from app.schemas.common import ApprovalRequest, MessageRequest
from app.storage.entity_store import delete_item, list_items, patch_item, upsert_item

router = APIRouter()

@router.get("/approvals")
def get_approvals():
    return list_items(APPROVALS_PATH)

@router.post("/approvals/from-chat")
def create_approval_from_chat(request: MessageRequest):
    approval = upsert_item(APPROVALS_PATH, {"title": request.message.strip()[:80] or "Onay İsteği", "action_type": "genel", "risk_level": "normal", "status": "bekliyor", "description": request.message, "payload": {}, "notes": ["Sohbetten oluşturuldu."]}, "onay")
    return {"success": True, "message": "Onay isteği oluşturuldu.", "approval": approval, "approvals": list_items(APPROVALS_PATH), "source_message": request.message}

@router.patch("/approvals/{approval_id}/approve")
def approve_approval(approval_id: str):
    approval = patch_item(APPROVALS_PATH, approval_id, {"status": "onaylandı"})
    return {"success": approval is not None, "message": "Onaylandı.", "approval": approval}

@router.patch("/approvals/{approval_id}/reject")
def reject_approval(approval_id: str):
    approval = patch_item(APPROVALS_PATH, approval_id, {"status": "reddedildi"})
    return {"success": approval is not None, "message": "Reddedildi.", "approval": approval}

@router.delete("/approvals/{approval_id}")
def delete_approval(approval_id: str):
    return {"success": delete_item(APPROVALS_PATH, approval_id), "message": "Onay isteği silindi."}
