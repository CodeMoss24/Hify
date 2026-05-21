"""Knowledge API 路由"""
import os
import uuid
from fastapi import APIRouter, Depends, Query, Path, UploadFile, File
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.common.response import ApiResponse
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService
from app.knowledge.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse,
    DocumentResponse,
)
from app.knowledge.service import KnowledgeBaseService, DocumentService, DocumentChunkService, UPLOAD_DIR

router = APIRouter()


# ── KnowledgeBase 端点 ────────────────────────────────────────


@router.post("/knowledge-bases", response_model=ApiResponse)
async def create_knowledge_base(
    body: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """创建知识库"""
    kb_service: IKnowledgeBaseService = KnowledgeBaseService()
    kb = await kb_service.create_knowledge_base(db, body)
    return ApiResponse.ok(data=kb)


@router.get("/knowledge-bases", response_model=ApiResponse)
async def list_knowledge_bases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: str = Query(None, description="按名称模糊搜索"),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """分页查询知识库列表"""
    kb_service: IKnowledgeBaseService = KnowledgeBaseService()
    page_result = await kb_service.list_knowledge_bases(db, page, page_size, name)
    return ApiResponse.ok(data=page_result)


@router.get("/knowledge-bases/{kb_id}", response_model=ApiResponse)
async def get_knowledge_base(
    kb_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """查询单个知识库"""
    kb_service: IKnowledgeBaseService = KnowledgeBaseService()
    kb = await kb_service.get_knowledge_base(db, kb_id)
    return ApiResponse.ok(data=kb)


@router.put("/knowledge-bases/{kb_id}", response_model=ApiResponse)
async def update_knowledge_base(
    kb_id: int = Path(..., ge=1),
    body: KnowledgeBaseUpdate = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """更新知识库"""
    kb_service: IKnowledgeBaseService = KnowledgeBaseService()
    kb = await kb_service.update_knowledge_base(db, kb_id, body)
    return ApiResponse.ok(data=kb)


@router.delete("/knowledge-bases/{kb_id}", response_model=ApiResponse)
async def delete_knowledge_base(
    kb_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """删除知识库（逻辑删除），级联软删该知识库下的所有文档"""
    kb_service: IKnowledgeBaseService = KnowledgeBaseService()
    await kb_service.delete_knowledge_base(db, kb_id)
    return ApiResponse.ok(message="deleted")


# ── Document 端点 ───────────────────────────────────────────


@router.post("/knowledge-bases/{kb_id}/documents", response_model=ApiResponse)
async def upload_document(
    kb_id: int = Path(..., ge=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """上传文档到指定知识库，返回 documentId，状态为 pending"""
    # 获取文件信息
    file_name = file.filename or "unknown"
    # 获取文件类型
    file_ext = file_name.split(".")[-1].lower() if "." in file_name else "txt"

    # 读取文件内容获取大小
    content = await file.read()
    file_size = len(content)

    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 确保上传目录存在
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except OSError as e:
        raise BizException(ErrorCode.INTERNAL_ERROR, f"无法创建上传目录: {e}")

    # 保存文件
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except OSError as e:
        raise BizException(ErrorCode.INTERNAL_ERROR, f"无法保存文件: {e}")

    # 创建文档记录
    doc_service: IDocumentService = DocumentService()
    doc = await doc_service.upload_document(db, kb_id, file_name, file_ext, file_size, file_path)
    return ApiResponse.ok(data=doc)


@router.get("/knowledge-bases/{kb_id}/documents", response_model=ApiResponse)
async def list_documents(
    kb_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """分页查询指定知识库下的文档列表"""
    doc_service: IDocumentService = DocumentService()
    page_result = await doc_service.list_documents(db, kb_id, page, page_size)
    return ApiResponse.ok(data=page_result)


@router.get("/documents/{doc_id}", response_model=ApiResponse)
async def get_document(
    doc_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """查询单个文档详情"""
    doc_service: IDocumentService = DocumentService()
    doc = await doc_service.get_document(db, doc_id)
    return ApiResponse.ok(data=doc)


@router.delete("/documents/{doc_id}", response_model=ApiResponse)
async def delete_document(
    doc_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """删除文档（逻辑删除）"""
    doc_service: IDocumentService = DocumentService()
    await doc_service.delete_document(db, doc_id)
    return ApiResponse.ok(message="deleted")


@router.get("/documents/{doc_id}/chunks", response_model=ApiResponse)
async def list_document_chunks(
    doc_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """分页查询指定文档的分块列表"""
    chunk_service: IDocumentChunkService = DocumentChunkService()
    page_result = await chunk_service.get_chunks(db, doc_id, page, page_size)
    return ApiResponse.ok(data=page_result)
