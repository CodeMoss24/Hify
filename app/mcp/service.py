"""MCP service implementation"""
import logging

from sqlalchemy.orm import Session

from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.common.response import PageResult
from app.mcp.interfaces import IMcpServerService, IMcpToolService

logger = logging.getLogger(__name__)


class McpServerService(IMcpServerService):
    """MCP server service - stub implementation"""

    async def create_server(self, db: Session, data):
        raise NotImplementedError("MCP module not implemented")

    async def get_server(self, db: Session, server_id: int):
        raise BizException(ErrorCode.MCP_SERVER_NOT_FOUND)

    async def list_servers(self, db: Session, page: int, page_size: int) -> PageResult:
        raise NotImplementedError("MCP module not implemented")

    async def update_server(self, db: Session, server_id: int, data):
        raise NotImplementedError("MCP module not implemented")

    async def delete_server(self, db: Session, server_id: int) -> bool:
        raise NotImplementedError("MCP module not implemented")

    async def test_connection(self, db: Session, server_id: int):
        raise NotImplementedError("MCP module not implemented")


class McpToolService(IMcpToolService):
    """MCP tool service - stub implementation"""

    async def create_tool(self, db: Session, server_id: int, data):
        raise NotImplementedError("MCP module not implemented")

    async def get_tool(self, db: Session, tool_id: int):
        raise BizException(ErrorCode.MCP_TOOL_NOT_FOUND)

    async def list_tools(self, db: Session, server_id, page: int, page_size: int) -> PageResult:
        raise NotImplementedError("MCP module not implemented")

    async def update_tool(self, db: Session, tool_id: int, data):
        raise NotImplementedError("MCP module not implemented")

    async def delete_tool(self, db: Session, tool_id: int) -> bool:
        raise NotImplementedError("MCP module not implemented")

    async def call_tool(self, db: Session, tool_id: int, parameters: dict):
        raise NotImplementedError("MCP module not implemented")
