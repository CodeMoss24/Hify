"""Chat service implementation"""
import time
import json
from typing import AsyncGenerator

import structlog
from sqlalchemy.orm import Session

from app.common.response import PageResult
from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.common.logging_config import get_correlation_id
from app.common.metrics import (
    chat_requests_total,
    chat_request_duration_seconds,
)
from app.agent.interfaces import IAgentService
from app.mcp.interfaces import IMcpToolService
from app.knowledge.service import DocumentChunkService
from app.provider.interfaces import IProviderService, IModelService
from app.provider.adapter_factory import provider_adapter_factory
from app.chat.interfaces import IChatService
from app.chat.models import ConversationModel, MessageModel
from app.chat.schemas import ConversationResponse, MessageResponse
from app.chat.context_manager import ContextManager
from app.provider.models import ProviderModel
from app.workflow.engine import workflow_engine

logger = structlog.get_logger(__name__)


class ChatService(IChatService):
    """Chat service - conversation CRUD + context management + send message"""

    def __init__(
        self,
        agent_service: IAgentService,
        model_service: IModelService,
        provider_service: IProviderService,
        mcp_tool_service: IMcpToolService,
    ):
        self._agent_service = agent_service
        self._model_service = model_service
        self._provider_service = provider_service
        self._mcp_tool_service = mcp_tool_service
        self._context_manager = ContextManager()

    @staticmethod
    def _error_event(message: str) -> str:
        """构建 SSE 错误事件，自动注入 correlation_id"""
        return json.dumps({
            "type": "error",
            "content": message,
            "correlationId": get_correlation_id(),
        }, ensure_ascii=False)

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
        _metric_start = time.monotonic()
        try:
            # 步骤 1: 查 Agent / Model / Provider 配置
            agent = await self._agent_service.get_agent(db, agent_id)

            # 检查 Agent 是否绑定了工作流，如果是则执行工作流并直接返回
            if agent.workflow_id:
                logger.info(f"Agent {agent_id} 绑定了工作流 {agent.workflow_id}，执行工作流")

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

                # 存用户消息
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

                # 执行工作流前先做 RAG 检索
                kb_ids = await self._agent_service.get_knowledge_base_ids(db, agent_id)
                rag_chunks = None
                if kb_ids:
                    chunks = []
                    chunk_service = DocumentChunkService()
                    for kb_id in kb_ids:
                        try:
                            results = await chunk_service.search_chunks(db, kb_id, content, top_k=3)
                            logger.info(f"Workflow RAG: kb {kb_id} 检索到 {len(results)} 个 chunks")
                            chunks.extend(results)
                        except Exception as e:
                            logger.warning(f"Workflow RAG search failed for kb_id={kb_id}: {e}")
                    if chunks:
                        rag_chunks = chunks
                        logger.info(f"Workflow RAG: 共 {len(rag_chunks)} 个 chunks 将传入工作流")

                # 执行工作流
                start_time = time.monotonic()
                workflow_result = await workflow_engine.execute(
                    agent.workflow_id, content, db, rag_chunks=rag_chunks,
                )
                full_response = workflow_result["result"]
                latency_ms = int((time.monotonic() - start_time) * 1000)

                # 推送 delta 事件（一次性推送全部内容，因为工作流已经执行完毕）
                yield f"data: {json.dumps({'type': 'delta', 'content': full_response}, ensure_ascii=False)}\n\n"

                # 发送 done 事件
                yield f"data: {json.dumps({'type': 'done', 'finishReason': 'stop', 'latencyMs': latency_ms, 'conversationId': conversation_id}, ensure_ascii=False)}\n\n"

                # 存 AI 回复
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
                model = await self._model_service.get_model(db, agent.model_id)
                await self._context_manager.add_message(
                    conversation_id, "user", content, agent.max_context_turns
                )
                await self._context_manager.add_message(
                    conversation_id, "assistant", full_response, agent.max_context_turns
                )

                duration = time.monotonic() - _metric_start
                chat_requests_total.labels(agent_id=str(agent_id), status="success").inc()
                chat_request_duration_seconds.labels(agent_id=str(agent_id)).observe(duration)

                return

            # 没有绑定工作流，走正常对话流程
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

            # 步骤 3.5: RAG 检索 — 如果 Agent 绑定了知识库，检索相关 chunk 注入 system prompt
            system_prompt = agent.system_prompt
            kb_ids = await self._agent_service.get_knowledge_base_ids(db, agent_id)
            logger.info(f"Agent {agent_id} 绑定的知识库 IDs: {kb_ids}")
            if kb_ids:
                rag_chunks = []
                chunk_service = DocumentChunkService()
                for kb_id in kb_ids:
                    try:
                        results = await chunk_service.search_chunks(db, kb_id, content, top_k=3)
                        logger.info(f"知识库 {kb_id} 检索结果: {len(results)} 个 chunks")
                        rag_chunks.extend(results)
                    except Exception as e:
                        logger.warning(f"RAG search failed for kb_id={kb_id}: {e}")

                if rag_chunks:
                    logger.info(f"使用 RAG 增强，共 {len(rag_chunks)} 个 chunks")
                    ref_lines = "\n".join(
                        f"[{i+1}] {c['content']}" for i, c in enumerate(rag_chunks)
                    )
                    system_prompt = (
                        f"{agent.system_prompt}\n\n"
                        "请基于以下参考资料回答用户问题。\n"
                        "如果资料中没有相关信息，直接说\"我没有找到相关资料\"，不要编造。\n\n"
                        f"【参考资料】\n{ref_lines}"
                    )
                    logger.info(f"最终 system_prompt:\n{system_prompt}")
                else:
                    logger.info("未找到相关的 RAG chunks")

            # 步骤 3.6: 构建 MCP 工具 schema（仅当有工具且无工作流时）
            tool_schemas = None
            tool_name_to_id: dict[str, int] = {}
            if agent.tools:
                tool_schemas = []
                for tool in agent.tools:
                    tool_schemas.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": json.loads(tool.input_schema) if tool.input_schema else {},
                        },
                    })
                    tool_name_to_id[tool.name] = tool.id
                logger.info(f"Agent {agent_id} 加载了 {len(tool_schemas)} 个 MCP 工具")

            # 步骤 4: 拼装 messages 数组
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": content})

            # 步骤 5: 调用 LLM
            # 获取 Provider 完整模型用于 adapter
            provider_model = (
                ProviderModel.find_all(db)
                .filter_by(id=provider.id)
                .first()
            )
            if not provider_model:
                raise BizException(ErrorCode.PROVIDER_NOT_FOUND)

            adapter = provider_adapter_factory.get_adapter(provider.provider_type)

            agent_config = {
                "temperature": agent.temperature,
                "max_tokens": agent.max_tokens,
            }

            start_time = time.monotonic()

            # 如果有工具，循环调用直到 LLM 不再请求工具，最后流式输出
            if tool_schemas:
                logger.info(f"Agent {agent_id} 带工具调用，进入 tool loop")
                max_tool_rounds = 5
                for _round in range(max_tool_rounds):
                    try:
                        result = await adapter.chat_complete(
                            provider=provider_model,
                            model=model.model_id,
                            messages=messages,
                            agent_config=agent_config,
                            tools=tool_schemas,
                        )
                    except Exception as e:
                        logger.error("llm.chat_complete.failed", error=str(e))
                        error_msg = "抱歉，回复生成失败"
                        yield f"data: {self._error_event(error_msg)}\n\n"
                        error_message = MessageModel(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=error_msg,
                            finish_reason="error",
                            latency_ms=0,
                        )
                        db.add(error_message)
                        db.commit()
                        duration = time.monotonic() - _metric_start
                        chat_requests_total.labels(agent_id=str(agent_id), status="error").inc()
                        chat_request_duration_seconds.labels(agent_id=str(agent_id)).observe(duration)
                        return

                    choices = result.get("choices", [])
                    if not choices:
                        raise BizException(ErrorCode.INTERNAL_ERROR, message="LLM 返回空 choices")

                    choice = choices[0]
                    finish_reason = choice.get("finish_reason", "stop")

                    if finish_reason == "tool_calls":
                        tool_calls = choice.get("message", {}).get("tool_calls", [])
                        assistant_msg = choice.get("message", {})
                        messages.append(assistant_msg)

                        for tc in tool_calls:
                            func = tc.get("function", {})
                            tool_name = func.get("name", "")
                            tool_call_id = tc.get("id", "")
                            tool_args_str = func.get("arguments", "{}")

                            logger.info(f"执行工具调用: {tool_name}, args={tool_args_str}")

                            try:
                                tool_args = json.loads(tool_args_str) if tool_args_str else {}
                                tool_id = tool_name_to_id.get(tool_name)
                                if tool_id is None:
                                    tool_result = f"错误：未找到工具 {tool_name}"
                                else:
                                    tool_result = await self._mcp_tool_service.call_tool(db, tool_id, tool_args)
                            except BizException as e:
                                tool_result = f"工具调用失败：{e.message}"
                                logger.warning(f"工具 {tool_name} 调用失败: {e}")
                            except Exception as e:
                                tool_result = f"工具调用异常：{str(e)}"
                                logger.error(f"工具 {tool_name} 调用异常: {e}")

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": tool_result,
                            })
                        # 继续下一轮，让 LLM 决定是继续调工具还是结束
                        continue
                    else:
                        # finish_reason == "stop"，退出循环
                        break

                # 工具循环结束，流式输出最终回复（不带 tools，LLM 不应再请求工具）
                full_response = ""
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
                    logger.error("llm.stream.final.failed", error=str(e))
                    error_msg = "抱歉，回复生成失败"
                    yield f"data: {self._error_event(error_msg)}\n\n"
                    error_message = MessageModel(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=error_msg,
                        finish_reason="error",
                        latency_ms=0,
                    )
                    db.add(error_message)
                    db.commit()
                    duration = time.monotonic() - _metric_start
                    chat_requests_total.labels(agent_id=str(agent_id), status="error").inc()
                    chat_request_duration_seconds.labels(agent_id=str(agent_id)).observe(duration)
                    return

                latency_ms = int((time.monotonic() - start_time) * 1000)
                yield f"data: {json.dumps({'type': 'done', 'finishReason': 'stop', 'latencyMs': latency_ms, 'conversationId': conversation_id}, ensure_ascii=False)}\n\n"

            else:
                # 无工具，走原有纯流式逻辑
                full_response = ""
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
                    logger.error("llm.stream.failed", error=str(e))
                    error_msg = "抱歉，回复生成失败"
                    yield f"data: {self._error_event(error_msg)}\n\n"

                    error_message = MessageModel(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=error_msg,
                        finish_reason="error",
                        latency_ms=0,
                    )
                    db.add(error_message)
                    db.commit()
                    duration = time.monotonic() - _metric_start
                    chat_requests_total.labels(agent_id=str(agent_id), status="error").inc()
                    chat_request_duration_seconds.labels(agent_id=str(agent_id)).observe(duration)
                    return

                latency_ms = int((time.monotonic() - start_time) * 1000)

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

            duration = time.monotonic() - _metric_start
            chat_requests_total.labels(agent_id=str(agent_id), status="success").inc()
            chat_request_duration_seconds.labels(agent_id=str(agent_id)).observe(duration)

        except BizException as e:
            logger.error("send_message.biz_error", error_code=e.code, error_message=e.message)
            yield f"data: {self._error_event(str(e))}\n\n"
            duration = time.monotonic() - _metric_start
            chat_requests_total.labels(agent_id=str(agent_id), status="error").inc()
            chat_request_duration_seconds.labels(agent_id=str(agent_id)).observe(duration)
        except Exception as e:
            logger.error("send_message.unexpected_error", error=str(e))
            yield f"data: {self._error_event('抱歉，服务出错了')}\n\n"
            duration = time.monotonic() - _metric_start
            chat_requests_total.labels(agent_id=str(agent_id), status="error").inc()
            chat_request_duration_seconds.labels(agent_id=str(agent_id)).observe(duration)

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
