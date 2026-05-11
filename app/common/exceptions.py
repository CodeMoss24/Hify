"""业务异常定义"""
from app.common.error_code import ErrorCode


class BizException(Exception):
    """业务异常，携带错误码，支持自定义 message，可包装底层异常"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str | None = None,
        *,
        cause: Exception | None = None,
    ):
        self.error_code = error_code
        self.message = message or error_code.message
        self.code = error_code.code
        self.cause = cause

    def __str__(self) -> str:
        base = f"[{self.code}] {self.message}"
        if self.cause:
            base += f" <- {type(self.cause).__name__}: {self.cause}"
        return base