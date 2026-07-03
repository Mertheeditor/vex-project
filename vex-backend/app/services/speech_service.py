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
