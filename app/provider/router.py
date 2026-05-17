"""Provider API 路由"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.response import ApiResponse
from app.provider.interfaces import IProviderService, IModelService
from app.provider.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    ModelCreate, ModelUpdate, ModelResponse,
    ConnectionTestResult,
)
from app.provider.service import ProviderService, ModelService

router = APIRouter()


# ── Provider 端点 ────────────────────────────────────────


@router.post("/providers", response_model=ApiResponse)
async def create_provider(
    body: ProviderCreate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """创建 Provider"""
    provider_service: IProviderService = ProviderService()
    provider = await provider_service.create_provider(db, body)
    return ApiResponse.ok(data=provider)


@router.get("/providers", response_model=ApiResponse)
async def list_providers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """分页查询 Provider 列表"""
    provider_service: IProviderService = ProviderService()
    page_result = await provider_service.list_providers(db, page, page_size)
    return ApiResponse.ok(data=page_result)


@router.get("/providers/{provider_id}", response_model=ApiResponse)
async def get_provider(
    provider_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """查询单个 Provider"""
    provider_service: IProviderService = ProviderService()
    provider = await provider_service.get_provider(db, provider_id)
    return ApiResponse.ok(data=provider)


@router.put("/providers/{provider_id}", response_model=ApiResponse)
async def update_provider(
    provider_id: int = Path(..., ge=1),
    body: ProviderUpdate = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """更新 Provider"""
    provider_service: IProviderService = ProviderService()
    provider = await provider_service.update_provider(db, provider_id, body)
    return ApiResponse.ok(data=provider)


@router.delete("/providers/{provider_id}", response_model=ApiResponse)
async def delete_provider(
    provider_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """删除 Provider（逻辑删除）"""
    provider_service: IProviderService = ProviderService()
    await provider_service.delete_provider(db, provider_id)
    return ApiResponse.ok(message="deleted")


@router.post("/providers/{provider_id}/test-connection", response_model=ApiResponse)
async def test_connection(
    provider_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """测试 Provider 连通性"""
    provider_service: IProviderService = ProviderService()
    result = await provider_service.test_connection(db, provider_id)
    return ApiResponse.ok(data=result)


# ── Model 端点 ───────────────────────────────────────────


@router.post("/models", response_model=ApiResponse)
async def create_model(
    body: ModelCreate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """创建模型"""
    model_service: IModelService = ModelService()
    model = await model_service.create_model(db, body)
    return ApiResponse.ok(data=model)


@router.get("/providers/{provider_id}/models", response_model=ApiResponse)
async def list_models(
    provider_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """分页查询指定 Provider 下的模型列表"""
    model_service: IModelService = ModelService()
    page_result = await model_service.list_models(db, provider_id, page, page_size)
    return ApiResponse.ok(data=page_result)


@router.get("/models/{model_id}", response_model=ApiResponse)
async def get_model(
    model_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """查询单个模型"""
    model_service: IModelService = ModelService()
    model = await model_service.get_model(db, model_id)
    return ApiResponse.ok(data=model)


@router.put("/models/{model_id}", response_model=ApiResponse)
async def update_model(
    model_id: int = Path(..., ge=1),
    body: ModelUpdate = ...,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """更新模型"""
    model_service: IModelService = ModelService()
    model = await model_service.update_model(db, model_id, body)
    return ApiResponse.ok(data=model)


@router.delete("/models/{model_id}", response_model=ApiResponse)
async def delete_model(
    model_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """删除模型（逻辑删除）"""
    model_service: IModelService = ModelService()
    await model_service.delete_model(db, model_id)
    return ApiResponse.ok(message="deleted")
