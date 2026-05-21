"""Workflow Pydantic DTO"""
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


# ── 节点配置 DTOs ──────────────────────────────────────────


class BaseNodeConfig(BaseModel):
    """节点配置基类"""
    pass


class StartNodeConfig(BaseNodeConfig):
    """START 节点配置（空配置）"""
    pass


class EndNodeConfig(BaseNodeConfig):
    """END 节点配置（空配置）"""
    pass


class LlmNodeConfig(BaseNodeConfig):
    """LLM 节点配置"""
    model_config_id: int = Field(..., description="模型配置 ID")
    prompt: str = Field(..., description="提示词模板")
    output_variable: str = Field(default="llm_output", description="输出变量名")


class ConditionNodeConfig(BaseNodeConfig):
    """CONDITION 节点配置"""
    expression: str = Field(..., description="条件表达式")
    output_variable: str = Field(default="condition_result", description="输出变量名")


class ApiCallNodeConfig(BaseNodeConfig):
    """API_CALL 节点配置"""
    url: str = Field(..., description="API URL")
    method: str = Field(default="GET", description="HTTP 方法")
    output_variable: str = Field(default="api_response", description="输出变量名")


# ── 节点/连线 DTOs ──────────────────────────────────────────


class WorkflowNodeCreate(BaseModel):
    """创建工作流节点的请求 DTO"""
    node_key: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=64)
    node_type: str = Field(..., min_length=1, max_length=32)
    config: Dict[str, Any] = Field(default_factory=dict)
    position_x: int = Field(default=0)
    position_y: int = Field(default=0)


class WorkflowNodeResponse(BaseModel):
    """工作流节点响应 DTO"""
    node_key: str
    name: str
    node_type: str
    config: Dict[str, Any]
    position_x: int
    position_y: int

    @classmethod
    def from_orm(cls, model) -> "WorkflowNodeResponse":
        """ORM 模型转 DTO"""
        return cls(
            node_key=model.node_key,
            name=model.name,
            node_type=model.node_type,
            config=model.config or {},
            position_x=model.position_x or 0,
            position_y=model.position_y or 0,
        )


class WorkflowEdgeCreate(BaseModel):
    """创建工作流连线的请求 DTO"""
    source_node_key: str = Field(..., min_length=1, max_length=32)
    target_node_key: str = Field(..., min_length=1, max_length=32)
    condition: Optional[str] = Field(default="", max_length=256)


class WorkflowEdgeResponse(BaseModel):
    """工作流连线响应 DTO"""
    source_node_key: str
    target_node_key: str
    condition: str

    @classmethod
    def from_orm(cls, model) -> "WorkflowEdgeResponse":
        """ORM 模型转 DTO"""
        return cls(
            source_node_key=model.source_node_key,
            target_node_key=model.target_node_key,
            condition=model.condition or "",
        )


# ── Workflow CRUD DTOs ──────────────────────────────────────


class WorkflowCreate(BaseModel):
    """创建工作流的请求 DTO"""
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(default="", max_length=256)
    nodes: list[WorkflowNodeCreate] = Field(default_factory=list)
    edges: list[WorkflowEdgeCreate] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    """更新工作流的请求 DTO，所有字段 Optional"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=256)
    status: Optional[str] = Field(default=None, max_length=20)
    nodes: Optional[list[WorkflowNodeCreate]] = Field(default=None)
    edges: Optional[list[WorkflowEdgeCreate]] = Field(default=None)


class WorkflowResponse(BaseModel):
    """工作流响应 DTO（含完整 nodes 和 edges）"""
    id: int
    name: str
    description: str
    status: str
    nodes: list[WorkflowNodeResponse]
    edges: list[WorkflowEdgeResponse]
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(
        cls,
        model,
        nodes: list[WorkflowNodeResponse] | None = None,
        edges: list[WorkflowEdgeResponse] | None = None,
    ) -> "WorkflowResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            name=model.name,
            description=model.description or "",
            status=model.status or "DRAFT",
            nodes=nodes or [],
            edges=edges or [],
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )
