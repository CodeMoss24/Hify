"""Ollama provider adapter"""
import json
import asyncio
from typing import AsyncGenerator

from app.provider.adapter import ProviderAdapter
from app.provider.models import ProviderModel
from app.provider.schemas import ConnectionTestResult
from app.infrastructure.llm.llm_client import llm_client


class OllamaAdapter(ProviderAdapter):
    """处理 ollama 类型，走原生 GET /api/tags 端点"""

    async def test_connection(self, provider: ProviderModel) -> ConnectionTestResult:
        base_url = provider.base_url.rstrip("/")
        url = f"{base_url}/api/tags"
        headers = {}
        return await self._do_test_get(provider, url, headers, timeout=10.0)

    async def stream_chat(
        self,
        provider: ProviderModel,
        model: str,
        messages: list[dict],
        agent_config: dict,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Ollama 格式流式对话"""
        base_url = provider.base_url.rstrip("/")
        url = f"{base_url}/api/chat"
        headers = {
            "content-type": "application/json",
        }

        body = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": agent_config.get("temperature", 0.7),
                "num_predict": agent_config.get("max_tokens", 2048),
            },
        }
        if tools:
            body["tools"] = tools

        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_sse_data(data_str: str) -> None:
            try:
                data = json.loads(data_str)
                message = data.get("message", {})
                content = message.get("content", "")
                if content:
                    await queue.put(content)
                if data.get("done"):
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
        """Ollama 格式非流式对话，返回完整响应"""
        base_url = provider.base_url.rstrip("/")
        url = f"{base_url}/api/chat"
        headers = {
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": agent_config.get("temperature", 0.7),
                "num_predict": agent_config.get("max_tokens", 2048),
            },
        }
        if tools:
            body["tools"] = tools

        result = await llm_client.admin_post(
            url, headers, body, timeout=30.0,
            provider=provider.provider_type, model=model,
        )
        return result.get("body", result)
