"""Workflow API 路由"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.response import ApiResponse
from app.workflow.interfaces import IWorkflowService
from app.workflow.schemas import WorkflowCreate, WorkflowUpdate, WorkflowResponse
from app.workflow.service import WorkflowService

router = APIRouter()


def _workflow_service() -> IWorkflowService:
    """构造 WorkflowService 实例"""
    return WorkflowService()


# ── Workflow CRUD 端点 ──────────────────────────────────────


@router.post("/workflows", response_model=ApiResponse)
async def create_workflow(
    body: WorkflowCreate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """创建工作流（含 nodes 和 edges）"""
    workflow_service = _workflow_service()
    workflow = await workflow_service.create_workflow(db, body)
    return ApiResponse.ok(data=workflow)


@router.get("/workflows", response_model=ApiResponse)
async def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """分页查询工作流列表（只返回主表信息）"""
    workflow_service = _workflow_service()
    page_result = await workflow_service.list_workflows(db, page, page_size)
    return ApiResponse.ok(data=page_result)


@router.get("/workflows/{workflow_id}", response_model=ApiResponse)
async def get_workflow(
    workflow_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """查询单个工作流（含完整 nodes 和 edges）"""
    workflow_service = _workflow_service()
    workflow = await workflow_service.get_workflow(db, workflow_id)
    return ApiResponse.ok(data=workflow)


@router.put("/workflows/{workflow_id}", response_model=ApiResponse)
async def update_workflow(
    workflow_id: int = Path(..., ge=1),
    body: WorkflowUpdate = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """更新工作流（nodes/edges 采用先删后插全量替换）"""
    workflow_service = _workflow_service()
    workflow = await workflow_service.update_workflow(db, workflow_id, body)
    return ApiResponse.ok(data=workflow)


@router.delete("/workflows/{workflow_id}", response_model=ApiResponse)
async def delete_workflow(
    workflow_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """删除工作流（逻辑删除，级联软删关联的 nodes 和 edges）"""
    workflow_service = _workflow_service()
    await workflow_service.delete_workflow(db, workflow_id)
    return ApiResponse.ok(message="deleted")
