from __future__ import annotations

from app.core.config import GEMINI_API_KEY
from app.core.optional_imports import optional_import

def generate_text(prompt: str) -> dict:
    if not GEMINI_API_KEY:
        return {"success": False, "message": "GEMINI_API_KEY tanımlı değil."}
    genai, error = optional_import("google.genai")
    if error:
        return {"success": False, "message": f"google-genai paketi kurulu değil: {error}"}
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return {"success": True, "text": getattr(response, "text", "") or ""}
    except Exception as exc:
        return {"success": False, "message": f"Gemini isteği başarısız: {exc}"}
