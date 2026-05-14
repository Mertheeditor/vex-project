import json
import os
import queue
import re
import tempfile
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
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Vex Backend")

MEMORY_PATH = Path("memory.json")
PROJECTS_PATH = Path("projects.json")
TASKS_PATH = Path("tasks.json")

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


@app.get("/")
def root():
    return {
        "app": "Vex",
        "status": "Backend çalışıyor",
        "message": "Vex backend hazır.",
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

    memory_data = load_memory()
    projects_data = load_projects()

    memory_text = build_memory_text(memory_data)
    projects_text = build_projects_text(projects_data)

    system_context = f"""
Senin adın Vex.
Sen Mert'in kişisel yapay zeka iş arkadaşısın.

Aşağıda kalıcı hafızan var. Bu hafızayı kimliğin, çalışma tarzın ve proje prensiplerin için kaynak kabul et:

{memory_text}

Aşağıda kayıtlı projeler var. Mert bir proje adı, site adı veya iş bağlamı söylediğinde bu projelerden yararlan:

{projects_text}

Davranış kuralların:
- Basit bir bot gibi davranma.
- Mert ile doğal, pratik ve samimi konuş.
- Mert'e tasarım, Shopify, site kurulumu, dosya işleri, çeviri ve günlük iş akışlarında yardımcı ol.
- Bu proje baştan en iyi versiyon olarak kuruluyor; basit MVP mantığıyla ilerleme.
- Maliyet düşük tutulacak; Gemini API, açık kaynak araçlar ve local-first mimari tercih edilecek.
- Kısa, net ve işe yarar cevaplar ver.
- Mert teknik konularda adım adım yönlendirilmek istiyor.
- Bir seferde çok fazla şey verme; bir adımı yaptır, sonra kontrol et.
- Kritik işlemlerde Mert'ten onay al.
- Kayıtlı projeleri hatırla ve ilgili olduğunda bağlam olarak kullan.
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
        "reply": response.text,
    }