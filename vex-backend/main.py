import json
import os
import queue
import re
import tempfile
from datetime import datetime, timedelta
import requests
import mss
import traceback
import time
import wave
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Vex Backend")

MEMORY_PATH = Path("memory.json")
SCREENSHOTS_PATH = Path("screenshots")
REMINDERS_PATH = Path("reminders.json")
PROJECTS_PATH = Path("projects.json")
TASKS_PATH = Path("tasks.json")
APPROVALS_PATH = Path("approvals.json")
ACTIVE_PROJECT_PATH = Path("active_project.json")
ACTIVE_TASK_PATH = Path("active_task.json")
OUTPUTS_PATH = Path("outputs.json")
PREFERENCES_PATH = Path("preferences.json")

WHISPER_MODEL_NAME = "small"
WHISPER_SAMPLE_RATE = 16000
WHISPER_CHANNELS = 1

# None = sistemin varsayılan mikrofonunu kullanır.
# Sabit index kullanmıyoruz çünkü cihaz index'i değişebiliyor.
MICROPHONE_DEVICE_INDEX = None

whisper_model: WhisperModel | None = None

recording_stream: sd.InputStream | None = None
recording_chunks: list[np.ndarray] = []
is_recording_active = False

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


class ChatMessage(BaseModel):
    sender: str
    text: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ShopifyContentFromChatRequest(BaseModel):
    message: str
    project_id: str = ""
    task_id: str = ""
    language: str = "English"


class ScreenAnalyzeRequest(BaseModel):
    prompt: str = "Ekranda ne olduğunu analiz et."


class ComputerPlanRequest(BaseModel):
    instruction: str


class UrlAnalyzeRequest(BaseModel):
    url: str
    prompt: str = "Siteyi SEO, tasarım, içerik ve güven algısı açısından analiz et."


class SiteProductFinderRequest(BaseModel):
    url: str
    query: str
    language: str = "Turkish"
    max_pages: int = 40


class ReminderRequest(BaseModel):
    id: str = ""
    title: str
    remind_at: str
    project_id: str = ""
    task_id: str = ""
    status: str = "active"
    notes: list[str] = []


class ReminderFromChatRequest(BaseModel):
    message: str
    project_id: str = ""
    task_id: str = ""


class ReminderDueRequest(BaseModel):
    mark_as_notified: bool = True


class MemoryRuleRequest(BaseModel):
    rule: str


class MemoryFromChatRequest(BaseModel):
    message: str


class ProjectRequest(BaseModel):
    id: str
    name: str
    type: str = "Genel proje"
    status: str = "aktif"
    description: str = ""
    main_goals: list[str] = []
    notes: list[str] = []


class ProjectFromChatRequest(BaseModel):
    message: str


class TaskRequest(BaseModel):
    id: str = ""
    title: str
    project_id: str = ""
    status: str = "açık"
    priority: str = "normal"
    description: str = ""
    notes: list[str] = []


class TaskFromChatRequest(BaseModel):
    message: str
    project_id: str = ""


class ApprovalRequest(BaseModel):
    id: str = ""
    title: str
    project_id: str = ""
    action_type: str = "genel"
    risk_level: str = "normal"
    status: str = "bekliyor"
    description: str = ""
    payload: dict = {}
    notes: list[str] = []


class ApprovalFromChatRequest(BaseModel):
    message: str
    project_id: str = ""


class ActiveProjectRequest(BaseModel):
    project_id: str


class ActiveTaskRequest(BaseModel):
    task_id: str


class OutputRequest(BaseModel):
    id: str = ""
    title: str
    project_id: str = ""
    task_id: str = ""
    output_type: str = "genel"
    content: str
    status: str = "taslak"
    notes: list[str] = []


class OutputFromChatRequest(BaseModel):
    title: str = ""
    content: str
    output_type: str = "genel"


class PreferenceRequest(BaseModel):
    id: str = ""
    project_id: str = ""
    task_id: str = ""
    category: str = "genel"
    preference: str
    source: str = "manual"
    confidence: str = "medium"
    status: str = "active"


class PreferenceFromChatRequest(BaseModel):
    message: str
    project_id: str = ""
    task_id: str = ""


class RecordSpeechRequest(BaseModel):
    duration_seconds: float = 5


class ListenSpeechRequest(BaseModel):
    max_seconds: float = 20
    silence_seconds: float = 1.2
    peak_threshold: float = 0.025
    average_threshold: float = 0.003


def get_microphone_device_kwargs() -> dict:
    if MICROPHONE_DEVICE_INDEX is None:
        return {}

    return {"device": MICROPHONE_DEVICE_INDEX}


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    return genai.Client(api_key=api_key)


def get_whisper_model() -> WhisperModel:
    global whisper_model

    if whisper_model is None:
        print(f"Vex STT modeli yükleniyor: {WHISPER_MODEL_NAME}")
        whisper_model = WhisperModel(
            WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8",
        )
        print("Vex STT modeli hazır.")

    return whisper_model


def transcribe_audio_file(audio_path: str) -> dict:
    model = get_whisper_model()

    segments, info = model.transcribe(
        audio_path,
        language="tr",
        beam_size=5,
        vad_filter=True,
    )

    text_parts = [segment.text.strip() for segment in segments]
    text = " ".join(part for part in text_parts if part).strip()

    return {
        "success": True,
        "language": info.language,
        "language_probability": info.language_probability,
        "text": text,
    }


def save_recording_to_wav(audio_data: np.ndarray, wav_path: str) -> None:
    if audio_data.ndim > 1:
        audio_data = audio_data.reshape(-1)

    clipped_audio = np.clip(audio_data, -1.0, 1.0)
    int16_audio = (clipped_audio * 32767).astype(np.int16)

    with wave.open(wav_path, "wb") as wav_file:
        wav_file.setnchannels(WHISPER_CHANNELS)
        wav_file.setsampwidth(2)
        wav_file.setframerate(WHISPER_SAMPLE_RATE)
        wav_file.writeframes(int16_audio.tobytes())


def slugify(text: str) -> str:
    text = text.strip().lower()

    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
        "İ": "i",
        "Ğ": "g",
        "Ü": "u",
        "Ş": "s",
        "Ö": "o",
        "Ç": "c",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")

    return text or "proje"


def clean_json_text(text: str) -> str:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace:last_brace + 1]

    return cleaned


