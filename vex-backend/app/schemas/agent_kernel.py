from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


class AgentTask(BaseModel):
    task_id: str
    objective: str
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    requested_by: str


class AgentResult(BaseModel):
    task_id: str
    agent: str
    status: str
    summary: str
    artifacts: list[Any] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    error: str | None = None


@dataclass(slots=True)
class AgentContext:
    metadata: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    device_id: str | None = None
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)

    def request_cancel(self) -> None:
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    async def wait_cancelled(self) -> None:
        await self._cancel_event.wait()
