"""Provider API 路由"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.response import ApiResponse
from app.provider.interfaces import IProviderService
from app.provider.schemas import ProviderCreate, ProviderUpdate, ProviderResponse
from app.provider.service import ProviderService

router = APIRouter()


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
