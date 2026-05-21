"""MCP API 路由"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.response import ApiResponse
from app.mcp.interfaces import IMcpServerService, IMcpToolService
from app.mcp.schemas import (
    McpServerCreate, McpServerUpdate, McpServerResponse,
    McpToolResponse, McpConnectionTestResult, McpDebugRequest,
)
from app.mcp.service import McpServerService, McpToolService

router = APIRouter()


# ── MCP Server 端点 ──────────────────────────────────────


@router.post("/mcp-servers", response_model=ApiResponse)
async def create_mcp_server(
    body: McpServerCreate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """创建 MCP Server"""
    server_service: IMcpServerService = McpServerService()
    server = await server_service.create_server(db, body)
    return ApiResponse.ok(data=server)


@router.get("/mcp-servers", response_model=ApiResponse)
async def list_mcp_servers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """分页查询 MCP Server 列表"""
    server_service: IMcpServerService = McpServerService()
    page_result = await server_service.list_servers(db, page, page_size)
    return ApiResponse.ok(data=page_result)


@router.get("/mcp-servers/{server_id}", response_model=ApiResponse)
async def get_mcp_server(
    server_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """查询 MCP Server 详情（含工具列表）"""
    server_service: IMcpServerService = McpServerService()
    server = await server_service.get_server(db, server_id)

    tool_service: IMcpToolService = McpToolService()
    tools = await tool_service.list_all_tools_by_server(db, server_id)

    return ApiResponse.ok(data={"server": server, "tools": tools})


@router.put("/mcp-servers/{server_id}", response_model=ApiResponse)
async def update_mcp_server(
    server_id: int = Path(..., ge=1),
    body: McpServerUpdate = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """更新 MCP Server"""
    server_service: IMcpServerService = McpServerService()
    server = await server_service.update_server(db, server_id, body)
    return ApiResponse.ok(data=server)


@router.delete("/mcp-servers/{server_id}", response_model=ApiResponse)
async def delete_mcp_server(
    server_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """删除 MCP Server（逻辑删除）"""
    server_service: IMcpServerService = McpServerService()
    await server_service.delete_server(db, server_id)
    return ApiResponse.ok(message="deleted")


@router.post("/mcp-servers/{server_id}/test-connection", response_model=ApiResponse)
async def test_mcp_connection(
    server_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """测试 MCP Server 连通性，自动拉取工具列表"""
    server_service: IMcpServerService = McpServerService()
    result = await server_service.test_connection(db, server_id)
    return ApiResponse.ok(data=result)


@router.post("/mcp-servers/{server_id}/debug", response_model=ApiResponse)
async def debug_mcp_tool(
    server_id: int = Path(..., ge=1),
    body: McpDebugRequest = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """调试 MCP 工具：按名称调用并返回结果和耗时"""
    server_service: IMcpServerService = McpServerService()
    result = await server_service.debug_tool(db, server_id, body.tool_name, body.arguments)
    return ApiResponse.ok(data=result)