def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return {
            "user": {
                "name": "Mert",
                "preferred_name": "Mert"
            },
            "assistant": {
                "name": "Vex",
                "role": "Mert'in kişisel yapay zeka iş arkadaşı",
                "tone": "samimi, pratik, doğal, iş odaklı"
            },
            "project": {
                "name": "Vex",
                "motto": "Basit MVP değil; baştan en iyi versiyon kurulacak.",
                "cost_principle": "Minimum para harcayarak, açık kaynak ve local-first mimariyle en iyi sistem hedeflenecek.",
                "interface_principle": "Telegram gibi basit botlar kullanılmayacak; özel masaüstü program geliştirilecek.",
                "development_machine": "Mac",
                "target_platforms": ["macOS", "Windows"]
            },
            "ai": {
                "primary_model_provider": "Gemini API",
                "fallback_strategy": "Gerekirse ileride başka modeller veya local modeller eklenebilir."
            },
            "work_domains": [
                "tasarım",
                "Shopify site yönetimi",
                "site kurulumu",
                "dosya düzenleme",
                "çeviri",
                "görsel düzenleme",
                "proje takibi"
            ],
            "rules": []
        }

    with MEMORY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_memory(memory: dict) -> None:
    with MEMORY_PATH.open("w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)


def load_projects() -> list[dict]:
    if not PROJECTS_PATH.exists():
        return []

    with PROJECTS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_projects(projects: list[dict]) -> None:
    with PROJECTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(projects, file, ensure_ascii=False, indent=2)



def load_tasks() -> list[dict]:
    if not TASKS_PATH.exists():
        return []

    with TASKS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_tasks(tasks: list[dict]) -> None:
    with TASKS_PATH.open("w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=2)


def normalize_task_data(task_data: dict) -> dict:
    title = str(task_data.get("title", "")).strip()

    if not title:
        title = "Yeni Görev"

    task_id = str(task_data.get("id", "")).strip()

    if not task_id:
        task_id = slugify(title)
    else:
        task_id = slugify(task_id)

    notes = task_data.get("notes", [])

    if not isinstance(notes, list):
        notes = [str(notes)]

    return {
        "id": task_id,
        "title": title,
        "project_id": str(task_data.get("project_id", "")).strip(),
        "status": str(task_data.get("status", "açık")).strip() or "açık",
        "priority": str(task_data.get("priority", "normal")).strip() or "normal",
        "description": str(task_data.get("description", "")).strip(),
        "notes": [str(item).strip() for item in notes if str(item).strip()],
    }


def add_task_to_storage(task_data: dict) -> dict:
    normalized_task = normalize_task_data(task_data)

    tasks_data = load_tasks()

    existing_ids = {task.get("id") for task in tasks_data}
    base_id = normalized_task["id"]
    counter = 2

    while normalized_task["id"] in existing_ids:
        normalized_task["id"] = f"{base_id}-{counter}"
        counter += 1

    tasks_data.append(normalized_task)
    save_tasks(tasks_data)

    return {
        "success": True,
        "message": "Görev başarıyla eklendi.",
        "task": normalized_task,
        "tasks": tasks_data,
    }


def extract_task_from_chat(message: str, project_id: str = "") -> dict:
    client = get_gemini_client()

    if client is None:
        return normalize_task_data({
            "title": message.strip()[:80] or "Yeni Görev",
            "project_id": project_id,
            "status": "açık",
            "priority": "normal",
            "description": message.strip(),
            "notes": [
                "Bu görev Gemini API key olmadan basit çıkarımla oluşturuldu."
            ],
        })

    projects_data = load_projects()
    projects_text = json.dumps(projects_data, ensure_ascii=False, indent=2)

    prompt = f"""
Sen Vex'in görev oluşturma modülüsün.

Mert'in mesajından yapılacak görevi çıkar.

Sadece geçerli JSON döndür.
Markdown, açıklama veya ekstra metin yazma.

Kayıtlı projeler:
{projects_text}

JSON şeması:
{{
  "id": "kebab-case-gorev-id",
  "title": "Görev başlığı",
  "project_id": "ilgili-proje-id-yoksa-boş",
  "status": "açık",
  "priority": "düşük | normal | yüksek | kritik",
  "description": "Görev açıklaması",
  "notes": ["Not 1", "Not 2"]
}}

Kurallar:
- Mesaj Türkçe ise alanlar Türkçe olsun.
- project_id net değilse boş bırak.
- Eğer mesajda Bilsanpack geçiyorsa project_id "bilsanpack" olsun.
- Eğer mesajda AirPack Europe geçiyorsa project_id "airpack-europe" olsun.
- title kısa ve yapılabilir bir iş başlığı olsun.
- status varsayılan olarak "açık" olsun.
- priority net değilse "normal" olsun.

Mert'in mesajı:
{message}

Varsayılan proje id:
{project_id}
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    raw_text = response.text or "{}"
    json_text = clean_json_text(raw_text)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        parsed = {
            "title": message.strip()[:80] or "Yeni Görev",
            "project_id": project_id,
            "status": "açık",
            "priority": "normal",
            "description": message.strip(),
            "notes": [
                "Gemini çıktısı JSON olarak okunamadığı için basit görev kaydı oluşturuldu."
            ],
        }

    return normalize_task_data(parsed)



def load_approvals() -> list[dict]:
    if not APPROVALS_PATH.exists():
        return []

    with APPROVALS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_approvals(approvals: list[dict]) -> None:
    with APPROVALS_PATH.open("w", encoding="utf-8") as file:
        json.dump(approvals, file, ensure_ascii=False, indent=2)


def normalize_approval_data(approval_data: dict) -> dict:
    title = str(approval_data.get("title", "")).strip()

    if not title:
        title = "Yeni Onay"

    approval_id = str(approval_data.get("id", "")).strip()

    if not approval_id:
        approval_id = slugify(title)
    else:
        approval_id = slugify(approval_id)

    notes = approval_data.get("notes", [])
    payload = approval_data.get("payload", {})

    if not isinstance(notes, list):
        notes = [str(notes)]

    if not isinstance(payload, dict):
        payload = {}

    return {
        "id": approval_id,
        "title": title,
        "project_id": str(approval_data.get("project_id", "")).strip(),
        "action_type": str(approval_data.get("action_type", "genel")).strip() or "genel",
        "risk_level": str(approval_data.get("risk_level", "normal")).strip() or "normal",
        "status": str(approval_data.get("status", "bekliyor")).strip() or "bekliyor",
        "description": str(approval_data.get("description", "")).strip(),
        "payload": payload,
        "notes": [str(item).strip() for item in notes if str(item).strip()],
    }


def add_approval_to_storage(approval_data: dict) -> dict:
    normalized_approval = normalize_approval_data(approval_data)

    approvals_data = load_approvals()
    outputs_data = load_outputs()
    preferences_data = load_preferences()
    outputs_data = load_outputs()

    existing_ids = {approval.get("id") for approval in approvals_data}
    base_id = normalized_approval["id"]
    counter = 2

    while normalized_approval["id"] in existing_ids:
        normalized_approval["id"] = f"{base_id}-{counter}"
        counter += 1

    approvals_data.append(normalized_approval)
    save_approvals(approvals_data)

    return {
        "success": True,
        "message": "Onay isteği oluşturuldu.",
        "approval": normalized_approval,
        "approvals": approvals_data,
    }



def guess_action_type_from_message(message: str) -> str:
    lower_message = message.lower()

    if "shopify" in lower_message or "ürün" in lower_message or "urun" in lower_message:
        if "canlı" in lower_message or "canli" in lower_message or "yayın" in lower_message or "yayin" in lower_message:
            return "shopify_publish"

        if "fiyat" in lower_message:
            return "shopify_price_update"

        if "sil" in lower_message:
            return "shopify_delete"

        return "shopify_update"

    if "mail" in lower_message or "e-posta" in lower_message or "email" in lower_message:
        return "email_send"

    if "dosya" in lower_message and "sil" in lower_message:
        return "file_delete"

    return "risky_action"


def guess_project_id_from_message(message: str, default_project_id: str = "") -> str:
    lower_message = message.lower()

    if "bilsanpack" in lower_message:
        return "bilsanpack"

    if "airpack europe" in lower_message or "airpack" in lower_message:
        return "airpack-europe"

    return default_project_id.strip()


def extract_approval_from_chat(message: str, project_id: str = "") -> dict:
    guessed_project_id = guess_project_id_from_message(message, project_id)
    guessed_action_type = guess_action_type_from_message(message)

    client = get_gemini_client()

    if client is None:
        return normalize_approval_data({
            "title": message.strip()[:80] or "Onay Gereken İşlem",
            "project_id": guessed_project_id,
            "action_type": guessed_action_type,
            "risk_level": "yüksek",
            "status": "bekliyor",
            "description": message.strip(),
            "payload": {
                "source_message": message.strip()
            },
            "notes": [
                "Bu işlem riskli kabul edildiği için Mert onayına gönderildi."
            ],
        })

    projects_data = load_projects()
    projects_text = json.dumps(projects_data, ensure_ascii=False, indent=2)

    prompt = f"""
Sen Vex'in Onay Merkezi modülüsün.

Mert'in mesajından riskli işlem için onay isteği çıkar.

Sadece geçerli JSON döndür.
Markdown, açıklama veya ekstra metin yazma.

Kayıtlı projeler:
{projects_text}

JSON şeması:
{{
  "id": "kebab-case-onay-id",
  "title": "Onay başlığı",
  "project_id": "ilgili-proje-id-yoksa-boş",
  "action_type": "shopify_publish | shopify_update | shopify_delete | shopify_price_update | email_send | file_delete | risky_action",
  "risk_level": "normal | yüksek | kritik",
  "status": "bekliyor",
  "description": "Onay açıklaması",
  "payload": {{
    "source_message": "Mert'in orijinal isteği",
    "detected_action": "algılanan işlem",
    "target": "işlem hedefi"
  }},
  "notes": ["Not 1", "Not 2"]
}}

Kurallar:
- Mesaj Türkçe ise alanlar Türkçe olsun.
- Canlıya alma, yayınlama, silme, fiyat değiştirme ve mail gönderme işlemleri risklidir.
- Canlıya alma/yayınlama için risk_level "yüksek" olsun.
- Silme işlemleri için risk_level "kritik" olsun.
- status her zaman "bekliyor" olsun.
- Eğer mesajda Bilsanpack geçiyorsa project_id "bilsanpack" olsun.
- Eğer mesajda AirPack Europe geçiyorsa project_id "airpack-europe" olsun.

Mert'in mesajı:
{message}

Varsayılan proje id:
{guessed_project_id}

Tahmini işlem tipi:
{guessed_action_type}
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    raw_text = response.text or "{}"
    json_text = clean_json_text(raw_text)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        parsed = {
            "title": message.strip()[:80] or "Onay Gereken İşlem",
            "project_id": guessed_project_id,
            "action_type": guessed_action_type,
            "risk_level": "yüksek",
            "status": "bekliyor",
            "description": message.strip(),
            "payload": {
                "source_message": message.strip()
            },
            "notes": [
                "Gemini çıktısı JSON olarak okunamadığı için basit onay isteği oluşturuldu."
            ],
        }

    return normalize_approval_data(parsed)



def load_active_project() -> dict:
    if not ACTIVE_PROJECT_PATH.exists():
        return {"project_id": ""}

    with ACTIVE_PROJECT_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_active_project(project_id: str) -> None:
    with ACTIVE_PROJECT_PATH.open("w", encoding="utf-8") as file:
        json.dump({"project_id": project_id}, file, ensure_ascii=False, indent=2)


def get_active_project_data() -> dict:
    active_data = load_active_project()
    active_project_id = active_data.get("project_id", "")

    projects_data = load_projects()

    for project in projects_data:
        if project.get("id") == active_project_id:
            return {
                "project_id": active_project_id,
                "project": project,
            }

    return {
        "project_id": active_project_id,
        "project": None,
    }



def load_active_task() -> dict:
    if not ACTIVE_TASK_PATH.exists():
        return {"task_id": ""}

    with ACTIVE_TASK_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_active_task(task_id: str) -> None:
    with ACTIVE_TASK_PATH.open("w", encoding="utf-8") as file:
        json.dump({"task_id": task_id}, file, ensure_ascii=False, indent=2)


def get_active_task_data() -> dict:
    active_data = load_active_task()
    active_task_id = active_data.get("task_id", "")

    tasks_data = load_tasks()

    for task in tasks_data:
        if task.get("id") == active_task_id:
            return {
                "task_id": active_task_id,
                "task": task,
            }

    return {
        "task_id": active_task_id,
        "task": None,
    }



def load_outputs() -> list[dict]:
    if not OUTPUTS_PATH.exists():
        return []

    with OUTPUTS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_outputs(outputs: list[dict]) -> None:
    with OUTPUTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(outputs, file, ensure_ascii=False, indent=2)


def normalize_output_data(output_data: dict) -> dict:
    title = str(output_data.get("title", "")).strip()

    if not title:
        title = "Yeni Çıktı"

    output_id = str(output_data.get("id", "")).strip()

    if not output_id:
        output_id = slugify(title)
    else:
        output_id = slugify(output_id)

    notes = output_data.get("notes", [])

    if not isinstance(notes, list):
        notes = [str(notes)]

    return {
        "id": output_id,
        "title": title,
        "project_id": str(output_data.get("project_id", "")).strip(),
        "task_id": str(output_data.get("task_id", "")).strip(),
        "output_type": str(output_data.get("output_type", "genel")).strip() or "genel",
        "content": str(output_data.get("content", "")).strip(),
        "status": str(output_data.get("status", "taslak")).strip() or "taslak",
        "notes": [str(item).strip() for item in notes if str(item).strip()],
    }


def add_output_to_storage(output_data: dict) -> dict:
    normalized_output = normalize_output_data(output_data)

    if not normalized_output["content"]:
        return {
            "success": False,
            "message": "Boş içerik çıktı olarak kaydedilemez.",
            "output": None,
            "outputs": load_outputs(),
        }

    outputs_data = load_outputs()

    existing_ids = {output.get("id") for output in outputs_data}
    base_id = normalized_output["id"]
    counter = 2

    while normalized_output["id"] in existing_ids:
        normalized_output["id"] = f"{base_id}-{counter}"
        counter += 1

    outputs_data.append(normalized_output)
    save_outputs(outputs_data)

    return {
        "success": True,
        "message": "Çıktı başarıyla kaydedildi.",
        "output": normalized_output,
        "outputs": outputs_data,
    }


def guess_output_type_from_text(title: str, content: str) -> str:
    combined = f"{title} {content}".lower()

    if "hero" in combined or "ana sayfa" in combined:
        return "hero_metni"

    if "seo" in combined or "meta" in combined:
        return "seo_metni"

    if "ürün" in combined or "urun" in combined or "product" in combined:
        return "urun_metni"

    if "sayfa" in combined or "page" in combined:
        return "sayfa_metni"

    if "plan" in combined:
        return "plan"

    return "genel"


def create_output_from_chat_data(title: str, content: str, output_type: str = "genel") -> dict:
    active_project_data = get_active_project_data()
    active_task_data = get_active_task_data()

    active_project_id = active_project_data.get("project_id", "")
    active_task_id = active_task_data.get("task_id", "")

    clean_title = title.strip()

    if not clean_title:
        active_task = active_task_data.get("task")
        if active_task:
            clean_title = active_task.get("title", "Aktif görev çıktısı")
        else:
            clean_title = "Sohbet çıktısı"

    clean_output_type = output_type.strip()

    if clean_output_type == "genel":
        clean_output_type = guess_output_type_from_text(clean_title, content)

    return normalize_output_data({
        "title": clean_title,
        "project_id": active_project_id,
        "task_id": active_task_id,
        "output_type": clean_output_type,
        "content": content,
        "status": "taslak",
        "notes": [
            "Bu çıktı sohbet üzerinden kaydedildi."
        ],
    })



def load_preferences() -> list[dict]:
    if not PREFERENCES_PATH.exists():
        return []

    with PREFERENCES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_preferences(preferences: list[dict]) -> None:
    with PREFERENCES_PATH.open("w", encoding="utf-8") as file:
        json.dump(preferences, file, ensure_ascii=False, indent=2)


def normalize_preference_data(preference_data: dict) -> dict:
    preference = str(preference_data.get("preference", "")).strip()

    preference_id = str(preference_data.get("id", "")).strip()

    if not preference_id:
        preference_id = slugify(preference[:80] or "tercih")
    else:
        preference_id = slugify(preference_id)

    return {
        "id": preference_id,
        "project_id": str(preference_data.get("project_id", "")).strip(),
        "task_id": str(preference_data.get("task_id", "")).strip(),
        "category": str(preference_data.get("category", "genel")).strip() or "genel",
        "preference": preference,
        "source": str(preference_data.get("source", "manual")).strip() or "manual",
        "confidence": str(preference_data.get("confidence", "medium")).strip() or "medium",
        "status": str(preference_data.get("status", "active")).strip() or "active",
    }


def add_preference_to_storage(preference_data: dict) -> dict:
    normalized_preference = normalize_preference_data(preference_data)

    if not normalized_preference["preference"]:
        return {
            "success": False,
            "message": "Boş tercih kaydedilemez.",
            "preference": None,
            "preferences": load_preferences(),
        }

    preferences_data = load_preferences()

    for existing in preferences_data:
        if (
            existing.get("preference") == normalized_preference["preference"]
            and existing.get("project_id") == normalized_preference["project_id"]
            and existing.get("task_id") == normalized_preference["task_id"]
        ):
            return {
                "success": True,
                "message": "Bu tercih zaten kayıtlı.",
                "preference": existing,
                "preferences": preferences_data,
            }

    existing_ids = {item.get("id") for item in preferences_data}
    base_id = normalized_preference["id"]
    counter = 2

    while normalized_preference["id"] in existing_ids:
        normalized_preference["id"] = f"{base_id}-{counter}"
        counter += 1

    preferences_data.append(normalized_preference)
    save_preferences(preferences_data)

    return {
        "success": True,
        "message": "Tercih başarıyla kaydedildi.",
        "preference": normalized_preference,
        "preferences": preferences_data,
    }


def extract_preference_from_chat(message: str, project_id: str = "", task_id: str = "") -> dict:
    active_project_data = get_active_project_data()
    active_task_data = get_active_task_data()

    clean_project_id = project_id.strip() or active_project_data.get("project_id", "")
    clean_task_id = task_id.strip() or active_task_data.get("task_id", "")

    client = get_gemini_client()

    if client is None:
        return normalize_preference_data({
            "project_id": clean_project_id,
            "task_id": clean_task_id,
            "category": "genel",
            "preference": message.strip(),
            "source": "chat",
            "confidence": "medium",
            "status": "active",
        })

    prompt = f"""
Sen Vex'in tercih öğrenme modülüsün.

Mert'in mesajından kalıcı veya yarı kalıcı bir tercih çıkar.

Sadece geçerli JSON döndür.
Markdown, açıklama veya ekstra metin yazma.

JSON şeması:
{{
  "project_id": "ilgili-proje-id-yoksa-boş",
  "task_id": "ilgili-görev-id-yoksa-boş",
  "category": "yazım_tarzı | marka_dili | ürün_metni | tasarım | iş_akışı | genel",
  "preference": "Öğrenilen tercih cümlesi",
  "source": "chat",
  "confidence": "low | medium | high",
  "status": "active"
}}

Kurallar:
- Mesajdan gerçekten gelecekte işe yarayacak tercih çıkar.
- Tek seferlik komutu genel tercih gibi kaydetme.
- Mert “bundan sonra”, “böyle olsun”, “bu tarzı koru”, “bunu seviyorum”, “fazla uzun”, “daha kısa”, “daha premium”, “böyle öğren” gibi ifadeler kullanıyorsa tercih çıkar.
- Proje bağlamı varsa project_id kullan.
- Aktif proje varsa ve mesaj proje tarzıyla ilgiliyse project_id olarak aktif proje id’sini kullan.
- Tercih kısa, net ve uygulanabilir olsun.
- Emin değilsen confidence "low" yap.

Aktif proje id:
{clean_project_id}

Aktif görev id:
{clean_task_id}

Mert'in mesajı:
{message}
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    raw_text = response.text or "{}"
    json_text = clean_json_text(raw_text)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        parsed = {
            "project_id": clean_project_id,
            "task_id": clean_task_id,
            "category": "genel",
            "preference": message.strip(),
            "source": "chat",
            "confidence": "low",
            "status": "active",
        }

    if not parsed.get("project_id"):
        parsed["project_id"] = clean_project_id

    if not parsed.get("task_id"):
        parsed["task_id"] = clean_task_id

    return normalize_preference_data(parsed)


def get_relevant_preferences(project_id: str = "", task_id: str = "") -> list[dict]:
    preferences_data = load_preferences()

    relevant = []

    for preference in preferences_data:
        if preference.get("status") != "active":
            continue

        pref_project_id = preference.get("project_id", "")
        pref_task_id = preference.get("task_id", "")

        if not pref_project_id and not pref_task_id:
            relevant.append(preference)
            continue

        if project_id and pref_project_id == project_id:
            relevant.append(preference)
            continue

        if task_id and pref_task_id == task_id:
            relevant.append(preference)
            continue

    return relevant



def ensure_screenshots_dir() -> None:
    SCREENSHOTS_PATH.mkdir(exist_ok=True)


def capture_screen_to_file() -> dict:
    ensure_screenshots_dir()

    screenshot_path = SCREENSHOTS_PATH / "latest_screen.png"

    with mss.mss() as screenshot_tool:
        # monitors[0] tüm ekranların birleşik görüntüsünü alır.
        # monitors[1], monitors[2] gibi değerler tek tek ekranları temsil eder.
        monitor = screenshot_tool.monitors[0]
        image = screenshot_tool.grab(monitor)

        from mss.tools import to_png
        png_bytes = to_png(image.rgb, image.size)

    screenshot_path.write_bytes(png_bytes)

    return {
        "success": True,
        "path": str(screenshot_path),
        "width": image.size.width,
        "height": image.size.height,
    }


def analyze_screen_image(image_path: str, user_prompt: str) -> dict:
    client = get_gemini_client()

    if client is None:
        return {
            "success": False,
            "message": "Gemini API key bulunamadı. Ekran analizi için GEMINI_API_KEY gerekiyor.",
            "analysis": "",
        }

    image_bytes = Path(image_path).read_bytes()

    prompt = f"""
Sen Vex'in GERÇEK EKRAN GÖRME modülüsün.

Sana gönderilen görüntü Mert'in o anki gerçek ekran görüntüsüdür.
Sadece bu görüntüde görsel olarak gördüğün şeyleri analiz et.

Mert'in isteği:
{user_prompt}

ÇOK ÖNEMLİ KURALLAR:
- Workspace hafızasına, proje listesine veya önceki sohbet bağlamına göre cevap verme.
- Sadece ekrandaki piksel görüntüsünden gördüklerini söyle.
- Görmediğin şeyi tahmin etme.
- "Şu panelde misin?" gibi soru sorma; ekranda ne görünüyorsa onu söyle.
- Eğer ekranda Vex uygulaması açıksa bunu açıkça söyle.
- Sol menü, aktif ekran, butonlar, hata yazıları, backend durumu, input alanı gibi görünen öğeleri tarif et.
- Eğer web sitesi veya tasarım görünüyorsa SEO, tasarım, güven algısı ve kullanılabilirlik açısından yorumla.
- Eğer terminal veya hata görünüyorsa görünen hatayı oku ve muhtemel sebebi söyle.
- Gereksiz uzun yazma.
- Cevaba mutlaka şu ifadeyle başla: "Gerçek ekran görüntüsüne göre:"
- Sonunda tek net sonraki adım öner.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png",
            ),
        ],
    )

    return {
        "success": True,
        "analysis": response.text or "Ekran analiz edildi ama metin boş döndü.",
    }



def normalize_url(url: str) -> str:
    clean_url = url.strip()

    if not clean_url:
        return ""

    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    return clean_url


def extract_site_data(url: str) -> dict:
    clean_url = normalize_url(url)

    if not clean_url:
        return {
            "success": False,
            "message": "URL boş olamaz.",
        }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/148.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }

    session = requests.Session()
    response = session.get(
        clean_url,
        headers=headers,
        timeout=20,
        allow_redirects=True,
    )

    content_type = response.headers.get("content-type", "")

    if response.status_code >= 400:
        if response.status_code == 403:
            message = (
                "Site Vex'in backend isteğini engelledi. HTTP 403 döndü. "
                "Bu genelde Cloudflare, bot koruması veya güvenlik duvarı nedeniyle olur. "
                "Siteyi tarayıcıda açıp 'ekranımı oku' dersen Screen Vision ile görsel analiz yapabilirim."
            )
        else:
            message = f"Siteye erişilemedi. HTTP status: {response.status_code}"

        return {
            "success": False,
            "message": message,
            "url": clean_url,
            "final_url": response.url,
        }

    if "text/html" not in content_type:
        return {
            "success": False,
            "message": f"Bu URL HTML sayfası gibi görünmüyor. Content-Type: {content_type}",
            "url": clean_url,
            "final_url": response.url,
        }

    soup = BeautifulSoup(response.text, "lxml")

    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    meta_description_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = ""
    if meta_description_tag:
        meta_description = meta_description_tag.get("content", "").strip()

    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    canonical = canonical_tag.get("href", "").strip() if canonical_tag else ""

    h1_list = [item.get_text(" ", strip=True) for item in soup.find_all("h1")]
    h2_list = [item.get_text(" ", strip=True) for item in soup.find_all("h2")[:20]]

    links = soup.find_all("a")
    buttons = soup.find_all("button")

    cta_candidates = []
    cta_words = [
        "buy", "shop", "get quote", "contact", "request", "start", "order",
        "satın", "teklif", "iletişim", "başla", "sipariş", "sepet"
    ]

    for link in links[:120]:
        text = link.get_text(" ", strip=True)
        lower_text = text.lower()

        if text and any(word in lower_text for word in cta_words):
            cta_candidates.append(text)

    for button in buttons[:80]:
        text = button.get_text(" ", strip=True)
        lower_text = text.lower()

        if text and any(word in lower_text for word in cta_words):
            cta_candidates.append(text)

    images = soup.find_all("img")
    image_count = len(images)
    images_without_alt = [
        image.get("src", "") for image in images
        if not image.get("alt")
    ]

    body_text = soup.get_text(" ", strip=True)
    body_text = re.sub(r"\\s+", " ", body_text)
    body_excerpt = body_text[:5000]

    word_count = len(body_text.split())

    return {
        "success": True,
        "url": clean_url,
        "final_url": response.url,
        "status_code": response.status_code,
        "title": title,
        "title_length": len(title),
        "meta_description": meta_description,
        "meta_description_length": len(meta_description),
        "canonical": canonical,
        "h1": h1_list,
        "h1_count": len(h1_list),
        "h2": h2_list,
        "cta_candidates": cta_candidates[:20],
        "link_count": len(links),
        "image_count": image_count,
        "images_without_alt_count": len(images_without_alt),
        "word_count": word_count,
        "body_excerpt": body_excerpt,
    }


