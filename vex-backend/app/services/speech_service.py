from __future__ import annotations

from collections import deque
import queue
import re
import subprocess
import tempfile
import time
from threading import Lock
import wave
from pathlib import Path

from app.core.config import MICROPHONE_DEVICE_INDEX, WHISPER_CHANNELS, WHISPER_MODEL_NAME, WHISPER_SAMPLE_RATE
from app.core.optional_imports import optional_import

whisper_model = None
recording_stream = None
recording_chunks = []
is_recording_active = False
speech_process = None
speech_process_lock = Lock()

WAKE_WORD_PATTERN = re.compile(
    r"(?<!\w)(vex|veks|vekiz|vekiş|vekis|vexx|wex|weks|fex|feks)(?!\w)",
    re.IGNORECASE,
)

WAKE_WORD_CANDIDATES = {
    "vex",
    "veks",
    "vek",
    "vekis",
    "vekiz",
    "vekz",
    "vexx",
    "wex",
    "weks",
    "wek",
    "fex",
    "feks",
    "bex",
    "beks",
    "vax",
    "vaks",
    "vecs",
    "vecks",
    "veeks",
    "tex",
    "teks",
    "dex",
    "deks",
    "pex",
    "peks",
    "hex",
    "heks",
    "vez",
    "vezz",
}

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

def _audio_metrics(np, audio_data) -> tuple[float, float]:
    if audio_data is None or audio_data.size == 0:
        return 0.0, 0.0

    flattened = audio_data.reshape(-1)
    absolute = np.abs(flattened)
    peak = float(np.max(absolute))
    rms = float(np.sqrt(np.mean(np.square(flattened))))
    return peak, rms

def _normalize_audio_for_whisper(np, audio_data, target_peak: float = 0.85):
    if audio_data is None or audio_data.size == 0:
        return audio_data

    peak, _ = _audio_metrics(np, audio_data)
    if peak <= 0:
        return audio_data

    gain = min(6.0, max(1.0, target_peak / peak))
    return np.clip(audio_data * gain, -1.0, 1.0)

def _is_voice_chunk(np, audio_data, peak_threshold: float, average_threshold: float) -> tuple[bool, float, float]:
    peak, rms = _audio_metrics(np, audio_data)

    # Tek seferlik küçük patlamaları konuşma saymamak için peak tek başına yetmesin;
    # RMS de en az eşik değerinin bir kısmını geçmeli.
    has_sustained_energy = rms >= average_threshold
    has_clear_peak = peak >= peak_threshold and rms >= average_threshold * 0.55
    return has_sustained_energy or has_clear_peak, peak, rms

