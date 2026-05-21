# Hify 项目测试总台账

> 所有测试工作围绕此文件展开。每完成一个方法，将 `- [ ]` 改为 `- [x]`。

---

## 执行策略

**分批推进，从底层到上层，从纯逻辑到需 mock。**

| 批次 | 方法数 | 特点 | 依赖 |
|------|--------|------|------|
| 第 1 批 | 14 | 纯函数/纯状态机，0 外部依赖 | 无 |
| 第 2 批 | 4 | Mock httpx/aiohttp，模式重复 | 第 1 批 |
| 第 3 批 | 7 | Mock DB Session + Redis，踩坑密集区 | 第 2 批 |
| 第 4 批 | 8 | 核心链路最复杂分支，组合前面所有 mock 模式 | 第 3 批 |

### 硬规则

1. **一批之内，写完再跑，不要写一个跑一个。**
2. **每批开始前，跑一遍上一批的测试**——确保没有退化。
3. **一批如果超过 2 小时还没写完，拆分后再继续**——避免疲劳写出低质量测试。
4. **每批写完、全部通过后，立即 commit。**
5. **写到一半发现被测代码有 bug，先修 bug，再继续写测试。** 不要带着已知 bug 写测试。
6. **ChatService.send_message 的 5 个分支分开 commit**——方便以后 git bisect 定位。
7. **一个方法 2-3 个核心场景够了，边界场景等出 bug 再补测试（回归测试）。**
8. **同一批内 mock 模式重复 3 次以上时，整批写完后再提取 conftest.py fixture，不要边写边重构。**

---

## 第 1 批：基础设施纯逻辑（14 方法）

**特点：纯函数/纯状态机，不需要 mock 任何东西，写完立刻能跑。**

### CircuitBreaker（3）

- [x] `CircuitBreaker.can_execute` — CLOSED 直接返回 True；OPEN 超时后切 HALF_OPEN 并放行；OPEN 未超时返回 False
- [x] `CircuitBreaker.record_success` — HALF_OPEN 成功后切 CLOSED 并清零 failure_count；CLOSED 下成功只清零计数
- [x] `CircuitBreaker.record_failure` — 失败次数达 threshold 切 OPEN；HALF_OPEN 下首次失败立即切 OPEN

### RetryHandler（2）

- [x] `RetryHandler.should_retry` — 429/5xx/TIMEOUT 返回 True；401/403 返回 False
- [x] `RetryHandler.execute_with_retry` — 可重试异常在 3 次内成功返回；超 max_retries 抛最后一次异常；不可重试异常直接 raise

### LlmClient（2）

- [x] `LlmClient._raise_by_status` — 401/403→LLM_AUTH_FAILED；429→LLM_RATE_LIMITED；5xx→LLM_SERVER_ERROR
- [x] `LlmClient._extract_base_url` — `https://api.openai.com/v1/chat` → `https://api.openai.com`；带端口号的 URL

### ProviderAdapter（1）

- [x] `ProviderAdapter._extract_error_message` — OpenAI 格式 `{"error":{"message":"x"}}` 正确提取；Anthropic 格式 `{"type":"error","error":{"message":"x"}}` 正确提取；无 error 字段返回 HTTP 状态码

### DocumentPipeline（4）

- [x] `DocumentPipeline._split_chunks` — 正常多段落文本分块；单段落超过 CHUNK_SIZE 走句子级分割；句子超 CHUNK_SIZE 走字符级截断；空文本返回空列表
- [x] `DocumentPipeline._split_paragraph` — 按 `。？！.?!` 边界分割；超长句子委托给 `_split_by_chars`
- [x] `DocumentPipeline._split_by_chars` — 正常截断且有 overlap；单字符文本（修复了死循环 bug）
- [x] `DocumentPipeline._estimate_tokens` — 纯中文估算；纯英文估算；中英混合估算

### ExecutionContext（1）

- [x] `ExecutionContext.resolve` — 存在变量替换为值；不存在变量保留原占位符 `{{unknown.var}}`；空模板返回空字符串

### WorkflowEngine（1）

- [x] `WorkflowEngine._find_next_node` — CONDITION 结果匹配指定边；未匹配走默认边（condition 为空的首条边）；非 CONDITION 节点跳过带 condition 的边；无边时返回 None

---

## 第 2 批：基础设施 HTTP 编排（4 方法）

**特点：需 mock httpx/aiohttp，但 mock 模式高度重复，学会一种就能写 4 个。**

- [ ] `LlmClient.post` — 熔断打开时直接抛异常不发起 HTTP；401/403 不触发 record_failure；正常响应走重试并记录成功
- [ ] `LlmClient.stream` — 熔断打开时快速失败；401/403 不触发熔断；正常流式响应逐行回调
- [ ] `ProviderAdapter._do_test_get` — HTTP 200 返回 success=True + model_count；HTTP 非 200 返回 success=False；LlmApiException 捕获返回 success=False
- [ ] `ProviderAdapter._do_test_post` — HTTP 200 返回 success=True；HTTP 非 200 走 _extract_error_message；LlmApiException 捕获返回 success=False

