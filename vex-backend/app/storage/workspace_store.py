from __future__ import annotations

from app.core.paths import ACTIVE_PROJECT_PATH, ACTIVE_TASK_PATH, APPROVALS_PATH, OUTPUTS_PATH, PROJECTS_PATH, TASKS_PATH
from app.storage.entity_store import find_item, list_items
from app.storage.json_store import load_json, save_json

def get_active_project_id() -> str:
    data = load_json(ACTIVE_PROJECT_PATH, {"project_id": ""})
    return str(data.get("project_id", "")) if isinstance(data, dict) else ""

def set_active_project_id(project_id: str) -> None:
    save_json(ACTIVE_PROJECT_PATH, {"project_id": project_id})

def get_active_task_id() -> str:
    data = load_json(ACTIVE_TASK_PATH, {"task_id": ""})
    return str(data.get("task_id", "")) if isinstance(data, dict) else ""

def set_active_task_id(task_id: str) -> None:
    save_json(ACTIVE_TASK_PATH, {"task_id": task_id})

def summary() -> dict:
    projects = list_items(PROJECTS_PATH)
    tasks = list_items(TASKS_PATH)
    approvals = list_items(APPROVALS_PATH)
    outputs = list_items(OUTPUTS_PATH)
    active_project_id = get_active_project_id()
    active_project = find_item(PROJECTS_PATH, active_project_id) if active_project_id else None
    open_tasks = [t for t in tasks if t.get("status") != "tamamlandı"]
    high_priority_tasks = [t for t in open_tasks if t.get("priority") in ["yüksek", "kritik", "high", "critical"]]
    pending_approvals = [a for a in approvals if a.get("status") in ["bekliyor", "pending"]]
    return {
        "success": True,
        "active_project": active_project,
        "active_project_id": active_project_id,
        "counts": {
            "active_projects": len([p for p in projects if p.get("status", "aktif") == "aktif"]),
            "open_tasks": len(open_tasks),
            "high_priority_tasks": len(high_priority_tasks),
            "pending_approvals": len(pending_approvals),
            "outputs": len(outputs),
            "preferences": 0,
        },
        "active_projects": [p for p in projects if p.get("status", "aktif") == "aktif"],
        "open_tasks": open_tasks,
        "high_priority_tasks": high_priority_tasks,
        "pending_approvals": pending_approvals,
        "outputs": outputs,
        "suggested_next_step": high_priority_tasks[0]["title"] if high_priority_tasks else (open_tasks[0]["title"] if open_tasks else "Yeni bir görev oluştur veya aktif projeyi seç."),
    }

def active_project_detail() -> dict:
    projects = list_items(PROJECTS_PATH)
    tasks = list_items(TASKS_PATH)
    approvals = list_items(APPROVALS_PATH)
    outputs = list_items(OUTPUTS_PATH)
    project_id = get_active_project_id()
    project = find_item(PROJECTS_PATH, project_id) if project_id else None
    project_tasks = [t for t in tasks if t.get("project_id") == project_id]
    open_tasks = [t for t in project_tasks if t.get("status") != "tamamlandı"]
    high_priority = [t for t in open_tasks if t.get("priority") in ["yüksek", "kritik", "high", "critical"]]
    project_approvals = [a for a in approvals if a.get("project_id") == project_id]
    pending = [a for a in project_approvals if a.get("status") in ["bekliyor", "pending"]]
    project_outputs = [o for o in outputs if o.get("project_id") == project_id]
    return {
        "success": True,
        "has_active_project": project is not None,
        "project_id": project_id,
        "project": project,
        "tasks": project_tasks,
        "open_tasks": open_tasks,
        "high_priority_tasks": high_priority,
        "approvals": project_approvals,
        "pending_approvals": pending,
        "outputs": project_outputs,
        "counts": {
            "tasks": len(project_tasks),
            "open_tasks": len(open_tasks),
            "high_priority_tasks": len(high_priority),
            "approvals": len(project_approvals),
            "pending_approvals": len(pending),
            "outputs": len(project_outputs),
        },
        "suggested_next_step": high_priority[0]["title"] if high_priority else (open_tasks[0]["title"] if open_tasks else "Bu proje için yeni görev oluştur."),
    }
