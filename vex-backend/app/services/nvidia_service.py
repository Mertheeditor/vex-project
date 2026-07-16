from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, AsyncGenerator

import httpx

from app.core.config import (
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    NVIDIA_TIMEOUT_SECONDS,
    NVIDIA_MAX_RETRIES,
    NVIDIA_ENABLED,
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

logger = logging.getLogger(__name__)


class NvidiaProvider(AiProvider):
    """NVIDIA NIM provider using OpenAI-compatible API."""

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._health: ProviderHealth | None = None

    @property
    def provider_name(self) -> str:
        return "nvidia"

    @property
    def model_name(self) -> str:
        return NVIDIA_MODEL

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,  # NVIDIA text models don't support vision
            supports_json=True,
            supports_system_prompt=True,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=NVIDIA_BASE_URL,
                headers={
                    "Authorization": f"Bearer {NVIDIA_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(NVIDIA_TIMEOUT_SECONDS),
            )
        return self._client

    def _convert_messages(self, messages: list[dict[str, Any]], system_prompt: str | None) -> list[dict[str, Any]]:
        """Convert standard messages to NVIDIA/OpenAI format."""
        result = []

        if system_prompt:
            result.append({"role": "system", "content": system_prompt})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle tool calls in assistant messages
            if role == "assistant" and "tool_calls" in msg:
                result.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": msg["tool_calls"],
                })
            elif role == "tool":
                result.append({
                    "role": "tool",
                    "content": content,
                    "tool_call_id": msg.get("tool_call_id", ""),
                })
            else:
                result.append({"role": role, "content": content})

        return result

    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Convert standard tool definitions to OpenAI format."""
        if not tools:
            return None
        converted = []
        for tool in tools:
            if tool.get("type") == "function":
                converted.append(tool)
            elif "name" in tool:
                converted.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                    },
                })
        return converted if converted else None

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        start_time = time.perf_counter()

        if not NVIDIA_ENABLED:
            return ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error="NVIDIA provider is disabled",
                finish_reason=FinishReason.ERROR,
            )

        if not NVIDIA_API_KEY:
            return ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error="NVIDIA_API_KEY not configured",
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

        client = await self._get_client()
        messages = self._convert_messages(request.messages, request.system_prompt)
        tools = self._convert_tools(request.tools)

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": request.temperature,
            "stream": False,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        if tools:
            payload["tools"] = tools
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice

        if request.response_format:
            payload["response_format"] = request.response_format

        last_error: Exception | None = None
        for attempt in range(NVIDIA_MAX_RETRIES):
            try:
                response = await client.post("/chat/completions", json=payload)
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                if response.status_code == 429:
                    self._record_failure("429")
                    wait_time = 2 ** attempt
                    logger.warning(f"NVIDIA rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    await asyncio.sleep(wait_time)
                    continue

                if response.status_code >= 500:
                    self._record_failure(str(response.status_code))
                    wait_time = 2 ** attempt
                    logger.warning(f"NVIDIA server error {response.status_code}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                data = response.json()

                self._record_success(latency_ms)

                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                finish_reason_str = choice.get("finish_reason", "stop")

                try:
                    finish_reason = FinishReason(finish_reason_str)
                except ValueError:
                    finish_reason = FinishReason.STOP

                tool_calls = []
                for tc in message.get("tool_calls", []):
                    tool_calls.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc.get("function", {}).get("name", ""),
                        arguments=json.loads(tc.get("function", {}).get("arguments", "{}")),
                    ))

                usage = data.get("usage", {})

                return ProviderResponse(
                    content=message.get("content"),
                    provider=self.provider_name,
                    model=self.model_name,
                    finish_reason=finish_reason,
                    tool_calls=tool_calls if tool_calls else None,
                    usage=usage if usage else None,
                    latency_ms=latency_ms,
                    raw_provider_metadata={"id": data.get("id"), "model": data.get("model")},
                )

            except httpx.TimeoutException as e:
                last_error = e
                self._record_failure("timeout")
                wait_time = 2 ** attempt
                logger.warning(f"NVIDIA timeout, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code
                self._record_failure(str(status))
                if status in (429, 500, 502, 503, 504):
                    wait_time = 2 ** attempt
                    logger.warning(f"NVIDIA error {status}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                error_body = e.response.text
                logger.error(f"NVIDIA HTTP error {status}: {error_body}")
                return ProviderResponse(
                    content=None,
                    provider=self.provider_name,
                    model=self.model_name,
                    error=f"HTTP {status}: {error_body}",
                    finish_reason=FinishReason.ERROR,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                )

            except Exception as e:
                last_error = e
                self._record_failure("unknown")
                logger.error(f"NVIDIA unexpected error: {e}")
                break

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        error_msg = f"NVIDIA request failed after {NVIDIA_MAX_RETRIES} attempts: {last_error}"
        logger.error(error_msg)

        return ProviderResponse(
            content=None,
            provider=self.provider_name,
            model=self.model_name,
            error=error_msg,
            finish_reason=FinishReason.ERROR,
            latency_ms=latency_ms,
        )

    async def stream(self, request: ProviderRequest) -> AsyncGenerator[ProviderResponse, None]:
        if not NVIDIA_ENABLED or not NVIDIA_API_KEY:
            yield ProviderResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                error="NVIDIA not configured or disabled",
                finish_reason=FinishReason.ERROR,
            )
            return

        client = await self._get_client()
        messages = self._convert_messages(request.messages, request.system_prompt)
        tools = self._convert_tools(request.tools)

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        if tools:
            payload["tools"] = tools
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice

        try:
            async with client.stream("POST", "/chat/completions", json=payload, timeout=NVIDIA_TIMEOUT_SECONDS) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choice = chunk.get("choices", [{}])[0]
                        delta = choice.get("delta", {})
                        finish_reason = choice.get("finish_reason")

                        content = delta.get("content")
                        tool_calls = delta.get("tool_calls")

                        yield ProviderResponse(
                            content=content,
                            provider=self.provider_name,
                            model=self.model_name,
                            finish_reason=FinishReason(finish_reason) if finish_reason else FinishReason.STOP,
                            tool_calls=[ToolCall(**tc) for tc in tool_calls] if tool_calls else None,
                            raw_provider_metadata=chunk,
                        )
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"NVIDIA streaming error: {e}")
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

        if not NVIDIA_ENABLED:
            self._health.configured = False
            self._health.enabled = False
            self._health.status = "disabled"
            return self._health

        if not NVIDIA_API_KEY:
            self._health.configured = False
            self._health.status = "not_configured"
            return self._health

        self._health.configured = True
        self._health.enabled = True

        if self._is_in_cooldown():
            self._health.status = "unavailable"
            self._health.available = False
            return self._health

        # Quick test request
        try:
            client = await self._get_client()
            test_payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
                "temperature": 0,
            }
            start = time.perf_counter()
            resp = await client.post("/chat/completions", json=test_payload)
            latency = (time.perf_counter() - start) * 1000

            if resp.status_code == 200:
                self._health.available = True
                self._health.status = "connected"
                self._health.last_success_at = time.time()
                self._health.average_latency_ms = (self._health.average_latency_ms * 0.9) + (latency * 0.1)
            elif resp.status_code == 429:
                self._health.status = "rate_limited"
                self._health.rate_limited = True
            else:
                self._health.status = "degraded"
                self._health.last_failure_at = time.time()
                self._health.last_error_code = str(resp.status_code)

        except Exception as e:
            self._health.available = False
            self._health.status = "unavailable"
            self._health.last_failure_at = time.time()
            self._health.last_error_code = type(e).__name__

        self._health.supports_streaming = True
        self._health.supports_tools = True
        self._health.supports_vision = False
        self._health.supports_json = True

        return self._health