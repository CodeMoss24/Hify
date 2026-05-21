"""熔断器与重试处理器（structlog 结构化事件）"""
import asyncio
import time
from enum import Enum
from typing import Any, Callable

import structlog

from app.infrastructure.llm.llm_api_exception import LlmApiException
from app.common.error_code import ErrorCode
from app.common.logging import (
    EVENT_CIRCUIT_STATE_CHANGE,
    EVENT_CIRCUIT_REJECTED,
    EVENT_RETRY,
    EVENT_RETRY_EXHAUSTED,
    LOG_KEY_FROM_STATE,
    LOG_KEY_TO_STATE,
    LOG_KEY_FAILURE_COUNT,
    LOG_KEY_PROVIDER,
    LOG_KEY_ATTEMPT,
    LOG_KEY_MAX_RETRIES,
    LOG_KEY_DELAY,
)
from app.common.metrics import circuit_breaker_state as cb_gauge

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """单 Provider 熔断器，按 base_url 隔离"""

    def __init__(
        self,
        provider_key: str,
        failure_threshold: int = 5,
        open_timeout: float = 30.0,
    ):
        self.provider_key = provider_key
        self.failure_threshold = failure_threshold
        self.open_timeout = open_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()
        cb_gauge.labels(provider=provider_key).set(0)

    async def can_execute(self) -> bool:
        """检查是否允许执行请求"""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if self._last_failure_time is None:
                    return False
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.open_timeout:
                    logger.info(
                        EVENT_CIRCUIT_STATE_CHANGE,
                        **{
                            LOG_KEY_PROVIDER: self.provider_key,
                            LOG_KEY_FROM_STATE: CircuitState.OPEN.value,
                            LOG_KEY_TO_STATE: CircuitState.HALF_OPEN.value,
                        },
                    )
                    self._state = CircuitState.HALF_OPEN
                    cb_gauge.labels(provider=self.provider_key).set(2)
                    return True
                return False
            return True

    async def record_success(self) -> None:
        """记录成功，关闭熔断器"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    EVENT_CIRCUIT_STATE_CHANGE,
                    **{
                        LOG_KEY_PROVIDER: self.provider_key,
                        LOG_KEY_FROM_STATE: CircuitState.HALF_OPEN.value,
                        LOG_KEY_TO_STATE: CircuitState.CLOSED.value,
                        LOG_KEY_FAILURE_COUNT: self._failure_count,
                    },
                )
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            cb_gauge.labels(provider=self.provider_key).set(0)

    async def record_failure(self) -> None:
        """记录失败，触发熔断"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    EVENT_CIRCUIT_STATE_CHANGE,
                    **{
                        LOG_KEY_PROVIDER: self.provider_key,
                        LOG_KEY_FROM_STATE: CircuitState.HALF_OPEN.value,
                        LOG_KEY_TO_STATE: CircuitState.OPEN.value,
                        LOG_KEY_FAILURE_COUNT: self._failure_count,
                    },
                )
                self._state = CircuitState.OPEN
                cb_gauge.labels(provider=self.provider_key).set(1)
            elif self._failure_count >= self.failure_threshold:
                logger.warning(
                    EVENT_CIRCUIT_STATE_CHANGE,
                    **{
                        LOG_KEY_PROVIDER: self.provider_key,
                        LOG_KEY_FROM_STATE: CircuitState.CLOSED.value,
                        LOG_KEY_TO_STATE: CircuitState.OPEN.value,
                        LOG_KEY_FAILURE_COUNT: self._failure_count,
                    },
                )
                self._state = CircuitState.OPEN
                cb_gauge.labels(provider=self.provider_key).set(1)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count


class RetryHandler:
    """指数退避重试处理器"""

    RETRY_DELAYS = [1.0, 2.0, 4.0]
    MAX_DELAY = 30.0

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def should_retry(self, exc: LlmApiException) -> bool:
        code = exc.error_code
        return code in (
            ErrorCode.LLM_TIMEOUT,
            ErrorCode.LLM_RATE_LIMITED,
            ErrorCode.LLM_SERVER_ERROR,
        )

    def get_retry_delay(self, attempt: int) -> float:
        if attempt >= len(self.RETRY_DELAYS):
            return self.MAX_DELAY
        return self.RETRY_DELAYS[attempt]

    async def execute_with_retry(
        self,
        coro_factory,
        is_retryable: Callable[[LlmApiException], bool],
    ) -> Any:
        attempt = 0
        last_exc = None

        while True:
            try:
                return await coro_factory()
            except LlmApiException as e:
                last_exc = e
                if not is_retryable(e):
                    logger.warning(
                        "retry.non_retryable",
                        error_code=e.error_code.code if e.error_code else None,
                        error_message=e.message,
                    )
                    raise
                if attempt >= self.max_retries:
                    logger.warning(
                        EVENT_RETRY_EXHAUSTED,
                        **{
                            LOG_KEY_ATTEMPT: attempt,
                            LOG_KEY_MAX_RETRIES: self.max_retries,
                        },
                    )
                    raise
                delay = self.get_retry_delay(attempt)
                logger.warning(
                    EVENT_RETRY,
                    **{
                        LOG_KEY_ATTEMPT: attempt + 1,
                        LOG_KEY_MAX_RETRIES: self.max_retries,
                        LOG_KEY_DELAY: delay,
                    },
                )
                await asyncio.sleep(delay)
                attempt += 1
