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

**每个模块 service.py 的 import 清单（必须严格遵守）：**

```python
# Layer 1: provider / mcp / knowledge
# service.py 不 import 任何业务模块（它们是基础能力，不被依赖）
from app.provider.interfaces import IProviderService, IModelService
from app.mcp.interfaces import IMcpServerService, IMcpToolService
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService

# Layer 2: agent
# service.py 必须 import Layer 1 的接口
from app.provider.interfaces import IProviderService, IModelService
from app.mcp.interfaces import IMcpServerService, IMcpToolService
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService

# Layer 3: workflow
# service.py 必须 import Layer 1 的接口
from app.provider.interfaces import IProviderService, IModelService
from app.mcp.interfaces import IMcpServerService, IMcpToolService
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService

# Layer 4: chat
# service.py 必须 import Layer 1 + Layer 2 + Layer 3 的所有接口
from app.provider.interfaces import IProviderService, IModelService
from app.mcp.interfaces import IMcpServerService, IMcpToolService
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService
from app.agent.interfaces import IAgentService
from app.workflow.interfaces import IWorkflowService
```

| 调用方 | 被调用方 | 允许？ |
|--------|----------|--------|
| chat.service | agent.service | ✅ |
| chat.service | provider.service | ✅ |
| chat.service | mcp.service | ✅ |
| chat.service | knowledge.service | ✅ |
| chat.service | workflow.service | ✅ |
| agent.service | chat.service | ❌ |
| agent.service | provider.service | ✅ |
| agent.service | mcp.service | ✅ |
| agent.service | knowledge.service | ✅ |
| workflow.service | mcp.service | ✅ |
| workflow.service | knowledge.service | ✅ |
| workflow.service | agent.service | ❌ |
| workflow.service | chat.service | ❌ |

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

**健康检查接口使用专用的健康状态响应格式（见下方健康检查规范），不使用 ApiResponse。**

### 分页

| 参数 | 说明 |
|------|------|
| page | 页码，从 1 开始 |
| page_size | 每页数量，默认 20，最大 100 |

```python
class PageResult(ApiResponse, Generic[T]):
    """统一分页响应，继承 ApiResponse，顶层结构为 {code, message, data}"""
    list: list[T]
    total: int
    page: int
    page_size: int
    # data 字段由 ApiResponse 提供，类型为 Optional[dict]（自动包含分页字段）
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

### 数据访问规则

- 查询业务表时，使用 `Model.find_all(session)` 方法，禁止直接使用 `session.query(Model)`
- 逻辑删除由 `SoftDeleteMixin` 实现，删除时调用 `model.soft_delete()`，不是 `session.delete()`
- 时间戳由 `TimestampMixin` 自动填充，无需手动维护 `created_at` / `updated_at`

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
## 测试体系
### 核心链路（按优先级）
1. **SSE流式对话链路**：ChatService.send_message() → AgentService / ProviderAdapter / LlmClient.stream() / ContextManager / RAG检索 / MCP工具调用。系统最核心链路，涉及全部Layer 1-3模块。
2. **Agent配置与绑定链路**：AgentService.create/update/bind_*()。所有功能的入口，绑定错误会导致RAG/工具/工作流全部失效。
3. **知识库文档处理链路**：DocumentService.upload_document() → DocumentPipeline.run() → LlmClient.embed() → Qdrant。RAG功能基础，异步任务处理。
4. **工作流执行链路**：WorkflowEngine.execute() → ExecutionContext → ProviderAdapter。图遍历+条件分支+审计记录。

### 高风险区域（必须重点测试）
| 区域 | 风险类型 | 典型致命失败场景 |
|------|----------|------------------|
| `ChatService.send_message` | 并发/一致性 | SSE阻塞event loop、消息已推送但未持久化、**Redis上下文并发写覆盖**、**长对话取最旧消息而非最新** |
| `LlmClient` | 可靠性 | 熔断器频繁打开、流式连接挂起、429/5xx重试逻辑错误 |
| `AgentService绑定操作` | 数据一致性 | 全量替换中间失败、并发竞态、级联软删部分成功 |
| `DocumentPipeline` | 可靠性 | 异步任务失败无重试、文档卡pending、进程重启丢任务 |
| 全局安全 | 安全 | **ProviderResponse暴露明文api_key**、跨模块直接import Model而非接口 |

### 测试重心
**✅ 必须100%覆盖（P0）**
- ChatService所有分支：纯对话/工具调用/RAG增强/工作流/LLM异常降级
- LlmClient：熔断器状态切换、重试策略、HTTP状态码映射
- AgentService绑定操作：全量替换正确性、幂等性、级联删除
- WorkflowEngine：流程执行、条件分支、最大步数保护、失败状态标记

**❌ 可以先跳过**
- 前端E2E测试、性能基准测试
- 复杂工作流（10+节点）、管理接口admin_get/post
- 纯CRUD接口的边界场景

### 核心测试原则
**异常路径优先于正常路径**。正常路径大家都能写对，90%的线上bug都出在异常处理上。

### 单元测试规范

#### 目录结构

```
tests/
├── conftest.py                  # 全局 fixtures（db session mock、async 支持等）
├── infrastructure/
│   └── llm/
│       ├── test_circuit_breaker.py
│       ├── test_retry_handler.py
│       └── test_llm_client.py
├── agent/
│   └── test_agent_service.py
├── chat/
│   ├── test_chat_service.py
│   └── test_context_manager.py
├── workflow/
│   └── test_workflow_engine.py
├── provider/
│   └── test_adapter.py
├── knowledge/
│   └── test_document_service.py
└── mcp/
    └── test_mcp_service.py
