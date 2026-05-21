"""全局异常处理器（structlog 输出，自动携带 correlation_id）"""
import traceback
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.common.error_code import ErrorCode
from app.common.exceptions import BizException
from app.common.response import ApiResponse

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器到 FastAPI 应用"""

    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException) -> Any:
        logger.warning(
            "exception.biz",
            path=request.url.path,
            error_code=exc.code,
            error_message=exc.message,
        )
        return JSONResponse(
            ApiResponse.fail(code=exc.code, message=exc.message).model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> Any:
        errors = exc.errors()
        logger.warning(
            "exception.validation",
            path=request.url.path,
            errors=errors,
        )
        return JSONResponse(
            ApiResponse.fail(
                code=ErrorCode.PARAM_ERROR.code,
                message=ErrorCode.PARAM_ERROR.message,
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> Any:
        logger.error(
            "exception.unhandled",
            path=request.url.path,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            ApiResponse.fail(
                code=ErrorCode.INTERNAL_ERROR.code,
                message=ErrorCode.INTERNAL_ERROR.message,
            ).model_dump()
        )
