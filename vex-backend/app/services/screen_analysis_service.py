from __future__ import annotations

from app.services.gemini_service import generate_with_image
from app.services.screenshot_service import capture_screenshot


def analyze_screen(prompt: str) -> dict:
    shot = capture_screenshot()
    if not shot.get("success"):
        return shot
    instruction = (prompt or "").strip() or "Ekranda ne olduğunu analiz et."
    full_prompt = (
        "Bu, kullanıcının o anki ekran görüntüsüdür. Türkçe cevap ver.\n"
        f"Kullanıcının isteği: {instruction}\n"
        "Ekranda gördüklerini kısa ve net açıkla; buton, form alanı, menü gibi "
        "etkileşim öğeleri varsa belirt."
    )
    ai = generate_with_image(full_prompt, shot["image_base64"], "image/png")
    if ai.get("success"):
        return {
            "success": True,
            "analysis": (ai.get("text") or "").strip() or "Ekran görüntüsü analiz edildi.",
            "timestamp": shot.get("timestamp"),
        }
    message = "Screenshot alındı ama Gemini analizi yapılamadı: " + ai.get("message", "Bilinmeyen hata")
    return {"success": False, "message": message, "analysis": message}
