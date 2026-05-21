"""测试 CircuitBreaker — 熔断器状态机

学习目标：怎么测状态机
- 状态机测试的核心：验证「当前状态 + 输入 → 新状态 + 输出」的每一种组合
- 不要只测返回值，还要验证内部状态是否被修改
- 每个测试方法只覆盖一条状态转换路径
"""
import pytest
from app.infrastructure.llm.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerCanExecute:
    """测试 can_execute() — 熔断器的「门禁」方法

    这个方法只有一个职责：判断当前是否允许请求通过。
    但它内部有 3 个状态分支，其中 OPEN 状态下又有一个时间判断子分支。
    """

    # ── 场景 1：CLOSED 状态 ────────────────────────────
    # 这是系统正常运行时的状态。熔断器刚创建时就是 CLOSED。
    # 验证点：返回值是 True，状态保持 CLOSED 不变。

    async def test_should_return_true_when_state_is_closed(self):
        """
        Given: 一个新创建的 CircuitBreaker，初始状态是 CLOSED
        When:  调用 can_execute()
        Then:  返回 True（放行），状态保持 CLOSED
        """
        breaker = CircuitBreaker(provider_key="test-provider")

        result = await breaker.can_execute()

        assert result is True
        assert breaker._state == CircuitState.CLOSED

    # ── 场景 2：OPEN 状态下，冷却时间还没到 ──────────────
    # 连续失败 5 次后熔断器打开（OPEN），此时距最后一次失败才过了 5 秒，
    # 小于 30 秒冷却时间，应该仍然拒绝请求。
    # 验证点：返回值是 False，状态保持 OPEN。

    async def test_should_return_false_when_circuit_is_open_and_timeout_not_elapsed(self):
        """
        Given: 熔断器已 OPEN，_last_failure_time 设在 10 秒前（< 30s 冷却时间）
        When:  调用 can_execute()
        Then:  返回 False（拒绝），状态保持 OPEN
        """
        breaker = CircuitBreaker(provider_key="test-provider", open_timeout=30.0)
        # 直接设置内部状态来模拟「已经熔断打开」的场景
        breaker._state = CircuitState.OPEN
        breaker._failure_count = 5
        breaker._last_failure_time = 0  # 很久以前，下面会覆盖

        import time
        breaker._last_failure_time = time.monotonic() - 10  # 10 秒前失败，还没到 30 秒冷却

        result = await breaker.can_execute()

        assert result is False
        assert breaker._state == CircuitState.OPEN  # 状态没有变

    # ── 场景 3：OPEN 状态下，冷却时间到了 ────────────────
    # 熔断器打开 35 秒后（超过 30 秒冷却），应该放行一个探测请求，
    # 同时状态从 OPEN 切换到 HALF_OPEN（半开）。
    # 这是最关键的转换：不验证这个，熔断器永远不会恢复。
    # 验证点：返回值是 True，状态变成了 HALF_OPEN。

    async def test_should_transition_to_half_open_when_open_timeout_elapsed(self):
        """
        Given: 熔断器已 OPEN 了 35 秒（> 30s 冷却时间）
        When:  调用 can_execute()
        Then:  返回 True（放行探测请求），状态切到 HALF_OPEN
        """
        breaker = CircuitBreaker(provider_key="test-provider", open_timeout=30.0)
        breaker._state = CircuitState.OPEN
        breaker._failure_count = 5

        import time
        breaker._last_failure_time = time.monotonic() - 35  # 35 秒前失败，已过冷却

        result = await breaker.can_execute()

        assert result is True
        assert breaker._state == CircuitState.HALF_OPEN  # 关键：状态转了！


class TestCircuitBreakerRecordSuccess:
    """测试 record_success() — 记录一次成功，重置熔断器

    不管当前状态是什么，调用后都是：状态=CLOSED，计数=0。
    唯一区别是 HALF_OPEN 恢复时会多打一行日志（我们不管日志，只管状态）。
    """

    async def test_should_close_circuit_when_half_open_probe_succeeds(self):
        """
        Given: 熔断器处于 HALF_OPEN（探测中）
        When:  调用 record_success()
        Then:  状态切回 CLOSED，失败计数清零，last_failure_time 置空
        """
        breaker = CircuitBreaker(provider_key="test-provider")
        breaker._state = CircuitState.HALF_OPEN
        breaker._failure_count = 5
        breaker._last_failure_time = 12345.0

        await breaker.record_success()

        assert breaker._state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._last_failure_time is None

    async def test_should_reset_counters_when_already_closed(self):
        """
        Given: 熔断器已经是 CLOSED，但 failure_count=3（之前有过失败但没到阈值）
        When:  调用 record_success()
        Then:  状态保持 CLOSED，计数清零
        """
        breaker = CircuitBreaker(provider_key="test-provider")
        breaker._state = CircuitState.CLOSED
        breaker._failure_count = 3

        await breaker.record_success()

        assert breaker._state == CircuitState.CLOSED
        assert breaker._failure_count == 0


class TestCircuitBreakerRecordFailure:
    """测试 record_failure() — 记录一次失败，可能触发熔断

    和 can_execute / record_success 不同，这个方法会「看情况」改变状态：
    - 如果当前是 HALF_OPEN → 探测失败了，立即回 OPEN
    - 如果当前是 CLOSED 且失败次数 < 阈值 → 只累加计数，不改变状态
    - 如果当前是 CLOSED 且失败次数 ≥ 阈值 → 切到 OPEN（触发熔断）
    """

    async def test_should_only_increment_count_when_below_threshold(self):
        """
        Given: CLOSED 状态，已失败 3 次（< 阈值 5）
        When:  调用 record_failure()
        Then:  状态保持 CLOSED，计数 +1 变成 4
        """
        breaker = CircuitBreaker(provider_key="test-provider", failure_threshold=5)
        breaker._state = CircuitState.CLOSED
        breaker._failure_count = 3

        await breaker.record_failure()

        assert breaker._state == CircuitState.CLOSED
        assert breaker._failure_count == 4

    async def test_should_open_circuit_when_failures_reach_threshold(self):
        """
        Given: CLOSED 状态，已失败 4 次（再失败一次就到阈值 5）
        When:  调用 record_failure()
        Then:  状态切到 OPEN，计数变成 5
        """
        breaker = CircuitBreaker(provider_key="test-provider", failure_threshold=5)
        breaker._state = CircuitState.CLOSED
        breaker._failure_count = 4

        await breaker.record_failure()

        assert breaker._state == CircuitState.OPEN
        assert breaker._failure_count == 5

    async def test_should_reopen_immediately_when_half_open_probe_fails(self):
        """
        Given: HALF_OPEN 状态（探测请求已经发出去了）
        When:  探测请求失败，调用 record_failure()
        Then:  立即切回 OPEN——不等下一次，不等 threshold，一次就回
        """
        breaker = CircuitBreaker(provider_key="test-provider", failure_threshold=5)
        breaker._state = CircuitState.HALF_OPEN
        breaker._failure_count = 5

        await breaker.record_failure()

        assert breaker._state == CircuitState.OPEN