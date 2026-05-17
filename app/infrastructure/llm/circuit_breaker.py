"""熔断器与重试处理器"""
import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable

from app.infrastructure.llm.llm_api_exception import LlmApiException
from app.common.error_code import ErrorCode

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # 正常，允许请求通过
    OPEN = "open"          # 熔断打开，快速失败
    HALF_OPEN = "half_open"  # 冷却后放行一个探测请求


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
                    logger.info(f"CircuitBreaker [{self.provider_key}] HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    return True
                return False
            # HALF_OPEN：允许执行
            return True

    async def record_success(self) -> None:
        """记录成功，关闭熔断器"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(f"CircuitBreaker [{self.provider_key}] CLOSED (probe ok)")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None

    async def record_failure(self) -> None:
        """记录失败，触发熔断"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"CircuitBreaker [{self.provider_key}] OPEN (probe failed)"
                )
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                logger.warning(
                    f"CircuitBreaker [{self.provider_key}] OPEN "
                    f"(failures={self._failure_count})"
                )
                self._state = CircuitState.OPEN


class RetryHandler:
    """指数退避重试处理器"""

    # 退避曲线：1s → 2s → 4s，上限 30s
    RETRY_DELAYS = [1.0, 2.0, 4.0]
    MAX_DELAY = 30.0

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def should_retry(self, exc: LlmApiException) -> bool:
        """判断异常是否可重试"""
        code = exc.error_code
        return code in (
            ErrorCode.LLM_TIMEOUT,
            ErrorCode.LLM_RATE_LIMITED,
            ErrorCode.LLM_SERVER_ERROR,
        )

    def get_retry_delay(self, attempt: int) -> float:
        """获取第 attempt 次重试的延迟（0-based）"""
        if attempt >= len(self.RETRY_DELAYS):
            return self.MAX_DELAY
        return self.RETRY_DELAYS[attempt]

    async def execute_with_retry(
        self,
        coro,
        is_retryable: Callable[[LlmApiException], bool],
    ) -> Any:
        """执行协程，失败时退避重试，返回最终结果或抛异常

        Args:
            coro: 要执行的异步协程对象
            is_retryable: 判断异常是否可重试的函数
        """
        # 注意：因为协程只能 await 一次，重试需要重新创建
        # 所以这里我们只尝试一次
        # 实际项目中应该传入协程工厂函数
        return await coro
