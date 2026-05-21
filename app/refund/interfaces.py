"""Refund module interfaces - define service contracts"""
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy.orm import Session

from app.refund.schemas import (
    RefundEligibilityResponse,
    RefundSubmitResponse,
    RefundStatusResponse,
    RefundCancelResponse,
)


class IRefundService(ABC):
    """Refund service interface"""

    @abstractmethod
    async def check_eligibility(self, db: Session, order_id: str) -> RefundEligibilityResponse:
        """检查订单退款资格"""
        pass

    @abstractmethod
    async def submit_refund(
        self, db: Session, order_id: str, user_id: str, amount: int, reason: str
    ) -> RefundSubmitResponse:
        """提交退款申请"""
        pass

    @abstractmethod
    async def get_status(
        self, db: Session, order_id: Optional[str] = None, refund_id: Optional[int] = None
    ) -> RefundStatusResponse:
        """查询退款状态"""
        pass

    @abstractmethod
    async def cancel_refund(self, db: Session, refund_id: int) -> RefundCancelResponse:
        """撤销退款申请"""
        pass

    @abstractmethod
    async def reset_test_data(self, db: Session) -> None:
        """清空退款表测试数据"""
        pass
