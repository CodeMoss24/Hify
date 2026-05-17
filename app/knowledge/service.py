"""Knowledge service implementation"""
import logging

from sqlalchemy.orm import Session

from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.common.response import PageResult
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService

logger = logging.getLogger(__name__)


class KnowledgeBaseService(IKnowledgeBaseService):
    """Knowledge base service - stub implementation"""

    async def create_knowledge_base(self, db: Session, data) -> any:
        raise NotImplementedError("Knowledge module not implemented")

    async def get_knowledge_base(self, db: Session, kb_id: int):
        raise BizException(ErrorCode.KNOWLEDGE_BASE_NOT_FOUND)

    async def list_knowledge_bases(self, db: Session, page: int, page_size: int) -> PageResult:
        raise NotImplementedError("Knowledge module not implemented")

    async def update_knowledge_base(self, db: Session, kb_id: int, data):
        raise NotImplementedError("Knowledge module not implemented")

    async def delete_knowledge_base(self, db: Session, kb_id: int) -> bool:
        raise NotImplementedError("Knowledge module not implemented")


class DocumentService(IDocumentService):
    """Document service - stub implementation"""

    async def create_document(self, db: Session, kb_id: int, data):
        raise NotImplementedError("Knowledge module not implemented")

    async def get_document(self, db: Session, doc_id: int):
        raise NotImplementedError("Knowledge module not implemented")

    async def list_documents(self, db: Session, kb_id, page: int, page_size: int) -> PageResult:
        raise NotImplementedError("Knowledge module not implemented")

    async def update_document(self, db: Session, doc_id: int, data):
        raise NotImplementedError("Knowledge module not implemented")

    async def delete_document(self, db: Session, doc_id: int) -> bool:
        raise NotImplementedError("Knowledge module not implemented")

    async def upload_document(self, db: Session, kb_id: int, file_name: str, content: bytes):
        raise NotImplementedError("Knowledge module not implemented")


class DocumentChunkService(IDocumentChunkService):
    """Document chunk service - stub implementation"""

    async def get_chunks(self, db: Session, doc_id: int, page: int, page_size: int) -> PageResult:
        raise NotImplementedError("Knowledge module not implemented")

    async def search_chunks(self, db: Session, kb_id: int, query: str, top_k: int) -> list:
        raise NotImplementedError("Knowledge module not implemented")
