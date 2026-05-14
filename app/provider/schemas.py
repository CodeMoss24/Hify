"""Provider Pydantic DTO"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator

PROVIDER_TYPES = ["openai", "anthropic", "gemini", "ollama"]


class ProviderCreate(BaseModel):
    """创建 Provider 的请求 DTO"""

    name: str = Field(..., min_length=1, max_length=64)
    provider_type: str = Field(...)
    base_url: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)

    @field_validator("provider_type")
    @classmethod
    def provider_type_must_be_valid(cls, v: str) -> str:
        if v not in PROVIDER_TYPES:
            raise ValueError(f"provider_type must be one of {PROVIDER_TYPES}")
        return v

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_valid_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must be a valid URL")
        return v


class ProviderUpdate(BaseModel):
    """更新 Provider 的请求 DTO，所有字段 Optional"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    base_url: Optional[str] = Field(default=None, min_length=1)
    api_key: Optional[str] = Field(default=None, min_length=1)

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_valid_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("base_url must be a valid URL")
        return v


class ProviderResponse(BaseModel):
    """Provider 响应 DTO（不含 api_key，避免泄露给前端）"""

    id: int
    name: str
    provider_type: str
    base_url: str
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, model) -> "ProviderResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            name=model.name,
            provider_type=model.provider_type,
            base_url=model.base_url,
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )