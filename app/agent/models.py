"""Agent 模块 ORM 模型"""
from sqlalchemy import BigInteger, String, Text, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class AgentModel(Base):
    """Agent ORM 模型

    表名：tb_agent
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_agent"

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="Agent 名称")
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", comment="描述"
    )
    model_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="关联模型 id")
    system_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="系统提示词"
    )
    temperature: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, default=0.70, comment="温度参数 0.00~1.00"
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2048, comment="最大生成 Token 数"
    )
    max_context_turns: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, comment="保留最近对话轮数"
    )
    enabled: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="0=禁用 1=启用"
    )


class AgentKnowledgeBaseModel(Base):
    """Agent 与知识库关联 ORM 模型

    表名：tb_agent_knowledge_base
    """

    __tablename__ = "tb_agent_knowledge_base"

    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Agent id")
    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="知识库 id")


class AgentToolModel(Base):
    """Agent 与 MCP 工具关联 ORM 模型

    表名：tb_agent_tool
    """

    __tablename__ = "tb_agent_tool"

    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Agent id")
    mcp_tool_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="MCP 工具 id")
