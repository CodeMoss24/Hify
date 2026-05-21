"""
Mock MCP Server — 模拟订单服务和退款服务

启动方式：
  python mock_mcp_server.py
  或指定端口：MOCK_PORT=9001 python mock_mcp_server.py

支持的 MCP 工具：
  - query_order: 查询订单状态
  - check_refund_eligibility: 检查退款资格
  - submit_refund: 提交退款申请
  - get_refund_status: 查询退款进度
  - cancel_refund: 撤销退款申请
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 模拟数据库（内存）──────────────────────────────

ORDERS = {
    "ORD-12345": {"user_id": "U001", "status": "已完成", "amount": 29900, "item": "蓝牙耳机"},
    "ORD-12346": {"user_id": "U002", "status": "已发货", "amount": 59900, "item": "机械键盘"},
    "ORD-12347": {"user_id": "U001", "status": "已完成", "amount": 19900, "item": "手机壳"},
    "ORD-99999": {"user_id": "U999", "status": "已退款", "amount": 9900,  "item": "测试商品"},
}

REFUNDS: dict[int, dict] = {}
_refund_id_seq = 1001

# ── 工具定义 ───────────────────────────────────────

TOOLS = [
    {
        "name": "query_order",
        "description": "查询用户订单状态，用户询问订单、物流、快递时使用",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "orderId": {"type": "string"},
            },
            "required": ["userId"],
        },
    },
    {
        "name": "check_refund_eligibility",
        "description": "查询订单退款资格。用户说'我要退款'时，先调此工具确认是否符合条件，再决定是否提交申请。不要跳过此步直接提交。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号"},
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

# ── JSON-RPC 入口 ──────────────────────────────────

@app.post("/")
async def mcp_endpoint(body: dict):
    method = body.get("method")

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": body.get("id"), "result": {"tools": TOOLS}}

    if method == "tools/call":
        return _handle_tool_call(body)

    return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def _handle_tool_call(body: dict) -> dict:
    params = body.get("params", {})
    tool_name = params.get("name", "")
    args = params.get("arguments", {})
    req_id = body.get("id")

    try:
        if tool_name == "query_order":
            text = _query_order(args)
        elif tool_name == "check_refund_eligibility":
            text = _check_refund_eligibility(args)
        elif tool_name == "submit_refund":
            text = _submit_refund(args)
        elif tool_name == "get_refund_status":
            text = _get_refund_status(args)
        elif tool_name == "cancel_refund":
            text = _cancel_refund(args)
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": text}]}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": f"工具执行失败: {e}"}]}}


# ── 工具实现 ───────────────────────────────────────

def _query_order(args: dict) -> str:
    order_id = args.get("orderId", "")
    user_id = args.get("userId", "")

    if not order_id:
        user_orders = {k: v for k, v in ORDERS.items() if v["user_id"] == user_id}
        if not user_orders:
            return f"用户 {user_id} 没有订单记录"
        lines = [f"用户 {user_id} 的订单列表："]
        for oid, o in user_orders.items():
            lines.append(f"  {oid}: {o['item']} ¥{o['amount']/100:.2f} [{o['status']}]")
        return "\n".join(lines)

    order = ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在"
    return f"订单 {order_id}: {order['item']} ¥{order['amount']/100:.2f} [{order['status']}]"


def _check_refund_eligibility(args: dict) -> str:
    order_id = args.get("order_id", "")

    order = ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在，无法申请退款"

    if order["status"] == "已退款":
        return f"订单 {order_id} 已退款，不能重复申请"

    if order["status"] == "已发货":
        return f"订单 {order_id} 状态为「已发货」，需先确认收货才能申请退款。是否确认收货后申请？"

    # 已完成/待发货 等状态允许退款
    return (
        f"订单 {order_id} 符合退款条件。\n"
        f"商品: {order['item']}\n"
        f"金额: ¥{order['amount']/100:.2f}（金额(分): {order['amount']}）\n"
        f"用户: {order['user_id']}\n"
        f"请确认是否提交退款申请？"
    )


def _submit_refund(args: dict) -> str:
    global _refund_id_seq
    order_id = args.get("order_id", "")
    user_id = args.get("user_id", "")
    amount = args.get("amount", 0)
    reason = args.get("reason", "未说明")

    order = ORDERS.get(order_id)
    if not order:
        return f"提交失败：订单 {order_id} 不存在"

    ref_id = _refund_id_seq
    _refund_id_seq += 1

    REFUNDS[ref_id] = {
        "refund_id": ref_id,
        "order_id": order_id,
        "user_id": user_id,
        "amount": amount,
        "reason": reason,
        "status": "待审核",
    }

    return (
        f"退款申请已提交！\n"
        f"退款单号: {ref_id}\n"
        f"订单号: {order_id}\n"
        f"金额: ¥{amount/100:.2f}\n"
        f"原因: {reason}\n"
        f"状态: 待审核（预计 1-3 个工作日完成审核）"
    )


def _get_refund_status(args: dict) -> str:
    order_id = args.get("order_id", "")
    refund_id = args.get("refund_id", 0)

    if refund_id and refund_id in REFUNDS:
        r = REFUNDS[refund_id]
        return f"退款单 {refund_id}: 订单 {r['order_id']} ¥{r['amount']/100:.2f} [{r['status']}]"

    if order_id:
        matches = [r for r in REFUNDS.values() if r["order_id"] == order_id]
        if not matches:
            return f"订单 {order_id} 没有退款记录"
        r = matches[0]
        return f"退款单 {r['refund_id']}: 订单 {r['order_id']} ¥{r['amount']/100:.2f} [{r['status']}]"

    if not REFUNDS:
        return "目前没有任何退款记录"
    lines = ["所有退款记录："]
    for r in REFUNDS.values():
        lines.append(f"  #{r['refund_id']} 订单{r['order_id']} ¥{r['amount']/100:.2f} [{r['status']}]")
    return "\n".join(lines)


def _cancel_refund(args: dict) -> str:
    refund_id = args.get("refund_id", 0)

    if refund_id not in REFUNDS:
        return f"退款单 {refund_id} 不存在"

    r = REFUNDS[refund_id]
    if r["status"] != "待审核":
        return f"退款单 {refund_id} 当前状态为「{r['status']}」，只有「待审核」状态的退款单才能撤销"

    r["status"] = "已撤销"
    return f"退款单 {refund_id}（订单 {r['order_id']} ¥{r['amount']/100:.2f}）已成功撤销"


if __name__ == "__main__":
    port = int(os.getenv("MOCK_PORT", "9001"))
    print(f"Mock MCP Server starting on http://localhost:{port}")
    print(f"Supported tools: {[t['name'] for t in TOOLS]}")
    uvicorn.run(app, host="0.0.0.0", port=port)
