"""结构化日志配置：开发环境彩色控制台，生产环境 JSON 文件滚动"""
import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

# 日志上下文：traceId 在同一请求内自动传递
_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """获取当前请求的 traceId"""
    return _trace_id_ctx.get()


class TraceIdFilter(logging.Filter):
    """日志过滤器：将 traceId 注入每条日志记录"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """JSON 格式化器：生产环境输出结构化 JSON"""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
        }
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色格式化器：开发环境控制台输出"""

    COLORS = {
        "DEBUG": "\033[36m",    # cyan
        "INFO": "\033[32m",     # green
        "WARNING": "\033[33m", # yellow
        "ERROR": "\033[31m",   # red
        "CRITICAL": "\033[35m", # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        trace = getattr(record, "trace_id", "-")
        return (
            f"{color}[{self.formatTime(record)}] "
            f"[{record.levelname}] "
            f"[{trace}] "
            f"{record.name}: {record.getMessage()}{self.RESET}"
        )


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件：自动记录 method/path/status/耗时，traceId 贯穿全请求"""

    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())
        _trace_id_ctx.set(trace_id)
        start = time.monotonic()

        response = await call_next(request)

        elapsed = time.monotonic() - start
        status = response.status_code
        log_level = logging.WARNING if elapsed > 1.0 else logging.INFO

        logger = logging.getLogger("hify.request")
        log_msg = (
            f"{request.method} {request.url.path} "
            f"-> {status} ({elapsed:.3f}s)"
        )
        logger.log(
            log_level,
            log_msg,
            extra={"trace_id": trace_id},
        )

        _trace_id_ctx.set("")
        return response


def setup_logging(app: FastAPI) -> None:
    """配置日志：开发环境彩色控制台，生产环境 JSON 文件按天滚动"""
    env = os.getenv("APP_ENV", "dev")

    # 根日志级别
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 清除已有 handler
    root.handlers.clear()

    if env == "prod":
        # 生产环境：JSON 格式，文件滚动，保留 30 天
        logs_dir = os.getenv("LOGS_DIR", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        handler = TimedRotatingFileHandler(
            f"{logs_dir}/hify.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        handler.setFormatter(JsonFormatter())
        handler.setLevel(logging.INFO)
        root.addHandler(handler)

        # 错误日志单独记录
        error_handler = TimedRotatingFileHandler(
            f"{logs_dir}/hify_error.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JsonFormatter())
        root.addHandler(error_handler)

    else:
        # 开发环境：彩色控制台输出
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter())
        handler.setLevel(logging.DEBUG)
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)

    # 所有 logger 注入 traceId filter
    for logger_name in ["hify", "hify.request"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG if env != "prod" else logging.INFO)
        logger.addFilter(TraceIdFilter())

    # uvicorn 日志也加上 traceId
    for name in ["uvicorn", "uvicorn.access"]:
        logger = logging.getLogger(name)
        logger.addFilter(TraceIdFilter())

    # 将请求日志中间件注册到 FastAPI
    app.add_middleware(RequestLogMiddleware)