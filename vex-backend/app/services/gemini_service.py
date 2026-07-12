from __future__ import annotations

import base64
import time
from typing import Any

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_VISION_MODEL
from app.core.optional_imports import optional_import

_client: Any = None

# Google'ın generativelanguage.googleapis.com ucu bazen (özellikle model
# geçişleri sırasında) tekil sunucularda geçici/rastgele 404 NOT_FOUND
# döndürebiliyor; aynı istek kısa süre sonra tekrar denendiğinde genelde
# başarılı oluyor. Bu yüzden 404 için birkaç kez retry yapıyoruz.
_RETRYABLE_STATUS_MARKERS = ("404", "NOT_FOUND", "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")


def _is_retryable_error(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in _RETRYABLE_STATUS_MARKERS)


def _call_with_retry(func, *, attempts: int = 3, delay: float = 0.6):
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return func(), None
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1 and _is_retryable_error(exc):
                time.sleep(delay * (attempt + 1))
                continue
            break
    return None, last_exc



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
        types_mod, types_error = optional_import("google.genai.types")
        if not types_error and hasattr(types_mod, "HttpOptions"):
            _client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=types_mod.HttpOptions(api_version="v1beta"),
            )
        else:
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
    target_model = model or GEMINI_MODEL
    response, exc = _call_with_retry(
        lambda: client.models.generate_content(model=target_model, contents=prompt)
    )
    if exc is not None:
        return {"success": False, "message": f"Gemini isteği başarısız: {exc}"}
    return {"success": True, "text": getattr(response, "text", "") or ""}


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

    def _call():
        if not types_error and hasattr(types_mod, "Part"):
            part = types_mod.Part.from_bytes(data=raw, mime_type=mime_type)
            return client.models.generate_content(model=target_model, contents=[prompt, part])
        return client.models.generate_content(
            model=target_model,
            contents=[{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": raw}},
                ],
            }],
        )

    response, exc = _call_with_retry(_call)
    if exc is not None:
        return {"success": False, "message": f"Gemini görüntü isteği başarısız: {exc}"}
    return {"success": True, "text": getattr(response, "text", "") or ""}
