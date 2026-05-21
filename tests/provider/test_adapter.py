"""测试 ProviderAdapter — 错误消息提取"""
from app.provider.adapter import ProviderAdapter


class TestExtractErrorMessage:
    """测试 _extract_error_message() — 多 Provider 错误格式解析"""

    def test_should_extract_openai_format(self):
        body = {"error": {"message": "Incorrect API key"}}
        result = ProviderAdapter._extract_error_message(body, 401)
        assert "Incorrect API key" in result
        assert "401" in result

    def test_should_extract_anthropic_format(self):
        body = {
            "type": "error",
            "error": {"type": "authentication_error", "message": "invalid x-api-key"},
        }
        result = ProviderAdapter._extract_error_message(body, 401)
        assert "invalid x-api-key" in result
        assert "401" in result

    def test_should_fallback_to_status_code_when_no_error_field(self):
        body = {"unexpected": "format"}
        result = ProviderAdapter._extract_error_message(body, 500)
        assert result == "HTTP 500"