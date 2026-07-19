from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import ValidationError

from app.core.paths import APPROVALS_PATH, TASKS_PATH
from app.schemas.agent_kernel import AgentContext, AgentTask
from app.schemas.task_engine import AgentTaskRecord, AgentTaskStatus
from app.schemas.task_execution import (
    ExecuteTaskRequest,
    ExecuteTaskResponse,
    ExecutionMetadataResponse,
    ExecutionResultResponse,
    ExecutionTaskResponse,
    ResumeTaskRequest,
    TaskApprovalCreateRequest,
    TaskApprovalResponse,
)
from app.services.task_engine import (
    ApprovalRequiredError,
    BlackRiskError,
    InvalidTaskRiskError,
    RejectedApprovalError,
    TaskAlreadyRunningError,
    TaskEngineError,
    TerminalTaskError,
)
from app.services.task_execution_runtime import TaskExecutionRuntime, get_task_execution_runtime
from app.storage.entity_store import find_item, list_items, upsert_item

router = APIRouter(prefix="/task-executions", tags=["task-executions"])


def _crud_task_or_404(task_id: str) -> dict[str, object]:
    task = find_item(TASKS_PATH, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _safe_string(record: dict[str, object], field: str, default: str = "") -> str:
    value = record.get(field, default)
    if not isinstance(value, str):
        raise HTTPException(status_code=409, detail=f"Stored record has invalid {field}")
    return value


def _safe_notes(record: dict[str, object]) -> list[str]:
    notes = record.get("notes", [])
    if not isinstance(notes, list) or not all(isinstance(note, str) for note in notes):
        raise HTTPException(status_code=409, detail="Stored record has invalid notes")
    return list(notes)


def _engine_task_or_404(runtime: TaskExecutionRuntime, task_id: str) -> AgentTaskRecord:
    try:
        return runtime.engine.get_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task execution not found") from exc


def _ensure_engine_task(
    runtime: TaskExecutionRuntime,
    task_id: str,
    crud_task: dict[str, object],
    request: ExecuteTaskRequest,
) -> AgentTaskRecord:
    try:
        record = runtime.engine.get_task(task_id)
    except KeyError:
        title = _safe_string(crud_task, "title").strip()
        description = _safe_string(crud_task, "description").strip()
        objective = title or description
        if not objective:
            raise HTTPException(status_code=409, detail="Stored task has no executable objective")

        metadata: dict[str, object] = {
            "risk_level": request.risk_level,
            "project_id": _safe_string(crud_task, "project_id"),
            "crud_status": _safe_string(crud_task, "status"),
            "priority": _safe_string(crud_task, "priority"),
            "description": description,
            "notes": _safe_notes(crud_task),
            "requested_by": "http",
            "request_context": dict(request.context),
        }
        record = runtime.engine.create_task(
            AgentTask(
                task_id=task_id,
                objective=objective,
                context=metadata,
                requested_by="http",
            )
        )
        runtime.engine.transition(task_id, AgentTaskStatus.PLANNING)
        record = runtime.engine.transition(task_id, AgentTaskStatus.WAITING_APPROVAL)
        return record

    stored_risk = record.metadata.get("risk_level")
    if stored_risk != request.risk_level:
        raise HTTPException(status_code=409, detail="Task execution risk does not match its existing record")
    return record


def _task_response(record: AgentTaskRecord) -> ExecutionTaskResponse:
    metadata_record: dict[str, object] = dict(record.metadata)
    result = None
    if record.result is not None:
        result = ExecutionResultResponse(
            task_id=record.result.task_id,
            agent=record.result.agent,
            status=record.result.status,
            summary=record.result.summary,
            evidence=list(record.result.evidence),
            risks=list(record.result.risks),
            requires_approval=record.result.requires_approval,
            error=record.result.error,
        )
    try:
        metadata = ExecutionMetadataResponse(
            risk_level=metadata_record.get("risk_level"),
            project_id=_safe_string(metadata_record, "project_id"),
            crud_status=_safe_string(metadata_record, "crud_status"),
            priority=_safe_string(metadata_record, "priority"),
            description=_safe_string(metadata_record, "description"),
            notes=_safe_notes(metadata_record),
            requested_by=_safe_string(metadata_record, "requested_by", "http"),
        )
        return ExecutionTaskResponse(
            task_id=record.task_id,
            objective=record.objective,
            status=record.status,
            assigned_agent=record.assigned_agent,
            created_at=record.created_at,
            updated_at=record.updated_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            parent_task_id=record.parent_task_id,
            metadata=metadata,
            result=result,
            error=record.error,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail="Stored task execution record is invalid") from exc


def _raise_engine_error(exc: TaskEngineError) -> None:
    if isinstance(exc, (BlackRiskError, InvalidTaskRiskError)):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, (RejectedApprovalError, TaskAlreadyRunningError, TerminalTaskError, ApprovalRequiredError)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise HTTPException(status_code=409, detail="Task execution state does not allow this operation") from exc


def _assign_requested_agent(runtime: TaskExecutionRuntime, record: AgentTaskRecord, agent_name: str) -> None:
    if record.assigned_agent is not None and record.assigned_agent != agent_name:
        raise HTTPException(status_code=409, detail="Task execution is already assigned to another agent")
    if record.assigned_agent is None:
        runtime.engine.assign_agent(record.task_id, agent_name)


async def _run_assigned_agent(
    runtime: TaskExecutionRuntime,
    record: AgentTaskRecord,
    context: AgentContext,
    response: Response,
) -> ExecuteTaskResponse:
    agent_name = record.assigned_agent
    if agent_name is None:
        response.status_code = 409
        return ExecuteTaskResponse(
            outcome="agent_unavailable",
            task=_task_response(record),
            detail="No agent is assigned to this task execution",
        )
    try:
        agent = runtime.agent_registry.get(agent_name)
    except KeyError:
        response.status_code = 409
        return ExecuteTaskResponse(
            outcome="agent_unavailable",
            task=_task_response(record),
            detail=f"Agent '{agent_name}' is unavailable",
        )

    try:
        await runtime.engine.execute_task(record.task_id, agent, context)
    except TaskEngineError as exc:
        _raise_engine_error(exc)
    except Exception as exc:
        runtime.engine.set_error(record.task_id, "Agent execution failed")
        current = runtime.engine.get_task(record.task_id)
        if current.status == AgentTaskStatus.RUNNING:
            runtime.engine.transition(record.task_id, AgentTaskStatus.FAILED)
        raise HTTPException(status_code=500, detail="Agent execution failed") from exc

    response.status_code = 202
    return ExecuteTaskResponse(
        outcome="started",
        task=_task_response(runtime.engine.get_task(record.task_id)),
        detail="Task execution started",
    )


@router.post("/{task_id}/execute", response_model=ExecuteTaskResponse, status_code=202)
async def execute_task(
    task_id: str,
    request: ExecuteTaskRequest,
    response: Response,
    runtime: TaskExecutionRuntime = Depends(get_task_execution_runtime),
) -> ExecuteTaskResponse:
    async with runtime.lock_for(task_id):
        crud_task = _crud_task_or_404(task_id)
        record = _ensure_engine_task(runtime, task_id, crud_task, request)
        try:
            runtime.engine.check_execution_allowed(task_id)
        except ApprovalRequiredError:
            _assign_requested_agent(runtime, record, request.agent_name)
            response.status_code = 202
            return ExecuteTaskResponse(
                outcome="approval_required",
                task=_task_response(runtime.engine.get_task(task_id)),
                detail="Task execution requires approval",
            )
        except TaskEngineError as exc:
            _raise_engine_error(exc)

        _assign_requested_agent(runtime, record, request.agent_name)
        return await _run_assigned_agent(
            runtime,
            runtime.engine.get_task(task_id),
            AgentContext(metadata=dict(request.context)),
            response,
        )


@router.get("/{task_id}", response_model=ExecutionTaskResponse)
def get_task_execution(
    task_id: str,
    runtime: TaskExecutionRuntime = Depends(get_task_execution_runtime),
) -> ExecutionTaskResponse:
    return _task_response(_engine_task_or_404(runtime, task_id))


@router.post("/{task_id}/cancel", response_model=ExecutionTaskResponse)
def cancel_task_execution(
    task_id: str,
    runtime: TaskExecutionRuntime = Depends(get_task_execution_runtime),
) -> ExecutionTaskResponse:
    _engine_task_or_404(runtime, task_id)
    try:
        record = runtime.engine.request_cancel(task_id)
    except TaskEngineError as exc:
        _raise_engine_error(exc)
    return _task_response(record)


def _approval_task_id(record: dict[str, object]) -> str | None:
    explicit_task_id = record.get("task_id")
    payload = record.get("payload")
    if "task_id" in record and not isinstance(explicit_task_id, str):
        raise HTTPException(status_code=409, detail="Stored approval has invalid task ID")
    if payload is not None and not isinstance(payload, dict):
        raise HTTPException(status_code=409, detail="Stored approval payload is invalid")
    payload_task_id = payload.get("task_id") if isinstance(payload, dict) else None
    if isinstance(payload, dict) and "task_id" in payload and not isinstance(payload_task_id, str):
        raise HTTPException(status_code=409, detail="Stored approval payload has invalid task ID")
    explicit = explicit_task_id if isinstance(explicit_task_id, str) else None
    linked = payload_task_id if isinstance(payload_task_id, str) else None
    if explicit is not None and linked is not None and explicit != linked:
        raise HTTPException(status_code=409, detail="Stored approval has conflicting task IDs")
    return explicit or linked


def _approval_response(record: dict[str, object], expected_task_id: str) -> TaskApprovalResponse:
    linked_task_id = _approval_task_id(record)
    if linked_task_id != expected_task_id:
        raise HTTPException(status_code=409, detail="Approval is linked to a different task")
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=409, detail="Stored approval payload is invalid")
    payload_task_id = payload.get("task_id")
    explicit_task_id = record.get("task_id")
    if payload_task_id is not None and payload_task_id != expected_task_id:
        raise HTTPException(status_code=409, detail="Stored approval payload is invalid")
    if payload_task_id is None and explicit_task_id != expected_task_id:
        raise HTTPException(status_code=409, detail="Stored approval has no valid task link")
    try:
        return TaskApprovalResponse(
            id=_safe_string(record, "id"),
            task_id=expected_task_id,
            title=_safe_string(record, "title"),
            project_id=_safe_string(record, "project_id"),
            action_type=_safe_string(record, "action_type"),
            risk_level=record.get("risk_level"),
            status=record.get("status"),
            description=_safe_string(record, "description"),
            payload={"task_id": expected_task_id},
            notes=_safe_notes(record),
            created_at=_safe_string(record, "created_at"),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail="Stored approval record is invalid") from exc


