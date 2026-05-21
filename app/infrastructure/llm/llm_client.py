"""统一 LLM HTTP 客户端，封装 OpenAI/Claude/Gemini/Ollama 等外部 API 调用（structlog 结构化日志）"""
import asyncio
import time
from typing import Any, Callable, Awaitable

import httpx
import aiohttp
import structlog

from app.infrastructure.llm.circuit_breaker import CircuitBreaker, RetryHandler
from app.infrastructure.llm.llm_api_exception import LlmApiException
from app.common.error_code import ErrorCode
from app.common import config
from app.common.logging import (
    EVENT_LLM_CALL_START,
    EVENT_LLM_CALL_END,
    EVENT_LLM_STREAM_START,
    EVENT_LLM_STREAM_END,
    EVENT_CIRCUIT_REJECTED,
    LOG_KEY_PROVIDER,
    LOG_KEY_MODEL,
    LOG_KEY_ACTION,
    LOG_KEY_METHOD,
    LOG_KEY_URL,
    LOG_KEY_LATENCY_MS,
    LOG_KEY_STATUS_CODE,
    LOG_KEY_ERROR_CODE,
)
from app.common.metrics import (
    llm_calls_total,
    llm_call_duration_seconds,
)

logger = structlog.get_logger(__name__)


def _log_context(
    provider: str | None = None,
    model: str | None = None,
    **extra,
) -> dict[str, Any]:
    """构建日志的共享上下文字段，过滤 None 值"""
    ctx: dict[str, Any] = {}
    if provider:
        ctx[LOG_KEY_PROVIDER] = provider
    if model:
        ctx[LOG_KEY_MODEL] = model
    ctx.update(extra)
    return ctx


