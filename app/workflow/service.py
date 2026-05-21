"""Workflow service implementation"""
from sqlalchemy.orm import Session

from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.workflow.interfaces import IWorkflowService
from app.workflow.models import WorkflowModel, WorkflowNodeModel, WorkflowEdgeModel
from app.workflow.schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowNodeResponse,
    WorkflowEdgeResponse,
)


class WorkflowService(IWorkflowService):
    """Workflow service - CRUD with nodes and edges"""

    async def create_workflow(self, db: Session, body: WorkflowCreate) -> WorkflowResponse:
        """创建工作流（在一个事务中创建主表、节点和连线）"""
        try:
            # 1. 创建主表记录
            workflow = WorkflowModel(
                name=body.name,
                description=body.description or "",
                status="DRAFT",
            )
            db.add(workflow)
            db.flush()  # 获取 workflow.id

            # 2. 批量创建节点
            nodes = []
            for node_body in body.nodes:
                node = WorkflowNodeModel(
                    workflow_id=workflow.id,
                    node_key=node_body.node_key,
                    name=node_body.name,
                    node_type=node_body.node_type,
                    config=node_body.config or {},
                    position_x=node_body.position_x or 0,
                    position_y=node_body.position_y or 0,
                )
                db.add(node)
                nodes.append(node)

            # 3. 批量创建连线
            edges = []
            for edge_body in body.edges:
                edge = WorkflowEdgeModel(
                    workflow_id=workflow.id,
                    source_node_key=edge_body.source_node_key,
                    target_node_key=edge_body.target_node_key,
                    condition=edge_body.condition or "",
                )
                db.add(edge)
                edges.append(edge)

            db.commit()
            db.refresh(workflow)

            # 4. 组装响应
            node_dtos = [WorkflowNodeResponse.from_orm(n) for n in nodes]
            edge_dtos = [WorkflowEdgeResponse.from_orm(e) for e in edges]
            return WorkflowResponse.from_orm(workflow, nodes=node_dtos, edges=edge_dtos)

        except Exception:
            db.rollback()
            raise

    async def get_workflow(self, db: Session, workflow_id: int) -> WorkflowResponse:
        """查询单个工作流（含完整 nodes 和 edges）"""
        workflow = WorkflowModel.find_all(db).filter_by(id=workflow_id).first()
        if not workflow:
            raise BizException(ErrorCode.WORKFLOW_NOT_FOUND)

        # 查询关联的节点和连线
        nodes = WorkflowNodeModel.find_all(db).filter_by(workflow_id=workflow_id).all()
        edges = WorkflowEdgeModel.find_all(db).filter_by(workflow_id=workflow_id).all()

        node_dtos = [WorkflowNodeResponse.from_orm(n) for n in nodes]
        edge_dtos = [WorkflowEdgeResponse.from_orm(e) for e in edges]
        return WorkflowResponse.from_orm(workflow, nodes=node_dtos, edges=edge_dtos)

    async def list_workflows(self, db: Session, page: int = 1, page_size: int = 20):
        """分页查询工作流列表（只返回主表信息，不含 nodes/edges）"""
        query = WorkflowModel.find_all(db)
        items, total = paginate(query, page, page_size)

        dtos = []
        for item in items:
            dtos.append(WorkflowResponse.from_orm(item, nodes=[], edges=[]))

        return to_page_result(dtos, total, page, page_size)

    async def update_workflow(self, db: Session, workflow_id: int, body: WorkflowUpdate) -> WorkflowResponse:
        """更新工作流（nodes/edges 采用先删后插全量替换策略）"""
        workflow = WorkflowModel.find_all(db).filter_by(id=workflow_id).first()
        if not workflow:
            raise BizException(ErrorCode.WORKFLOW_NOT_FOUND)

        try:
            # 1. 更新主表字段
            if body.name is not None:
                workflow.name = body.name
            if body.description is not None:
                workflow.description = body.description
            if body.status is not None:
                workflow.status = body.status

            # 2. 如果提供了新的 nodes/edges，则先删后插全量替换
            new_nodes = []
            new_edges = []

            if body.nodes is not None:
                # 逻辑删除旧节点
                WorkflowNodeModel.find_all(db).filter_by(workflow_id=workflow_id).update(
                    {"deleted": 1}
                )
                # 插入新节点
                for node_body in body.nodes:
                    node = WorkflowNodeModel(
                        workflow_id=workflow_id,
                        node_key=node_body.node_key,
                        name=node_body.name,
                        node_type=node_body.node_type,
                        config=node_body.config or {},
                        position_x=node_body.position_x or 0,
                        position_y=node_body.position_y or 0,
                    )
                    db.add(node)
                    new_nodes.append(node)

            if body.edges is not None:
                # 逻辑删除旧连线
                WorkflowEdgeModel.find_all(db).filter_by(workflow_id=workflow_id).update(
                    {"deleted": 1}
                )
                # 插入新连线
                for edge_body in body.edges:
                    edge = WorkflowEdgeModel(
                        workflow_id=workflow_id,
                        source_node_key=edge_body.source_node_key,
                        target_node_key=edge_body.target_node_key,
                        condition=edge_body.condition or "",
                    )
                    db.add(edge)
                    new_edges.append(edge)

            db.commit()
            db.refresh(workflow)

            # 3. 组装响应（如果没更新 nodes/edges，则重新查询现有数据）
            if body.nodes is None:
                nodes = WorkflowNodeModel.find_all(db).filter_by(workflow_id=workflow_id).all()
                node_dtos = [WorkflowNodeResponse.from_orm(n) for n in nodes]
            else:
                node_dtos = [WorkflowNodeResponse.from_orm(n) for n in new_nodes]

            if body.edges is None:
                edges = WorkflowEdgeModel.find_all(db).filter_by(workflow_id=workflow_id).all()
                edge_dtos = [WorkflowEdgeResponse.from_orm(e) for e in edges]
            else:
                edge_dtos = [WorkflowEdgeResponse.from_orm(e) for e in new_edges]

            return WorkflowResponse.from_orm(workflow, nodes=node_dtos, edges=edge_dtos)

        except Exception:
            db.rollback()
            raise

    async def delete_workflow(self, db: Session, workflow_id: int) -> None:
        """删除工作流（逻辑删除，级联软删关联的 nodes 和 edges）"""
        workflow = WorkflowModel.find_all(db).filter_by(id=workflow_id).first()
        if not workflow:
            raise BizException(ErrorCode.WORKFLOW_NOT_FOUND)

        # 级联软删关联表
        WorkflowNodeModel.find_all(db).filter_by(workflow_id=workflow_id).update(
            {"deleted": 1}
        )
        WorkflowEdgeModel.find_all(db).filter_by(workflow_id=workflow_id).update(
            {"deleted": 1}
        )

        workflow.soft_delete()
        db.commit()
