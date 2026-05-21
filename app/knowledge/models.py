"""Knowledge 模块 ORM 模型"""
from sqlalchemy import String, Integer, BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class KnowledgeBaseModel(Base):
    """知识库 ORM 模型

    表名：tb_knowledge_base
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_knowledge_base"

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="知识库名称")
    description: Mapped[str] = mapped_column(String(256), nullable=False, default="", comment="知识库描述")


class DocumentModel(Base):
    """文档 ORM 模型

    表名：tb_document
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_document"

    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="知识库 id")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="文档名称")
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="文件大小字节")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", comment="状态：pending/processing/done/failed")
    error_message: Mapped[str] = mapped_column(String(512), nullable=False, default="", comment="处理失败时的错误信息")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="分块数量")


class DocumentChunkModel(Base):
    """文档分块 ORM 模型

    表名：tb_document_chunk
    公共字段（id、created_at、updated_at、deleted）由 Base 直接提供
    """

    __tablename__ = "tb_document_chunk"

    document_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文档 id")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="文本内容")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="分块序号")
    vector_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", comment="Qdrant 向量 id")
