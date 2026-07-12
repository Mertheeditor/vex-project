from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.agent_kernel import AgentResult


class AgentTaskStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NEEDS_HUMAN = "needs_human"
    ROLLED_BACK = "rolled_back"


TERMINAL_TASK_STATUSES = {
    AgentTaskStatus.COMPLETED,
    AgentTaskStatus.FAILED,
    AgentTaskStatus.CANCELLED,
    AgentTaskStatus.ROLLED_BACK,
}


class AgentTaskRecord(BaseModel):
    task_id: str
    objective: str
    status: AgentTaskStatus
    assigned_agent: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    parent_task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    result: AgentResult | None = None
    error: str | None = None
