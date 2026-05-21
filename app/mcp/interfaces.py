"""MCP module interfaces - define service contracts for Layer 1"""
from abc import ABC, abstractmethod
from typing import Optional, Any

from sqlalchemy.orm import Session

from app.common.response import PageResult
from app.mcp.schemas import (
    McpServerCreate, McpServerUpdate, McpServerResponse,
    McpToolResponse, McpConnectionTestResult, McpDebugResult,
)


class IMcpServerService(ABC):
    """MCP server service interface - exposed to Layer 2/3 modules"""

    @abstractmethod
    async def create_server(self, db: Session, body: McpServerCreate) -> McpServerResponse:
        pass

    @abstractmethod
    async def get_server(self, db: Session, server_id: int) -> McpServerResponse:
        pass

    @abstractmethod
    async def list_servers(self, db: Session, page: int, page_size: int) -> PageResult:
        pass

    @abstractmethod
    async def update_server(self, db: Session, server_id: int, body: McpServerUpdate) -> McpServerResponse:
        pass

    @abstractmethod
    async def delete_server(self, db: Session, server_id: int) -> None:
        pass

    @abstractmethod
    async def test_connection(self, db: Session, server_id: int) -> McpConnectionTestResult:
        pass

    @abstractmethod
    async def debug_tool(self, db: Session, server_id: int, tool_name: str, arguments: dict) -> McpDebugResult:
        pass


class IMcpToolService(ABC):
    """MCP tool service interface"""

    @abstractmethod
    async def list_tools_by_server(self, db: Session, server_id: int, page: int, page_size: int) -> PageResult:
        pass

    @abstractmethod
    async def list_all_tools_by_server(self, db: Session, server_id: int) -> list[McpToolResponse]:
        pass

    @abstractmethod
    async def get_tool_by_id(self, db: Session, tool_id: int) -> McpToolResponse:
        pass

    @abstractmethod
    async def get_tools_by_ids(self, db: Session, tool_ids: list[int]) -> list[McpToolResponse]:
        pass

    @abstractmethod
    async def create_tool(self, db: Session, server_id: int, data) -> McpToolResponse:
        pass

    @abstractmethod
    async def get_tool(self, db: Session, tool_id: int) -> Optional[McpToolResponse]:
        pass

    @abstractmethod
    async def list_tools(self, db: Session, server_id: Optional[int], page: int, page_size: int) -> PageResult:
        pass

    @abstractmethod
    async def update_tool(self, db: Session, tool_id: int, data) -> Optional[McpToolResponse]:
        pass

    @abstractmethod
    async def delete_tool(self, db: Session, tool_id: int) -> bool:
        pass

    @abstractmethod
    async def call_tool(self, db: Session, tool_id: int, arguments: dict[str, Any]) -> str:
        pass
