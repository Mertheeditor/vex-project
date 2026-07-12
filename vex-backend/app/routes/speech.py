from __future__ import annotations

from fastapi import APIRouter
from app.schemas.common import ActiveListenSpeechRequest, DetectWakeWordRequest, ListenSpeechRequest, SpeakTextRequest, WakeListenSpeechRequest
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

@router.post("/speech/wake-listen-and-transcribe")
def speech_wake_listen(request: WakeListenSpeechRequest):
    return speech_service.wake_listen_and_transcribe(
        request.wake_seconds,
        request.active_silence_seconds,
        request.max_active_seconds,
        request.peak_threshold,
        request.average_threshold,
    )

@router.post("/speech/wake/detect")
def speech_detect_wake(request: DetectWakeWordRequest):
    return speech_service.detect_wake_word(
        request.wake_seconds,
        request.peak_threshold,
        request.average_threshold,
    )

@router.post("/speech/wake/active-listen")
def speech_active_listen(request: ActiveListenSpeechRequest):
    return speech_service.active_listen_and_transcribe(
        request.active_silence_seconds,
        request.max_active_seconds,
        request.peak_threshold,
        request.average_threshold,
    )

@router.post("/speech/speak")
def speech_speak(request: SpeakTextRequest):
    return speech_service.speak_text(request.text)

@router.post("/speech/stop-speaking")
def speech_stop_speaking():
    return speech_service.stop_speaking()

@router.get("/speech/speaking-status")
def speech_speaking_status():
    return speech_service.speaking_status()
