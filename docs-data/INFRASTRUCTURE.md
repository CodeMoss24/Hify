# Hify 架构部署、缓存策略与数据库规范

本文档汇总架构设计、部署方案、缓存策略和数据库规范。

---

## 一、应用架构

### 模块划分

```
hify/
├── hify-app/               # 启动模块（FastAPI main.py）
├── hify-provider/           # 模型提供商管理
├── hify-agent/             # Agent 管理与配置
├── hify-chat/              # 对话引擎
├── hify-mcp/               # MCP 工具管理与调用
├── hify-workflow/          # 工作流编排与执行
├── hify-knowledge/         # 知识库与 RAG
├── hify-common/            # 公共模块（工具类、常量、异常、DTO）
├── hify-web/               # Vue 前端
└── deploy/                 # Docker Compose 配置
```

对应到 Python FastAPI 的模块结构：

```
app/
├── main.py                 # FastAPI 入口
├── common/                  # 公共模块（config/exceptions/utils）
├── provider/                # 模型提供商
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

## 二、代码组织规范

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

### 命名规则

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 请求模型 | `{Entity}Create` / `{Entity}Update` | `AgentCreate` |
| 响应模型 | `{Entity}Response` | `AgentResponse` |
| ORM 模型 | `{Entity}Model` | `AgentModel` |
| 服务接口 | `I{Entity}Service` | `IAgentService` |
| 服务实现 | `{Entity}Service` | `AgentService` |
| 数据库表 | `tb_{module}_{entity}` | `tb_agent` |

---

## 三、部署架构

### 组件清单

```
┌─────────────────────────────────────────────────────────┐
│                    用户浏览器                            │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Nginx (反向代理)                       │
│              端口：80/443                                │
│         - 静态资源 / 前端_dist                           │
│         - API 反向代理到后端                             │
│         - SSE 流式响应优化（proxy_buffering off）        │
│         - gzip 压缩                                     │
└────────────┬───────────────────────────┬────────────────┘
             │                           │
             ▼                           ▼
┌────────────────────────┐    ┌─────────────────────────┐
│   Vue 前端 (静态资源)   │    │   FastAPI 后端           │
│   端口：由 Nginx Serve  │    │   端口：8000              │
└────────────────────────┘    │                          │
                               │   - API 路由             │
                               │   - 业务逻辑             │
                               │   - SSE 流式响应         │
                               └────────────┬────────────┘
                                            │
              ┌────────────────────────────┼────────────────┐
              │            ┌─────────────────┴───┐            │
              ▼            ▼                    ▼            ▼
     ┌────────────┐  ┌───────────┐       ┌──────────┐  ┌──────────┐
     │   MySQL    │  │   Redis   │       │  Qdrant  │  │ LLM APIs │
     │   3306     │  │   6379     │       │   6333   │  │(外部)    │
     │  数据持久化 │  │  会话缓存   │       │ 向量存储  │  └──────────┘
     └────────────┘  └───────────┘       └──────────┘
