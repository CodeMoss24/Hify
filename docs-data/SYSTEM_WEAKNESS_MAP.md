# Hify 系统软肋地图

> 本文档记录系统可能的性能瓶颈。按严重程度排序，标注触发条件和处理策略。
> 后续出现性能问题时，以本文档为索引，不用猜测。

---

## 一、瓶颈优先级

| 优先级 | 瓶颈 | 触发条件 | 一期处理？ |
|--------|------|----------|------------|
| **1** | LLM API 延迟 | 任何对话请求 | ✅ 必须处理 |
| **2** | SSE event loop 阻塞 | 20+ 并发对话 | ✅ 必须处理 |
| **3** | MySQL 连接池耗尽 | 30+ 并发用户 | ⚠️ 监控 + 配置 |
| **4** | Redis 内存压力 | 50 用户 × 多轮对话 | ⚠️ 设置 maxmemory |
| **5** | Qdrant 向量检索 | 开启 RAG 的对话 | ❌ 一期够用 |

---

## 二、已处理事项（一期必须做）

### 1. LLM 调用（超时 + 断路器 + 并发控制）

**问题：** 外部 LLM API 慢（2-30s），是系统响应时间的天花板。

**处理方案：**

| 措施 | 配置 |
|------|------|
| SSE 流式超时 | 120s |
| 管理/测试请求超时 | 10s |
| 全局并发上限 | 10 |
| 每 Provider 并发上限 | 5 |
| 断路器失败阈值 | 连续 5 次 |
| 断路器恢复超时 | 30s |
| 重试次数 | 3 |
| 401/403/400 不重试 | 明确排除 |

**详见：** `LLM_TECHNICAL_DESIGN.md`

### 2. SSE 优先级隔离

**问题：** SSE 长连接占用 event loop，阻塞管理页面请求。

**处理方案：**
- 对话请求：`chat_complete()` / `stream()`，受 `chat_semaphore` 限制
- 管理请求：`admin_call()`，不受限制，快速响应

**详见：** `LLM_TECHNICAL_DESIGN.md` 第一节「请求分类与优先级」

### 3. Nginx gzip 压缩

**问题：** 静态资源未压缩，首屏加载慢。

**处理：** Nginx 配置开启 gzip

```nginx
# nginx.conf
gzip on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript;
gzip_vary on;
gzip_proxied any;
```

---

## 三、已知但暂不处理

> 以下问题存在，但触发条件未到。记录在此，等时机成熟时处理。

### 3.1 MySQL 连接池耗尽

**问题：** 高并发时连接池不够用，新请求排队。

**触发条件：** 30+ 并发用户。

**处理方向：**
```python
# app/common/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)
```

**触发条件到了再动：** 监控 `Active connections`，超过阈值时调整。

---

### 3.2 Redis 内存压力

**问题：** 会话上下文缓存占用内存。

**触发条件：** 50 用户 × 多轮对话（每轮 1KB × 20 轮）。

**处理方向：**
```bash
# redis.conf
maxmemory 64mb
maxmemory-policy allkeys-lru
```

**触发条件到了再动：** 监控 Redis 内存使用率，超过 80% 时调整 `maxmemory`。

---

### 3.3 Qdrant 向量检索延迟

**问题：** RAG 查询向量库，增加 prompt 组装时间。

**触发条件：** 知识库文档多、查询频繁。

**处理方向：**
- Qdrant 延迟本身 50-200ms，不是主要瓶颈
- 主要是 LLM 那边的延迟（2-30s），Qdrant 影响相对小
- 等文档量上万、查询 QPS 变高时再优化

**触发条件到了再动：** 监控 Qdrant 查询延迟，超过 500ms 时考虑优化（分片、索引调优）。

---

### 3.4 FastAPI 同步 DB 调用阻塞 event loop

**问题：** 同步数据库操作阻塞事件循环。

**触发条件：** 复杂查询（JOIN 多表、大数据量）。

**处理方向：**
- 写代码时注意 `await` 正确使用
- 复杂查询用 `asyncio.to_thread()` 包装
- 监控 event loop 延迟

**触发条件到了再动：** 监控 `event loop lag`，超过 100ms 时排查同步调用。

---

## 四、后续扩展方向

当用户量或数据量上来时，按以下顺序处理：

| 触发条件 | 处理优先级 | 处理内容 |
|----------|-----------|----------|
| 并发用户 > 30 | 1 | 调整 MySQL 连接池配置 |
| Redis 内存 > 80% | 2 | 设置 maxmemory + LRU 淘汰 |
| Qdrant 延迟 > 500ms | 3 | 向量库索引优化或升级硬件 |
| 多实例部署 | 4 | 引入会话粘性策略（Redis Session） |
| 数据量 > 1000 万 | 5 | 数据库分库分表、读写分离 |
| 需要链路追踪 | 6 | 引入 Prometheus + Grafana |

---

## 五、监控指标

| 组件 | 关键指标 | 告警阈值 |
|------|----------|----------|
| LLM | 调用延迟、错误率、断路器状态 | 延迟 > 30s 或 错误率 > 10% |
| FastAPI | event loop lag、并发连接数 | lag > 100ms |
| MySQL | Active connections、Query latency | 连接数 > 20 或 QLatency > 500ms |
| Redis | 内存使用率、连接数 | 内存 > 80% |
| Qdrant | 查询延迟、向量数量 | 延迟 > 500ms |

---

## 六、快速索引

| 问题现象 | 可能原因 | 查哪个配置 |
|----------|----------|-----------|
| 对话响应慢 | LLM API 慢 / 超时 | LLM_TIMEOUT / 断路器状态 |
| 管理页面转圈 | event loop 被 SSE 阻塞 | chat_semaphore / admin_call |
| 请求排队 | MySQL 连接池不够 | pool_size / max_overflow |
| Redis OOM | 内存设置过小 | maxmemory 配置 |
| RAG 结果不准 | Qdrant 向量检索问题 | 查询延迟 / 向量索引状态 |

---

## 文档版本

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-05-10 | 初始版本，记录一期瓶颈分析和处理策略 |