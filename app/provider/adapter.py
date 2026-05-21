"""Provider adapter abstract base class - strategy pattern for provider connection testing & streaming chat"""
import time
import logging
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any

from app.infrastructure.llm.llm_client import llm_client
from app.infrastructure.llm.llm_api_exception import LlmApiException
from app.provider.models import ProviderModel
from app.provider.schemas import ConnectionTestResult

logger = logging.getLogger(__name__)


class ProviderAdapter(ABC):
    """供应商适配器基类：连通性测试 + 流式对话"""

    @abstractmethod
    async def test_connection(self, provider: ProviderModel) -> ConnectionTestResult:
        """测试供应商连通性"""
        pass

    @abstractmethod
    async def stream_chat(
        self,
        provider: ProviderModel,
        model: str,
        messages: list[dict],
        agent_config: dict,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式对话，yield 纯文本 delta"""
        pass

    @abstractmethod
    async def chat_complete(
        self,
        provider: ProviderModel,
        model: str,
        messages: list[dict],
        agent_config: dict,
        tools: list[dict] | None = None,
    ) -> dict:
        """非流式对话，返回完整响应（含 finish_reason、tool_calls 等）"""
        pass

    async def _do_test_get(
        self, provider: ProviderModel, url: str, headers: dict, timeout: float
    ) -> ConnectionTestResult:
        """通过 LlmClient GET 请求测试连通性"""
        start = time.monotonic()
        try:
            result = await llm_client.admin_get(url, headers, timeout, provider=provider.provider_type)
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
        self, provider: ProviderModel, url: str, headers: dict, body: dict, timeout: float
    ) -> ConnectionTestResult:
        """通过 LlmClient POST chat/completions 测试连通性"""
        start = time.monotonic()
        try:
            test_model = body.get("model", "unknown")
            result = await llm_client.admin_post(
                url, headers, body, timeout,
                provider=provider.provider_type, model=test_model,
            )
            latency_ms = int((time.monotonic() - start) * 1000)

            status_code = result["status_code"]
            if status_code == 200:
                return ConnectionTestResult(success=True, latency_ms=latency_ms)

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
