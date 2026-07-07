from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.common import ComputerPlanRequest
from app.services import computer_service
from app.services.screenshot_service import capture_screenshot

router = APIRouter()


class ComputerTaskRequest(BaseModel):
    instruction: str = ""
    # Varsayılan artık "autonomous": model karar verir, adım doğrudan uygulanır.
    # Frontend "manual_step" gönderirse adımlar onaya düşer.
    mode: str = "autonomous"
    max_steps: int = 20


@router.get("/computer/screenshot")
def computer_screenshot():
    return capture_screenshot()


@router.get("/computer/status")
def computer_status():
    return computer_service.status()


@router.get("/computer/logs")
def computer_logs():
    return computer_service.logs()


@router.post("/computer/observe")
def computer_observe():
    return computer_service.observe()


@router.post("/computer/task")
def computer_task(request: ComputerTaskRequest):
    return computer_service.run_task(request.instruction, request.mode, request.max_steps)


@router.post("/computer/action")
def computer_action(payload: dict):
    return computer_service.execute_direct(payload or {})


@router.post("/computer/step/approve")
def computer_step_approve():
    return computer_service.step_approve()


@router.post("/computer/step/reject")
def computer_step_reject():
    return computer_service.step_reject()


@router.post("/computer/stop")
def computer_stop():
    return computer_service.stop()


@router.post("/computer/plan")
def computer_plan(request: ComputerPlanRequest):
    return computer_service.plan(request.instruction)
