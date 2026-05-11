# LLM 调用技术方案

## 问题背景

外部 LLM API（OpenAI / Claude / Gemini / Ollama）的特点：
- **慢**：单个请求 2-30 秒
- **不稳定**：可能超时、429 限流、500 错误
- **并发有限**：API 本身有速率限制

## 整体架构

```
app/
├── infrastructure/
│   ├── llm/
│   │   ├── base.py              # 抽象基类
│   │   ├── openai_client.py     # OpenAI 实现
│   │   ├── anthropic_client.py  # Claude 实现
│   │   ├── gemini_client.py     # Gemini 实现
│   │   └── ollama_client.py      # Ollama 实现
│   │
│   ├── circuit_breaker.py       # 断路器
│   │
│   └── llm_gateway.py           # LLM 网关（统一入口）
│
├── application/
│   └── llm/
│       └── retry.py             # 重试策略
```

---

## 一、请求分类与优先级

### 两类请求的隔离

Hify 有两类请求：
1. **对话请求（SSE 长连接）**：占用 event loop 资源，持续 10-120 秒
2. **管理请求（CRUD）**：需要快速响应，毫秒级完成

**问题：** 50 个并发 SSE 连接时，如果共用 event loop，管理页面的增删改查会排在队列里等，用户看到的就是页面一直转圈。

**解决：** 在 `LLMGateway` 里区分优先级，对管理请求提供快速通道：

```python
# app/infrastructure/llm/llm_gateway.py

class LLMGateway:
    """
    LLM 统一网关

    优先级设计：
    - 管理请求：直接路由，不走并发控制（轻量）
    - 对话请求：走全局 Semaphore 控制（重量）
    """

    def __init__(self):
        # 对话请求并发控制
        self._chat_semaphore = asyncio.Semaphore(10)  # SSE 并发上限
        self._provider_semaphores: dict[str, asyncio.Semaphore] = {}
        # 管理请求不限制

        self._clients: dict[str, LLMClientBase] = {}

    async def chat_complete(self, provider: str, messages: list[dict], model: str, **kwargs) -> str:
        """
        对话请求（重量级，走并发控制）
        用于 Agent 对话、工作流调用等
        """
        semaphore = self._get_provider_semaphore(provider)

        async with semaphore:
            async with self._chat_semaphore:
                # 严格超时，流式场景 120s
                return await asyncio.wait_for(
                    self._clients[provider].complete(messages, model, **kwargs),
                    timeout=120.0
                )

    async def admin_call(self, provider: str, messages: list[dict], model: str, **kwargs) -> str:
        """
        管理请求（轻量级，快速响应）
        用于连通性测试、配置验证等
        不受 chat_semaphore 限制
        """
        # 管理请求用短超时：10s
        return await asyncio.wait_for(
            self._clients[provider].complete(messages, model, **kwargs),
            timeout=10.0
        )

    async def stream(self, provider: str, messages: list[dict], model: str, **kwargs):
        """流式对话，同样受并发控制，超时 120s"""
        semaphore = self._get_provider_semaphore(provider)

        async with semaphore:
            async with self._chat_semaphore:
                async for chunk in self._clients[provider].stream(messages, model, **kwargs):
                    yield chunk
```

**优先级隔离原则：**
- 对话请求占用 `chat_semaphore`（最多 10 个并发 SSE）
- 管理请求不占用 `chat_semaphore`，走独立路径
- 一个 Provider 挂了不影响另一个（独立 Semaphore）

---

## 二、线程/并发管理

### 异步优先 + 连接池控制

**背景：** LLM 调用是 IO 密集型（等待网络），不是 CPU 密集型。Python 用 `async/await` 释放事件循环，比多线程更高效。

```python
# app/infrastructure/llm/base.py
from abc import ABC, abstractmethod
import asyncio
from typing import AsyncIterator
import httpx

class LLMClientBase(ABC):
    """LLM 客户端抽象基类"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        max_connections: int = 20,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=10,
        )

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str,
        **kwargs
    ) -> str:
        """同步调用，返回完整响应"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        model: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式调用，yield 每个 token"""
        pass

    async def close(self):
        await self._connector.close()
```

**并发控制设计：**

| 维度 | 限制值 | 说明 |
|------|--------|------|
| 对话全局并发 | 10 | SSE 连接上限，防止系统过载 |
| 每 Provider 并发 | 5 | 防止单个 provider 触发限流 |
| 管理请求 | 无限制 | 轻量，快速响应 |

---

## 三、容错：断路器模式

### 为什么需要

