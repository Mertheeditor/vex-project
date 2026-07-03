from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO

from app.core.optional_imports import optional_import

def capture_screenshot() -> dict:
    mss_module, mss_error = optional_import("mss")
    image_cls, pil_error = optional_import("PIL.Image", "Image")
    if mss_error:
        return {"success": False, "message": f"mss paketi kurulu değil veya çalışmıyor: {mss_error}"}
    if pil_error:
        return {"success": False, "message": f"Pillow/PIL paketi kurulu değil veya çalışmıyor: {pil_error}"}
    try:
        with mss_module.mss() as sct:
            monitor = sct.monitors[0]
            shot = sct.grab(monitor)
            image = image_cls.frombytes("RGB", shot.size, shot.rgb)
            buffer = BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return {
                "success": True,
                "image_base64": encoded,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "width": shot.size.width,
                "height": shot.size.height,
            }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Screenshot alınamadı: {exc}. macOS Screen Recording iznini Terminal/VS Code/Python için kontrol et.",
        }
