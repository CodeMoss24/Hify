"""Error code definitions"""
from enum import Enum


class ErrorCode(Enum):
    """Standard error codes"""

    # Common (1000-1999)
    PARAM_ERROR = (1001, "Parameter error")
    UNAUTHORIZED = (1002, "Unauthorized")
    FORBIDDEN = (1003, "Forbidden")
    NOT_FOUND = (1004, "Resource not found")
    INTERNAL_ERROR = (1005, "Internal server error")
    SERVICE_UNAVAILABLE = (1006, "Service unavailable")

    # Provider (2000-2999)
    PROVIDER_NOT_FOUND = (2001, "Provider not found")
    PROVIDER_CONNECTION_FAILED = (2002, "Provider connection failed")

    # Agent (3000-3999)
    AGENT_NOT_FOUND = (3001, "Agent not found")

    # Chat (4000-4999)
    CONVERSATION_NOT_FOUND = (4001, "Conversation not found")
    MESSAGE_NOT_FOUND = (4002, "Message not found")

    # MCP (5000-5999)
    MCP_SERVER_NOT_FOUND = (5001, "MCP server not found")
    MCP_TOOL_NOT_FOUND = (5002, "MCP tool not found")
    MCP_CALL_FAILED = (5003, "MCP tool call failed")

    # Workflow (6000-6999)
    WORKFLOW_NOT_FOUND = (6001, "Workflow not found")
    WORKFLOW_EXECUTE_FAILED = (6002, "Workflow execution failed")

    # Knowledge (7000-7999)
    KNOWLEDGE_BASE_NOT_FOUND = (7001, "Knowledge base not found")
    DOCUMENT_NOT_FOUND = (7002, "Document not found")
    CHUNK_NOT_FOUND = (7003, "Chunk not found")

    # LLM (8000-8999)
    LLM_TIMEOUT = (8001, "LLM API timeout")
    LLM_AUTH_FAILED = (8002, "LLM API auth failed")
    LLM_RATE_LIMITED = (8003, "LLM API rate limited")
    LLM_SERVER_ERROR = (8004, "LLM API server error")

    def __init__(self, code: int, message: str):
        self._code = code
        self._message = message

    @property
    def code(self) -> int:
        return self._code

    @property
    def message(self) -> str:
        return self._message
