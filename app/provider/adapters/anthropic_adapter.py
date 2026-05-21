"""Anthropic provider adapter"""
import json
import asyncio
from typing import AsyncGenerator

from app.provider.adapter import ProviderAdapter
from app.provider.models import ProviderModel
from app.provider.schemas import ConnectionTestResult
from app.infrastructure.llm.llm_client import llm_client

_DEFAULT_TEST_MODEL = "claude-3-5-haiku-20241022"


def _convert_messages_to_anthropic(messages: list[dict]) -> tuple[str, list[dict]]:
    """将 OpenAI 格式消息转为 Anthropic 格式，返回 (system_prompt, messages)"""
    system_prompt = ""
    converted = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            system_prompt = content or ""
            continue

        if role == "assistant":
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                # OpenAI assistant with tool_calls → Anthropic tool_use blocks
                blocks = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in tool_calls:
                    func = tc.get("function", {})
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": args,
                    })
                converted.append({"role": "assistant", "content": blocks})
                continue

            # Plain text assistant message
            if isinstance(content, list):
                # Already in Anthropic format (content blocks), pass through
                converted.append({"role": "assistant", "content": content})
            elif content:
                converted.append({"role": "assistant", "content": str(content)})
            continue

        if role == "tool":
            # OpenAI tool result → Anthropic user with tool_result block
            converted.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id", ""),
                    "content": str(content),
                }],
            })
            continue

        if role == "user":
            if isinstance(content, list):
                converted.append({"role": "user", "content": content})
            else:
                converted.append({"role": "user", "content": str(content)})
            continue

    return system_prompt, converted


def _convert_tools_to_anthropic(tools: list[dict]) -> list[dict]:
    """将 OpenAI function-calling 格式转为 Anthropic tool 格式"""
    converted = []
    for tool in tools:
        func = tool.get("function", {})
        converted.append({
            "name": func.get("name", tool.get("name", "")),
            "description": func.get("description", tool.get("description", "")),
            "input_schema": func.get("parameters", tool.get("input_schema", {})),
        })
    return converted


def _convert_anthropic_response_to_openai(response_body: dict) -> dict:
    """将 Anthropic Messages 响应转为 OpenAI chat/completions 格式"""
    stop_reason = response_body.get("stop_reason", "stop")
    content = response_body.get("content", [])

    text_parts = []
    tool_calls = []

    for block in content:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block.get("id", ""),
                "type": "function",
                "function": {
                    "name": block.get("name", ""),
                    "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                },
            })

    finish_reason = "tool_calls" if stop_reason == "tool_use" else "stop"
    return {
        "choices": [{
            "finish_reason": finish_reason,
            "message": {
                "role": "assistant",
                "content": "\n".join(text_parts) if text_parts else None,
                "tool_calls": tool_calls if tool_calls else None,
            },
        }],
    }


class AnthropicAdapter(ProviderAdapter):
    """处理 anthropic 类型，走 /messages 端点"""

    async def test_connection(self, provider: ProviderModel) -> ConnectionTestResult:
        base_url = provider.base_url.rstrip("/")
        extra_config = provider.extra_config or {}
        test_model = extra_config.get("test_model", _DEFAULT_TEST_MODEL)

        url = f"{base_url}/messages"
        headers = {
            "x-api-key": provider.api_key,
            "anthropic-version": extra_config.get("anthropic_version", "2023-06-01"),
            "content-type": "application/json",
        }
        body = {
            "model": test_model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        }
        return await self._do_test_post(provider, url, headers, body, timeout=10.0)

    async def stream_chat(
        self,
        provider: ProviderModel,
        model: str,
        messages: list[dict],
        agent_config: dict,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Anthropic 格式流式对话"""
        base_url = provider.base_url.rstrip("/")
        extra_config = provider.extra_config or {}
        url = f"{base_url}/messages"
        headers = {
            "x-api-key": provider.api_key,
            "anthropic-version": extra_config.get("anthropic_version", "2023-06-01"),
            "content-type": "application/json",
        }

        # 转换 OpenAI 格式消息到 Anthropic 格式
        system_message, anthropic_messages = _convert_messages_to_anthropic(messages)

        body = {
            "model": model,
            "messages": anthropic_messages,
            "stream": True,
            "max_tokens": agent_config.get("max_tokens", 2048),
        }
        if system_message:
            body["system"] = system_message
        if tools:
            body["tools"] = _convert_tools_to_anthropic(tools)

        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_sse_data(data_str: str) -> None:
            if data_str == "[DONE]":
                await queue.put(None)
                return
            try:
                data = json.loads(data_str)
                event_type = data.get("type")
                if event_type == "content_block_delta":
                    delta = data.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        await queue.put(text)
                elif event_type == "message_stop":
                    await queue.put(None)
            except json.JSONDecodeError:
                pass

        async def run_stream():
            try:
                await llm_client.stream(
                    url, headers, body, on_sse_data, timeout=120.0,
                    provider=provider.provider_type, model=model,
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_stream())

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def chat_complete(
        self,
        provider: ProviderModel,
        model: str,
        messages: list[dict],
        agent_config: dict,
        tools: list[dict] | None = None,
    ) -> dict:
        """Anthropic 格式非流式对话，返回完整响应"""
        base_url = provider.base_url.rstrip("/")
        extra_config = provider.extra_config or {}
        url = f"{base_url}/messages"
        headers = {
            "x-api-key": provider.api_key,
            "anthropic-version": extra_config.get("anthropic_version", "2023-06-01"),
            "content-type": "application/json",
        }

        # 转换 OpenAI 格式消息到 Anthropic 格式
        system_message, anthropic_messages = _convert_messages_to_anthropic(messages)

        body = {
            "model": model,
            "messages": anthropic_messages,
            "stream": False,
            "max_tokens": agent_config.get("max_tokens", 2048),
        }
        if system_message:
            body["system"] = system_message
        if tools:
            body["tools"] = _convert_tools_to_anthropic(tools)

        result = await llm_client.admin_post(
            url, headers, body, timeout=120.0,
            provider=provider.provider_type, model=model,
        )
        response_body = result.get("body", result)
        return _convert_anthropic_response_to_openai(response_body)
