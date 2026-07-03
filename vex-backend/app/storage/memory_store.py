from __future__ import annotations

from app.core.paths import MEMORY_PATH
from app.storage.json_store import load_json, save_json

def default_memory() -> dict:
    return {
        "user": {"name": "Mert", "preferred_name": "Mert"},
        "assistant": {"name": "Vex", "role": "Mert'in kişisel yapay zeka iş arkadaşı", "tone": "samimi, pratik, doğal, iş odaklı"},
        "project": {"name": "Vex", "motto": "Basit MVP değil; baştan iyi mimariyle büyüyen sistem."},
        "ai": {"primary_model_provider": "Gemini API", "fallback_strategy": "Modüller opsiyonel ve local-first çalışır."},
        "work_domains": ["tasarım", "Shopify", "site yönetimi", "otomasyon", "proje takibi"],
        "rules": [],
    }

def load_memory() -> dict:
    memory = load_json(MEMORY_PATH, default_memory())
    memory.setdefault("rules", [])
    return memory

def save_memory(memory: dict) -> None:
    save_json(MEMORY_PATH, memory)

def add_rule_from_message(message: str) -> dict:
    memory = load_memory()
    rule = message.strip()
    prefixes = ["hafızana yaz", "hafızaya yaz", "bunu unutma", "unutma", "remember that"]
    lower = rule.lower()
    for prefix in prefixes:
        if lower.startswith(prefix):
            rule = rule[len(prefix):].strip(" :,-")
            break
    if not rule:
        return {"success": False, "message": "Net bir kural çıkaramadım."}
    if rule not in memory["rules"]:
        memory["rules"].append(rule)
        save_memory(memory)
    return {"success": True, "message": "Kural hafızaya eklendi.", "rule": rule}