def analyze_site_data_with_ai(site_data: dict, user_prompt: str) -> dict:
    client = get_gemini_client()

    if client is None:
        return {
            "success": False,
            "message": "Gemini API key bulunamadı. Site analizi için GEMINI_API_KEY gerekiyor.",
            "analysis": "",
            "site_data": site_data,
        }

    site_text = json.dumps(site_data, ensure_ascii=False, indent=2)

    prompt = f"""
Sen Vex'in URL site analiz modülüsün.

Mert sana bir web sitesi URL'si verdi.
Aşağıdaki HTML/SEO verilerine göre siteyi analiz et.

Mert'in isteği:
{user_prompt}

Site verisi:
{site_text}

Cevap kuralları:
- Türkçe cevap ver.
- Önce kısa genel değerlendirme yap.
- Sadece verilen HTML/SEO verisine dayanarak konuş.
- Ölçmediğin şeyi kesin bilgi gibi söyleme.
- Core Web Vitals, sayfa hızı, mobil skor, güvenlik skoru gibi ölçümler yapılmadıysa "bunun için ayrı performans testi gerekir" de.
- Tasarım/marka algısı yorumu yaparken bunun HTML metni, başlık yapısı, CTA ve içerik sinyallerine göre sınırlı bir yorum olduğunu belirt.
- SEO başlığı, meta description, H1/H2 yapısı, içerik kalitesi, CTA, güven algısı ve marka algısı başlıklarını ayrı değerlendir.
- Eksik veya zayıf alanları net söyle ama kanıtsız kesin hüküm verme.
- E-ticaret / Shopify sitesi ise ürün satışı, güven, CTA ve global marka algısına özellikle bak.
- Gereksiz uzun yazma.
- En sonunda 5 maddelik net iyileştirme listesi ver.
- Eğer veri yetersizse bunu açıkça söyle.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    return {
        "success": True,
        "analysis": response.text or "Site analiz edildi ama metin boş döndü.",
        "site_data": site_data,
    }



def load_reminders() -> list[dict]:
    if not REMINDERS_PATH.exists():
        return []

    with REMINDERS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_reminders(reminders: list[dict]) -> None:
    with REMINDERS_PATH.open("w", encoding="utf-8") as file:
        json.dump(reminders, file, ensure_ascii=False, indent=2)


def parse_reminder_datetime_fallback(message: str) -> str:
    now = datetime.now()
    lower_message = message.lower()

    if "dakika sonra" in lower_message:
        match = re.search(r"(\\d+)\\s*dakika sonra", lower_message)
        if match:
            return (now + timedelta(minutes=int(match.group(1)))).isoformat(timespec="minutes")

    if "saat sonra" in lower_message:
        match = re.search(r"(\\d+)\\s*saat sonra", lower_message)
        if match:
            return (now + timedelta(hours=int(match.group(1)))).isoformat(timespec="minutes")

    time_match = re.search(r"(\\d{1,2})[:\\.](\\d{2})", lower_message)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if "yarın" in lower_message or "yarin" in lower_message:
            target = target + timedelta(days=1)
        elif target <= now:
            target = target + timedelta(days=1)

        return target.isoformat(timespec="minutes")

    if "yarın" in lower_message or "yarin" in lower_message:
        target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return target.isoformat(timespec="minutes")

    return (now + timedelta(hours=1)).isoformat(timespec="minutes")


def normalize_reminder_data(reminder_data: dict) -> dict:
    title = str(reminder_data.get("title", "")).strip()

    if not title:
        title = "Yeni Hatırlatma"

    reminder_id = str(reminder_data.get("id", "")).strip()

    if not reminder_id:
        reminder_id = slugify(title)
    else:
        reminder_id = slugify(reminder_id)

    notes = reminder_data.get("notes", [])

    if not isinstance(notes, list):
        notes = [str(notes)]

    return {
        "id": reminder_id,
        "title": title,
        "remind_at": str(reminder_data.get("remind_at", "")).strip(),
        "project_id": str(reminder_data.get("project_id", "")).strip(),
        "task_id": str(reminder_data.get("task_id", "")).strip(),
        "status": str(reminder_data.get("status", "active")).strip() or "active",
        "notified": bool(reminder_data.get("notified", False)),
        "notes": [str(item).strip() for item in notes if str(item).strip()],
    }


def add_reminder_to_storage(reminder_data: dict) -> dict:
    normalized_reminder = normalize_reminder_data(reminder_data)

    if not normalized_reminder["remind_at"]:
        return {
            "success": False,
            "message": "Hatırlatma zamanı boş olamaz.",
            "reminder": None,
            "reminders": load_reminders(),
        }

    reminders_data = load_reminders()

    existing_ids = {item.get("id") for item in reminders_data}
    base_id = normalized_reminder["id"]
    counter = 2

    while normalized_reminder["id"] in existing_ids:
        normalized_reminder["id"] = f"{base_id}-{counter}"
        counter += 1

    reminders_data.append(normalized_reminder)
    save_reminders(reminders_data)

    return {
        "success": True,
        "message": "Hatırlatma kaydedildi.",
        "reminder": normalized_reminder,
        "reminders": reminders_data,
    }


def extract_reminder_from_chat(message: str, project_id: str = "", task_id: str = "") -> dict:
    active_project_data = get_active_project_data()
    active_task_data = get_active_task_data()

    clean_project_id = project_id.strip() or active_project_data.get("project_id", "")
    clean_task_id = task_id.strip() or active_task_data.get("task_id", "")

    client = get_gemini_client()

    fallback_remind_at = parse_reminder_datetime_fallback(message)

    if client is None:
        return normalize_reminder_data({
            "title": message.strip(),
            "remind_at": fallback_remind_at,
            "project_id": clean_project_id,
            "task_id": clean_task_id,
            "status": "active",
            "notified": False,
            "notes": ["Bu hatırlatma sohbetten oluşturuldu."],
        })

    prompt = f"""
Sen Vex'in hatırlatma çıkarma modülüsün.

Mert'in mesajından hatırlatma başlığı ve zamanı çıkar.

Sadece geçerli JSON döndür.
Markdown, açıklama veya ekstra metin yazma.

Şu anki local zaman:
{datetime.now().isoformat(timespec="minutes")}

Varsayılan/fallback zaman:
{fallback_remind_at}

JSON şeması:
{{
  "title": "Hatırlatma başlığı",
  "remind_at": "YYYY-MM-DDTHH:MM",
  "project_id": "ilgili proje id yoksa boş",
  "task_id": "ilgili görev id yoksa boş",
  "status": "active",
  "notified": false,
  "notes": ["Sohbetten oluşturuldu"]
}}

Kurallar:
- "30 dakika sonra", "2 saat sonra", "yarın", "saat 18:00" gibi ifadeleri doğru yorumla.
- Tarih belirsizse en yakın mantıklı zamanı seç.
- Hatırlatma başlığı kısa ve uygulanabilir olsun.
- Aktif proje/görev bağlamı uygunsa kullan.

Aktif proje id:
{clean_project_id}

Aktif görev id:
{clean_task_id}

Mert'in mesajı:
{message}
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    raw_text = response.text or "{}"
    json_text = clean_json_text(raw_text)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        parsed = {
            "title": message.strip(),
            "remind_at": fallback_remind_at,
            "project_id": clean_project_id,
            "task_id": clean_task_id,
            "status": "active",
            "notified": False,
            "notes": ["Gemini çıktısı JSON okunamadığı için fallback zaman kullanıldı."],
        }

    if not parsed.get("project_id"):
        parsed["project_id"] = clean_project_id

    if not parsed.get("task_id"):
        parsed["task_id"] = clean_task_id

    if not parsed.get("remind_at"):
        parsed["remind_at"] = fallback_remind_at

    return normalize_reminder_data(parsed)


def get_due_reminders(mark_as_notified: bool = True) -> dict:
    now = datetime.now()
    reminders_data = load_reminders()
    due_reminders = []

    for reminder in reminders_data:
        if reminder.get("status") != "active":
            continue

        if reminder.get("notified"):
            continue

        remind_at_text = reminder.get("remind_at", "")

        try:
            remind_at = datetime.fromisoformat(remind_at_text)
        except ValueError:
            continue

        if remind_at <= now:
            due_reminders.append(reminder)

    if mark_as_notified and due_reminders:
        due_ids = {item.get("id") for item in due_reminders}

        for reminder in reminders_data:
            if reminder.get("id") in due_ids:
                reminder["notified"] = True
                reminder["status"] = "notified"

        save_reminders(reminders_data)

    return {
        "success": True,
        "due_reminders": due_reminders,
        "reminders": reminders_data,
    }



def plan_computer_action_from_screen(instruction: str) -> dict:
    capture_result = capture_screen_to_file()

    if not capture_result.get("success"):
        return capture_result

    client = get_gemini_client()

    if client is None:
        return {
            "success": False,
            "message": "Gemini API key bulunamadı. Bilgisayar kontrol planı için GEMINI_API_KEY gerekiyor.",
        }

    image_bytes = Path(capture_result["path"]).read_bytes()

    prompt = f"""
Sen Vex'in bilgisayar kontrol hazırlık modülüsün.

Sana Mert'in gerçek ekran görüntüsü veriliyor.
Henüz hiçbir şeye tıklama, yazma veya işlem yapma.
Sadece yapılacak işi analiz et ve güvenli bir plan çıkar.

Mert'in isteği:
{instruction}

Kurallar:
- Türkçe cevap ver.
- Sadece ekranda gördüğün şeylere dayan.
- Görmediğin butonu veya alanı varmış gibi söyleme.
- Eğer işlem riskliyse açıkça riskli de.
- Dosya silme, ödeme, canlıya alma, mail gönderme, ürün yayınlama gibi işlemler yüksek risklidir.
- Tıklama veya yazma yapmadan önce Mert’ten onay istenmesi gerektiğini belirt.
- Cevapta şu başlıkları kullan:
  1. Ekranda gördüğüm
  2. Yapılacak işlem
  3. Risk seviyesi
  4. Onay gerekiyor mu?
  5. Önerilen güvenli sonraki adım
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png",
            ),
        ],
    )

    return {
        "success": True,
        "plan": response.text or "Plan oluşturuldu ama metin boş döndü.",
        "screenshot": capture_result,
    }



def extract_shopify_content_from_chat(
    message: str,
    project_id: str = "",
    task_id: str = "",
    language: str = "English",
) -> dict:
    active_project_data = get_active_project_data()
    active_task_data = get_active_task_data()

    clean_project_id = project_id.strip() or active_project_data.get("project_id", "")
    clean_task_id = task_id.strip() or active_task_data.get("task_id", "")

    try:
        active_brand_profile = get_brand_profile_for_project(clean_project_id)
    except Exception:
        active_brand_profile = None

    try:
        relevant_preferences = get_relevant_preferences(
            project_id=clean_project_id,
            task_id=clean_task_id,
        )
    except Exception:
        relevant_preferences = []

    client = get_gemini_client()

    if client is None:
        return {
            "success": False,
            "message": "Gemini API key bulunamadı.",
            "content": None,
        }

    brand_text = json.dumps(active_brand_profile, ensure_ascii=False, indent=2)
    preferences_text = json.dumps(relevant_preferences, ensure_ascii=False, indent=2)

    prompt = f"""
Sen Vex'in Shopify ürün içerik hazırlama modülüsün.

Mert bir ürün bilgisi verdi. Bu ürünü Shopify'a koymaya hazır içerik paketine dönüştür.

Dil:
{language}

Aktif proje id:
{clean_project_id}

Aktif görev id:
{clean_task_id}

Marka profili:
{brand_text}

Öğrenilmiş tercihler:
{preferences_text}

Mert'in ürün mesajı:
{message}

Sadece geçerli JSON döndür. Markdown, açıklama veya ekstra metin yazma.

JSON şeması:
{{
  "product_title": "Shopify ürün başlığı",
  "seo_title": "SEO title, mümkünse 55-60 karakter civarı",
  "meta_description": "Meta description, mümkünse 140-160 karakter civarı",
  "handle": "shopify-url-handle",
  "product_type": "Ürün tipi",
  "collection_suggestion": "Önerilen koleksiyon",
  "tags": ["tag1", "tag2", "tag3"],
  "short_description": "Kısa ürün açıklaması",
  "product_description_html": "<p>HTML ürün açıklaması</p>",
  "key_benefits": ["Avantaj 1", "Avantaj 2", "Avantaj 3"],
  "technical_specs": ["Özellik 1", "Özellik 2"],
  "usage_areas": ["Kullanım alanı 1", "Kullanım alanı 2"],
  "quality_notes": ["Dikkat edilecek not 1"],
  "missing_info_questions": ["Eksik bilgi varsa Mert'e sorulacak kısa soru"]
}}

Kurallar:
- Bilsanpack veya global ambalaj ürünü ise güven veren, net, profesyonel ve global satışa uygun dil kullan.
- Fazla süslü ve uzun cümlelerden kaçın.
- Ürün ölçüsü, malzeme, kullanım alanı gibi bilgiler verilmişse koru.
- Verilmeyen teknik bilgiyi uydurma; missing_info_questions içine yaz.
- Shopify'a yapıştırılabilir çıktı üret.
- SEO title ve meta description sade, tıklanabilir ve anahtar kelime odaklı olsun.
- HTML açıklama temiz olsun; gereksiz inline style kullanma.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    raw_text = response.text or "{}"
    json_text = clean_json_text(raw_text)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return {
            "success": False,
            "message": "Shopify içerik JSON olarak okunamadı.",
            "raw": raw_text,
            "content": None,
        }

    return {
        "success": True,
        "message": "Shopify içerik paketi hazırlandı.",
        "content": parsed,
        "project_id": clean_project_id,
        "task_id": clean_task_id,
        "source_message": message,
    }


def build_shopify_content_output_text(content: dict) -> str:
    if not content:
        return ""

    tags = content.get("tags", [])
    benefits = content.get("key_benefits", [])
    specs = content.get("technical_specs", [])
    usage_areas = content.get("usage_areas", [])
    quality_notes = content.get("quality_notes", [])
    questions = content.get("missing_info_questions", [])

    def list_text(items):
        if not items:
            return "-"
        return "\\n".join([f"- {item}" for item in items])

    return f"""Shopify Ürün İçeriği

Ürün Başlığı:
{content.get("product_title", "")}

SEO Title:
{content.get("seo_title", "")}

Meta Description:
{content.get("meta_description", "")}

Handle:
{content.get("handle", "")}

Product Type:
{content.get("product_type", "")}

Koleksiyon Önerisi:
{content.get("collection_suggestion", "")}

Tags:
{", ".join(tags) if isinstance(tags, list) else tags}

Kısa Açıklama:
{content.get("short_description", "")}

HTML Ürün Açıklaması:
{content.get("product_description_html", "")}

Öne Çıkan Avantajlar:
{list_text(benefits)}

Teknik Özellikler:
{list_text(specs)}

Kullanım Alanları:
{list_text(usage_areas)}

Kalite Notları:
{list_text(quality_notes)}

Eksik Bilgi Soruları:
{list_text(questions)}
"""



def get_site_request_headers() -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/148.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def same_domain(url_a: str, url_b: str) -> bool:
    try:
        return urlparse(url_a).netloc.replace("www.", "") == urlparse(url_b).netloc.replace("www.", "")
    except Exception:
        return False


def fetch_url_text(url: str, timeout: int = 15) -> dict:
    clean_url = normalize_url(url)
    headers = get_site_request_headers()

    try:
        response = requests.get(
            clean_url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )
    except Exception as error:
        return {
            "success": False,
            "message": str(error),
            "url": clean_url,
            "text": "",
            "content_type": "",
            "status_code": 0,
        }

    return {
        "success": response.status_code < 400,
        "message": "" if response.status_code < 400 else f"HTTP {response.status_code}",
        "url": clean_url,
        "final_url": response.url,
        "text": response.text,
        "content_type": response.headers.get("content-type", ""),
        "status_code": response.status_code,
    }


def discover_sitemap_urls(base_url: str) -> list[str]:
    clean_url = normalize_url(base_url)
    parsed = urlparse(clean_url)
    root = f"{parsed.scheme}://{parsed.netloc}"

    candidate_sitemaps = [
        urljoin(root, "/sitemap.xml"),
        urljoin(root, "/sitemap_index.xml"),
        urljoin(root, "/product-sitemap.xml"),
        urljoin(root, "/page-sitemap.xml"),
        urljoin(root, "/products-sitemap.xml"),
    ]

    discovered_urls = []

    for sitemap_url in candidate_sitemaps:
        result = fetch_url_text(sitemap_url, timeout=12)

        if not result.get("success"):
            continue

        text = result.get("text", "")

        soup = BeautifulSoup(text, "xml")
        loc_tags = soup.find_all("loc")

        for loc in loc_tags:
            loc_text = loc.get_text(strip=True)

            if loc_text and same_domain(clean_url, loc_text):
                discovered_urls.append(loc_text)

    # unique preserve order
    unique_urls = []
    seen = set()

    for item in discovered_urls:
        if item not in seen:
            seen.add(item)
            unique_urls.append(item)

    return unique_urls


def discover_links_from_home(base_url: str, max_links: int = 80) -> list[str]:
    clean_url = normalize_url(base_url)
    result = fetch_url_text(clean_url, timeout=15)

    if not result.get("success"):
        return []

    soup = BeautifulSoup(result.get("text", ""), "lxml")
    links = []

    product_signals = [
        "product", "products", "produkt", "produkty", "shop", "collection", "collections",
        "category", "kategorie", "catalog", "catalogue", "urun", "ürün", "obchod"
    ]

    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()

        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue

        absolute = urljoin(result.get("final_url", clean_url), href)

        if not same_domain(clean_url, absolute):
            continue

        lower_url = absolute.lower()
        link_text = link.get_text(" ", strip=True).lower()

        if any(signal in lower_url or signal in link_text for signal in product_signals):
            links.append(absolute)

    unique_links = []
    seen = set()

    for item in links:
        if item not in seen:
            seen.add(item)
            unique_links.append(item)

    return unique_links[:max_links]


