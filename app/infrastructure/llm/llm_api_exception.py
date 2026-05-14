"""LLM API 调用异常"""
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode


class LlmApiException(BizException):
    """LLM API 调用异常，携带错误码和原始异常"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str | None = None,
        *,
        cause: Exception | None = None,
    ):
        super().__init__(error_code, message, cause=cause)