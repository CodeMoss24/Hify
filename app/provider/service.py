"""Provider & Model service implementation"""
import logging

from sqlalchemy.orm import Session

from app.common.cache_helper import CacheHelper
from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.common.redis_client import redis_client
from app.provider.interfaces import IProviderService, IModelService
from app.provider.models import ProviderModel, ModelModel
from app.provider.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    ModelCreate, ModelUpdate, ModelResponse,
    ConnectionTestResult,
)
from app.provider.adapter_factory import provider_adapter_factory

logger = logging.getLogger(__name__)


class ProviderService(IProviderService):
    """Provider service - CRUD for model providers"""

    def __init__(self):
        self._cache = CacheHelper(redis_client)

    async def list_providers(self, db: Session, page: int = 1, page_size: int = 20) -> any:
        """分页查询 Provider 列表，附带 Redis 健康状态"""
        query = ProviderModel.find_all(db)
        items, total = paginate(query, page, page_size)
        dtos = []
        for item in items:
            health = await redis_client.get(f"provider:health:{item.id}")
            dtos.append(ProviderResponse.from_orm(item, health=health))
        return to_page_result(dtos, total, page, page_size)

    async def create_provider(self, db: Session, body: ProviderCreate) -> ProviderResponse:
        """创建 Provider"""
        model = ProviderModel(
            name=body.name,
            provider_type=body.provider_type,
            base_url=body.base_url,
            api_key=body.api_key,
            extra_config=body.extra_config,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
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
        if body.extra_config is not None:
            model.extra_config = body.extra_config
        if body.status is not None:
            model.status = body.status
        db.commit()
        db.refresh(model)
        await self._cache.evict_pattern("provider:*")
        return ProviderResponse.from_orm(model)

    async def delete_provider(self, db: Session, provider_id: int) -> None:
        """删除 Provider（逻辑删除）"""
        model = ProviderModel.find_all(db).filter_by(id=provider_id).first()
        if not model:
            raise BizException(ErrorCode.PROVIDER_NOT_FOUND)
        model.soft_delete()
        db.commit()
        await self._cache.evict_pattern("provider:*")

    async def test_connection(self, db: Session, provider_id: int) -> ConnectionTestResult:
        """测试 Provider 连通性，通过 Adapter 策略分发"""
        model = ProviderModel.find_all(db).filter_by(id=provider_id).first()
        if not model:
            raise BizException(ErrorCode.PROVIDER_NOT_FOUND)

        adapter = provider_adapter_factory.get_adapter(model.provider_type)
        return await adapter.test_connection(model)


class ModelService(IModelService):
    """Model service - CRUD for models under a provider"""

    def __init__(self):
        self._cache = CacheHelper(redis_client)

    async def list_models(
        self, db: Session, provider_id: int, page: int = 1, page_size: int = 20
    ) -> any:
        """分页查询指定 Provider 下的模型列表"""
        query = ModelModel.find_all(db).filter_by(provider_id=provider_id)
        items, total = paginate(query, page, page_size)
        dtos = [ModelResponse.from_orm(item) for item in items]
        return to_page_result(dtos, total, page, page_size)

    async def create_model(self, db: Session, body: ModelCreate) -> ModelResponse:
        """创建模型"""
        provider = ProviderModel.find_all(db).filter_by(id=body.provider_id).first()
        if not provider:
            raise BizException(ErrorCode.PROVIDER_NOT_FOUND)
        model = ModelModel(
            provider_id=body.provider_id,
            name=body.name,
            model_id=body.model_id,
            capabilities=body.capabilities,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        await self._cache.evict_pattern("model:*")
        return ModelResponse.from_orm(model)

    async def get_model(self, db: Session, model_id: int) -> ModelResponse:
        """查询单个模型"""
        model = ModelModel.find_all(db).filter_by(id=model_id).first()
        if not model:
            raise BizException(ErrorCode.MODEL_NOT_FOUND)
        return ModelResponse.from_orm(model)

    async def update_model(
        self, db: Session, model_id: int, body: ModelUpdate
    ) -> ModelResponse:
        """更新模型，只改非空字段"""
        model = ModelModel.find_all(db).filter_by(id=model_id).first()
        if not model:
            raise BizException(ErrorCode.MODEL_NOT_FOUND)
        if body.name is not None:
            model.name = body.name
        if body.model_id is not None:
            model.model_id = body.model_id
        if body.status is not None:
            model.status = body.status
        if body.capabilities is not None:
            model.capabilities = body.capabilities
        db.commit()
        db.refresh(model)
        await self._cache.evict_pattern("model:*")
        return ModelResponse.from_orm(model)

    async def delete_model(self, db: Session, model_id: int) -> None:
        """删除模型（逻辑删除）"""
        model = ModelModel.find_all(db).filter_by(id=model_id).first()
        if not model:
            raise BizException(ErrorCode.MODEL_NOT_FOUND)
        model.soft_delete()
        db.commit()
        await self._cache.evict_pattern("model:*")
