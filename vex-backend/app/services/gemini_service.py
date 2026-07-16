from __future__ import annotations

import base64
import time
from typing import Any, AsyncGenerator

from google.genai import types as genai_types

from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_VISION_MODEL,
    GEMINI_TIMEOUT_SECONDS,
    GEMINI_MAX_RETRIES,
    GEMINI_ENABLED,
)
from app.schemas.ai_provider import (
    AiProvider,
    ProviderCapabilities,
    ProviderHealth,
    ProviderRequest,
    ProviderResponse,
    ToolCall,
)
from app.services.ai_provider import FinishReason

_client: Any = None

_RETRYABLE_STATUS_MARKERS = ("404", "NOT_FOUND", "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")


def _is_retryable_error(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in _RETRYABLE_STATUS_MARKERS)


def _call_with_retry(func, *, attempts: int = 3, delay: float = 0.6):
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return func(), None
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1 and _is_retryable_error(exc):
                time.sleep(delay * (attempt + 1))
                continue
            break
    return None, last_exc


def _get_client() -> tuple[Any, str | None]:
    global _client
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY tanımlı değil."
    if _client is not None:
        return _client, None

    try:
        from google import genai
        from google.genai import types as genai_types_local

        if hasattr(genai_types_local, "HttpOptions"):
            _client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=genai_types_local.HttpOptions(api_version="v1beta"),
            )
        else:
            _client = genai.Client(api_key=GEMINI_API_KEY)
        return _client, None
    except Exception as exc:
        return None, f"Gemini client oluşturulamadı: {exc}"


def strip_code_fences(text: str) -> str:
    value = (text or "").strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def _convert_messages(messages: list[dict[str, Any]], system_prompt: str | None) -> list[dict[str, Any]]:
    """Convert standard messages to Gemini format."""
    result = []

    if system_prompt:
        result.append({"role": "user", "parts": [{"text": f"System: {system_prompt}"}]})
        result.append({"role": "model", "parts": [{"text": "Understood."}]})

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            continue

        gemini_role = "model" if role == "assistant" else "user"
        result.append({"role": gemini_role, "parts": [{"text": content}]})

    return result


def _convert_tools(tools: list[dict[str, Any]] | None) -> list[Any] | None:
    """Convert standard tool definitions to Gemini function declarations."""
    if not tools:
        return None

    declarations = []
    for tool in tools:
        if tool.get("type") == "function":
            func = tool.get("function", {})
            declarations.append(genai_types.FunctionDeclaration(
                name=func.get("name", ""),
                description=func.get("description", ""),
                parameters=func.get("parameters", {"type": "object", "properties": {}}),
            ))
        elif "name" in tool:
            declarations.append(genai_types.FunctionDeclaration(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters=tool.get("parameters", {"type": "object", "properties": {}}),
            ))

    if declarations:
        return [genai_types.Tool(function_declarations=declarations)]
    return None


