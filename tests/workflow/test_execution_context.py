"""测试 ExecutionContext — 工作流变量解析"""
from app.workflow.context import ExecutionContext


class TestResolve:
    """测试 resolve() — 模板变量 {{node.var}} 替换"""

    def test_should_replace_existing_variable(self):
        ctx = ExecutionContext("你好")
        result = ctx.resolve("用户说：{{start.userMessage}}")
        assert result == "用户说：你好"

    def test_should_keep_placeholder_when_variable_not_found(self):
        ctx = ExecutionContext("你好")
        result = ctx.resolve("{{unknown.var}}")
        assert result == "{{unknown.var}}"

    def test_should_return_empty_string_when_template_is_empty(self):
        ctx = ExecutionContext("你好")
        result = ctx.resolve("")
        assert result == ""