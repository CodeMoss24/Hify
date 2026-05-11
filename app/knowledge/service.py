"""Knowledge service implementation"""
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService


class KnowledgeBaseService(IKnowledgeBaseService):
    """Knowledge base service implementation"""
    pass


class DocumentService(IDocumentService):
    """Document service implementation"""
    pass


class DocumentChunkService(IDocumentChunkService):
    """Document chunk service implementation"""
    pass