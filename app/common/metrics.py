"""Prometheus 指标定义，统一管理所有指标对象"""
from prometheus_client import Counter, Histogram, Gauge

BUCKETS = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]

# ── 对话请求 ──────────────────────────────────────────────

chat_requests_total = Counter(
    "hify_chat_requests_total",
    "对话请求总数",
    ["agent_id", "status"],
)

chat_request_duration_seconds = Histogram(
    "hify_chat_request_duration_seconds",
    "对话请求延迟（秒）",
    ["agent_id"],
    buckets=BUCKETS,
)

# ── LLM 调用 ──────────────────────────────────────────────

llm_calls_total = Counter(
    "hify_llm_calls_total",
    "LLM 调用总数",
    ["provider", "model", "method", "status"],
)

llm_call_duration_seconds = Histogram(
    "hify_llm_call_duration_seconds",
    "LLM 调用延迟（秒）",
    ["provider", "model", "method"],
    buckets=BUCKETS,
)

# ── 熔断器状态 ────────────────────────────────────────────

circuit_breaker_state = Gauge(
    "hify_circuit_breaker_state",
    "熔断器状态（0=closed, 1=open, 2=half_open）",
    ["provider"],
)

# ── MCP 工具调用 ──────────────────────────────────────────

mcp_tool_calls_total = Counter(
    "hify_mcp_tool_calls_total",
    "MCP 工具调用总数",
    ["tool_name", "status"],
)
