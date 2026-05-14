"""Provider service implementation - complete CRUD样板"""
from sqlalchemy.orm import Session

from app.common.cache_helper import CacheHelper
from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.provider.interfaces import IProviderService
from app.provider.models import ProviderModel
from app.provider.schemas import ProviderCreate, ProviderUpdate, ProviderResponse
from app.common.redis_client import redis_client


class ProviderService(IProviderService):
    """Provider service - complete CRUD standard implementation"""

    def __init__(self):
        self._cache = CacheHelper(redis_client)

    async def list_providers(self, db: Session, page: int = 1, page_size: int = 20) -> any:
        """分页查询 Provider 列表"""
        query = ProviderModel.find_all(db)
        items, total = paginate(query, page, page_size)
        dtos = [ProviderResponse.from_orm(item) for item in items]
        return to_page_result(dtos, total, page, page_size)

    async def create_provider(self, db: Session, body: ProviderCreate) -> ProviderResponse:
        """创建 Provider"""
        model = ProviderModel(
            name=body.name,
            provider_type=body.provider_type,
            base_url=body.base_url,
            api_key=body.api_key,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        # 失效缓存
        await self._cache.evict_pattern("provider:*")
        return ProviderResponse.from_orm(model)

    async def get_provider(self, db: Session, provider_id: int) -> ProviderResponse:
        """查询单个 Provider"""
        model = ProviderModel.find_all(db).filter_by(id=provider_id).first()
        if not model:
            raise BizException(ErrorCode.PROVIDER_NOT_FOUND)
        return ProviderResponse.from_orm(model)

    async def update_provider(
        self, db: Session, provider_id: int, body: ProviderUpdate
    ) -> ProviderResponse:
        """更新 Provider，只改非空字段"""
        model = ProviderModel.find_all(db).filter_by(id=provider_id).first()
        if not model:
            raise BizException(ErrorCode.PROVIDER_NOT_FOUND)
        if body.name is not None:
            model.name = body.name
        if body.base_url is not None:
            model.base_url = body.base_url
        if body.api_key is not None:
            model.api_key = body.api_key
        db.commit()
        db.refresh(model)
        # 失效缓存
        await self._cache.evict_pattern("provider:*")
        return ProviderResponse.from_orm(model)

    async def delete_provider(self, db: Session, provider_id: int) -> None:
        """删除 Provider（逻辑删除）"""
        model = ProviderModel.find_all(db).filter_by(id=provider_id).first()
        if not model:
            raise BizException(ErrorCode.PROVIDER_NOT_FOUND)
        model.soft_delete()
        db.commit()
        # 失效缓存
        await self._cache.evict_pattern("provider:*")
