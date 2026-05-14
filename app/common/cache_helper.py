"""Cache-Aside 模式封装：get_or_set / evict / evict_pattern"""
import json
from typing import Any, Awaitable, Callable

from app.common.redis_client import RedisClient


class CacheHelper:
    """Cache-Aside 模式工具类"""

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client

    async def get_or_set(
        self,
        key: str,
        ttl: int,
        factory: Callable[[], Awaitable[Any]],
    ) -> Any | None:
        """Cache-Aside：先查缓存，未命中调用 factory，结果写入 Redis（TTL 秒）

        Args:
            key: Redis key
            ttl: 过期时间（秒）
            factory: 回源函数（查数据库等），返回 None 时不缓存
        """
        # Step 1: 查缓存
        cached = await self._redis.get(key)
        if cached is not None:
            return cached

        # Step 2: 回源
        value = await factory()
        if value is None:
            return None

        # Step 3: 写缓存
        await self._redis.set(key, value, expire=ttl)
        return value

    async def evict(self, key: str) -> None:
        """删除单个缓存 key"""
        await self._redis.delete(key)

    async def evict_pattern(self, pattern: str) -> None:
        """按模糊匹配批量删除缓存 keys（支持 * 通配符）

        Args:
            pattern: 如 "provider:*" 清掉所有 provider 相关 key
        """
        if not self._redis._client:
            raise RuntimeError("Redis client not connected")

        cursor = 0
        while True:
            cursor, keys = await self._redis._client.scan(
                cursor=cursor, match=pattern, count=100
            )
            if keys:
                await self._redis._client.delete(*keys)
            if cursor == 0:
                break