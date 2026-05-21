"""MCP service implementation"""
import json
import logging
import time

from sqlalchemy.orm import Session

from app.agent.models import AgentToolModel
from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.common.metrics import mcp_tool_calls_total
from app.infrastructure.llm.llm_client import llm_client
from app.mcp.interfaces import IMcpServerService, IMcpToolService
from app.mcp.models import McpServerModel, McpToolModel
from app.mcp.schemas import (
    McpServerCreate, McpServerUpdate, McpServerResponse,
    McpToolResponse, McpConnectionTestResult, McpDebugResult,
)

logger = logging.getLogger(__name__)


class McpServerService(IMcpServerService):
    """MCP server service - CRUD + 连通性测试"""

    async def create_server(self, db: Session, body: McpServerCreate) -> McpServerResponse:
        """创建 MCP Server"""
        model = McpServerModel(
            name=body.name,
            url=body.url,
            enabled=body.enabled,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return McpServerResponse.from_orm(model)

    async def get_server(self, db: Session, server_id: int) -> McpServerResponse:
        """查询单个 MCP Server"""
        model = McpServerModel.find_all(db).filter_by(id=server_id).first()
        if not model:
            raise BizException(ErrorCode.MCP_SERVER_NOT_FOUND)
        return McpServerResponse.from_orm(model)

    async def list_servers(self, db: Session, page: int = 1, page_size: int = 20) -> any:
        """分页查询 MCP Server 列表"""
        query = McpServerModel.find_all(db)
        items, total = paginate(query, page, page_size)
        dtos = [McpServerResponse.from_orm(item) for item in items]
        return to_page_result(dtos, total, page, page_size)

    async def update_server(
        self, db: Session, server_id: int, body: McpServerUpdate
    ) -> McpServerResponse:
        """更新 MCP Server，只改非空字段"""
        model = McpServerModel.find_all(db).filter_by(id=server_id).first()
        if not model:
            raise BizException(ErrorCode.MCP_SERVER_NOT_FOUND)
        if body.name is not None:
            model.name = body.name
        if body.url is not None:
            model.url = body.url
        if body.enabled is not None:
            model.enabled = body.enabled
        db.commit()
        db.refresh(model)
        return McpServerResponse.from_orm(model)

    async def delete_server(self, db: Session, server_id: int) -> None:
        """删除 MCP Server（逻辑删除），删除前检查是否有 Agent 关联"""
        model = McpServerModel.find_all(db).filter_by(id=server_id).first()
        if not model:
            raise BizException(ErrorCode.MCP_SERVER_NOT_FOUND)

        # 查询该 server 下所有未删除的 tool id
        tool_ids = [
            t.id for t in McpToolModel.find_all(db)
            .filter_by(server_id=server_id)
            .all()
        ]

        # 检查 tb_agent_tool 是否有关联记录
        if tool_ids:
            bound = (
                AgentToolModel.find_all(db)
                .filter(AgentToolModel.mcp_tool_id.in_(tool_ids))
                .first()
            )
            if bound:
                raise BizException(ErrorCode.MCP_SERVER_IN_USE)

        model.soft_delete()
        db.commit()

    async def test_connection(self, db: Session, server_id: int) -> McpConnectionTestResult:
        """测试 MCP Server 连通性（JSON-RPC），成功时全量替换工具列表"""
        model = McpServerModel.find_all(db).filter_by(id=server_id).first()
        if not model:
            raise BizException(ErrorCode.MCP_SERVER_NOT_FOUND)

        url = model.url.rstrip("/")

        try:
            start = time.monotonic()
            result = await llm_client.admin_post(
                url,
                headers={"Content-Type": "application/json"},
                body={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                timeout=10.0,
            )
            elapsed = time.monotonic() - start
            logger.info(f"MCP test_connection {url} succeeded ({elapsed:.2f}s)")

            body = result.get("body", result)

            # JSON-RPC 错误响应
            if "error" in body:
                err = body["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return McpConnectionTestResult(success=False, error_message=msg)

            raw_tools = body.get("result", {}).get("tools", [])

            # 全量替换：先物理删旧工具，再插入新的
            db.query(McpToolModel).filter_by(server_id=server_id).delete()
            db.flush()

            tool_dtos = []
            for raw in raw_tools:
                input_schema_obj = raw.get("inputSchema", {})
                input_schema_str = json.dumps(input_schema_obj, ensure_ascii=False) if input_schema_obj else ""
                tool_model = McpToolModel(
                    server_id=server_id,
                    name=raw.get("name", ""),
                    description=raw.get("description", ""),
                    input_schema=input_schema_str,
                )
                db.add(tool_model)
                db.flush()
                tool_dtos.append(McpToolResponse.from_orm(tool_model))

            db.commit()

            return McpConnectionTestResult(
                success=True,
                tool_count=len(tool_dtos),
                tools=tool_dtos,
            )
        except BizException:
            raise
        except Exception as e:
            logger.error(f"MCP test_connection {url} failed: {e}")
            return McpConnectionTestResult(
                success=False,
                error_message=str(e),
            )

    async def debug_tool(
        self, db: Session, server_id: int, tool_name: str, arguments: dict
    ) -> McpDebugResult:
        """调试 MCP 工具：按名称查找工具，调用并记录耗时"""
        tool = (
            McpToolModel.find_all(db)
            .filter_by(server_id=server_id, name=tool_name)
            .first()
        )
        if not tool:
            raise BizException(ErrorCode.MCP_TOOL_NOT_FOUND, message=f"工具不存在: {tool_name}")

        start = time.monotonic()
        result_text = await McpToolService().call_tool(db, tool.id, arguments)
        elapsed = int((time.monotonic() - start) * 1000)

        return McpDebugResult(result=result_text, elapsed_ms=elapsed)


class McpToolService(IMcpToolService):
    """MCP tool service - 按服务器查询工具列表"""

    async def list_tools_by_server(
        self, db: Session, server_id: int, page: int = 1, page_size: int = 20
    ) -> any:
        """分页查询指定 MCP Server 下的工具列表"""
        query = McpToolModel.find_all(db).filter_by(server_id=server_id)
        items, total = paginate(query, page, page_size)
        dtos = [McpToolResponse.from_orm(item) for item in items]
        return to_page_result(dtos, total, page, page_size)

    async def list_all_tools_by_server(self, db: Session, server_id: int) -> list[McpToolResponse]:
        """查询指定 MCP Server 下的全部工具（不分页）"""
        items = McpToolModel.find_all(db).filter_by(server_id=server_id).all()
        return [McpToolResponse.from_orm(item) for item in items]

    async def get_tool_by_id(self, db: Session, tool_id: int) -> McpToolResponse:
        """根据 id 查询单个工具"""
        model = McpToolModel.find_all(db).filter_by(id=tool_id).first()
        if not model:
            raise BizException(ErrorCode.MCP_TOOL_NOT_FOUND)
        return McpToolResponse.from_orm(model)

    async def get_tools_by_ids(self, db: Session, tool_ids: list[int]) -> list[McpToolResponse]:
        """根据 id 列表批量查询工具"""
        if not tool_ids:
            return []
        models = McpToolModel.find_all(db).filter(McpToolModel.id.in_(tool_ids)).all()
        return [McpToolResponse.from_orm(m) for m in models]

    # ── 以下方法为接口兼容保留，暂不实现 ──

    async def create_tool(self, db: Session, server_id: int, data):
        raise NotImplementedError("MCP tools are auto-discovered via test-connection")

    async def get_tool(self, db: Session, tool_id: int):
        return await self.get_tool_by_id(db, tool_id)

    async def list_tools(self, db: Session, server_id, page: int, page_size: int):
        return await self.list_tools_by_server(db, server_id, page, page_size)

    async def update_tool(self, db: Session, tool_id: int, data):
        raise NotImplementedError("MCP tools are auto-discovered via test-connection")

    async def delete_tool(self, db: Session, tool_id: int) -> bool:
        raise NotImplementedError("MCP tools are auto-discovered via test-connection")

    async def call_tool(self, db: Session, tool_id: int, arguments: dict) -> str:
        """调用 MCP 工具（JSON-RPC tools/call），返回工具执行结果文本"""
        tool = McpToolModel.find_all(db).filter_by(id=tool_id).first()
        if not tool:
            raise BizException(ErrorCode.MCP_TOOL_NOT_FOUND)

        server = McpServerModel.find_all(db).filter_by(id=tool.server_id).first()
        if not server:
            raise BizException(ErrorCode.MCP_SERVER_NOT_FOUND)

        url = server.url.rstrip("/")

        try:
            result = await llm_client.admin_post(
                url,
                headers={"Content-Type": "application/json"},
                body={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": tool.name, "arguments": arguments},
                },
                timeout=30.0,
            )

            body = result.get("body", result)

            if "error" in body:
                err = body["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                raise BizException(ErrorCode.MCP_CALL_FAILED, message=msg)

            content = body.get("result", {}).get("content", [])
            texts = [item["text"] for item in content if item.get("type") == "text" and "text" in item]
            result_text = "\n".join(texts)
            mcp_tool_calls_total.labels(tool_name=tool.name, status="success").inc()
            return result_text

        except BizException:
            mcp_tool_calls_total.labels(tool_name=tool.name, status="fail").inc()
            raise
        except Exception as e:
            logger.error(f"MCP call_tool {tool.name} on {url} failed: {e}")
            mcp_tool_calls_total.labels(tool_name=tool.name, status="fail").inc()
            raise BizException(ErrorCode.MCP_CALL_FAILED, message=str(e))
