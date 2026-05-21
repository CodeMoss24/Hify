"""健康检查服务：检查 MySQL / Redis / Qdrant / 熔断器状态"""
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from app.common.config import QDRANT_HOST, QDRANT_PORT
from app.common.database import SessionLocal
from app.common.redis_client import redis_client
from app.infrastructure.llm.llm_client import llm_client


@dataclass
class ComponentStatus:
    status: str  # "UP" | "DOWN" | "skipped"
    latency_ms: float | None = None
    message: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"status": self.status}
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 1)
        if self.message is not None:
            result["message"] = self.message
        if self.error is not None:
            result["error"] = self.error
        return result


async def check_mysql() -> ComponentStatus:
    session = SessionLocal()
    try:
        start = time.monotonic()
        session.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(status="UP", latency_ms=latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(status="DOWN", latency_ms=latency, error=str(e))
    finally:
        session.close()


async def check_redis() -> ComponentStatus:
    if redis_client._client is None:
        return ComponentStatus(status="skipped", message="Redis not configured")
    try:
        start = time.monotonic()
        await redis_client._client.ping()
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(status="UP", latency_ms=latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(status="DOWN", latency_ms=latency, error=str(e))


async def check_qdrant() -> ComponentStatus:
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        return ComponentStatus(status="skipped", message="Qdrant not configured")

    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        start = time.monotonic()
        client.get_collections()
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(status="UP", latency_ms=latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(status="DOWN", latency_ms=latency, error=str(e))


def get_circuit_breakers_status() -> dict[str, str]:
    breakers: dict[str, str] = {}
    for url, cb in llm_client._circuit_breakers.items():
        breakers[url] = cb.state.value
    return breakers


async def get_health_status() -> tuple[dict[str, Any], int]:
    mysql = await check_mysql()
    redis = await check_redis()
    qdrant = await check_qdrant()
    breakers = get_circuit_breakers_status()

    # 聚合整体状态
    if mysql.status == "DOWN":
        overall = "DOWN"
        http_status = 503
    elif redis.status == "DOWN":
        overall = "DEGRADED"
        http_status = 200
    elif qdrant.status == "DOWN":
        overall = "DEGRADED"
        http_status = 200
    elif breakers and all(s == "open" for s in breakers.values()):
        overall = "DEGRADED"
        http_status = 200
    else:
        overall = "UP"
        http_status = 200

    return {
        "status": overall,
        "components": {
            "mysql": mysql.to_dict(),
            "redis": redis.to_dict(),
            "qdrant": qdrant.to_dict(),
            "circuit_breakers": breakers,
        },
    }, http_status
