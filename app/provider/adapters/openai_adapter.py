"""OpenAI / OpenAI Compatible provider adapter"""
import json
import logging
import asyncio
from typing import AsyncGenerator

from app.provider.adapter import ProviderAdapter
from app.provider.models import ProviderModel
from app.provider.schemas import ConnectionTestResult
from app.infrastructure.llm.llm_client import llm_client

_DEFAULT_TEST_MODEL = "gpt-4o-mini"
logger = logging.getLogger(__name__)


class OpenAiAdapter(ProviderAdapter):
    """处理 openai 和 openai_compatible 两种类型，共用 chat/completions 逻辑"""

    async def test_connection(self, provider: ProviderModel) -> ConnectionTestResult:
        base_url = provider.base_url.rstrip("/")
        extra_config = provider.extra_config or {}
        test_model = extra_config.get("test_model", _DEFAULT_TEST_MODEL)

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
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
        """OpenAI 格式流式对话"""
        base_url = provider.base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "content-type": "application/json",
        }

        body = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": agent_config.get("temperature", 0.7),
            "max_tokens": agent_config.get("max_tokens", 2048),
        }
        if tools:
            body["tools"] = tools

        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_sse_data(data_str: str) -> None:
            if data_str == "[DONE]":
                await queue.put(None)
                return
            try:
                data = json.loads(data_str)
                choices = data.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        await queue.put(content)
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
        """OpenAI 格式非流式对话，返回完整响应"""
        base_url = provider.base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": agent_config.get("temperature", 0.7),
            "max_tokens": agent_config.get("max_tokens", 2048),
        }
        if tools:
            body["tools"] = tools

        result = await llm_client.admin_post(
            url, headers, body, timeout=30.0,
            provider=provider.provider_type, model=model,
        )
        return result.get("body", result)
