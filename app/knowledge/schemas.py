"""Knowledge Pydantic DTO"""
from typing import Optional

from pydantic import BaseModel, Field


# ── KnowledgeBase DTOs ─────────────────────────────────────────


class KnowledgeBaseCreate(BaseModel):
    """创建知识库的请求 DTO"""

    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(default="", max_length=256)


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库的请求 DTO，所有字段 Optional"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=256)


class KnowledgeBaseResponse(BaseModel):
    """知识库响应 DTO"""

    id: int
    name: str
    description: str
    document_count: int = 0
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, model, document_count: int = 0) -> "KnowledgeBaseResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            document_count=document_count,
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )


# ── Document DTOs ────────────────────────────────────────────


class DocumentResponse(BaseModel):
    """文档响应 DTO"""

    id: int
    knowledge_base_id: int
    name: str
    size: int
    status: str
    error_message: str = ""
    chunk_count: int = 0
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, model) -> "DocumentResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            knowledge_base_id=model.knowledge_base_id,
            name=model.name,
            size=model.size,
            status=model.status,
            error_message=model.error_message,
            chunk_count=model.chunk_count,
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )


# ── DocumentChunk DTOs ───────────────────────────────────────


class DocumentChunkResponse(BaseModel):
    """文档分块响应 DTO"""

    id: int
    document_id: int
    content: str
    chunk_index: int
    vector_id: str
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, model) -> "DocumentChunkResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            document_id=model.document_id,
            content=model.content,
            chunk_index=model.chunk_index,
            vector_id=model.vector_id,
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )
