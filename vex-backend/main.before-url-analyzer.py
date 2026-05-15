import json
import os
import queue
import re
import tempfile
import mss
import traceback
import time
import wave
from pathlib import Path

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


class ScreenAnalyzeRequest(BaseModel):
    prompt: str = "Ekranda ne olduğunu analiz et."


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


def build_memory_text(memory: dict) -> str:
    return json.dumps(memory, ensure_ascii=False, indent=2)


def build_projects_text(projects: list[dict]) -> str:
    return json.dumps(projects, ensure_ascii=False, indent=2)


def normalize_project_data(project_data: dict) -> dict:
    name = str(project_data.get("name", "")).strip()

    if not name:
        name = "Yeni Proje"

    project_id = str(project_data.get("id", "")).strip()

    if not project_id:
        project_id = slugify(name)
    else:
        project_id = slugify(project_id)

    main_goals = project_data.get("main_goals", [])
    notes = project_data.get("notes", [])

    if not isinstance(main_goals, list):
        main_goals = [str(main_goals)]

    if not isinstance(notes, list):
        notes = [str(notes)]

    return {
        "id": project_id,
        "name": name,
        "type": str(project_data.get("type", "Genel proje")).strip() or "Genel proje",
        "status": str(project_data.get("status", "aktif")).strip() or "aktif",
        "description": str(project_data.get("description", "")).strip(),
        "main_goals": [str(item).strip() for item in main_goals if str(item).strip()],
        "notes": [str(item).strip() for item in notes if str(item).strip()],
    }


def add_project_to_storage(project_data: dict) -> dict:
    normalized_project = normalize_project_data(project_data)

    projects_data = load_projects()

    for project in projects_data:
        if project.get("id") == normalized_project["id"]:
            return {
                "success": True,
                "message": "Bu proje zaten kayıtlı.",
                "project": project,
                "projects": projects_data,
            }

    projects_data.append(normalized_project)
    save_projects(projects_data)

    return {
        "success": True,
        "message": "Proje başarıyla eklendi.",
        "project": normalized_project,
        "projects": projects_data,
    }


