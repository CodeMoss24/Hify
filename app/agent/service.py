"""Agent service implementation"""
import logging

from sqlalchemy.orm import Session

from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.agent.interfaces import IAgentService
from app.agent.models import AgentModel, AgentKnowledgeBaseModel, AgentToolModel
from app.agent.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    KnowledgeBaseItem,
    ToolItem,
)
from app.provider.interfaces import IModelService
from app.mcp.interfaces import IMcpToolService
from app.knowledge.interfaces import IKnowledgeBaseService

logger = logging.getLogger(__name__)


class AgentService(IAgentService):
    """Agent service - CRUD + knowledge base / tool binding"""

    def __init__(
        self,
        model_service: IModelService,
        knowledge_base_service: IKnowledgeBaseService,
        mcp_tool_service: IMcpToolService,
    ):
        self._model_service = model_service
        self._kb_service = knowledge_base_service
        self._tool_service = mcp_tool_service

    async def list_agents(self, db: Session, page: int = 1, page_size: int = 20):
        """分页查询 Agent 列表（不含关联数据）"""
        query = AgentModel.find_all(db)
        items, total = paginate(query, page, page_size)
        dtos = [AgentResponse.from_orm(item) for item in items]
        return to_page_result(dtos, total, page, page_size)

    async def create_agent(self, db: Session, body: AgentCreate) -> AgentResponse:
        """创建 Agent，校验 model_id 存在"""
        await self._model_service.get_model(db, body.model_id)

        model = AgentModel(
            name=body.name,
            description=body.description,
            model_id=body.model_id,
            system_prompt=body.system_prompt,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            max_context_turns=body.max_context_turns,
            enabled=body.enabled,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return AgentResponse.from_orm(model)

    async def get_agent(self, db: Session, agent_id: int) -> AgentResponse:
        """查询单个 Agent（含关联的知识库和工具列表）"""
        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        knowledge_bases = await self._get_bound_knowledge_bases(db, agent_id)
        tools = await self._get_bound_tools(db, agent_id)
        return AgentResponse.from_orm(agent, knowledge_bases=knowledge_bases, tools=tools)

    async def update_agent(self, db: Session, agent_id: int, body: AgentUpdate) -> AgentResponse:
        """更新 Agent，只改非空字段"""
        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        if body.model_id is not None:
            await self._model_service.get_model(db, body.model_id)
            agent.model_id = body.model_id
        if body.name is not None:
            agent.name = body.name
        if body.description is not None:
            agent.description = body.description
        if body.system_prompt is not None:
            agent.system_prompt = body.system_prompt
        if body.temperature is not None:
            agent.temperature = body.temperature
        if body.max_tokens is not None:
            agent.max_tokens = body.max_tokens
        if body.max_context_turns is not None:
            agent.max_context_turns = body.max_context_turns
        if body.enabled is not None:
            agent.enabled = body.enabled

        db.commit()
        db.refresh(agent)
        knowledge_bases = await self._get_bound_knowledge_bases(db, agent_id)
        tools = await self._get_bound_tools(db, agent_id)
        return AgentResponse.from_orm(agent, knowledge_bases=knowledge_bases, tools=tools)

    async def delete_agent(self, db: Session, agent_id: int) -> None:
        """删除 Agent（逻辑删除，级联软删关联表）"""
        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        # 级联软删关联表
        AgentKnowledgeBaseModel.find_all(db).filter_by(agent_id=agent_id).update(
            {"deleted": 1}
        )
        AgentToolModel.find_all(db).filter_by(agent_id=agent_id).update(
            {"deleted": 1}
        )

        agent.soft_delete()
        db.commit()

    async def bind_knowledge_base(self, db: Session, agent_id: int, kb_id: int) -> bool:
        """绑定知识库（幂等：已存在则直接返回 True）"""
        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        await self._kb_service.get_knowledge_base(db, kb_id)

        existing = (
            AgentKnowledgeBaseModel.find_all(db)
            .filter_by(agent_id=agent_id, knowledge_base_id=kb_id)
            .first()
        )
        if existing:
            return True

        rel = AgentKnowledgeBaseModel(agent_id=agent_id, knowledge_base_id=kb_id)
        db.add(rel)
        db.commit()
        return True

    async def unbind_knowledge_base(self, db: Session, agent_id: int, kb_id: int) -> bool:
        """解绑知识库"""
        rel = (
            AgentKnowledgeBaseModel.find_all(db)
            .filter_by(agent_id=agent_id, knowledge_base_id=kb_id)
            .first()
        )
        if not rel:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        rel.soft_delete()
        db.commit()
        return True

    async def bind_tool(self, db: Session, agent_id: int, tool_id: int) -> bool:
        """绑定 MCP 工具（幂等：已存在则直接返回 True）"""
        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        await self._tool_service.get_tool(db, tool_id)

        existing = (
            AgentToolModel.find_all(db)
            .filter_by(agent_id=agent_id, mcp_tool_id=tool_id)
            .first()
        )
        if existing:
            return True

        rel = AgentToolModel(agent_id=agent_id, mcp_tool_id=tool_id)
        db.add(rel)
        db.commit()
        return True

    async def unbind_tool(self, db: Session, agent_id: int, tool_id: int) -> bool:
        """解绑 MCP 工具"""
        rel = (
            AgentToolModel.find_all(db)
            .filter_by(agent_id=agent_id, mcp_tool_id=tool_id)
            .first()
        )
        if not rel:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        rel.soft_delete()
        db.commit()
        return True

    async def _get_bound_knowledge_bases(
        self, db: Session, agent_id: int
    ) -> list[KnowledgeBaseItem]:
        """查询 Agent 已绑定的知识库摘要列表"""
        rels = (
            AgentKnowledgeBaseModel.find_all(db)
            .filter_by(agent_id=agent_id)
            .all()
        )
        items = []
        for rel in rels:
            try:
                kb = await self._kb_service.get_knowledge_base(db, rel.knowledge_base_id)
                items.append(KnowledgeBaseItem(id=kb.id, name=kb.name))
            except BizException:
                pass
        return items

    async def _get_bound_tools(
        self, db: Session, agent_id: int
    ) -> list[ToolItem]:
        """查询 Agent 已绑定的 MCP 工具摘要列表"""
        rels = (
            AgentToolModel.find_all(db)
            .filter_by(agent_id=agent_id)
            .all()
        )
        items = []
        for rel in rels:
            try:
                tool = await self._tool_service.get_tool(db, rel.mcp_tool_id)
                items.append(ToolItem(id=tool.id, name=tool.name))
            except BizException:
                pass
        return items
