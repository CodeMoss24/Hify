"""Refund module ORM model"""
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class RefundApplicationModel(Base):
    """退款申请 ORM 模型

    表名：tb_refund_application
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_refund_application"

    order_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="订单号")
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="用户ID")
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="退款金额(分)")
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="", comment="退款原因")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", comment="PENDING/APPROVED/PROCESSING/COMPLETED/REJECTED")
    reject_reason: Mapped[str] = mapped_column(String(512), nullable=False, default="", comment="拒绝原因")
