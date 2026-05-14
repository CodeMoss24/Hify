"""统一配置模块，所有配置项从 .env 读取"""
from datetime import datetime, date
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
import json

load_dotenv()

import os

# MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "hify")
DB_USERNAME = os.getenv("DB_USERNAME", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

# Redis（同步 redis_client.py 中的配置）
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# 服务端口
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

# LLM 超时
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
LLM_CONNECT_TIMEOUT = int(os.getenv("LLM_CONNECT_TIMEOUT", "10"))

# LLM 并发控制
LLM_CHAT_CONCURRENCY = int(os.getenv("LLM_CHAT_CONCURRENCY", "10"))
BACKGROUND_CONCURRENCY = int(os.getenv("BACKGROUND_CONCURRENCY", "5"))


def setup_json_encoders(app: FastAPI) -> None:
    """注册时间类型序列化：所有 datetime/date 序列化为 ISO 8601 字符串"""

    def json_encoder_default(val: Any) -> Any:
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, date):
            return val.isoformat()
        raise TypeError(f"Object of type {type(val)} is not JSON serializable")

    # 替换 FastAPI 的默认 JSON 编码器
    app.json_encoder = json_encoder_default