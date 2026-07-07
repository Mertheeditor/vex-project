from __future__ import annotations

import base64
from typing import Any

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_VISION_MODEL
from app.core.optional_imports import optional_import

_client: Any = None


def _get_client() -> tuple[Any, str | None]:
    global _client
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY tanımlı değil."
    if _client is not None:
        return _client, None
    genai, error = optional_import("google.genai")
    if error:
        return None, f"google-genai paketi kurulu değil: {error}"
    try:
        _client = genai.Client(api_key=GEMINI_API_KEY)
        return _client, None
    except Exception as exc:
        return None, f"Gemini client oluşturulamadı: {exc}"


def strip_code_fences(text: str) -> str:
    value = (text or "").strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def generate_text(prompt: str, model: str | None = None) -> dict:
    client, error = _get_client()
    if error:
        return {"success": False, "message": error}
    try:
        response = client.models.generate_content(model=model or GEMINI_MODEL, contents=prompt)
        return {"success": True, "text": getattr(response, "text", "") or ""}
    except Exception as exc:
        return {"success": False, "message": f"Gemini isteği başarısız: {exc}"}


def generate_with_image(prompt: str, image_base64: str, mime_type: str = "image/png", model: str | None = None) -> dict:
    client, error = _get_client()
    if error:
        return {"success": False, "message": error}
    try:
        raw = base64.b64decode(image_base64)
    except Exception as exc:
        return {"success": False, "message": f"Görüntü çözümlenemedi: {exc}"}
    target_model = model or GEMINI_VISION_MODEL
    types_mod, types_error = optional_import("google.genai.types")
    try:
        if not types_error and hasattr(types_mod, "Part"):
            part = types_mod.Part.from_bytes(data=raw, mime_type=mime_type)
            response = client.models.generate_content(model=target_model, contents=[prompt, part])
        else:
            response = client.models.generate_content(
                model=target_model,
                contents=[{
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": raw}},
                    ],
                }],
            )
        return {"success": True, "text": getattr(response, "text", "") or ""}
    except Exception as exc:
        return {"success": False, "message": f"Gemini görüntü isteği başarısız: {exc}"}
