"""结构化日志字段常量与事件名常量

所有日志打点必须使用此模块定义的常量，禁止在代码中硬编码字段名字符串。
"""

# ── 通用字段 ──────────────────────────────────────────────

LOG_KEY_CORRELATION_ID = "correlation_id"
LOG_KEY_MODULE = "module"

# ── LLM 调用专用字段 ───────────────────────────────────────

LOG_KEY_PROVIDER = "provider"
LOG_KEY_MODEL = "model"
LOG_KEY_ACTION = "action"
LOG_KEY_METHOD = "method"
LOG_KEY_URL = "url"
LOG_KEY_LATENCY_MS = "latency_ms"
LOG_KEY_STATUS_CODE = "status_code"
LOG_KEY_ERROR_CODE = "error_code"

# ── 熔断器字段 ────────────────────────────────────────────

LOG_KEY_FROM_STATE = "from_state"
LOG_KEY_TO_STATE = "to_state"
LOG_KEY_FAILURE_COUNT = "failure_count"

# ── 重试字段 ──────────────────────────────────────────────

LOG_KEY_RETRY_COUNT = "retry_count"
LOG_KEY_ATTEMPT = "attempt"
LOG_KEY_MAX_RETRIES = "max_retries"
LOG_KEY_DELAY = "delay"

# ── 事件名常量 ────────────────────────────────────────────

EVENT_LLM_CALL_START = "llm_call.start"
EVENT_LLM_CALL_END = "llm_call.end"
EVENT_LLM_STREAM_START = "llm_stream.start"
EVENT_LLM_STREAM_END = "llm_stream.end"
EVENT_CIRCUIT_STATE_CHANGE = "circuit_breaker.state_change"
EVENT_CIRCUIT_REJECTED = "circuit_breaker.rejected"
EVENT_RETRY = "retry.attempt"
EVENT_RETRY_EXHAUSTED = "retry.exhausted"
