"""Refund API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.response import ApiResponse
from app.refund.interfaces import IRefundService
from app.refund.schemas import RefundCheckRequest, RefundSubmitRequest, RefundCancelRequest
from app.refund.service import RefundService

router = APIRouter()


def _refund_service() -> IRefundService:
    return RefundService()


@router.post("/refund/check-eligibility", response_model=ApiResponse)
async def check_eligibility(
    body: RefundCheckRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """检查订单退款资格"""
    service = _refund_service()
    result = await service.check_eligibility(db, body.order_id)
    return ApiResponse.ok(data=result)


@router.post("/refund/submit", response_model=ApiResponse)
async def submit_refund(
    body: RefundSubmitRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """提交退款申请"""
    service = _refund_service()
    result = await service.submit_refund(db, body.order_id, body.user_id, body.amount, body.reason)
    return ApiResponse.ok(data=result)


@router.get("/refund/status", response_model=ApiResponse)
async def get_status(
    order_id: Optional[str] = Query(default=None),
    refund_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """查询退款状态"""
    service = _refund_service()
    result = await service.get_status(db, order_id=order_id, refund_id=refund_id)
    return ApiResponse.ok(data=result)


@router.post("/refund/cancel", response_model=ApiResponse)
async def cancel_refund(
    body: RefundCancelRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """撤销退款申请"""
    service = _refund_service()
    result = await service.cancel_refund(db, body.refund_id)
    return ApiResponse.ok(data=result)


@router.post("/refund/reset", response_model=ApiResponse)
async def reset_test_data(
    db: Session = Depends(get_db),
) -> ApiResponse:
    """清空退款表测试数据"""
    service = _refund_service()
    await service.reset_test_data(db)
    return ApiResponse.ok(message="已清空退款表数据")