def is_probable_product_url(url: str) -> bool:
    lower_url = url.lower()

    product_signals = [
        "/product", "/products", "/produkt", "/produkty", "/shop", "/collections",
        "/collection", "/category", "/kategorie", "/catalog", "/urun", "/ürün",
        "variant=", "sku=", "handle="
    ]

    avoid_signals = [
        "/cart", "/checkout", "/account", "/login", "/register", "/privacy",
        "/terms", "/contact", "/blog", "/news", "/search", "/tag/"
    ]

    if any(signal in lower_url for signal in avoid_signals):
        return False

    return any(signal in lower_url for signal in product_signals)


def extract_product_page_summary(url: str) -> dict:
    result = fetch_url_text(url, timeout=15)

    if not result.get("success"):
        return {
            "success": False,
            "url": url,
            "message": result.get("message", "Sayfa okunamadı."),
        }

    content_type = result.get("content_type", "")

    if "html" not in content_type.lower() and result.get("text", "").strip().startswith("<?xml"):
        return {
            "success": False,
            "url": url,
            "message": "HTML ürün sayfası değil.",
        }

    soup = BeautifulSoup(result.get("text", ""), "lxml")

    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_description = meta_tag.get("content", "").strip()

    h1 = [item.get_text(" ", strip=True) for item in soup.find_all("h1")[:3]]
    h2 = [item.get_text(" ", strip=True) for item in soup.find_all("h2")[:8]]

    # Remove noisy nodes
    for noisy in soup(["script", "style", "noscript", "svg", "iframe"]):
        noisy.decompose()

    body_text = soup.get_text(" ", strip=True)
    body_text = re.sub(r"\s+", " ", body_text)
    body_excerpt = body_text[:2500]

    images = soup.find_all("img")
    alt_texts = [
        image.get("alt", "").strip()
        for image in images
        if image.get("alt", "").strip()
    ]

    # Fiyat çıkarma
    price = ""
    
    # 1. Meta property (Open Graph / Shopify / Yoast) - EN GÜVENİLİR YÖNTEM!
    if not price:
        price_meta = (
            soup.find("meta", property="product:price:amount") or
            soup.find("meta", attrs={"name": "product:price:amount"}) or
            soup.find("meta", itemprop="price")
        )
        if price_meta and price_meta.get("content", "").strip():
            price = price_meta.get("content", "").strip()

    # 2. JSON-LD schema.org/Product içinde price (Yalnızca "Product" tipindeki şemadan al)
    if not price:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.get_text(strip=True))
                
                # Bazen liste olabilir
                ld_list = ld if isinstance(ld, list) else [ld]
                
                # Bazen "@graph" içinde olabilir (Yoast SEO)
                if isinstance(ld, dict) and "@graph" in ld:
                    ld_list = ld["@graph"]

                for item in ld_list:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        offers = item.get("offers", {})
                        if isinstance(offers, dict) and offers.get("price"):
                            price = str(offers.get("price"))
                            break
                        if isinstance(offers, list) and len(offers) > 0:
                            price = str(offers[0].get("price", ""))
                            break
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass
            
            if price:
                break

    # 3. HTML attribute "data-price" (sepete ekle butonlarında falan kesin fiyat bulunur)
    if not price:
        button_with_price = soup.find(attrs={"data-price": True})
        if button_with_price and button_with_price.get("data-price", "").strip():
            price = button_with_price.get("data-price").strip()

    # 4. Regex fallback
    if not price:
        price_match = re.search(
            r'(?:[$€£])\s*(\d+(?:[.,]\d{1,2})?)|(\d+(?:[.,]\d{1,2})?)\s*(?:[$€£€]|EUR|USD)',
            body_text[:500],
            re.IGNORECASE,
        )
        if price_match:
            price = price_match.group(0).strip()

    # Para birimini de çıkar
    currency = ""
    currency_meta = soup.find("meta", property="product:price:currency")
    if currency_meta and currency_meta.get("content", "").strip():
        currency = currency_meta.get("content", "").strip()

    if not currency and price:
        currency_match = re.match(r'([$€£€]|EUR|USD|TRY)', price)
        if currency_match:
            currency = currency_match.group(1)

    return {
        "success": True,
        "url": result.get("final_url", url),
        "title": title,
        "meta_description": meta_description,
        "h1": h1,
        "h2": h2,
        "price": price,
        "currency": currency,
        "body_excerpt": body_excerpt,
        "image_alt_texts": alt_texts[:10],
        "word_count": len(body_text.split()),
    }


def collect_candidate_product_pages(base_url: str, max_pages: int = 40) -> list[dict]:
    clean_url = normalize_url(base_url)

    sitemap_urls = discover_sitemap_urls(clean_url)
    home_links = discover_links_from_home(clean_url)

    candidate_urls = []

    for item in sitemap_urls:
        if is_probable_product_url(item):
            candidate_urls.append(item)

    for item in home_links:
        if item not in candidate_urls:
            candidate_urls.append(item)

    if not candidate_urls:
        candidate_urls = home_links or [clean_url]

    candidate_urls = candidate_urls[:max_pages]

    pages = []

    for candidate_url in candidate_urls:
        summary = extract_product_page_summary(candidate_url)

        if summary.get("success"):
            pages.append(summary)

    return pages


