"""并发控制模块：LLM 调用和后台异步任务的并发控制"""
import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar

from app.common.config import (
    LLM_CHAT_CONCURRENCY,
    LLM_CONNECT_TIMEOUT,
    LLM_TIMEOUT,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class LlmExecutor:
    """LLM 调用并发控制器

    - 全局信号量限制并发数为 LLM_CHAT_CONCURRENCY
    - 同步调用封装为异步，通过 asyncio.to_thread 避免阻塞事件循环
    - 记录耗时和异常到日志
    """

    def __init__(
        self,
        concurrency: int | None = None,
        timeout: float | None = None,
    ):
        self._semaphore = asyncio.Semaphore(concurrency or LLM_CHAT_CONCURRENCY)
        self._timeout = timeout or LLM_TIMEOUT

    async def run(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """在信号量控制下执行同步阻塞调用，保护事件循环不阻塞"""
        start = time.monotonic()
        async with self._semaphore:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(fn, *args, **kwargs),
                    timeout=self._timeout,
                )
                elapsed = time.monotonic() - start
                logger.info(f"[LlmExecutor] call succeeded in {elapsed:.2f}s")
                return result
            except asyncio.TimeoutError:
                elapsed = time.monotonic() - start
                logger.error(f"[LlmExecutor] call timeout after {elapsed:.2f}s")
                raise
            except Exception as e:
                elapsed = time.monotonic() - start
                logger.error(f"[LlmExecutor] call failed after {elapsed:.2f}s: {e}")
                raise


class AsyncExecutor:
    """后台异步任务执行器

    - 信号量限制并发数为 BACKGROUND_CONCURRENCY
    - submit() 将任务提交到后台执行，不阻塞主流程
    - 任务在共享事件循环中以协程方式运行
    """

    def __init__(self, concurrency: int | None = None):
        self._semaphore = asyncio.Semaphore(concurrency or 5)

    async def submit(
        self, fn: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any
    ) -> asyncio.Task[T]:
        """将协程任务提交到后台执行，返回 Task 对象"""
        async def _wrapped() -> T:
            async with self._semaphore:
                return await fn(*args, **kwargs)

        task = asyncio.create_task(_wrapped())
        logger.info(f"[AsyncExecutor] task submitted: {task.get_name()}")
        return task


# 模块级单例，外部直接导入使用
llm_executor = LlmExecutor()
async_executor = AsyncExecutor()