```

#### 必须写单测的代码

| 被测类/方法 | 理由 |
|------------|------|
| `CircuitBreaker` — `can_execute` / `record_success` / `record_failure` | 纯状态机，0 外部依赖，核心链路的容错基础，3 种状态 + 半开探测逻辑 |
| `RetryHandler` — `execute_with_retry` / `should_retry` | 纯逻辑，无副作用，需覆盖 429 重试/401 不重试/超过 max_retries 等分支 |
| `LlmClient._raise_by_status` / `post` / `stream` | 所有 LLM 调用的唯一出口，HTTP 状态码→异常映射是正确熔断的前提 |
| `ContextManager.get_history` / `add_message` | 对话上下文正确性是 SSE 链路正确的前提（缓存命中/未命中/滑动窗口） |
| `ChatService.send_message` — 纯流式路径（无工具、无 RAG） | 核心链路最常用分支 |
| `ChatService.send_message` — 工具调用路径（`finish_reason=tool_calls`） | 风险最高分支：两轮 LLM 调用 + 工具执行 |
| `WorkflowEngine._find_next_node` | 条件分支路由是工作流正确性的核心 |
| `WorkflowEngine.execute` — 线性流程（START → LLM → END） | 工作流最基础路径，节点执行记录写入、成功/失败状态标记 |
| `AgentService.bind_tools` | 全量替换 + 校验链路长（tool 存在 → server 启用），并发下最易出问题 |
| `AgentService.update_agent` — 知识库重绑定 | DELETE + INSERT 两步操作的数据一致性，中间失败场景必须覆盖 |
| `ProviderAdapter._extract_error_message` | 纯函数，多 Provider 错误格式解析，出问题影响排障 |

#### 绝对不写单测、用集成测试替代

| 代码 | 理由 |
|------|------|
| **Router 层**（所有 `router.py`） | 核心逻辑只有「参数校验→调 service→包装响应」。FastAPI 中间件、序列化、异常处理链路只能用 `TestClient` 集成测试覆盖 |
| **CRUD 操作**（`list_*` / `get_*` / `create_*` / `delete_*`） | 本质是 SQL 查询 + ORM 映射，mock 掉 DB 等于测空壳。索引是否命中、软删是否正确、级联是否生效必须对真实 MySQL 跑 |
| **`DocumentPipeline.run()`** | 涉及文件读取、分块、Embedding API、Qdrant 写入，每一步都是外部系统交互，单测要 mock 一切，集成测试直接跑真实流程更有价值 |
| **`DocumentChunkService.search_chunks()`** | Embedding API → Qdrant 检索，向量检索的 score 和排序行为无法通过 mock 验证 |
| **`ProviderAdapter.test_connection()` 及子类实现** | 测的就是和外部 LLM API 的连通性，mock 掉外部调用失去全部意义 |
| **`LlmClient.embed()`** | 测的是 Embedding API 实际返回维度和格式，需要真实 API |

#### 测试命名规范

统一格式：**`should_[期望结果]_when_[输入条件]`**

```python
# ✅ 正确
def test_should_return_true_when_circuit_is_closed():
def test_should_open_circuit_when_failures_reach_threshold():
def test_should_retry_when_rate_limited():
def test_should_not_retry_when_auth_failed():
def test_should_soft_delete_old_bindings_when_bind_tools_called():
def test_should_mark_workflow_failed_when_node_execution_throws():
def test_should_walk_default_edge_when_condition_not_matched():

