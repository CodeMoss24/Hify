"""Provider 模块 ORM 模型"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class ProviderModel(Base):
    """模型提供商 ORM 模型

    表名：tb_model_provider
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_model_provider"

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="Provider name")
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="openai/anthropic/gemini/ollama")
    base_url: Mapped[str] = mapped_column(String(256), nullable=False, comment="API Base URL")
    api_key: Mapped[str] = mapped_column(String(256), nullable=False, default="", comment="API Key")
