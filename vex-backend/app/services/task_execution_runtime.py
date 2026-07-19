from __future__ import annotations

import asyncio

from fastapi import HTTPException, Request

from app.services.agent_kernel import AgentRegistry
from app.services.task_engine import TaskEngine


class TaskExecutionRuntime:
    """Application-scoped execution state and agent registry."""

    def __init__(
        self,
        engine: TaskEngine | None = None,
        agent_registry: AgentRegistry | None = None,
    ) -> None:
        self.engine = engine or TaskEngine()
        self.agent_registry = agent_registry or AgentRegistry()
        self._task_locks: dict[str, asyncio.Lock] = {}

    def lock_for(self, task_id: str) -> asyncio.Lock:
        lock = self._task_locks.get(task_id)
        if lock is None:
            lock = asyncio.Lock()
            self._task_locks[task_id] = lock
        return lock


def get_task_execution_runtime(request: Request) -> TaskExecutionRuntime:
    runtime = getattr(request.app.state, "task_execution_runtime", None)
    if not isinstance(runtime, TaskExecutionRuntime):
        raise HTTPException(status_code=503, detail="Task execution runtime is unavailable")
    return runtime
