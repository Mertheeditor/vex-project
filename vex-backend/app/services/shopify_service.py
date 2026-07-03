from __future__ import annotations

def create_content_from_chat(message: str, project_id: str = "", task_id: str = "", language: str = "English") -> dict:
    title = message.strip()[:80] or "Shopify İçeriği"
    output = f"Başlık: {title}\n\nAçıklama:\n{message.strip()}\n\nSEO Meta Title:\n{title}\n\nSEO Meta Description:\n{message.strip()[:150]}"
    return {"success": True, "formatted_output": output, "message": "Shopify içerik taslağı hazırlandı."}
