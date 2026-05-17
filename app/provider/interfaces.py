"""Provider module interfaces - define service contracts for Layer 1"""
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.common.response import PageResult
from app.provider.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    ModelCreate, ModelUpdate, ModelResponse,
    ConnectionTestResult,
)


class IProviderService(ABC):
    """Provider service interface - exposed to Layer 2/3/4 modules"""

    @abstractmethod
    async def list_providers(self, db: Session, page: int = 1, page_size: int = 20) -> PageResult:
        """分页查询 Provider 列表"""
        pass

    @abstractmethod
    async def create_provider(self, db: Session, body: ProviderCreate) -> ProviderResponse:
        """创建 Provider"""
        pass

    @abstractmethod
    async def get_provider(self, db: Session, provider_id: int) -> ProviderResponse:
        """查询单个 Provider"""
        pass

    @abstractmethod
    async def update_provider(self, db: Session, provider_id: int, body: ProviderUpdate) -> ProviderResponse:
        """更新 Provider"""
        pass

    @abstractmethod
    async def delete_provider(self, db: Session, provider_id: int) -> None:
        """删除 Provider（逻辑删除）"""
        pass

    @abstractmethod
    async def test_connection(self, db: Session, provider_id: int) -> ConnectionTestResult:
        """测试 Provider 连通性"""
        pass


class IModelService(ABC):
    """Model service interface - exposed to Layer 2/3/4 modules"""

    @abstractmethod
    async def list_models(self, db: Session, provider_id: int, page: int = 1, page_size: int = 20) -> PageResult:
        """分页查询指定 Provider 下的模型列表"""
        pass

    @abstractmethod
    async def create_model(self, db: Session, body: ModelCreate) -> ModelResponse:
        """创建模型"""
        pass

    @abstractmethod
    async def get_model(self, db: Session, model_id: int) -> ModelResponse:
        """查询单个模型"""
        pass

    @abstractmethod
    async def update_model(self, db: Session, model_id: int, body: ModelUpdate) -> ModelResponse:
        """更新模型"""
        pass

    @abstractmethod
    async def delete_model(self, db: Session, model_id: int) -> None:
        """删除模型（逻辑删除）"""
        pass
