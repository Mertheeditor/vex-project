from __future__ import annotations

from datetime import datetime

from app.core.paths import EVOLUTION_LOGS_PATH, EVOLUTION_PENDING_PATH
from app.storage.json_store import load_json, save_json

running = False

def get_logs() -> dict:
    return {"success": True, "logs": load_json(EVOLUTION_LOGS_PATH, [])}

def add_log(message: str) -> None:
    logs = load_json(EVOLUTION_LOGS_PATH, [])
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    save_json(EVOLUTION_LOGS_PATH, logs[-300:])

def reset_logs() -> dict:
    save_json(EVOLUTION_LOGS_PATH, [])
    return {"success": True, "message": "Evrim logları sıfırlandı."}

def status() -> dict:
    return {"success": True, "running": running}

def pending_actions() -> dict:
    return {"success": True, "pending_actions": load_json(EVOLUTION_PENDING_PATH, [])}

def start_prompt(prompt: str) -> dict:
    global running
    running = True
    add_log(f"Evrim prompt alındı: {prompt}")
    actions = load_json(EVOLUTION_PENDING_PATH, [])
    action = {"id": f"evo-{datetime.now().strftime('%Y%m%d%H%M%S')}", "title": "Önerilen güvenli refactor", "description": prompt, "risk_level": "manual_review", "status": "pending"}
    actions.append(action)
    save_json(EVOLUTION_PENDING_PATH, actions)
    running = False
    return {"success": True, "message": "Evrim önerisi bekleyen işlemlere eklendi.", "action": action}

def approve(action_id: str) -> dict:
    actions = load_json(EVOLUTION_PENDING_PATH, [])
    for action in actions:
        if action.get("id") == action_id:
            action["status"] = "approved"
            add_log(f"İşlem onaylandı: {action_id}")
    save_json(EVOLUTION_PENDING_PATH, actions)
    return {"success": True, "message": "İşlem onaylandı."}

def reject(action_id: str) -> dict:
    actions = load_json(EVOLUTION_PENDING_PATH, [])
    for action in actions:
        if action.get("id") == action_id:
            action["status"] = "rejected"
            add_log(f"İşlem reddedildi: {action_id}")
    save_json(EVOLUTION_PENDING_PATH, actions)
    return {"success": True, "message": "İşlem reddedildi."}