class LlmClient:
    """统一 LLM HTTP 客户端，支持普通请求和 SSE 流式请求，带熔断和重试"""

    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None
        self._aio_session: aiohttp.ClientSession | None = None
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._retry_handler = RetryHandler()

    def _get_breaker(self, base_url: str) -> CircuitBreaker:
        if base_url not in self._circuit_breakers:
            self._circuit_breakers[base_url] = CircuitBreaker(provider_key=base_url)
        return self._circuit_breakers[base_url]

    async def _ensure_http(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=120.0,
                    write=5.0,
                    pool=5.0,
                )
            )
        return self._http_client

    async def _ensure_aiohttp(self) -> aiohttp.ClientSession:
        if self._aio_session is None:
            connector = aiohttp.TCPConnector(limit=0)
            self._aio_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(
                    total=None,
                    connect=5.0,
                    sock_read=0,
                ),
            )
        return self._aio_session

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._aio_session:
            await self._aio_session.close()
            self._aio_session = None

    def _extract_base_url(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    # ── 普通 POST ──────────────────────────────────────────

    async def _do_post(
        self,
        url: str,
        headers: dict,
        body: dict,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        client = await self._ensure_http()
        start = time.monotonic()
        try:
            response = await client.post(url, headers=headers, json=body)
            elapsed = time.monotonic() - start
            latency_ms = int(elapsed * 1000)
            logger.info(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{
                        LOG_KEY_METHOD: "post",
                        LOG_KEY_URL: url,
                        LOG_KEY_STATUS_CODE: response.status_code,
                        LOG_KEY_LATENCY_MS: latency_ms,
                    },
                ),
            )
            self._raise_on_status(response.status_code, response.text)
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="post", status="success",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="post",
            ).observe(elapsed)
            return response.json()
        except LlmApiException:
            elapsed = time.monotonic() - start
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="post", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="post",
            ).observe(elapsed)
            raise
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start
            logger.warning(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{
                        LOG_KEY_METHOD: "post",
                        LOG_KEY_URL: url,
                        LOG_KEY_LATENCY_MS: int(elapsed * 1000),
                        LOG_KEY_STATUS_CODE: "timeout",
                        LOG_KEY_ERROR_CODE: ErrorCode.LLM_TIMEOUT.code,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="post", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="post",
            ).observe(elapsed)
            raise LlmApiException(
                ErrorCode.LLM_TIMEOUT,
                message=f"LLM API timeout after {elapsed:.2f}s",
                cause=e,
            )
        except httpx.HTTPStatusError as e:
            self._raise_by_status(e.response.status_code, e.response.text, e)
            raise
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{
                        LOG_KEY_METHOD: "post",
                        LOG_KEY_URL: url,
                        LOG_KEY_LATENCY_MS: int(elapsed * 1000),
                        LOG_KEY_ERROR_CODE: ErrorCode.LLM_SERVER_ERROR.code,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="post", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="post",
            ).observe(elapsed)
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"LLM API request failed: {e}",
                cause=e,
            )

    async def post(
        self,
        url: str,
        headers: dict,
        body: dict,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        base_url = self._extract_base_url(url)
        breaker = self._get_breaker(base_url)

        logger.info(
            EVENT_LLM_CALL_START,
            **_log_context(
                provider=provider,
                model=model,
                **{
                    LOG_KEY_METHOD: "post",
                    LOG_KEY_URL: url,
                },
            ),
        )

        if not await breaker.can_execute():
            logger.warning(
                EVENT_CIRCUIT_REJECTED,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{LOG_KEY_URL: url},
                ),
            )
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"Circuit open for {base_url}",
            )

        async def _exec():
            return await self._do_post(url, headers, body, provider=provider, model=model)

        try:
            result = await self._retry_handler.execute_with_retry(
                _exec,
                is_retryable=self._retry_handler.should_retry,
            )
            await breaker.record_success()
            return result
        except LlmApiException as e:
            if e.error_code not in (ErrorCode.LLM_AUTH_FAILED,):
                await breaker.record_failure()
            raise

    # ── SSE 流式请求 ────────────────────────────────────────

    async def _do_stream(
        self,
        url: str,
        headers: dict,
        body: dict,
        callback: Callable[[str], Awaitable[None]],
        timeout: float = 120.0,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        session = await self._ensure_aiohttp()
        start = time.monotonic()

        async def _do_request():
            nonlocal session
            async with session.post(url, headers=headers, json=body) as response:
                elapsed = time.monotonic() - start
                latency_ms = int(elapsed * 1000)
                logger.info(
                    EVENT_LLM_STREAM_END,
                    **_log_context(
                        provider=provider,
                        model=model,
                        **{
                            LOG_KEY_URL: url,
                            LOG_KEY_STATUS_CODE: response.status,
                            LOG_KEY_LATENCY_MS: latency_ms,
                        },
                    ),
                )
                self._raise_by_status(response.status, "", None)
                async for line in response.content:
                    decoded = line.decode("utf-8").strip()
                    if decoded.startswith("data:"):
                        await callback(decoded[5:].strip())
                stream_elapsed = time.monotonic() - start
                llm_calls_total.labels(
                    provider=provider or "", model=model or "", method="stream", status="success",
                ).inc()
                llm_call_duration_seconds.labels(
                    provider=provider or "", model=model or "", method="stream",
                ).observe(stream_elapsed)

        try:
            await asyncio.wait_for(_do_request(), timeout=timeout)
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            logger.warning(
                EVENT_LLM_STREAM_END,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{
                        LOG_KEY_URL: url,
                        LOG_KEY_LATENCY_MS: int(elapsed * 1000),
                        LOG_KEY_STATUS_CODE: "timeout",
                        LOG_KEY_ERROR_CODE: ErrorCode.LLM_TIMEOUT.code,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="stream", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="stream",
            ).observe(elapsed)
            raise LlmApiException(
                ErrorCode.LLM_TIMEOUT,
                message=f"LLM stream timeout after {elapsed:.2f}s",
            )
        except LlmApiException:
            elapsed = time.monotonic() - start
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="stream", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="stream",
            ).observe(elapsed)
            raise

    async def stream(
        self,
        url: str,
        headers: dict,
        body: dict,
        callback: Callable[[str], Awaitable[None]],
        timeout: float = 120.0,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        base_url = self._extract_base_url(url)
        breaker = self._get_breaker(base_url)

        logger.info(
            EVENT_LLM_STREAM_START,
            **_log_context(
                provider=provider,
                model=model,
                **{
                    LOG_KEY_METHOD: "stream",
                    LOG_KEY_URL: url,
                },
            ),
        )

        if not await breaker.can_execute():
            logger.warning(
                EVENT_CIRCUIT_REJECTED,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{LOG_KEY_URL: url},
                ),
            )
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"Circuit open for {base_url}",
            )

        try:
            await self._do_stream(
                url, headers, body, callback, timeout,
                provider=provider, model=model,
            )
            await breaker.record_success()
        except LlmApiException as e:
            if e.error_code not in (ErrorCode.LLM_AUTH_FAILED,):
                await breaker.record_failure()
            raise

    # ── 管理 / 连通性测试 GET ───────────────────────────────

    async def _do_get(
        self,
        url: str,
        headers: dict,
        timeout: float = 10.0,
        provider: str | None = None,
    ) -> dict:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=timeout, write=5.0, pool=5.0)
            ) as client:
                response = await client.get(url, headers=headers)
            elapsed = time.monotonic() - start
            latency_ms = int(elapsed * 1000)
            logger.info(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    **{
                        LOG_KEY_METHOD: "admin_get",
                        LOG_KEY_URL: url,
                        LOG_KEY_STATUS_CODE: response.status_code,
                        LOG_KEY_LATENCY_MS: latency_ms,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model="", method="admin_get", status="success",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model="", method="admin_get",
            ).observe(elapsed)
            return {"status_code": response.status_code, "body": response.json()}
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start
            logger.warning(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    **{
                        LOG_KEY_METHOD: "admin_get",
                        LOG_KEY_URL: url,
                        LOG_KEY_LATENCY_MS: int(elapsed * 1000),
                        LOG_KEY_STATUS_CODE: "timeout",
                        LOG_KEY_ERROR_CODE: ErrorCode.LLM_TIMEOUT.code,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model="", method="admin_get", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model="", method="admin_get",
            ).observe(elapsed)
            raise LlmApiException(
                ErrorCode.LLM_TIMEOUT,
                message=f"LLM API timeout after {elapsed:.2f}s",
                cause=e,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    **{
                        LOG_KEY_METHOD: "admin_get",
                        LOG_KEY_URL: url,
                        LOG_KEY_LATENCY_MS: int(elapsed * 1000),
                        LOG_KEY_ERROR_CODE: ErrorCode.LLM_SERVER_ERROR.code,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model="", method="admin_get", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model="", method="admin_get",
            ).observe(elapsed)
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"LLM API request failed: {e}",
                cause=e,
            )

    async def admin_get(
        self,
        url: str,
        headers: dict,
        timeout: float = 10.0,
        provider: str | None = None,
    ) -> dict:
        return await self._do_get(url, headers, timeout, provider=provider)

    # ── 管理 / 连通性测试 POST ──────────────────────────────

    async def _do_admin_post(
        self,
        url: str,
        headers: dict,
        body: dict,
        timeout: float = 10.0,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=timeout, write=5.0, pool=5.0)
            ) as client:
                response = await client.post(url, headers=headers, json=body)
            elapsed = time.monotonic() - start
            latency_ms = int(elapsed * 1000)
            logger.info(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{
                        LOG_KEY_METHOD: "admin_post",
                        LOG_KEY_URL: url,
                        LOG_KEY_STATUS_CODE: response.status_code,
                        LOG_KEY_LATENCY_MS: latency_ms,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="admin_post", status="success",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="admin_post",
            ).observe(elapsed)
            return {"status_code": response.status_code, "body": response.json()}
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start
            logger.warning(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{
                        LOG_KEY_METHOD: "admin_post",
                        LOG_KEY_URL: url,
                        LOG_KEY_LATENCY_MS: int(elapsed * 1000),
                        LOG_KEY_STATUS_CODE: "timeout",
                        LOG_KEY_ERROR_CODE: ErrorCode.LLM_TIMEOUT.code,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="admin_post", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="admin_post",
            ).observe(elapsed)
            raise LlmApiException(
                ErrorCode.LLM_TIMEOUT,
                message=f"LLM API timeout after {elapsed:.2f}s",
                cause=e,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(
                EVENT_LLM_CALL_END,
                **_log_context(
                    provider=provider,
                    model=model,
                    **{
                        LOG_KEY_METHOD: "admin_post",
                        LOG_KEY_URL: url,
                        LOG_KEY_LATENCY_MS: int(elapsed * 1000),
                        LOG_KEY_ERROR_CODE: ErrorCode.LLM_SERVER_ERROR.code,
                    },
                ),
            )
            llm_calls_total.labels(
                provider=provider or "", model=model or "", method="admin_post", status="fail",
            ).inc()
            llm_call_duration_seconds.labels(
                provider=provider or "", model=model or "", method="admin_post",
            ).observe(elapsed)
            raise LlmApiException(
                ErrorCode.LLM_SERVER_ERROR,
                message=f"LLM API request failed: {e}",
                cause=e,
            )

    async def admin_post(
        self,
        url: str,
        headers: dict,
        body: dict,
        timeout: float = 10.0,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        logger.info(
            EVENT_LLM_CALL_START,
            **_log_context(
                provider=provider,
                model=model,
                **{
                    LOG_KEY_METHOD: "admin_post",
                    LOG_KEY_URL: url,
                },
            ),
        )
        return await self._do_admin_post(
            url, headers, body, timeout, provider=provider, model=model
        )

    # ── Embedding ───────────────────────────────────────────

    async def embed(
        self,
        texts: list[str],
        provider: str | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        base_url = config.ARK_EMBEDDING_BASE_URL.rstrip("/")
        api_key = config.ARK_EMBEDDING_API_KEY
        model = config.ARK_EMBEDDING_MODEL
        batch_size = config.ARK_EMBEDDING_BATCH_SIZE

        if not api_key:
            logger.error(
                "embed.failed",
                error_code=ErrorCode.LLM_AUTH_FAILED.code,
                error_message="ARK_EMBEDDING_API_KEY is not configured",
            )
            raise LlmApiException(
                ErrorCode.LLM_AUTH_FAILED,
                message="ARK_EMBEDDING_API_KEY is not configured",
            )

        provider_name = provider or "ark"
        url = f"{base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size

            body = {
                "model": model,
                "input": batch,
                "dimensions": config.ARK_EMBEDDING_DIMENSION,
            }

            try:
                result = await self.post(
                    url, headers, body,
                    provider=provider_name, model=model,
                )
                data = result.get("data", [])
                data_sorted = sorted(data, key=lambda x: x.get("index", 0))
                batch_embeddings = [item.get("embedding", []) for item in data_sorted]

                for emb in batch_embeddings:
                    if len(emb) != config.ARK_EMBEDDING_DIMENSION:
                        logger.warning(
                            "embed.dimension_mismatch",
                            actual=len(emb),
                            expected=config.ARK_EMBEDDING_DIMENSION,
                        )

                all_embeddings.extend(batch_embeddings)

            except Exception:
                logger.error(
                    "embed.batch_failed",
                    batch=batch_num,
                    total_batches=total_batches,
                )
                raise

        logger.info(
            "embed.completed",
            embedding_count=len(all_embeddings),
            text_count=len(texts),
        )
        return all_embeddings

    # ── HTTP 状态码 → 异常映射 ──────────────────────────────

    def _raise_on_status(self, status_code: int, response_text: str) -> None:
        if status_code == 200:
            return
        self._raise_by_status(status_code, response_text, None)

    def _raise_by_status(
        self, status_code: int, response_text: str, cause: Exception | None
    ) -> None:
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


llm_client = LlmClient()