@router.post("/{task_id}/approvals", response_model=TaskApprovalResponse)
def create_task_approval(
    task_id: str,
    request: TaskApprovalCreateRequest,
    runtime: TaskExecutionRuntime = Depends(get_task_execution_runtime),
) -> TaskApprovalResponse:
    crud_task = _crud_task_or_404(task_id)
    if request.risk_level == "black":
        raise HTTPException(status_code=403, detail="Black risk approvals cannot be created")
    if request.risk_level == "green":
        raise HTTPException(status_code=409, detail="Green risk tasks do not require approval")

    try:
        execution = runtime.engine.get_task(task_id)
    except KeyError:
        execution = None
    if execution is not None and execution.metadata.get("risk_level") != request.risk_level:
        raise HTTPException(status_code=409, detail="Approval risk does not match task execution risk")

    action = request.action
    approval = upsert_item(
        APPROVALS_PATH,
        {
            "task_id": task_id,
            "title": action[:80],
            "project_id": _safe_string(crud_task, "project_id"),
            "action_type": "task_execution",
            "risk_level": request.risk_level,
            "status": "bekliyor",
            "description": action,
            "payload": {"task_id": task_id},
            "notes": [],
        },
        "onay",
    )
    return _approval_response(approval, task_id)


@router.get("/{task_id}/approvals", response_model=list[TaskApprovalResponse])
def list_task_approvals(task_id: str) -> list[TaskApprovalResponse]:
    _crud_task_or_404(task_id)
    approvals: list[TaskApprovalResponse] = []
    for record in list_items(APPROVALS_PATH):
        if _approval_task_id(record) == task_id:
            approvals.append(_approval_response(record, task_id))
    return approvals