---

## 第 3 批：业务核心 — Agent + ContextManager（7 方法）

**特点：Mock DB Session + Redis，是之前踩坑最密集的区域（全量替换、级联软删、Redis 滑动窗口排序方向）。**

- [ ] `AgentService.update_agent` — 知识库正常替换：旧软删→新写入；中间步骤异常后数据状态
- [ ] `AgentService.delete_agent` — 三表级联软删全部执行；Agent 不存在抛 AGENT_NOT_FOUND
- [ ] `AgentService.bind_tools` — 正常全量替换：旧绑定软删+新绑定插入；部分 tool_id 不存在抛异常且不执行替换；server 禁用时抛 PARAM_ERROR
- [ ] `AgentService.bind_knowledge_base` — 首次绑定插入；已软删记录恢复 deleted=0 而非插入重复；重复绑定幂等返回 True
- [ ] `AgentService.bind_tool` — 工具不存在抛异常；已软删恢复而非新增；幂等返回

### ContextManager（2）

- [ ] `ContextManager.get_history` — Redis 命中直接返回；Redis 未命中从 MySQL 加载并回写 Redis；**验证 ORDER BY created_at ASC 取的是最近消息，不是最早消息**
- [ ] `ContextManager.add_message` — 插入后 Redis list 长度不超过 max_turns*2；pipeline 包含 RPUSH+LTRIM+EXPIRE 三个命令

---

## 第 4 批：业务核心 — ChatService + WorkflowEngine + 其他（8 方法）

**特点：核心链路最复杂分支，组合前面所有 mock 模式。ChatService.send_message 的 5 个分支必须分开 commit。**

- [ ] `ChatService.send_message`（纯流式，无工具无 RAG） — 正常流式 delta 逐条推送 + done 含 latencyMs/conversationId；LLM 流式中途异常推送 error 事件 + 存 error 消息；首条消息自动更新会话标题
- [ ] `ChatService.send_message`（工具调用 finish_reason=tool_calls） — 正常链路：第一次返回 tool_calls→工具执行→第二次流式返回；工具执行失败不中断链路，错误信息拼入 tool result；第一次 LLM 调用异常存 error 并中断
- [ ] `ChatService.send_message`（RAG 增强分支） — 绑定知识库时 system prompt 包含参考资料；某知识库检索异常跳过继续；所有知识库无结果时不注入 RAG 前缀
- [ ] `ChatService.send_message`（工作流分支） — workflow 正常执行→推送 delta+done+存储消息；workflow 异常时的错误 SSE 事件
- [ ] `ChatService.send_message`（conversation_id 为 None 自动创建会话） — 自动创建会话成功；首条消息用内容更新标题
- [ ] `ChatService.delete_conversation` — 会话+关联消息全部软删；会话不存在抛异常
- [ ] `WorkflowEngine.execute` — START→LLM→END 正常流程 WorkflowRun 标记 SUCCESS；节点失败标记 FAILED+error_message；max_steps 上限抛异常
- [ ] `McpServerService.delete_server` — 有 Agent 绑定时抛 MCP_SERVER_IN_USE；无绑定正常软删
- [ ] `DocumentService.upload_document` — 不支持的类型抛异常；超大文件抛异常；正常文件创建 pending 记录

---

## 进度统计

| 批次 | 方法数 | 已完成 | 进度 |
|------|--------|--------|------|
| 第 1 批 | 14 | 14 | 100% |
| 第 2 批 | 4 | 0 | 0% |
| 第 3 批 | 7 | 0 | 0% |
| 第 4 批 | 9 | 0 | 0% |
| **合计** | **34** | **14** | **41%** |

---

## 集成测试计划（后续补充）

以下方法跳过单测，在集成测试阶段用真实 MySQL/Redis/Qdrant/LLM API 覆盖：

| 模块 | 方法 | 理由 |
|------|------|------|
| 所有 Router 层 | 全部 | FastAPI TestClient 集成测试 |
| ProviderService / ModelService | 全部 CRUD | 索引命中、软删级联、ORM 映射需真实 DB |
| KnowledgeBaseService | 全部 CRUD | 同上 |
| DocumentPipeline | `run` | 文件 I/O + Embedding API + Qdrant |
| DocumentChunkService | `search_chunks` | Embedding API + Qdrant 向量检索 |
| McpServerService | `test_connection` | JSON-RPC 真实调用 |
| McpToolService | `call_tool` | JSON-RPC 真实调用 |
| ProviderAdapter 子类 | `test_connection` / `stream_chat` / `chat_complete` | 真实 LLM API 连通性 |
| LlmClient | `embed` | Embedding API 真实返回维度和格式 |