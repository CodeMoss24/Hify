"""Refund MCP Server — JSON-RPC 端点，供 Hify MCP Client 发现和调用"""
import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.error_code import ErrorCode
from app.common.exceptions import BizException
from app.refund.service import RefundService

logger = logging.getLogger(__name__)

mcp_refund_router = APIRouter()

# ── 工具 Schema 定义 ───────────────────────────────────────

REFUND_TOOLS = [
    {
        "name": "check_refund_eligibility",
        "description": "查询订单退款资格。用户说'我要退款'时，先调此工具确认是否符合条件，再决定是否提交申请。不要跳过此步直接提交。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "订单号",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "submit_refund",
        "description": "提交退款申请。仅在用户确认退款意愿、且 check_refund_eligibility 返回 eligible=true 后调用。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号"},
                "user_id": {"type": "string", "description": "用户ID"},
                "amount": {"type": "integer", "description": "退款金额(分)"},
                "reason": {"type": "string", "description": "退款原因"},
            },
            "required": ["order_id", "user_id", "amount", "reason"],
        },
    },
    {
        "name": "get_refund_status",
        "description": "查询退款状态。用户问'退款到哪了''审批通过没'时调用。支持按订单号或退款单号查询。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号"},
                "refund_id": {"type": "integer", "description": "退款单号"},
            },
            "required": [],
        },
    },
    {
        "name": "cancel_refund",
        "description": "撤销退款申请。用户说'不退了''取消退款'时调用。只有待审核状态才能撤销。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "refund_id": {"type": "integer", "description": "退款单号"},
            },
            "required": ["refund_id"],
        },
    },
]


# ── JSON-RPC 请求处理 ──────────────────────────────────────

@mcp_refund_router.post("")
async def handle_jsonrpc(
    request: dict,
    db: Session = Depends(get_db),
) -> dict:
    """处理所有 JSON-RPC 请求（tools/list、tools/call）"""
    jsonrpc = request.get("jsonrpc", "2.0")
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    response_base = {"jsonrpc": jsonrpc}
    if req_id is not None:
        response_base["id"] = req_id

    if method == "tools/list":
        response_base["result"] = {"tools": REFUND_TOOLS}
        return response_base

    if method == "tools/call":
        return await _handle_tools_call(response_base, params, db)

    # 未知方法
    response_base["error"] = {"code": -32601, "message": "Method not found"}
    return response_base


async def _handle_tools_call(response_base: dict, params: dict, db: Session) -> dict:
    """处理 tools/call 请求"""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    service = RefundService()

    try:
        result_dto = await _dispatch_tool(service, db, tool_name, arguments)
        text = json.dumps(result_dto.model_dump(), ensure_ascii=False)
        response_base["result"] = {
            "content": [{"type": "text", "text": text}]
        }
    except BizException as e:
        response_base["error"] = {"code": -1, "message": e.message}
    except Exception as e:
        logger.error(f"MCP tools/call {tool_name} failed: {e}")
        response_base["error"] = {"code": -1, "message": str(e)}

    return response_base


async def _dispatch_tool(service: RefundService, db: Session, name: str, args: dict):
    """根据工具名路由到 RefundService 对应方法"""
    if name == "check_refund_eligibility":
        return await service.check_eligibility(db, args["order_id"])

    if name == "submit_refund":
        return await service.submit_refund(
            db,
            order_id=args["order_id"],
            user_id=args["user_id"],
            amount=args["amount"],
            reason=args.get("reason", ""),
        )

    if name == "get_refund_status":
        return await service.get_status(
            db,
            order_id=args.get("order_id"),
            refund_id=args.get("refund_id"),
        )

    if name == "cancel_refund":
        return await service.cancel_refund(db, args["refund_id"])

    raise BizException(ErrorCode.PARAM_ERROR, message=f"未知工具: {name}")
