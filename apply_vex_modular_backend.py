#!/usr/bin/env python3
"""
Vex modular backend refactor installer.
Run from /Users/mert/Vex or /Users/mert/Vex/vex-backend:
  python3 apply_vex_modular_backend.py

What it does:
- Backs up vex-backend/main.py to main.legacy.py and timestamped backup.
- Creates modular FastAPI backend under vex-backend/app/.
- Replaces vex-backend/main.py with a lightweight router-based app.
- Writes requirements.txt, .env.example, PROJECT_CONTEXT.md and safer .gitignore.
"""
from __future__ import annotations

import os
import shutil
import textwrap
from datetime import datetime
from pathlib import Path


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    print(f"wrote {path}")


def find_paths() -> tuple[Path, Path]:
    cwd = Path.cwd().resolve()
    if (cwd / "vex-backend").is_dir():
        root = cwd
        backend = cwd / "vex-backend"
    elif cwd.name == "vex-backend":
        backend = cwd
        root = cwd.parent
    else:
        raise SystemExit("Bu script'i /Users/mert/Vex veya /Users/mert/Vex/vex-backend içinde çalıştır.")
    return root, backend


def backup_main(backend: Path) -> None:
    main = backend / "main.py"
    if not main.exists():
        print("main.py bulunamadı, yeni main.py oluşturulacak.")
        return
    legacy = backend / "main.legacy.py"
    if not legacy.exists():
        shutil.copy2(main, legacy)
        print("backup created: main.legacy.py")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    ts_backup = backend / f"main.backup-{ts}.py"
    shutil.copy2(main, ts_backup)
    print(f"backup created: {ts_backup.name}")