def find_products_on_site_with_ai(
    url: str,
    query: str,
    language: str = "Turkish",
    max_pages: int = 40,
) -> dict:
    clean_url = normalize_url(url)

    if not clean_url:
        return {
            "success": False,
            "message": "URL boş olamaz.",
            "results": [],
        }

    if not query.strip():
        return {
            "success": False,
            "message": "Aranacak ürün/soru boş olamaz.",
            "results": [],
        }

    pages = collect_candidate_product_pages(clean_url, max_pages=max_pages)

    if not pages:
        return {
            "success": False,
            "message": "Sitede okunabilir ürün sayfası bulunamadı. Site bot koruması kullanıyor olabilir veya ürünler JavaScript ile yükleniyor olabilir.",
            "results": [],
            "pages_scanned": 0,
        }

    client = get_gemini_client()

    if client is None:
        return {
            "success": False,
            "message": "Gemini API key bulunamadı.",
            "results": [],
            "pages_scanned": len(pages),
        }

    pages_text = json.dumps(pages[:max_pages], ensure_ascii=False, indent=2)

    prompt = f"""
Sen Vex'in çok dilli site ürün bulma modülüsün.

Mert sana bir site URL'si ve ürün arama isteği verdi.
Site Çekçe, Almanca, İngilizce, Türkçe veya başka dilde olabilir.
Mert Türkçe veya Almanca sorsa bile sitedeki ürünleri anlamlandırıp eşleştir.

Site URL:
{clean_url}

Mert'in aradığı / sorduğu şey:
{query}

Cevap dili:
{language}

Taranan ürün/sayfa verileri:
{pages_text}

Sadece geçerli JSON döndür. Markdown, açıklama veya ekstra metin yazma.

JSON şeması:
{{
  "summary": "Kısa genel sonuç",
  "best_match": {{
    "url": "en iyi eşleşen ürün URL'i",
    "original_title": "sitedeki orijinal başlık",
    "turkish_explanation": "ürünün Türkçe açıklaması",
    "why_match": "neden bu ürün eşleşiyor",
    "confidence": "low | medium | high"
  }},
  "matches": [
    {{
      "url": "ürün URL'i",
      "original_title": "orijinal başlık",
      "translated_title_tr": "Türkçe başlık",
      "short_explanation_tr": "Türkçe kısa açıklama",
      "confidence": "low | medium | high"
    }}
  ],
  "questions_for_mert": ["Eksik bilgi varsa kısa soru"]
}}

Kurallar:
- Ürün başlıklarını ve açıklamaları mümkün olduğunca Türkçeye çevir.
- Emin değilsen confidence düşük yaz.
- Uydurma ürün ekleme; sadece verilen sayfalara dayan.
- Eğer sonuçlar zayıfsa bunu açıkça söyle.
- E-ticaret ürünüyse ürünün ne işe yaradığını, kime uygun olduğunu ve Shopify için kullanılabilirliğini kısa açıkla.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    raw_text = response.text or "{}"
    json_text = clean_json_text(raw_text)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return {
            "success": False,
            "message": "Ürün bulma sonucu JSON olarak okunamadı.",
            "raw": raw_text,
            "results": [],
            "pages_scanned": len(pages),
        }

    return {
        "success": True,
        "message": "Site ürün araması tamamlandı.",
        "url": clean_url,
        "query": query,
        "pages_scanned": len(pages),
        "analysis": parsed,
        "pages": pages[:max_pages],
    }


def build_product_finder_reply(result: dict) -> str:
    if not result.get("success"):
        return result.get("message", "Ürün araması yapılamadı.")

    analysis = result.get("analysis", {})
    best = analysis.get("best_match") or {}
    matches = analysis.get("matches") or []
    questions = analysis.get("questions_for_mert") or []
    pages_scanned = result.get("pages_scanned", 0)

    summary = analysis.get("summary", "").strip()

    lines = []

    lines.append("🔍 Ürün aramasını tamamladım Mert.")
    lines.append(f"Toplam {pages_scanned} sayfayı taradım ve sonuçları derledim.")
    lines.append("")

    if summary:
        lines.append("📌 Kısa Sonuç")
        lines.append(summary)
        lines.append("")

    if best and best.get("url"):
        lines.append("⭐ En İyi Eşleşme")
        lines.append(f"Ürün: {best.get('original_title', '-')}")
        lines.append(f"Açıklama: {best.get('turkish_explanation', '-')}")
        lines.append(f"Eşleşme Oranı: {str(best.get('confidence', '-')).capitalize()}")
        lines.append(f"Bağlantı: {best.get('url', '-')}")
        lines.append("")

        why_match = best.get("why_match", "").strip()
        if why_match:
            lines.append("💡 Seçim Nedeni:")
            lines.append(why_match)
            lines.append("")

    filtered_matches = []

    for match in matches:
        match_url = match.get("url", "")
        best_url = best.get("url", "")

        if match_url and best_url and match_url == best_url:
            continue

        filtered_matches.append(match)

    if filtered_matches:
        lines.append("🔎 Diğer Yakın Sonuçlar:")

        for index, match in enumerate(filtered_matches[:3], start=1):
            title = (
                match.get("translated_title_tr")
                or match.get("original_title")
                or "Başlık yok"
            )

            explanation = match.get("short_explanation_tr", "").strip()
            confidence = match.get("confidence", "-")
            url = match.get("url", "-")

            lines.append(f"{index}. {title}")
            lines.append(f"   Eşleşme: {str(confidence).capitalize()}")

            if explanation:
                lines.append(f"   Not: {explanation}")

            lines.append(f"   Bağlantı: {url}")
            lines.append("")

    if questions:
        lines.append("❓ Netleştirmem Gerekenler:")
        for question in questions[:2]:
            lines.append(f"- {question}")
        lines.append("")

    lines.append("İstersen en iyi eşleşmeyi tek komutla Shopify ürün içeriğine dönüştürebilirim.")

    return "\n".join(lines)


@app.post("/site/find-products")
def site_find_products(request: SiteProductFinderRequest):
    try:
        result = find_products_on_site_with_ai(
            url=request.url,
            query=request.query,
            language=request.language,
            max_pages=request.max_pages,
        )

        if result.get("success"):
            result["formatted_output"] = build_product_finder_reply(result)

        return result

    except Exception as error:
        print("Vex site ürün bulma hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
            "results": [],
        }


@app.post("/site/analyze")
def analyze_site(request: UrlAnalyzeRequest):
    try:
        site_data = extract_site_data(request.url)

        if not site_data.get("success"):
            return {
                **site_data,
                "analysis": "",
            }

        return analyze_site_data_with_ai(
            site_data=site_data,
            user_prompt=request.prompt,
        )

    except Exception as error:
        print("Vex site analiz hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
            "analysis": "",
        }



@app.post("/computer/plan")
def computer_plan(request: ComputerPlanRequest):
    try:
        return plan_computer_action_from_screen(request.instruction)
    except Exception as error:
        print("Vex bilgisayar kontrol plan hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
        }


@app.post("/screen/capture")
def capture_screen():
    try:
        return capture_screen_to_file()
    except Exception as error:
        print("Vex ekran yakalama hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
        }


@app.post("/screen/capture-and-analyze")
def capture_and_analyze_screen(request: ScreenAnalyzeRequest):
    try:
        capture_result = capture_screen_to_file()

        if not capture_result.get("success"):
            return capture_result

        analysis_result = analyze_screen_image(
            image_path=capture_result["path"],
            user_prompt=request.prompt,
        )

        return {
            **analysis_result,
            "screenshot": capture_result,
        }

    except Exception as error:
        print("Vex ekran analiz hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
            "analysis": "",
        }



@app.get("/health")
def health():
    return {
        "success": True,
        "status": "online",
        "app": "Vex",
        "message": "Backend çalışıyor",
    }


@app.get("/")
def root():
    return {
        "app": "Vex",
        "status": "Backend çalışıyor",
        "message": "Vex backend hazır.",
    }






@app.get("/workspace/active-task")
def active_task():
    return {
        "success": True,
        **get_active_task_data(),
    }


@app.post("/workspace/active-task")
def set_active_task(request: ActiveTaskRequest):
    clean_task_id = request.task_id.strip().lower()

    if not clean_task_id:
        save_active_task("")

        return {
            "success": True,
            "message": "Aktif görev temizlendi.",
            "task_id": "",
            "task": None,
        }

    tasks_data = load_tasks()

    for task in tasks_data:
        if task.get("id") == clean_task_id:
            save_active_task(clean_task_id)

            return {
                "success": True,
                "message": "Aktif görev güncellendi.",
                "task_id": clean_task_id,
                "task": task,
            }

    return {
        "success": False,
        "message": "Bu id ile kayıtlı görev bulunamadı.",
        "task_id": clean_task_id,
        "task": None,
    }


@app.get("/workspace/active-project/detail")
def active_project_detail():
    active_data = get_active_project_data()
    active_project_id = active_data.get("project_id", "")
    active_project = active_data.get("project")

    tasks_data = load_tasks()
    approvals_data = load_approvals()
    outputs_data = load_outputs()
    preferences_data = load_preferences()

    if not active_project_id or not active_project:
        return {
            "success": True,
            "has_active_project": False,
            "project_id": "",
            "project": None,
            "tasks": [],
            "open_tasks": [],
            "high_priority_tasks": [],
            "approvals": [],
            "pending_approvals": [],
            "outputs": [],
            "preferences": [],
            "counts": {
                "tasks": 0,
                "open_tasks": 0,
                "high_priority_tasks": 0,
                "approvals": 0,
                "pending_approvals": 0,
                "outputs": 0,
                "preferences": 0,
            },
            "suggested_next_step": "Önce aktif bir proje seçelim.",
        }

    project_tasks = [
        task for task in tasks_data
        if task.get("project_id") == active_project_id
    ]

    open_tasks = [
        task for task in project_tasks
        if task.get("status", "").lower() != "tamamlandı"
    ]

    high_priority_tasks = [
        task for task in open_tasks
        if task.get("priority", "").lower() in ["yüksek", "kritik"]
    ]

    project_approvals = [
        approval for approval in approvals_data
        if approval.get("project_id") == active_project_id
    ]

    pending_approvals = [
        approval for approval in project_approvals
        if approval.get("status", "").lower() == "bekliyor"
    ]

    project_outputs = [
        output for output in outputs_data
        if output.get("project_id") == active_project_id
    ]

    project_preferences = [
        preference for preference in preferences_data
        if preference.get("status") == "active"
        and (
            not preference.get("project_id")
            or preference.get("project_id") == active_project_id
        )
    ]

    suggested_next_step = f"{active_project.get('name', active_project_id)} için sıradaki işi birlikte netleştirebiliriz."

    if pending_approvals:
        suggested_next_step = f"{active_project.get('name', active_project_id)} için bekleyen onaylar var; önce onları kontrol etmek iyi olur."
    elif high_priority_tasks:
        suggested_next_step = f"{active_project.get('name', active_project_id)} için yüksek öncelikli görevler var; önce onlardan biriyle başlayalım."
    elif open_tasks:
        suggested_next_step = f"{active_project.get('name', active_project_id)} için açık görevler var; sıradaki görevi seçebiliriz."

    return {
        "success": True,
        "has_active_project": True,
        "project_id": active_project_id,
        "project": active_project,
        "tasks": project_tasks,
        "open_tasks": open_tasks,
        "high_priority_tasks": high_priority_tasks,
        "approvals": project_approvals,
        "pending_approvals": pending_approvals,
        "outputs": project_outputs,
        "preferences": project_preferences,
        "counts": {
            "tasks": len(project_tasks),
            "open_tasks": len(open_tasks),
            "high_priority_tasks": len(high_priority_tasks),
            "approvals": len(project_approvals),
            "pending_approvals": len(pending_approvals),
            "outputs": len(project_outputs),
            "preferences": len(project_preferences),
        },
        "suggested_next_step": suggested_next_step,
    }

@app.get("/workspace/active-project")
def active_project():
    return {
        "success": True,
        **get_active_project_data(),
    }


@app.post("/workspace/active-project")
def set_active_project(request: ActiveProjectRequest):
    clean_project_id = request.project_id.strip().lower()

    if not clean_project_id:
        save_active_project("")

        return {
            "success": True,
            "message": "Aktif proje temizlendi.",
            "project_id": "",
            "project": None,
        }

    projects_data = load_projects()

    for project in projects_data:
        if project.get("id") == clean_project_id:
            save_active_project(clean_project_id)

            return {
                "success": True,
                "message": "Aktif proje güncellendi.",
                "project_id": clean_project_id,
                "project": project,
            }

    return {
        "success": False,
        "message": "Bu id ile kayıtlı proje bulunamadı.",
        "project_id": clean_project_id,
        "project": None,
    }


@app.get("/workspace/summary")
def workspace_summary():
    projects_data = load_projects()
    tasks_data = load_tasks()
    approvals_data = load_approvals()
    outputs_data = load_outputs()
    preferences_data = load_preferences()

    active_project_data = get_active_project_data()
    active_project = active_project_data.get("project")
    active_project_id = active_project_data.get("project_id", "")

    active_task_data = get_active_task_data()
    active_task = active_task_data.get("task")
    active_task_id = active_task_data.get("task_id", "")

    active_projects = [
        project for project in projects_data
        if project.get("status", "").lower() == "aktif"
    ]

    open_tasks = [
        task for task in tasks_data
        if task.get("status", "").lower() != "tamamlandı"
    ]

    high_priority_tasks = [
        task for task in open_tasks
        if task.get("priority", "").lower() in ["yüksek", "kritik"]
    ]

    pending_approvals = [
        approval for approval in approvals_data
        if approval.get("status", "").lower() == "bekliyor"
    ]

    active_project_tasks = [
        task for task in tasks_data
        if active_project_id and task.get("project_id") == active_project_id
    ]

    active_project_open_tasks = [
        task for task in active_project_tasks
        if task.get("status", "").lower() != "tamamlandı"
    ]

    active_project_high_priority_tasks = [
        task for task in active_project_open_tasks
        if task.get("priority", "").lower() in ["yüksek", "kritik"]
    ]

    active_project_approvals = [
        approval for approval in approvals_data
        if active_project_id and approval.get("project_id") == active_project_id
    ]

    active_project_pending_approvals = [
        approval for approval in active_project_approvals
        if approval.get("status", "").lower() == "bekliyor"
    ]

    active_project_outputs = [
        output for output in outputs_data
        if active_project_id and output.get("project_id") == active_project_id
    ]

    suggested_next_step = "Aktif projeye bağlı güncel bir durum yok. Sohbetten devam edebiliriz."

    if active_project_pending_approvals:
        suggested_next_step = f"{active_project.get('name', 'Proje')} için bekleyen onaylar var. Onay Merkezi'ni kontrol et."

    if active_project_pending_approvals and active_project_high_priority_tasks:
        suggested_next_step = f"{active_project.get('name', 'Proje')} için hem onaylar hem yüksek öncelikli görevler var."

    return {
        "success": True,
        "active_project": active_project,
        "active_project_id": active_project_id,
        "active_task": active_task,
        "active_task_id": active_task_id,
        "counts": {
            "active_projects": len(active_projects),
            "open_tasks": len(open_tasks),
            "high_priority_tasks": len(high_priority_tasks),
            "pending_approvals": len(pending_approvals),
            "outputs": len(outputs_data),
            "preferences": len(preferences_data),
        },
        "active_projects": active_projects,
        "open_tasks": open_tasks,
        "high_priority_tasks": high_priority_tasks,
        "pending_approvals": pending_approvals,
        "outputs": outputs_data[-10:],
        "active_project_context": {
            "tasks": active_project_tasks,
            "open_tasks": active_project_open_tasks,
            "high_priority_tasks": active_project_high_priority_tasks,
            "approvals": active_project_approvals,
            "pending_approvals": active_project_pending_approvals,
            "outputs": active_project_outputs[-10:],
        },
        "suggested_next_step": suggested_next_step,
    }


@app.get("/reminders")
def reminders():
    return load_reminders()


@app.post("/reminders")
def add_reminder(request: ReminderRequest):
    return add_reminder_to_storage({
        "id": request.id,
        "title": request.title,
        "remind_at": request.remind_at,
        "project_id": request.project_id,
        "task_id": request.task_id,
        "status": request.status,
        "notified": False,
        "notes": request.notes,
    })


@app.post("/reminders/from-chat")
def add_reminder_from_chat(request: ReminderFromChatRequest):
    clean_message = request.message.strip()

    if not clean_message:
        return {
            "success": False,
            "message": "Boş mesajdan hatırlatma oluşturulamaz.",
            "reminder": None,
            "reminders": load_reminders(),
        }

    reminder_data = extract_reminder_from_chat(
        message=clean_message,
        project_id=request.project_id,
        task_id=request.task_id,
    )

    result = add_reminder_to_storage(reminder_data)

    return {
        **result,
        "source_message": clean_message,
    }


@app.post("/reminders/due")
def due_reminders(request: ReminderDueRequest):
    return get_due_reminders(mark_as_notified=request.mark_as_notified)


@app.delete("/reminders/{reminder_id}")
def delete_reminder(reminder_id: str):
    clean_id = reminder_id.strip().lower()

    reminders_data = load_reminders()
    remaining_reminders = [
        reminder for reminder in reminders_data
        if reminder.get("id") != clean_id
    ]

    if len(remaining_reminders) == len(reminders_data):
        return {
            "success": False,
            "message": "Silinecek hatırlatma bulunamadı.",
            "reminder_id": clean_id,
            "reminders": reminders_data,
        }

    save_reminders(remaining_reminders)

    return {
        "success": True,
        "message": "Hatırlatma silindi.",
        "reminder_id": clean_id,
        "reminders": remaining_reminders,
    }


@app.get("/preferences")
def preferences():
    return load_preferences()


@app.post("/preferences")
def add_preference(request: PreferenceRequest):
    return add_preference_to_storage({
        "id": request.id,
        "project_id": request.project_id,
        "task_id": request.task_id,
        "category": request.category,
        "preference": request.preference,
        "source": request.source,
        "confidence": request.confidence,
        "status": request.status,
    })


@app.post("/preferences/from-chat")
def add_preference_from_chat(request: PreferenceFromChatRequest):
    clean_message = request.message.strip()

    if not clean_message:
        return {
            "success": False,
            "message": "Boş mesajdan tercih öğrenilemez.",
            "preference": None,
            "preferences": load_preferences(),
        }

    preference_data = extract_preference_from_chat(
        message=clean_message,
        project_id=request.project_id,
        task_id=request.task_id,
    )

    result = add_preference_to_storage(preference_data)

    return {
        **result,
        "source_message": clean_message,
    }


@app.delete("/preferences/{preference_id}")
def delete_preference(preference_id: str):
    clean_id = preference_id.strip().lower()

    preferences_data = load_preferences()
    remaining_preferences = [
        preference for preference in preferences_data
        if preference.get("id") != clean_id
    ]

    if len(remaining_preferences) == len(preferences_data):
        return {
            "success": False,
            "message": "Silinecek tercih bulunamadı.",
            "preference_id": clean_id,
            "preferences": preferences_data,
        }

    save_preferences(remaining_preferences)

    return {
        "success": True,
        "message": "Tercih silindi.",
        "preference_id": clean_id,
        "preferences": remaining_preferences,
    }


@app.get("/outputs")
def outputs():
    return load_outputs()


@app.post("/outputs")
def add_output(request: OutputRequest):
    return add_output_to_storage({
        "id": request.id,
        "title": request.title,
        "project_id": request.project_id,
        "task_id": request.task_id,
        "output_type": request.output_type,
        "content": request.content,
        "status": request.status,
        "notes": request.notes,
    })


@app.post("/outputs/from-chat")
def add_output_from_chat(request: OutputFromChatRequest):
    clean_content = request.content.strip()

    if not clean_content:
        return {
            "success": False,
            "message": "Boş sohbet çıktısı kaydedilemez.",
            "output": None,
            "outputs": load_outputs(),
        }

    output_data = create_output_from_chat_data(
        title=request.title,
        content=clean_content,
        output_type=request.output_type,
    )

    result = add_output_to_storage(output_data)

    return {
        **result,
        "active_project": get_active_project_data(),
        "active_task": get_active_task_data(),
    }


@app.delete("/outputs/{output_id}")
def delete_output(output_id: str):
    clean_id = output_id.strip().lower()

    outputs_data = load_outputs()
    remaining_outputs = [
        output for output in outputs_data
        if output.get("id") != clean_id
    ]

    if len(remaining_outputs) == len(outputs_data):
        return {
            "success": False,
            "message": "Silinecek çıktı bulunamadı.",
            "output_id": clean_id,
            "outputs": outputs_data,
        }

    save_outputs(remaining_outputs)

    return {
        "success": True,
        "message": "Çıktı silindi.",
        "output_id": clean_id,
        "outputs": remaining_outputs,
    }


@app.get("/approvals")
def approvals():
    return load_approvals()


@app.post("/approvals")
def add_approval(request: ApprovalRequest):
    return add_approval_to_storage({
        "id": request.id,
        "title": request.title,
        "project_id": request.project_id,
        "action_type": request.action_type,
        "risk_level": request.risk_level,
        "status": request.status,
        "description": request.description,
        "payload": request.payload,
        "notes": request.notes,
    })



@app.post("/approvals/from-chat")
def add_approval_from_chat(request: ApprovalFromChatRequest):
    clean_message = request.message.strip()

    if not clean_message:
        return {
            "success": False,
            "message": "Boş mesajdan onay isteği oluşturulamaz.",
        }

    approval_data = extract_approval_from_chat(
        message=clean_message,
        project_id=request.project_id,
    )

    result = add_approval_to_storage(approval_data)

    return {
        **result,
        "source_message": clean_message,
    }


@app.patch("/approvals/{approval_id}/approve")
def approve_approval(approval_id: str):
    clean_id = approval_id.strip().lower()

    approvals_data = load_approvals()
    outputs_data = load_outputs()

    for approval in approvals_data:
        if approval.get("id") == clean_id:
            approval["status"] = "onaylandı"
            save_approvals(approvals_data)

            return {
                "success": True,
                "message": "Onay isteği onaylandı.",
                "approval": approval,
                "approvals": approvals_data,
            }

    return {
        "success": False,
        "message": "Onaylanacak istek bulunamadı.",
        "approval_id": clean_id,
        "approvals": approvals_data,
    }


@app.patch("/approvals/{approval_id}/reject")
def reject_approval(approval_id: str):
    clean_id = approval_id.strip().lower()

    approvals_data = load_approvals()
    outputs_data = load_outputs()

    for approval in approvals_data:
        if approval.get("id") == clean_id:
            approval["status"] = "reddedildi"
            save_approvals(approvals_data)

            return {
                "success": True,
                "message": "Onay isteği reddedildi.",
                "approval": approval,
                "approvals": approvals_data,
            }

    return {
        "success": False,
        "message": "Reddedilecek istek bulunamadı.",
        "approval_id": clean_id,
        "approvals": approvals_data,
    }


@app.delete("/approvals/{approval_id}")
def delete_approval(approval_id: str):
    clean_id = approval_id.strip().lower()

    approvals_data = load_approvals()
    outputs_data = load_outputs()
    remaining_approvals = [
        approval for approval in approvals_data
        if approval.get("id") != clean_id
    ]

    if len(remaining_approvals) == len(approvals_data):
        return {
            "success": False,
            "message": "Silinecek onay isteği bulunamadı.",
            "approval_id": clean_id,
            "approvals": approvals_data,
        }

    save_approvals(remaining_approvals)

    return {
        "success": True,
        "message": "Onay isteği silindi.",
        "approval_id": clean_id,
        "approvals": remaining_approvals,
    }


@app.get("/tasks")
def tasks():
    return load_tasks()


@app.post("/tasks")
def add_task(request: TaskRequest):
    return add_task_to_storage({
        "id": request.id,
        "title": request.title,
        "project_id": request.project_id,
        "status": request.status,
        "priority": request.priority,
        "description": request.description,
        "notes": request.notes,
    })


@app.post("/tasks/from-chat")
def add_task_from_chat(request: TaskFromChatRequest):
    clean_message = request.message.strip()

    if not clean_message:
        return {
            "success": False,
            "message": "Boş mesajdan görev oluşturulamaz.",
        }

    task_data = extract_task_from_chat(
        message=clean_message,
        project_id=request.project_id,
    )

    result = add_task_to_storage(task_data)

    return {
        **result,
        "source_message": clean_message,
    }


@app.patch("/tasks/{task_id}/complete")
def complete_task(task_id: str):
    clean_id = task_id.strip().lower()

    tasks_data = load_tasks()

    for task in tasks_data:
        if task.get("id") == clean_id:
            task["status"] = "tamamlandı"
            save_tasks(tasks_data)

            return {
                "success": True,
                "message": "Görev tamamlandı.",
                "task": task,
                "tasks": tasks_data,
            }

    return {
        "success": False,
        "message": "Tamamlanacak görev bulunamadı.",
        "task_id": clean_id,
        "tasks": tasks_data,
    }


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    clean_id = task_id.strip().lower()

    tasks_data = load_tasks()
    remaining_tasks = [
        task for task in tasks_data
        if task.get("id") != clean_id
    ]

    if len(remaining_tasks) == len(tasks_data):
        return {
            "success": False,
            "message": "Silinecek görev bulunamadı.",
            "task_id": clean_id,
            "tasks": tasks_data,
        }

    save_tasks(remaining_tasks)

    return {
        "success": True,
        "message": "Görev silindi.",
        "task_id": clean_id,
        "tasks": remaining_tasks,
    }


@app.get("/memory")
def memory():
    return load_memory()


@app.get("/projects")
def projects():
    return load_projects()


@app.post("/projects")
def add_project(request: ProjectRequest):
    return add_project_to_storage({
        "id": request.id,
        "name": request.name,
        "type": request.type,
        "status": request.status,
        "description": request.description,
        "main_goals": request.main_goals,
        "notes": request.notes,
    })


@app.post("/projects/from-chat")
def add_project_from_chat(request: ProjectFromChatRequest):
    clean_message = request.message.strip()

    if not clean_message:
        return {
            "success": False,
            "message": "Boş mesajdan proje oluşturulamaz.",
        }

    project_data = extract_project_from_chat(clean_message)
    result = add_project_to_storage(project_data)

    return {
        **result,
        "source_message": clean_message,
    }


@app.delete("/projects/{project_id}")
def delete_project(project_id: str):
    clean_id = project_id.strip().lower()

    projects_data = load_projects()
    remaining_projects = [
        project for project in projects_data
        if project.get("id") != clean_id
    ]

    if len(remaining_projects) == len(projects_data):
        return {
            "success": False,
            "message": "Silinecek proje bulunamadı.",
            "project_id": clean_id,
            "projects": projects_data,
        }

    save_projects(remaining_projects)

    return {
        "success": True,
        "message": "Proje silindi.",
        "project_id": clean_id,
        "projects": remaining_projects,
    }


@app.post("/memory/rules")
def add_memory_rule(request: MemoryRuleRequest):
    clean_rule = request.rule.strip()

    if not clean_rule:
        return {
            "success": False,
            "message": "Boş kural eklenemez.",
        }

    memory_data = load_memory()

    if "rules" not in memory_data or not isinstance(memory_data["rules"], list):
        memory_data["rules"] = []

    if clean_rule in memory_data["rules"]:
        return {
            "success": True,
            "message": "Bu kural zaten hafızada vardı.",
            "rule": clean_rule,
            "rules": memory_data["rules"],
        }

    memory_data["rules"].append(clean_rule)
    save_memory(memory_data)

    return {
        "success": True,
        "message": "Kural hafızaya eklendi.",
        "rule": clean_rule,
        "rules": memory_data["rules"],
    }


@app.post("/memory/rules/from-chat")
def add_memory_rule_from_chat(request: MemoryFromChatRequest):
    message = request.message.strip()

    if not message:
        return {
            "success": False,
            "message": "Boş mesajdan kural çıkarılamaz.",
        }

    cleanup_phrases = [
        "bunu hafızana yaz",
        "bunu hafızaya yaz",
        "bunu unutma",
        "hafızana yaz",
        "hafızaya yaz",
        "unutma",
        "bundan sonra",
        "Bunu hafızana yaz",
        "Bunu hafızaya yaz",
        "Bunu unutma",
        "Hafızana yaz",
        "Hafızaya yaz",
        "Unutma",
        "Bundan sonra",
    ]

    rule = message

    for phrase in cleanup_phrases:
        rule = rule.replace(phrase, "")

    rule = rule.strip(" .,!;:-")

    if not rule:
        return {
            "success": False,
            "message": "Mesajdan kural çıkarılamadı.",
        }

    memory_data = load_memory()

    if "rules" not in memory_data or not isinstance(memory_data["rules"], list):
        memory_data["rules"] = []

    if rule in memory_data["rules"]:
        return {
            "success": True,
            "message": "Bu kural zaten hafızada vardı.",
            "rule": rule,
            "rules": memory_data["rules"],
        }

    memory_data["rules"].append(rule)
    save_memory(memory_data)

    return {
        "success": True,
        "message": "Kural sohbet mesajından hafızaya eklendi.",
        "rule": rule,
        "rules": memory_data["rules"],
    }


@app.post("/speech/transcribe")
async def transcribe_speech(file: UploadFile = File(...)):
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
        temp_path = temp_audio.name
        content = await file.read()
        temp_audio.write(content)

    try:
        return transcribe_audio_file(temp_path)
    except Exception as error:
        print("Vex transcribe hata:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
            "text": "",
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@app.post("/speech/record-and-transcribe")
def record_and_transcribe_speech(request: RecordSpeechRequest):
    duration = max(1.0, min(float(request.duration_seconds), 20.0))

    try:
        print(f"Vex mikrofon kaydı başlıyor: {duration} saniye")
        print("Şimdi konuşabilirsin Mert...")

        audio_data = sd.rec(
            int(duration * WHISPER_SAMPLE_RATE),
            samplerate=WHISPER_SAMPLE_RATE,
            channels=WHISPER_CHANNELS,
            dtype="float32",
            **get_microphone_device_kwargs(),
        )

        sd.wait()

        print("Vex mikrofon kaydı bitti, yazıya çevriliyor...")

        max_volume = float(np.max(np.abs(audio_data))) if audio_data.size else 0
        average_volume = float(np.mean(np.abs(audio_data))) if audio_data.size else 0

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_path = temp_audio.name

        try:
            save_recording_to_wav(audio_data, temp_path)
            result = transcribe_audio_file(temp_path)

            return {
                **result,
                "duration_seconds": duration,
                "max_volume": max_volume,
                "average_volume": average_volume,
            }
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    except Exception as error:
        print("Vex record-and-transcribe hata:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
            "text": "",
        }


@app.post("/speech/record/start")
def start_speech_recording():
    global recording_stream
    global recording_chunks
    global is_recording_active

    try:
        if is_recording_active:
            return {
                "success": False,
                "message": "Kayıt zaten devam ediyor.",
            }

        recording_chunks = []

        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Vex kayıt uyarısı: {status}")

            recording_chunks.append(indata.copy())

        print("Vex manuel mikrofon kaydı başladı. Mert konuşabilir.")

        recording_stream = sd.InputStream(
            samplerate=WHISPER_SAMPLE_RATE,
            channels=WHISPER_CHANNELS,
            dtype="float32",
            callback=audio_callback,
            **get_microphone_device_kwargs(),
        )

        recording_stream.start()
        is_recording_active = True

        return {
            "success": True,
            "message": "Kayıt başladı.",
        }

    except Exception as error:
        recording_stream = None
        recording_chunks = []
        is_recording_active = False

        print("Vex kayıt başlatma hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
        }


@app.post("/speech/record/stop-and-transcribe")
def stop_speech_recording_and_transcribe():
    global recording_stream
    global recording_chunks
    global is_recording_active

    temp_path = ""

    try:
        if not is_recording_active or recording_stream is None:
            return {
                "success": False,
                "message": "Aktif kayıt bulunamadı.",
                "text": "",
            }

        print("Vex manuel mikrofon kaydı durduruluyor...")

        recording_stream.stop()
        recording_stream.close()
        recording_stream = None
        is_recording_active = False

        if not recording_chunks:
            return {
                "success": False,
                "message": "Ses kaydı boş geldi.",
                "text": "",
                "max_volume": 0,
                "average_volume": 0,
            }

        audio_data = np.concatenate(recording_chunks, axis=0)
        recording_chunks = []

        max_volume = float(np.max(np.abs(audio_data))) if audio_data.size else 0
        average_volume = float(np.mean(np.abs(audio_data))) if audio_data.size else 0

        print(f"Vex kayıt ses seviyesi — max: {max_volume}, ortalama: {average_volume}")

        if max_volume < 0.001:
            return {
                "success": False,
                "message": "Ses çok düşük geldi veya mikrofon sessiz kaldı.",
                "text": "",
                "max_volume": max_volume,
                "average_volume": average_volume,
            }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_path = temp_audio.name

        save_recording_to_wav(audio_data, temp_path)
        result = transcribe_audio_file(temp_path)

        text = result.get("text", "").strip()

        if not text:
            return {
                "success": False,
                "message": "Whisper ses aldı ama metin çıkaramadı.",
                "text": "",
                "language": result.get("language"),
                "language_probability": result.get("language_probability"),
                "max_volume": max_volume,
                "average_volume": average_volume,
            }

        return {
            **result,
            "max_volume": max_volume,
            "average_volume": average_volume,
        }

    except Exception as error:
        print("Vex kayıt durdurma/transcribe hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
            "text": "",
        }

    finally:
        recording_stream = None
        recording_chunks = []
        is_recording_active = False

        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass



@app.post("/speech/listen-and-transcribe")
def listen_and_transcribe_speech(request: ListenSpeechRequest):
    max_seconds = max(2.0, min(float(request.max_seconds), 60.0))
    silence_seconds = max(0.25, min(float(request.silence_seconds), 5.0))
    peak_threshold = max(0.001, float(request.peak_threshold))
    average_threshold = max(0.0005, float(request.average_threshold))

    audio_queue = queue.Queue()
    collected_chunks: list[np.ndarray] = []
    pre_buffer_chunks: list[np.ndarray] = []

    block_duration = 0.2
    block_size = int(WHISPER_SAMPLE_RATE * block_duration)
    pre_buffer_limit = int(0.8 / block_duration)

    speech_started = False
    recording_start_time = time.monotonic()
    speech_start_time = 0.0
    last_voice_time = 0.0

    print("Vex otomatik dinleme başladı. Mert konuşabilir.")

    def audio_callback(indata, frames, callback_time, status):
        if status:
            print(f"Vex otomatik dinleme uyarısı: {status}")

        audio_queue.put(indata.copy())

    try:
        with sd.InputStream(
            samplerate=WHISPER_SAMPLE_RATE,
            channels=WHISPER_CHANNELS,
            dtype="float32",
            blocksize=block_size,
            callback=audio_callback,
            **get_microphone_device_kwargs(),
        ):
            while True:
                now = time.monotonic()

                if now - recording_start_time > max_seconds:
                    print("Vex otomatik dinleme maksimum süreye ulaştı.")
                    break

                try:
                    chunk = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                chunk_peak = float(np.max(np.abs(chunk))) if chunk.size else 0
                chunk_average = float(np.mean(np.abs(chunk))) if chunk.size else 0

                has_voice = (
                    chunk_peak >= peak_threshold or
                    chunk_average >= average_threshold
                )

                if not speech_started:
                    pre_buffer_chunks.append(chunk)

                    if len(pre_buffer_chunks) > pre_buffer_limit:
                        pre_buffer_chunks.pop(0)

                    if has_voice:
                        speech_started = True
                        speech_start_time = now
                        last_voice_time = now
                        collected_chunks.extend(pre_buffer_chunks)
                        pre_buffer_chunks = []
                        collected_chunks.append(chunk)
                        print("Vex konuşmayı algıladı.")
                else:
                    collected_chunks.append(chunk)

                    if has_voice:
                        last_voice_time = now

                    speech_duration = now - speech_start_time
                    silence_duration = now - last_voice_time

                    if speech_duration >= 0.6 and silence_duration >= silence_seconds:
                        print("Vex sessizliği algıladı, kayıt otomatik duruyor.")
                        break

        if not collected_chunks:
            return {
                "success": False,
                "message": "Konuşma algılanmadı.",
                "text": "",
                "max_volume": 0,
                "average_volume": 0,
            }

        audio_data = np.concatenate(collected_chunks, axis=0)

        max_volume = float(np.max(np.abs(audio_data))) if audio_data.size else 0
        average_volume = float(np.mean(np.abs(audio_data))) if audio_data.size else 0

        print(f"Vex otomatik kayıt ses seviyesi — max: {max_volume}, ortalama: {average_volume}")

        if max_volume < 0.001:
            return {
                "success": False,
                "message": "Ses çok düşük geldi veya mikrofon sessiz kaldı.",
                "text": "",
                "max_volume": max_volume,
                "average_volume": average_volume,
            }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_path = temp_audio.name

        try:
            save_recording_to_wav(audio_data, temp_path)
            result = transcribe_audio_file(temp_path)

            text = result.get("text", "").strip()

            if not text:
                return {
                    "success": False,
                    "message": "Whisper ses aldı ama metin çıkaramadı.",
                    "text": "",
                    "language": result.get("language"),
                    "language_probability": result.get("language_probability"),
                    "max_volume": max_volume,
                    "average_volume": average_volume,
                }

            return {
                **result,
                "max_volume": max_volume,
                "average_volume": average_volume,
            }
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    except Exception as error:
        print("Vex otomatik dinleme/transcribe hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
            "text": "",
        }



def build_memory_text(memory) -> str:
    if not memory:
        return "Henüz kalıcı hafıza kaydı yok."

    try:
        if isinstance(memory, dict):
            lines = []

            for key, value in memory.items():
                if isinstance(value, list):
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"- {item}")
                else:
                    lines.append(f"{key}: {value}")

            return "\n".join(lines) if lines else "Henüz kalıcı hafıza kaydı yok."

        if isinstance(memory, list):
            return "\n".join([f"- {item}" for item in memory]) if memory else "Henüz kalıcı hafıza kaydı yok."

        return str(memory)
    except Exception:
        return "Hafıza okunurken hata oluştu."


def build_projects_text(projects: list[dict]) -> str:
    if not projects:
        return "Henüz kayıtlı proje yok."

    lines = []

    for project in projects:
        lines.append(f"- {project.get('name', project.get('id', 'İsimsiz proje'))}")
        lines.append(f"  id: {project.get('id', '')}")
        lines.append(f"  tür: {project.get('type', '')}")
        lines.append(f"  durum: {project.get('status', '')}")

        description = project.get("description", "")
        if description:
            lines.append(f"  açıklama: {description}")

    return "\n".join(lines)

def build_conversation_text(history: list[ChatMessage], current_message: str) -> str:
    conversation_lines = []

    for item in history[-12:]:
        if item.sender == "Sen":
            conversation_lines.append(f"Mert: {item.text}")
        else:
            conversation_lines.append(f"Vex: {item.text}")

    conversation_lines.append(f"Mert: {current_message}")

    return "\n".join(conversation_lines)



@app.post("/shopify/content-from-chat")
def shopify_content_from_chat(request: ShopifyContentFromChatRequest):
    try:
        clean_message = request.message.strip()

        if not clean_message:
            return {
                "success": False,
                "message": "Boş mesajdan Shopify içeriği hazırlanamaz.",
                "content": None,
            }

        result = extract_shopify_content_from_chat(
            message=clean_message,
            project_id=request.project_id,
            task_id=request.task_id,
            language=request.language,
        )

        if result.get("success") and result.get("content"):
            result["formatted_output"] = build_shopify_content_output_text(result["content"])

        return result

    except Exception as error:
        print("Vex Shopify içerik hazırlama hatası:")
        traceback.print_exc()

        return {
            "success": False,
            "message": str(error),
            "content": None,
        }


@app.post("/chat")
def chat(request: ChatRequest):
    client = get_gemini_client()

    if client is None:
        return {
            "reply": "Gemini API key bulunamadı. .env dosyasında GEMINI_API_KEY var mı kontrol edelim.",
        }

    try:
        memory_data = load_memory()
        projects_data = load_projects()
        tasks_data = load_tasks()
        approvals_data = load_approvals()
        outputs_data = load_outputs()

        try:
            preferences_data = load_preferences()
        except Exception:
            preferences_data = []

        active_project_data = get_active_project_data()
        active_task_data = get_active_task_data()

        active_project_id = active_project_data.get("project_id", "")
        active_project = active_project_data.get("project")
        active_task_id = active_task_data.get("task_id", "")
        active_task = active_task_data.get("task")

        try:
            active_brand_profile = get_brand_profile_for_project(active_project_id)
        except Exception:
            active_brand_profile = None

        try:
            relevant_preferences = get_relevant_preferences(
                project_id=active_project_id,
                task_id=active_task_id,
            )
        except Exception:
            relevant_preferences = []

        open_tasks = [
            task for task in tasks_data
            if task.get("status", "").lower() != "tamamlandı"
        ]

        high_priority_tasks = [
            task for task in open_tasks
            if task.get("priority", "").lower() in ["yüksek", "kritik"]
        ]

        pending_approvals = [
            approval for approval in approvals_data
            if approval.get("status", "").lower() == "bekliyor"
        ]

        active_project_tasks = [
            task for task in tasks_data
            if active_project_id and task.get("project_id") == active_project_id
        ]

        active_project_open_tasks = [
            task for task in active_project_tasks
            if task.get("status", "").lower() != "tamamlandı"
        ]

        active_project_high_priority_tasks = [
            task for task in active_project_open_tasks
            if task.get("priority", "").lower() in ["yüksek", "kritik"]
        ]

        active_project_approvals = [
            approval for approval in approvals_data
            if active_project_id and approval.get("project_id") == active_project_id
        ]

        active_project_pending_approvals = [
            approval for approval in active_project_approvals
            if approval.get("status", "").lower() == "bekliyor"
        ]

        active_project_outputs = [
            output for output in outputs_data
            if active_project_id and output.get("project_id") == active_project_id
        ]

        active_task_outputs = [
            output for output in outputs_data
            if active_task_id and output.get("task_id") == active_task_id
        ]

        workspace_summary_data = {
            "active_project": active_project_data.get("project") if active_project_data else None,
            "active_task": active_task_data.get("task") if active_task_data else None,
            "learned_preferences": relevant_preferences,
        }

        memory_text = build_memory_text(memory_data)
        
        # Proje ve görev listelerini yapay zekaya çok detaylı vermeyeceğiz
        # Sadece bağlamı vermek yeterli, aksi takdirde sürekli "şu görev var" diyor
        workspace_text = json.dumps(workspace_summary_data, ensure_ascii=False, indent=2)

        system_context = f"""
