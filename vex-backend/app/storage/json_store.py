from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

# Dosya başına kilit: aynı json dosyasına eşzamanlı okuma/yazma çakışmasını önler.
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path)
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    with _lock_for(path):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            # Bozuk dosyayı sessizce sıfırlamak yerine yedeğini al, sonra default dön.
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            corrupt_copy = path.with_name(path.name + f".corrupt-{stamp}")
            try:
                shutil.copy2(path, corrupt_copy)
                print(f"[json_store] UYARI: {path.name} bozuk JSON içeriyordu; yedek: {corrupt_copy.name}")
            except Exception:
                pass
            return default
        except Exception as exc:
            print(f"[json_store] UYARI: {path.name} okunamadı: {exc}")
            return default


def save_json(path: Path, data: Any) -> None:
    with _lock_for(path):
        ensure_parent(path)
        # Atomik yazma: önce aynı klasörde geçici dosyaya yaz, sonra yerine taşı.
        fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