# ❌ 错误
def test_circuit_breaker():           # 太模糊
def test_case1():                      # 无意义编号
def test_send_message_works():         # works 不够精确
def test_error():                      # 什么错误？
```

#### 测试结构：Given-When-Then

每个测试方法内部分三段，用空行分隔，不写注释标注：

```python
async def test_should_return_cached_history_when_redis_hit():
    # Given
    ctx = ContextManager()
    conversation_id = 1
    cached = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    mock_redis = AsyncMock()
    mock_redis.lrange.return_value = [json.dumps(m) for m in cached]
    redis_client._client = mock_redis

    # When
    result = await ctx.get_history(mock_db, conversation_id, max_turns=10)

    # Then
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "hello"
    mock_redis.lrange.assert_called_once_with("session:1", 0, -1)
```

#### Mock 使用规范

**原则：只 mock 跨越本类边界的外部依赖。**

该 mock 的：
- 数据库 Session（`Mock(spec=Session)`）
- 其他模块的 Service 接口（`create_autospec(IAgentService)`）
- Redis 客户端（`AsyncMock()`）
- HTTP 客户端（`AsyncMock()`）
- Provider Adapter 子类（`create_autospec(OpenAiAdapter)`）
- Qdrant 客户端

绝对不能 mock 的：
- **标准库**（`json`、`datetime`、`asyncio`、`time`）——标准库行为是稳定契约
- **被测类自身的方法**——mock 自己等于测空转
- **Pydantic 模型 / DTO**——纯数据结构，直接构造实例
- **SQLAlchemy ORM 模型**——直接构造实例，如 `MessageModel(role="user", content="hello")`
- **`BizException` / `ErrorCode`**——异常本身就是测试断言的目标

```python
# ✅ 正确：mock 外部 service 接口
mock_agent_service = create_autospec(IAgentService)
mock_agent_service.get_agent.return_value = fake_agent_response

# ❌ 错误：mock 标准库
mock_json = mocker.patch("json.dumps")

# ❌ 错误：mock 被测类自己的方法
mocker.patch.object(chat_service, "_get_last_message_text")
```

#### 断言规范

用 pytest 原生 `assert`，断言必须一眼看出在验证什么：

```python
# ✅ 正确
assert result.code == 200
assert len(items) == 3
assert items[0].name == "GPT-4"

# 验证异常
with pytest.raises(BizException) as exc:
    await service.get_agent(mock_db, 999)
assert exc.value.code == ErrorCode.AGENT_NOT_FOUND.code

# 验证副作用（断言参数的具体值，不是只 assert called）
mock_db.add.assert_called_once()
call_args = mock_db.add.call_args[0][0]
assert call_args.role == "assistant"
assert call_args.content == "expected response"

