"""Provider & Model service implementation"""
import time
import logging

from sqlalchemy.orm import Session

from app.common.cache_helper import CacheHelper
from app.common.database import paginate, to_page_result
from app.common.exceptions import BizException
from app.common.error_code import ErrorCode
from app.common.redis_client import redis_client
from app.infrastructure.llm.llm_client import llm_client
from app.infrastructure.llm.llm_api_exception import LlmApiException
from app.provider.interfaces import IProviderService, IModelService
from app.provider.models import ProviderModel, ModelModel
from app.provider.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    ModelCreate, ModelUpdate, ModelResponse,
    ConnectionTestResult,
)

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

    # 默认测试模型：连通性测试用最小 chat 请求代替 GET /models
    _TEST_MODELS = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-20241022",
        "ollama": "llama3",
    }

    async def test_connection(self, db: Session, provider_id: int) -> ConnectionTestResult:
        """测试 Provider 连通性

        openai/anthropic/openai_compatible: 发 POST /chat/completions 最小请求
        ollama: 发 GET /api/tags（Ollama 原生接口，支持列表）
        """
        model = ProviderModel.find_all(db).filter_by(id=provider_id).first()
        if not model:
            raise BizException(ErrorCode.PROVIDER_NOT_FOUND)

        provider_type = model.provider_type
        base_url = model.base_url.rstrip("/")
        extra_config = model.extra_config or {}
        timeout = 10.0

        if provider_type == "ollama":
            url = f"{base_url}/api/tags"
            headers = {}
            return await self._do_test_get(url, headers, timeout, "ollama")

        # OpenAI / Anthropic / OpenAI 兼容：走 chat completions
        if provider_type == "anthropic":
            url = f"{base_url}/messages"
            headers = {
                "x-api-key": model.api_key,
                "anthropic-version": extra_config.get("anthropic_version", "2023-06-01"),
                "content-type": "application/json",
            }
            test_model = extra_config.get("test_model", self._TEST_MODELS["anthropic"])
            body = {
                "model": test_model,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            }
            return await self._do_test_post(url, headers, body, timeout)

        # openai / openai_compatible
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {model.api_key}",
            "content-type": "application/json",
        }
        test_model = extra_config.get("test_model", self._TEST_MODELS.get(provider_type, "gpt-4o-mini"))
        body = {
            "model": test_model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        }
        return await self._do_test_post(url, headers, body, timeout)

    async def _do_test_get(
        self, url: str, headers: dict, timeout: float, provider_type: str
    ) -> ConnectionTestResult:
        """通过 LlmClient GET 请求测试连通性（仅 Ollama）"""
        start = time.monotonic()
        try:
            result = await llm_client.admin_get(url, headers, timeout)
            latency_ms = int((time.monotonic() - start) * 1000)

            status_code = result["status_code"]
            if status_code != 200:
                return ConnectionTestResult(
                    success=False,
                    latency_ms=latency_ms,
                    error_message=f"HTTP {status_code}",
                )

            model_count = len(result["body"].get("models", []))
            return ConnectionTestResult(
                success=True,
                latency_ms=latency_ms,
                model_count=model_count,
            )

        except LlmApiException as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning(f"Provider connection test failed: {url} -> {e.message}")
            return ConnectionTestResult(
                success=False,
                latency_ms=latency_ms,
                error_message=e.message,
            )
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning(f"Provider connection test failed: {url} -> {e}")
            return ConnectionTestResult(
                success=False,
                latency_ms=latency_ms,
                error_message=str(e),
            )

    async def _do_test_post(
        self, url: str, headers: dict, body: dict, timeout: float
    ) -> ConnectionTestResult:
        """通过 LlmClient POST chat/completions 测试连通性"""
        start = time.monotonic()
        try:
            result = await llm_client.admin_post(url, headers, body, timeout)
            latency_ms = int((time.monotonic() - start) * 1000)

            status_code = result["status_code"]
            if status_code == 200:
                return ConnectionTestResult(success=True, latency_ms=latency_ms)

            # 非 200：解析错误信息
            resp_body = result.get("body", {})
            error_msg = self._extract_error_message(resp_body, status_code)
            return ConnectionTestResult(
                success=False,
                latency_ms=latency_ms,
                error_message=error_msg,
            )

        except LlmApiException as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning(f"Provider connection test failed: {url} -> {e.message}")
            return ConnectionTestResult(
                success=False,
                latency_ms=latency_ms,
                error_message=e.message,
            )
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning(f"Provider connection test failed: {url} -> {e}")
            return ConnectionTestResult(
                success=False,
                latency_ms=latency_ms,
                error_message=str(e),
            )

    @staticmethod
    def _extract_error_message(body: dict, status_code: int) -> str:
        """从不同 Provider 的错误响应中提取可读的错误信息"""
        # OpenAI 格式: {"error": {"message": "..."}}
        if "error" in body:
            err = body["error"]
            if isinstance(err, dict):
                return f"HTTP {status_code}: {err.get('message', str(err))}"
            return f"HTTP {status_code}: {err}"
        # Anthropic 格式: {"type": "error", "error": {"type": "...", "message": "..."}}
        if body.get("type") == "error":
            err = body.get("error", {})
            return f"HTTP {status_code}: {err.get('message', str(err))}"
        return f"HTTP {status_code}"


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
