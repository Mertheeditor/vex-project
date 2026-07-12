from __future__ import annotations

"""
Proaktif zamanlayıcı — Vex'in arka planda kendi kendine çalışan kalbi.

Frontend'e bağlı DEĞİLDİR: uygulama penceresi kapalı olsa bile backend açık
olduğu sürece hatırlatmaları kontrol eder. Zamanı gelen hatırlatmayı
"notified" işaretler ve bir bildirim kaydına düşer. Böylece "Vex zamanı
gelince uyarır" hedefinin backend temeli kurulur. (Gerçek OS/masaüstü push'u
ileride frontend'e bağlanır; bu katman kaynağı üretir.)
"""

import threading
import time
from datetime import datetime

from app.core.paths import REMINDERS_PATH
from app.storage.entity_store import list_items, patch_item
from app.storage.json_store import load_json, save_json

CHECK_INTERVAL_SECONDS = 30

_thread: threading.Thread | None = None
_stop = threading.Event()
_state = {"running": False, "last_check": None, "fired_total": 0}

# Bildirim kaydı: zamanı gelen hatırlatmalar buraya yazılır; frontend/status okur.
from app.core.config import DATA_DIR  # noqa: E402

NOTIFICATIONS_PATH = DATA_DIR / "notifications.json"


def _log_notification(reminder: dict) -> None:
    notes = load_json(NOTIFICATIONS_PATH, [])
    notes.append({
        "id": f"notif-{datetime.now().strftime('%Y%m%d%H%M%S')}-{reminder.get('id', '')}",
        "reminder_id": reminder.get("id"),
        "title": reminder.get("title", "Hatırlatma"),
        "fired_at": datetime.now().isoformat(timespec="seconds"),
        "seen": False,
    })
    save_json(NOTIFICATIONS_PATH, notes[-200:])


def _check_due() -> int:
    now = datetime.now()
    fired = 0
    for item in list_items(REMINDERS_PATH):
        if item.get("status") != "active" or item.get("notified"):
            continue
        try:
            remind_at = datetime.fromisoformat(str(item.get("remind_at", "")))
        except Exception:
            continue
        if remind_at <= now:
            patch_item(REMINDERS_PATH, item["id"], {"notified": True})
            _log_notification(item)
            fired += 1
    return fired


def _loop() -> None:
    while not _stop.is_set():
        try:
            fired = _check_due()
            _state["last_check"] = datetime.now().isoformat(timespec="seconds")
            if fired:
                _state["fired_total"] += fired
                print(f"[scheduler] {fired} hatırlatma tetiklendi.")
        except Exception as exc:
            print(f"[scheduler] hata: {exc}")
        _stop.wait(CHECK_INTERVAL_SECONDS)
    _state["running"] = False


def start() -> None:
    global _thread
    if _state["running"]:
        return
    _stop.clear()
    _state["running"] = True
    _thread = threading.Thread(target=_loop, daemon=True, name="vex-scheduler")
    _thread.start()
    print("[scheduler] Proaktif zamanlayıcı başladı.")


def stop() -> None:
    _stop.set()
    _state["running"] = False


def status() -> dict:
    return {"success": True, **_state, "interval_seconds": CHECK_INTERVAL_SECONDS}


def pending_notifications(only_unseen: bool = True) -> dict:
    notes = load_json(NOTIFICATIONS_PATH, [])
    if only_unseen:
        notes = [n for n in notes if not n.get("seen")]
    return {"success": True, "notifications": notes}


def mark_notifications_seen() -> dict:
    notes = load_json(NOTIFICATIONS_PATH, [])
    for n in notes:
        n["seen"] = True
    save_json(NOTIFICATIONS_PATH, notes)
    return {"success": True, "message": "Bildirimler okundu işaretlendi."}
