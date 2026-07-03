from __future__ import annotations

from datetime import datetime

from app.core.paths import COMPUTER_LOGS_PATH
from app.services.screenshot_service import capture_screenshot
from app.storage.json_store import load_json, save_json

state = {
    "running": False,
    "active_task_id": None,
    "last_intent": "unknown",
    "last_action": "none",
    "manual_pending_action": None,
}

def add_log(message: str) -> None:
    logs = load_json(COMPUTER_LOGS_PATH, [])
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    save_json(COMPUTER_LOGS_PATH, logs[-200:])

def status() -> dict:
    result = {"success": True, **state}
    if state.get("running"):
        result["screenshot"] = capture_screenshot()
    return result

def logs() -> dict:
    return {"success": True, "logs": load_json(COMPUTER_LOGS_PATH, [])}

def plan(instruction: str) -> dict:
    state["last_intent"] = instruction or "unknown"
    add_log(f"Plan istendi: {instruction}")
    return {"success": True, "plan": ["Ekranı analiz et", "Riskli aksiyon varsa onay iste", "Güvenli aksiyonu uygula"], "message": "Plan hazır."}

def start(instruction: str = "") -> dict:
    state["running"] = True
    state["active_task_id"] = f"computer-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    state["last_intent"] = instruction or "manual"
    state["last_action"] = "started"
    add_log(f"Computer-use başladı: {instruction}")
    return {"success": True, "message": "Computer-use başlatıldı.", **state}

def stop() -> dict:
    state["running"] = False
    state["last_action"] = "stopped"
    add_log("Computer-use durduruldu.")
    return {"success": True, "message": "Computer-use durduruldu.", **state}
