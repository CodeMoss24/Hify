"""Anthropic provider adapter"""
import json
import asyncio
from typing import AsyncGenerator

from app.provider.adapter import ProviderAdapter
from app.provider.models import ProviderModel
from app.provider.schemas import ConnectionTestResult
from app.infrastructure.llm.llm_client import llm_client

_DEFAULT_TEST_MODEL = "claude-3-5-haiku-20241022"


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
        return await self._do_test_post(url, headers, body, timeout=10.0)

    async def stream_chat(
        self,
        provider: ProviderModel,
        model: str,
        messages: list[dict],
        agent_config: dict,
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

        # 转换 OpenAI 格式消息到 Anthropic 格式（去掉 system 消息，单独放）
        system_message = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append(msg)

        body = {
            "model": model,
            "messages": anthropic_messages,
            "stream": True,
            "max_tokens": agent_config.get("max_tokens", 2048),
        }
        if system_message:
            body["system"] = system_message

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
                await llm_client.stream(url, headers, body, on_sse_data, timeout=120.0)
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