# ❌ 错误
assert True                              # 永远为真
assert result is not None                # 太弱
assert len(result) > 0                   # 不够精确
```

测异常时必须同时 assert `exc.value.code`（错误码）和 `exc.value.message`（消息内容），只 assert 抛出异常是不够的。

#### 禁止事项

1. **禁止在测试中重复实现业务逻辑**——期望值必须硬编码，不能把被测方法的核心逻辑又写一遍来算 expected。
2. **禁止 mock 掉全部依赖测空转**——mock 外部依赖后，核心逻辑必须真正执行。只证明「代码跑了」不证明「代码对了」。
3. **禁止一个测试方法覆盖多个场景**——每个场景一个独立测试方法，失败时能立刻定位。
4. **禁止在测试中使用真实的外部服务**（数据库、Redis、外部 API）——单测中用 mock，真实服务走集成测试。
5. **禁止跳过异常用例**——核心链路异常场景数量 ≥ 正常场景数量。
6. **禁止在 setUp/teardown 中隐藏核心测试逻辑**——每个测试方法 Given 段内自包含。如果 fixture 复用率很高，用 conftest.py 的 `@pytest.fixture`。
7. **禁止对有副作用的异步生成器不做 cleanup**——`async generator` 没跑完要显式 `await gen.aclose()`。

---

## 可观测性与日志规范

### 技术选型

- **日志库**：`structlog`（结构化日志，开发环境彩色 ConsoleRenderer，生产环境 JSONRenderer）
- **日志输出**：应用代码走 `structlog.PrintLoggerFactory`（stdout / 文件），第三方库（uvicorn、sqlalchemy）走 stdlib logging
- **链路追踪**：`X-Request-ID` header（Nginx 生成 → FastAPI 中间件透传 → structlog.contextvars 注入 → 响应 header 返回）
- **指标暴露**：待建设（一期计划引入 `prometheus_client` + Prometheus + Grafana）

### 日志字段常量

所有日志字段名和事件名必须使用 `app/common/logging.py` 中定义的常量，禁止在代码中硬编码字段名字符串。

**通用字段：**
- `LOG_KEY_CORRELATION_ID` = `"correlation_id"`
- `LOG_KEY_MODULE` = `"module"`

**LLM 调用专用字段：**
- `LOG_KEY_PROVIDER` = `"provider"`
- `LOG_KEY_MODEL` = `"model"`
- `LOG_KEY_ACTION` = `"action"`
- `LOG_KEY_METHOD` = `"method"`
- `LOG_KEY_URL` = `"url"`
- `LOG_KEY_LATENCY_MS` = `"latency_ms"`
- `LOG_KEY_STATUS_CODE` = `"status_code"`
- `LOG_KEY_ERROR_CODE` = `"error_code"`

**熔断器字段：**
- `LOG_KEY_FROM_STATE` = `"from_state"`
- `LOG_KEY_TO_STATE` = `"to_state"`
- `LOG_KEY_FAILURE_COUNT` = `"failure_count"`

**重试字段：**
- `LOG_KEY_RETRY_COUNT` = `"retry_count"`
- `LOG_KEY_ATTEMPT` = `"attempt"`
- `LOG_KEY_MAX_RETRIES` = `"max_retries"`
- `LOG_KEY_DELAY` = `"delay"`

**事件名常量：**
- `EVENT_LLM_CALL_START` = `"llm_call.start"`
- `EVENT_LLM_CALL_END` = `"llm_call.end"`
- `EVENT_LLM_STREAM_START` = `"llm_stream.start"`
- `EVENT_LLM_STREAM_END` = `"llm_stream.end"`
- `EVENT_CIRCUIT_STATE_CHANGE` = `"circuit_breaker.state_change"`
- `EVENT_CIRCUIT_REJECTED` = `"circuit_breaker.rejected"`
- `EVENT_RETRY` = `"retry.attempt"`
- `EVENT_RETRY_EXHAUSTED` = `"retry.exhausted"`

### Correlation ID 链路

```
Nginx(生成/透传 X-Request-ID) → FastAPI CorrelationIdMiddleware(注入 contextvars)
  → structlog 自动携带 correlation_id
  → Response Header(X-Request-ID)
  → SSE error 事件注入 correlationId
  → 前端报错可直接贴 correlation_id 定位
