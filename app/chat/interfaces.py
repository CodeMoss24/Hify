"""Chat module interfaces - define service contracts for Layer 4"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from app.common.response import PageResult
from app.chat.schemas import ConversationCreate, ConversationResponse, MessageResponse


class IChatService(ABC):
    """Chat service interface - exposed to other modules"""

    @abstractmethod
    async def create_conversation(
        self, db: Session, agent_id: int
    ) -> ConversationResponse:
        """创建会话"""
        pass

    @abstractmethod
    async def list_conversations(
        self, db: Session, page: int = 1, page_size: int = 20
    ) -> PageResult:
        """分页查询会话列表"""
        pass

    @abstractmethod
    async def get_conversation(
        self, db: Session, conversation_id: int
    ) -> ConversationResponse:
        """查询单个会话详情"""
        pass

    @abstractmethod
    async def delete_conversation(self, db: Session, conversation_id: int) -> None:
        """删除会话（逻辑删除，级联软删消息）"""
        pass

    @abstractmethod
    async def send_message(
        self,
        db: Session,
        agent_id: int,
        content: str,
        conversation_id: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """发送消息（流式响应 SSE）"""
        pass

    @abstractmethod
    async def get_messages(
        self, db: Session, conversation_id: int, page: int = 1, page_size: int = 100
    ) -> PageResult[MessageResponse]:
        """分页查询会话历史消息"""
        pass