class GeminiProvider(AiProvider):
    """Google Gemini provider implementation."""

    def __init__(self):
        super().__init__()
        self._health: ProviderHealth | None = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return GEMINI_MODEL

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            supports_json=True,
            supports_system_prompt=True,
        )

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        start_time = time.perf_counter()

        if not GEMINI_ENABLED:
            return ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error="Gemini provider is disabled",
                finish_reason=FinishReason.ERROR,
            )

        if not GEMINI_API_KEY:
            return ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error="GEMINI_API_KEY not configured",
                finish_reason=FinishReason.ERROR,
            )

        if self._is_in_cooldown():
            return ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error="Provider in cooldown after consecutive failures",
                finish_reason=FinishReason.ERROR,
            )

        try:
            client, error = _get_client()
            if error:
                self._record_failure("config")
                return ProviderResponse(
                    content=None,
                    provider=self.provider_name,
                    model=self.model_name,
                    error=error,
                    finish_reason=FinishReason.ERROR,
                )

            messages = _convert_messages(request.messages, request.system_prompt)
            tools = _convert_tools(request.tools)

            contents = []
            for msg in messages:
                role = msg.get("role", "user")
                parts = msg.get("parts", [])
                if isinstance(parts[0], dict) and "text" in parts[0]:
                    contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=p["text"]) for p in parts]))
                else:
                    contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=str(p)) for p in parts]))

            config = genai_types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                tools=tools,
                response_mime_type="application/json" if request.response_format and request.response_format.get("type") == "json_object" else None,
            )

            last_error: Exception | None = None
            for attempt in range(GEMINI_MAX_RETRIES):
                try:
                    response = await client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=config,
                    )
                    latency_ms = int((time.perf_counter() - start_time) * 1000)

                    self._record_success(latency_ms)

                    text = getattr(response, "text", "") or ""
                    finish_reason_str = "stop"
                    if hasattr(response, "candidates") and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, "finish_reason"):
                            finish_reason_str = str(candidate.finish_reason).lower()
                            if "tool" in finish_reason_str:
                                finish_reason_str = "tool_calls"
                            elif "length" in finish_reason_str:
                                finish_reason_str = "length"

                    try:
                        finish_reason = FinishReason(finish_reason_str)
                    except ValueError:
                        finish_reason = FinishReason.STOP

                    tool_calls = []
                    if hasattr(response, "candidates") and response.candidates:
                        for part in getattr(response.candidates[0].content, "parts", []):
                            if hasattr(part, "function_call") and part.function_call:
                                fc = part.function_call
                                tool_calls.append(ToolCall(
                                    id=fc.name,
                                    name=fc.name,
                                    arguments=dict(fc.args) if fc.args else {},
                                ))

                    usage = {}
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        usage = {
                            "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                            "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                            "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                        }

                    return ProviderResponse(
                        content=text,
                        provider=self.provider_name,
                        model=self.model_name,
                        finish_reason=finish_reason,
                        tool_calls=tool_calls if tool_calls else None,
                        usage=usage if usage else None,
                        latency_ms=latency_ms,
                        raw_provider_metadata={"model": self.model_name},
                    )

                except Exception as e:
                    last_error = e
                    self._record_failure(type(e).__name__)
                    if attempt < GEMINI_MAX_RETRIES - 1 and _is_retryable_error(e):
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    break

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            error_msg = f"Gemini request failed after {GEMINI_MAX_RETRIES} attempts: {last_error}"

            return ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error=error_msg,
                finish_reason=FinishReason.ERROR,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            self._record_failure("unknown")
            return ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error=str(e),
                finish_reason=FinishReason.ERROR,
                latency_ms=latency_ms,
            )

    async def stream(self, request: ProviderRequest) -> AsyncGenerator[ProviderResponse, None]:
        if not GEMINI_ENABLED or not GEMINI_API_KEY:
            yield ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error="Gemini not configured or disabled",
                finish_reason=FinishReason.ERROR,
            )
            return

        try:
            client, error = _get_client()
            if error:
                yield ProviderResponse(
                    content=None,
                    provider=self.provider_name,
                    model=self.model_name,
                    error=error,
                    finish_reason=FinishReason.ERROR,
                )
                return

            messages = _convert_messages(request.messages, request.system_prompt)
            tools = _convert_tools(request.tools)

            contents = []
            for msg in messages:
                role = msg.get("role", "user")
                parts = msg.get("parts", [])
                if isinstance(parts[0], dict) and "text" in parts[0]:
                    contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=p["text"]) for p in parts]))
                else:
                    contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=str(p)) for p in parts]))

            config = genai_types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                tools=tools,
            )

            stream = await client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            async for chunk in stream:
                text = getattr(chunk, "text", None)
                finish_reason = FinishReason.STOP

                if hasattr(chunk, "candidates") and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, "finish_reason"):
                        fr = str(candidate.finish_reason).lower()
                        if "tool" in fr:
                            finish_reason = FinishReason.TOOL_CALLS
                        elif "length" in fr:
                            finish_reason = FinishReason.LENGTH

                tool_calls = None
                if hasattr(chunk, "candidates") and chunk.candidates:
                    for part in getattr(chunk.candidates[0].content, "parts", []):
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            if tool_calls is None:
                                tool_calls = []
                            tool_calls.append(ToolCall(
                                id=fc.name,
                                name=fc.name,
                                arguments=dict(fc.args) if fc.args else {},
                            ))

                yield ProviderResponse(
                    content=text,
                    provider=self.provider_name,
                    model=self.model_name,
                    finish_reason=finish_reason,
                    tool_calls=tool_calls,
                    raw_provider_metadata={},
                )

        except Exception as e:
            yield ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error=str(e),
                finish_reason=FinishReason.ERROR,
            )

    async def health_check(self) -> ProviderHealth:
        if self._health is None:
            self._health = ProviderHealth(
                provider=self.provider_name,
                model=self.model_name,
            )

        if not GEMINI_ENABLED:
            self._health.configured = False
            self._health.enabled = False
            self._health.status = "disabled"
            return self._health

        if not GEMINI_API_KEY:
            self._health.configured = False
            self._health.status = "not_configured"
            return self._health

        self._health.configured = True
        self._health.enabled = True

        if self._is_in_cooldown():
            self._health.status = "unavailable"
            self._health.available = False
            return self._health

        try:
            client, error = _get_client()
            if error:
                self._health.status = "not_configured"
                self._health.last_error_code = "config_error"
                return self._health

            test_contents = [genai_types.Content(role="user", parts=[genai_types.Part(text="ping")])]
            config = genai_types.GenerateContentConfig(temperature=0, max_output_tokens=5)
            start = time.perf_counter()
            response = await client.aio.models.generate_content(
                model=self.model_name,
                contents=test_contents,
                config=config,
            )
            latency = (time.perf_counter() - start) * 1000

            if getattr(response, "text", None) is not None:
                self._health.available = True
                self._health.status = "connected"
                self._health.last_success_at = time.time()
                self._health.average_latency_ms = (self._health.average_latency_ms * 0.9) + (latency * 0.1)
            else:
                self._health.status = "degraded"
                self._health.last_failure_at = time.time()

        except Exception as e:
            self._health.available = False
            self._health.status = "unavailable"
            self._health.last_failure_at = time.time()
            self._health.last_error_code = type(e).__name__

        self._health.supports_streaming = True
        self._health.supports_tools = True
        self._health.supports_vision = True
        self._health.supports_json = True

        return self._health


