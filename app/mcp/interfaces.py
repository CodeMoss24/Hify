"""MCP module interfaces - define service contracts for Layer 1"""
from abc import ABC, abstractmethod
from typing import Optional, Any

from sqlalchemy.orm import Session

from app.common.response import PageResult


class IMcpServerService(ABC):
    """MCP server service interface - exposed to Layer 2/3 modules"""

    @abstractmethod
    async def create_server(self, db: Session, data: "McpServerCreate") -> "McpServerResponse":
        pass

    @abstractmethod
    async def get_server(self, db: Session, server_id: int) -> Optional["McpServerResponse"]:
        pass

    @abstractmethod
    async def list_servers(self, db: Session, page: int, page_size: int) -> "PageResult[McpServerResponse]":
        pass

    @abstractmethod
    async def update_server(self, db: Session, server_id: int, data: "McpServerUpdate") -> Optional["McpServerResponse"]:
        pass

    @abstractmethod
    async def delete_server(self, db: Session, server_id: int) -> bool:
        pass

    @abstractmethod
    async def test_connection(self, db: Session, server_id: int) -> "TestConnectionResponse":
        pass


class IMcpToolService(ABC):
    """MCP tool service interface"""

    @abstractmethod
    async def create_tool(self, db: Session, server_id: int, data: "McpToolCreate") -> "McpToolResponse":
        pass

    @abstractmethod
    async def get_tool(self, db: Session, tool_id: int) -> Optional["McpToolResponse"]:
        pass

    @abstractmethod
    async def list_tools(self, db: Session, server_id: Optional[int], page: int, page_size: int) -> "PageResult[McpToolResponse]":
        pass

    @abstractmethod
    async def update_tool(self, db: Session, tool_id: int, data: "McpToolUpdate") -> Optional["McpToolResponse"]:
        pass

    @abstractmethod
    async def delete_tool(self, db: Session, tool_id: int) -> bool:
        pass

    @abstractmethod
    async def call_tool(self, db: Session, tool_id: int, parameters: dict[str, Any]) -> Any:
        pass
