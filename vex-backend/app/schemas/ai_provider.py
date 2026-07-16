from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# REQUEST / RESPONSE MODELS (Provider-agnostic)
# =============================================================================


class ToolCall(BaseModel):
    """Standardized tool call representation."""

    id: str
    name: str
    arguments: dict[str, Any]


class ToolDefinition(BaseModel):
    """Standardized tool definition for provider能力查询."""

    name: str
    description: str
    parameters: dict[str, Any]


class ProviderRequest(BaseModel):
    """Unified request sent to any provider."""

    system_prompt: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: str | dict | None = None  # "auto", "none", or {"type": "function", "function": {"name": "..."}}
    response_format: dict[str, Any] | None = None  # e.g., {"type": "json_object"}
    stream: bool = False
    timeout_seconds: float = 60.0
    task_type: str = "chat"  # chat, coding, planning, reasoning, vision, computer_use, seo, structured_json, tool_calling
    requires_vision: bool = False
    requires_tools: bool = False


@dataclass
class ProviderResponse:
    """Unified response from any provider."""

    content: str | None
    provider: str
    model: str
    finish_reason: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: dict[str, int] | None = None
    latency_ms: int | None = None
    error: str | None = None
    fallback_used: bool = False
    original_provider: str | None = None
    raw_provider_metadata: dict[str, Any] | None = None


# =============================================================================
# PROVIDER CAPABILITIES
# =============================================================================


@dataclass
class ProviderCapabilities:
    """What a provider can do."""

    supports_streaming: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    supports_json: bool = False
    supports_system_prompt: bool = True
    max_context_tokens: int | None = None


@dataclass
class ProviderHealth:
    """Runtime health/status of a provider."""

    provider: str
    model: str
    configured: bool = False
    enabled: bool = True
    available: bool = False
    status: Literal[
        "connected",
        "not_configured",
        "disabled",
        "degraded",
        "rate_limited",
        "unavailable",
        "checking",
    ] = "not_configured"
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    supports_json: bool = False
    last_success_at: float | None = None
    last_failure_at: float | None = None
    last_error_code: str | None = None
    consecutive_failures: int = 0
    rate_limited: bool = False
    average_latency_ms: float | None = None


# =============================================================================
# PROVIDER SETTINGS
# =============================================================================


class ProviderSettings(BaseModel):
    """AI provider configuration settings."""

    mode: str = "auto"
    manual_provider: str | None = None
    fallback_order: list[str] = []
    available_providers: list[str] = []


# =============================================================================
# PROVIDER INTERFACE
# =============================================================================


class AiProvider(ABC):
    """Abstract base class for all AI providers."""

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
        """Unique provider identifier: 'gemini', 'nvidia', etc."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Current model being used."""

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
        """Check provider connectivity and update health status."""

    def get_provider_name(self) -> str:
        return self.provider_name

    def get_model_name(self) -> str:
        return self.model_name

    def supports_streaming(self) -> bool:
        return self.capabilities.supports_streaming

    def supports_tools(self) -> bool:
        return self.capabilities.supports_tools

    def supports_vision(self) -> bool:
        return self.capabilities.supports_vision

    def supports_json(self) -> bool:
        return self.capabilities.supports_json

    def supports_system_prompt(self) -> bool:
        return self.capabilities.supports_system_prompt

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