"""对话上下文管理器 - 滑动窗口策略 + Redis/MySQL 双写"""
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.common.redis_client import redis_client
from app.chat.models import MessageModel

logger = logging.getLogger(__name__)

TTL_SECONDS = 2 * 60 * 60  # 2 小时


class ContextManager:
    """对话上下文管理器"""

    def _get_key(self, conversation_id: int) -> str:
        """获取 Redis 缓存 key"""
        return f"session:{conversation_id}"

    async def get_history(
        self, db: Session, conversation_id: int, max_turns: int
    ) -> list[dict]:
        """获取最近 max_turns 轮消息

        先从 Redis 取，缓存未命中则从 MySQL 加载并回写 Redis
        """
        key = self._get_key(conversation_id)
        client = redis_client._client  # type: ignore
        if not client:
            raise RuntimeError("Redis client not connected")

        # 尝试从 Redis 获取
        cached = await client.lrange(key, 0, -1)
        if cached:
            # 解析 JSON，只返回最近 max_turns 轮
            history = [json.loads(msg) for msg in cached]
            return history[-max_turns * 2 :]  # 按需求返回，但 Redis 保留更多

        # 缓存未命中，从 MySQL 加载最近 max_turns * 2 条消息
        messages = (
            MessageModel.find_all(db)
            .filter_by(conversation_id=conversation_id)
            .order_by(MessageModel.created_at.asc())
            .limit(max_turns * 2)
            .all()
        )

        # 转换为 dict 列表
        history = []
        for msg in messages:
            history.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                }
            )

        # 回写 Redis
        if history:
            pipe = client.pipeline()
            for msg in history:
                pipe.rpush(key, json.dumps(msg, ensure_ascii=False))
            pipe.expire(key, TTL_SECONDS)
            await pipe.execute()

        # 返回最近 max_turns 轮
        return history[-max_turns:]

    async def add_message(
        self, conversation_id: int, role: str, content: str, max_turns: int
    ) -> None:
        """添加新消息到 Redis

        RPUSH 后 LTRIM 保留最近 max_turns * 2 条，刷新 TTL
        """
        key = self._get_key(conversation_id)
        client = redis_client._client  # type: ignore
        if not client:
            raise RuntimeError("Redis client not connected")

        msg_dict = {"role": role, "content": content}
        msg_json = json.dumps(msg_dict, ensure_ascii=False)

        pipe = client.pipeline()
        pipe.rpush(key, msg_json)
        pipe.ltrim(key, -(max_turns * 2), -1)  # 保留最近 max_turns*2 条
        pipe.expire(key, TTL_SECONDS)
        await pipe.execute()
