from __future__ import annotations

from fastapi import APIRouter
from app.schemas.common import ChatRequest
from app.services.gemini_service import generate_text
from app.storage.memory_store import load_memory

router = APIRouter()

@router.post("/chat")
def chat(request: ChatRequest):
    memory = load_memory()
    rules = "\n".join(f"- {rule}" for rule in memory.get("rules", []))
    prompt = f"Sen Vex'sin, Mert'in kişisel yapay zeka iş arkadaşısın. Kısa, net ve pratik cevap ver.\nKurallar:\n{rules}\n\nMert: {request.message}\nVex:"
    result = generate_text(prompt)
    if result.get("success"):
        return {"success": True, "reply": result.get("text") or "Tamam Mert."}
    return {"success": True, "reply": f"Backend çalışıyor Mert. Gemini hazır değil: {result.get('message')}"}
