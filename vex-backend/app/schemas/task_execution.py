from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

from app.schemas.task_engine import AgentTaskStatus

RiskLevel = Literal["green", "yellow", "red", "black"]
ApprovalStatus = Literal["bekliyor", "onaylandı", "reddedildi"]
ExecutionOutcome = Literal["started", "approval_required", "agent_unavailable"]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExecuteTaskRequest(StrictRequestModel):
    agent_name: NonEmptyString
    risk_level: RiskLevel
    context: dict[str, JsonValue] = Field(default_factory=dict)


class ResumeTaskRequest(StrictRequestModel):
    approval_id: NonEmptyString


class ExecutionMetadataResponse(BaseModel):
    risk_level: RiskLevel
    project_id: str = ""
    crud_status: str = ""
    priority: str = ""
    description: str = ""
    notes: list[str] = Field(default_factory=list)
    requested_by: str = "http"


class ExecutionResultResponse(BaseModel):
    task_id: str
    agent: str
    status: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    error: str | None = None


class ExecutionTaskResponse(BaseModel):
    task_id: str
    objective: str
    status: AgentTaskStatus
    assigned_agent: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    parent_task_id: str | None = None
    metadata: ExecutionMetadataResponse
    result: ExecutionResultResponse | None = None
    error: str | None = None


class ExecuteTaskResponse(BaseModel):
    outcome: ExecutionOutcome
    task: ExecutionTaskResponse
    detail: str


class ApprovalPayloadResponse(BaseModel):
    task_id: str


class TaskApprovalCreateRequest(StrictRequestModel):
    risk_level: RiskLevel
    action: NonEmptyString


class TaskApprovalResponse(BaseModel):
    id: str
    task_id: str
    title: str
    project_id: str = ""
    action_type: str
    risk_level: RiskLevel
    status: ApprovalStatus
    description: str
    payload: ApprovalPayloadResponse
    notes: list[str] = Field(default_factory=list)
    created_at: datetime
