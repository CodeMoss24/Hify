"""FastAPI 入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.common.handlers import register_exception_handlers
from app.common.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理：启动时连接 Redis，关闭时断开"""
    await redis_client.connect()
    yield
    await redis_client.close()


app = FastAPI(lifespan=lifespan)

# 注册全局异常处理器
register_exception_handlers(app)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok"}