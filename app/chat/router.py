"""Chat API 路由"""
from fastapi import APIRouter, Depends, Query, Path
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.response import ApiResponse
from app.agent.interfaces import IAgentService
from app.provider.interfaces import IProviderService, IModelService
from app.agent.service import AgentService
from app.provider.service import ProviderService, ModelService
from app.knowledge.service import KnowledgeBaseService
from app.mcp.service import McpToolService
from app.chat.interfaces import IChatService
from app.chat.service import ChatService
from app.chat.schemas import ConversationCreate, ConversationResponse, ChatRequest, MessageResponse

router = APIRouter()


def _chat_service() -> IChatService:
    """构造 ChatService 实例及其依赖"""
    agent_service = AgentService(
        model_service=ModelService(),
        knowledge_base_service=KnowledgeBaseService(),
        mcp_tool_service=McpToolService(),
    )
    return ChatService(
        agent_service=agent_service,
        model_service=ModelService(),
        provider_service=ProviderService(),
    )


# ── Conversation 端点 ──────────────────────────────────────


@router.post("/conversations")
async def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """创建会话"""
    chat_service = _chat_service()
    conversation = await chat_service.create_conversation(db, body.agent_id)
    return JSONResponse(ApiResponse.ok(data=conversation).model_dump())


@router.get("/conversations")
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """分页查询会话列表"""
    chat_service = _chat_service()
    page_result = await chat_service.list_conversations(db, page, page_size)
    return JSONResponse(ApiResponse.ok(data=page_result).model_dump())


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """查询单个会话详情"""
    chat_service = _chat_service()
    conversation = await chat_service.get_conversation(db, conversation_id)
    return JSONResponse(ApiResponse.ok(data=conversation).model_dump())


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """删除会话（逻辑删除，级联软删消息）"""
    chat_service = _chat_service()
    await chat_service.delete_conversation(db, conversation_id)
    return JSONResponse(ApiResponse.ok(message="deleted").model_dump())


# ── Message 端点 ──────────────────────────────────────


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """分页查询会话历史消息"""
    chat_service = _chat_service()
    page_result = await chat_service.get_messages(db, conversation_id, page, page_size)
    return JSONResponse(ApiResponse.ok(data=page_result).model_dump())


@router.post("/conversations/{conversation_id}/messages")
async def send_message_to_conversation(
    conversation_id: int,
    body: ChatRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """给指定会话发送消息（流式响应）"""
    # 先获取会话来得到 agent_id
    chat_service = _chat_service()
    conversation = await chat_service.get_conversation(db, conversation_id)

    async def generate():
        async for chunk in chat_service.send_message(
            db=db,
            agent_id=conversation.agent_id,
            content=body.content,
            conversation_id=conversation_id,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/agents/{agent_id}/chat")
async def chat_with_agent(
    agent_id: int,
    body: ChatRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """直接和 Agent 聊天（自动创建新会话）"""
    chat_service = _chat_service()

    async def generate():
        async for chunk in chat_service.send_message(
            db=db,
            agent_id=agent_id,
            content=body.content,
            conversation_id=None,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")
