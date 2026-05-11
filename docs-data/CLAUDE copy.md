# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

### 产品定位

Hify 是一个可本地部署的 AI Agent 开发平台，面向团队内部 20-50 人使用。一个人开发，以 Docker Compose 一键部署为核心交付形式。

### 做什么
- 多模型提供商管理（平台基础能力）
- Agent 创建与配置（选模型、绑工具、设系统提示词）
- 对话引擎（流式响应、多轮对话、上下文管理）
- 知识库 + RAG（一期只支持 TXT 文档，固定长度分块）
- 简版工作流（JSON 配置，线性 + 条件分支，不做可视化拖拽）
- MCP 工具接入（Agent 可通过 MCP 协议调用外部工具）
- 管理控制台（模型管理、Agent 配置、对话界面）

### 不做什么
- 不做可视化工作流拖拽编排
- 不做多租户 / 权限体系
- 不做插件市场、计费系统
- 不做文本生成应用、WebApp 发布、嵌入组件
- 不做标注与微调

### 技术栈

| 层级 | 技术选型 |
|------|---------|
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | MySQL 8.x + Redis 7.x |
| 向量数据库 | Qdrant（Docker 部署） |
| 前端 | Vue 3 + TypeScript + Element Plus |
| 容器化 | Docker + Docker Compose |

---

## 应用架构

### 模块划分

```
app/
├── main.py                 # FastAPI 入口
├── common/                 # 公共模块（config/exceptions/utils）
├── provider/               # 模型提供商
├── agent/                   # Agent 管理
├── chat/                    # 对话引擎
├── mcp/                     # MCP 工具
├── workflow/                # 工作流
└── knowledge/              # 知识库 RAG
```

### 模块依赖层级（单向依赖，不能循环）

```
Layer 0: common（所有模块依赖）
Layer 1: provider, mcp, knowledge（基础能力）
Layer 2: agent（依赖 provider, mcp, knowledge）
Layer 3: workflow（依赖 provider, mcp, knowledge）
Layer 4: chat（依赖所有模块）
```

| 调用方 | 被调用方 | 允许？ |
|--------|----------|--------|
| chat.service | agent.service | ✅ |
| agent.service | chat.service | ❌ |
| agent.service | provider.service | ✅ |
| agent.service | mcp.service | ✅ |
| agent.service | knowledge.service | ✅ |
| workflow.service | mcp.service | ✅ |
| workflow.service | knowledge.service | ✅ |

---

## 代码组织规范

每个模块内部结构：

```
app/{module}/
├── __init__.py           # 导出 router、service、schemas、interfaces
├── router.py             # API 路由
├── service.py            # 业务逻辑实现
├── interfaces.py         # 服务接口（抽象类）
├── schemas.py            # Pydantic 模型（请求/响应 DTO）
└── models.py             # SQLAlchemy ORM 模型
```

### 各层职责

| 文件 | 职责 | 禁止 |
|------|------|------|
| **router.py** | HTTP 路由、参数校验、调用 service | 写业务逻辑、SQL |
| **service.py** | 业务逻辑、事务管理、实现接口 | 处理 HTTP、导入 router |
| **interfaces.py** | 定义服务接口，跨模块调用必须通过接口 | — |
| **schemas.py** | Pydantic 请求/响应 DTO，控制字段暴露 | 直接暴露 Entity |
| **models.py** | SQLAlchemy ORM 模型，对应数据库表 | 写业务逻辑 |

### 跨模块调用规则

**必须通过 interfaces.py，不能直接 import 实现类。**

```python
# ✅ 正确：通过接口调用
from app.agent.interfaces import IAgentService

class ChatService:
    def __init__(self, agent_service: IAgentService):
        self._agent = agent_service

# ❌ 错误：直接 import 实现类
from app.agent.service import AgentService
```

**为什么：** 后续拆微服务时，只需改依赖注入配置，调用方代码不用动。

### 命名规则

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 请求模型 | `{Entity}Create` / `{Entity}Update` | `AgentCreate` |
| 响应模型 | `{Entity}Response` | `AgentResponse` |
| ORM 模型 | `{Entity}Model` | `AgentModel` |
| 服务接口 | `I{Entity}Service` | `IAgentService` |
| 服务实现 | `{Entity}Service` | `AgentService` |
| 数据库表 | `tb_{module}_{entity}` | `tb_agent` |

### 异常处理

- 业务异常定义在 `app/common/exceptions.py`
- service 层抛出，router 层捕获
- Entity 有敏感字段（API Key），不能直接返回给前端，必须通过 schemas.py 转换

---

## 接口规范

### 路径

`/api/v1/{resources}` RESTful 风格

```
GET    /api/v1/providers              # 列表
POST   /api/v1/providers              # 创建
GET    /api/v1/providers/{id}         # 详情
PUT    /api/v1/providers/{id}         # 更新
DELETE /api/v1/providers/{id}         # 删除
POST   /api/v1/providers/{id}/test-connection  # 非CRUD用动词
```

