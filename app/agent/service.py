"""Agent service implementation"""
import logging

from sqlalchemy.orm import Session

from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.agent.interfaces import IAgentService
from app.agent.models import AgentModel, AgentKnowledgeBaseModel, AgentToolModel
from app.knowledge.models import KnowledgeBaseModel
from app.agent.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    KnowledgeBaseItem,
)
from app.mcp.schemas import McpToolResponse
from app.provider.interfaces import IModelService
from app.mcp.interfaces import IMcpToolService, IMcpServerService
from app.knowledge.interfaces import IKnowledgeBaseService

logger = logging.getLogger(__name__)


class AgentService(IAgentService):
    """Agent service - CRUD + knowledge base / tool binding"""

    def __init__(
        self,
        model_service: IModelService,
        knowledge_base_service: IKnowledgeBaseService,
        mcp_tool_service: IMcpToolService,
        mcp_server_service: IMcpServerService,
    ):
        self._model_service = model_service
        self._kb_service = knowledge_base_service
        self._tool_service = mcp_tool_service
        self._server_service = mcp_server_service

    async def list_agents(self, db: Session, page: int = 1, page_size: int = 20):
        """分页查询 Agent 列表（含关联数据）"""
        query = AgentModel.find_all(db)
        items, total = paginate(query, page, page_size)

        dtos = []
        for item in items:
            knowledge_bases = await self._get_bound_knowledge_bases(db, item.id)
            tools = await self._get_bound_tools(db, item.id)
            dtos.append(AgentResponse.from_orm(item, knowledge_bases=knowledge_bases, tools=tools))

        return to_page_result(dtos, total, page, page_size)

    async def create_agent(self, db: Session, body: AgentCreate) -> AgentResponse:
        """创建 Agent，校验 model_id 存在，绑定知识库"""
        await self._model_service.get_model(db, body.model_id)

        model = AgentModel(
            name=body.name,
            description=body.description,
            model_id=body.model_id,
            workflow_id=body.workflow_id,
            system_prompt=body.system_prompt,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            max_context_turns=body.max_context_turns,
            enabled=body.enabled,
        )
        db.add(model)
        db.commit()
        db.refresh(model)

        # 绑定知识库
        if body.knowledge_base_id is not None and body.knowledge_base_id != 0:
            await self.bind_knowledge_base(db, model.id, body.knowledge_base_id)

        knowledge_bases = await self._get_bound_knowledge_bases(db, model.id)
        tools = await self._get_bound_tools(db, model.id)
        return AgentResponse.from_orm(model, knowledge_bases=knowledge_bases, tools=tools)

    async def get_agent(self, db: Session, agent_id: int) -> AgentResponse:
        """查询单个 Agent（含关联的知识库和工具列表）"""
        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        knowledge_bases = await self._get_bound_knowledge_bases(db, agent_id)
        tools = await self._get_bound_tools(db, agent_id)
        return AgentResponse.from_orm(agent, knowledge_bases=knowledge_bases, tools=tools)

    async def update_agent(self, db: Session, agent_id: int, body: AgentUpdate) -> AgentResponse:
        """更新 Agent，只改非空字段，处理知识库绑定"""
        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        if body.model_id is not None:
            await self._model_service.get_model(db, body.model_id)
            agent.model_id = body.model_id
        if body.workflow_id is not None:
            agent.workflow_id = body.workflow_id
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

        # 处理知识库绑定：先解绑所有，再绑定新的（如果有）
        if body.knowledge_base_id is not None:
            # 先获取所有关联记录（包括已软删除的）
            existing_rels = db.query(AgentKnowledgeBaseModel).filter_by(agent_id=agent_id).all()
            for rel in existing_rels:
                rel.soft_delete()

            db.flush()

            # 如果有新的知识库 ID，绑定它
            if body.knowledge_base_id != 0:
                await self.bind_knowledge_base(db, agent_id, body.knowledge_base_id)

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

    async def bind_tools(self, db: Session, agent_id: int, tool_ids: list[int]) -> AgentResponse:
        """Agent 批量绑定 MCP 工具（全量替换）"""
        if len(tool_ids) > 10:
            raise BizException(ErrorCode.PARAM_ERROR, message="Agent can bind at most 10 tools")

        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        # 批量校验 tool 存在且对应 Server 启用
        validated_tools = await self._tool_service.get_tools_by_ids(db, tool_ids)
        if len(validated_tools) != len(tool_ids):
            found_ids = {t.id for t in validated_tools}
            missing = [tid for tid in tool_ids if tid not in found_ids]
            raise BizException(
                ErrorCode.MCP_TOOL_NOT_FOUND,
                message=f"MCP tools not found: {missing}",
            )

        server_ids = {t.server_id for t in validated_tools}
        for sid in server_ids:
            server = await self._server_service.get_server(db, sid)
            if not server.enabled:
                raise BizException(
                    ErrorCode.PARAM_ERROR,
                    message=f"MCP Server (id={server.id}) is disabled, cannot bind its tools",
                )

        # 全量替换：先软删旧关联，再插入新关联
        old_rels = AgentToolModel.find_all(db).filter_by(agent_id=agent_id).all()
        for rel in old_rels:
            rel.soft_delete()
        db.flush()

        for tid in tool_ids:
            db.add(AgentToolModel(agent_id=agent_id, mcp_tool_id=tid))
        db.commit()

        knowledge_bases = await self._get_bound_knowledge_bases(db, agent_id)
        tools = await self._get_bound_tools(db, agent_id)
        db.refresh(agent)
        return AgentResponse.from_orm(agent, knowledge_bases=knowledge_bases, tools=tools)

    async def bind_knowledge_base(self, db: Session, agent_id: int, kb_id: int) -> bool:
        """绑定知识库（幂等：已存在则直接返回 True）"""
        agent = AgentModel.find_all(db).filter_by(id=agent_id).first()
        if not agent:
            raise BizException(ErrorCode.AGENT_NOT_FOUND)

        await self._kb_service.get_knowledge_base(db, kb_id)

        # 先查找包括已删除的记录
        existing = db.query(AgentKnowledgeBaseModel).filter_by(
            agent_id=agent_id,
            knowledge_base_id=kb_id
        ).first()

        if existing:
            if existing.deleted == 0:
                # 已存在且未删除，直接返回
                return True
            else:
                # 已存在但被软删除，恢复它
                existing.deleted = 0
                db.commit()
                return True

        # 不存在任何记录，插入新的
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

        # 先查找包括已删除的记录
        existing = db.query(AgentToolModel).filter_by(
            agent_id=agent_id,
            mcp_tool_id=tool_id
        ).first()

        if existing:
            if existing.deleted == 0:
                # 已存在且未删除，直接返回
                return True
            else:
                # 已存在但被软删除，恢复它
                existing.deleted = 0
                db.commit()
                return True

        # 不存在任何记录，插入新的
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

    async def get_knowledge_base_ids(self, db: Session, agent_id: int) -> list[int]:
        """获取 Agent 绑定的知识库 ID 列表"""
        rels = (
            AgentKnowledgeBaseModel.find_all(db)
            .filter_by(agent_id=agent_id)
            .all()
        )
        kb_ids = [rel.knowledge_base_id for rel in rels]
        logger.info(f"Agent {agent_id} 绑定的知识库: {kb_ids}")
        return kb_ids

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
            kb = KnowledgeBaseModel.find_all(db).filter_by(id=rel.knowledge_base_id).first()
            if kb:
                items.append(KnowledgeBaseItem(id=kb.id, name=kb.name))
        return items

    async def _get_bound_tools(
        self, db: Session, agent_id: int
    ) -> list[McpToolResponse]:
        """查询 Agent 已绑定的 MCP 工具列表（批量查询）"""
        rels = (
            AgentToolModel.find_all(db)
            .filter_by(agent_id=agent_id)
            .all()
        )
        if not rels:
            return []
        tool_ids = [rel.mcp_tool_id for rel in rels]
        return await self._tool_service.get_tools_by_ids(db, tool_ids)
