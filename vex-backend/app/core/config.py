from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parents[2]

if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

# Runtime verileri (json dosyaları, screenshotlar) bu klasörde tutulur.
# Kişisel veri içerdiği için git'e girmez (bkz. kökteki .gitignore).
DATA_DIR = Path(os.getenv("VEX_DATA_DIR", str(BASE_DIR / "data"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "").strip() or GEMINI_MODEL
CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "20"))

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "small").strip() or "small"
WHISPER_SAMPLE_RATE = int(os.getenv("WHISPER_SAMPLE_RATE", "16000"))
WHISPER_CHANNELS = int(os.getenv("WHISPER_CHANNELS", "1"))
MICROPHONE_DEVICE_INDEX_RAW = os.getenv("MICROPHONE_DEVICE_INDEX", "").strip()
MICROPHONE_DEVICE_INDEX = int(MICROPHONE_DEVICE_INDEX_RAW) if MICROPHONE_DEVICE_INDEX_RAW else None
