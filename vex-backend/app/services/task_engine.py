from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from app.core.paths import APPROVALS_PATH
from app.schemas.agent_kernel import AgentResult, AgentTask
from app.schemas.task_engine import AgentTaskRecord, AgentTaskStatus, TERMINAL_TASK_STATUSES
from app.storage.entity_store import list_items

ALLOWED_TRANSITIONS: dict[AgentTaskStatus, set[AgentTaskStatus]] = {
    AgentTaskStatus.CREATED: {
        AgentTaskStatus.PLANNING,
        AgentTaskStatus.BLOCKED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.NEEDS_HUMAN,
    },
    AgentTaskStatus.PLANNING: {
        AgentTaskStatus.WAITING_APPROVAL,
        AgentTaskStatus.RUNNING,
        AgentTaskStatus.BLOCKED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.NEEDS_HUMAN,
    },
    AgentTaskStatus.WAITING_APPROVAL: {
        AgentTaskStatus.RUNNING,
        AgentTaskStatus.BLOCKED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.NEEDS_HUMAN,
    },
    AgentTaskStatus.RUNNING: {
        AgentTaskStatus.VERIFYING,
        AgentTaskStatus.BLOCKED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.NEEDS_HUMAN,
    },
    AgentTaskStatus.VERIFYING: {
        AgentTaskStatus.COMPLETED,
        AgentTaskStatus.BLOCKED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.NEEDS_HUMAN,
        AgentTaskStatus.ROLLED_BACK,
    },
    AgentTaskStatus.BLOCKED: {
        AgentTaskStatus.PLANNING,
        AgentTaskStatus.RUNNING,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.NEEDS_HUMAN,
    },
    AgentTaskStatus.NEEDS_HUMAN: {
        AgentTaskStatus.PLANNING,
        AgentTaskStatus.RUNNING,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
    },
}


def _normalize_risk(value: str | None) -> str:
    return str(value or "").strip().lower()


def _get_linked_task_id(approval: dict) -> str | None:
    payload = approval.get("payload")
    if isinstance(payload, dict):
        return payload.get("task_id")
    return None


def _check_approval_gate(task_id: str, task_risk: str) -> None:
    """Enforce approval gate for WAITING_APPROVAL -> RUNNING transition.

    Raises ValueError if the transition should be blocked.
    """
    risk = _normalize_risk(task_risk)

    if risk == "black":
        raise ValueError("Task has black risk level - cannot proceed")

    if risk == "green":
        return

    if risk not in ("yellow", "red"):
        raise ValueError(f"Unknown or missing risk level: '{task_risk}'")

    approvals = list_items(APPROVALS_PATH)
    linked_approvals = [a for a in approvals if _get_linked_task_id(a) == task_id]

    if not linked_approvals:
        raise ValueError(f"No approval found for task '{task_id}' with risk level '{risk}'")

    has_rejected = any(a.get("status") == "reddedildi" for a in linked_approvals)
    if has_rejected:
        raise ValueError(f"Task '{task_id}' has a rejected approval")

    has_approved = any(a.get("status") == "onaylandı" for a in linked_approvals)
    if not has_approved:
        raise ValueError(f"Task '{task_id}' requires an approved approval for risk level '{risk}'")


class TaskEngine:
    def __init__(self, now_provider: Callable[[], datetime] | None = None) -> None:
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._tasks: dict[str, AgentTaskRecord] = {}

    def _now(self) -> datetime:
        current = self._now_provider()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("now_provider must return timezone-aware UTC datetimes.")
        return current.astimezone(timezone.utc)

    def create_task(self, task: AgentTask, parent_task_id: str | None = None) -> AgentTaskRecord:
        if task.task_id in self._tasks:
            raise ValueError(f"Task '{task.task_id}' is already registered.")
        if not task.objective.strip():
            raise ValueError("Task objective cannot be empty.")
        now = self._now()
        record = AgentTaskRecord(
            task_id=task.task_id,
            objective=task.objective,
            status=AgentTaskStatus.CREATED,
            created_at=now,
            updated_at=now,
            parent_task_id=parent_task_id,
            metadata=dict(task.context),
        )
        self._tasks[task.task_id] = record
        return record

    def get_task(self, task_id: str) -> AgentTaskRecord:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"Task '{task_id}' is not registered.") from exc

    def list_tasks(self) -> list[AgentTaskRecord]:
        return list(self._tasks.values())

    def transition(self, task_id: str, new_status: AgentTaskStatus) -> AgentTaskRecord:
        record = self.get_task(task_id)
        if record.status in TERMINAL_TASK_STATUSES:
            raise ValueError(f"Task '{task_id}' is already terminal with status '{record.status.value}'.")
        allowed = ALLOWED_TRANSITIONS.get(record.status, set())
        if new_status not in allowed:
            raise ValueError(f"Invalid transition for task '{task_id}': {record.status.value} -> {new_status.value}.")

        if record.status == AgentTaskStatus.WAITING_APPROVAL and new_status == AgentTaskStatus.RUNNING:
            risk = record.metadata.get("risk_level")
            _check_approval_gate(task_id, str(risk) if risk is not None else "")

        now = self._now()
        record.status = new_status
        record.updated_at = now
        if new_status == AgentTaskStatus.RUNNING and record.started_at is None:
            record.started_at = now
        if new_status in TERMINAL_TASK_STATUSES:
            record.completed_at = now
        return record

    def assign_agent(self, task_id: str, agent_name: str) -> AgentTaskRecord:
        if not agent_name.strip():
            raise ValueError("Agent name cannot be empty.")
        record = self.get_task(task_id)
        record.assigned_agent = agent_name
        record.updated_at = self._now()
        return record

    def set_result(self, task_id: str, result: AgentResult) -> AgentTaskRecord:
        record = self.get_task(task_id)
        record.result = result
        record.updated_at = self._now()
        return record

    def set_error(self, task_id: str, error: str) -> AgentTaskRecord:
        record = self.get_task(task_id)
        record.error = error
        record.updated_at = self._now()
        return record

    def request_cancel(self, task_id: str) -> AgentTaskRecord:
        return self.transition(task_id, AgentTaskStatus.CANCELLED)
