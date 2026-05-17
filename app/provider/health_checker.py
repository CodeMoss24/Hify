"""Provider 健康检查定时任务"""
import asyncio
import json
import logging
import time

from sqlalchemy.orm import Session

from app.common.database import SessionLocal
from app.common.executor import async_executor
from app.common.redis_client import redis_client
from app.provider.models import ProviderModel, ProviderHealthLogModel
from app.provider.service import ProviderService

logger = logging.getLogger(__name__)

HEALTH_KEY_PREFIX = "provider:health:"
HEALTH_TTL = 120
UNHEALTHY_THRESHOLD = 3
CHECK_INTERVAL = 60


class HealthChecker:
    """定时检查所有 enabled Provider 的连通性，结果写入 Redis"""

    def __init__(self):
        self._provider_service = ProviderService()
        self._running = False

    async def check_all_providers(self, db: Session) -> None:
        """遍历所有 enabled Provider，逐个检查连通性"""
        providers = ProviderModel.find_all(db).filter_by(status="enabled").all()
        if not providers:
            return

        logger.info(f"[HealthChecker] start checking {len(providers)} providers")
        success_count = 0
        fail_count = 0

        for provider in providers:
            try:
                result = await self._provider_service.test_connection(db, provider.id)
                await self._update_health(db, provider.id, result)
                if result.success:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"[HealthChecker] provider {provider.id} check error: {e}")

        logger.info(
            f"[HealthChecker] done: {success_count} healthy, {fail_count} failed"
        )

    async def _update_health(self, db: Session, provider_id: int, result) -> None:
        """更新 Redis 健康状态，状态切换时写 tb_provider_health_log"""
        key = f"{HEALTH_KEY_PREFIX}{provider_id}"

        # 读取上一次状态
        prev_raw = await redis_client.get(key)
        prev_health = None
        prev_failures = 0
        if prev_raw:
            prev_health = prev_raw.get("status")
            prev_failures = prev_raw.get("consecutive_failures", 0)

        # 计算新状态
        if result.success:
            consecutive_failures = 0
            curr_health = "healthy"
        else:
            consecutive_failures = prev_failures + 1
            curr_health = "unhealthy" if consecutive_failures >= UNHEALTHY_THRESHOLD else "healthy"

        # 写 Redis
        health_data = {
            "status": curr_health,
            "last_check_at": int(time.time()),
            "response_time_ms": result.latency_ms,
            "consecutive_failures": consecutive_failures,
            "last_error": result.error_message,
        }
        await redis_client.set(key, health_data, expire=HEALTH_TTL)

        # 状态切换时写日志表
        if prev_health is not None and prev_health != curr_health:
            log = ProviderHealthLogModel(
                provider_id=provider_id,
                prev_status=prev_health,
                curr_status=curr_health,
                error_message=result.error_message,
                response_time_ms=result.latency_ms,
            )
            db.add(log)
            db.commit()
            logger.info(
                f"[HealthChecker] provider {provider_id} status changed: "
                f"{prev_health} -> {curr_health}"
            )

    async def run_loop(self) -> None:
        """后台循环，每 CHECK_INTERVAL 秒执行一次"""
        self._running = True
        logger.info("[HealthChecker] background loop started")
        while self._running:
            try:
                db = SessionLocal()
                try:
                    await self.check_all_providers(db)
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"[HealthChecker] loop error: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

    def stop(self) -> None:
        """停止循环"""
        self._running = False
        logger.info("[HealthChecker] background loop stopping")


# 模块级单例
health_checker = HealthChecker()
