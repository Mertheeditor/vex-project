from __future__ import annotations

from fastapi import APIRouter

from app.core.config import CHAT_HISTORY_LIMIT
from app.schemas.ai_provider import ProviderRequest
from app.schemas.common import ChatRequest
from app.services.ai_provider import TaskType
from app.services.ai_provider_router import initialize_router
from app.storage.memory_store import load_memory

router = APIRouter()

MAX_MESSAGE_CHARS = 2000


def _display_name(memory: dict) -> str:
    user = memory.get("user") or {}
    name = str(user.get("preferred_name") or user.get("name") or "").strip()
    return name or "Mert"


def _build_history_block(history: list, user_name: str) -> str:
    if not history:
        return ""
    lines: list[str] = []
    for item in history[-CHAT_HISTORY_LIMIT:]:
        sender = (getattr(item, "sender", "") or "").strip()
        text = (getattr(item, "text", "") or "").strip()
        if not text:
            continue
        speaker = user_name if sender in ("Sen", user_name) else "Vex"
        if len(text) > MAX_MESSAGE_CHARS:
            text = text[:MAX_MESSAGE_CHARS] + " …"
        lines.append(f"{speaker}: {text}")
    if not lines:
        return ""
    return "Önceki konuşma:\n" + "\n".join(lines) + "\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    memory = load_memory()
    user_name = _display_name(memory)
    assistant = memory.get("assistant") or {}
    tone = assistant.get("tone") or "samimi, pratik, doğal, iş odaklı"
    rules_list = memory.get("rules", []) or []
    rules = "\n".join(f"- {rule}" for rule in rules_list) if rules_list else "- (özel kural yok)"

    history_block = _build_history_block(request.history, user_name)

    prompt = (
        f"Sen Vex'sin; {user_name} adlı kullanıcının kişisel yapay zeka iş arkadaşısın. "
        f"Üslubun: {tone}. Kısa, net ve pratik cevap ver; önceki konuşmayı dikkate al.\n"
        f"Hafızadaki kurallar:\n{rules}\n\n"
        f"{history_block}"
        f"{user_name}: {request.message}\n"
        f"Vex:"
    )

    router = await initialize_router()
    provider_request = ProviderRequest(
        messages=[{"role": "user", "content": prompt}],
        task_type=TaskType.CHAT,
        temperature=0.7,
    )
    response = await router.complete(provider_request)

    if response.error:
        return {
            "success": False,
            "reply": f"⚠️ Şu an AI sağlayıcısına ulaşamıyorum {user_name}. Teknik detay: {response.error}",
            "error": response.error,
        }

    reply = (response.content or "").strip() or f"Tamam {user_name}."
    return {"success": True, "reply": reply, "provider": response.provider, "model": response.model}