LLM API 不稳定时，如果持续调用会：
1. 大量请求堆积，内存飙升
2. 下游服务被压垮
3. 用户等待超时，体验差

**断路器模式：** 连续失败 N 次后，短路后续请求，快速失败而不是等待超时。

```python
# app/infrastructure/circuit_breaker.py
import asyncio
import time
from enum import Enum
from typing import Optional

class CircuitState(Enum):
    CLOSED = "closed"        # 正常，流量通过
    OPEN = "open"            # 断路，拒绝请求
    HALF_OPEN = "half_open"  # 探测，恢复中

class CircuitBreaker:
    """
    断路器实现

    状态转换：
    CLOSED → OPEN：连续失败超过 threshold
    OPEN → HALF_OPEN：open_timeout 后放行一个探测请求
    HALF_OPEN → CLOSED：探测成功
    HALF_OPEN → OPEN：探测失败
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,      # 连续失败 5 次
        success_threshold: int = 2,      # 需要连续成功 2 次才恢复
        open_timeout: float = 30.0,      # 30 秒后尝试恢复
    ):
        self.name = name
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._open_timeout = open_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self._open_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    async def call(self, func, *args, **kwargs):
        """通过断路器执行函数"""
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit {self.name} is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        else:
            self._failure_count = 0

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
        elif self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN

class CircuitOpenError(Exception):
    """断路器打开时抛出的异常"""
    pass
```

**集成到 LLM Gateway：**

```python
# app/infrastructure/llm/llm_gateway.py
from app.infrastructure.circuit_breaker import CircuitBreaker, CircuitOpenError

class LLMGateway:
    def __init__(self):
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def _get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = CircuitBreaker(
                name=provider,
                failure_threshold=5,
                open_timeout=30.0,
            )
        return self._circuit_breakers[provider]

    async def chat_complete(self, provider: str, messages: list[dict], model: str, **kwargs):
        circuit = self._get_circuit_breaker(provider)

        try:
            return await circuit.call(
                self._do_call, provider, messages, model, **kwargs
            )
        except CircuitOpenError:
            # 断路器打开，快速失败，不等超时
            return await self._fallback(provider, messages, model)
```

---

## 四、超时设计

### 两档超时（简化方案）

| 场景 | 超时 | 说明 |
|------|------|------|
| **SSE 流式对话** | 120 秒 | 用户感知等待时间，流式有 chunk 返回 |
| **管理请求/连通性测试** | 10 秒 | 验证配置是否正确，不需要等太久 |

```python
# app/infrastructure/llm/llm_gateway.py

class TimeoutConfig:
    """超时配置（两档简化）"""
    SSE_TIMEOUT = 120.0   # 流式对话
    ADMIN_TIMEOUT = 10.0  # 管理/测试
    SYNC_TIMEOUT = 60.0   # 非流式同步调用（备用）
```

**超时后的处理：**

```python
async def chat_complete(self, provider: str, messages: list[dict], model: str, **kwargs):
    try:
        return await asyncio.wait_for(
            self._clients[provider].complete(messages, model, **kwargs),
            timeout=TimeoutConfig.SSE_TIMEOUT
        )
    except asyncio.TimeoutError:
        # 超时后尝试 fallback 到其他 provider
        logger.warning(f"Timeout calling {provider}/{model}, trying fallback")
        return await self._fallback(provider, messages, model)
```

**为什么不用更细分的三档（connect/read/total）：**
- 分层超时增加了配置复杂度
- SSE 场景下 connect + read 共享 120s，实际效果相同
- 简化方案更易维护

---

## 五、重试策略

### 按异常类型区分重试

**核心原则：** 不是所有失败都值得重试。

| 异常类型 | 是否重试 | 原因 |
|----------|----------|------|
| 网络超时（Timeout） | ✅ 重试 | 临时抖动，重试可能成功 |
| 限流（429） | ✅ 退避重试 | 等一等再试 |
| 服务器过载（503/504） | ✅ 重试 | 临时性，等恢复 |
| **认证失败（401）** | ❌ 不重试 | API Key 错了，重试也没用 |
| **Forbidden（403）** | ❌ 不重试 | 权限问题，重试也失败 |
| 参数错误（400） | ❌ 不重试 | 请求有问题，重试也失败 |
| 内容过滤（400） | ❌ 不重试 | 内容违规，重试也失败 |
| 服务器内部错误（500） | ❌ 不重试 | 服务端问题，非我能解决 |