Senin adın Vex. Sen Mert'in kişisel yapay zeka iş arkadaşısın.

Kalıcı hafızan ve kurallar:
{memory_text}

Aktif bağlam:
{workspace_text}

ÇOK ÖNEMLİ DAVRANIŞ KURALLARI:
1. Mert ne sorduysa/ne istediyse SADECE ona odaklan. 
2. Asla "Şu görev var", "Şu proje bekliyor", "Buna başlayalım mı?" gibi YÖNLENDİRMELER YAPMA.
3. Mesajlarının girişinde "şunu hallettik", "şu taslağımız cebimizde" gibi durum özetleri VERME.
4. "Mert", "Selam Mert" kelimelerini her cümlenin başına koyma, çok doğal ve kısa yanıt ver.
5. Bir soru sorulduğunda en kısa ve net cevabı ver, uzatma.
"""

        conversation_text = build_conversation_text(
            history=request.history,
            current_message=request.message,
        )

        prompt = f"""
{system_context}

Konuşma geçmişi:
{conversation_text}

Vex olarak Mert'e cevap ver.
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )

        return {
            "reply": response.text or "Cevap oluşturdum ama metin boş döndü.",
        }

    except Exception as error:
        print("Vex chat endpoint hatası:")
        traceback.print_exc()

        return {
            "reply": f"Chat tarafında teknik bir hata oluştu Mert: {str(error)}",
        }


# ==========================================
# COMPUTER USE / BİLGİSAYAR KONTROL MODÜLÜ
# ==========================================

import pyautogui
import base64
import io
import webbrowser
import shlex
import subprocess
from datetime import datetime
import json
import re

computer_use_logs: list[str] = []
computer_use_running = False
computer_use_stop_event = False
current_computer_task_id = None
last_computer_intent = "unknown"
last_computer_action = "none"

# Manual step memory
manual_pending_action = None
manual_pending_screenshot = None

APP_ALLOWLIST = [
    "Spotify",
    "Safari",
    "Google Chrome",
    "Visual Studio Code",
    "Finder",
    "Mail",
    "Notes",
    "Terminal"
]