```

### 组件职责

| 组件 | 职责 | 数据持久化 |
|------|------|------------|
| **Nginx** | 反向代理、静态资源、SSE 透传、gzip | 无 |
| **Vue 前端** | 静态资源（由 Nginx 托管） | — |
| **FastAPI 后端** | API 路由、业务逻辑、SSE 流式、LLM 调用 | 无（stateless） |
| **MySQL** | 业务数据持久化 | ✅ Docker volume |
| **Redis** | 会话上下文缓存 | 可选 volume |
| **Qdrant** | 向量数据库、RAG 向量存储 | ✅ Docker volume |
| **LLM APIs** | 外部服务 | — |

### Nginx 配置关键点

```nginx
server {
    listen 80;

    # 前端静态资源
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    # SSE 流式响应优化
    location /chat/stream {
        proxy_pass http://backend:8000;
        proxy_buffering off;       # 关键：关闭缓冲
        chunked_transfer_encoding on;
        proxy_cache off;
        proxy_read_timeout 120s;
    }

    # gzip 压缩
    gzip on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_vary on;
    gzip_proxied any;
}
```

---

## 四、缓存策略

### 缓存分层

| 层级 | 组件 | 缓存内容 | TTL |
|------|------|----------|-----|
| **配置缓存** | Redis | Provider/Agent 配置 | 长期 |
| **会话缓存** | Redis | 对话上下文（最近 10 轮） | 24h |
| **向量缓存** | Qdrant | 文档向量 | 持久化 |
| **LLM 响应** | 不缓存 | — | — |

### Redis 配置

```bash
# redis.conf
maxmemory 64mb
maxmemory-policy allkeys-lru
```

### 不缓存的内容

- LLM 响应（每次对话结果不同）
- 实时性要求高的数据

---

## 五、数据表结构

### 核心表清单（18 张）

```
tb_model_provider          # 模型提供商
tb_model                  # 模型配置
tb_agent                  # Agent
tb_agent_knowledge_base   # Agent-知识库关联
tb_agent_tool            # Agent-工具关联
tb_mcp_server            # MCP服务器
tb_mcp_tool              # MCP工具
tb_knowledge_base        # 知识库
tb_document              # 文档
tb_document_chunk        # 文档块
tb_conversation          # 对话会话
tb_message               # 消息
tb_message_reference     # RAG溯源关联
tb_workflow              # 工作流
tb_workflow_node         # 工作流节点
tb_workflow_edge         # 工作流边
tb_user                  # 用户
tb_api_key               # API密钥
```

### 通用字段约定

每张表必须有四个公共字段：

```sql
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
deleted TINYINT(1) NOT NULL DEFAULT 0
```

### 索引设计五条规矩

| 规矩 | 说明 |
|------|------|
| **1. deleted 必须加入索引** | 几乎所有查询都带 `deleted = 0` |
| **2. 组合索引等值在前，范围在后** | `(conversation_id, created_at)` |
| **3. 多对多关联表两个方向都要索引** | `agent_tool` 表要 `(agent_id, tool_id)` 和 `(tool_id)` |
| **4. 唯一约束用 UNIQUE INDEX** | 数据库约束是最后防线 |
| **5. 禁止 TEXT 字段建索引** | 需要全文搜索用 ES |

### 分页规范

```sql
-- ✅ 游标分页（推荐）
WHERE conversation_id = ? AND id < #{lastId} AND deleted = 0

-- ❌ 禁止 OFFSET 深分页（百万行时极慢）
LIMIT 20 OFFSET 100000
```

---

## 六、扩展路径

### 三阶段扩展路径

| 阶段 | 目标用户 | 触发条件 | 核心改动 |
|------|----------|----------|----------|
| **Phase 1** | 50 → 500 | 响应变慢，CPU/内存告警 | 多副本 + 读写分离 + CDN |
| **Phase 2** | 500 → 2000 | LLM 调用队列堆积，P99 > 2s | MQ 异步化 + 分库 |
| **Phase 3** | 2000 → 几千 | 模块发布互相干扰 | 微服务拆分 + API Gateway |

### 全程不变的组件

- 模块边界（provider/agent/chat/knowledge/workflow/mcp）
- 技术栈（FastAPI + MySQL + Redis + Qdrant）
- 部署形态（容器化）

---

## 七、系统软肋地图

### 瓶颈优先级

| 优先级 | 瓶颈 | 触发条件 | 一期处理？ |
|--------|------|----------|------------|
| **1** | LLM API 延迟 | 任何对话请求 | ✅ 必须处理 |
| **2** | SSE event loop 阻塞 | 20+ 并发对话 | ✅ 必须处理 |
| **3** | MySQL 连接池耗尽 | 30+ 并发用户 | ⚠️ 监控 + 配置 |
| **4** | Redis 内存压力 | 50 用户 × 多轮对话 | ⚠️ 设置 maxmemory |
| **5** | Qdrant 向量检索 | 开启 RAG 的对话 | ❌ 一期够用 |

### 一期只做两件事

| 事项 | 内容 |
|------|------|
| **LLM 调用** | 超时（120s）+ 断路器 + 并发控制（Semaphore） |
| **Nginx gzip** | 一行配置，首屏加载加速 |

### 其他已知瓶颈（暂不处理）

- MySQL 连接池耗尽 → 等并发 > 30 再处理
- Redis 内存压力 → 等内存 > 80% 再处理
- Qdrant 延迟 → 等文档量上来再处理

---

## 八、详细文档索引

| 文档 | 内容 |
|------|------|
| `CODE_ORGANIZATION.md` | 代码组织规范完整版 |
| `DATABASE_PERFORMANCE.md` | 数据库性能规范完整版 |
| `LLM_TECHNICAL_DESIGN.md` | LLM 调用技术方案完整版 |
| `SCALING_PATH.md` | 扩展路径规划完整版 |
| `SYSTEM_WEAKNESS_MAP.md` | 系统软肋地图完整版 |