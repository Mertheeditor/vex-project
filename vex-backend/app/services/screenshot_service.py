from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from typing import Any, Dict


def capture_screenshot() -> Dict[str, Any]:
    try:
        try:
            import mss
            from PIL import Image
        except Exception as import_error:
            return {
                "success": False,
                "message": f"Screenshot için gerekli paket eksik: {import_error}",
            }

        with mss.mss() as sct:
            monitor = sct.monitors[0]
            raw_screenshot = sct.grab(monitor)

            image = Image.frombytes(
                "RGB",
                raw_screenshot.size,
                raw_screenshot.rgb,
            )

            buffer = BytesIO()
            image.save(buffer, format="PNG", optimize=True)

            image_bytes = buffer.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            width, height = image.size

            return {
                "success": True,
                "image_base64": image_base64,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "width": width,
                "height": height,
            }

    except Exception as error:
        return {
            "success": False,
            "message": (
                f"Screenshot alınamadı: {error}. "
                "macOS Screen Recording iznini Terminal/VS Code/Python için kontrol et."
            ),
        }