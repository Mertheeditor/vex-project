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
