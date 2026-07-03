from __future__ import annotations

from fastapi import APIRouter
from app.schemas.common import ScreenAnalyzeRequest
from app.services.screen_analysis_service import analyze_screen

router = APIRouter()

@router.post("/screen/capture-and-analyze")
def capture_and_analyze(request: ScreenAnalyzeRequest):
    return analyze_screen(request.prompt)
