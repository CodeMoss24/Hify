"""Workflow Engine - 工作流执行核心"""
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.workflow.context import ExecutionContext
from app.workflow.models import (
    WorkflowModel,
    WorkflowNodeModel,
    WorkflowEdgeModel,
    WorkflowRunModel,
    WorkflowNodeRunModel,
)
from app.provider.models import ProviderModel
from app.provider.adapter_factory import provider_adapter_factory
from app.provider.interfaces import IModelService, IProviderService
from app.provider.service import ModelService, ProviderService


class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self):
        self._model_service: IModelService = ModelService()
        self._provider_service: IProviderService = ProviderService()

    async def execute(self, workflow_id: int, user_message: str, db: Session) -> Dict[str, Any]:
        """执行工作流（async 方法）

        Args:
            workflow_id: 工作流 ID
            user_message: 用户消息
            db: 数据库 Session

        Returns:
            执行结果字典

        Raises:
            BizException: 执行出错时抛出
        """
        # 1. 加载工作流配置
        workflow = WorkflowModel.find_all(db).filter_by(id=workflow_id).first()
        if not workflow:
            raise BizException(ErrorCode.WORKFLOW_NOT_FOUND, f"Workflow {workflow_id} not found")

        nodes = WorkflowNodeModel.find_all(db).filter_by(workflow_id=workflow_id).all()
        edges = WorkflowEdgeModel.find_all(db).filter_by(workflow_id=workflow_id).all()

        # 构建 node_map 和 edge_map
        node_map: Dict[str, WorkflowNodeModel] = {n.node_key: n for n in nodes}
        edge_map: Dict[str, List[WorkflowEdgeModel]] = {}
        for edge in edges:
            if edge.source_node_key not in edge_map:
                edge_map[edge.source_node_key] = []
            edge_map[edge.source_node_key].append(edge)

        # 2. 创建 WorkflowRun 记录
        workflow_run = WorkflowRunModel(
            workflow_id=workflow_id,
            status="RUNNING",
            input={"user_message": user_message},
            started_at=datetime.utcnow(),
        )
        db.add(workflow_run)
        db.commit()
        db.refresh(workflow_run)

        # 3. 创建执行上下文
        ctx = ExecutionContext(user_message)
        last_llm_output = ""

        # 4. 找到 START 节点
        current_node_key = None
        for node in nodes:
            if node.node_type == "START":
                current_node_key = node.node_key
                break

        if not current_node_key:
            workflow_run.status = "FAILED"
            workflow_run.error_message = "No START node found"
            workflow_run.finished_at = datetime.utcnow()
            db.commit()
            raise BizException(ErrorCode.WORKFLOW_EXECUTE_FAILED, "No START node found")

        try:
            # 5. 主循环：逐节点执行
            step_count = 0
            max_steps = 50

            while current_node_key and step_count < max_steps:
                step_count += 1

                current_node = node_map.get(current_node_key)
                if not current_node:
                    raise BizException(ErrorCode.WORKFLOW_EXECUTE_FAILED, f"Node {current_node_key} not found")

                # 如果是 END 节点，结束执行
                if current_node.node_type == "END":
                    # 记录 END 节点执行
                    self._record_node_run(db, workflow_run.id, current_node, None, None, "SUCCESS", 0)
                    break

                node_start = time.monotonic()
                node_run = None

                try:
                    node_run = self._record_node_run(db, workflow_run.id, current_node, None, None, "RUNNING", 0)

                    node_output = None
                    if current_node.node_type == "LLM":
                        node_output = await self._execute_llm_node(db, current_node, ctx)
                        last_llm_output = node_output
                        ctx.set(current_node_key, "output", node_output)
                    elif current_node.node_type == "CONDITION":
                        # 执行 CONDITION 节点：解析表达式，存储结果
                        config = current_node.config or {}
                        expression = config.get("expression", "")
                        resolved_value = ctx.resolve(expression)
                        ctx.set(current_node_key, "result", resolved_value)
                        node_output = resolved_value
                    else:
                        # START/END/API_CALL
                        pass

                    # 更新节点执行记录
                    elapsed_ms = int((time.monotonic() - node_start) * 1000)
                    output_data = {"result": node_output} if node_output else None
                    self._update_node_run(db, node_run.id, "SUCCESS", None, output_data, elapsed_ms)

                except Exception as e:
                    error = str(e)
                    elapsed_ms = int((time.monotonic() - node_start) * 1000)
                    if node_run:
                        self._update_node_run(db, node_run.id, "FAILED", error, None, elapsed_ms)
                    raise

                # 找下一个节点（支持条件分支）
                current_node_key = self._find_next_node(edge_map, current_node_key, current_node.node_type, ctx)

            if step_count >= max_steps:
                raise BizException(ErrorCode.WORKFLOW_EXECUTE_FAILED, "Max steps exceeded")

            # 6. 执行成功，更新 WorkflowRun
            total_elapsed_ms = 0
            if workflow_run.started_at:
                total_elapsed_ms = int((datetime.utcnow() - workflow_run.started_at).total_seconds() * 1000)

            workflow_run.status = "SUCCESS"
            workflow_run.output = {"result": last_llm_output}
            workflow_run.finished_at = datetime.utcnow()
            workflow_run.elapsed_ms = total_elapsed_ms
            db.commit()

            return {"result": last_llm_output, "workflow_run_id": workflow_run.id}

        except Exception as e:
            # 执行失败，更新 WorkflowRun
            total_elapsed_ms = 0
            if workflow_run.started_at:
                total_elapsed_ms = int((datetime.utcnow() - workflow_run.started_at).total_seconds() * 1000)

            workflow_run.status = "FAILED"
            workflow_run.error_message = str(e)
            workflow_run.finished_at = datetime.utcnow()
            workflow_run.elapsed_ms = total_elapsed_ms
            db.commit()

            raise

    async def _execute_llm_node(self, db: Session, node: WorkflowNodeModel, ctx: ExecutionContext) -> str:
        """执行 LLM 节点

        Args:
            db: 数据库 Session
            node: LLM 节点
            ctx: 执行上下文

        Returns:
            LLM 响应文本
        """
        config = node.config or {}
        model_config_id = config.get("model_config_id")
        prompt_template = config.get("prompt", "")

        if not model_config_id:
            raise BizException(ErrorCode.WORKFLOW_EXECUTE_FAILED, "model_config_id not found in node config")

        # 解析 prompt 模板
        resolved_prompt = ctx.resolve(prompt_template)

        # 加载 model 和 provider
        model = await self._model_service.get_model(db, model_config_id)
        provider = await self._provider_service.get_provider(db, model.provider_id)

        # 获取 provider model
        provider_model = (
            db.query(ProviderModel)
            .filter_by(id=provider.id, deleted=0)
            .first()
        )
        if not provider_model:
            raise BizException(ErrorCode.PROVIDER_NOT_FOUND)

        adapter = provider_adapter_factory.get_adapter(provider.provider_type)

        # 调用 LLM
        messages = [{"role": "user", "content": resolved_prompt}]

        full_response = ""
        async for delta in adapter.stream_chat(
            provider=provider_model,
            model=model.model_id,
            messages=messages,
            agent_config={"temperature": 0.7, "max_tokens": 2048},
        ):
            full_response += delta

        return full_response

    def _find_next_node(
        self, edge_map: Dict[str, List[WorkflowEdgeModel]], current_node_key: str, current_node_type: str, ctx: ExecutionContext
    ) -> str | None:
        """找下一个节点（支持条件分支）

        Args:
            edge_map: 边映射
            current_node_key: 当前节点 key
            current_node_type: 当前节点类型
            ctx: 执行上下文

        Returns:
            下一个节点 key，或 None
        """
        out_edges = edge_map.get(current_node_key, [])
        if not out_edges:
            return None

        if current_node_type == "CONDITION":
            # CONDITION 节点：根据结果走对应分支
            condition_result = ctx.get(f"{current_node_key}.result")

            # 先找匹配 condition 的边
            for edge in out_edges:
                if edge.condition and edge.condition == condition_result:
                    return edge.target_node_key

            # 没匹配到，找第一条 condition 为空的边作为默认路径
            for edge in out_edges:
                if not edge.condition or edge.condition.strip() == "":
                    return edge.target_node_key

            # 都没有，返回 None（END）
            return None
        else:
            # 非 CONDITION 节点：只走 condition 为空的边
            for edge in out_edges:
                if not edge.condition or edge.condition.strip() == "":
                    return edge.target_node_key
            return None

    def _record_node_run(
        self,
        db: Session,
        workflow_run_id: int,
        node: WorkflowNodeModel,
        input_data: Any | None,
        output_data: Any | None,
        status: str,
        elapsed_ms: int,
    ) -> WorkflowNodeRunModel:
        """记录节点执行

        Args:
            db: 数据库 Session
            workflow_run_id: 工作流执行 ID
            node: 节点
            input_data: 输入数据
            output_data: 输出数据
            status: 状态
            elapsed_ms: 耗时

        Returns:
            节点执行记录
        """
        node_run = WorkflowNodeRunModel(
            workflow_run_id=workflow_run_id,
            node_key=node.node_key,
            node_type=node.node_type,
            status=status,
            input_data=input_data,
            output_data=output_data,
            elapsed_ms=elapsed_ms,
            started_at=datetime.utcnow() if status == "RUNNING" else None,
            finished_at=datetime.utcnow() if status in ("SUCCESS", "FAILED") else None,
        )
        db.add(node_run)
        db.commit()
        db.refresh(node_run)
        return node_run

    def _update_node_run(
        self,
        db: Session,
        node_run_id: int,
        status: str,
        error_message: str | None,
        output_data: Any | None,
        elapsed_ms: int,
    ) -> None:
        """更新节点执行记录

        Args:
            db: 数据库 Session
            node_run_id: 节点执行 ID
            status: 状态
            error_message: 错误信息
            output_data: 输出数据
            elapsed_ms: 耗时
        """
        node_run = db.query(WorkflowNodeRunModel).filter_by(id=node_run_id).first()
        if node_run:
            node_run.status = status
            if error_message:
                node_run.error_message = error_message
            if output_data:
                node_run.output_data = output_data
            node_run.elapsed_ms = elapsed_ms
            node_run.finished_at = datetime.utcnow()
            db.commit()


# 模块级单例
workflow_engine = WorkflowEngine()
