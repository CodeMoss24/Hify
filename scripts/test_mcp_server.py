"""Simple JSON-RPC MCP test server for hify testing.
Provides 4 tools: get_current_time, calculate, echo, random_number.
"""
import json
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


class McpTestHandler(BaseHTTPRequestHandler):

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _tool_list(self):
        return [
            {
                "name": "get_current_time",
                "description": "获取当前日期和时间，返回 ISO 格式的时间字符串",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "calculate",
                "description": "执行四则运算，支持加减乘除。参数 expression 是一个数学表达式字符串，如 '2 + 3 * 4'",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，如 '2 + 3'",
                        },
                    },
                    "required": ["expression"],
                },
            },
            {
                "name": "echo",
                "description": "回显输入的文本，可用于测试工具调用是否正常工作",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "要回显的文本",
                        },
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "random_number",
                "description": "生成指定范围内的随机整数",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "min": {
                            "type": "integer",
                            "description": "最小值（含），默认 1",
                        },
                        "max": {
                            "type": "integer",
                            "description": "最大值（含），默认 100",
                        },
                    },
                    "required": [],
                },
            },
        ]

    def _call_tool(self, name, arguments):
        if name == "get_current_time":
            t = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
            return f"当前时间: {t}"

        elif name == "calculate":
            expr = arguments.get("expression", "")
            try:
                result = eval(expr, {"__builtins__": {}}, {})
                return f"计算结果: {expr} = {result}"
            except Exception as e:
                return f"计算错误: {str(e)}"

        elif name == "echo":
            text = arguments.get("text", "")
            return f"Echo: {text}"

        elif name == "random_number":
            lo = int(arguments.get("min", 1))
            hi = int(arguments.get("max", 100))
            n = random.randint(lo, hi)
            return f"随机数 ({lo}-{hi}): {n}"

        else:
            return f"未知工具: {name}"

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            req = json.loads(raw)

            method = req.get("method", "")
            req_id = req.get("id")

            if method == "tools/list":
                tools = self._tool_list()
                self._send_json({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": tools},
                })

            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                text = self._call_tool(tool_name, arguments)
                self._send_json({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                    },
                })

            else:
                self._send_json({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                })

        except Exception as e:
            self._send_json({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)},
            }, status=500)

    def do_GET(self):
        self._send_json({"status": "ok", "server": "hify-mcp-test"})


if __name__ == "__main__":
    port = 9001
    server = HTTPServer(("0.0.0.0", port), McpTestHandler)
    print(f"MCP test server listening on :{port}")
    server.serve_forever()
