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
    async def get_knowledge_base(self, db: Session, kb_id: int) -> Optional["KnowledgeBaseResponse"]:
        pass

    @abstractmethod
    async def list_knowledge_bases(self, db: Session, page: int, page_size: int) -> "PageResult[KnowledgeBaseResponse]":
        pass

    @abstractmethod
    async def update_knowledge_base(self, db: Session, kb_id: int, data: "KnowledgeBaseUpdate") -> Optional["KnowledgeBaseResponse"]:
        pass

    @abstractmethod
    async def delete_knowledge_base(self, db: Session, kb_id: int) -> bool:
        pass


class IDocumentService(ABC):
    """Document service interface"""

    @abstractmethod
    async def create_document(self, db: Session, kb_id: int, data: "DocumentCreate") -> "DocumentResponse":
        pass

    @abstractmethod
    async def get_document(self, db: Session, doc_id: int) -> Optional["DocumentResponse"]:
        pass

    @abstractmethod
    async def list_documents(self, db: Session, kb_id: Optional[int], page: int, page_size: int) -> "PageResult[DocumentResponse]":
        pass

    @abstractmethod
    async def update_document(self, db: Session, doc_id: int, data: "DocumentUpdate") -> Optional["DocumentResponse"]:
        pass

    @abstractmethod
    async def delete_document(self, db: Session, doc_id: int) -> bool:
        pass

    @abstractmethod
    async def upload_document(self, db: Session, kb_id: int, file_name: str, content: bytes) -> "DocumentResponse":
        pass


class IDocumentChunkService(ABC):
    """Document chunk service interface"""

    @abstractmethod
    async def get_chunks(self, db: Session, doc_id: int, page: int, page_size: int) -> "PageResult[DocumentChunkResponse]":
        pass

    @abstractmethod
    async def search_chunks(self, db: Session, kb_id: int, query: str, top_k: int) -> list["DocumentChunkResponse"]:
        pass
