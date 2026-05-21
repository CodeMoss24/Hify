"""Workflow Execution Context"""
from collections import OrderedDict
from typing import Any, Dict
import re


class ExecutionContext:
    """工作流执行上下文

    内部用有序字典存变量，支持变量引用替换
    """

    def __init__(self, user_message: str):
        self._data: OrderedDict[str, Any] = OrderedDict()
        # 预写入用户消息
        self.set("start", "userMessage", user_message)

    def set(self, node_key: str, var_name: str, value: Any) -> None:
        """写入变量

        Args:
            node_key: 节点 key
            var_name: 变量名
            value: 变量值
        """
        key = f"{node_key}.{var_name}"
        self._data[key] = value

    def resolve(self, template: str) -> str:
        """替换模板中的变量占位符

        Args:
            template: 模板字符串，包含 {{node_key.var_name}}

        Returns:
            替换后的字符串。变量不存在时保留原占位符
        """
        if not template:
            return template

        # 匹配 {{node_key.var_name}} 格式
        pattern = r"{{([\w]+\.[\w]+)}}"

        def replace_var(match: re.Match) -> str:
            var_key = match.group(1)
            if var_key in self._data:
                value = self._data[var_key]
                return str(value) if value is not None else ""
            # 变量不存在，返回原占位符
            return match.group(0)

        return re.sub(pattern, replace_var, template)

    def get_all(self) -> Dict[str, Any]:
        """返回所有变量的只读视图

        Returns:
            变量字典
        """
        return dict(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        """获取单个变量

        Args:
            key: 变量键，格式 "node_key.var_name"
            default: 默认值

        Returns:
            变量值
        """
        return self._data.get(key, default)
