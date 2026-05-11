"""全局异常处理器"""
import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.common.error_code import ErrorCode
from app.common.exceptions import BizException
from app.common.response import ApiResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器到 FastAPI 应用"""

    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException) -> Any:
        """捕获业务异常，返回规范化的 ApiResponse.fail()"""
        logger.warning(
            f"[BizException] path={request.url.path} code={exc.code} message={exc.message}",
            extra={"cause": str(exc.cause)} if exc.cause else None,
        )
        return ApiResponse.fail(code=exc.code, message=exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> Any:
        """捕获 FastAPI 参数校验异常，返回规范化的 ApiResponse.fail()"""
        errors = exc.errors()
        logger.warning(f"[ValidationError] path={request.url.path} errors={errors}")
        return ApiResponse.fail(
            code=ErrorCode.PARAM_ERROR.code,
            message=ErrorCode.PARAM_ERROR.message,
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> Any:
        """兜底捕获所有未处理异常，返回 ApiResponse.fail()，隐藏堆栈信息"""
        logger.error(
            f"[InternalError] path={request.url.path} exception={type(exc).__name__}: {exc}\n"
            + traceback.format_exc(),
        )
        return ApiResponse.fail(
            code=ErrorCode.INTERNAL_ERROR.code,
            message=ErrorCode.INTERNAL_ERROR.message,
        )