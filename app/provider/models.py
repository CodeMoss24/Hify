"""Provider 模块 ORM 模型"""
from sqlalchemy import JSON, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class ProviderModel(Base):
    """模型提供商 ORM 模型

    表名：tb_model_provider
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_model_provider"

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="Provider 展示名称")
    provider_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="openai/anthropic/openai_compatible/ollama"
    )
    base_url: Mapped[str] = mapped_column(String(256), nullable=False, comment="API Base URL")
    api_key: Mapped[str] = mapped_column(String(512), nullable=False, default="", comment="API Key")
    extra_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None, comment="差异配置(anthropic_version, custom_headers等)"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="enabled", comment="enabled/disabled 用户控制"
    )


class ModelModel(Base):
    """模型 ORM 模型

    表名：tb_model
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_model"

    provider_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="关联 provider id")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="展示名称")
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="API 调用标识(如 gpt-4o)")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="enabled", comment="enabled/disabled"
    )
    capabilities: Mapped[str] = mapped_column(
        String(256), nullable=False, default="", comment="能力标签(逗号分隔: streaming,tool_use,thinking)"
    )


class ProviderHealthLogModel(Base):
    """Provider 健康状态变更日志 ORM 模型

    表名：tb_provider_health_log
    只在健康状态切换时写入，高频心跳数据存 Redis 不落盘
    """

    __tablename__ = "tb_provider_health_log"

    provider_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="Provider id")
    prev_status: Mapped[str] = mapped_column(String(16), nullable=False, comment="变更前状态")
    curr_status: Mapped[str] = mapped_column(String(16), nullable=False, comment="变更后状态")
    error_message: Mapped[str] = mapped_column(
        String(512), nullable=False, default="", comment="错误信息"
    )
    response_time_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="响应时间(ms)"
    )
