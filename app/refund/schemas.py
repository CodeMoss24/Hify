"""Refund Pydantic DTO"""
from pydantic import BaseModel, Field


class RefundEligibilityResponse(BaseModel):
    """退款资格检查响应"""

    eligible: bool
    reason: str
    deadline: str
    amount: int


class RefundSubmitResponse(BaseModel):
    """退款提交响应"""

    refund_id: int
    status: str
    status_label: str
    estimated_days: int


class RefundStatusResponse(BaseModel):
    """退款状态查询响应"""

    refund_id: int
    order_id: str
    amount: int
    status: str
    status_label: str
    submitted_at: str
    reject_reason: str


class RefundCancelResponse(BaseModel):
    """退款撤销响应"""

    success: bool
    message: str


class RefundCheckRequest(BaseModel):
    """退款资格检查请求"""

    order_id: str = Field(..., min_length=1, max_length=64)


class RefundSubmitRequest(BaseModel):
    """退款提交请求"""

    order_id: str = Field(..., min_length=1, max_length=64)
    user_id: str = Field(..., min_length=1, max_length=64)
    amount: int = Field(..., ge=1)
    reason: str = Field(default="", max_length=512)


class RefundCancelRequest(BaseModel):
    """退款撤销请求"""

    refund_id: int = Field(..., ge=1)