### 统一响应

```python
# app/common/response.py
class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None
```

### 分页

| 参数 | 说明 |
|------|------|
| page | 页码，从 1 开始 |
| page_size | 每页数量，默认 20，最大 100 |

```python
class PageResult(BaseModel, Generic[T]):
    list: list[T]
    total: int
    page: int
    page_size: int
```

### 空值

- 列表空时返回 `[]`
- 字符串空时返回 `""`
- 对象不存在时返回 `null`

### 错误码

| 区间 | 模块 |
|------|------|
| 1000-1999 | 通用 |
| 2000-2999 | Provider |
| 3000-3999 | Agent |
| 4000-4999 | Chat |
| 5000-5999 | MCP |
| 6000-6999 | Workflow |
| 7000-7999 | Knowledge |

---

## LLM 调用技术方案

### 技术选型

- **流式响应**：FastAPI 原生 `StreamingResponse` + SSE，不需要 WebSocket 或 Socket.IO
- **并发控制**：异步优先 + Semaphore（不是线程池）
- **容错**：断路器模式（per-provider 独立）
- **重试**：指数退避 + 抖动

### LLM 请求分类与优先级

| 请求类型 | 方法 | 超时 | 并发控制 |
|----------|------|------|----------|
| SSE 流式对话 | `chat_complete()` / `stream()` | 120s | 受 chat_semaphore 限制 |
| 管理/连通性测试 | `admin_call()` | 10s | 不受限制 |

对话请求和管理请求走不同路径，防止 SSE 长连接阻塞管理页面响应。

### 断路器配置（per-provider 独立）

- 连续失败 5 次 → 断路打开
- 30 秒后放行一个探测请求
- 探测成功 → 恢复；探测失败 → 继续熔断

### 重试策略

| 异常类型 | 是否重试 |
|----------|----------|
| 网络超时（Timeout） | ✅ 重试 |
| 限流（429） | ✅ 退避重试 |
| 服务器过载（503/504） | ✅ 重试 |
| **认证失败（401）** | ❌ 不重试 |
| **权限问题（403）** | ❌ 不重试 |
| **参数错误（400）** | ❌ 不重试 |

退避曲线：1s → 2s → 4s（最多 3 次，30s 上限）

### 流式调用不重试

已经 yield 的数据无法撤回，一旦开始 stream 就不重试。

### 并发控制参数

| 维度 | 值 |
|------|---|
| 对话全局并发 | 10 |
| 每 Provider 并发 | 5 |

### 实现代码

```python
# app/infrastructure/llm/llm_gateway.py
import asyncio

# 并发控制
CHAT_SEMAPHORE = asyncio.Semaphore(10)  # 全局 SSE 并发上限
PROVIDER_SEMAPHORES = {provider: asyncio.Semaphore(5) for provider in providers}

# 超时配置
TIMEOUT_SSE = 120.0      # SSE 流式对话
TIMEOUT_ADMIN = 10.0      # 管理/测试请求

# 断路器
CircuitBreaker(failure_threshold=5, open_timeout=30.0)

# 重试退避
RETRY_MAX = 3
BACKOFF_BASE = 1.0
BACKOFF_MAX = 30.0
```

### Provider 配置

| Provider | Base URL | 超时 |
|----------|----------|------|
| OpenAI | `https://api.openai.com/v1` | 120s |
| Anthropic | `https://api.anthropic.com/v1` | 120s |
| Gemini | `https://generativelanguage.googleapis.com/v1beta` | 120s |
| Ollama | `http://localhost:11434/v1` | 300s |

---

## 部署架构

### 组件

| 组件 | 职责 | 关键配置 |
|------|------|----------|
| Nginx | 反向代理、静态资源、SSE 透传 | `proxy_buffering off`, `gzip on` |
| FastAPI | API 路由、SSE 流式、LLM 调用 | 单副本，一期 |
| MySQL | 业务数据持久化 | 挂载 volume |
| Redis | 会话缓存 | `maxmemory 64mb` |
| Qdrant | 向量数据库 | 挂载 volume |

### 缓存策略

| 内容 | 策略 | TTL |
|------|------|-----|
| Provider/Agent 配置 | Redis Cache-Aside | 30min |
| 对话上下文 | Redis | 2h |
| 对话消息、知识库文档 | 不缓存，走数据库 | — |
| LLM 响应 | 不缓存 | — |

### 本地开发

| 组件 | 启动命令 |
|------|----------|
| 后端 | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| 前端 | `npm run dev` |
| 基础设施 | `docker-compose -f docker-compose.dev.yml up -d` |

一键启动：`start.sh`

---

## 数据库规范

### 表命名

`tb_{module}_{entity}`

### 核心表（18 张）

```
tb_model_provider, tb_model,
tb_agent, tb_agent_knowledge_base, tb_agent_tool,
tb_mcp_server, tb_mcp_tool,
tb_knowledge_base, tb_document, tb_document_chunk,
tb_conversation, tb_message, tb_message_reference,
tb_workflow, tb_workflow_node, tb_workflow_edge,
tb_user, tb_api_key
```

