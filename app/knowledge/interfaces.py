"""Knowledge module interfaces - define service contracts for Layer 1"""
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy.orm import Session

from app.common.response import PageResult


class IKnowledgeBaseService(ABC):
    """Knowledge base service interface - exposed to Layer 2/3 modules"""

    @abstractmethod
    async def create_knowledge_base(self, db: Session, data: "KnowledgeBaseCreate") -> "KnowledgeBaseResponse":
        pass

    @abstractmethod
    async def list_knowledge_bases(
        self, db: Session, page: int = 1, page_size: int = 20, name: Optional[str] = None
    ) -> "PageResult":
        pass

    @abstractmethod
    async def get_knowledge_base(self, db: Session, kb_id: int) -> "KnowledgeBaseResponse":
        pass

    @abstractmethod
    async def update_knowledge_base(
        self, db: Session, kb_id: int, data: "KnowledgeBaseUpdate"
    ) -> "KnowledgeBaseResponse":
        pass

    @abstractmethod
    async def delete_knowledge_base(self, db: Session, kb_id: int) -> None:
        pass


class IDocumentService(ABC):
    """Document service interface"""

    @abstractmethod
    async def upload_document(
        self, db: Session, kb_id: int, file_name: str, file_type: str, file_size: int, file_path: str
    ) -> "DocumentResponse":
        pass

    @abstractmethod
    async def list_documents(
        self, db: Session, kb_id: int, page: int = 1, page_size: int = 20
    ) -> "PageResult":
        pass

    @abstractmethod
    async def get_document(self, db: Session, doc_id: int) -> "DocumentResponse":
        pass

    @abstractmethod
    async def delete_document(self, db: Session, doc_id: int) -> None:
        pass


class IDocumentChunkService(ABC):
    """Document chunk service interface"""

    @abstractmethod
    async def get_chunks(self, db: Session, doc_id: int, page: int, page_size: int) -> "PageResult":
        pass

    @abstractmethod
    async def search_chunks(self, db: Session, kb_id: int, query: str, top_k: int) -> list:
        pass


# Import schemas for type annotations to avoid circular imports
from app.knowledge.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse,
    DocumentResponse, DocumentChunkResponse,
)
