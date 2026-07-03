from __future__ import annotations

from fastapi import APIRouter

from app.core.optional_imports import module_status
from app.core.paths import MEMORY_PATH

router = APIRouter()

@router.get("/health")
def health():
    return {
        "success": True,
        "status": "online",
        "service": "vex-backend",
        "modules": {
            "gemini": module_status("google.genai"),
            "speech_whisper": module_status("faster_whisper", "WhisperModel"),
            "speech_device": module_status("sounddevice"),
            "screenshot": module_status("mss"),
            "storage": "ok",
            "memory_path": str(MEMORY_PATH),
        },
    }
