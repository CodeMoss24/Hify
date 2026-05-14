"""统一响应模型"""
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""

    code: int = 200
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: T = None, message: str = "success") -> "ApiResponse":
        """快速构建成功响应"""
        return cls(code=200, message=message, data=data)

    @classmethod
    def fail(cls, code: int = 1000, message: str = "fail") -> "ApiResponse":
        """快速构建失败响应"""
        return cls(code=code, message=message, data=None)


class PageResult(BaseModel, Generic[T]):
    """统一分页响应，继承 BaseModel，顶层结构为 {code, message, data}"""

    list: list[T]
    total: int
    page: int
    page_size: int