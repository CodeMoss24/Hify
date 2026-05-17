"""Agent module interfaces - define service contracts for Layer 2"""
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy.orm import Session

from app.common.response import PageResult
from app.agent.schemas import AgentCreate, AgentUpdate, AgentResponse


class IAgentService(ABC):
    """Agent service interface - exposed to Layer 4 (chat) module"""

    @abstractmethod
    async def list_agents(self, db: Session, page: int = 1, page_size: int = 20) -> PageResult:
        """分页查询 Agent 列表（不含关联数据）"""
        pass

    @abstractmethod
    async def create_agent(self, db: Session, body: AgentCreate) -> AgentResponse:
        """创建 Agent"""
        pass

    @abstractmethod
    async def get_agent(self, db: Session, agent_id: int) -> AgentResponse:
        """查询单个 Agent（含关联的知识库和工具列表）"""
        pass

    @abstractmethod
    async def update_agent(self, db: Session, agent_id: int, body: AgentUpdate) -> AgentResponse:
        """更新 Agent"""
        pass

    @abstractmethod
    async def delete_agent(self, db: Session, agent_id: int) -> None:
        """删除 Agent（逻辑删除，级联软删关联表）"""
        pass

    @abstractmethod
    async def bind_knowledge_base(self, db: Session, agent_id: int, kb_id: int) -> bool:
        """绑定知识库（幂等）"""
        pass

    @abstractmethod
    async def unbind_knowledge_base(self, db: Session, agent_id: int, kb_id: int) -> bool:
        """解绑知识库"""
        pass

    @abstractmethod
    async def bind_tool(self, db: Session, agent_id: int, tool_id: int) -> bool:
        """绑定 MCP 工具（幂等）"""
        pass

    @abstractmethod
    async def unbind_tool(self, db: Session, agent_id: int, tool_id: int) -> bool:
        """解绑 MCP 工具"""
        pass
