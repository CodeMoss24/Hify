"""Agent Pydantic DTO"""
from typing import Optional

from pydantic import BaseModel, Field

from app.mcp.schemas import McpToolResponse


# ── 关联摘要 DTO（Agent 详情内联返回）──────────────────────


class KnowledgeBaseItem(BaseModel):
    """知识库摘要（Agent 详情内联）"""

    id: int
    name: str


# ── Agent CRUD DTOs ─────────────────────────────────────────


class AgentCreate(BaseModel):
    """创建 Agent 的请求 DTO"""

    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(default="", max_length=500)
    model_id: int = Field(..., ge=1)
    workflow_id: Optional[int] = Field(default=None)
    system_prompt: str = Field(default="")
    temperature: float = Field(default=0.70, ge=0.00, le=1.00)
    max_tokens: int = Field(default=2048, ge=1)
    max_context_turns: int = Field(default=10, ge=1)
    enabled: int = Field(default=1)
    knowledge_base_id: Optional[int] = Field(default=None)


class AgentUpdate(BaseModel):
    """更新 Agent 的请求 DTO，所有字段 Optional"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=500)
    model_id: Optional[int] = Field(default=None, ge=1)
    workflow_id: Optional[int] = Field(default=None)
    system_prompt: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None, ge=0.00, le=1.00)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    max_context_turns: Optional[int] = Field(default=None, ge=1)
    enabled: Optional[int] = Field(default=None)
    knowledge_base_id: Optional[int] = Field(default=None)


class AgentResponse(BaseModel):
    """Agent 响应 DTO"""

    id: int
    name: str
    description: str
    model_id: int
    workflow_id: int | None
    system_prompt: str
    temperature: float
    max_tokens: int
    max_context_turns: int
    enabled: int
    knowledge_bases: list[KnowledgeBaseItem] = []
    tools: list[McpToolResponse] = []
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(
        cls,
        model,
        knowledge_bases: list[KnowledgeBaseItem] | None = None,
        tools: list[McpToolResponse] | None = None,
    ) -> "AgentResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            name=model.name,
            description=model.description or "",
            model_id=model.model_id,
            workflow_id=model.workflow_id if hasattr(model, "workflow_id") else None,
            system_prompt=model.system_prompt or "",
            temperature=float(model.temperature) if model.temperature is not None else 0.70,
            max_tokens=model.max_tokens or 2048,
            max_context_turns=model.max_context_turns or 10,
            enabled=model.enabled or 1,
            knowledge_bases=knowledge_bases or [],
            tools=tools or [],
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )


# ── 绑定请求 DTOs ──────────────────────────────────────────


class BindKnowledgeBaseRequest(BaseModel):
    """绑定知识库请求"""

    knowledge_base_id: int = Field(..., ge=1)


class BindToolRequest(BaseModel):
    """绑定 MCP 工具请求"""

    mcp_tool_id: int = Field(..., ge=1)


class AgentToolBindRequest(BaseModel):
    """Agent 批量绑定 MCP 工具请求"""

    tool_ids: list[int] = Field(..., max_length=10)
