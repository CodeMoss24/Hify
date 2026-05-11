"""错误码定义"""
from enum import Enum


class ErrorCode(Enum):
    """统一错误码枚举"""

    # 通用错误（1000-1999）
    PARAM_ERROR = (1001, "参数错误")
    UNAUTHORIZED = (1002, "未授权")
    FORBIDDEN = (1003, "无权限")
    NOT_FOUND = (1004, "资源不存在")
    INTERNAL_ERROR = (1005, "系统内部错误")
    SERVICE_UNAVAILABLE = (1006, "服务不可用")

    # Provider 错误（2000-2999）
    PROVIDER_NOT_FOUND = (2001, " Provider 不存在")
    PROVIDER_CONNECTION_FAILED = (2002, "Provider 连接失败")

    # Agent 错误（3000-3999）
    AGENT_NOT_FOUND = (3001, "Agent 不存在")

    # Chat 错误（4000-4999）
    CONVERSATION_NOT_FOUND = (4001, "会话不存在")
    MESSAGE_NOT_FOUND = (4002, "消息不存在")

    # MCP 错误（5000-5999）
    MCP_SERVER_NOT_FOUND = (5001, "MCP Server 不存在")
    MCP_TOOL_NOT_FOUND = (5002, "MCP Tool 不存在")
    MCP_CALL_FAILED = (5003, "MCP Tool 调用失败")

    # Workflow 错误（6000-6999）
    WORKFLOW_NOT_FOUND = (6001, "Workflow 不存在")
    WORKFLOW_EXECUTE_FAILED = (6002, "Workflow 执行失败")

    # Knowledge 错误（7000-7999）
    KNOWLEDGE_BASE_NOT_FOUND = (7001, "知识库不存在")
    DOCUMENT_NOT_FOUND = (7002, "文档不存在")
    CHUNK_NOT_FOUND = (7003, "分块不存在")

    def __init__(self, code: int, message: str):
        self._code = code
        self._message = message

    @property
    def code(self) -> int:
        return self._code

    @property
    def message(self) -> str:
        return self._message