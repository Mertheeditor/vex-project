from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.config import AI_PROVIDER_MODE, AI_PROVIDER_FALLBACK_ORDER
from app.schemas.ai_provider import (
    AiProvider,
    ProviderCapabilities,
    ProviderHealth,
    ProviderRequest,
    ProviderResponse,
)
from app.services.ai_provider import FinishReason, TaskType

logger = logging.getLogger(__name__)


class RoutingMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class FallbackReason(str, Enum):
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    CONNECTION_ERROR = "connection_error"
    CIRCUIT_OPEN = "circuit_open"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ProviderRoute:
    """Routing decision with provider and fallback info."""
    provider: AiProvider
    is_fallback: bool = False
    fallback_reason: FallbackReason | None = None
    attempted_providers: list[str] = None

    def __post_init__(self):
        if self.attempted_providers is None:
            self.attempted_providers = [self.provider.provider_name]


@dataclass
class RoutingConfig:
    """Configuration for provider routing."""
    mode: RoutingMode = RoutingMode.AUTO
    manual_provider: str | None = None
    task_priority_map: dict[TaskType, list[str]] | None = None
    fallback_order: list[str] | None = None
    respect_circuit_breaker: bool = True
    respect_disabled: bool = True
    respect_health: bool = True


DEFAULT_TASK_PRIORITY: dict[TaskType, list[str]] = {
    TaskType.CHAT: ["gemini", "nvidia"],
    TaskType.CODING: ["gemini", "nvidia"],
    TaskType.PLANNING: ["gemini", "nvidia"],
    TaskType.REASONING: ["gemini", "nvidia"],
    TaskType.VISION: ["gemini"],
    TaskType.COMPUTER_USE: ["gemini"],
    TaskType.SEO: ["gemini", "nvidia"],
    TaskType.STRUCTURED_JSON: ["gemini", "nvidia"],
    TaskType.TOOL_CALLING: ["gemini", "nvidia"],
}


DEFAULT_FALLBACK_ORDER = ["gemini", "nvidia"]


FALLBACK_TRIGGER_CODES = {
    "timeout",
    "429",
    "500",
    "502",
    "503",
    "504",
    "connection_error",
    "rate_limited",
    "server_error",
    "circuit_open",
}

NON_FALLBACK_CODES = {
    "user_cancel",
    "approval_gate",
    "security_deny",
    "validation_error",
    "invalid_request",
}


