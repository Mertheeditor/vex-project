from __future__ import annotations

from fastapi import APIRouter
from app.core.paths import PROJECTS_PATH
from app.schemas.common import MessageRequest, ProjectRequest
from app.services.text_utils import slugify
from app.storage.entity_store import delete_item, list_items, upsert_item

router = APIRouter()

@router.get("/projects")
def get_projects():
    return list_items(PROJECTS_PATH)

@router.post("/projects")
def create_project(request: ProjectRequest):
    data = request.model_dump()
    if not data.get("id"):
        data["id"] = slugify(data.get("name", "proje"), "proje")
    return upsert_item(PROJECTS_PATH, data, "proje")

@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    return {"success": delete_item(PROJECTS_PATH, project_id), "message": "Proje silindi."}

@router.post("/projects/from-chat")
def create_project_from_chat(request: MessageRequest):
    name = request.message.strip()[:80] or "Yeni Proje"
    project = upsert_item(PROJECTS_PATH, {"name": name, "type": "Genel proje", "status": "aktif", "description": request.message, "main_goals": [], "notes": ["Sohbetten oluşturuldu."]}, "proje")
    return {"success": True, "message": "Proje oluşturuldu.", "project": project, "projects": list_items(PROJECTS_PATH), "source_message": request.message}
