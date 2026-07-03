from __future__ import annotations

from fastapi import APIRouter
from app.core.paths import OUTPUTS_PATH
from app.schemas.common import OutputRequest
from app.storage.entity_store import delete_item, list_items, upsert_item

router = APIRouter()

@router.get("/outputs")
def get_outputs():
    return list_items(OUTPUTS_PATH)

@router.post("/outputs/from-chat")
def create_output_from_chat(request: OutputRequest):
    output = upsert_item(OUTPUTS_PATH, request.model_dump(), "cikti")
    return {"success": True, "message": "Çıktı kaydedildi.", "output": output, "outputs": list_items(OUTPUTS_PATH)}

@router.delete("/outputs/{output_id}")
def delete_output(output_id: str):
    return {"success": delete_item(OUTPUTS_PATH, output_id), "message": "Çıktı silindi."}
