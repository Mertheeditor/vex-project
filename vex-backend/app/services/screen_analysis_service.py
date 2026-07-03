from __future__ import annotations

from app.services.gemini_service import generate_text
from app.services.screenshot_service import capture_screenshot

def analyze_screen(prompt: str) -> dict:
    shot = capture_screenshot()
    if not shot.get("success"):
        return shot
    ai = generate_text(f"Ekran görüntüsü alındı. Kullanıcı isteği: {prompt}\nNot: Bu geçici modül görseli modele göndermiyor, sadece screenshot durumunu raporluyor.")
    if ai.get("success"):
        return {"success": True, "analysis": ai.get("text") or "Screenshot alındı."}
    return {"success": True, "analysis": "Screenshot alındı ama Gemini analizi yapılamadı: " + ai.get("message", "Bilinmeyen hata")}
