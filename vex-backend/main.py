import json
import os
import tempfile
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

WHISPER_MODEL_NAME = "small"
WHISPER_SAMPLE_RATE = 16000
WHISPER_CHANNELS = 1

# Mert'in MacBook Pro Microphone cihaz index'i.
# Daha sonra bunu otomatik cihaz seçimine çevirebiliriz.
MICROPHONE_DEVICE_INDEX = 1

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


class RecordSpeechRequest(BaseModel):
    duration_seconds: float = 5


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


def build_memory_text(memory: dict) -> str:
    return json.dumps(memory, ensure_ascii=False, indent=2)


def build_projects_text(projects: list[dict]) -> str:
    return json.dumps(projects, ensure_ascii=False, indent=2)


@app.get("/")
def root():
    return {
        "app": "Vex",
        "status": "Backend çalışıyor",
        "message": "Vex backend hazır.",
    }


@app.get("/memory")
def memory():
    return load_memory()


@app.get("/projects")
def projects():
    return load_projects()


@app.post("/projects")
def add_project(request: ProjectRequest):
    clean_id = request.id.strip().lower().replace(" ", "-")
    clean_name = request.name.strip()

    if not clean_id or not clean_name:
        return {
            "success": False,
            "message": "Proje id ve proje adı boş olamaz.",
        }

    projects_data = load_projects()

    for project in projects_data:
        if project.get("id") == clean_id:
            return {
                "success": True,
                "message": "Bu proje zaten kayıtlı.",
                "project": project,
                "projects": projects_data,
            }

    new_project = {
        "id": clean_id,
        "name": clean_name,
        "type": request.type,
        "status": request.status,
        "description": request.description,
        "main_goals": request.main_goals,
        "notes": request.notes,
    }

    projects_data.append(new_project)
    save_projects(projects_data)

    return {
        "success": True,
        "message": "Proje başarıyla eklendi.",
        "project": new_project,
        "projects": projects_data,
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
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@app.post("/speech/record-and-transcribe")
def record_and_transcribe_speech(request: RecordSpeechRequest):
    duration = max(1.0, min(float(request.duration_seconds), 20.0))

    print(f"Vex mikrofon kaydı başlıyor: {duration} saniye")
    print("Şimdi konuşabilirsin Mert...")

    audio_data = sd.rec(
        int(duration * WHISPER_SAMPLE_RATE),
        samplerate=WHISPER_SAMPLE_RATE,
        channels=WHISPER_CHANNELS,
        dtype="float32",
        device=MICROPHONE_DEVICE_INDEX,
    )

    sd.wait()

    print("Vex mikrofon kaydı bitti, yazıya çevriliyor...")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_path = temp_audio.name

    try:
        save_recording_to_wav(audio_data, temp_path)
        result = transcribe_audio_file(temp_path)

        return {
            **result,
            "duration_seconds": duration,
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@app.post("/speech/record/start")
def start_speech_recording():
    global recording_stream
    global recording_chunks
    global is_recording_active

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
        device=MICROPHONE_DEVICE_INDEX,
    )

    recording_stream.start()
    is_recording_active = True

    return {
        "success": True,
        "message": "Kayıt başladı.",
    }


@app.post("/speech/record/stop-and-transcribe")
def stop_speech_recording_and_transcribe():
    global recording_stream
    global recording_chunks
    global is_recording_active

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
        }

    audio_data = np.concatenate(recording_chunks, axis=0)
    recording_chunks = []

    max_volume = float(np.max(np.abs(audio_data))) if audio_data.size else 0
    average_volume = float(np.mean(np.abs(audio_data))) if audio_data.size else 0

    print(f"Vex kayıt ses seviyesi — max: {max_volume}, ortalama: {average_volume}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_path = temp_audio.name

    try:
        save_recording_to_wav(audio_data, temp_path)
        result = transcribe_audio_file(temp_path)

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
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "reply": "Gemini API key bulunamadı. .env dosyasında GEMINI_API_KEY var mı kontrol edelim.",
        }

    client = genai.Client(api_key=api_key)

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