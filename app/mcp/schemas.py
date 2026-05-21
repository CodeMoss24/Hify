"""MCP Pydantic DTO"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── McpServer DTOs ─────────────────────────────────────────


class McpServerCreate(BaseModel):
    """创建 MCP Server 的请求 DTO"""

    name: str = Field(..., min_length=1, max_length=64)
    url: str = Field(..., min_length=1)
    enabled: Optional[bool] = True

    @field_validator("url")
    @classmethod
    def url_must_be_valid(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must be a valid URL")
        return v


class McpServerUpdate(BaseModel):
    """更新 MCP Server 的请求 DTO，所有字段 Optional"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    url: Optional[str] = Field(default=None, min_length=1)
    enabled: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def url_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("url must be a valid URL")
        return v


class McpServerResponse(BaseModel):
    """MCP Server 响应 DTO"""

    id: int
    name: str
    url: str
    enabled: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, model) -> "McpServerResponse":
        return cls(
            id=model.id,
            name=model.name,
            url=model.url,
            enabled=model.enabled,
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )


# ── McpTool DTOs ──────────────────────────────────────────


class McpToolResponse(BaseModel):
    """MCP Tool 响应 DTO"""

    id: int
    server_id: int
    name: str
    description: str
    input_schema: str

    @classmethod
    def from_orm(cls, model) -> "McpToolResponse":
        return cls(
            id=model.id,
            server_id=model.server_id,
            name=model.name,
            description=model.description,
            input_schema=model.input_schema,
        )


# ── ConnectionTestResult DTO ──────────────────────────────


class McpConnectionTestResult(BaseModel):
    """MCP 连通性测试结果"""

    success: bool
    tool_count: int = 0
    tools: list[McpToolResponse] = []
    error_message: str = ""


# ── Debug DTOs ──────────────────────────────────────────────


class McpDebugRequest(BaseModel):
    """MCP 工具调试请求"""

    tool_name: str = Field(..., min_length=1)
    arguments: dict = Field(default_factory=dict)


class McpDebugResult(BaseModel):
    """MCP 工具调试结果"""

    result: str
    elapsed_ms: int
