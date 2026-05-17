"""Provider Pydantic DTO"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator

PROVIDER_TYPES = ["openai", "anthropic", "openai_compatible", "ollama"]
PROVIDER_STATUSES = ["enabled", "disabled"]
MODEL_STATUSES = ["enabled", "disabled"]
HEALTH_STATUSES = ["healthy", "unhealthy", "unknown"]


# ── Provider DTOs ─────────────────────────────────────────


class ProviderCreate(BaseModel):
    """创建 Provider 的请求 DTO"""

    name: str = Field(..., min_length=1, max_length=64)
    provider_type: str = Field(...)
    base_url: str = Field(..., min_length=1)
    api_key: str = Field(default="")
    extra_config: Optional[dict] = Field(default=None)

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
    api_key: Optional[str] = Field(default=None)
    extra_config: Optional[dict] = Field(default=None)
    status: Optional[str] = Field(default=None)

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_valid_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("base_url must be a valid URL")
        return v

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PROVIDER_STATUSES:
            raise ValueError(f"status must be one of {PROVIDER_STATUSES}")
        return v


class ProviderResponse(BaseModel):
    """Provider 响应 DTO（不含 api_key，避免泄露给前端）"""

    id: int
    name: str
    provider_type: str
    base_url: str
    extra_config: Optional[dict] = None
    status: str
    health: Optional[dict] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, model, health: dict | None = None) -> "ProviderResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            name=model.name,
            provider_type=model.provider_type,
            base_url=model.base_url,
            extra_config=model.extra_config,
            status=model.status,
            health=health,
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )


# ── Model DTOs ────────────────────────────────────────────


class ModelCreate(BaseModel):
    """创建 Model 的请求 DTO"""

    provider_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=64)
    model_id: str = Field(..., min_length=1, max_length=128)
    capabilities: str = Field(default="", max_length=256)


class ModelUpdate(BaseModel):
    """更新 Model 的请求 DTO，所有字段 Optional"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    model_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    status: Optional[str] = Field(default=None)
    capabilities: Optional[str] = Field(default=None, max_length=256)

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MODEL_STATUSES:
            raise ValueError(f"status must be one of {MODEL_STATUSES}")
        return v


class ModelResponse(BaseModel):
    """Model 响应 DTO"""

    id: int
    provider_id: int
    name: str
    model_id: str
    status: str
    capabilities: str
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, model) -> "ModelResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            provider_id=model.provider_id,
            name=model.name,
            model_id=model.model_id,
            status=model.status,
            capabilities=model.capabilities,
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )


# ── ConnectionTestResult DTO ──────────────────────────────


class ConnectionTestResult(BaseModel):
    """连通性测试结果"""

    success: bool
    latency_ms: int = 0
    model_count: int = 0
    error_message: str = ""


# ── ProviderHealthLog DTOs ────────────────────────────────


class ProviderHealthLogResponse(BaseModel):
    """Provider 健康状态变更日志 响应 DTO"""

    id: int
    provider_id: int
    prev_status: str
    curr_status: str
    error_message: str
    response_time_ms: int
    created_at: str

    @classmethod
    def from_orm(cls, model) -> "ProviderHealthLogResponse":
        """ORM 模型转 DTO"""
        return cls(
            id=model.id,
            provider_id=model.provider_id,
            prev_status=model.prev_status,
            curr_status=model.curr_status,
            error_message=model.error_message,
            response_time_ms=model.response_time_ms,
            created_at=model.created_at.isoformat() if model.created_at else "",
        )