def main() -> None:
    root, backend = find_paths()
    print(f"root: {root}")
    print(f"backend: {backend}")
    backup_main(backend)

    # Package markers
    for package in [
        "app", "app/core", "app/schemas", "app/storage", "app/services", "app/routes",
    ]:
        write_file(backend / package / "__init__.py", "")

    write_file(backend / "main.py", r'''
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware

        from app.routes import (
            approvals,
            chat,
            computer,
            evolution,
            health,
            memory,
            outputs,
            projects,
            reminders,
            screen,
            shopify,
            site,
            speech,
            tasks,
            workspace,
        )

        app = FastAPI(title="Vex Backend", version="0.2.0")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:1420",
                "http://127.0.0.1:1420",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/")
        def root():
            return {"success": True, "message": "Vex backend çalışıyor.", "service": "vex-backend"}

        app.include_router(health.router)
        app.include_router(chat.router)
        app.include_router(memory.router)
        app.include_router(projects.router)
        app.include_router(tasks.router)
        app.include_router(approvals.router)
        app.include_router(outputs.router)
        app.include_router(reminders.router)
        app.include_router(workspace.router)
        app.include_router(speech.router)
        app.include_router(screen.router)
        app.include_router(computer.router)
        app.include_router(site.router)
        app.include_router(shopify.router)
        app.include_router(evolution.router)
    ''')

    write_file(backend / "app/core/config.py", r'''
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

        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
        WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "small").strip() or "small"
        WHISPER_SAMPLE_RATE = int(os.getenv("WHISPER_SAMPLE_RATE", "16000"))
        WHISPER_CHANNELS = int(os.getenv("WHISPER_CHANNELS", "1"))
        MICROPHONE_DEVICE_INDEX_RAW = os.getenv("MICROPHONE_DEVICE_INDEX", "").strip()
        MICROPHONE_DEVICE_INDEX = int(MICROPHONE_DEVICE_INDEX_RAW) if MICROPHONE_DEVICE_INDEX_RAW else None
    ''')

    write_file(backend / "app/core/paths.py", r'''
        from __future__ import annotations

        from pathlib import Path
        from app.core.config import BASE_DIR

        MEMORY_PATH = BASE_DIR / "memory.json"
        REMINDERS_PATH = BASE_DIR / "reminders.json"
        PROJECTS_PATH = BASE_DIR / "projects.json"
        TASKS_PATH = BASE_DIR / "tasks.json"
        APPROVALS_PATH = BASE_DIR / "approvals.json"
        ACTIVE_PROJECT_PATH = BASE_DIR / "active_project.json"
        ACTIVE_TASK_PATH = BASE_DIR / "active_task.json"
        OUTPUTS_PATH = BASE_DIR / "outputs.json"
        PREFERENCES_PATH = BASE_DIR / "preferences.json"
        SCREENSHOTS_PATH = BASE_DIR / "screenshots"
        COMPUTER_LOGS_PATH = BASE_DIR / "computer_logs.json"
        EVOLUTION_LOGS_PATH = BASE_DIR / "evolution_logs.json"
        EVOLUTION_PENDING_PATH = BASE_DIR / "evolution_pending_actions.json"
    ''')

    write_file(backend / "app/core/optional_imports.py", r'''
        from __future__ import annotations

        from importlib import import_module
        from typing import Any

        def optional_import(module_name: str, attr_name: str | None = None) -> tuple[Any | None, str | None]:
            try:
                module = import_module(module_name)
                if attr_name:
                    return getattr(module, attr_name), None
                return module, None
            except Exception as exc:
                return None, str(exc)

        def module_status(module_name: str, attr_name: str | None = None) -> str:
            _, error = optional_import(module_name, attr_name)
            return "available" if error is None else f"missing: {error}"
    ''')

    write_file(backend / "app/core/responses.py", r'''
        from __future__ import annotations

        def ok(**kwargs):
            return {"success": True, **kwargs}

        def fail(message: str, **kwargs):
            return {"success": False, "message": message, **kwargs}
    ''')

    write_file(backend / "app/schemas/common.py", r'''
        from __future__ import annotations

        from pydantic import BaseModel, Field

        class ChatMessage(BaseModel):
            sender: str = ""
            text: str = ""

        class ChatRequest(BaseModel):
            message: str
            history: list[ChatMessage] = Field(default_factory=list)

        class MessageRequest(BaseModel):
            message: str = ""

        class UrlAnalyzeRequest(BaseModel):
            url: str = ""
            prompt: str = "Siteyi SEO, tasarım, içerik ve güven algısı açısından analiz et."

        class SiteProductFinderRequest(BaseModel):
            url: str = ""
            query: str = ""
            language: str = "Turkish"
            max_pages: int = 40

        class ShopifyContentFromChatRequest(BaseModel):
            message: str
            project_id: str = ""
            task_id: str = ""
            language: str = "English"

        class ScreenAnalyzeRequest(BaseModel):
            prompt: str = "Ekranda ne olduğunu analiz et."

        class ComputerPlanRequest(BaseModel):
            instruction: str = ""

        class ReminderFromChatRequest(BaseModel):
            message: str
            project_id: str = ""
            task_id: str = ""

        class ReminderDueRequest(BaseModel):
            mark_as_notified: bool = True

        class ProjectRequest(BaseModel):
            id: str
            name: str
            type: str = "Genel proje"
            status: str = "aktif"
            description: str = ""
            main_goals: list[str] = Field(default_factory=list)
            notes: list[str] = Field(default_factory=list)

        class TaskRequest(BaseModel):
            id: str = ""
            title: str
            project_id: str = ""
            status: str = "açık"
            priority: str = "normal"
            description: str = ""
            notes: list[str] = Field(default_factory=list)

        class ApprovalRequest(BaseModel):
            id: str = ""
            title: str
            project_id: str = ""
            action_type: str = "genel"
            risk_level: str = "normal"
            status: str = "bekliyor"
            description: str = ""
            payload: dict = Field(default_factory=dict)
            notes: list[str] = Field(default_factory=list)

        class ActiveProjectRequest(BaseModel):
            project_id: str

        class ActiveTaskRequest(BaseModel):
            task_id: str

        class OutputRequest(BaseModel):
            id: str = ""
            title: str = ""
            project_id: str = ""
            task_id: str = ""
            output_type: str = "genel"
            content: str = ""
            status: str = "taslak"
            notes: list[str] = Field(default_factory=list)

        class RecordSpeechRequest(BaseModel):
            duration_seconds: float = 5

        class ListenSpeechRequest(BaseModel):
            max_seconds: float = 20
            silence_seconds: float = 1.2
            peak_threshold: float = 0.025
            average_threshold: float = 0.003
    ''')

    # Schema re-export placeholder modules
    for name in ["chat", "workspace", "memory", "projects", "tasks", "approvals", "outputs", "reminders", "speech", "computer", "site", "shopify", "evolution"]:
        write_file(backend / f"app/schemas/{name}.py", "from app.schemas.common import *\n")

    write_file(backend / "app/services/text_utils.py", r'''
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
    ''')

    write_file(backend / "app/storage/json_store.py", r'''
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Any

        def ensure_parent(path: Path) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)

        def load_json(path: Path, default: Any) -> Any:
            try:
                if not path.exists():
                    return default
                with path.open("r", encoding="utf-8") as file:
                    return json.load(file)
            except Exception:
                return default

        def save_json(path: Path, data: Any) -> None:
            ensure_parent(path)
            with path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
    ''')

    write_file(backend / "app/storage/memory_store.py", r'''
        from __future__ import annotations

        from app.core.paths import MEMORY_PATH
        from app.storage.json_store import load_json, save_json

        def default_memory() -> dict:
            return {
                "user": {"name": "Mert", "preferred_name": "Mert"},
                "assistant": {"name": "Vex", "role": "Mert'in kişisel yapay zeka iş arkadaşı", "tone": "samimi, pratik, doğal, iş odaklı"},
                "project": {"name": "Vex", "motto": "Basit MVP değil; baştan iyi mimariyle büyüyen sistem."},
                "ai": {"primary_model_provider": "Gemini API", "fallback_strategy": "Modüller opsiyonel ve local-first çalışır."},
                "work_domains": ["tasarım", "Shopify", "site yönetimi", "otomasyon", "proje takibi"],
                "rules": [],
            }

        def load_memory() -> dict:
            memory = load_json(MEMORY_PATH, default_memory())
            memory.setdefault("rules", [])
            return memory

        def save_memory(memory: dict) -> None:
            save_json(MEMORY_PATH, memory)

        def add_rule_from_message(message: str) -> dict:
            memory = load_memory()
            rule = message.strip()
            prefixes = ["hafızana yaz", "hafızaya yaz", "bunu unutma", "unutma", "remember that"]
            lower = rule.lower()
            for prefix in prefixes:
                if lower.startswith(prefix):
                    rule = rule[len(prefix):].strip(" :,-")
                    break
            if not rule:
                return {"success": False, "message": "Net bir kural çıkaramadım."}
            if rule not in memory["rules"]:
                memory["rules"].append(rule)
                save_memory(memory)
            return {"success": True, "message": "Kural hafızaya eklendi.", "rule": rule}
    ''')

    write_file(backend / "app/storage/entity_store.py", r'''
        from __future__ import annotations

        from datetime import datetime
        from pathlib import Path
        from typing import Any

        from app.services.text_utils import slugify
        from app.storage.json_store import load_json, save_json

        def list_items(path: Path) -> list[dict]:
            data = load_json(path, [])
            return data if isinstance(data, list) else []

        def save_items(path: Path, items: list[dict]) -> None:
            save_json(path, items)

        def unique_id(items: list[dict], base: str, fallback: str = "item") -> str:
            base_id = slugify(base, fallback)
            existing = {str(item.get("id", "")) for item in items}
            item_id = base_id
            counter = 2
            while item_id in existing:
                item_id = f"{base_id}-{counter}"
                counter += 1
            return item_id

        def upsert_item(path: Path, item: dict, fallback: str = "item") -> dict:
            items = list_items(path)
            item = dict(item)
            if not item.get("id"):
                item["id"] = unique_id(items, item.get("title") or item.get("name") or fallback, fallback)
            item.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
            for index, current in enumerate(items):
                if current.get("id") == item["id"]:
                    items[index] = {**current, **item}
                    save_items(path, items)
                    return item
            items.append(item)
            save_items(path, items)
            return item

        def delete_item(path: Path, item_id: str) -> bool:
            items = list_items(path)
            new_items = [item for item in items if str(item.get("id")) != item_id]
            save_items(path, new_items)
            return len(new_items) != len(items)

        def find_item(path: Path, item_id: str) -> dict | None:
            for item in list_items(path):
                if str(item.get("id")) == item_id:
                    return item
            return None

        def patch_item(path: Path, item_id: str, updates: dict[str, Any]) -> dict | None:
            items = list_items(path)
            for index, item in enumerate(items):
                if str(item.get("id")) == item_id:
                    items[index] = {**item, **updates}
                    save_items(path, items)
                    return items[index]
            return None
    ''')

    # Thin store modules
    store_map = {
        "project_store": "PROJECTS_PATH",
        "task_store": "TASKS_PATH",
        "approval_store": "APPROVALS_PATH",
        "output_store": "OUTPUTS_PATH",
        "reminder_store": "REMINDERS_PATH",
        "preference_store": "PREFERENCES_PATH",
    }
    for module, path_name in store_map.items():
        write_file(backend / f"app/storage/{module}.py", f"from app.core.paths import {path_name} as PATH\nfrom app.storage.entity_store import list_items, save_items, upsert_item, delete_item, find_item, patch_item\n")

    write_file(backend / "app/storage/workspace_store.py", r'''
        from __future__ import annotations

        from app.core.paths import ACTIVE_PROJECT_PATH, ACTIVE_TASK_PATH, APPROVALS_PATH, OUTPUTS_PATH, PROJECTS_PATH, TASKS_PATH
        from app.storage.entity_store import find_item, list_items
        from app.storage.json_store import load_json, save_json

        def get_active_project_id() -> str:
            data = load_json(ACTIVE_PROJECT_PATH, {"project_id": ""})
            return str(data.get("project_id", "")) if isinstance(data, dict) else ""

        def set_active_project_id(project_id: str) -> None:
            save_json(ACTIVE_PROJECT_PATH, {"project_id": project_id})

        def get_active_task_id() -> str:
            data = load_json(ACTIVE_TASK_PATH, {"task_id": ""})
            return str(data.get("task_id", "")) if isinstance(data, dict) else ""

        def set_active_task_id(task_id: str) -> None:
            save_json(ACTIVE_TASK_PATH, {"task_id": task_id})

        def summary() -> dict:
            projects = list_items(PROJECTS_PATH)
            tasks = list_items(TASKS_PATH)
            approvals = list_items(APPROVALS_PATH)
            outputs = list_items(OUTPUTS_PATH)
            active_project_id = get_active_project_id()
            active_project = find_item(PROJECTS_PATH, active_project_id) if active_project_id else None
            open_tasks = [t for t in tasks if t.get("status") != "tamamlandı"]
            high_priority_tasks = [t for t in open_tasks if t.get("priority") in ["yüksek", "kritik", "high", "critical"]]
            pending_approvals = [a for a in approvals if a.get("status") in ["bekliyor", "pending"]]
            return {
                "success": True,
                "active_project": active_project,
                "active_project_id": active_project_id,
                "counts": {
                    "active_projects": len([p for p in projects if p.get("status", "aktif") == "aktif"]),
                    "open_tasks": len(open_tasks),
                    "high_priority_tasks": len(high_priority_tasks),
                    "pending_approvals": len(pending_approvals),
                    "outputs": len(outputs),
                    "preferences": 0,
                },
                "active_projects": [p for p in projects if p.get("status", "aktif") == "aktif"],
                "open_tasks": open_tasks,
                "high_priority_tasks": high_priority_tasks,
                "pending_approvals": pending_approvals,
                "outputs": outputs,
                "suggested_next_step": high_priority_tasks[0]["title"] if high_priority_tasks else (open_tasks[0]["title"] if open_tasks else "Yeni bir görev oluştur veya aktif projeyi seç."),
            }

        def active_project_detail() -> dict:
            projects = list_items(PROJECTS_PATH)
            tasks = list_items(TASKS_PATH)
            approvals = list_items(APPROVALS_PATH)
            outputs = list_items(OUTPUTS_PATH)
            project_id = get_active_project_id()
            project = find_item(PROJECTS_PATH, project_id) if project_id else None
            project_tasks = [t for t in tasks if t.get("project_id") == project_id]
            open_tasks = [t for t in project_tasks if t.get("status") != "tamamlandı"]
            high_priority = [t for t in open_tasks if t.get("priority") in ["yüksek", "kritik", "high", "critical"]]
            project_approvals = [a for a in approvals if a.get("project_id") == project_id]
            pending = [a for a in project_approvals if a.get("status") in ["bekliyor", "pending"]]
            project_outputs = [o for o in outputs if o.get("project_id") == project_id]
            return {
                "success": True,
                "has_active_project": project is not None,
                "project_id": project_id,
                "project": project,
                "tasks": project_tasks,
                "open_tasks": open_tasks,
                "high_priority_tasks": high_priority,
                "approvals": project_approvals,
                "pending_approvals": pending,
                "outputs": project_outputs,
                "counts": {
                    "tasks": len(project_tasks),
                    "open_tasks": len(open_tasks),
                    "high_priority_tasks": len(high_priority),
                    "approvals": len(project_approvals),
                    "pending_approvals": len(pending),
                    "outputs": len(project_outputs),
                },
                "suggested_next_step": high_priority[0]["title"] if high_priority else (open_tasks[0]["title"] if open_tasks else "Bu proje için yeni görev oluştur."),
            }
    ''')

    write_file(backend / "app/services/gemini_service.py", r'''
        from __future__ import annotations

        from app.core.config import GEMINI_API_KEY
        from app.core.optional_imports import optional_import

        def generate_text(prompt: str) -> dict:
            if not GEMINI_API_KEY:
                return {"success": False, "message": "GEMINI_API_KEY tanımlı değil."}
            genai, error = optional_import("google.genai")
            if error:
                return {"success": False, "message": f"google-genai paketi kurulu değil: {error}"}
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                return {"success": True, "text": getattr(response, "text", "") or ""}
            except Exception as exc:
                return {"success": False, "message": f"Gemini isteği başarısız: {exc}"}
    ''')

    write_file(backend / "app/services/screenshot_service.py", r'''
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
    ''')

    write_file(backend / "app/services/speech_service.py", r'''
        from __future__ import annotations

        import tempfile
        import wave
        from pathlib import Path

        from app.core.config import MICROPHONE_DEVICE_INDEX, WHISPER_CHANNELS, WHISPER_MODEL_NAME, WHISPER_SAMPLE_RATE
        from app.core.optional_imports import optional_import

        whisper_model = None
        recording_stream = None
        recording_chunks = []
        is_recording_active = False

        def _imports():
            np, np_error = optional_import("numpy")
            sd, sd_error = optional_import("sounddevice")
            whisper_cls, whisper_error = optional_import("faster_whisper", "WhisperModel")
            errors = [e for e in [np_error, sd_error, whisper_error] if e]
            return np, sd, whisper_cls, errors

        def get_status() -> dict:
            _, _, _, errors = _imports()
            return {"available": not errors, "errors": errors}

        def _device_kwargs() -> dict:
            return {} if MICROPHONE_DEVICE_INDEX is None else {"device": MICROPHONE_DEVICE_INDEX}

        def _get_whisper_model():
            global whisper_model
            _, _, whisper_cls, errors = _imports()
            if errors:
                raise RuntimeError("; ".join(errors))
            if whisper_model is None:
                whisper_model = whisper_cls(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
            return whisper_model

        def _save_wav(np, audio_data, wav_path: str) -> None:
            if audio_data.ndim > 1:
                audio_data = audio_data.reshape(-1)
            clipped = np.clip(audio_data, -1.0, 1.0)
            int16_audio = (clipped * 32767).astype(np.int16)
            with wave.open(wav_path, "wb") as wav_file:
                wav_file.setnchannels(WHISPER_CHANNELS)
                wav_file.setsampwidth(2)
                wav_file.setframerate(WHISPER_SAMPLE_RATE)
                wav_file.writeframes(int16_audio.tobytes())

        def transcribe_audio_file(audio_path: str) -> dict:
            try:
                model = _get_whisper_model()
                segments, info = model.transcribe(audio_path, language="tr", beam_size=5, vad_filter=True)
                text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
                return {"success": True, "language": info.language, "language_probability": info.language_probability, "text": text}
            except Exception as exc:
                return {"success": False, "message": f"Ses yazıya çevrilemedi: {exc}", "text": ""}

        def start_recording() -> dict:
            global recording_stream, recording_chunks, is_recording_active
            np, sd, _, errors = _imports()
            if errors:
                return {"success": False, "message": "Speech modülü hazır değil: " + "; ".join(errors)}
            if is_recording_active:
                return {"success": True, "message": "Kayıt zaten aktif."}
            recording_chunks = []
            def callback(indata, frames, time, status):
                recording_chunks.append(indata.copy())
            try:
                recording_stream = sd.InputStream(samplerate=WHISPER_SAMPLE_RATE, channels=WHISPER_CHANNELS, dtype="float32", callback=callback, **_device_kwargs())
                recording_stream.start()
                is_recording_active = True
                return {"success": True, "message": "Kayıt başladı."}
            except Exception as exc:
                is_recording_active = False
                return {"success": False, "message": f"Kayıt başlatılamadı: {exc}"}

        def stop_and_transcribe() -> dict:
            global recording_stream, recording_chunks, is_recording_active
            np, _, _, errors = _imports()
            if errors:
                return {"success": False, "message": "Speech modülü hazır değil: " + "; ".join(errors), "text": ""}
            try:
                if recording_stream is not None:
                    recording_stream.stop()
                    recording_stream.close()
                recording_stream = None
                is_recording_active = False
                if not recording_chunks:
                    return {"success": False, "message": "Kayıt verisi bulunamadı.", "text": ""}
                audio_data = np.concatenate(recording_chunks, axis=0)
                recording_chunks = []
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    wav_path = tmp.name
                _save_wav(np, audio_data, wav_path)
                result = transcribe_audio_file(wav_path)
                Path(wav_path).unlink(missing_ok=True)
                return result
            except Exception as exc:
                is_recording_active = False
                return {"success": False, "message": f"Kayıt durdurulamadı: {exc}", "text": ""}

        def listen_and_transcribe(max_seconds: float = 20, silence_seconds: float = 1.2, peak_threshold: float = 0.025, average_threshold: float = 0.003) -> dict:
            np, sd, _, errors = _imports()
            if errors:
                return {"success": False, "message": "Speech modülü hazır değil: " + "; ".join(errors), "text": ""}
            try:
                duration = max(1.0, min(float(max_seconds), 60.0))
                audio = sd.rec(int(duration * WHISPER_SAMPLE_RATE), samplerate=WHISPER_SAMPLE_RATE, channels=WHISPER_CHANNELS, dtype="float32", **_device_kwargs())
                sd.wait()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    wav_path = tmp.name
                _save_wav(np, audio, wav_path)
                result = transcribe_audio_file(wav_path)
                Path(wav_path).unlink(missing_ok=True)
                return result
            except Exception as exc:
                return {"success": False, "message": f"Dinleme başarısız: {exc}", "text": ""}
    ''')

    write_file(backend / "app/services/screen_analysis_service.py", r'''
        from __future__ import annotations

        from app.services.gemini_service import generate_text
        from app.services.screenshot_service import capture_screenshot

        def analyze_screen(prompt: str) -> dict:
            shot = capture_screenshot()
            if not shot.get("success"):
                return shot
            ai = generate_text(f"Ekran görüntüsü alındı. Kullanıcı isteği: {prompt}\nNot: Bu geçici modül görseli modele göndermiyor, sadece screenshot durumunu raporluyor.")
            if ai.get("success"):
                return {"success": True, "analysis": ai.get("text") or "Screenshot alındı."}
            return {"success": True, "analysis": "Screenshot alındı ama Gemini analizi yapılamadı: " + ai.get("message", "Bilinmeyen hata")}
    ''')

    write_file(backend / "app/services/site_service.py", r'''
        from __future__ import annotations

        from urllib.parse import urljoin

        import requests
        from bs4 import BeautifulSoup

        def analyze_site(url: str, prompt: str = "") -> dict:
            if not url:
                return {"success": False, "message": "URL boş."}
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            try:
                response = requests.get(url, timeout=15, headers={"User-Agent": "VexBot/0.2"})
                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.title.get_text(strip=True) if soup.title else ""
                description_tag = soup.find("meta", attrs={"name": "description"})
                description = description_tag.get("content", "") if description_tag else ""
                h1s = [h.get_text(strip=True) for h in soup.find_all("h1")[:5]]
                return {"success": True, "analysis": f"Başlık: {title}\nMeta açıklama: {description}\nH1: {', '.join(h1s) or 'Bulunamadı'}\nHTTP: {response.status_code}"}
            except Exception as exc:
                return {"success": False, "message": f"Site analiz edilemedi: {exc}"}

        def find_products(url: str, query: str = "", language: str = "Turkish", max_pages: int = 40) -> dict:
            if not url:
                return {"success": False, "message": "URL boş."}
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            try:
                response = requests.get(url, timeout=15, headers={"User-Agent": "VexBot/0.2"})
                soup = BeautifulSoup(response.text, "html.parser")
                links = []
                for a in soup.find_all("a", href=True):
                    text = a.get_text(" ", strip=True)
                    href = urljoin(url, a["href"])
                    if text and any(word in href.lower() for word in ["product", "urun", "produkt", "collections", "shop"]):
                        links.append({"title": text[:120], "url": href})
                    if len(links) >= 20:
                        break
                formatted = "\n".join(f"- {item['title']}: {item['url']}" for item in links) or "Ürün linki bulunamadı."
                return {"success": True, "products": links, "formatted_output": formatted}
            except Exception as exc:
                return {"success": False, "message": f"Ürün araması başarısız: {exc}"}
    ''')

    write_file(backend / "app/services/shopify_service.py", r'''
        from __future__ import annotations

        def create_content_from_chat(message: str, project_id: str = "", task_id: str = "", language: str = "English") -> dict:
            title = message.strip()[:80] or "Shopify İçeriği"
            output = f"Başlık: {title}\n\nAçıklama:\n{message.strip()}\n\nSEO Meta Title:\n{title}\n\nSEO Meta Description:\n{message.strip()[:150]}"
            return {"success": True, "formatted_output": output, "message": "Shopify içerik taslağı hazırlandı."}
    ''')

    write_file(backend / "app/services/computer_service.py", r'''
        from __future__ import annotations

        from datetime import datetime

        from app.core.paths import COMPUTER_LOGS_PATH
        from app.services.screenshot_service import capture_screenshot
        from app.storage.json_store import load_json, save_json

        state = {
            "running": False,
            "active_task_id": None,
            "last_intent": "unknown",
            "last_action": "none",
            "manual_pending_action": None,
        }

        def add_log(message: str) -> None:
            logs = load_json(COMPUTER_LOGS_PATH, [])
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            save_json(COMPUTER_LOGS_PATH, logs[-200:])

        def status() -> dict:
            result = {"success": True, **state}
            if state.get("running"):
                result["screenshot"] = capture_screenshot()
            return result

        def logs() -> dict:
            return {"success": True, "logs": load_json(COMPUTER_LOGS_PATH, [])}

        def plan(instruction: str) -> dict:
            state["last_intent"] = instruction or "unknown"
            add_log(f"Plan istendi: {instruction}")
            return {"success": True, "plan": ["Ekranı analiz et", "Riskli aksiyon varsa onay iste", "Güvenli aksiyonu uygula"], "message": "Plan hazır."}

        def start(instruction: str = "") -> dict:
            state["running"] = True
            state["active_task_id"] = f"computer-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            state["last_intent"] = instruction or "manual"
            state["last_action"] = "started"
            add_log(f"Computer-use başladı: {instruction}")
            return {"success": True, "message": "Computer-use başlatıldı.", **state}

        def stop() -> dict:
            state["running"] = False
            state["last_action"] = "stopped"
            add_log("Computer-use durduruldu.")
            return {"success": True, "message": "Computer-use durduruldu.", **state}
    ''')

    write_file(backend / "app/services/evolution_service.py", r'''
        from __future__ import annotations

        from datetime import datetime

        from app.core.paths import EVOLUTION_LOGS_PATH, EVOLUTION_PENDING_PATH
        from app.storage.json_store import load_json, save_json

        running = False

        def get_logs() -> dict:
            return {"success": True, "logs": load_json(EVOLUTION_LOGS_PATH, [])}

        def add_log(message: str) -> None:
            logs = load_json(EVOLUTION_LOGS_PATH, [])
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            save_json(EVOLUTION_LOGS_PATH, logs[-300:])

        def reset_logs() -> dict:
            save_json(EVOLUTION_LOGS_PATH, [])
            return {"success": True, "message": "Evrim logları sıfırlandı."}

        def status() -> dict:
            return {"success": True, "running": running}

        def pending_actions() -> dict:
            return {"success": True, "pending_actions": load_json(EVOLUTION_PENDING_PATH, [])}

        def start_prompt(prompt: str) -> dict:
            global running
            running = True
            add_log(f"Evrim prompt alındı: {prompt}")
            actions = load_json(EVOLUTION_PENDING_PATH, [])
            action = {"id": f"evo-{datetime.now().strftime('%Y%m%d%H%M%S')}", "title": "Önerilen güvenli refactor", "description": prompt, "risk_level": "manual_review", "status": "pending"}
            actions.append(action)
            save_json(EVOLUTION_PENDING_PATH, actions)
            running = False
            return {"success": True, "message": "Evrim önerisi bekleyen işlemlere eklendi.", "action": action}

        def approve(action_id: str) -> dict:
            actions = load_json(EVOLUTION_PENDING_PATH, [])
            for action in actions:
                if action.get("id") == action_id:
                    action["status"] = "approved"
                    add_log(f"İşlem onaylandı: {action_id}")
            save_json(EVOLUTION_PENDING_PATH, actions)
            return {"success": True, "message": "İşlem onaylandı."}

        def reject(action_id: str) -> dict:
            actions = load_json(EVOLUTION_PENDING_PATH, [])
            for action in actions:
                if action.get("id") == action_id:
                    action["status"] = "rejected"
                    add_log(f"İşlem reddedildi: {action_id}")
            save_json(EVOLUTION_PENDING_PATH, actions)
            return {"success": True, "message": "İşlem reddedildi."}
    ''')

    # Routes
    write_file(backend / "app/routes/health.py", r'''
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
    ''')

    write_file(backend / "app/routes/memory.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.schemas.common import MessageRequest
        from app.storage.memory_store import add_rule_from_message, load_memory

        router = APIRouter()

        @router.get("/memory")
        def get_memory():
            return load_memory()

        @router.post("/memory/rules/from-chat")
        def memory_from_chat(request: MessageRequest):
            return add_rule_from_message(request.message)
    ''')

    write_file(backend / "app/routes/projects.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.core.paths import PROJECTS_PATH
        from app.schemas.common import MessageRequest, ProjectRequest
        from app.services.text_utils import slugify
        from app.storage.entity_store import delete_item, list_items, upsert_item

        router = APIRouter()

        @router.get("/projects")
        def get_projects():
            return list_items(PROJECTS_PATH)

        @router.post("/projects")
        def create_project(request: ProjectRequest):
            data = request.model_dump()
            if not data.get("id"):
                data["id"] = slugify(data.get("name", "proje"), "proje")
            return upsert_item(PROJECTS_PATH, data, "proje")

        @router.delete("/projects/{project_id}")
        def delete_project(project_id: str):
            return {"success": delete_item(PROJECTS_PATH, project_id), "message": "Proje silindi."}

        @router.post("/projects/from-chat")
        def create_project_from_chat(request: MessageRequest):
            name = request.message.strip()[:80] or "Yeni Proje"
            project = upsert_item(PROJECTS_PATH, {"name": name, "type": "Genel proje", "status": "aktif", "description": request.message, "main_goals": [], "notes": ["Sohbetten oluşturuldu."]}, "proje")
            return {"success": True, "message": "Proje oluşturuldu.", "project": project, "projects": list_items(PROJECTS_PATH), "source_message": request.message}
    ''')

    write_file(backend / "app/routes/tasks.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from pydantic import BaseModel
        from app.core.paths import TASKS_PATH
        from app.schemas.common import TaskRequest
        from app.storage.entity_store import delete_item, list_items, patch_item, upsert_item

        router = APIRouter()

        class TaskFromChatRequest(BaseModel):
            message: str = ""
            project_id: str = ""

        @router.get("/tasks")
        def get_tasks():
            return list_items(TASKS_PATH)

        @router.post("/tasks/from-chat")
        def create_task_from_chat(request: TaskFromChatRequest):
            task = upsert_item(TASKS_PATH, {"title": request.message.strip()[:80] or "Yeni Görev", "project_id": request.project_id, "status": "açık", "priority": "normal", "description": request.message, "notes": ["Sohbetten oluşturuldu."]}, "gorev")
            return {"success": True, "message": "Görev oluşturuldu.", "task": task, "tasks": list_items(TASKS_PATH), "source_message": request.message}

        @router.patch("/tasks/{task_id}/complete")
        def complete_task(task_id: str):
            task = patch_item(TASKS_PATH, task_id, {"status": "tamamlandı"})
            return {"success": task is not None, "message": "Görev tamamlandı.", "task": task, "tasks": list_items(TASKS_PATH)}

        @router.delete("/tasks/{task_id}")
        def delete_task(task_id: str):
            return {"success": delete_item(TASKS_PATH, task_id), "message": "Görev silindi."}
    ''')

    write_file(backend / "app/routes/approvals.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.core.paths import APPROVALS_PATH
        from app.schemas.common import ApprovalRequest, MessageRequest
        from app.storage.entity_store import delete_item, list_items, patch_item, upsert_item

        router = APIRouter()

        @router.get("/approvals")
        def get_approvals():
            return list_items(APPROVALS_PATH)

        @router.post("/approvals/from-chat")
        def create_approval_from_chat(request: MessageRequest):
            approval = upsert_item(APPROVALS_PATH, {"title": request.message.strip()[:80] or "Onay İsteği", "action_type": "genel", "risk_level": "normal", "status": "bekliyor", "description": request.message, "payload": {}, "notes": ["Sohbetten oluşturuldu."]}, "onay")
            return {"success": True, "message": "Onay isteği oluşturuldu.", "approval": approval, "approvals": list_items(APPROVALS_PATH), "source_message": request.message}

        @router.patch("/approvals/{approval_id}/approve")
        def approve_approval(approval_id: str):
            approval = patch_item(APPROVALS_PATH, approval_id, {"status": "onaylandı"})
            return {"success": approval is not None, "message": "Onaylandı.", "approval": approval}

        @router.patch("/approvals/{approval_id}/reject")
        def reject_approval(approval_id: str):
            approval = patch_item(APPROVALS_PATH, approval_id, {"status": "reddedildi"})
            return {"success": approval is not None, "message": "Reddedildi.", "approval": approval}

        @router.delete("/approvals/{approval_id}")
        def delete_approval(approval_id: str):
            return {"success": delete_item(APPROVALS_PATH, approval_id), "message": "Onay isteği silindi."}
    ''')

    write_file(backend / "app/routes/outputs.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.core.paths import OUTPUTS_PATH
        from app.schemas.common import OutputRequest
        from app.storage.entity_store import delete_item, list_items, upsert_item

        router = APIRouter()

        @router.get("/outputs")
        def get_outputs():
            return list_items(OUTPUTS_PATH)

        @router.post("/outputs/from-chat")
        def create_output_from_chat(request: OutputRequest):
            output = upsert_item(OUTPUTS_PATH, request.model_dump(), "cikti")
            return {"success": True, "message": "Çıktı kaydedildi.", "output": output, "outputs": list_items(OUTPUTS_PATH)}

        @router.delete("/outputs/{output_id}")
        def delete_output(output_id: str):
            return {"success": delete_item(OUTPUTS_PATH, output_id), "message": "Çıktı silindi."}
    ''')

    write_file(backend / "app/routes/reminders.py", r'''
        from __future__ import annotations

        from datetime import datetime

        from fastapi import APIRouter
        from app.core.paths import REMINDERS_PATH
        from app.schemas.common import ReminderDueRequest, ReminderFromChatRequest
        from app.services.text_utils import parse_reminder_time
        from app.storage.entity_store import delete_item, list_items, patch_item, upsert_item

        router = APIRouter()

        @router.get("/reminders")
        def get_reminders():
            return list_items(REMINDERS_PATH)

        @router.post("/reminders/from-chat")
        def create_reminder_from_chat(request: ReminderFromChatRequest):
            reminder = upsert_item(REMINDERS_PATH, {"title": request.message.strip()[:100] or "Hatırlatma", "remind_at": parse_reminder_time(request.message), "project_id": request.project_id, "task_id": request.task_id, "status": "active", "notified": False, "notes": ["Sohbetten oluşturuldu."]}, "hatirlatma")
            return {"success": True, "message": "Hatırlatma oluşturuldu.", "reminder": reminder, "reminders": list_items(REMINDERS_PATH)}

        @router.post("/reminders/due")
        def due_reminders(request: ReminderDueRequest):
            now = datetime.now()
            due = []
            for item in list_items(REMINDERS_PATH):
                try:
                    remind_at = datetime.fromisoformat(str(item.get("remind_at", "")))
                except Exception:
                    continue
                if item.get("status") == "active" and not item.get("notified") and remind_at <= now:
                    due.append(item)
                    if request.mark_as_notified:
                        patch_item(REMINDERS_PATH, item["id"], {"notified": True})
            return {"success": True, "due_reminders": due}

        @router.delete("/reminders/{reminder_id}")
        def delete_reminder(reminder_id: str):
            return {"success": delete_item(REMINDERS_PATH, reminder_id), "message": "Hatırlatma silindi."}
    ''')

    write_file(backend / "app/routes/workspace.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.core.paths import PROJECTS_PATH, TASKS_PATH
        from app.schemas.common import ActiveProjectRequest, ActiveTaskRequest
        from app.storage.entity_store import find_item
        from app.storage.workspace_store import active_project_detail, get_active_project_id, get_active_task_id, set_active_project_id, set_active_task_id, summary

        router = APIRouter()

        @router.get("/workspace/summary")
        def workspace_summary():
            return summary()

        @router.get("/workspace/active-project")
        def get_active_project():
            project_id = get_active_project_id()
            return {"success": True, "project_id": project_id, "project": find_item(PROJECTS_PATH, project_id) if project_id else None}

        @router.post("/workspace/active-project")
        def set_active_project(request: ActiveProjectRequest):
            set_active_project_id(request.project_id)
            return {"success": True, "message": "Aktif proje güncellendi.", "project_id": request.project_id, "project": find_item(PROJECTS_PATH, request.project_id)}

        @router.get("/workspace/active-task")
        def get_active_task():
            task_id = get_active_task_id()
            return {"success": True, "task_id": task_id, "task": find_item(TASKS_PATH, task_id) if task_id else None}

        @router.post("/workspace/active-task")
        def set_active_task(request: ActiveTaskRequest):
            set_active_task_id(request.task_id)
            return {"success": True, "message": "Aktif görev güncellendi.", "task_id": request.task_id, "task": find_item(TASKS_PATH, request.task_id)}

        @router.get("/workspace/active-project/detail")
        def get_active_project_detail():
            return active_project_detail()
    ''')

    write_file(backend / "app/routes/chat.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.schemas.common import ChatRequest
        from app.services.gemini_service import generate_text
        from app.storage.memory_store import load_memory

        router = APIRouter()

        @router.post("/chat")
        def chat(request: ChatRequest):
            memory = load_memory()
            rules = "\n".join(f"- {rule}" for rule in memory.get("rules", []))
            prompt = f"Sen Vex'sin, Mert'in kişisel yapay zeka iş arkadaşısın. Kısa, net ve pratik cevap ver.\nKurallar:\n{rules}\n\nMert: {request.message}\nVex:"
            result = generate_text(prompt)
            if result.get("success"):
                return {"success": True, "reply": result.get("text") or "Tamam Mert."}
            return {"success": True, "reply": f"Backend çalışıyor Mert. Gemini hazır değil: {result.get('message')}"}
    ''')

    write_file(backend / "app/routes/speech.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.schemas.common import ListenSpeechRequest
        from app.services import speech_service

        router = APIRouter()

        @router.post("/speech/record/start")
        def speech_start():
            return speech_service.start_recording()

        @router.post("/speech/record/stop-and-transcribe")
        def speech_stop_and_transcribe():
            return speech_service.stop_and_transcribe()

        @router.post("/speech/listen-and-transcribe")
        def speech_listen(request: ListenSpeechRequest):
            return speech_service.listen_and_transcribe(request.max_seconds, request.silence_seconds, request.peak_threshold, request.average_threshold)
    ''')

    write_file(backend / "app/routes/screen.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.schemas.common import ScreenAnalyzeRequest
        from app.services.screen_analysis_service import analyze_screen

        router = APIRouter()

        @router.post("/screen/capture-and-analyze")
        def capture_and_analyze(request: ScreenAnalyzeRequest):
            return analyze_screen(request.prompt)
    ''')

    write_file(backend / "app/routes/computer.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.schemas.common import ComputerPlanRequest
        from app.services.computer_service import logs, plan, start, status, stop
        from app.services.screenshot_service import capture_screenshot

        router = APIRouter()

        @router.get("/computer/screenshot")
        def computer_screenshot():
            return capture_screenshot()

        @router.get("/computer/status")
        def computer_status():
            return status()

        @router.get("/computer/logs")
        def computer_logs():
            return logs()

        @router.post("/computer/plan")
        def computer_plan(request: ComputerPlanRequest):
            return plan(request.instruction)

        @router.post("/computer/start")
        def computer_start(request: ComputerPlanRequest | None = None):
            return start(request.instruction if request else "")

        @router.post("/computer/stop")
        def computer_stop():
            return stop()

        @router.post("/computer/approve-action")
        def computer_approve_action():
            return {"success": True, "message": "Manuel aksiyon onaylandı."}

        @router.post("/computer/reject-action")
        def computer_reject_action():
            return {"success": True, "message": "Manuel aksiyon reddedildi."}
    ''')

    write_file(backend / "app/routes/site.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.schemas.common import SiteProductFinderRequest, UrlAnalyzeRequest
        from app.services.site_service import analyze_site, find_products

        router = APIRouter()

        @router.post("/site/analyze")
        def site_analyze(request: UrlAnalyzeRequest):
            return analyze_site(request.url, request.prompt)

        @router.post("/site/find-products")
        def site_find_products(request: SiteProductFinderRequest):
            return find_products(request.url, request.query, request.language, request.max_pages)
    ''')

    write_file(backend / "app/routes/shopify.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from app.schemas.common import ShopifyContentFromChatRequest
        from app.services.shopify_service import create_content_from_chat

        router = APIRouter()

        @router.post("/shopify/content-from-chat")
        def shopify_content_from_chat(request: ShopifyContentFromChatRequest):
            return create_content_from_chat(request.message, request.project_id, request.task_id, request.language)
    ''')

    write_file(backend / "app/routes/evolution.py", r'''
        from __future__ import annotations

        from fastapi import APIRouter
        from pydantic import BaseModel
        from app.services import evolution_service

        router = APIRouter()

        class EvolutionPromptRequest(BaseModel):
            prompt: str = ""
            message: str = ""

        @router.get("/evolution/logs")
        def evolution_logs():
            return evolution_service.get_logs()

        @router.get("/evolution/status")
        def evolution_status():
            return evolution_service.status()

        @router.get("/evolution/pending-actions")
        def evolution_pending_actions():
            return evolution_service.pending_actions()

        @router.post("/evolution/reset-logs")
        def evolution_reset_logs():
            return evolution_service.reset_logs()

        @router.post("/evolution/prompt")
        def evolution_prompt(request: EvolutionPromptRequest):
            return evolution_service.start_prompt(request.prompt or request.message)

        @router.post("/evolution/approve-action/{action_id}")
        def evolution_approve(action_id: str):
            return evolution_service.approve(action_id)

        @router.post("/evolution/reject-action/{action_id}")
        def evolution_reject(action_id: str):
            return evolution_service.reject(action_id)
    ''')

    write_file(backend / "requirements.txt", r'''
        fastapi
        uvicorn[standard]
        requests
        python-dotenv
        google-genai
        python-multipart
        pydantic
        pillow
        mss
        pyautogui
        numpy
        sounddevice
        scipy
        faster-whisper
        beautifulsoup4
        lxml
        aiofiles
        python-dateutil
        psutil
        pynput
    ''')

    write_file(backend / ".env.example", r'''
        GEMINI_API_KEY=BURAYA_GEMINI_API_KEY_GELECEK
        WHISPER_MODEL_NAME=small
        WHISPER_SAMPLE_RATE=16000
        WHISPER_CHANNELS=1
        MICROPHONE_DEVICE_INDEX=
    ''')

    write_file(root / ".gitignore", r'''
        # Secrets
        .env
        .env.*
        *.env

        # Node
        node_modules/
        dist/
        build/
        npm-debug.log*
        yarn-debug.log*
        yarn-error.log*

        # Python virtual environments
        .venv/
        venv/
        *.venv/
        .venv*/
        venv*/
        vex-backend/.venv*
        vex-backend/venv*
        vex-backend/.venvcd/

        # Python cache
        __pycache__/
        *.pyc
        .pytest_cache/
        .mypy_cache/

        # Tauri / Rust
        target/
        src-tauri/target/
        vex-app/src-tauri/target/

        # OS
        .DS_Store

        # Logs / runtime files
        *.log
        logs/
        screenshots/
        recordings/
        audio/
        uploads/
        downloads/
        models/
        vex-backend/screenshots/
        vex-backend/recordings/
        vex-backend/audio/
        vex-backend/uploads/
        vex-backend/downloads/
        vex-backend/models/
    ''')

    write_file(root / "PROJECT_CONTEXT.md", r'''
        # Vex Project Context

        Vex, Mert'in kişisel yapay zeka iş arkadaşıdır.

        ## Mimari

        - Frontend: `vex-app` — React + TypeScript + Vite/Tauri
        - Backend: `vex-backend` — FastAPI
        - Backend portu: `127.0.0.1:8000`

        ## Modüler Backend Kuralları

        - `main.py` sadece app oluşturur ve router include eder.
        - Ağır/opsiyonel importlar `main.py` içinde yapılmaz.
        - Gemini, Whisper, sounddevice, mss ve pyautogui eksikse backend çökmez; sadece ilgili endpoint anlamlı hata döner.
        - JSON storage korunur. Veritabanına geçiş sonraki aşamadır.

        ## Çalıştırma

        ```bash
        cd /Users/mert/Vex/vex-backend
        source .venv/bin/activate
        uvicorn main:app --reload --host 127.0.0.1 --port 8000
        ```

        ## Test

        ```bash
        curl -i http://127.0.0.1:8000/health
        curl -i http://127.0.0.1:8000/computer/status
        curl -i http://127.0.0.1:8000/computer/screenshot
        ```
    ''')

    print("\nModüler backend dosyaları yazıldı.")
    print("\nSonraki komutlar:")
    print("cd", backend)
    print("deactivate 2>/dev/null || true")
    print("rm -rf .venv venv .venvcd")
    print("uv python install 3.12")
    print("uv venv .venv --python 3.12 --seed")
    print("source .venv/bin/activate")
    print("uv pip install -r requirements.txt")
    print("python -m compileall app main.py")
    print("uvicorn main:app --reload --host 127.0.0.1 --port 8000")


if __name__ == "__main__":
    main()
