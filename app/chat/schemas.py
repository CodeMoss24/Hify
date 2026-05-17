"""Chat Pydantic DTO"""
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """创建会话的请求 DTO"""

    agent_id: int = Field(..., ge=1)


class ConversationResponse(BaseModel):
    """会话响应 DTO"""

    id: int
    agent_id: int
    title: str
    status: str
    created_at: str
    updated_at: str
    last_message: str = ""

    @classmethod
    def from_orm(cls, model, last_message_text: str = "") -> "ConversationResponse":
        """ORM 模型转 DTO"""
        # 安全地获取所有属性
        id_val = getattr(model, "id", 0)
        agent_id_val = getattr(model, "agent_id", 0)
        title_val = getattr(model, "title", "新对话")
        status_val = getattr(model, "status", "ACTIVE")
        created_at_val = getattr(model, "created_at", None)
        updated_at_val = getattr(model, "updated_at", None)

        created_at_str = ""
        if created_at_val is not None and hasattr(created_at_val, "isoformat"):
            created_at_str = created_at_val.isoformat()

        updated_at_str = ""
        if updated_at_val is not None and hasattr(updated_at_val, "isoformat"):
            updated_at_str = updated_at_val.isoformat()

        return cls(
            id=id_val,
            agent_id=agent_id_val,
            title=title_val,
            status=status_val,
            created_at=created_at_str,
            updated_at=updated_at_str,
            last_message=last_message_text,
        )


class MessageResponse(BaseModel):
    """消息响应 DTO"""

    id: int
    conversation_id: int
    role: str
    content: str
    finish_reason: str
    latency_ms: int
    created_at: str

    @classmethod
    def from_orm(cls, model) -> "MessageResponse":
        """ORM 模型转 DTO"""
        # 安全地获取所有属性
        id_val = getattr(model, "id", 0)
        conversation_id_val = getattr(model, "conversation_id", 0)
        role_val = getattr(model, "role", "user")
        content_val = getattr(model, "content", "")
        finish_reason_val = getattr(model, "finish_reason", "")
        latency_ms_val = getattr(model, "latency_ms", 0)
        created_at_val = getattr(model, "created_at", None)

        created_at_str = ""
        if created_at_val is not None and hasattr(created_at_val, "isoformat"):
            created_at_str = created_at_val.isoformat()

        return cls(
            id=id_val,
            conversation_id=conversation_id_val,
            role=role_val,
            content=content_val,
            finish_reason=finish_reason_val,
            latency_ms=latency_ms_val,
            created_at=created_at_str,
        )


class ChatRequest(BaseModel):
    """对话请求 DTO"""

    content: str = Field(..., min_length=1)
    stream: bool = Field(default=True)