```

- Nginx 配置：`proxy_set_header X-Request-ID $request_id;`
- FastAPI 中间件：从 header 读取，没有则生成 UUID7（时间排序友好）
- 外部模块获取：`from app.common.logging_config import get_correlation_id`

### 日志输出格式

**开发环境（APP_ENV=dev 或未设置）：**
```
2024-01-01T12:00:00.000Z [info] [hify.llm] llm_call.start  correlation_id=xxx provider=openai model=gpt-4 method=stream
```

**生产环境（APP_ENV=prod）：**
```json
{"timestamp": "2024-01-01T12:00:00.000Z", "level": "info", "logger": "hify.llm", "event": "llm_call.start", "correlation_id": "xxx", "provider": "openai", "model": "gpt-4", "method": "stream"}
```

### 关键日志点

| 位置 | 事件 | 字段 |
|------|------|------|
| `LlmClient.post` 开始 | `llm_call.start` | provider, model, method, url |
| `LlmClient.post` 结束 | `llm_call.end` | provider, model, method, url, status_code, latency_ms |
| `LlmClient.stream` 开始 | `llm_stream.start` | provider, model, method, url |
| `LlmClient.stream` 结束 | `llm_stream.end` | provider, model, url, status_code, latency_ms |
| `CircuitBreaker.can_execute` 半开转换 | `circuit_breaker.state_change` | provider, from_state, to_state |
| `CircuitBreaker.record_success` 关闭 | `circuit_breaker.state_change` | provider, from_state, to_state, failure_count |
| `CircuitBreaker.record_failure` 打开 | `circuit_breaker.state_change` | provider, from_state, to_state, failure_count |
| 熔断拒绝 | `circuit_breaker.rejected` | provider, model, url |
| `RetryHandler` 重试 | `retry.attempt` | attempt, max_retries, delay |
| `RetryHandler` 耗尽 | `retry.exhausted` | attempt, max_retries |
| `ChatService` SSE 异常 | `send_message.biz_error` / `send_message.unexpected_error` | error_code / error |
| 全局异常处理器 | `exception.biz` / `exception.validation` / `exception.unhandled` | path, error_code, traceback |
| 请求完成 | `request.completed` / `request.slow` | method, path, status_code, latency_ms |

### 使用规范

**获取 logger：**
```python
import structlog
logger = structlog.get_logger(__name__)
```

**打日志（结构化）：**
```python
# ✅ 正确：event 字符串 + 关键字字段
logger.info("llm_call.start", provider="openai", model="gpt-4", method="stream")
logger.warning("circuit_breaker.state_change", provider="openai", from_state="closed", to_state="open")

# ❌ 错误：硬编码字段名字符串
logger.info("llm_call.start", {"provider": "openai"})
```

**打日志（简单消息）：**
```python
# 也允许，event 自动设为消息内容
logger.info("Agent started successfully")
```

**生产环境日志输出：**
- 应用日志（structlog）：stdout，JSON 格式
- 第三方库日志（stdlib）：stdout，JSON 格式
- 日志轮转和持久化交由 Docker logging driver 处理（`json-file` + `max-size` / `max-file`）

---

## 指标规范

### 技术选型

- **库**：`prometheus_client`（Python 标准 Prometheus 客户端）
- **暴露方式**：FastAPI `/metrics` 端点，不走 Nginx，仅内部 Prometheus 抓取
- **指标管理**：所有指标定义集中在 `app/common/metrics.py`

### 指标命名

前缀统一 `hify_`，命名遵循 `<namespace>_<metric>_<unit>` 模式。

### 指标清单

#### hify_chat_requests_total（Counter）

对话请求总数。

| Label | 说明 |
|-------|------|
| `agent_id` | Agent ID（字符串） |
| `status` | `success` / `error` |

埋点位置：`app/chat/service.py` — `ChatService.send_message()` 各退出点。

#### hify_chat_request_duration_seconds（Histogram）

对话请求延迟分布。

| Label | 说明 |
|-------|------|
| `agent_id` | Agent ID（字符串） |

Bucket: `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]`

埋点位置：同上 `send_message()` 各退出点。

#### hify_llm_calls_total（Counter）

LLM 调用总数。

| Label | 说明 |
|-------|------|
| `provider` | 模型提供商（openai/anthropic/gemini/ollama/ark） |
| `model` | 模型名（gpt-4/claude-3 等） |
| `method` | 调用方法（post/stream/admin_get/admin_post） |
| `status` | `success` / `fail` |

埋点位置：`app/infrastructure/llm/llm_client.py` — `_do_post` / `_do_stream` / `_do_get` / `_do_admin_post` 各退出点。

#### hify_llm_call_duration_seconds（Histogram）

LLM 调用延迟分布。

| Label | 说明 |
|-------|------|
| `provider` | 模型提供商 |
| `model` | 模型名 |
| `method` | 调用方法（post/stream/admin_get/admin_post） |

Bucket: `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]`

埋点位置：同上 `_do_post` / `_do_stream` / `_do_get` / `_do_admin_post` 各退出点。

**注意：`stream` 方法的延迟为完整流式读取时间（连接建立 + 全部 token 接收），非仅连接建立时间。**

#### hify_circuit_breaker_state（Gauge）

各 Provider 熔断器状态。

| Label | 说明 |
|-------|------|
| `provider` | Provider base_url |

| 值 | 状态 |
|----|------|
| 0 | CLOSED（正常） |
| 1 | OPEN（熔断） |
| 2 | HALF_OPEN（半开探测） |

埋点位置：`app/infrastructure/llm/circuit_breaker.py` — `CircuitBreaker` 状态变更时更新。

#### hify_mcp_tool_calls_total（Counter）

MCP 工具调用总数。

| Label | 说明 |
|-------|------|
| `tool_name` | 工具名称 |
| `status` | `success` / `fail` |

埋点位置：`app/mcp/service.py` — `McpToolService.call_tool()` 结束点。

### /metrics 端点

```python
# app/main.py
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

