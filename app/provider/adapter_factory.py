"""Provider adapter factory - registry mapping provider_type to adapter instance"""
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.provider.adapter import ProviderAdapter
from app.provider.adapters.openai_adapter import OpenAiAdapter
from app.provider.adapters.anthropic_adapter import AnthropicAdapter
from app.provider.adapters.ollama_adapter import OllamaAdapter


class ProviderAdapterFactory:
    """供应商适配器工厂，通过 provider_type 获取对应 Adapter"""

    def __init__(self):
        self._registry: dict[str, ProviderAdapter] = {
            "openai": OpenAiAdapter(),
            "openai_compatible": OpenAiAdapter(),
            "anthropic": AnthropicAdapter(),
            "ollama": OllamaAdapter(),
        }

    def get_adapter(self, provider_type: str) -> ProviderAdapter:
        """根据 provider_type 获取适配器，不支持则抛出异常"""
        adapter = self._registry.get(provider_type)
        if not adapter:
            raise BizException(ErrorCode.PROVIDER_CONNECTION_FAILED)
        return adapter


# 模块级单例
provider_adapter_factory = ProviderAdapterFactory()
