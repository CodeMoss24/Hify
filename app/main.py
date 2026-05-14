"""FastAPI 入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.common.config import setup_json_encoders
from app.common.database import Base, _engine
from app.common.handlers import register_exception_handlers
from app.common.logging_config import setup_logging
from app.common.redis_client import redis_client
from app.common.response import ApiResponse

# 导入所有业务模块的 models，确保 SQLAlchemy 能发现全部表
from app.provider import models as provider_models
from app.agent import models as agent_models
from app.chat import models as chat_models
from app.mcp import models as mcp_models
from app.workflow import models as workflow_models
from app.knowledge import models as knowledge_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理：启动时连接 Redis 并建表，关闭时断开"""
    await redis_client.connect()
    # 自动创建所有表（仅当表不存在时）
    Base.metadata.create_all(bind=_engine)
    yield
    await redis_client.close()


app = FastAPI(lifespan=lifespan)

# 配置结构化日志 + 注册请求追踪中间件
setup_logging(app)

# 注册时间序列化
setup_json_encoders(app)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册路由
from app.provider.router import router as provider_router

# 注册 provider 路由
app.include_router(provider_router, prefix="/api/v1", tags=["provider"])


@app.get("/v1/health")
async def health_check():
    """健康检查接口"""
    return ApiResponse.ok(data="Hify is running")