- 不走 Nginx 对外暴露（Nginx 配置中 `/metrics` 无 `proxy_pass`，命中 `location /` 返回静态文件）
- Prometheus 直接抓取 `backend:8000/metrics`
- 使用 `prometheus_client` 默认全局 Registry，无需手动管理

### 使用规范

```python
# ✅ 正确：从 app.common.metrics 导入指标对象，调用 .labels().inc() / .observe() / .set()
from app.common.metrics import llm_calls_total, llm_call_duration_seconds

llm_calls_total.labels(provider="openai", model="gpt-4", method="post", status="success").inc()
llm_call_duration_seconds.labels(provider="openai", model="gpt-4", method="post").observe(elapsed)

# ✅ 正确：label value 必填，无值用空字符串
llm_calls_total.labels(provider=provider or "", model=model or "", method="post", status="fail").inc()

# ❌ 错误：跳过 .labels() 直接调用
llm_calls_total.inc()

# ❌ 错误：label 数量不匹配
llm_calls_total.labels(provider="openai").inc()
```

---

## 健康检查规范

### 端点

`GET /v1/health`（不走 `/api` 前缀，直接在 app 上注册）

### 检查项

| 组件 | 检查方式 | 是否必须 |
|------|---------|---------|
| MySQL | `SELECT 1` | 是，不可跳过 |
| Redis | `PING` | 否，未配置时显示 `skipped` |
| Qdrant | `get_collections()` | 否，未配置时显示 `skipped` |
| 熔断器 | 读取 `LlmClient._circuit_breakers` | — |

### 响应格式

```json
{
  "status": "UP | DEGRADED | DOWN",
  "components": {
    "mysql": {"status": "UP", "latency_ms": 2.0},
    "redis": {"status": "UP", "latency_ms": 1.0},
    "qdrant": {"status": "UP", "latency_ms": 5.0},
    "circuit_breakers": {
      "https://api.openai.com": "closed",
      "https://api.anthropic.com": "half_open"
    }
  }
}
```

每个组件可包含 `error` 字段（内部监控用，不暴露敏感信息）和 `message` 字段（`skipped` 状态时说明原因）。

### 状态判定规则

| 条件 | 整体状态 | HTTP 状态码 |
|------|---------|------------|
| MySQL DOWN | DOWN | 503 |
| MySQL UP + Redis DOWN | DEGRADED | 200 |
| MySQL UP + Qdrant DOWN | DEGRADED | 200 |
| MySQL UP + 全部 Provider 熔断器 OPEN | DEGRADED | 200 |
| 以上都不满足 | UP | 200 |

- 单个 Provider 熔断器 OPEN 不影响整体状态，仅展示在 `circuit_breakers` 中
- Redis/Qdrant `skipped` 不影响整体状态

### 实现位置

- 检查逻辑：`app/common/health.py`（`check_mysql` / `check_redis` / `check_qdrant` / `get_circuit_breakers_status` / `get_health_status`）
- 端点注册：`app/main.py`

---

## 监控部署（Prometheus + Grafana）

### 架构

```
backend:8000/metrics  ←── Prometheus (15s 抓取) ←── Grafana (仪表盘可视化)
```

两个服务仅 Docker 内网可访问，不经过 Nginx 对外暴露。

### Prometheus

