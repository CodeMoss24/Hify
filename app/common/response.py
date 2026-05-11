"""统一响应模型"""
from typing import Generic, Optional, Any

from pydantic import BaseModel


class ApiResponse(BaseModel, Generic[Any]):
    """统一 API 响应格式"""

    code: int = 200
    message: str = "success"
    data: Optional[Any] = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "success") -> "ApiResponse":
        """快速构建成功响应"""
        return cls(code=200, message=message, data=data)

    @classmethod
    def fail(cls, code: int = 1000, message: str = "fail") -> "ApiResponse":
        """快速构建失败响应"""
        return cls(code=code, message=message, data=None)


class PageResult(ApiResponse, Generic[Any]):
    """统一分页响应，继承 ApiResponse，顶层结构为 {code, message, data}"""

    list: list[Any]
    total: int
    page: int
    page_size: int