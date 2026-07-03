from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from app.core.paths import TASKS_PATH
from app.schemas.common import TaskRequest
from app.storage.entity_store import delete_item, list_items, patch_item, upsert_item

router = APIRouter()

class TaskFromChatRequest(BaseModel):
    message: str = ""
    project_id: str = ""

@router.get("/tasks")
def get_tasks():
    return list_items(TASKS_PATH)

@router.post("/tasks/from-chat")
def create_task_from_chat(request: TaskFromChatRequest):
    task = upsert_item(TASKS_PATH, {"title": request.message.strip()[:80] or "Yeni Görev", "project_id": request.project_id, "status": "açık", "priority": "normal", "description": request.message, "notes": ["Sohbetten oluşturuldu."]}, "gorev")
    return {"success": True, "message": "Görev oluşturuldu.", "task": task, "tasks": list_items(TASKS_PATH), "source_message": request.message}

@router.patch("/tasks/{task_id}/complete")
def complete_task(task_id: str):
    task = patch_item(TASKS_PATH, task_id, {"status": "tamamlandı"})
    return {"success": task is not None, "message": "Görev tamamlandı.", "task": task, "tasks": list_items(TASKS_PATH)}

@router.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    return {"success": delete_item(TASKS_PATH, task_id), "message": "Görev silindi."}
