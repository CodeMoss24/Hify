"""统一 LLM HTTP 客户端，封装 OpenAI/Claude/Gemini/Ollama 等外部 API 调用"""
import asyncio
import logging
import time
from typing import Any, Callable, Awaitable

import httpx
import aiohttp

from app.infrastructure.llm.circuit_breaker import CircuitBreaker, RetryHandler
from app.infrastructure.llm.llm_api_exception import LlmApiException
from app.common.error_code import ErrorCode

logger = logging.getLogger(__name__)


class LlmClient:
    """统一 LLM HTTP 客户端，支持普通请求和 SSE 流式请求，带熔断和重试"""

    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None
        self._aio_session: aiohttp.ClientSession | None = None
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._retry_handler = RetryHandler()

    def _get_breaker(self, base_url: str) -> CircuitBreaker:
        """获取或创建指定 Provider 的熔断器"""
        if base_url not in self._circuit_breakers:
            self._circuit_breakers[base_url] = CircuitBreaker(provider_key=base_url)
        return self._circuit_breakers[base_url]

    async def _ensure_http(self) -> httpx.AsyncClient:
        """懒初始化 httpx 普通会话"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=120.0,
                )
            )
        return self._http_client

    async def _ensure_aiohttp(self) -> aiohttp.ClientSession:
        """懒初始化 aiohttp SSE 会话"""
        if self._aio_session is None:
            connector = aiohttp.TCPConnector(limit=0)
            self._aio_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(
                    total=None,
                    connect=5.0,
                    sock_read=0,  # 流式响应无读超时
                ),
            )
        return self._aio_session

    async def close(self) -> None:
        """关闭所有会话"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._aio_session:
            await self._aio_session.close()
            self._aio_session = None

    async def _do_post(self, url: str, headers: dict, body: dict) -> dict:
        """实际执行 POST 请求（内部方法，由重试+熔断包装）"""
        client = await self._ensure_http()
        start = time.monotonic()
        try:
            response = await client.post(url, headers=headers, json=body)
            elapsed = time.monotonic() - start
            logger.info(
                f"LLM POST {url} -> {response.status_code} ({elapsed:.2f}s)"
            )
            self._raise_on_status(response.status_code, response.text)
            return response.json()
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start
            logger.warning(f"LLM POST {url} TIMEOUT after {elapsed:.2f}s")
            raise LlmApiException(
                ErrorCode.LLM_TIMEOUT,
                message=f"LLM API timeout after {elapsed:.2f}s",
                cause=e,
            )
        except httpx.HTTPStatusError as e:
            self._raise_by_status(e.response.status_code, e.response.text, e)
            raise  # unreachable
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(f"LLM POST {url} ERROR after {elapsed:.2f}s: {e}")
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"LLM API request failed: {e}",
                cause=e,
            )

    def _extract_base_url(self, url: str) -> str:
        """从 URL 中提取 base_url 用于熔断器 key（如 https://api.openai.com/v1 → https://api.openai.com）"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    async def post(self, url: str, headers: dict, body: dict) -> dict:
        """普通 POST 请求，返回解析后的 JSON 数据（带熔断和重试）"""
        base_url = self._extract_base_url(url)
        breaker = self._get_breaker(base_url)

        # 检查熔断器状态
        if not await breaker.can_execute():
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"Circuit open for {base_url}",
            )

        async def _exec():
            return await self._do_post(url, headers, body)

        try:
            result = await self._retry_handler.execute_with_retry(
                _exec(),
                is_retryable=self._retry_handler.should_retry,
            )
            await breaker.record_success()
            return result
        except LlmApiException as e:
            # 401/403 不触发熔断
            if e.error_code not in (ErrorCode.LLM_AUTH_FAILED,):
                await breaker.record_failure()
            raise

    async def _do_stream(
        self,
        url: str,
        headers: dict,
        body: dict,
        callback: Callable[[str], Awaitable[None]],
        timeout: float = 120.0,
    ) -> None:
        """实际执行 SSE 流式请求（内部方法，由重试+熔断包装）"""
        session = await self._ensure_aiohttp()
        start = time.monotonic()

        async def _do_request():
            nonlocal session
            async with session.post(url, headers=headers, json=body) as response:
                elapsed = time.monotonic() - start
                logger.info(
                    f"LLM stream {url} -> {response.status} ({elapsed:.2f}s)"
                )
                self._raise_by_status(response.status, "", None)
                async for line in response.content:
                    decoded = line.decode("utf-8").strip()
                    if decoded.startswith("data:"):
                        await callback(decoded[5:].strip())

        try:
            await asyncio.wait_for(_do_request(), timeout=timeout)
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            logger.warning(f"LLM stream {url} TIMEOUT after {elapsed:.2f}s")
            raise LlmApiException(
                ErrorCode.LLM_TIMEOUT,
                message=f"LLM stream timeout after {elapsed:.2f}s",
            )

    async def stream(
        self,
        url: str,
        headers: dict,
        body: dict,
        callback: Callable[[str], Awaitable[None]],
        timeout: float = 120.0,
    ) -> None:
        """SSE 流式请求，逐行读取 data: 开头的 SSE 事件，触发 callback（带熔断和重试）"""
        base_url = self._extract_base_url(url)
        breaker = self._get_breaker(base_url)

        # 检查熔断器状态
        if not await breaker.can_execute():
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"Circuit open for {base_url}",
            )

        try:
            await self._retry_handler.execute_with_retry(
                self._do_stream(url, headers, body, callback, timeout),
                is_retryable=self._retry_handler.should_retry,
            )
            await breaker.record_success()
        except LlmApiException as e:
            # 401/403 不触发熔断
            if e.error_code not in (ErrorCode.LLM_AUTH_FAILED,):
                await breaker.record_failure()
            raise

    async def _do_get(self, url: str, headers: dict, timeout: float = 10.0) -> dict:
        """实际执行 GET 请求（管理/连通性测试，不走熔断和重试）"""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=timeout, write=5.0, pool=5.0)
            ) as client:
                response = await client.get(url, headers=headers)
            elapsed = time.monotonic() - start
            logger.info(
                f"LLM GET {url} -> {response.status_code} ({elapsed:.2f}s)"
            )
            return {"status_code": response.status_code, "body": response.json()}
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start
            logger.warning(f"LLM GET {url} TIMEOUT after {elapsed:.2f}s")
            raise LlmApiException(
                ErrorCode.LLM_TIMEOUT,
                message=f"LLM API timeout after {elapsed:.2f}s",
                cause=e,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(f"LLM GET {url} ERROR after {elapsed:.2f}s: {e}")
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"LLM API request failed: {e}",
                cause=e,
            )

    async def admin_get(self, url: str, headers: dict, timeout: float = 10.0) -> dict:
        """管理/连通性测试 GET 请求，不走熔断和重试，超时默认 10s"""
        return await self._do_get(url, headers, timeout)

    async def _do_admin_post(self, url: str, headers: dict, body: dict, timeout: float = 10.0) -> dict:
        """实际执行 POST 请求（管理/连通性测试，不走熔断和重试）"""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=timeout, write=5.0, pool=5.0)
            ) as client:
                response = await client.post(url, headers=headers, json=body)
            elapsed = time.monotonic() - start
            logger.info(
                f"LLM POST {url} -> {response.status_code} ({elapsed:.2f}s)"
            )
            return {"status_code": response.status_code, "body": response.json()}
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start
            logger.warning(f"LLM POST {url} TIMEOUT after {elapsed:.2f}s")
            raise LlmApiException(
                ErrorCode.LLM_TIMEOUT,
                message=f"LLM API timeout after {elapsed:.2f}s",
                cause=e,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(f"LLM POST {url} ERROR after {elapsed:.2f}s: {e}")
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"LLM API request failed: {e}",
                cause=e,
            )

    async def admin_post(self, url: str, headers: dict, body: dict, timeout: float = 10.0) -> dict:
        """管理/连通性测试 POST 请求，不走熔断和重试，超时默认 10s"""
        return await self._do_admin_post(url, headers, body, timeout)

    def _raise_on_status(self, status_code: int, response_text: str) -> None:
        """根据 HTTP 状态码抛对应异常"""
        if status_code == 200:
            return
        # 触发 _raise_by_status 的统一逻辑
        self._raise_by_status(status_code, response_text, None)

    def _raise_by_status(
        self, status_code: int, response_text: str, cause: Exception | None
    ) -> None:
        """根据 HTTP 状态码映射到具体错误类型"""
        if status_code == 401:
            raise LlmApiException(
                ErrorCode.LLM_AUTH_FAILED,
                message="LLM API auth failed (401)",
                cause=cause,
            )
        elif status_code == 403:
            raise LlmApiException(
                ErrorCode.LLM_AUTH_FAILED,
                message="LLM API forbidden (403)",
                cause=cause,
            )
        elif status_code == 429:
            raise LlmApiException(
                ErrorCode.LLM_RATE_LIMITED,
                message="LLM API rate limited (429)",
                cause=cause,
            )
        elif status_code >= 500:
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"LLM API server error ({status_code})",
                cause=cause,
            )
        elif status_code != 200:
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"LLM API unexpected status {status_code}",
                cause=cause,
            )


# 模块级单例
llm_client = LlmClient()