### 通用字段

```sql
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
deleted TINYINT(1) NOT NULL DEFAULT 0
```

### 硬规矩

| 规矩 | 说明 |
|------|------|
| 主键 BIGINT 自增 | 禁止 UUID |
| 禁止 NULL | 空值用空字符串或 0 |
| 金额/Token 用 BIGINT | 不用 DECIMAL |
| 枚举用 VARCHAR(32) | 不用 ENUM |

### 索引规则

- 命名 `idx_{表名}_{字段名}`
- deleted 必须加入组合索引
- 组合索引等值列在前，范围列在后
- 多对多关联表两个方向都要索引
- 唯一约束用 UNIQUE INDEX
- 禁止 TEXT/BLOB 建索引
- 不建数据库外键，应用层维护

### 分页规则

- 默认游标分页：`WHERE id < #{lastId}`
- OFFSET 最大 10000
- COUNT 只在第一页查，翻页不重复

### 索引监控

**开发阶段**：SQLAlchemy `echo=True`，拦截 >10ms 查询打印 EXPLAIN，type=ALL 时告警。

**CI 阶段**：单元测试验证关键查询走索引，EXPLAIN type=ALL 则测试失败。

**生产阶段**：定期查询 `performance_schema.events_statements_summary_by_digest`，找出 `sum_no_index_used > 0` 的 SQL。

```sql
SELECT digest_text, count_star, sum_no_index_used
FROM performance_schema.events_statements_summary_by_digest
WHERE sum_no_index_used > 0
ORDER BY sum_no_index_used DESC LIMIT 20;
```

### 大表预判

- message：增长最快，建 `(conversation_id, created_at)` 索引
- document_chunk：MySQL 只存元数据，向量存 Qdrant

---

## 系统瓶颈

### 瓶颈优先级

| 优先级 | 瓶颈 | 触发条件 | 一期处理 |
|--------|------|----------|----------|
| 1 | LLM API 延迟 | 任何请求 | ✅ 超时+断路器+并发控制 |
| 2 | SSE event loop 阻塞 | 20+ 并发 | ✅ 优先级隔离 |
| 3 | MySQL 连接池 | 30+ 并发 | ⚠️ 监控调参 |
| 4 | Redis 内存 | 50 用户多轮 | ⚠️ 设置 maxmemory |

### 一期只做两件事

1. LLM 调用控制：超时（120s）+ 断路器 + Semaphore 并发
2. Nginx gzip：一行配置

其他已知但暂不处理，等触发条件到了再动。

---

## 扩展路径

| 阶段 | 用户规模 | 触发条件 | 核心改动 |
|------|----------|----------|----------|
| Phase 1 | 50→500 | 响应变慢 | 多副本 + 读写分离 |
| Phase 2 | 500→2000 | LLM 队列堆积 | MQ 异步化 + 分库 |
| Phase 3 | 2000→几千 | 模块发布干扰 | 微服务拆分 |

触发条件驱动，条件不到不动。技术栈全程不变。

---

## 行为指令

### 写代码时
- 每个功能用最简单直接的方式实现
- 不引入不必要的设计模式，除非明确要求
- 不做过度抽象
- 不引入技术栈以外的依赖，需要时先问我
- 所有外部调用必须有超时设置
- 配置项外化到 `.env` 文件，通过 `app/common/config.py` 读取，不硬编码

### 改代码时
- 先理解相关模块的设计意图
- 不要为了新功能破坏已有接口契约
- 改完确保已有测试通过

### 不确定时
- 架构选择给 2-3 个方案对比，我来拍板
- 规范没覆盖的情况，先问，不要自己编规矩

---

## 关键决策记录

### 1. 模块化单体架构

选模块化单体而不是微服务：一人开发，一期 50 人，架构简单交付快。模块化设计预留扩容口子，后续可拆。

### 2. 功能模块化而不是 DDD

一人开发，DDD 前期设计成本高。轻量功能模块化足够，service 直接 import 实现类（但跨模块必须通过 interfaces）。

### 3. SSE 而不是 WebSocket

AI 对话本质是单向推送（用户发一次请求，服务器持续推 token），SSE 足够。WebSocket 握手开销大，需要双向通信，不是必要特性。

### 4. 异步优先的并发控制

LLM 调用是 IO 密集型，用 async/await 释放事件循环比线程池更高效。FastAPI 原生支持异步，不需要额外线程管理。

---

## 详细文档索引

- `CODE_ORGANIZATION.md` — 代码组织规范完整版
- `LLM_TECHNICAL_DESIGN.md` — LLM 调用技术方案完整版
- `DATABASE_PERFORMANCE.md` — 数据库性能规范完整版
- `SCALING_PATH.md` — 扩展路径规划完整版
- `SYSTEM_WEAKNESS_MAP.md` — 系统软肋地图完整版
- `INFRASTRUCTURE.md` — 架构、部署、缓存、数据库完整规范