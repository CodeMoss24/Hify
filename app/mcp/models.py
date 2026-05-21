"""MCP 模块 ORM 模型"""
from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class McpServerModel(Base):
    """MCP 服务器 ORM 模型

    表名：tb_mcp_server
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_mcp_server"

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="服务器名称")
    url: Mapped[str] = mapped_column(String(256), nullable=False, comment="服务器 URL")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")


class McpToolModel(Base):
    """MCP 工具 ORM 模型

    表名：tb_mcp_tool
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_mcp_tool"

    server_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="服务器 id")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="工具名称")
    description: Mapped[str] = mapped_column(
        String(256), nullable=False, default="", comment="工具描述"
    )
    input_schema: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="工具输入参数 JSON schema"
    )
