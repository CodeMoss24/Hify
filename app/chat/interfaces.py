"""Chat module interfaces - define service contracts for Layer 4"""
from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator


class IConversationService(ABC):
    """Conversation service interface"""

    @abstractmethod
    async def create_conversation(self, agent_id: int, user_id: int) -> "ConversationResponse":
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: int) -> Optional["ConversationResponse"]:
        pass

    @abstractmethod
    async def list_conversations(self, agent_id: Optional[int], user_id: Optional[int], page: int, page_size: int) -> "PageResult[ConversationResponse]":
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: int) -> bool:
        pass


class IMessageService(ABC):
    """Message service interface"""

    @abstractmethod
    async def create_message(self, conversation_id: int, data: "MessageCreate") -> "MessageResponse":
        pass

    @abstractmethod
    async def get_message(self, message_id: int) -> Optional["MessageResponse"]:
        pass

    @abstractmethod
    async def list_messages(self, conversation_id: int, page: int, page_size: int) -> "PageResult[MessageResponse]":
        pass

    @abstractmethod
    async def stream_chat(self, conversation_id: int, message: str) -> AsyncIterator[str]:
        pass