```python
# app/infrastructure/llm/retry.py

class RetryConfig:
    """重试配置"""
    MAX_ATTEMPTS = 3
    BASE_DELAY = 1.0
    MAX_DELAY = 30.0

    # 明确：认证失败不重试
    NON_RETRYABLE_CODES = {401, 403, 400}  # 认证、权限、参数错误

    @staticmethod
    def should_retry(error: Exception) -> bool:
        """判断错误是否应该重试"""
        # 超时重试
        if isinstance(error, asyncio.TimeoutError):
            return True

        # 连接错误重试
        if isinstance(error, (ConnectionError, aiohttp.ClientError)):
            return True

        # HTTP 状态码判断
        if isinstance(error, httpx.HTTPStatusError):
            code = error.response.status_code
            # 401 认证失败，不重试
            if code == 401:
                return False
            # 4xx 客户端错误（除 429），不重试
            if 400 <= code < 500 and code != 429:
                return False
            # 5xx 服务端错误，重试
            if code >= 500:
                return True
            # 429 限流，重试（会走退避）
            if code == 429:
                return True

        return False
```

### 退避策略（Exponential Backoff + Jitter）

避免多请求同时重试造成惊群效应。

```python
# app/infrastructure/llm/retry.py
import random
import asyncio

class BackoffStrategy:
    """
    指数退避 + 抖动
    延迟 = min(base * 2^n + jitter, max_delay)
    """

    def __init__(self, base_delay: float = 1.0, max_delay: float = 30.0):
        self._base = base_delay
        self._max = max_delay

    def get_delay(self, attempt: int) -> float:
        exponential_delay = self._base * (2 ** attempt)
        jitter = random.uniform(0, exponential_delay * 0.1)  # 10% 抖动
        return min(exponential_delay + jitter, self._max)

    async def wait(self, attempt: int):
        delay = self.get_delay(attempt)
        await asyncio.sleep(delay)
```

**退避曲线（3 次重试）：**

| 重试次数 | 计算公式 | 延迟范围 |
|----------|----------|----------|
| 第1次 | min(1 * 2^0 + jitter, 30) | 1.0 - 1.1s |
| 第2次 | min(1 * 2^1 + jitter, 30) | 2.0 - 2.2s |
| 第3次 | min(1 * 2^2 + jitter, 30) | 4.0 - 4.4s |

### 完整重试实现

```python
# app/infrastructure/llm/retry.py

class RetryExecutor:
    def __init__(self, config: RetryConfig, backoff: BackoffStrategy):
        self._config = config
        self._backoff = backoff

    async def execute(self, func, *args, **kwargs):
        """
        执行带重试的调用
        """
        last_error = None

        for attempt in range(self._config.MAX_ATTEMPTS):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if attempt + 1 >= self._config.MAX_ATTEMPTS:
                    break

                if not self._config.should_retry(e):
                    break  # 不可重试的错误，直接抛出

                await self._backoff.wait(attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")

        raise RetryExhaustedError(
            f"All {self._config.MAX_ATTEMPTS} attempts failed",
            last_error
        )
```

### 流式调用不重试

流式调用一旦开始 yield 数据就无法撤回，不能重试。

```python
async def stream(self, provider: str, messages: list[dict], model: str, **kwargs):
    """
    流式调用：不重试
    已经 yield 的数据无法撤回
    """
    try:
        semaphore = self._get_provider_semaphore(provider)
        async with semaphore:
            async with self._chat_semaphore:
                async for chunk in self._clients[provider].stream(messages, model, **kwargs):
                    yield chunk
    except Exception as e:
        # 流式异常：返回错误信息作为特殊 chunk
        yield f"error: {str(e)}"
```

---

## 六、综合集成

### LLM Gateway 最终形态