import asyncio


# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =============================================================================

def generate_text(prompt: str, model: str | None = None) -> dict:
    """Legacy sync wrapper for backward compatibility."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_async_generate_text(prompt, model))


async def _async_generate_text(prompt: str, model: str | None = None) -> dict:
    """Async implementation using provider router."""
    from app.services.ai_provider_router import initialize_router
    from app.schemas.ai_provider import ProviderRequest, TaskType
    from app.services.ai_provider import TaskType as AiTaskType

    router = await initialize_router()
    request = ProviderRequest(
        messages=[{"role": "user", "content": prompt}],
        task_type=AiTaskType.CHAT,
        temperature=0.7,
    )
    response = await router.complete(request)
    if response.error:
        return {"success": False, "message": response.error}
    return {"success": True, "text": response.content or ""}


def generate_with_image(prompt: str, image_base64: str, mime_type: str = "image/png", model: str | None = None) -> dict:
    """Legacy sync wrapper for vision requests."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_async_generate_with_image(prompt, image_base64, mime_type, model))


async def _async_generate_with_image(prompt: str, image_base64: str, mime_type: str = "image/png", model: str | None = None) -> dict:
    """Async implementation for vision using provider router."""
    from app.services.ai_provider_router import initialize_router
    from app.schemas.ai_provider import ProviderRequest
    from app.services.ai_provider import TaskType as AiTaskType

    router = await initialize_router()
    # Try to get a vision-capable provider
    provider = router.get_provider("gemini")  # Gemini supports vision
    if not provider:
        # Fallback to any available
        providers = router.get_available_providers()
        provider = providers[0] if providers else None

    if not provider:
        return {"success": False, "message": "No vision-capable provider available"}

    import base64
    try:
        raw = base64.b64decode(image_base64)
    except Exception as exc:
        return {"success": False, "message": f"Görüntü çözümlenemedi: {exc}"}

    # Use the provider directly for vision
    from app.schemas.ai_provider import ProviderRequest

    request = ProviderRequest(
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "image": image_base64, "mime_type": mime_type}
            ]
        }],
        task_type=AiTaskType.VISION,
        temperature=0.7,
    )
    response = await provider.complete(request)
    if response.error:
        return {"success": False, "message": response.error}
    return {"success": True, "text": response.content or ""}


def strip_code_fences(text: str) -> str:
    """Legacy function for backward compatibility."""
    value = (text or "").strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value