- 镜像：`prom/prometheus`
- 端口：`9090`（仅 Docker 内网 + 本地 `localhost:9090`）
- 配置文件：`deploy/prometheus.yml`（只读挂载）
- 数据持久化：Docker volume `prometheus_data`
- 抓取目标：`backend:8000/metrics`，间隔 15s

### Grafana

- 镜像：`grafana/grafana`
- 端口：`3000`（仅 Docker 内网 + 本地 `localhost:3000`）
- 管理员密码：环境变量 `GRAFANA_PASSWORD`，默认 `hify123`
- 禁止用户注册：`GF_USERS_ALLOW_SIGN_UP=false`
- 数据持久化：Docker volume `grafana_data`
- 自动配置：Prometheus 数据源 + Hify 仪表盘（通过 provisioning 文件）

### 目录结构

```
deploy/
├── prometheus.yml                              # Prometheus 抓取配置
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── datasource.yml                  # 自动添加 Prometheus 数据源
│   │   └── dashboards/
│   │       └── dashboard.yml                   # 自动加载仪表盘
│   └── dashboards/
│       └── hify.json                           # Hify 监控仪表盘（JSON 模型）
├── nginx.conf                                  # Nginx 配置（屏蔽 /metrics + /v1/health 外部访问）
└── ...
```

### 仪表盘面板

| 面板 | 指标 | 类型 |
|------|------|------|
| 对话请求速率 | `rate(hify_chat_requests_total[5m])` by status | Time series |
| 对话 P95 延迟 | `histogram_quantile(0.95, rate(hify_chat_request_duration_seconds_bucket[5m]))` by agent_id | Time series |
| LLM 调用速率 | `rate(hify_llm_calls_total[5m])` by provider | Time series |
| LLM P95 延迟 | `histogram_quantile(0.95, rate(hify_llm_call_duration_seconds_bucket[5m]))` by provider, method | Time series |
| LLM 错误率 | `rate(hify_llm_calls_total{status="fail"}[5m])` by provider | Time series |
| 熔断器状态 | `hify_circuit_breaker_state`（值映射：0=CLOSED, 1=OPEN, 2=HALF_OPEN） | Table |
| MCP 工具调用 | `rate(hify_mcp_tool_calls_total[5m])` by tool_name | Time series |

### 访问方式

```bash
# Grafana 仪表盘（默认密码 hify123，可通过 GRAFANA_PASSWORD 环境变量修改）
open http://localhost:3000

# Prometheus 控制台
open http://localhost:9090
```

### 安全

- `/metrics` 端点：Nginx 显式返回 404，外部不可访问，仅 Prometheus 通过 Docker 内网抓取
- `/v1/health` 端点：Nginx 显式返回 404，外部不可访问，Docker healthcheck 通过 `/health` 内部路径访问
- Prometheus / Grafana 端口仅映射到宿主机 localhost，生产环境建议配合防火墙或 SSH 隧道

---

## 行为指令

### 写代码时
- 每个功能用最简单直接的方式实现
- 不引入不必要的设计模式，除非明确要求
- 不做过度抽象
- 不引入技术栈以外的依赖，需要时先问我
- 所有外部调用必须有超时设置
- 配置项外化到 `.env` 文件，通过 `app/common/config.py` 读取，不硬编码
- Redis 客户端统一用 `redis.asyncio`，不单独使用 `aioredis`
- **所有接口返回的数据，在进入响应封装前，必须全部转为 Pydantic DTO，禁止将 ORM 对象直接暴露给序列化层**（例如 `list_providers` 中 ORM 模型必须先通过 `ProviderResponse.from_orm()` 转 DTO 再传 `to_page_result`）
- **关联表更新优先全量替换**：数据量小时（如 Agent 绑定的工具列表），优先用 DELETE + INSERT 全量替换，逻辑比增量 diff 简单得多，不易出错
- **语义有歧义的接口要拆开**：如果同一个接口的某个参数有两种不同语义（如 toolIds 不传时是“清空工具”还是“不修改工具”），拆成两个独立接口，让每个接口的语义唯一、无歧义

### 改代码时
- 先理解相关模块的设计意图
- 不要为了新功能破坏已有接口契约
- 改完确保已有测试通过

### 不确定时
- 架构选择给 2-3 个方案对比，我来拍板
- 规范没覆盖的情况，先问，不要自己编规矩

---


