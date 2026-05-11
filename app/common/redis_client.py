"""Redis 配置模块"""
import json
from typing import Any

import redis.asyncio as redis

from app.common.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD


class RedisClient:
    """Redis 异步客户端封装，key 为字符串，value 为 JSON"""

    def __init__(self):
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """建立 Redis 连接"""
        self._client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )

    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()

    async def get(self, key: str) -> Any | None:
        """获取值，自动反序列化 JSON"""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        value = await self._client.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set(
        self, key: str, value: Any, expire: int | None = None
    ) -> None:
        """设置值，序列化 JSON，支持 expire 超时（秒）"""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        serialized = json.dumps(value)
        if expire:
            await self._client.setex(key, expire, serialized)
        else:
            await self._client.set(key, serialized)

    async def delete(self, key: str) -> None:
        """删除 key"""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """判断 key 是否存在"""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        result = await self._client.exists(key)
        return result > 0


# 全局单例
redis_client = RedisClient()