def add_computer_log(task_id: str, text: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    tid_label = f" [{task_id[:6]}]" if task_id else ""
    line = f"[{ts}]{tid_label} {text}"
    print(line)
    computer_use_logs.append(line)

def check_accessibility_permission() -> bool:
    try:
        return True
    except Exception:
        return False

def take_screenshot() -> dict:
    try:
        screenshot = pyautogui.screenshot()
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return {
            "success": True,
            "image_base64": img_b64,
            "width": screenshot.width,
            "height": screenshot.height,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

def route_instruction_intent(instruction: str) -> dict:
    try:
        client = get_gemini_client()
        if not client:
            return {"intent": "unknown", "confidence": 0.0}

        prompt = f'Kullanıcının bilgisayar kontrol talimatını analiz et ve niyetini (intent) sınıflandır.\n\nTalimat: "{instruction}"\n\nSadece şu JSON formatında cevap ver (Markdown, açıklama veya ek yazı yazma):\n{{\n  "intent": "open_app|open_url|observe_screen|ui_click_task|type_task|unknown",\n  "app_name": "Spotify|Safari|Google Chrome|Visual Studio Code|Finder|Mail|Notes|Terminal veya null",\n  "url": "Açılması istenen URL veya null",\n  "confidence": 0.95\n}}\n\nEğer talimatta Shopify\'ı açmak geçiyorsa intent "open_url" olmalıdır.'

        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z0-9]*\n", "", raw)
            raw = re.sub(r"\n```$", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"Intent router error: {e}")
        return {"intent": "unknown", "confidence": 0.0}

def execute_computer_action(task_id: str, action_data: dict, instruction: str = "") -> dict:
    global computer_use_stop_event, last_computer_action
    if computer_use_stop_event:
        return {"success": False, "message": "Stopped by user"}

    action = action_data.get("action", "").lower()
    last_computer_action = action
    
    # 5. SELF-UI TRAP GUARD
    is_vex_dashboard_targeted = False
    thought = action_data.get("thought", "").lower()
    
    if "vex" in thought or "dashboard" in thought or "görevi başlat" in thought or "task" in thought:
        if "vex" not in instruction.lower() and "panel" not in instruction.lower():
            is_vex_dashboard_targeted = True

    if is_vex_dashboard_targeted and action in ("click", "double_click", "move"):
        add_computer_log(task_id, "SELF_UI_TRAP_BLOCKED: Vex tried to click its own control panel during an external task.")
        return {"success": False, "message": "SELF_UI_TRAP_BLOCKED: Vex tried to click its own control panel during an external task."}

    try:
        if action == "open_app":
            app_name = action_data.get("app_name")
            if not app_name or app_name not in APP_ALLOWLIST:
                add_computer_log(task_id, f"APP_NOT_ALLOWED_OR_UNKNOWN: '{app_name}'")
                return {"success": False, "message": "APP_NOT_ALLOWED_OR_UNKNOWN", "action": "open_app"}
            
            add_computer_log(task_id, f"OPEN_APP: Opening '{app_name}' securely.")
            subprocess.run(["open", "-a", app_name], check=True)
            return {"success": True, "action": "open_app", "app_name": app_name}

        elif action == "open_url":
            url = action_data.get("url")
            if not url:
                return {"success": False, "message": "URL required"}
            
            if not (url.startswith("http://") or url.startswith("https://")):
                add_computer_log(task_id, f"BLOCKED: Unsafe URL scheme in '{url}'")
                return {"success": False, "message": "SECURITY_BLOCKED: Unsafe URL scheme"}

            add_computer_log(task_id, f"OPEN_URL: Opening '{url}' securely.")
            webbrowser.open(url)
            return {"success": True, "action": "open_url", "url": url}

        elif action == "click":
            x, y = action_data.get("x"), action_data.get("y")
            if x is None or y is None:
                return {"success": False, "message": "x/y required"}
            pyautogui.click(x, y)
            add_computer_log(task_id, f"CLICK at ({x}, {y})")
            return {"success": True, "action": "click", "x": x, "y": y}

        elif action == "double_click":
            x, y = action_data.get("x"), action_data.get("y")
            if x is None or y is None:
                return {"success": False, "message": "x/y required"}
            pyautogui.doubleClick(x, y)
            add_computer_log(task_id, f"DOUBLE_CLICK at ({x}, {y})")
            return {"success": True, "action": "double_click", "x": x, "y": y}

        elif action == "type_text":
            text = action_data.get("text", "")
            if not text:
                return {"success": False, "message": "text required"}
            pyautogui.typewrite(text, interval=0.02)
            add_computer_log(task_id, f"TYPE_TEXT: {text[:40]}...")
            return {"success": True, "action": "type_text", "text": text}

        elif action == "press_key":
            key = action_data.get("key", "")
            if not key:
                return {"success": False, "message": "key required"}
            pyautogui.press(key)
            add_computer_log(task_id, f"PRESS_KEY: {key}")
            return {"success": True, "action": "press_key", "key": key}

        elif action == "hotkey":
            keys = action_data.get("keys", [])
            if not keys:
                return {"success": False, "message": "keys required"}
            pyautogui.hotkey(*keys)
            add_computer_log(task_id, f"HOTKEY: {'+'.join(keys)}")
            return {"success": True, "action": "hotkey", "keys": keys}

        elif action == "scroll":
            clicks = action_data.get("clicks", 3)
            pyautogui.scroll(clicks)
            add_computer_log(task_id, f"SCROLL: {clicks}")
            return {"success": True, "action": "scroll", "clicks": clicks}

        elif action == "wait":
            seconds = action_data.get("seconds", 1)
            import time
            time.sleep(seconds)
            add_computer_log(task_id, f"WAIT: {seconds}s")
            return {"success": True, "action": "wait", "seconds": seconds}

        elif action == "done":
            return {"success": True, "action": "done"}

        else:
            return {"success": False, "message": f"Unsupported action: {action}"}
            
    except Exception as e:
        add_computer_log(task_id, f"Execution Error: {e}")
        return {"success": False, "message": str(e)}

def analyze_screen_with_ai(image_base64: str, prompt: str) -> dict:
    try:
        client = get_gemini_client()
        if not client:
            return {"success": False, "message": "Gemini client not available"}

        image_part = {"mime_type": "image/png", "data": base64.b64decode(image_base64)}
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": image_part}
                ]}
            ],
        )
        return {"success": True, "analysis": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/computer/status")
def computer_status():
    global computer_use_running, computer_use_stop_event, current_computer_task_id, last_computer_intent, last_computer_action
    screenshot_data = take_screenshot()
    return {
        "success": True,
        "running": computer_use_running,
        "stopped": computer_use_stop_event,
        "active_task_id": current_computer_task_id,
        "last_intent": last_computer_intent,
        "last_action": last_computer_action,
        "accessibility_status": check_accessibility_permission(),
        "screenshot": screenshot_data,
        "logs": computer_use_logs[-50:],
        "manual_pending_action": manual_pending_action
    }

@app.get("/computer/screenshot")
def computer_screenshot():
    return take_screenshot()

@app.post("/computer/observe")
def computer_observe():
    try:
        screenshot = take_screenshot()
        if not screenshot.get("success"):
            return screenshot
        result = analyze_screen_with_ai(
            screenshot["image_base64"],
            "Bu ekran görüntüsünü detaylıca analiz et. Türkçe olarak ne gördüğünü açıkla. Butonlar, metinler, form alanları, menüler varsa bunları listele."
        )
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/computer/action")
def computer_action(request: dict):
    global current_computer_task_id
    task_id = current_computer_task_id or str(uuid.uuid4())[:8]
    return execute_computer_action(task_id, request)

@app.post("/computer/step/approve")
def computer_step_approve():
    global manual_pending_action, current_computer_task_id
    if not manual_pending_action:
        return {"success": False, "message": "Onay bekleyen manuel adım yok."}
    
    task_id = current_computer_task_id or str(uuid.uuid4())[:8]
    action_to_run = manual_pending_action
    manual_pending_action = None
    
    result = execute_computer_action(task_id, action_to_run)
    return {
        "success": True,
        "result": result,
        "message": f"Manuel adım onaylandı ve yürütüldü: {action_to_run.get('action')}"
    }

@app.post("/computer/step/reject")
def computer_step_reject():
    global manual_pending_action
    if not manual_pending_action:
        return {"success": False, "message": "Reddedilecek adım yok."}
    
    manual_pending_action = None
    return {"success": True, "message": "Önerilen adım reddedildi."}

@app.post("/computer/task")
def computer_task(request: dict):
    global computer_use_running, computer_use_stop_event, current_computer_task_id, last_computer_intent, manual_pending_action
    
    if computer_use_running:
        return {
            "success": False,
            "message": "Zaten aktif bir bilgisayar kontrol görevi çalışıyor! Lütfen önce onu durdurun.",
            "active_task_id": current_computer_task_id
        }

    instruction = request.get("instruction", "")
    mode = request.get("mode", "assisted_fast")
    max_steps = request.get("max_steps", 20)

    if not instruction:
        return {"success": False, "message": "Talimat (instruction) gereklidir."}

    task_id = str(uuid.uuid4())[:8]
    current_computer_task_id = task_id
    computer_use_running = True
    computer_use_stop_event = False
    
    add_computer_log(task_id, f"GÖREV BAŞLATILDI: {instruction} (Mod: {mode})")
    
    intent_data = route_instruction_intent(instruction)
    intent = intent_data.get("intent", "unknown")
    last_computer_intent = intent
    add_computer_log(task_id, f"Algılanan Niyet: {intent} (Güven Oranı: {intent_data.get('confidence', 0.0)})")

    if intent == "open_app":
        app_name = intent_data.get("app_name")
        res = execute_computer_action(task_id, {"action": "open_app", "app_name": app_name})
        computer_use_running = False
        return {"success": res.get("success"), "message": res.get("message"), "intent": intent, "steps": 1}

    elif intent == "open_url":
        url = intent_data.get("url")
        if "shopify" in instruction.lower() and not url:
            computer_use_running = False
            return {
                "success": True,
                "message": "Shopify admin URL'sini ayarlara eklemem gerekiyor.",
                "action": "ask_user"
            }
        
        res = execute_computer_action(task_id, {"action": "open_url", "url": url})
        computer_use_running = False
        return {"success": res.get("success"), "message": res.get("message"), "intent": intent, "steps": 1}

    elif intent == "observe_screen":
        obs_res = computer_observe()
        computer_use_running = False
        return {"success": True, "message": "Ekran analizi tamamlandı.", "analysis": obs_res.get("analysis")}

    try:
        for step in range(1, max_steps + 1):
            if computer_use_stop_event:
                add_computer_log(task_id, "Görev kullanıcı tarafından durduruldu.")
                return {"success": True, "message": "Stopped by user", "steps": step - 1}

            screenshot = take_screenshot()
            if not screenshot.get("success"):
                return screenshot

            prompt = f'Sen Vex\'in Bilgisayar Kontrol yapay zekasısın. Ekran görüntüsüne bakarak bir sonraki adımı seç.\n\nKural: Kendi Vex uygulamasındaki \'Görevi Başlat\', \'Durdur\' butonlarına veya kendi paneline KESİNLİKLE tıklama! Sadece diğer dış pencerelere odaklan.\n\nGörev: "{instruction}"\n\nSadece şu JSON formatında yanıt ver:\n{{\n  "thought": "Ekranda ne gördüğünü kısa açıkla",\n  "action": "click|double_click|type_text|press_key|hotkey|scroll|wait|done|ask_user",\n  "x": 100,\n  "y": 200,\n  "text": "yazılacak metin",\n  "key": "enter",\n  "keys": ["ctrl", "c"],\n  "clicks": 3,\n  "seconds": 1,\n  "confidence": 0.9,\n  "risk_level": "low|medium|high"\n}}'

            analysis = analyze_screen_with_ai(screenshot["image_base64"], prompt)
            if not analysis.get("success"):
                add_computer_log(task_id, f"AI analiz hatası: {analysis.get('message')}")
                return analysis

            try:
                raw = analysis["analysis"]
                if raw.startswith("```"):
                    raw = re.sub(r"^```[a-zA-Z0-9]*\n", "", raw)
                    raw = re.sub(r"\n```$", "", raw).strip()
                action_data = json.loads(raw)
            except Exception as e:
                add_computer_log(task_id, f"AI yanıtı geçerli JSON değil: {e}")
                return {"success": False, "message": "AI invalid response JSON", "raw": analysis.get("analysis")}

            action = action_data.get("action", "").lower()
            thought = action_data.get("thought", "")
            add_computer_log(task_id, f"Adım {step}: {action} - {thought[:60]}...")

            if action == "done":
                add_computer_log(task_id, "Görev başarıyla tamamlandı.")
                return {"success": True, "message": "Task completed", "steps": step}

            if action == "ask_user":
                question = action_data.get("text") or "Kullanıcı girdisi gerekiyor"
                add_computer_log(task_id, f"Vex soruyor: {question}")
                return {"success": True, "message": "AI needs input", "question": question, "steps": step}

            if mode == "manual_step":
                manual_pending_action = action_data
                add_computer_log(task_id, f"Adım {step} için onay bekleniyor: {action}")
                return {
                    "success": True,
                    "message": "Manual step approval required",
                    "step": step,
                    "proposed_action": action_data,
                    "screenshot": screenshot
                }

            result = execute_computer_action(task_id, action_data, instruction)
            if not result.get("success"):
                add_computer_log(task_id, f"Aksiyon başarısız oldu: {result.get('message')}")
                return result

            if action in ("click", "double_click", "type_text", "press_key", "hotkey"):
                import time
                time.sleep(0.5)

        add_computer_log(task_id, f"Maksimum adım ({max_steps}) sınırına ulaşıldı.")
        return {"success": True, "message": "Max steps reached", "steps": max_steps}

    finally:
        computer_use_running = False
        current_computer_task_id = None
# ==========================================
# GÜVENLİ SELF-EVOLUTION / KENDİ KENDİNE GELİŞİM AJANI
# ==========================================

import threading
import subprocess
import shutil
import time
import uuid
import re
from pathlib import Path

# === EMERGENCY SAFE MODE ===
SELF_EVOLUTION_SAFE_MODE = True  # Default: True

# === ALLOWED DIRECTORIES ===
ALLOWED_WORKSPACE_DIRS = [
    Path("/Users/mert/Vex/vex-app").resolve(),
    Path("/Users/mert/Vex/vex-backend").resolve(),
]

# === FORBIDDEN FILES / PATHS (glob matching) ===
FORBIDDEN_PATH_MARKERS = [
    ".env", ".env.", ".git", "node_modules", "src-tauri/target", "__pycache__",
    ".ssh", "*.pem", "*.key", "*.p12", "*.pfx", "*.sqlite", "*.db"
]

# === COMMAND ALLOWLIST ===
ALLOWED_COMMANDS = [
    "npm run build",
    "npm run dev",
    "npm run tauri dev",
    "python -m pytest",
    "pytest",
    "cargo build",
]

# === FORBIDDEN COMMAND PATTERNS ===
FORBIDDEN_COMMAND_PATTERNS = [
    r"\brm\b", r"\bsudo\b", r"\bcurl\b", r"\bwget\b", r"\bbash\b", r"\bsh\b",
    r"\bchmod\b", r"\bchown\b", r"\bdocker\b", r"\bgit reset\b", r"\bgit clean\b",
    r"\bgit push\b", r"\bpython -c\b", r"\bnode -e\b", r"\bopen\b", r"\bosascript\b",
    r"[>]{2}", r"[>]", r"\|", r"&&", r";",
]

# === SECRET REDACTION PATTERNS ===
SECRET_PATTERNS = [
    r"(?i)(api[_-]?key\s*[:=]\s*['\"\s]?)[A-Za-z0-9_-]{10,}(['\"\s]?)",
    r"(?i)(gemini[_-]?api[_-]?key\s*[:=]\s*['\"\s]?)[A-Za-z0-9_-]{10,}(['\"\s]?)",
    r"(?i)(secret\s*[:=]\s*['\"\s]?)[A-Za-z0-9_-]{10,}(['\"\s]?)",
    r"(?i)(password\s*[:=]\s*['\"\s]?)[A-Za-z0-9!@#$%^&*()_+-=]{6,}(['\"\s]?)",
    r"(?i)(token\s*[:=]\s*['\"\s]?)[A-Za-z0-9_-]{10,}(['\"\s]?)",
    r"(?i)(access[_-]?token\s*[:=]\s*['\"\s]?)[A-Za-z0-9_-]{10,}(['\"\s]?)",
    r"(?i)(refresh[_-]?token\s*[:=]\s*['\"\s]?)[A-Za-z0-9_-]{10,}(['\"\s]?)",
    r"(?i)(bearer\s*[:=]\s*['\"\s]?)[A-Za-z0-9_-]{10,}(['\"\s]?)",
    r"(?i)(authorization\s*[:=]\s*['\"\s]?)[A-Za-z0-9_-]{10,}(['\"\s]?)",
]

class EvolutionRequest(BaseModel):
    prompt: str

evolution_logs_list = []
is_evolution_running = False
pending_evolution_actions: list[dict] = []

# --- GÜVENLİK YARDIMCI FONKSİYONLARI ---

def add_evolution_log(level: str, text: str):
    redacted_text = text
    for pattern in SECRET_PATTERNS:
        redacted_text = re.sub(pattern, r"\1[REDACTED]\2", redacted_text)
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {redacted_text}"
    print(log_line)
    evolution_logs_list.append(log_line)

def is_safe_path(rel_path: str) -> tuple:
    if not rel_path.strip():
        return False, "Dosya yolu boş."
    
    # Block reading .env file explicitly under any circumstance
    if ".env" in rel_path.lower():
        add_evolution_log("SECURITY-BLOCK", "SECURITY_BLOCKED: unsafe path rejected - .env files are forbidden")
        return False, "SECURITY_BLOCKED: unsafe path rejected"
        
    try:
        root = Path("/Users/mert/Vex")
        path_to_check = (root / rel_path).resolve()
    except Exception:
        add_evolution_log("SECURITY-BLOCK", f"SECURITY_BLOCKED: unsafe path rejected - unresolvable path: {rel_path}")
        return False, "SECURITY_BLOCKED: unsafe path rejected"
        
    # Sıkı Sandbox Kontrolü (os.path.commonpath)
    allowed = False
    for dir_path in ALLOWED_WORKSPACE_DIRS:
        try:
            # check if path_to_check is nested inside dir_path
            common = os.path.commonpath([str(dir_path), str(path_to_check)])
            if common == str(dir_path):
                allowed = True
                break
        except ValueError:
            continue
            
    if not allowed:
        add_evolution_log("SECURITY-BLOCK", f"SECURITY_BLOCKED: unsafe path rejected - resolved path {path_to_check} is outside allowed directories")
        return False, "SECURITY_BLOCKED: unsafe path rejected"
        
    path_str = str(path_to_check).lower()
    for marker in FORBIDDEN_PATH_MARKERS:
        if "*" in marker:
            pattern = marker.replace(".", r"\.").replace("*", r".*")
            if re.search(pattern, path_str):
                add_evolution_log("SECURITY-BLOCK", f"SECURITY_BLOCKED: unsafe path rejected - forbidden pattern matched: {marker}")
                return False, "SECURITY_BLOCKED: unsafe path rejected"
        else:
            if marker.lower() in path_str:
                add_evolution_log("SECURITY-BLOCK", f"SECURITY_BLOCKED: unsafe path rejected - forbidden file/folder marker matched: {marker}")
                return False, "SECURITY_BLOCKED: unsafe path rejected"
                
    return True, ""

def is_command_safe(command: str) -> tuple:
    if not command.strip():
        return False, "Komut boş."
        
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if re.search(pattern, command):
            return False, "Güvenlik duvarı: Komutta yasaklı bir shell operatörü veya komut tespit edildi."
            
    allowed = False
    for allowed_cmd in ALLOWED_COMMANDS:
        if command.strip() == allowed_cmd or command.strip().startswith(allowed_cmd + " "):
            allowed = True
            break
            
    if not allowed:
        return False, "Güvenlik duvarı: Komut izin verilen komutlar listesinde (Allowlist) bulunamadı."
        
    return True, ""

def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = re.sub(pattern, r"\1[REDACTED]\2", redacted)
    return redacted

def create_pending_action(action_type: str, data: dict) -> dict:
    action_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    pending = {
        "id": action_id,
        "action_type": action_type,
        "status": "pending",
        "created_at": now,
        "target_path": data.get("path", ""),
        "command": data.get("command", ""),
        "reason": data.get("thought", "Açıklama belirtilmedi."),
        "risk_level": data.get("risk_level", "normal"),
    }
    if action_type in ("WRITE_FILE", "REPLACE_IN_FILE"):
        pending["before_content"] = data.get("before_content", "")
        if action_type == "WRITE_FILE":
            pending["after_content"] = data.get("content", "")
        else:
            pending["replacement"] = data.get("replace", "")
    pending_evolution_actions.append(pending)
    return pending

def find_pending_action(action_id: str):
    for action in pending_evolution_actions:
        if action["id"] == action_id:
            return action
    return None

def execute_approved_action(action: dict, workspace_root: Path) -> str:
    # RE-RUN SECURITY CHECKS RIGHT BEFORE EXECUTION FOR ABSOLUTE SAFETY!
    action_type = action["action_type"]
    rel_path = action.get("target_path", "")
    cmd = action.get("command", "")
    
    if action_type in ("WRITE_FILE", "REPLACE_IN_FILE"):
        safe, msg = is_safe_path(rel_path)
        if not safe:
            add_evolution_log("SECURITY-BLOCK", f"YENİDEN KONTROL ENGELLEMESİ: {msg}")
            return f"GÜVENLİK ENGELLEMESİ: {msg}"
            
    if action_type == "EXECUTE_COMMAND":
        safe, msg = is_command_safe(cmd)
        if not safe:
            add_evolution_log("SECURITY-BLOCK", f"YENİDEN KONTROL ENGELLEMESİ: {msg}")
            return f"GÜVENLİK ENGELLEMESİ: {msg}"

    if action_type == "WRITE_FILE":
        content = redact_secrets(action.get("after_content", ""))
        file_path = workspace_root / rel_path
        if file_path.exists():
            backup_path = file_path.with_suffix(f".before-evolution-{int(time.time())}{file_path.suffix}")
            shutil.copy2(file_path, backup_path)
            add_evolution_log("INFO", f"Yedek alındı: {backup_path.name}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        add_evolution_log("SUCCESS", f"Kullanıcı onayı ile dosya yazıldı: {rel_path}")
        return f"BAŞARI ({action_type}): {rel_path} dosyası yazıldı."
        
    elif action_type == "REPLACE_IN_FILE":
        replacement = redact_secrets(action.get("replacement", ""))
        search_text = action.get("before_content", "")
        file_path = workspace_root / rel_path
        if file_path.exists():
            current_content = file_path.read_text(encoding="utf-8")
            if search_text in current_content:
                backup_path = file_path.with_suffix(f".before-evolution-{int(time.time())}{file_path.suffix}")
                shutil.copy2(file_path, backup_path)
                add_evolution_log("INFO", f"Yedek alındı: {backup_path.name}")
                new_content = current_content.replace(search_text, replacement, 1)
                file_path.write_text(new_content, encoding="utf-8")
                add_evolution_log("SUCCESS", f"Kullanıcı onayı ile dosya düzenlendi: {rel_path}")
                return f"BAŞARI ({action_type}): {rel_path} içinde değişim yapıldı."
            else:
                return f"HATA: Aranan metin {rel_path} içinde bulunamadı."
        else:
            return f"HATA: {rel_path} dosyası bulunamadı."
            
    elif action_type == "EXECUTE_COMMAND":
        try:
            # execute command securely using shlex split if possible or with safe parameters
            # we block shell injection above, so shell=True is only used for allowed command lines
            result = subprocess.run(cmd, shell=True, cwd=str(workspace_root), text=True, capture_output=True, timeout=120)
            stdout = redact_secrets(result.stdout or "")
            stderr = redact_secrets(result.stderr or "")
            ec = result.returncode
            add_evolution_log("INFO", f"Komut tamamlandı. Exit Code: {ec}")
            
            # Geri dönüş ve yedek bilgilendirme mesajı ekleme
            build_info = ""
            if ec != 0:
                build_info = "\n[BİLGİ] Eğer derleme/build başarısız olduysa, yapılan değişiklikleri geri almak için klasördeki en son oluşturulan '.before-evolution-[timestamp]' yedek dosyasını asıl dosyanın üzerine yazabilirsiniz."
                
            return f"KOMUT ÇIKTISI (Exit Code: {ec}):\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}{build_info}"
        except subprocess.TimeoutExpired:
            return "HATA: Komut zaman aşımına uğradı."
        except Exception as e:
            return f"HATA: {str(e)}"
            
    return f"HATA: Bilinmeyen eylem tipi: {action_type}"

def wait_for_action_approval(action_id: str, max_wait: int = 300) -> tuple:
    start = time.time()
    while time.time() - start < max_wait:
        action = find_pending_action(action_id)
        if action is None:
            return False, "İşlem bulunamadı."
        if action["status"] == "approved":
            return True, "İşlem onaylandı."
        elif action["status"] == "rejected":
            return False, "Mert bu işlemi reddetti."
        time.sleep(0.5)
    act = find_pending_action(action_id)
    if act:
        act["status"] = "expired"
    return False, "İşlem zaman aşımına uğradı."

def run_safe_evolution_step(action_data: dict, workspace_root: Path) -> str:
    action = action_data.get("action", "").upper()
    rel_path = action_data.get("path", "")
    cmd = action_data.get("command", "")
    
    if action == "READ_FILE":
        safe, msg = is_safe_path(rel_path)
        if not safe:
            add_evolution_log("SECURITY-BLOCK", msg)
            return f"GÜVENLİK ENGELLEMESİ: {msg}"
        fp = workspace_root / rel_path
        if fp.exists():
            return f"DOSYA İÇERİĞİ ({rel_path}):\n{fp.read_text(encoding='utf-8')}"
        return f"HATA: {rel_path} dosyası bulunamadı."
        
    elif action == "LIST_FILES":
        safe, msg = is_safe_path(rel_path)
        if not safe:
            add_evolution_log("SECURITY-BLOCK", msg)
            return f"GÜVENLİK ENGELLEMESİ: {msg}"
        dp = workspace_root / rel_path
        if dp.exists() and dp.is_dir():
            files = [str(f.relative_to(workspace_root)) for f in dp.glob("*")]
            return f"KLASÖR LİSTESİ ({rel_path}):\n" + "\n".join(files)
        return f"HATA: {rel_path} klasör bulunamadı."
        
    elif action == "WRITE_FILE":
        safe, msg = is_safe_path(rel_path)
        if not safe:
            add_evolution_log("SECURITY-BLOCK", msg)
            return f"GÜVENLİK ENGELLEMESİ: {msg}"
            
        content = redact_secrets(action_data.get("content", ""))
        bc = ""
        fp = workspace_root / rel_path
        if fp.exists():
            bc = fp.read_text(encoding="utf-8")
            
        pd = {
            "path": rel_path,
            "content": content,
            "thought": action_data.get("thought", "Yeni dosya yazılacak."),
            "risk_level": "yüksek",
            "before_content": bc
        }
        p = create_pending_action("WRITE_FILE", pd)
        add_evolution_log("WAITING-APPROVAL", f"Kullanıcı onayı bekleniyor: {rel_path} dosyası yazılacak.")
        
        ok, m = wait_for_action_approval(p["id"])
        if ok:
            return execute_approved_action(p, workspace_root)
        p["status"] = "rejected"
        return f"KULLANICI REDDETTİ: {m}"
        
    elif action == "REPLACE_IN_FILE":
        safe, msg = is_safe_path(rel_path)
        if not safe:
            add_evolution_log("SECURITY-BLOCK", msg)
            return f"GÜVENLİK ENGELLEMESİ: {msg}"
            
        fp = workspace_root / rel_path
        st = action_data.get("search", "")
        bc = ""
        if fp.exists():
            bc = fp.read_text(encoding="utf-8")
            
        pd = {
            "path": rel_path,
            "search": st,
            "replace": action_data.get("replace", ""),
            "thought": action_data.get("thought", "Dosya düzenlenecek."),
            "risk_level": "yüksek",
            "before_content": st
        }
        p = create_pending_action("REPLACE_IN_FILE", pd)
        add_evolution_log("WAITING-APPROVAL", f"Kullanıcı onayı bekleniyor: {rel_path} dosyasında değişiklik.")
        
        ok, m = wait_for_action_approval(p["id"])
        if ok:
            return execute_approved_action(p, workspace_root)
        p["status"] = "rejected"
        return f"KULLANICI REDDETTİ: {m}"
        
    elif action == "EXECUTE_COMMAND":
        safe, msg = is_command_safe(cmd)
        if not safe:
            add_evolution_log("SECURITY-BLOCK", f"Komut engellendi: {msg}")
            return f"GÜVENLİK ENGELLEMESİ: {msg}"
            
        pd = {
            "command": cmd,
            "thought": action_data.get("thought", "Komut çalıştırılacak."),
            "risk_level": "yüksek"
        }
        p = create_pending_action("EXECUTE_COMMAND", pd)
        add_evolution_log("WAITING-APPROVAL", f"Kullanıcı onayı bekleniyor: '{cmd}'")
        
        ok, m = wait_for_action_approval(p["id"])
        if ok:
            return execute_approved_action(p, workspace_root)
        p["status"] = "rejected"
        return f"KULLANICI REDDETTİ: {m}"
        
    elif action == "FINISH":
        return "__FINISH__"
    else:
        return f"HATA: Bilinmeyen eylem: {action}."

def run_evolution_agent_loop(prompt: str):
    global evolution_logs_list
    if SELF_EVOLUTION_SAFE_MODE:
        add_evolution_log("INFO", f"[SAFE MODE] Evrim başlatıldı: {prompt}")
        add_evolution_log("INFO", "Tüm WRITE/REPLACE/EXECUTE işlemleri kullanıcı onayına tabidir.")
    else:
        add_evolution_log("INFO", f"Evrim başlatıldı: {prompt}")
        
    client = get_gemini_client()
    if not client:
        add_evolution_log("ERROR", "Gemini API anahtarı bulunamadı!")
        return {"success": False, "message": "Gemini API anahtarı bulunamadı."}
        
    wr = Path("/Users/mert/Vex")
    sn = "GÜVENLİK KURALI: WRITE_FILE, REPLACE_IN_FILE, EXECUTE_COMMAND KULLANICI ONAYI BEKLER."
    key = "Proje: vex-app/ (React+Tauri) ve vex-backend/ (FastAPI)"
    ch = []
    si = f"""Sen Vex'in Güvenli Evrim Ajanısın.
{sn}

Eylemler:
1. READ_FILE (güvenli)
2. WRITE_FILE (ONAY GEREKİR)
3. REPLACE_IN_FILE (ONAY GEREKİR)
4. EXECUTE_COMMAND (ONAY GEREKİR)
5. LIST_FILES (güvenli)
6. FINISH

Sadece JSON yanıt ver."""
    ch.append({"role": "user", "text": f"Mert'in İsteği: {prompt}"})
    for step in range(1, 26):
        add_evolution_log("INFO", f"Adım {step}/25")
        try:
            ht = ""
            for m in ch:
                rl = "Kullanıcı" if m["role"] == "user" else "Asistan"
                ht += f"{rl}: {m['text']}\n"
            fp = f"{si}\n\n{ht}\nŞimdi sıradaki eylemini JSON olarak dön:"
            r = client.models.generate_content(model="gemini-2.5-pro", contents=fp)
            rt = r.text.strip()
            if rt.startswith("```"):
                rt = re.sub(r"^```[a-zA-Z0-9]*\n", "", rt)
                rt = re.sub(r"\n```$", "", rt).strip()
            ad = json.loads(rt)
        except Exception as e:
            add_evolution_log("ERROR", f"JSON ayrıştırma hatası: {e}")
            ch.append({"role": "user", "text": "HATA: Geçerli JSON dön."})
            continue
            
        t = ad.get("thought", "")
        a = ad.get("action", "").upper()
        add_evolution_log("AGENT-THOUGHT", t)
        
        if a == "FINISH":
            add_evolution_log("SUCCESS", "Tamamlandı!")
            return {"success": True, "message": "Tamamlandı."}
            
        try:
            r2 = run_safe_evolution_step(ad, wr)
        except Exception as e:
            r2 = f"HATA: {e}"
            traceback.print_exc()
            
        if r2 == "__FINISH__":
            add_evolution_log("SUCCESS", "Tamamlandı!")
            return {"success": True, "message": "Tamamlandı."}
            
        ch.append({"role": "model", "text": rt})
        ch.append({"role": "user", "text": r2})
        
    return {"success": False, "message": "Maksimum adım sınırı."}

def run_evolution_background(prompt: str):
    global is_evolution_running
    is_evolution_running = True
    try:
        run_evolution_agent_loop(prompt)
    except Exception as e:
        add_evolution_log("ERROR", f"Arka planda hata: {e}")
        traceback.print_exc()
    finally:
        is_evolution_running = False

@app.post("/evolution/prompt")
def run_evolution(request: EvolutionRequest):
    global is_evolution_running
    if is_evolution_running:
        return {"success": False, "message": "Zaten çalışıyor."}
    threading.Thread(target=run_evolution_background, args=(request.prompt,), daemon=True).start()
    return {"success": True, "message": "Evrim başlatıldı.", "safe_mode": SELF_EVOLUTION_SAFE_MODE}

@app.get("/evolution/logs")
def get_evolution_logs():
    return {"logs": evolution_logs_list}

@app.post("/evolution/reset-logs")
def reset_evolution_logs():
    global evolution_logs_list, pending_evolution_actions
    evolution_logs_list = []
    pending_evolution_actions = []
    return {"success": True}

@app.get("/evolution/status")
def get_evolution_status():
    return {"running": is_evolution_running, "safe_mode": SELF_EVOLUTION_SAFE_MODE, "pending_actions": len(pending_evolution_actions)}

@app.get("/evolution/pending-actions")
def get_pending_actions():
    return {"pending_actions": [a for a in pending_evolution_actions if a["status"] == "pending"]}

@app.post("/evolution/approve-action/{action_id}")
def approve_action(action_id: str):
    a = find_pending_action(action_id)
    if not a:
        return {"success": False, "message": "İşlem bulunamadı."}
    if a["status"] != "pending":
        return {"success": False, "message": "Bu işlem zaten işlenmiş."}
    a["status"] = "approved"
    add_evolution_log("INFO", f"Kullanıcı ONAYLADI: {a['action_type']}")
    return {"success": True, "message": "İşlem onaylandı.", "action": a}

@app.post("/evolution/reject-action/{action_id}")
def reject_action(action_id: str):
    a = find_pending_action(action_id)
    if not a:
        return {"success": False, "message": "İşlem bulunamadı."}
    if a["status"] != "pending":
        return {"success": False, "message": "Bu işlem zaten işlenmiş."}
    a["status"] = "rejected"
    add_evolution_log("INFO", f"Kullanıcı REDDETTİ: {a['action_type']}")
    return {"success": True, "message": "İşlem reddedildi.", "action": a}
