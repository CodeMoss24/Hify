"""Workflow 模块 ORM 模型"""
from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class WorkflowModel(Base):
    """Workflow ORM 模型

    表名：tb_workflow
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_workflow"

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="工作流名称")
    description: Mapped[str] = mapped_column(
        String(256), nullable=False, default="", comment="描述"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT", comment="状态: DRAFT/ACTIVE"
    )


class WorkflowNodeModel(Base):
    """Workflow Node ORM 模型

    表名：tb_workflow_node
    """

    __tablename__ = "tb_workflow_node"

    workflow_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="工作流 id")
    node_key: Mapped[str] = mapped_column(String(32), nullable=False, comment="节点唯一标识")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="节点名称")
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="节点类型: START/END/LLM/CONDITION/API_CALL")
    config: Mapped[dict] = mapped_column(JSON, nullable=False, comment="节点配置 JSON")
    position_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="X 坐标")
    position_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Y 坐标")


class WorkflowEdgeModel(Base):
    """Workflow Edge ORM 模型

    表名：tb_workflow_edge
    """

    __tablename__ = "tb_workflow_edge"

    workflow_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="工作流 id")
    source_node_key: Mapped[str] = mapped_column(String(32), nullable=False, comment="源节点 key")
    target_node_key: Mapped[str] = mapped_column(String(32), nullable=False, comment="目标节点 key")
    condition: Mapped[str] = mapped_column(String(256), nullable=False, default="", comment="条件表达式")


class WorkflowRunModel(Base):
    """Workflow Run ORM 模型

    表名：tb_workflow_run
    """

    __tablename__ = "tb_workflow_run"

    workflow_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="工作流 id")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", comment="状态: PENDING/RUNNING/SUCCESS/FAILED")
    input: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="输入数据")
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="输出数据")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True, comment="错误信息")
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="耗时(毫秒)")
    started_at: Mapped[datetime | None] = mapped_column(nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True, comment="结束时间")


class WorkflowNodeRunModel(Base):
    """Workflow Node Run ORM 模型

    表名：tb_workflow_node_run
    """

    __tablename__ = "tb_workflow_node_run"

    workflow_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="工作流执行 id")
    node_key: Mapped[str] = mapped_column(String(32), nullable=False, comment="节点 key")
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="节点类型")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", comment="状态: PENDING/RUNNING/SUCCESS/FAILED")
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="输入数据")
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="输出数据")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True, comment="错误信息")
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="耗时(毫秒)")
    started_at: Mapped[datetime | None] = mapped_column(nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True, comment="结束时间")
