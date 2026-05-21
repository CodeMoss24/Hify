"""结构化日志配置：structlog + correlation_id 中间件。

输出策略：全部输出到 stdout，日志轮转交由 Docker logging driver 处理。
- 开发环境：structlog 彩色 ConsoleRenderer，stdlib 彩色控制台
- 生产环境：structlog JSONRenderer，stdlib JSON
"""
import json
import logging
import os
import sys
import time
from typing import Any

import structlog
from fastapi import FastAPI


class _JsonFormatter(logging.Formatter):
    """第三方库日志的 JSON 格式化器"""
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


class _ColoredFormatter(logging.Formatter):
    """第三方库日志的彩色控制台输出"""
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        return (
            f"{color}[{self.formatTime(record)}] "
            f"[{record.levelname}] "
            f"{record.name}: {record.getMessage()}{self.RESET}"
        )


def _uuid7() -> str:
    """Generate a UUID7 (time-ordered, RFC 9562).

    UUID7 的 48-bit 毫秒时间戳放在最前面，同一请求的多条日志可以按
    correlation_id 排序后保持时间顺序，避免了 UUID4 随机打散的问题。
    """
    ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand = os.urandom(10)
    buf = bytearray(16)
    buf[0] = (ts_ms >> 40) & 0xFF
    buf[1] = (ts_ms >> 32) & 0xFF
    buf[2] = (ts_ms >> 24) & 0xFF
    buf[3] = (ts_ms >> 16) & 0xFF
    buf[4] = (ts_ms >> 8) & 0xFF
    buf[5] = ts_ms & 0xFF
    buf[6:16] = rand
    # version (4 bits): 0x7 → 0111
    buf[6] = (buf[6] & 0x0F) | 0x70
    # variant (2 bits): 10 → 10xx
    buf[8] = (buf[8] & 0x3F) | 0x80
    h = buf.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def get_correlation_id() -> str:
    """获取当前请求的 correlation_id（供外部模块使用）"""
    ctx = structlog.contextvars.get_contextvars()
    return ctx.get("correlation_id", "-")


class CorrelationIdMiddleware:
    """纯 ASGI 中间件：从 X-Request-ID 透传或生成 correlation_id，注入 structlog contextvars

    不用 BaseHTTPMiddleware — 其 call_next() 会创建新 asyncio task，
    导致 structlog.contextvars 上下文丢失。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # 从 header 取 X-Request-ID，没有则生成 UUID
        headers = dict(scope.get("headers", []))
        correlation_id = headers.get(
            b"x-request-id",
            _uuid7().encode(),
        ).decode()

        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        async def send_with_header(message):
            if message["type"] == "http.response.start":
                msg_headers = list(message.get("headers", []))
                # 避免重复设置
                msg_headers.append((b"x-request-id", correlation_id.encode()))
                message["headers"] = msg_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.clear_contextvars()


class RequestTimingMiddleware:
    """纯 ASGI 中间件：记录请求耗时日志

    不用 BaseHTTPMiddleware — 同上原因。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        path = scope.get("path", "")
        method = scope.get("method", "")
        status_code: int = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        elapsed = time.monotonic() - start
        log = structlog.get_logger("hify.request")
        log_kwargs: dict[str, Any] = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": int(elapsed * 1000),
        }
        if elapsed > 1.0:
            log.warning("request.slow", **log_kwargs)
        else:
            log.info("request.completed", **log_kwargs)


def setup_logging(app: FastAPI | None = None) -> None:
    """配置结构化日志 + 注册中间件

    全部输出到 stdout，日志轮转交由 Docker logging driver 处理。
    - 开发环境：structlog 彩色 ConsoleRenderer，stdlib 彩色控制台
    - 生产环境：structlog JSONRenderer，stdlib JSON
    """
    env = os.getenv("APP_ENV", "dev")
    is_prod = env == "prod"

    # ── Stdlib logging：仅用于第三方库（uvicorn, sqlalchemy 等）──
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    stdlib_handler = logging.StreamHandler(sys.stdout)
    stdlib_handler.setFormatter(_JsonFormatter() if is_prod else _ColoredFormatter())
    stdlib_handler.setLevel(logging.DEBUG if not is_prod else logging.INFO)
    root.addHandler(stdlib_handler)

    if not is_prod:
        root.setLevel(logging.DEBUG)

    # ── structlog：应用代码结构化日志 ──
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if is_prod:
        final_processor = structlog.processors.JSONRenderer(
            serializer=lambda obj, **kw: json.dumps(obj, ensure_ascii=False, **kw)
        )
        min_level = logging.INFO
    else:
        final_processor = structlog.dev.ConsoleRenderer(colors=True)
        min_level = logging.DEBUG

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            final_processor,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(min_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # ── 注册中间件 ──
    if app is not None:
        app.add_middleware(CorrelationIdMiddleware)
        app.add_middleware(RequestTimingMiddleware)