def _bounded_float(value: float, default: float, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default

    return max(minimum, min(numeric, maximum))

def _normalize_wake_token(token: str) -> str:
    normalized = (token or "").strip().lower()
    normalized = (
        normalized.replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    return re.sub(r"[^a-z]", "", normalized)

def _edit_distance_is_small(left: str, right: str, limit: int = 1) -> bool:
    if left == right:
        return True

    if abs(len(left) - len(right)) > limit:
        return False

    i = 0
    j = 0
    edits = 0

    while i < len(left) and j < len(right):
        if left[i] == right[j]:
            i += 1
            j += 1
            continue

        edits += 1
        if edits > limit:
            return False

        if len(left) > len(right):
            i += 1
        elif len(right) > len(left):
            j += 1
        else:
            i += 1
            j += 1

    edits += (len(left) - i) + (len(right) - j)
    return edits <= limit

def _is_wake_like_token(token: str) -> bool:
    normalized = _normalize_wake_token(token)
    if not normalized or len(normalized) < 3 or len(normalized) > 6:
        return False

    if normalized in WAKE_WORD_CANDIDATES:
        return True

    if normalized.startswith(("vex", "vek", "wex", "wek", "fex", "fek", "bex", "bek")):
        return True

    return any(_edit_distance_is_small(normalized, candidate, limit=1) for candidate in WAKE_WORD_CANDIDATES)

def _contains_wake_word(text: str) -> bool:
    raw_text = text or ""
    if WAKE_WORD_PATTERN.search(raw_text):
        return True

    return any(
        _is_wake_like_token(match.group(0))
        for match in re.finditer(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", raw_text)
    )

def _strip_wake_word(text: str) -> str:
    raw_text = text or ""
    exact_match = WAKE_WORD_PATTERN.search(raw_text)
    if exact_match:
        without_wake = WAKE_WORD_PATTERN.sub("", raw_text, count=1)
        return re.sub(r"^[\s,.:;!\-–—]+", "", without_wake).strip()

    for match in re.finditer(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", raw_text):
        if _is_wake_like_token(match.group(0)):
            without_wake = (raw_text[:match.start()] + raw_text[match.end():]).strip()
            return re.sub(r"^[\s,.:;!\-–—]+", "", without_wake).strip()

    return raw_text.strip()

def _stop_speech_process() -> None:
    global speech_process
    with speech_process_lock:
        if speech_process is not None and speech_process.poll() is None:
            speech_process.terminate()
            try:
                speech_process.wait(timeout=1)
            except Exception:
                speech_process.kill()
        speech_process = None

def speak_text(text: str) -> dict:
    global speech_process
    cleaned = (text or "").strip()
    if not cleaned:
        return {"success": False, "message": "Seslendirilecek metin boş."}

    try:
        _stop_speech_process()
        with speech_process_lock:
            speech_process = subprocess.Popen(
                ["say", "-v", "Yelda", cleaned],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return {"success": True, "message": "Sesli cevap başlatıldı."}
    except Exception as exc:
        speech_process = None
        return {"success": False, "message": f"Sesli cevap başlatılamadı: {exc}"}

def stop_speaking() -> dict:
    try:
        _stop_speech_process()
        return {"success": True, "message": "Sesli cevap durduruldu."}
    except Exception as exc:
        return {"success": False, "message": f"Sesli cevap durdurulamadı: {exc}"}

def speaking_status() -> dict:
    with speech_process_lock:
        speaking = speech_process is not None and speech_process.poll() is None
    return {"success": True, "speaking": speaking}

def _transcribe_audio_data(np, audio_data, **transcribe_kwargs) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        _save_wav(np, audio_data, wav_path)
        return transcribe_audio_file(wav_path, **transcribe_kwargs)
    finally:
        Path(wav_path).unlink(missing_ok=True)

def transcribe_audio_file(
    audio_path: str,
    vad_filter: bool = True,
    beam_size: int = 5,
    language: str | None = "tr",
    initial_prompt: str | None = None,
    hotwords: str | None = None,
    strict: bool = False,
) -> dict:
    try:
        model = _get_whisper_model()
        transcribe_kwargs = {
            "beam_size": beam_size,
            "vad_filter": vad_filter,
            # condition_on_previous_text=False: Whisper'ın önceki (var olmayan)
            # bağlamdan uydurma cümle üretmesini azaltır. Kısa/sessiz ses
            # klipslerinde (örn "Vex" gibi tek kelime) modelin tamamen alakasız
            # bir cümle "halüsinasyon" etmesi buradan kaynaklanıyordu.
            "condition_on_previous_text": False,
        }

        if strict:
            # Uyandırma kelimesi tespiti gibi kritik anlarda modeli daha
            # şüpheci yapıyoruz: düşük olasılıklı / konuşma-dışı sayılan
            # segmentleri baştan reddet ki "Vex" yerine uydurma bir cümle
            # dönmesin.
            transcribe_kwargs["no_speech_threshold"] = 0.4
            transcribe_kwargs["log_prob_threshold"] = -0.6
            transcribe_kwargs["compression_ratio_threshold"] = 2.0

        if language is not None:
            transcribe_kwargs["language"] = language

        if initial_prompt:
            transcribe_kwargs["initial_prompt"] = initial_prompt

        if hotwords:
            transcribe_kwargs["hotwords"] = hotwords

        segments, info = model.transcribe(audio_path, **transcribe_kwargs)
        kept_texts = []
        for segment in segments:
            segment_text = segment.text.strip()
            if not segment_text:
                continue
            # Ek güvenlik filtresi: no_speech_prob yüksekse ("burada konuşma
            # yok" diyorsa) veya avg_logprob çok düşükse (model kendinden emin
            # değilse) bu segmenti at. strict modda bu filtre daha sıkı.
            no_speech_prob = getattr(segment, "no_speech_prob", 0.0) or 0.0
            avg_logprob = getattr(segment, "avg_logprob", 0.0) or 0.0
            no_speech_limit = 0.5 if strict else 0.85
            logprob_limit = -0.8 if strict else -1.5
            if no_speech_prob >= no_speech_limit or avg_logprob <= logprob_limit:
                continue
            kept_texts.append(segment_text)

        text = " ".join(kept_texts).strip()
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
        duration = _bounded_float(max_seconds, 20.0, 1.0, 60.0)
        silence_limit = _bounded_float(silence_seconds, 1.2, 0.25, 5.0)
        peak_limit = _bounded_float(peak_threshold, 0.025, 0.005, 0.5)
        average_limit = _bounded_float(average_threshold, 0.003, 0.0005, 0.2)

        block_seconds = 0.1
        block_size = max(256, int(WHISPER_SAMPLE_RATE * block_seconds))
        min_voice_chunks_to_start = 2
        min_recorded_seconds = 0.25

        audio_queue: queue.Queue = queue.Queue()
        pre_roll_chunks = deque(maxlen=max(1, int(0.3 / block_seconds)))
        recorded_chunks = []
        speech_started = False
        consecutive_voice_chunks = 0
        last_voice_at: float | None = None
        started_at = time.monotonic()
        max_peak = 0.0
        max_rms = 0.0

        def callback(indata, frames, time_info, status):
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=WHISPER_SAMPLE_RATE,
            channels=WHISPER_CHANNELS,
            dtype="float32",
            blocksize=block_size,
            callback=callback,
            **_device_kwargs(),
        ):
            while time.monotonic() - started_at < duration:
                remaining = duration - (time.monotonic() - started_at)
                if remaining <= 0:
                    break

                try:
                    chunk = audio_queue.get(timeout=min(0.2, remaining))
                except queue.Empty:
                    continue

                now = time.monotonic()
                is_voice, chunk_peak, chunk_rms = _is_voice_chunk(np, chunk, peak_limit, average_limit)
                max_peak = max(max_peak, chunk_peak)
                max_rms = max(max_rms, chunk_rms)

                if not speech_started:
                    pre_roll_chunks.append(chunk)

                    if is_voice:
                        consecutive_voice_chunks += 1
                    else:
                        consecutive_voice_chunks = 0

                    if consecutive_voice_chunks >= min_voice_chunks_to_start:
                        speech_started = True
                        recorded_chunks = list(pre_roll_chunks)
                        last_voice_at = now

                    continue

                recorded_chunks.append(chunk)

                if is_voice:
                    last_voice_at = now
                    continue

                if last_voice_at is not None and now - last_voice_at >= silence_limit:
                    break

        listened_seconds = round(time.monotonic() - started_at, 2)

        if not speech_started or not recorded_chunks:
            return {
                "success": False,
                "reason": "no_speech",
                "message": "Konuşma algılanmadı; sessizlik yok sayıldı.",
                "text": "",
                "metrics": {"listened_seconds": listened_seconds, "peak": max_peak, "rms": max_rms},
            }

        audio = np.concatenate(recorded_chunks, axis=0)
        audio_seconds = float(audio.shape[0]) / float(WHISPER_SAMPLE_RATE)
        audio_peak, audio_rms = _audio_metrics(np, audio)

        if audio_seconds < min_recorded_seconds or (audio_peak < peak_limit and audio_rms < average_limit):
            return {
                "success": False,
                "reason": "no_speech",
                "message": "Konuşma algılanmadı; sessizlik yok sayıldı.",
                "text": "",
                "metrics": {"listened_seconds": listened_seconds, "audio_seconds": round(audio_seconds, 2), "peak": audio_peak, "rms": audio_rms},
            }

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        _save_wav(np, audio, wav_path)
        result = transcribe_audio_file(wav_path)
        Path(wav_path).unlink(missing_ok=True)

        result["metrics"] = {
            "listened_seconds": listened_seconds,
            "audio_seconds": round(audio_seconds, 2),
            "peak": audio_peak,
            "rms": audio_rms,
        }

        if result.get("success") and not result.get("text", "").strip():
            result.update(
                {
                    "success": False,
                    "reason": "empty_transcription",
                    "message": "Konuşma algılandı ama anlamlı metin çıkarılamadı.",
                    "text": "",
                }
            )

        return result
    except Exception as exc:
        return {"success": False, "message": f"Dinleme başarısız: {exc}", "text": ""}

def wake_listen_and_transcribe(
    wake_seconds: float = 4,
    active_silence_seconds: float = 10,
    max_active_seconds: float = 90,
    peak_threshold: float = 0.075,
    average_threshold: float = 0.012,
) -> dict:
    """Listen briefly for the "Vex" wake word, then keep listening until 10s of silence.

    The 10 second timer is reset whenever new speech-like audio is detected in the
    active phase. This endpoint is intentionally finite so the frontend can call it
    in a loop without keeping a single HTTP request open forever.
    """

    np, sd, _, errors = _imports()
    if errors:
        return {"success": False, "message": "Speech modülü hazır değil: " + "; ".join(errors), "text": ""}

    try:
        wake_window = _bounded_float(wake_seconds, 4.0, 1.0, 12.0)
        active_silence_limit = _bounded_float(active_silence_seconds, 10.0, 2.0, 30.0)
        active_max_duration = _bounded_float(max_active_seconds, 90.0, 10.0, 180.0)
        peak_limit = _bounded_float(peak_threshold, 0.075, 0.005, 0.5)
        average_limit = _bounded_float(average_threshold, 0.012, 0.0005, 0.2)

        block_seconds = 0.1
        block_size = max(256, int(WHISPER_SAMPLE_RATE * block_seconds))
        min_voice_chunks_to_start = 2
        wake_phrase_silence_seconds = 0.75
        wake_phrase_max_seconds = 3.5

        audio_queue: queue.Queue = queue.Queue()
        wake_started_at = time.monotonic()
        max_peak = 0.0
        max_rms = 0.0

        def callback(indata, frames, time_info, status):
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=WHISPER_SAMPLE_RATE,
            channels=WHISPER_CHANNELS,
            dtype="float32",
            blocksize=block_size,
            callback=callback,
            **_device_kwargs(),
        ):
            wake_pre_roll_chunks = deque(maxlen=max(1, int(0.3 / block_seconds)))
            wake_chunks = []
            wake_speech_started = False
            wake_consecutive_voice_chunks = 0
            wake_last_voice_at: float | None = None
            wake_segment_started_at: float | None = None

            while time.monotonic() - wake_started_at < wake_window:
                remaining = wake_window - (time.monotonic() - wake_started_at)
                if remaining <= 0:
                    break

                try:
                    chunk = audio_queue.get(timeout=min(0.2, remaining))
                except queue.Empty:
                    continue

                now = time.monotonic()
                is_voice, chunk_peak, chunk_rms = _is_voice_chunk(np, chunk, peak_limit, average_limit)
                max_peak = max(max_peak, chunk_peak)
                max_rms = max(max_rms, chunk_rms)

                if not wake_speech_started:
                    wake_pre_roll_chunks.append(chunk)

                    if is_voice:
                        wake_consecutive_voice_chunks += 1
                    else:
                        wake_consecutive_voice_chunks = 0

                    if wake_consecutive_voice_chunks >= min_voice_chunks_to_start:
                        wake_speech_started = True
                        wake_chunks = list(wake_pre_roll_chunks)
                        wake_last_voice_at = now
                        wake_segment_started_at = now

                    continue

                wake_chunks.append(chunk)

                if is_voice:
                    wake_last_voice_at = now

                if wake_last_voice_at is not None and now - wake_last_voice_at >= wake_phrase_silence_seconds:
                    break

                if wake_segment_started_at is not None and now - wake_segment_started_at >= wake_phrase_max_seconds:
                    break

            if not wake_chunks:
                return {
                    "success": False,
                    "reason": "no_wake",
                    "wake_detected": False,
                    "message": "Vex uyandırma kelimesi bekleniyor.",
                    "text": "",
                    "metrics": {
                        "wake_listened_seconds": round(time.monotonic() - wake_started_at, 2),
                        "peak": max_peak,
                        "rms": max_rms,
                    },
                }

            wake_audio = np.concatenate(wake_chunks, axis=0)
            wake_result = _transcribe_audio_data(np, wake_audio)
            wake_text = wake_result.get("text", "").strip() if wake_result.get("success") else ""

            if not _contains_wake_word(wake_text):
                return {
                    "success": False,
                    "reason": "no_wake",
                    "wake_detected": False,
                    "message": "Vex uyandırma kelimesi duyulmadı.",
                    "text": "",
                    "wake_text": wake_text,
                    "metrics": {
                        "wake_listened_seconds": round(time.monotonic() - wake_started_at, 2),
                        "peak": max_peak,
                        "rms": max_rms,
                    },
                }

            wake_remainder = _strip_wake_word(wake_text)

            active_started_at = time.monotonic()
            active_last_voice_at = active_started_at
            active_pre_roll_chunks = deque(maxlen=max(1, int(0.25 / block_seconds)))
            active_chunks = []
            active_voice_seen = False

            while time.monotonic() - active_started_at < active_max_duration:
                now = time.monotonic()

                if now - active_last_voice_at >= active_silence_limit:
                    break

                try:
                    chunk = audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                now = time.monotonic()
                is_voice, chunk_peak, chunk_rms = _is_voice_chunk(np, chunk, peak_limit, average_limit)
                max_peak = max(max_peak, chunk_peak)
                max_rms = max(max_rms, chunk_rms)

                if not active_voice_seen:
                    active_pre_roll_chunks.append(chunk)

                    if is_voice:
                        active_voice_seen = True
                        active_chunks = list(active_pre_roll_chunks)
                        active_last_voice_at = now

                    continue

                active_chunks.append(chunk)

                if is_voice:
                    active_last_voice_at = now

            active_text = ""
            active_audio_seconds = 0.0

            if active_chunks:
                active_audio = np.concatenate(active_chunks, axis=0)
                active_audio_seconds = float(active_audio.shape[0]) / float(WHISPER_SAMPLE_RATE)
                active_peak, active_rms = _audio_metrics(np, active_audio)

                if active_peak >= peak_limit or active_rms >= average_limit:
                    active_result = _transcribe_audio_data(np, active_audio)
                    if active_result.get("success"):
                        active_text = _strip_wake_word(active_result.get("text", "").strip())

            combined_text = " ".join(part for part in [wake_remainder, active_text] if part).strip()

            if not combined_text:
                return {
                    "success": False,
                    "reason": "no_command",
                    "wake_detected": True,
                    "message": "Vex'i duydum ama komut algılanmadı.",
                    "text": "",
                    "wake_text": wake_text,
                    "metrics": {
                        "wake_listened_seconds": round(active_started_at - wake_started_at, 2),
                        "active_listened_seconds": round(time.monotonic() - active_started_at, 2),
                        "active_audio_seconds": round(active_audio_seconds, 2),
                        "peak": max_peak,
                        "rms": max_rms,
                    },
                }

            return {
                "success": True,
                "wake_detected": True,
                "message": "Vex uyandı ve komutu yazıya çevirdi.",
                "text": combined_text,
                "wake_text": wake_text,
                "active_text": active_text,
                "metrics": {
                    "wake_listened_seconds": round(active_started_at - wake_started_at, 2),
                    "active_listened_seconds": round(time.monotonic() - active_started_at, 2),
                    "active_audio_seconds": round(active_audio_seconds, 2),
                    "peak": max_peak,
                    "rms": max_rms,
                },
            }
    except Exception as exc:
        return {"success": False, "message": f"Uyandırmalı dinleme başarısız: {exc}", "text": ""}

def detect_wake_word(
    wake_seconds: float = 4,
    peak_threshold: float = 0.075,
    average_threshold: float = 0.012,
) -> dict:
    """Return quickly when a real "Vex" wake phrase is heard."""

    np, sd, _, errors = _imports()
    if errors:
        return {"success": False, "message": "Speech modülü hazır değil: " + "; ".join(errors), "text": ""}

    try:
        wake_window = _bounded_float(wake_seconds, 4.0, 1.0, 12.0)
        peak_limit = _bounded_float(peak_threshold, 0.075, 0.005, 0.5)
        average_limit = _bounded_float(average_threshold, 0.012, 0.0005, 0.2)
        wake_peak_limit = max(0.01, peak_limit * 0.35)
        wake_average_limit = max(0.0015, average_limit * 0.25)

        block_seconds = 0.1
        block_size = max(256, int(WHISPER_SAMPLE_RATE * block_seconds))
        min_voice_chunks_to_start = 1
        wake_phrase_silence_seconds = 0.65
        wake_phrase_max_seconds = 2.6

        audio_queue: queue.Queue = queue.Queue()
        wake_started_at = time.monotonic()
        max_peak = 0.0
        max_rms = 0.0

        def callback(indata, frames, time_info, status):
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=WHISPER_SAMPLE_RATE,
            channels=WHISPER_CHANNELS,
            dtype="float32",
            blocksize=block_size,
            callback=callback,
            **_device_kwargs(),
        ):
            pre_roll_chunks = deque(maxlen=max(1, int(0.3 / block_seconds)))
            wake_chunks = []
            speech_started = False
            consecutive_voice_chunks = 0
            last_voice_at: float | None = None
            segment_started_at: float | None = None

            while time.monotonic() - wake_started_at < wake_window:
                remaining = wake_window - (time.monotonic() - wake_started_at)
                if remaining <= 0:
                    break

                try:
                    chunk = audio_queue.get(timeout=min(0.2, remaining))
                except queue.Empty:
                    continue

                now = time.monotonic()
                is_voice, chunk_peak, chunk_rms = _is_voice_chunk(np, chunk, wake_peak_limit, wake_average_limit)
                max_peak = max(max_peak, chunk_peak)
                max_rms = max(max_rms, chunk_rms)

                if not speech_started:
                    pre_roll_chunks.append(chunk)

                    if is_voice:
                        consecutive_voice_chunks += 1
                    else:
                        consecutive_voice_chunks = 0

                    if consecutive_voice_chunks >= min_voice_chunks_to_start:
                        speech_started = True
                        wake_chunks = list(pre_roll_chunks)
                        last_voice_at = now
                        segment_started_at = now

                    continue

                wake_chunks.append(chunk)

                if is_voice:
                    last_voice_at = now

                if last_voice_at is not None and now - last_voice_at >= wake_phrase_silence_seconds:
                    break

                if segment_started_at is not None and now - segment_started_at >= wake_phrase_max_seconds:
                    break

        listened_seconds = round(time.monotonic() - wake_started_at, 2)

        if not wake_chunks:
            return {
                "success": False,
                "reason": "no_wake",
                "wake_detected": False,
                "message": "Vex uyandırma kelimesi bekleniyor.",
                "text": "",
                "metrics": {"wake_listened_seconds": listened_seconds, "peak": max_peak, "rms": max_rms},
            }

        wake_audio = np.concatenate(wake_chunks, axis=0)
        wake_audio_for_model = _normalize_audio_for_whisper(np, wake_audio)
        wake_audio_seconds = float(wake_audio.shape[0]) / float(WHISPER_SAMPLE_RATE)
        wake_peak, wake_rms = _audio_metrics(np, wake_audio)
        # Basit ve kısa bir prompt kullanıyoruz: uzun/açıklayıcı promptlar
        # Whisper tarafından bazen olduğu gibi "yankılanıp" transkripte
        # sızabiliyor (örn. "wake word is Vex" gibi). hotwords="Vex" zaten
        # kelimeye önyargı kazandırıyor, initial_prompt'u minimal tutuyoruz.
        wake_prompt = "Vex"
        wake_result = _transcribe_audio_data(
            np,
            wake_audio_for_model,
            vad_filter=False,
            beam_size=5,
            language=None,
            initial_prompt=wake_prompt,
            hotwords="Vex",
            strict=True,
        )
        wake_text = wake_result.get("text", "").strip() if wake_result.get("success") else ""
        explicit_wake = _contains_wake_word(wake_text)
        print(f"[WAKE] pass1 (lang=auto) heard: {wake_text!r} -> wake={explicit_wake}")

        if not explicit_wake:
            second_pass = _transcribe_audio_data(
                np,
                wake_audio_for_model,
                vad_filter=False,
                beam_size=5,
                language="tr",
                initial_prompt="Vex",
                hotwords="Vex",
                strict=True,
            )
            second_pass_text = second_pass.get("text", "").strip() if second_pass.get("success") else ""
            print(f"[WAKE] pass2 (lang=tr) heard: {second_pass_text!r}")
            if _contains_wake_word(second_pass_text):
                explicit_wake = True
                wake_text = second_pass_text

        if not explicit_wake:
            third_pass = _transcribe_audio_data(
                np,
                wake_audio_for_model,
                vad_filter=True,
                beam_size=5,
                language="tr",
                initial_prompt="Vex",
                hotwords="Vex",
                strict=True,
            )
            third_pass_text = third_pass.get("text", "").strip() if third_pass.get("success") else ""
            print(f"[WAKE] pass3 (lang=tr, vad) heard: {third_pass_text!r}")
            if _contains_wake_word(third_pass_text):
                explicit_wake = True
                wake_text = third_pass_text

        if not explicit_wake:
            return {
                "success": False,
                "reason": "no_wake",
                "wake_detected": False,
                "message": "Vex uyandırma kelimesi duyulmadı.",
                "text": "",
                "wake_text": wake_text,
                "metrics": {
                    "wake_listened_seconds": listened_seconds,
                    "wake_audio_seconds": round(wake_audio_seconds, 2),
                    "peak": wake_peak,
                    "rms": wake_rms,
                },
            }

        command_text = _strip_wake_word(wake_text) if explicit_wake else ""

        return {
            "success": True,
            "wake_detected": True,
            "wake_reason": "word",
            "message": "Vex uyandı. 10 saniyelik aktif dinleme başlıyor.",
            "text": command_text,
            "wake_text": wake_text,
            "metrics": {
                "wake_listened_seconds": listened_seconds,
                "wake_audio_seconds": round(wake_audio_seconds, 2),
                "peak": wake_peak,
                "rms": wake_rms,
            },
        }
    except Exception as exc:
        return {"success": False, "message": f"Uyandırma algılama başarısız: {exc}", "text": ""}

def active_listen_and_transcribe(
    active_silence_seconds: float = 10,
    max_active_seconds: float = 90,
    peak_threshold: float = 0.075,
    average_threshold: float = 0.012,
) -> dict:
    """Listen after wake.

    Behavior:
    - Wait up to `active_silence_seconds` for the user to start speaking.
    - Once speech starts, keep listening until the user finishes speaking.
    - User finish is determined by a short end-of-turn silence, not the full
      active session timeout.
    """

    np, sd, _, errors = _imports()
    if errors:
        return {"success": False, "message": "Speech modülü hazır değil: " + "; ".join(errors), "text": ""}

    try:
        active_silence_limit = _bounded_float(active_silence_seconds, 10.0, 2.0, 30.0)
        active_max_duration = _bounded_float(max_active_seconds, 90.0, 10.0, 180.0)
        peak_limit = _bounded_float(peak_threshold, 0.04, 0.005, 0.5)
        average_limit = _bounded_float(average_threshold, 0.006, 0.0005, 0.2)
        start_peak_limit = max(0.018, peak_limit * 0.65)
        start_average_limit = max(0.0025, average_limit * 0.55)
        end_peak_limit = max(0.014, peak_limit * 0.5)
        end_average_limit = max(0.002, average_limit * 0.45)
        turn_end_silence_limit = 0.75
        max_single_turn_seconds = 18.0

        block_seconds = 0.1
        block_size = max(256, int(WHISPER_SAMPLE_RATE * block_seconds))
        audio_queue: queue.Queue = queue.Queue()
        active_started_at = time.monotonic()
        active_last_voice_at = active_started_at
        pre_roll_chunks = deque(maxlen=max(1, int(0.25 / block_seconds)))
        active_chunks = []
        active_voice_seen = False
        max_peak = 0.0
        max_rms = 0.0

        def callback(indata, frames, time_info, status):
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=WHISPER_SAMPLE_RATE,
            channels=WHISPER_CHANNELS,
            dtype="float32",
            blocksize=block_size,
            callback=callback,
            **_device_kwargs(),
        ):
            while time.monotonic() - active_started_at < active_max_duration:
                now = time.monotonic()

                if not active_voice_seen:
                    if now - active_started_at >= active_silence_limit:
                        break
                elif now - active_last_voice_at >= turn_end_silence_limit:
                    break
                elif now - active_turn_started_at >= max_single_turn_seconds:
                    break

                try:
                    chunk = audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                now = time.monotonic()
                if not active_voice_seen:
                    is_voice, chunk_peak, chunk_rms = _is_voice_chunk(np, chunk, start_peak_limit, start_average_limit)
                else:
                    is_voice, chunk_peak, chunk_rms = _is_voice_chunk(np, chunk, end_peak_limit, end_average_limit)
                max_peak = max(max_peak, chunk_peak)
                max_rms = max(max_rms, chunk_rms)

                if not active_voice_seen:
                    pre_roll_chunks.append(chunk)

                    if is_voice:
                        active_voice_seen = True
                        active_chunks = list(pre_roll_chunks)
                        active_last_voice_at = now
                        active_turn_started_at = now

                    continue

                active_chunks.append(chunk)

                if is_voice:
                    active_last_voice_at = now

        listened_seconds = round(time.monotonic() - active_started_at, 2)

        if not active_chunks:
            return {
                "success": False,
                "reason": "no_command",
                "message": "Vex uyandı ama 10 saniye içinde komut algılanmadı.",
                "text": "",
                "metrics": {"active_listened_seconds": listened_seconds, "peak": max_peak, "rms": max_rms},
            }

        active_audio = np.concatenate(active_chunks, axis=0)
        active_audio_seconds = float(active_audio.shape[0]) / float(WHISPER_SAMPLE_RATE)
        active_peak, active_rms = _audio_metrics(np, active_audio)

        if active_peak < peak_limit and active_rms < average_limit:
            return {
                "success": False,
                "reason": "no_command",
                "message": "Vex uyandı ama anlamlı komut algılanmadı.",
                "text": "",
                "metrics": {
                    "active_listened_seconds": listened_seconds,
                    "active_audio_seconds": round(active_audio_seconds, 2),
                    "peak": active_peak,
                    "rms": active_rms,
                },
            }

        result = _transcribe_audio_data(np, active_audio)
        result["metrics"] = {
            "active_listened_seconds": listened_seconds,
            "active_audio_seconds": round(active_audio_seconds, 2),
            "peak": active_peak,
            "rms": active_rms,
        }

        if result.get("success"):
            text = _strip_wake_word(result.get("text", "").strip())
            if text:
                result["text"] = text
            else:
                result.update(
                    {
                        "success": False,
                        "reason": "empty_transcription",
                        "message": "Komut algılandı ama anlamlı metin çıkarılamadı.",
                        "text": "",
                    }
                )

        return result
    except Exception as exc:
        return {"success": False, "message": f"Aktif dinleme başarısız: {exc}", "text": ""}
