"""Chat service implementation"""
import logging
import time
import json
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from app.common.response import PageResult
from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.agent.interfaces import IAgentService
from app.provider.interfaces import IProviderService, IModelService
from app.provider.adapter_factory import provider_adapter_factory
from app.chat.interfaces import IChatService
from app.chat.models import ConversationModel, MessageModel
from app.chat.schemas import ConversationResponse, MessageResponse
from app.chat.context_manager import ContextManager
from app.provider.models import ProviderModel

logger = logging.getLogger(__name__)


class ChatService(IChatService):
    """Chat service - conversation CRUD + context management + send message"""

    def __init__(
        self,
        agent_service: IAgentService,
        model_service: IModelService,
        provider_service: IProviderService,
    ):
        self._agent_service = agent_service
        self._model_service = model_service
        self._provider_service = provider_service
        self._context_manager = ContextManager()

    def _get_last_message_text(self, db: Session, conversation_id: int) -> str:
        """获取会话最后一条消息的文本（截断到50字）"""
        last_msg = MessageModel.find_all(db).filter_by(
            conversation_id=conversation_id
        ).order_by(MessageModel.created_at.desc()).first()
        if last_msg:
            text = last_msg.content
            return text[:50] + "..." if len(text) > 50 else text
        return ""

    def _get_conversation_title(self, db: Session, conversation_id: int) -> str:
        """获取会话标题：取第一条用户消息的前30字，没有就返回新对话"""
        first_user_msg = MessageModel.find_all(db).filter_by(
            conversation_id=conversation_id,
            role="user"
        ).order_by(MessageModel.created_at.asc()).first()
        if first_user_msg:
            text = first_user_msg.content
            return text[:30] + "..." if len(text) > 30 else text
        return "新对话"

    async def create_conversation(
        self, db: Session, agent_id: int
    ) -> ConversationResponse:
        """创建会话：检查 Agent 存在 → 创建 ConversationModel"""
        # 校验 Agent 存在
        await self._agent_service.get_agent(db, agent_id)

        # 创建会话
        conversation = ConversationModel(
            agent_id=agent_id,
            title="新对话",
            status="ACTIVE"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        return ConversationResponse.from_orm(conversation, "")

    async def list_conversations(
        self, db: Session, page: int = 1, page_size: int = 20
    ) -> PageResult:
        """分页查询会话列表"""
        query = ConversationModel.find_all(db).order_by(
            ConversationModel.created_at.desc()
        )
        items, total = paginate(query, page, page_size)
        dtos = []
        for item in items:
            last_msg = self._get_last_message_text(db, item.id)
            conv_title = self._get_conversation_title(db, item.id)
            # 动态替换标题
            dto = ConversationResponse.from_orm(item, last_msg)
            dto.title = conv_title
            dtos.append(dto)
        return to_page_result(dtos, total, page, page_size)

    async def get_conversation(
        self, db: Session, conversation_id: int
    ) -> ConversationResponse:
        """查询单个会话详情"""
        conversation = ConversationModel.find_all(db).filter_by(id=conversation_id).first()
        if not conversation:
            raise BizException(ErrorCode.CONVERSATION_NOT_FOUND)
        last_msg = self._get_last_message_text(db, conversation_id)
        conv_title = self._get_conversation_title(db, conversation_id)
        dto = ConversationResponse.from_orm(conversation, last_msg)
        dto.title = conv_title
        return dto

    async def delete_conversation(self, db: Session, conversation_id: int) -> None:
        """删除会话：逻辑删除会话 + 级联软删该会话下所有消息"""
        conversation = ConversationModel.find_all(db).filter_by(id=conversation_id).first()
        if not conversation:
            raise BizException(ErrorCode.CONVERSATION_NOT_FOUND)

        # 级联软删该会话下所有消息
        MessageModel.find_all(db).filter_by(conversation_id=conversation_id).update(
            {"deleted": 1}
        )

        # 逻辑删除会话
        conversation.soft_delete()
        db.commit()

    async def send_message(
        self,
        db: Session,
        agent_id: int,
        content: str,
        conversation_id: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """核心对话链路：六步流程"""
        conversation = None
        try:
            # 步骤 1: 查 Agent / Model / Provider 配置
            agent = await self._agent_service.get_agent(db, agent_id)
            model = await self._model_service.get_model(db, agent.model_id)
            provider = await self._provider_service.get_provider(db, model.provider_id)

            # 如果没有 conversation_id，先创建新会话
            if conversation_id is None:
                conv_model = ConversationModel(
                    agent_id=agent_id,
                    title="新对话",
                    status="ACTIVE"
                )
                db.add(conv_model)
                db.commit()
                db.refresh(conv_model)
                conversation_id = conv_model.id
                conversation = ConversationResponse.from_orm(conv_model, "")
            else:
                # 验证会话存在
                conv_model = ConversationModel.find_all(db).filter_by(id=conversation_id).first()
                if not conv_model:
                    raise BizException(ErrorCode.CONVERSATION_NOT_FOUND)
                last_msg = self._get_last_message_text(db, conversation_id)
                conversation = ConversationResponse.from_orm(conv_model, last_msg)

            # 步骤 2: 取历史消息
            history = await self._context_manager.get_history(
                db, conversation_id, agent.max_context_turns
            )

            # 步骤 3: 存用户消息
            user_message = MessageModel(
                conversation_id=conversation_id,
                role="user",
                content=content,
            )
            db.add(user_message)
            db.commit()

            # 如果是第一条消息，用它更新会话标题
            msg_count = MessageModel.find_all(db).filter_by(
                conversation_id=conversation_id
            ).count()
            if msg_count == 1:
                # 取用户消息前30字作为标题
                title = content[:30] + "..." if len(content) > 30 else content
                conv_model = ConversationModel.find_all(db).filter_by(
                    id=conversation_id
                ).first()
                if conv_model:
                    conv_model.title = title
                    db.commit()
                    db.refresh(conv_model)

            # 步骤 4: 拼装 messages 数组
            messages = [{"role": "system", "content": agent.system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": content})

            # 步骤 5: 流式调用 LLM + 推送给前端
            # 获取 Provider 完整模型用于 adapter
            provider_model = (
                db.query(ProviderModel)
                .filter_by(id=provider.id, deleted=0)
                .first()
            )
            if not provider_model:
                raise BizException(ErrorCode.PROVIDER_NOT_FOUND)

            adapter = provider_adapter_factory.get_adapter(provider.provider_type)

            agent_config = {
                "temperature": agent.temperature,
                "max_tokens": agent.max_tokens,
            }

            full_response = ""
            start_time = time.monotonic()

            try:
                async for delta in adapter.stream_chat(
                    provider=provider_model,
                    model=model.model_id,
                    messages=messages,
                    agent_config=agent_config,
                ):
                    full_response += delta
                    yield f"data: {json.dumps({'type': 'delta', 'content': delta}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"LLM stream failed: {e}")
                error_msg = "抱歉，回复生成失败"
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg}, ensure_ascii=False)}\n\n"

                # 存错误消息
                error_message = MessageModel(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=error_msg,
                    finish_reason="error",
                    latency_ms=0,
                )
                db.add(error_message)
                db.commit()
                return

            latency_ms = int((time.monotonic() - start_time) * 1000)

            # 步骤 5a: 发送 done 事件
            yield f"data: {json.dumps({'type': 'done', 'finishReason': 'stop', 'latencyMs': latency_ms, 'conversationId': conversation_id}, ensure_ascii=False)}\n\n"

            # 步骤 6: 存 AI 回复 + 更新 Redis 上下文
            ai_message = MessageModel(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                finish_reason="stop",
                latency_ms=latency_ms,
            )
            db.add(ai_message)
            db.commit()

            # 更新 Redis 上下文
            await self._context_manager.add_message(
                conversation_id, "user", content, agent.max_context_turns
            )
            await self._context_manager.add_message(
                conversation_id, "assistant", full_response, agent.max_context_turns
            )

        except BizException as e:
            logger.error(f"send_message biz error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"send_message unexpected error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': '抱歉，服务出错了'}, ensure_ascii=False)}\n\n"

    async def get_messages(
        self, db: Session, conversation_id: int, page: int = 1, page_size: int = 100
    ) -> PageResult[MessageResponse]:
        """分页查询会话历史消息（按 created_at 升序）"""
        query = MessageModel.find_all(db).filter_by(
            conversation_id=conversation_id
        ).order_by(MessageModel.created_at.asc())
        items, total = paginate(query, page, page_size)
        dtos = [MessageResponse.from_orm(item) for item in items]
        return to_page_result(dtos, total, page, page_size)
