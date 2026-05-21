"""Agent API 路由"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.response import ApiResponse
from app.agent.interfaces import IAgentService
from app.agent.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    BindKnowledgeBaseRequest,
    BindToolRequest,
    AgentToolBindRequest,
)
from app.agent.service import AgentService
from app.provider.service import ModelService
from app.knowledge.service import KnowledgeBaseService
from app.mcp.service import McpToolService, McpServerService

router = APIRouter()


def _agent_service() -> IAgentService:
    """构造 AgentService 实例及其依赖"""
    return AgentService(
        model_service=ModelService(),
        knowledge_base_service=KnowledgeBaseService(),
        mcp_tool_service=McpToolService(),
        mcp_server_service=McpServerService(),
    )


# ── Agent CRUD 端点 ────────────────────────────────────────


@router.post("/agents", response_model=ApiResponse)
async def create_agent(
    body: AgentCreate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """创建 Agent"""
    agent_service = _agent_service()
    agent = await agent_service.create_agent(db, body)
    return ApiResponse.ok(data=agent)


@router.get("/agents", response_model=ApiResponse)
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """分页查询 Agent 列表"""
    agent_service = _agent_service()
    page_result = await agent_service.list_agents(db, page, page_size)
    return ApiResponse.ok(data=page_result)


@router.get("/agents/{agent_id}", response_model=ApiResponse)
async def get_agent(
    agent_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """查询单个 Agent（含关联的知识库和工具列表）"""
    agent_service = _agent_service()
    agent = await agent_service.get_agent(db, agent_id)
    return ApiResponse.ok(data=agent)


@router.put("/agents/{agent_id}", response_model=ApiResponse)
async def update_agent(
    agent_id: int = Path(..., ge=1),
    body: AgentUpdate = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """更新 Agent"""
    agent_service = _agent_service()
    agent = await agent_service.update_agent(db, agent_id, body)
    return ApiResponse.ok(data=agent)


@router.delete("/agents/{agent_id}", response_model=ApiResponse)
async def delete_agent(
    agent_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """删除 Agent（逻辑删除）"""
    agent_service = _agent_service()
    await agent_service.delete_agent(db, agent_id)
    return ApiResponse.ok(message="deleted")


# ── 知识库绑定端点 ──────────────────────────────────────────


@router.post("/agents/{agent_id}/knowledge-bases", response_model=ApiResponse)
async def bind_knowledge_base(
    agent_id: int = Path(..., ge=1),
    body: BindKnowledgeBaseRequest = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """绑定知识库"""
    agent_service = _agent_service()
    await agent_service.bind_knowledge_base(db, agent_id, body.knowledge_base_id)
    return ApiResponse.ok(message="bound")


@router.delete(
    "/agents/{agent_id}/knowledge-bases/{kb_id}", response_model=ApiResponse
)
async def unbind_knowledge_base(
    agent_id: int = Path(..., ge=1),
    kb_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """解绑知识库"""
    agent_service = _agent_service()
    await agent_service.unbind_knowledge_base(db, agent_id, kb_id)
    return ApiResponse.ok(message="unbound")


# ── MCP 工具绑定端点 ────────────────────────────────────────


@router.put("/agents/{agent_id}/tools", response_model=ApiResponse)
async def bind_tools(
    agent_id: int = Path(..., ge=1),
    body: AgentToolBindRequest = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """批量绑定 MCP 工具（全量替换）"""
    agent_service = _agent_service()
    agent = await agent_service.bind_tools(db, agent_id, body.tool_ids)
    return ApiResponse.ok(data=agent)


@router.post("/agents/{agent_id}/tools", response_model=ApiResponse)
async def bind_tool(
    agent_id: int = Path(..., ge=1),
    body: BindToolRequest = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """绑定 MCP 工具"""
    agent_service = _agent_service()
    await agent_service.bind_tool(db, agent_id, body.mcp_tool_id)
    return ApiResponse.ok(message="bound")


@router.delete("/agents/{agent_id}/tools/{tool_id}", response_model=ApiResponse)
async def unbind_tool(
    agent_id: int = Path(..., ge=1),
    tool_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """解绑 MCP 工具"""
    agent_service = _agent_service()
    await agent_service.unbind_tool(db, agent_id, tool_id)
    return ApiResponse.ok(message="unbound")
