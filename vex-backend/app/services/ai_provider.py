from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.schemas.ai_provider import ProviderCapabilities


class TaskType(str, Enum):
    CHAT = "chat"
    CODING = "coding"
    PLANNING = "planning"
    REASONING = "reasoning"
    VISION = "vision"
    COMPUTER_USE = "computer_use"
    SEO = "seo"
    STRUCTURED_JSON = "structured_json"
    TOOL_CALLING = "tool_calling"


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderRequest:
    system_prompt: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    response_format: dict[str, Any] | None = None
    stream: bool = False
    timeout: float | None = None
    task_type: TaskType = TaskType.CHAT
    requires_vision: bool = False
    requires_tools: bool = False


@dataclass
class ProviderResponse:
    content: str | None = None
    provider: str = ""
    model: str = ""
    finish_reason: FinishReason = FinishReason.STOP
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0
    error: str | None = None
    fallback_used: bool = False
    original_provider: str | None = None
    raw_provider_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class ProviderCapabilities:
    streaming: bool = False
    tools: bool = False
    vision: bool = False
    json_mode: bool = False
    system_prompt: bool = True


@dataclass
class ProviderHealth:
    provider: str
    model: str
    configured: bool = False
    enabled: bool = True
    available: bool = False
    status: str = "not_configured"  # connected, not_configured, disabled, degraded, rate_limited, unavailable, checking
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    supports_json: bool = False
    last_success_at: float | None = None
    last_failure_at: float | None = None
    last_error_code: str | None = None
    consecutive_failures: int = 0
    rate_limited: bool = False
    average_latency_ms: float = 0.0


class AiProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._consecutive_failures = 0
        self._last_latencies: list[float] = []
        self._failure_threshold = 3
        self._cooldown_seconds = 120
        self._cooldown_until: float = 0

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier (e.g., 'gemini', 'nvidia')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Current model name."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """What this provider supports."""

    @abstractmethod
    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Non-streaming completion."""

    @abstractmethod
    async def stream(self, request: ProviderRequest):
        """Streaming completion - yields ProviderResponse chunks."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check provider health and capabilities."""

    def get_provider_name(self) -> str:
        return self.provider_name

    def get_model_name(self) -> str:
        return self.model_name

    def supports_streaming(self) -> bool:
        return False

    def supports_tools(self) -> bool:
        return False

    def supports_vision(self) -> bool:
        return False

    def supports_json(self) -> bool:
        return False

    def supports_system_prompt(self) -> bool:
        return True

    # Circuit breaker logic
    def _record_success(self, latency_ms: float):
        self._consecutive_failures = 0
        self._last_latencies.append(latency_ms)
        if len(self._last_latencies) > 100:
            self._last_latencies.pop(0)

    def _record_failure(self, error_code: str | None = None):
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self._cooldown_until = time.time() + self._cooldown_seconds

    def _is_in_cooldown(self) -> bool:
        return time.time() < self._cooldown_until

    def get_failure_count(self) -> int:
        return self._consecutive_failures

    def get_average_latency(self) -> float:
        if not self._last_latencies:
            return 0.0
        return sum(self._last_latencies) / len(self._last_latencies)

    def reset_circuit_breaker(self):
        self._consecutive_failures = 0
        self._cooldown_until = 0