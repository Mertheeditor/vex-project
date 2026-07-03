from __future__ import annotations

import re
from datetime import datetime, timedelta

def slugify(text: str, fallback: str = "item") -> str:
    value = (text or "").strip().lower()
    replacements = {
        "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
        "İ": "i", "Ğ": "g", "Ü": "u", "Ş": "s", "Ö": "o", "Ç": "c",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or fallback

def split_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]

def extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*", text or "")
    if not match:
        return ""
    return match.group(0).rstrip("),.;")

def parse_reminder_time(message: str) -> str:
    now = datetime.now()
    text = (message or "").lower()
    m = re.search(r"(\d+)\s*dakika", text)
    if m:
        return (now + timedelta(minutes=int(m.group(1)))).isoformat(timespec="seconds")
    m = re.search(r"(\d+)\s*saat", text)
    if m:
        return (now + timedelta(hours=int(m.group(1)))).isoformat(timespec="seconds")
    m = re.search(r"(\d+)\s*gün", text)
    if m:
        return (now + timedelta(days=int(m.group(1)))).isoformat(timespec="seconds")
    return (now + timedelta(hours=1)).isoformat(timespec="seconds")