def extract_project_from_chat(message: str) -> dict:
    client = get_gemini_client()

    if client is None:
        fallback_name = message.strip()[:60] or "Yeni Proje"

        return normalize_project_data({
            "name": fallback_name,
            "type": "Genel proje",
            "status": "aktif",
            "description": message.strip(),
            "main_goals": [
                "Proje detaylarını Mert ile netleştirmek"
            ],
            "notes": [
                "Bu proje Gemini API key olmadan basit çıkarımla oluşturuldu."
            ],
        })

    prompt = f"""
Sen Vex'in proje oluşturma modülüsün.

Mert'in mesajından yeni proje bilgisi çıkar.

Sadece geçerli JSON döndür.
Markdown, açıklama veya ekstra metin yazma.

JSON şeması:
{{
  "id": "kebab-case-proje-id",
  "name": "Proje adı",
  "type": "Proje tipi",
  "status": "aktif",
  "description": "Proje açıklaması",
  "main_goals": ["Hedef 1", "Hedef 2", "Hedef 3"],
  "notes": ["Not 1", "Not 2"]
}}

Kurallar:
- Mesaj Türkçe ise cevap alanları Türkçe olsun.
- Proje adı net değilse kısa ve anlamlı bir ad üret.
- id alanı küçük harfli, Türkçe karaktersiz ve tireli olsun.
- main_goals listesi en az 2, en fazla 5 madde olsun.
- notes listesi en az 1, en fazla 4 madde olsun.
- status varsayılan olarak "aktif" olsun.

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
            "name": message.strip()[:60] or "Yeni Proje",
            "type": "Genel proje",
            "status": "aktif",
            "description": message.strip(),
            "main_goals": [
                "Proje detaylarını netleştirmek",
                "İlk iş planını oluşturmak"
            ],
            "notes": [
                "Gemini çıktısı JSON olarak okunamadığı için basit proje kaydı oluşturuldu."
            ],
        }

    return normalize_project_data(parsed)






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

    active_project_preferences = [
        preference for preference in preferences_data
        if preference.get("status") == "active"
        and (
            not preference.get("project_id")
            or preference.get("project_id") == active_project_id
        )
    ]

    suggested_next_step = "Bugün önce açık görevleri ve bekleyen onayları kontrol edelim."

    if active_project and active_project_pending_approvals:
        suggested_next_step = f"{active_project.get('name', active_project_id)} için bekleyen onaylar var; önce Onay Merkezi’ni kontrol etmek iyi olur."
    elif active_project and active_project_high_priority_tasks:
        suggested_next_step = f"{active_project.get('name', active_project_id)} için yüksek öncelikli görevler var; önce onlardan biriyle başlamak iyi olur."
    elif pending_approvals:
        suggested_next_step = "Bekleyen onaylar var; önce Onay Merkezi’ni kontrol etmek iyi olur."
    elif high_priority_tasks:
        suggested_next_step = "Yüksek öncelikli görevler var; önce onlardan biriyle başlamak iyi olur."
    elif active_project:
        suggested_next_step = f"Aktif proje olarak {active_project.get('name', active_project_id)} üzerinden devam edebiliriz."
    elif active_projects:
        suggested_next_step = f"Aktif proje olarak {active_projects[0].get('name', 'ilk proje')} üzerinden devam edebiliriz."

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
        "outputs": outputs_data,
        "preferences": preferences_data,
        "active_project_context": {
            "project": active_project,
            "open_tasks": active_project_open_tasks,
            "high_priority_tasks": active_project_high_priority_tasks,
            "pending_approvals": active_project_pending_approvals,
            "outputs": active_project_outputs,
            "preferences": active_project_preferences,
            "all_project_tasks_count": len(active_project_tasks),
            "open_project_tasks_count": len(active_project_open_tasks),
            "pending_project_approvals_count": len(active_project_pending_approvals),
            "project_outputs_count": len(active_project_outputs),
            "project_preferences_count": len(active_project_preferences),
        },
        "suggested_next_step": suggested_next_step,
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


def build_conversation_text(history: list[ChatMessage], current_message: str) -> str:
    conversation_lines = []

    for item in history[-12:]:
        if item.sender == "Sen":
            conversation_lines.append(f"Mert: {item.text}")
        else:
            conversation_lines.append(f"Vex: {item.text}")

    conversation_lines.append(f"Mert: {current_message}")

    return "\n".join(conversation_lines)


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
            "active_project": active_project_data,
            "active_task": active_task_data,
            "active_brand_profile": active_brand_profile,
            "learned_preferences": relevant_preferences,
            "counts": {
                "projects": len(projects_data),
                "open_tasks": len(open_tasks),
                "high_priority_tasks": len(high_priority_tasks),
                "pending_approvals": len(pending_approvals),
                "outputs": len(outputs_data),
                "preferences": len(preferences_data),
            },
            "open_tasks": open_tasks[:10],
            "high_priority_tasks": high_priority_tasks[:10],
            "pending_approvals": pending_approvals[:10],
            "outputs": outputs_data[-10:],
            "active_outputs_context": {
                "active_project_outputs": active_project_outputs[-10:],
                "active_task_outputs": active_task_outputs[-10:],
            },
            "active_project_context": {
                "project": active_project,
                "open_tasks": active_project_open_tasks[:10],
                "high_priority_tasks": active_project_high_priority_tasks[:10],
                "pending_approvals": active_project_pending_approvals[:10],
                "outputs": active_project_outputs[-10:],
            },
        }

        memory_text = build_memory_text(memory_data)
        projects_text = build_projects_text(projects_data)
        workspace_text = json.dumps(workspace_summary_data, ensure_ascii=False, indent=2)

        system_context = f"""
Senin adın Vex.
Sen Mert'in kişisel yapay zeka iş arkadaşısın.

Kalıcı hafızan:
{memory_text}

Kayıtlı projeler:
{projects_text}

Çalışma alanı, aktif proje, aktif görev, kayıtlı çıktılar ve öğrenilmiş tercihler:
{workspace_text}

Davranış kuralların:
- Basit bir bot gibi davranma.
- Mert ile doğal, pratik ve samimi konuş.
- Kısa, net ve işe yarar cevaplar ver.
- Mert teknik konularda adım adım yönlendirilmek istiyor.
- Bir seferde çok fazla şey verme.
- Kritik işlemlerde Mert'ten onay al.
- Aktif proje seçiliyse kısa ve bağlamsız konuşmalarda aktif projeyi varsayılan bağlam olarak kullan.
- Aktif görev seçiliyse “devam et”, “başla”, “bunu hazırla”, “üret”, “yapalım” gibi komutlarda aktif görevi bağlam olarak kullan.
- Aktif görev açıksa mümkünse doğrudan somut ilk çıktıyı üret.
- Aktif görev tamamlandıysa yeni görev seçmeyi öner.
- Mert kayıtlı çıktı, son taslak, hero metni veya kayıtlı metin sorarsa outputs verisini kullan.
- Kayıtlı çıktıyı sorarsa yeniden uydurma; kayıtlı içeriği özetle veya aynen göster.
- Öğrenilmiş tercihler varsa, içerik üretirken bunları marka profilinden daha güncel kabul et.
- Aktif projeye bağlı tercihler genel tercihlerden daha önceliklidir.
- Aktif göreve bağlı tercihler proje tercihlerinden daha önceliklidir.
- Mert’i soru yağmuruna tutma; sadece gerçekten öğrenmeye değer yerde kısa soru sor.
- Her şeyi baştan sabitlemeye çalışma; kervanı yolda düzme mantığıyla gerçek kullanımdan öğren.
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
