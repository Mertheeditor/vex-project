from __future__ import annotations

from fastapi import APIRouter
from app.core.paths import PROJECTS_PATH, TASKS_PATH
from app.schemas.common import ActiveProjectRequest, ActiveTaskRequest
from app.storage.entity_store import find_item
from app.storage.workspace_store import active_project_detail, get_active_project_id, get_active_task_id, set_active_project_id, set_active_task_id, summary

router = APIRouter()

@router.get("/workspace/summary")
def workspace_summary():
    return summary()

@router.get("/workspace/active-project")
def get_active_project():
    project_id = get_active_project_id()
    return {"success": True, "project_id": project_id, "project": find_item(PROJECTS_PATH, project_id) if project_id else None}

@router.post("/workspace/active-project")
def set_active_project(request: ActiveProjectRequest):
    set_active_project_id(request.project_id)
    return {"success": True, "message": "Aktif proje güncellendi.", "project_id": request.project_id, "project": find_item(PROJECTS_PATH, request.project_id)}

@router.get("/workspace/active-task")
def get_active_task():
    task_id = get_active_task_id()
    return {"success": True, "task_id": task_id, "task": find_item(TASKS_PATH, task_id) if task_id else None}

@router.post("/workspace/active-task")
def set_active_task(request: ActiveTaskRequest):
    set_active_task_id(request.task_id)
    return {"success": True, "message": "Aktif görev güncellendi.", "task_id": request.task_id, "task": find_item(TASKS_PATH, request.task_id)}

@router.get("/workspace/active-project/detail")
def get_active_project_detail():
    return active_project_detail()
