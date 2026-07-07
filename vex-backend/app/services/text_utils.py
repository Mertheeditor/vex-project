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


_WEEKDAYS = {
    "pazartesi": 0,
    "salı": 1, "sali": 1,
    "çarşamba": 2, "carsamba": 2,
    "perşembe": 3, "persembe": 3,
    "cuma": 4,
    "cumartesi": 5,
    "pazar": 6,
}


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def parse_reminder_time_detailed(message: str) -> tuple[str, bool]:
    """(ISO zaman, ifade gerçekten anlaşıldı mı) döner.

    Anlaşılan kalıplar: "X dakika/dk", "X saat", "X gün", "15:00" / "15.30",
    "saat 9", "bugün", "yarın", hafta günü adları ve bunların kombinasyonları
    ("yarın 15:00", "pazartesi saat 10" gibi).
    Hiçbiri eşleşmezse 1 saat sonrası döner ve bayrak False olur.
    """
    now = datetime.now()
    text = (message or "").lower()

    m = re.search(r"(\d+)\s*(dakika|dk)\b", text)
    if m:
        return _iso(now + timedelta(minutes=int(m.group(1)))), True
    m = re.search(r"(\d+)\s*saat\b", text)
    if m:
        return _iso(now + timedelta(hours=int(m.group(1)))), True
    m = re.search(r"(\d+)\s*g[uü]n\b", text)
    if m:
        return _iso(now + timedelta(days=int(m.group(1)))), True

    hour: int | None = None
    minute = 0
    m = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"saat\s*([01]?\d|2[0-3])\b", text)
        if m:
            hour = int(m.group(1))

    day_offset: int | None = None
    if "yarın" in text or "yarin" in text:
        day_offset = 1
    elif "bugün" in text or "bugun" in text:
        day_offset = 0
    else:
        for name, weekday in _WEEKDAYS.items():
            if re.search(r"\b" + name + r"\b", text):
                delta = (weekday - now.weekday()) % 7
                day_offset = 7 if delta == 0 else delta
                break

    if hour is not None:
        base = now + timedelta(days=day_offset or 0)
        target = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if day_offset is None and target <= now:
            target += timedelta(days=1)
        return _iso(target), True

    if day_offset is not None:
        target = (now + timedelta(days=day_offset)).replace(hour=9, minute=0, second=0, microsecond=0)
        if day_offset == 0 and target <= now:
            target = now + timedelta(hours=1)
        return _iso(target), True

    return _iso(now + timedelta(hours=1)), False


def parse_reminder_time(message: str) -> str:
    return parse_reminder_time_detailed(message)[0]
