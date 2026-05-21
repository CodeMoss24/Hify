"""测试 WorkflowEngine — 工作流执行引擎"""
from app.workflow.engine import WorkflowEngine
from app.workflow.context import ExecutionContext
from app.workflow.models import WorkflowEdgeModel


def _make_edge(source, target, condition=None):
    """辅助函数：快速构造一条边"""
    edge = WorkflowEdgeModel()
    edge.source_node_key = source
    edge.target_node_key = target
    edge.condition = condition or ""
    return edge


class TestFindNextNode:
    """测试 _find_next_node() — 条件分支路由"""

    def test_should_follow_matched_condition_branch(self):
        """CONDITION 节点 + ctx 中 result 匹配到某条边的 condition → 走那条边"""
        engine = WorkflowEngine()
        edge_map = {
            "cond1": [
                _make_edge("cond1", "node_yes", condition="yes"),
                _make_edge("cond1", "node_no", condition="no"),
            ]
        }
        ctx = ExecutionContext("hello")
        ctx.set("cond1", "result", "yes")

        next_node = engine._find_next_node(edge_map, "cond1", "CONDITION", ctx)

        assert next_node == "node_yes"

    def test_should_walk_default_edge_when_condition_not_matched(self):
        """CONDITION 节点 + ctx 结果不匹配任何 condition → 走首条空 condition 边"""
        engine = WorkflowEngine()
        edge_map = {
            "cond1": [
                _make_edge("cond1", "node_yes", condition="yes"),
                _make_edge("cond1", "node_default"),  # 无 condition = 默认边
            ]
        }
        ctx = ExecutionContext("hello")
        ctx.set("cond1", "result", "unknown_value")

        next_node = engine._find_next_node(edge_map, "cond1", "CONDITION", ctx)

        assert next_node == "node_default"

    def test_should_skip_conditional_edges_for_non_condition_node(self):
        """非 CONDITION 节点 → 跳过带 condition 的边，只走空 condition 边"""
        engine = WorkflowEngine()
        edge_map = {
            "llm1": [
                _make_edge("llm1", "node_branch", condition="yes"),
                _make_edge("llm1", "node_next"),  # 无 condition，唯一可走的边
            ]
        }
        ctx = ExecutionContext("hello")

        next_node = engine._find_next_node(edge_map, "llm1", "LLM", ctx)

        assert next_node == "node_next"