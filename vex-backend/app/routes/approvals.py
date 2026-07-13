from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.core.paths import APPROVALS_PATH
from app.schemas.common import ApprovalRequest, MessageRequest
from app.storage.entity_store import delete_item, find_item, list_items, patch_item, upsert_item

router = APIRouter()

VALID_STATUSES = {"bekliyor", "onaylandı", "reddedildi"}

def _normalize_risk(value: str | None) -> str:
    return str(value or "").strip().lower()

@router.get("/approvals")
def get_approvals():
    return list_items(APPROVALS_PATH)

@router.post("/approvals/from-chat")
def create_approval_from_chat(request: MessageRequest):
    approval = upsert_item(APPROVALS_PATH, {"title": request.message.strip()[:80] or "Onay İsteği", "action_type": "genel", "risk_level": "normal", "status": "bekliyor", "description": request.message, "payload": {}, "notes": ["Sohbetten oluşturuldu."]}, "onay")
    return {"success": True, "message": "Onay isteği oluşturuldu.", "approval": approval, "approvals": list_items(APPROVALS_PATH), "source_message": request.message}

@router.patch("/approvals/{approval_id}/approve")
def approve_approval(approval_id: str):
    approval = find_item(APPROVALS_PATH, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    risk = _normalize_risk(approval.get("risk_level"))
    if risk == "black":
        raise HTTPException(status_code=409, detail="Black risk approvals cannot be approved")

    current_status = approval.get("status")
    if current_status not in VALID_STATUSES:
        raise HTTPException(status_code=409, detail=f"Invalid approval status: {current_status}")

    if current_status == "onaylandı":
        return {"success": True, "message": "Zaten onaylanmış.", "approval": approval}

    if current_status == "reddedildi":
        raise HTTPException(status_code=409, detail="Cannot approve a rejected approval")

    if current_status == "bekliyor":
        approval = patch_item(APPROVALS_PATH, approval_id, {"status": "onaylandı"})
        return {"success": True, "message": "Onaylandı.", "approval": approval}

    raise HTTPException(status_code=409, detail=f"Cannot approve from status: {current_status}")

@router.patch("/approvals/{approval_id}/reject")
def reject_approval(approval_id: str):
    approval = find_item(APPROVALS_PATH, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    current_status = approval.get("status")
    if current_status not in VALID_STATUSES:
        raise HTTPException(status_code=409, detail=f"Invalid approval status: {current_status}")

    if current_status == "reddedildi":
        return {"success": True, "message": "Zaten reddedilmiş.", "approval": approval}

    if current_status == "onaylandı":
        raise HTTPException(status_code=409, detail="Cannot reject an approved approval")

    if current_status == "bekliyor":
        approval = patch_item(APPROVALS_PATH, approval_id, {"status": "reddedildi"})
        return {"success": True, "message": "Reddedildi.", "approval": approval}

    raise HTTPException(status_code=409, detail=f"Cannot reject from status: {current_status}")

@router.delete("/approvals/{approval_id}")
def delete_approval(approval_id: str):
    return {"success": delete_item(APPROVALS_PATH, approval_id), "message": "Onay isteği silindi."}