```python
# app/infrastructure/llm/llm_gateway.py

class LLMGateway:
    """
    LLM 统一网关，整合：
    - 请求优先级隔离（对话 vs 管理）
    - 并发控制（Semaphore）
    - 断路器（per-provider）
    - 超时（两档）
    - 重试（指数退避）
    """

    def __init__(self):
        # 对话并发控制
        self._chat_semaphore = asyncio.Semaphore(10)
        self._provider_semaphores: dict[str, asyncio.Semaphore] = {}

        # 断路器（每 provider 独立）
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

        # 重试
        self._retry_config = RetryConfig()
        self._backoff = BackoffStrategy()

        # 客户端
        self._clients: dict[str, LLMClientBase] = {}

    async def chat_complete(
        self,
        provider: str,
        messages: list[dict],
        model: str,
        retry: bool = True,
    ) -> str:
        """
        对话请求（重量级）
        超时 120s，受并发控制，可重试
        """
        circuit = self._get_circuit_breaker(provider)
        semaphore = self._get_provider_semaphore(provider)

        async def do_call():
            async with semaphore:
                async with self._chat_semaphore:
                    return await asyncio.wait_for(
                        self._clients[provider].complete(messages, model),
                        timeout=TimeoutConfig.SSE_TIMEOUT
                    )

        try:
            if retry:
                return await circuit.call(
                    RetryExecutor(self._retry_config, self._backoff).execute,
                    do_call
                )
            else:
                return await circuit.call(do_call)
        except CircuitOpenError:
            return await self._fallback(provider, messages, model)

    async def admin_call(
        self,
        provider: str,
        messages: list[dict],
        model: str,
    ) -> str:
        """
        管理请求（轻量级）
        超时 10s，不受 chat_semaphore 控制
        用于连通性测试、配置验证
        """
        return await asyncio.wait_for(
            self._clients[provider].complete(messages, model),
            timeout=TimeoutConfig.ADMIN_TIMEOUT
        )

    async def stream(self, provider: str, messages: list[dict], model: str, **kwargs):
        """流式对话，不重试"""
        semaphore = self._get_provider_semaphore(provider)

        try:
            async with semaphore:
                async with self._chat_semaphore:
                    async for chunk in self._clients[provider].stream(
                        messages, model, **kwargs
                    ):
                        yield chunk
        except Exception as e:
            yield f"error: {str(e)}"

    async def _fallback(
        self,
        failed_provider: str,
        messages: list[dict],
        model: str,
    ) -> str:
        """Fallback 到其他 provider"""
        for provider in self._clients:
            if provider == failed_provider:
                continue
            try:
                return await self.chat_complete(
                    provider, messages, model, retry=False
                )
            except Exception:
                continue

        raise NoAvailableProviderError("All LLM providers unavailable")
```

---

## 七、各 Provider 配置

```python
# app/infrastructure/llm/config.py

PROVIDER_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "timeout": 120.0,
        "rate_limit": 500,    # RPM（收费版）
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "timeout": 120.0,
        "rate_limit": 50,
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "timeout": 120.0,
        "rate_limit": 60,
        "models": ["gemini-pro", "gemini-pro-vision"],
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",  # 兼容 OpenAI API 格式
        "timeout": 300.0,  # 本地模型可更长
        "rate_limit": 999999,
        "models": ["llama2", "mistral", "qwen"],
    },
}
```

---

## 八、监控与告警

```python
# app/infrastructure/llm/metrics.py

class LLMMetrics:
    """LLM 调用指标收集"""

    @staticmethod
    def record(provider: str, model: str, latency: float, success: bool):
        # 发送到 Prometheus / 写入结构化日志
        logger.info(
            f"llm_call{{provider={provider},model={model}}} "
            f"latency={latency:.3f} success={success}"
        )

    @staticmethod
    def record_error(provider: str, error_type: str):
        logger.error(f"llm_error{{provider={provider},type={error_type}}}")

    @staticmethod
    def record_circuit_open(provider: str):
        logger.warning(f"llm_circuit_open{{provider={provider}}}")

# 使用
async def call_with_metrics(provider: str, messages: list[dict], model: str):
    start = time.time()
    try:
        result = await gateway.chat_complete(provider, messages, model)
        LLMMetrics.record(provider, model, time.time() - start, True)
        return result
    except Exception as e:
        LLMMetrics.record(provider, model, time.time() - start, False)
        LLMMetrics.record_error(provider, type(e).__name__)
        raise
```

---

## 总结：关键配置参数

| 维度 | 参数 | 推荐值 |
|------|------|--------|
| **并发** | 对话全局 Semaphore | 10 |
| **并发** | 每 Provider Semaphore | 5 |
| **断路器** | 失败阈值 | 连续 5 次 |
| **断路器** | 恢复超时 | 30 秒 |
| **超时** | SSE 流式对话 | 120s |
| **超时** | 管理请求/测试 | 10s |
| **超时** | 非流式同步（备用） | 60s |
| **重试** | 最大次数 | 3 |
| **重试** | 基础延迟 | 1s |
| **重试** | 最大延迟 | 30s |
| **重试** | 401/403/400 不重试 | 明确排除 |
| **重试** | 429/503/504 重试 | 退避重试 |

---

## 快速参考：开发时检查清单

- [ ] 对话请求用 `chat_complete()`，受并发控制
- [ ] 管理/测试请求用 `admin_call()`，快速响应
- [ ] 流式调用用 `stream()`，不重试
- [ ] 401/403 错误不重试，直接抛异常
- [ ] 429 限流走退避重试
- [ ] Provider 挂了走 fallback
- [ ] 断路器打开时快速失败