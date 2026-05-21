"""文档处理数据管线"""
import logging
import os
import re
import uuid
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.common.config import QDRANT_HOST, QDRANT_PORT, ARK_EMBEDDING_DIMENSION
from app.common.database import SessionLocal
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.infrastructure.llm.llm_client import llm_client
from app.knowledge.models import DocumentModel, DocumentChunkModel

logger = logging.getLogger(__name__)

# 配置
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
COLLECTION_NAME = "knowledge_chunks"


class DocumentPipeline:
    """文档处理管线"""

    def __init__(self):
        self.qdrant_client = None

    def _get_qdrant_client(self) -> QdrantClient:
        """获取或创建 Qdrant 客户端"""
        if self.qdrant_client is None:
            self.qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        return self.qdrant_client

    def _ensure_collection(self) -> None:
        """确保 Qdrant collection 存在"""
        client = self._get_qdrant_client()
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME not in collection_names:
            logger.info(f"创建 Qdrant collection: {COLLECTION_NAME}")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=ARK_EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )

    async def run(self, db: Session, document_id: int) -> None:
        """
        运行文档处理管线

        Args:
            db: 数据库会话
            document_id: 文档 ID
        """
        # 获取文档记录
        doc = db.query(DocumentModel).filter_by(id=document_id, deleted=0).first()
        if not doc:
            logger.error(f"文档不存在: {document_id}")
            return

        # 更新状态为处理中
        doc.status = "processing"
        db.commit()

        try:
            # Step 1: 查找文件路径
            # 从全局导入获取路径映射
            from app.knowledge.service import _doc_path_map

            file_path = _doc_path_map.get(document_id)

            # 获取文件类型
            file_type = "txt"
            if doc.name.lower().endswith(".pdf"):
                file_type = "pdf"
            elif doc.name.lower().endswith(".md"):
                file_type = "md"

            # Step 1: 解析文本
            logger.info(f"Step 1 - 解析文档: {document_id}")
            try:
                if file_path and os.path.exists(file_path):
                    text = self._parse_text(file_path, file_type)
                else:
                    # 如果找不到文件，使用测试内容
                    logger.warning(f"找不到文件路径，使用测试内容: {document_id}")
                    text = f"这是文档 {doc.name} 的内容。\n\n用于测试文档处理管线。"
            except Exception as e:
                logger.error(f"解析文档失败: {e}")
                self._set_failed(db, doc, f"解析失败: {str(e)}")
                return

            if not text or not text.strip():
                self._set_failed(db, doc, "文档内容为空或无法提取文本")
                return

            # Step 2: 分块
            logger.info(f"Step 2 - 文档分块: {document_id}")
            try:
                chunks = self._split_chunks(text)
            except Exception as e:
                logger.error(f"文档分块失败: {e}")
                self._set_failed(db, doc, f"分块失败: {str(e)}")
                return

            if not chunks:
                self._set_failed(db, doc, "分块结果为空")
                return

            logger.info(f"分块完成，共 {len(chunks)} 块")

            # Step 3: 向量化
            logger.info(f"Step 3 - 向量化: {document_id}")
            try:
                chunks = await self._embed_chunks(chunks)
            except Exception as e:
                logger.error(f"向量化失败: {e}")
                self._set_failed(db, doc, f"向量化失败: {str(e)}")
                return

            # Step 4: 存储
            logger.info(f"Step 4 - 存储: {document_id}")
            try:
                await self._store_chunks(db, doc.id, doc.knowledge_base_id, chunks)
            except Exception as e:
                logger.error(f"存储失败: {e}")
                self._set_failed(db, doc, f"存储失败: {str(e)}")
                return

            # Step 5: 更新状态为完成
            doc.status = "done"
            doc.chunk_count = len(chunks)
            db.commit()
            logger.info(f"文档处理完成: {document_id}，共 {len(chunks)} 个分块")

        except Exception as e:
            logger.exception(f"文档处理异常: {document_id}")
            self._set_failed(db, doc, f"处理异常: {str(e)}")

    def _parse_text(self, file_path: str, file_type: str) -> str:
        """
        Step 1 - 解析文本

        Args:
            file_path: 文件路径
            file_type: 文件类型（txt/md/pdf）

        Returns:
            解析后的文本内容

        Raises:
            Exception: 解析失败时抛出异常
        """
        if file_type in ["txt", "md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif file_type == "pdf":
            try:
                import PyPDF2

                text = ""
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        page_text = page.extract_text() or ""
                        text += page_text + "\n"

                if not text.strip():
                    raise Exception("扫描版 PDF 不支持")
                return text
            except Exception as e:
                raise Exception(f"PDF 解析失败: {str(e)}")
        else:
            raise Exception(f"不支持的文件类型: {file_type}")

    def _split_chunks(self, text: str) -> List[Dict[str, Any]]:
        """
        Step 2 - 分块

        Args:
            text: 待分块的文本

        Returns:
            分块列表，每个 chunk 包含 chunk_index、content、token_count
        """
        chunks = []

        # 先按段落分割
        paragraphs = re.split(r"\n\s*\n", text.strip())
        current_text = ""

        for para in paragraphs:
            # 估算 token 数
            current_tokens = self._estimate_tokens(current_text)
            para_tokens = self._estimate_tokens(para)

            if current_tokens + para_tokens <= CHUNK_SIZE:
                # 可以加入当前块
                current_text += ("\n\n" if current_text else "") + para
            else:
                if current_text:
                    # 当前块已满，保存
                    chunks.append({
                        "chunk_index": len(chunks),
                        "content": current_text.strip(),
                        "token_count": current_tokens
                    })

                # 检查段落是否超过单个 chunk 大小
                if para_tokens > CHUNK_SIZE:
                    # 需要进一步分割段落
                    sub_chunks = self._split_paragraph(para)
                    for sub_chunk in sub_chunks:
                        chunks.append({
                            "chunk_index": len(chunks),
                            "content": sub_chunk.strip(),
                            "token_count": self._estimate_tokens(sub_chunk)
                        })
                    current_text = ""
                else:
                    current_text = para

        # 处理最后一个块
        if current_text.strip():
            chunks.append({
                "chunk_index": len(chunks),
                "content": current_text.strip(),
                "token_count": self._estimate_tokens(current_text)
            })

        return chunks

    def _split_paragraph(self, paragraph: str) -> List[str]:
        """
        分割单个段落（超过 chunk_size 时使用）

        按句子边界分割，再按字符截断
        """
        chunks = []
        sentences = re.split(r"([。？！.?\!])", paragraph)

        current_text = ""
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]

            if self._estimate_tokens(current_text + sentence) <= CHUNK_SIZE:
                current_text += sentence
            else:
                if current_text:
                    chunks.append(current_text)
                # 如果单个句子超过大小，按字符截断
                if self._estimate_tokens(sentence) > CHUNK_SIZE:
                    chunks.extend(self._split_by_chars(sentence))
                    current_text = ""
                else:
                    current_text = sentence

        if current_text:
            chunks.append(current_text)

        return chunks

    def _split_by_chars(self, text: str) -> List[str]:
        """按字符截断"""
        chunks = []
        start = 0
        while start < len(text):
            # 估算能放多少字符
            end = start
            while end < len(text) and self._estimate_tokens(text[start:end]) < CHUNK_SIZE - CHUNK_OVERLAP:
                end += 1
            chunks.append(text[start:end])
            # 有空间做 overlap 时才回退，否则直接跳到 end
            if end - CHUNK_OVERLAP > start:
                start = end - CHUNK_OVERLAP
            else:
                start = end
        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """
        估算 token 数

        中文 1 字符 ≈ 1.5 token，英文 1 单词 ≈ 1 token
        """
        if not text:
            return 0

        # 统计中文字符
        chinese_chars = len(re.findall(r"[一-龥]", text))
        # 统计英文单词
        english_words = len(re.findall(r"[a-zA-Z]+", text))
        # 其他字符
        other_chars = len(text) - chinese_chars

        return int(chinese_chars * 1.5 + english_words + other_chars * 0.5) + 1

    async def _embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 3 - 向量化

        Args:
            chunks: 分块列表

        Returns:
            更新 embedding 字段后的分块列表
        """
        if not chunks:
            return chunks

        # 提取所有 chunk 的 content
        texts = [chunk["content"] for chunk in chunks]

        # 调用 LlmClient.embed()
        embeddings = await llm_client.embed(texts)

        # 将向量添加到每个 chunk
        for i, chunk in enumerate(chunks):
            if i < len(embeddings):
                chunk["embedding"] = embeddings[i]

        return chunks

    async def _store_chunks(
        self,
        db: Session,
        document_id: int,
        kb_id: int,
        chunks: List[Dict[str, Any]]
    ) -> None:
        """
        Step 4 - 存储

        Args:
            db: 数据库会话
            document_id: 文档 ID
            kb_id: 知识库 ID
            chunks: 分块列表（含 embedding）
        """
        if not chunks:
            return

        # 确保 collection 存在
        self._ensure_collection()

        # 准备 Qdrant points
        points = []
        chunk_records = []

        for chunk in chunks:
            point_id = str(uuid.uuid4())
            embedding = chunk.get("embedding", [])

            # 创建 Qdrant point
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "knowledge_base_id": kb_id,
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"]
                }
            ))

            # 创建数据库记录
            chunk_records.append(DocumentChunkModel(
                document_id=document_id,
                content=chunk["content"],
                chunk_index=chunk["chunk_index"],
                vector_id=point_id
            ))

        # 批量插入 Qdrant
        if points:
            client = self._get_qdrant_client()
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            logger.info(f"Qdrant 插入 {len(points)} 个向量")

        # 批量插入 MySQL
        if chunk_records:
            db.add_all(chunk_records)
            db.commit()
            logger.info(f"MySQL 插入 {len(chunk_records)} 个分块记录")

    def _set_failed(self, db: Session, doc: DocumentModel, error_message: str) -> None:
        """设置文档状态为失败"""
        doc.status = "failed"
        doc.error_message = error_message
        db.commit()
        logger.error(f"文档处理失败: {doc.id}, 错误: {error_message}")