class ProviderRouter:
    """Routes requests to AI providers based on mode, task type, and health."""

    def __init__(self):
        self._providers: dict[str, AiProvider] = {}
        self._config = RoutingConfig()
        self._initialized = False

    def register_provider(self, provider: AiProvider) -> None:
        """Register a provider by name."""
        self._providers[provider.provider_name] = provider
        logger.info(f"Registered AI provider: {provider.provider_name} ({provider.model_name})")

    def get_provider(self, name: str) -> AiProvider | None:
        """Get a registered provider by name."""
        return self._providers.get(name)

    def get_all_providers(self) -> list[AiProvider]:
        """Get all registered providers."""
        return list(self._providers.values())

    def get_available_providers(self) -> list[AiProvider]:
        """Get providers that are configured and enabled."""
        available = []
        for provider in self._providers.values():
            caps = provider.get_capabilities()
            if caps.system_prompt or caps.vision or caps.tools or caps.streaming:
                available.append(provider)
        return available

    def configure(
        self,
        mode: str | RoutingMode = RoutingMode.AUTO,
        manual_provider: str | None = None,
        task_priority_map: dict[TaskType, list[str]] | None = None,
        fallback_order: list[str] | None = None,
        respect_circuit_breaker: bool = True,
        respect_disabled: bool = True,
        respect_health: bool = True,
    ) -> None:
        """Configure routing behavior."""
        self._config.mode = RoutingMode(mode) if isinstance(mode, str) else mode
        self._config.manual_provider = manual_provider
        self._config.task_priority_map = task_priority_map or DEFAULT_TASK_PRIORITY
        self._config.fallback_order = fallback_order or DEFAULT_FALLBACK_ORDER
        self._config.respect_circuit_breaker = respect_circuit_breaker
        self._config.respect_disabled = respect_disabled
        self._config.respect_health = respect_health
        logger.info(f"Router configured: mode={self._config.mode.value}, manual={manual_provider}")

    def _is_provider_available(self, provider: AiProvider) -> bool:
        """Check if provider is available for routing."""
        if self._config.respect_disabled:
            caps = provider.capabilities
            if not caps:
                return False

        if self._config.respect_circuit_breaker and provider.get_failure_count() >= 3:
            return False

        if provider._is_in_cooldown():
            return False

        return True

    def _get_providers_for_task(self, task_type: TaskType) -> list[AiProvider]:
        """Get ordered list of providers for a task type."""
        priority_list = self._config.task_priority_map.get(task_type, DEFAULT_FALLBACK_ORDER)
        result = []
        for name in priority_list:
            provider = self._providers.get(name)
            if provider and self._is_provider_available(provider):
                result.append(provider)
        return result

    def _should_fallback(self, response: ProviderResponse | None, error_code: str | None = None) -> bool:
        """Determine if we should fallback based on response/error."""
        if response is None:
            return True

        if error_code and error_code in FALLBACK_TRIGGER_CODES:
            return True

        if response.error:
            error_lower = response.error.lower()
            for trigger in FALLBACK_TRIGGER_CODES:
                if trigger in error_lower:
                    return True

        if response.finish_reason == FinishReason.ERROR:
            return True

        return False

    def route(self, request: ProviderRequest) -> ProviderRoute | None:
        """Determine which provider to use for a request."""
        task_type = getattr(request, "task_type", TaskType.CHAT)

        if self._config.mode == RoutingMode.MANUAL:
            if self._config.manual_provider:
                provider = self._providers.get(self._config.manual_provider)
                if provider and self._is_provider_available(provider):
                    return ProviderRoute(provider=provider)
                logger.warning(f"Manual provider {self._config.manual_provider} not available, falling back to auto")
            return self._route_auto(request)

        return self._route_auto(request)

    def _route_auto(self, request: ProviderRequest) -> ProviderRoute | None:
        """Auto-route based on task type priority."""
        task_type = getattr(request, "task_type", TaskType.CHAT)
        providers = self._get_providers_for_task(task_type)

        if not providers:
            return None

        return ProviderRoute(provider=providers[0])

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute completion with automatic fallback."""
        route = self.route(request)
        if not route:
            return ProviderResponse(
                content=None,
                provider="none",
                model="none",
                error="No available providers",
                finish_reason=FinishReason.ERROR,
            )

        provider = route.provider
        attempted = [provider.provider_name]

        response = await provider.complete(request)

        if self._should_fallback(response):
            fallback_providers = self._get_fallback_providers(provider.provider_name)
            for fallback in fallback_providers:
                if fallback.provider_name in attempted:
                    continue
                logger.warning(
                    f"Falling back from {provider.provider_name} to {fallback.provider_name}: "
                    f"reason={response.error or 'error'}"
                )
                attempted.append(fallback.provider_name)
                route.is_fallback = True
                route.fallback_reason = FallbackReason.SERVER_ERROR
                route.attempted_providers = attempted
                provider = fallback
                response = await fallback.complete(request)

                if not self._should_fallback(response):
                    break

            if route.is_fallback:
                response.fallback_used = True
                response.original_provider = route.attempted_providers[0] if route.attempted_providers else None

        return response

    async def stream(self, request: ProviderRequest):
        """Execute streaming completion with fallback on error."""
        route = self.route(request)
        if not route:
            yield ProviderResponse(
                content=None,
                provider="none",
                model="none",
                error="No available providers",
                finish_reason=FinishReason.ERROR,
            )
            return

        provider = route.provider
        attempted = [provider.provider_name]

        async for chunk in provider.stream(request):
            yield chunk
            if chunk.error and self._should_fallback(chunk, chunk.error):
                break

        if self._should_fallback(None):
            fallback_providers = self._get_fallback_providers(provider.provider_name)
            for fallback in fallback_providers:
                if fallback.provider_name in attempted:
                    continue
                logger.warning(f"Stream fallback from {provider.provider_name} to {fallback.provider_name}")
                attempted.append(fallback.provider_name)
                async for chunk in fallback.stream(request):
                    if chunk.finish_reason == FinishReason.ERROR and self._should_fallback(chunk, chunk.error):
                        continue
                    chunk.fallback_used = True
                    chunk.original_provider = route.attempted_providers[0] if route.attempted_providers else None
                    yield chunk
                break

    def _get_fallback_providers(self, exclude: str) -> list[AiProvider]:
        """Get fallback providers excluding the given one."""
        fallbacks = []
        for name in self._config.fallback_order:
            if name == exclude:
                continue
            provider = self._providers.get(name)
            if provider and self._is_provider_available(provider):
                fallbacks.append(provider)
        return fallbacks

    async def get_health_status(self) -> dict[str, ProviderHealth]:
        """Get health status for all providers."""
        status = {}
        for name, provider in self._providers.items():
            try:
                health = await provider.health_check()
                status[name] = health
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                status[name] = ProviderHealth(
                    provider=name,
                    model=provider.model_name,
                    configured=False,
                    status="unavailable",
                    last_error_code=type(e).__name__,
                )
        return status


_router_instance: ProviderRouter | None = None


def get_router() -> ProviderRouter:
    """Get or create the singleton router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ProviderRouter()
    return _router_instance


async def initialize_router() -> ProviderRouter:
    """Initialize router with configured providers."""
    router = get_router()

    if router._initialized:
        return router

    from app.services.gemini_service import GeminiProvider
    from app.services.nvidia_service import NvidiaProvider

    gemini = GeminiProvider()
    nvidia = NvidiaProvider()

    router.register_provider(gemini)
    router.register_provider(nvidia)

    mode = AI_PROVIDER_MODE or "auto"
    fallback_order = AI_PROVIDER_FALLBACK_ORDER.split(",") if AI_PROVIDER_FALLBACK_ORDER else None
    router.configure(mode=mode, fallback_order=fallback_order)

    router._initialized = True
    logger.info("Provider router initialized with providers: gemini, nvidia")
    return router


async def get_provider_health() -> dict[str, ProviderHealth]:
    """Get health status for all providers."""
    router = await initialize_router()
    return await router.get_health_status()