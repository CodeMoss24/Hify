"""测试 LlmClient — LLM HTTP 客户端底层方法"""
import pytest
from app.infrastructure.llm.llm_client import LlmClient
from app.infrastructure.llm.llm_api_exception import LlmApiException
from app.common.error_code import ErrorCode


class TestRaiseByStatus:
    """测试 _raise_by_status() — HTTP 状态码映射到业务异常"""

    def test_should_raise_auth_failed_when_401(self):
        client = LlmClient()
        with pytest.raises(LlmApiException) as exc:
            client._raise_by_status(401, "", None)
        assert exc.value.error_code == ErrorCode.LLM_AUTH_FAILED

    def test_should_raise_rate_limited_when_429(self):
        client = LlmClient()
        with pytest.raises(LlmApiException) as exc:
            client._raise_by_status(429, "", None)
        assert exc.value.error_code == ErrorCode.LLM_RATE_LIMITED

    def test_should_raise_server_error_when_500(self):
        client = LlmClient()
        with pytest.raises(LlmApiException) as exc:
            client._raise_by_status(500, "", None)
        assert exc.value.error_code == ErrorCode.LLM_SERVER_ERROR

    def test_should_raise_auth_failed_when_403(self):
        client = LlmClient()
        with pytest.raises(LlmApiException) as exc:
            client._raise_by_status(403, "", None)
        assert exc.value.error_code == ErrorCode.LLM_AUTH_FAILED


class TestExtractBaseUrl:
    """测试 _extract_base_url() — URL 解析出熔断器 key"""

    def test_should_extract_scheme_and_host(self):
        client = LlmClient()
        result = client._extract_base_url("https://api.openai.com/v1/chat/completions")
        assert result == "https://api.openai.com"

    def test_should_preserve_port(self):
        client = LlmClient()
        result = client._extract_base_url("http://localhost:11434/v1/chat")
        assert result == "http://localhost:11434"