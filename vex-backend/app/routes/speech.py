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