@router.post("/{task_id}/resume", response_model=ExecuteTaskResponse, status_code=202)
async def resume_task_execution(
    task_id: str,
    request: ResumeTaskRequest,
    response: Response,
    runtime: TaskExecutionRuntime = Depends(get_task_execution_runtime),
) -> ExecuteTaskResponse:
    async with runtime.lock_for(task_id):
        _crud_task_or_404(task_id)
        record = _engine_task_or_404(runtime, task_id)
        approval_record = find_item(APPROVALS_PATH, request.approval_id)
        if approval_record is None:
            raise HTTPException(status_code=404, detail="Approval not found")
        approval = _approval_response(approval_record, task_id)
        if approval.risk_level == "black":
            raise HTTPException(status_code=403, detail="Black risk approvals cannot resume execution")
        if approval.status != "onaylandı":
            raise HTTPException(status_code=409, detail="Approval is not approved")
        if record.metadata.get("risk_level") != approval.risk_level:
            raise HTTPException(status_code=409, detail="Approval risk does not match task execution risk")

        try:
            runtime.engine.check_execution_allowed(task_id)
        except TaskEngineError as exc:
            _raise_engine_error(exc)
        return await _run_assigned_agent(
            runtime,
            record,
            AgentContext(metadata={"approval_id": request.approval_id}),
            response,
        )
