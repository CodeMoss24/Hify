"""测试 RetryHandler — 异步重试处理器

学习目标：怎么测异步重试逻辑
- 用 AsyncMock 模拟「有时成功、有时失败」的函数
- 用 mocker.patch 替换 asyncio.sleep，避免测试真的等 1s/2s/4s
- 验证重试次数：不能让 ShouldRetry 返回 True 却不重试，也不能让 401 误触发重试
"""
import pytest
from unittest.mock import AsyncMock
from app.infrastructure.llm.circuit_breaker import RetryHandler
from app.infrastructure.llm.llm_api_exception import LlmApiException
from app.common.error_code import ErrorCode


class TestRetryHandlerExecuteWithRetry:
    """测试 execute_with_retry() — 重试编排方法

    这个方法接收一个「协程工厂」函数，执行它：
    - 成功 → 返回结果
    - 失败 → 判断是否可重试 → 等退避延迟 → 再试
    - 不可重试或超过最大次数 → 抛异常

    关键设计：参数是「协程工厂」而不是协程本身。
    因为每次重试需要一个新的协程（协程只能被 await 一次）。
    """

    # ── 场景 1：第一次调用就成功 ─────────────────────────
    # 最简单的路径。验证点：返回值正确 + 协程工厂只被调用了 1 次。

    async def test_should_return_result_when_first_attempt_succeeds(self, mocker):
        """
        Given: 一个第一次就成功的协程工厂
        When:  调用 execute_with_retry
        Then:  直接返回结果，不重试，不 sleep
        """
        handler = RetryHandler(max_retries=3)

        call_count = 0

        async def success_coro():
            nonlocal call_count
            call_count += 1
            return {"data": "ok"}

        result = await handler.execute_with_retry(
            success_coro,
            is_retryable=handler.should_retry,
        )

        assert result == {"data": "ok"}
        assert call_count == 1  # 只调了一次，没有重试

    # ── 场景 2：失败 2 次，第 3 次成功 ───────────────────
    # 核心重试路径。验证点：总共调用了 3 次；第 1、2 次都触发了 sleep；
    # 最终返回成功的结果。

    async def test_should_retry_and_return_result_when_retryable_error_then_success(self, mocker):
        """
        Given: 前 2 次抛可重试异常（429），第 3 次成功
        When:  调用 execute_with_retry
        Then:  重试 2 次后返回成功结果，总共调用 3 次
        """
        # 替换 asyncio.sleep，不让测试真的等 4 秒
        mock_sleep = mocker.patch("asyncio.sleep")

        handler = RetryHandler(max_retries=3)
        call_count = 0

        async def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LlmApiException(ErrorCode.LLM_RATE_LIMITED, message="rate limited")
            return {"data": "finally ok"}

        result = await handler.execute_with_retry(
            fail_twice_then_succeed,
            is_retryable=handler.should_retry,
        )

        assert result == {"data": "finally ok"}
        assert call_count == 3
        # 验证退避延迟被调用（第 1 次等 1s，第 2 次等 2s）
        assert mock_sleep.call_count == 2

    # ── 场景 3：不可重试异常，直接抛出 ───────────────────
    # 401 认证失败不应该重试。验证点：只调了 1 次就抛异常，没有 sleep。

    async def test_should_raise_immediately_when_non_retryable_error(self, mocker):
        """
        Given: 协程工厂直接抛 401 认证失败（不可重试异常）
        When:  调用 execute_with_retry
        Then:  直接抛出 LlmApiException，不重试，不 sleep
        """
        mock_sleep = mocker.patch("asyncio.sleep")
        handler = RetryHandler(max_retries=3)
        call_count = 0

        async def auth_fail():
            nonlocal call_count
            call_count += 1
            raise LlmApiException(ErrorCode.LLM_AUTH_FAILED, message="bad key")

        with pytest.raises(LlmApiException) as exc:
            await handler.execute_with_retry(
                auth_fail,
                is_retryable=handler.should_retry,
            )

        assert exc.value.error_code == ErrorCode.LLM_AUTH_FAILED
        assert call_count == 1  # 只调了 1 次，没有重试
        mock_sleep.assert_not_called()  # 没等，直接抛


class TestRetryHandlerShouldRetry:
    """测试 should_retry() — 判断异常是否可重试"""

    def test_should_return_true_when_timeout(self):
        handler = RetryHandler()
        exc = LlmApiException(ErrorCode.LLM_TIMEOUT, message="timeout")
        assert handler.should_retry(exc) is True

    def test_should_return_true_when_rate_limited(self):
        handler = RetryHandler()
        exc = LlmApiException(ErrorCode.LLM_RATE_LIMITED, message="429")
        assert handler.should_retry(exc) is True

    def test_should_return_true_when_server_error(self):
        handler = RetryHandler()
        exc = LlmApiException(ErrorCode.LLM_SERVER_ERROR, message="503")
        assert handler.should_retry(exc) is True

    def test_should_return_false_when_auth_failed(self):
        handler = RetryHandler()
        exc = LlmApiException(ErrorCode.LLM_AUTH_FAILED, message="bad key")
        assert handler.should_retry(exc) is False