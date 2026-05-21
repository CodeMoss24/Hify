"""Knowledge service implementation"""
import logging
import os
import asyncio
from typing import Optional, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.common.database import paginate, to_page_result, SessionLocal
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.common.response import PageResult
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService
from app.knowledge.models import KnowledgeBaseModel, DocumentModel, DocumentChunkModel
from app.knowledge.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse,
    DocumentResponse, DocumentChunkResponse,
)
from app.knowledge.pipeline import DocumentPipeline, COLLECTION_NAME
from app.infrastructure.llm.llm_client import llm_client
from qdrant_client import QdrantClient
from app.common.config import QDRANT_HOST, QDRANT_PORT

logger = logging.getLogger(__name__)

# 允许的文件类型
ALLOWED_FILE_TYPES = ["txt", "md", "pdf"]
# 最大文件大小（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024
# 上传目录
UPLOAD_DIR = "uploads"
# 文档 ID 到文件路径的映射（临时方案）
_doc_path_map: Dict[int, str] = {}


class KnowledgeBaseService(IKnowledgeBaseService):
    """Knowledge base service - CRUD for knowledge bases"""

    async def create_knowledge_base(self, db: Session, data: KnowledgeBaseCreate) -> KnowledgeBaseResponse:
        """创建知识库"""
        if not data.name or len(data.name.strip()) == 0:
            raise BizException(ErrorCode.PARAM_ERROR, "知识库名称不能为空")

        model = KnowledgeBaseModel(
            name=data.name,
            description=data.description or "",
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return KnowledgeBaseResponse.from_orm(model)

    async def list_knowledge_bases(
        self, db: Session, page: int = 1, page_size: int = 20, name: Optional[str] = None
    ) -> PageResult:
        """分页查询知识库列表，支持按名称模糊搜索"""
        query = KnowledgeBaseModel.find_all(db)
        if name:
            query = query.filter(KnowledgeBaseModel.name.like(f"%{name}%"))
        items, total = paginate(query, page, page_size)

        # 批量查询每个知识库下的文档数量
        kb_ids = [item.id for item in items]
        count_map: Dict[int, int] = {}
        if kb_ids:
            rows = (
                db.query(DocumentModel.knowledge_base_id, func.count())
                .filter(DocumentModel.deleted == 0, DocumentModel.knowledge_base_id.in_(kb_ids))
                .group_by(DocumentModel.knowledge_base_id)
                .all()
            )
            count_map = {kb_id: cnt for kb_id, cnt in rows}

        dtos = [KnowledgeBaseResponse.from_orm(item, document_count=count_map.get(item.id, 0)) for item in items]
        return to_page_result(dtos, total, page, page_size)

    async def get_knowledge_base(self, db: Session, kb_id: int) -> KnowledgeBaseResponse:
        """查询单个知识库"""
        model = KnowledgeBaseModel.find_all(db).filter_by(id=kb_id).first()
        if not model:
            raise BizException(ErrorCode.KNOWLEDGE_BASE_NOT_FOUND)
        return KnowledgeBaseResponse.from_orm(model)

    async def update_knowledge_base(
        self, db: Session, kb_id: int, data: KnowledgeBaseUpdate
    ) -> KnowledgeBaseResponse:
        """更新知识库，只改非空字段"""
        model = KnowledgeBaseModel.find_all(db).filter_by(id=kb_id).first()
        if not model:
            raise BizException(ErrorCode.KNOWLEDGE_BASE_NOT_FOUND)
        if data.name is not None:
            model.name = data.name
        if data.description is not None:
            model.description = data.description
        db.commit()
        db.refresh(model)
        return KnowledgeBaseResponse.from_orm(model)

    async def delete_knowledge_base(self, db: Session, kb_id: int) -> None:
        """删除知识库（逻辑删除），并级联软删该知识库下的所有文档"""
        model = KnowledgeBaseModel.find_all(db).filter_by(id=kb_id).first()
        if not model:
            raise BizException(ErrorCode.KNOWLEDGE_BASE_NOT_FOUND)

        # 级联软删该知识库下的所有文档
        docs = DocumentModel.find_all(db).filter_by(knowledge_base_id=kb_id).all()
        for doc in docs:
            doc.soft_delete()

        # 软删知识库
        model.soft_delete()
        db.commit()


class DocumentService(IDocumentService):
    """Document service - CRUD for documents"""

    async def upload_document(
        self, db: Session, kb_id: int, file_name: str, file_type: str, file_size: int, file_path: str
    ) -> DocumentResponse:
        """上传文档，创建文档记录，状态为 pending，然后启动异步处理管线"""
        # 验证知识库存在
        kb = KnowledgeBaseModel.find_all(db).filter_by(id=kb_id).first()
        if not kb:
            raise BizException(ErrorCode.KNOWLEDGE_BASE_NOT_FOUND)

        # 验证文件类型
        if file_type not in ALLOWED_FILE_TYPES:
            raise BizException(ErrorCode.PARAM_ERROR, f"不支持的文件类型，仅支持：{', '.join(ALLOWED_FILE_TYPES)}")

        # 验证文件大小
        if file_size > MAX_FILE_SIZE:
            raise BizException(ErrorCode.PARAM_ERROR, f"文件大小不能超过 {MAX_FILE_SIZE // (1024*1024)}MB")

        # 确保上传目录存在
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # 创建文档记录
        model = DocumentModel(
            knowledge_base_id=kb_id,
            name=file_name,
            size=file_size,
            status="pending",
        )
        db.add(model)
        db.commit()
        db.refresh(model)

        # 保存文件路径映射
        _doc_path_map[model.id] = file_path

        # 创建新的 Session 给异步任务
        async def run_pipeline():
            new_db = None
            try:
                new_db = SessionLocal()
                pipeline = DocumentPipeline()
                # 存储文件路径到 pipeline（临时方案）
                pipeline._doc_path_map = _doc_path_map
                await pipeline.run(new_db, model.id)
            except Exception as e:
                logger.exception(f"文档处理管线异常: {model.id}")
            finally:
                if new_db is not None:
                    try:
                        new_db.close()
                    except Exception:
                        pass

        # 启动异步任务
        asyncio.create_task(run_pipeline())

        return DocumentResponse.from_orm(model)

    async def list_documents(
        self, db: Session, kb_id: int, page: int = 1, page_size: int = 20
    ) -> PageResult:
        """分页查询指定知识库下的文档列表"""
        query = DocumentModel.find_all(db).filter_by(knowledge_base_id=kb_id)
        items, total = paginate(query, page, page_size)
        dtos = [DocumentResponse.from_orm(item) for item in items]
        return to_page_result(dtos, total, page, page_size)

    async def get_document(self, db: Session, doc_id: int) -> DocumentResponse:
        """查询单个文档"""
        model = DocumentModel.find_all(db).filter_by(id=doc_id).first()
        if not model:
            raise BizException(ErrorCode.DOCUMENT_NOT_FOUND)
        return DocumentResponse.from_orm(model)

    async def delete_document(self, db: Session, doc_id: int) -> None:
        """删除文档（逻辑删除）"""
        model = DocumentModel.find_all(db).filter_by(id=doc_id).first()
        if not model:
            raise BizException(ErrorCode.DOCUMENT_NOT_FOUND)
        model.soft_delete()
        db.commit()


class DocumentChunkService(IDocumentChunkService):
    """Document chunk service - 暂未实现"""

    async def get_chunks(self, db: Session, doc_id: int, page: int, page_size: int) -> PageResult:
        """分页查询指定文档下的分块列表"""
        doc = DocumentModel.find_all(db).filter_by(id=doc_id).first()
        if not doc:
            raise BizException(ErrorCode.DOCUMENT_NOT_FOUND)
        query = DocumentChunkModel.find_all(db).filter_by(document_id=doc_id).order_by(DocumentChunkModel.chunk_index)
        items, total = paginate(query, page, page_size)
        dtos = [DocumentChunkResponse.from_orm(item) for item in items]
        return to_page_result(dtos, total, page, page_size)

    async def search_chunks(self, db: Session, kb_id: int, query: str, top_k: int) -> list:
        """基于用户查询做向量检索，返回匹配的 chunk 列表"""
        # 生成查询向量
        embeddings = await llm_client.embed([query])
        if not embeddings or not embeddings[0]:
            return []

        query_vector = embeddings[0]

        # 调 Qdrant 检索
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        hits = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=0.3,
            query_filter={
                "must": [
                    {"key": "knowledge_base_id", "match": {"value": kb_id}}
                ]
            },
        )

        results = []
        for hit in hits:
            results.append({
                "content": hit.payload.get("content", ""),
                "score": hit.score,
                "document_id": hit.payload.get("document_id"),
                "chunk_index": hit.payload.get("chunk_index"),
            })
        return results
