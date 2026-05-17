"""Chat 模块 ORM 模型"""
from sqlalchemy import BigInteger, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class ConversationModel(Base):
    """会话 ORM 模型

    表名：tb_conversation
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_conversation"

    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Agent id")
    title: Mapped[str] = mapped_column(
        String(128), nullable=False, default="新对话", comment="会话标题"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", comment="ACTIVE/ARCHIVED"
    )


class MessageModel(Base):
    """消息 ORM 模型

    表名：tb_message
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_message"

    conversation_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="会话 id")
    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="user/assistant/system")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    finish_reason: Mapped[str] = mapped_column(
        String(20), nullable=False, default="", comment="stop/length/error"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="响应耗时ms"
    )
