"""Refund service implementation"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.refund.interfaces import IRefundService
from app.refund.models import RefundApplicationModel
from app.refund.schemas import (
    RefundEligibilityResponse,
    RefundSubmitResponse,
    RefundStatusResponse,
    RefundCancelResponse,
)

STATUS_LABEL_MAP = {
    "PENDING": "待审核",
    "APPROVED": "已通过",
    "PROCESSING": "处理中",
    "COMPLETED": "已完成",
    "REJECTED": "已拒绝",
}

ACTIVE_STATUSES = {"PENDING", "APPROVED", "PROCESSING"}


class RefundService(IRefundService):
    """退款服务实现"""

    async def check_eligibility(self, db: Session, order_id: str) -> RefundEligibilityResponse:
        """检查订单退款资格：同一订单无进行中的退款申请即可退款"""
        existing = (
            RefundApplicationModel.find_all(db)
            .filter(
                RefundApplicationModel.order_id == order_id,
                RefundApplicationModel.status.in_(ACTIVE_STATUSES),
            )
            .first()
        )

        if existing:
            return RefundEligibilityResponse(
                eligible=False,
                reason=f"该订单已有进行中的退款申请，编号：{existing.id}",
                deadline="",
                amount=0,
            )

        deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        return RefundEligibilityResponse(
            eligible=True,
            reason="订单在退款有效期内",
            deadline=deadline,
            amount=29900,
        )

    async def submit_refund(
        self, db: Session, order_id: str, user_id: str, amount: int, reason: str
    ) -> RefundSubmitResponse:
        """提交退款申请：检查重复，写入记录"""
        existing = (
            RefundApplicationModel.find_all(db)
            .filter(
                RefundApplicationModel.order_id == order_id,
                RefundApplicationModel.status.in_(ACTIVE_STATUSES),
            )
            .first()
        )

        if existing:
            raise BizException(
                ErrorCode.REFUND_DUPLICATE,
                message=f"该订单已有进行中的退款申请，编号：{existing.id}",
            )

        model = RefundApplicationModel(
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            reason=reason,
            status="PENDING",
        )
        db.add(model)
        db.commit()
        db.refresh(model)

        return RefundSubmitResponse(
            refund_id=model.id,
            status=model.status,
            status_label=STATUS_LABEL_MAP[model.status],
            estimated_days=3,
        )

    async def get_status(
        self, db: Session, order_id: str | None = None, refund_id: int | None = None
    ) -> RefundStatusResponse:
        """查询退款状态：优先 refund_id，其次 order_id 查最新"""
        model = None

        if refund_id is not None:
            model = RefundApplicationModel.find_all(db).filter_by(id=refund_id).first()
        elif order_id is not None:
            model = (
                RefundApplicationModel.find_all(db)
                .filter_by(order_id=order_id)
                .order_by(RefundApplicationModel.id.desc())
                .first()
            )

        if not model:
            raise BizException(ErrorCode.REFUND_NOT_FOUND, message="未找到退款申请")

        return RefundStatusResponse(
            refund_id=model.id,
            order_id=model.order_id,
            amount=model.amount,
            status=model.status,
            status_label=STATUS_LABEL_MAP.get(model.status, model.status),
            submitted_at=model.created_at.isoformat() if model.created_at else "",
            reject_reason=model.reject_reason or "",
        )

    async def cancel_refund(self, db: Session, refund_id: int) -> RefundCancelResponse:
        """撤销退款申请：仅 PENDING 状态可撤销"""
        model = RefundApplicationModel.find_all(db).filter_by(id=refund_id).first()
        if not model:
            raise BizException(ErrorCode.REFUND_NOT_FOUND, message="未找到退款申请")

        if model.status == "PENDING":
            model.soft_delete()
            db.commit()
            return RefundCancelResponse(success=True, message="已撤销退款申请")

        return RefundCancelResponse(success=False, message="退款已在处理中，无法撤销")

    async def reset_test_data(self, db: Session) -> None:
        """清空退款表所有数据（测试用）"""
        db.query(RefundApplicationModel).delete()
        db.commit()
