#!/usr/bin/env python3
"""Best-effort macOS notification hook for the Vex agent team."""

from __future__ import annotations

import json
import re
import subprocess
import sys


SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|credential|private[_-]?key)\b"
)


def safe_message(data: dict) -> str:
    candidates = (
        data.get("message"),
        data.get("notification"),
        data.get("title"),
        data.get("event"),
    )

    message = next(
        (value for value in candidates if isinstance(value, str) and value.strip()),
        "Claude Code bildirimi",
    )

    message = " ".join(message.split())
    if SENSITIVE_PATTERN.search(message):
        return "Gizli bilgi içerebilecek bir olay algılandı; ayrıntılar bildirimde gösterilmedi."

    return message[:240]


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    message = safe_message(data)

    apple_script = (
        'on run argv\n'
        'display notification (item 1 of argv) with title "Vex Agent Team"\n'
        'end run'
    )

    try:
        subprocess.run(
            ["osascript", "-e", apple_script, message],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
