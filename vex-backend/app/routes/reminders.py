from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.core.paths import REMINDERS_PATH
from app.schemas.common import ReminderDueRequest, ReminderFromChatRequest
from app.services.text_utils import parse_reminder_time_detailed
from app.storage.entity_store import delete_item, list_items, patch_item, upsert_item

router = APIRouter()


@router.get("/reminders")
def get_reminders():
    return list_items(REMINDERS_PATH)


@router.post("/reminders/from-chat")
def create_reminder_from_chat(request: ReminderFromChatRequest):
    remind_at, understood = parse_reminder_time_detailed(request.message)
    notes = ["Sohbetten oluşturuldu."]
    if not understood:
        notes.append("Zaman ifadesi net anlaşılamadı; varsayılan olarak 1 saat sonrasına kuruldu.")
    reminder = upsert_item(
        REMINDERS_PATH,
        {
            "title": request.message.strip()[:100] or "Hatırlatma",
            "remind_at": remind_at,
            "project_id": request.project_id,
            "task_id": request.task_id,
            "status": "active",
            "notified": False,
            "notes": notes,
        },
        "hatirlatma",
    )
    message = "Hatırlatma oluşturuldu." if understood else (
        "Hatırlatma oluşturuldu ama zaman ifadesini net anlayamadım; 1 saat sonrasına kurdum."
    )
    return {"success": True, "message": message, "reminder": reminder, "reminders": list_items(REMINDERS_PATH)}


@router.post("/reminders/due")
def due_reminders(request: ReminderDueRequest):
    now = datetime.now()
    due = []
    for item in list_items(REMINDERS_PATH):
        try:
            remind_at = datetime.fromisoformat(str(item.get("remind_at", "")))
        except Exception:
            continue
        if item.get("status") == "active" and not item.get("notified") and remind_at <= now:
            due.append(item)
            if request.mark_as_notified:
                patch_item(REMINDERS_PATH, item["id"], {"notified": True})
    return {"success": True, "due_reminders": due}


@router.delete("/reminders/{reminder_id}")
def delete_reminder(reminder_id: str):
    return {"success": delete_item(REMINDERS_PATH, reminder_id), "message": "Hatırlatma silindi."}
