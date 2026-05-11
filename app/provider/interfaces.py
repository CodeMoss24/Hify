"""Provider module interfaces - define service contracts for Layer 1"""
from abc import ABC, abstractmethod
from typing import Optional


class IProviderService(ABC):
    """Provider service interface - exposed to Layer 2/3/4 modules"""

    @abstractmethod
    async def create_provider(self, data: "ProviderCreate") -> "ProviderResponse":
        pass

    @abstractmethod
    async def get_provider(self, provider_id: int) -> Optional["ProviderResponse"]:
        pass

    @abstractmethod
    async def list_providers(self, page: int, page_size: int) -> "PageResult[ProviderResponse]":
        pass

    @abstractmethod
    async def update_provider(self, provider_id: int, data: "ProviderUpdate") -> Optional["ProviderResponse"]:
        pass

    @abstractmethod
    async def delete_provider(self, provider_id: int) -> bool:
        pass

    @abstractmethod
    async def test_connection(self, provider_id: int) -> "TestConnectionResponse":
        pass


class IModelService(ABC):
    """Model service interface"""

    @abstractmethod
    async def create_model(self, provider_id: int, data: "ModelCreate") -> "ModelResponse":
        pass

    @abstractmethod
    async def get_model(self, model_id: int) -> Optional["ModelResponse"]:
        pass

    @abstractmethod
    async def list_models(self, provider_id: Optional[int], page: int, page_size: int) -> "PageResult[ModelResponse]":
        pass

    @abstractmethod
    async def update_model(self, model_id: int, data: "ModelUpdate") -> Optional["ModelResponse"]:
        pass

    @abstractmethod
    async def delete_model(self, model_id: int) -> bool:
        pass