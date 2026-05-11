"""Agent module interfaces - define service contracts for Layer 2"""
from abc import ABC, abstractmethod
from typing import Optional


class IAgentService(ABC):
    """Agent service interface - exposed to Layer 4 (chat) module"""

    @abstractmethod
    async def create_agent(self, data: "AgentCreate") -> "AgentResponse":
        pass

    @abstractmethod
    async def get_agent(self, agent_id: int) -> Optional["AgentResponse"]:
        pass

    @abstractmethod
    async def list_agents(self, page: int, page_size: int) -> "PageResult[AgentResponse]":
        pass

    @abstractmethod
    async def update_agent(self, agent_id: int, data: "AgentUpdate") -> Optional["AgentResponse"]:
        pass

    @abstractmethod
    async def delete_agent(self, agent_id: int) -> bool:
        pass

    @abstractmethod
    async def bind_knowledge_base(self, agent_id: int, kb_id: int) -> bool:
        pass

    @abstractmethod
    async def unbind_knowledge_base(self, agent_id: int, kb_id: int) -> bool:
        pass

    @abstractmethod
    async def bind_tool(self, agent_id: int, tool_id: int) -> bool:
        pass

    @abstractmethod
    async def unbind_tool(self, agent_id: int, tool_id: int) -> bool:
        pass