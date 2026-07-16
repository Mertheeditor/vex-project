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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "").strip() or GEMINI_MODEL
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
GEMINI_ENABLED = os.getenv("GEMINI_ENABLED", "true").strip().lower() == "true"

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip() or "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra").strip() or "nvidia/nemotron-3-ultra"
NVIDIA_TIMEOUT_SECONDS = float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "60"))
NVIDIA_MAX_RETRIES = int(os.getenv("NVIDIA_MAX_RETRIES", "3"))
NVIDIA_ENABLED = os.getenv("NVIDIA_ENABLED", "true").strip().lower() == "true"

AI_PROVIDER_MODE = os.getenv("AI_PROVIDER_MODE", "auto").strip() or "auto"
AI_PROVIDER_FALLBACK_ORDER = os.getenv("AI_PROVIDER_FALLBACK_ORDER", "gemini,nvidia").strip() or "gemini,nvidia"

CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "20"))

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "small").strip() or "small"
WHISPER_SAMPLE_RATE = int(os.getenv("WHISPER_SAMPLE_RATE", "16000"))
WHISPER_CHANNELS = int(os.getenv("WHISPER_CHANNELS", "1"))
MICROPHONE_DEVICE_INDEX_RAW = os.getenv("MICROPHONE_DEVICE_INDEX", "").strip()
MICROPHONE_DEVICE_INDEX = int(MICROPHONE_DEVICE_INDEX_RAW) if MICROPHONE_DEVICE_INDEX_RAW else None
