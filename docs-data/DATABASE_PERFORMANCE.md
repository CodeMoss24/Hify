# Hify 数据库性能规范

## 一、通用字段约定

**每张表必须有四个公共字段：**

```sql
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记：0-正常，1-删除'
```

### 几条硬规矩

| 规矩 | 说明 | 示例 |
|------|------|------|
| **主键用 BIGINT 自增，禁止 UUID** | UUID 索引性能差，BIGINT 更小更快 | `id BIGINT AUTO_INCREMENT PRIMARY KEY` |
| **禁止 NULL** | 业务空值用空字符串或 0 | `name VARCHAR(100) NOT NULL DEFAULT ''` |
| **金额/Token 用 BIGINT** | 不用 DECIMAL，最小精度存储 | `amount BIGINT NOT NULL DEFAULT 0` |
| **枚举字段用 VARCHAR(32)** | 不用 MySQL ENUM（加值要改表结构） | `status VARCHAR(32) NOT NULL DEFAULT 'pending'` |

**说明：**
- `DATETIME(3)` 毫秒精度，满足日志记录需求
- `updated_at` 不加的场景：创建后不可修改的表（如 message）
- `deleted` 不加的场景：日志类表，按时间范围查询即可

---

## 二、表命名规范

```sql
-- 格式：tb_{功能域}_{实体名}
-- 示例：
tb_model_provider        -- 模型提供商
tb_model                  -- 模型配置
tb_agent                  -- Agent
tb_agent_knowledge_base   -- Agent-知识库关联（多对多）
tb_agent_tool             -- Agent-工具关联（多对多）
tb_mcp_server             -- MCP服务器
tb_mcp_tool               -- MCP工具
tb_knowledge_base         -- 知识库
tb_document               -- 文档
tb_document_chunk         -- 文档块
tb_conversation            -- 对话会话
tb_message                -- 消息
tb_message_reference      -- RAG溯源关联
tb_workflow               -- 工作流
tb_workflow_node          -- 工作流节点
tb_workflow_edge          -- 工作流边
tb_user                   -- 用户
tb_api_key                -- API密钥
```

---

## 三、索引设计原则

### 3.1 五条硬规矩

**规矩 1：逻辑删除字段必须加进索引**

几乎所有查询都带 `deleted = 0`，不加进索引等于索引白建。

```sql
-- ✅ 正确
INDEX idx_agent_user (user_id, deleted)

-- ❌ 不够（查的时候还是全表扫 deleted）
INDEX idx_agent_user (user_id)
```

**规矩 2：组合索引等值列在前，范围列在后**

```sql
-- ✅ 正确：等值列 conversation_id 在前，范围列 created_at 在后
INDEX idx_message_conv_time (conversation_id, created_at)

-- ❌ 错误：范围列在前，索引无法生效
INDEX idx_message_conv_time (created_at, conversation_id)
```

**规矩 3：多对多关联表两个方向都要索引**

agent_tool 表按 agent_id 查和按 tool_id 查都是高频操作，只建一个方向的索引，另一个方向就全表扫描。

```sql
-- agent_tool 表
PRIMARY KEY (agent_id, tool_id),                        -- 主键索引（正向）
INDEX idx_tool_agent (tool_id)                          -- 反向查询索引

-- agent_knowledge_base 表
PRIMARY KEY (agent_id, knowledge_base_id),              -- 主键索引（正向）
INDEX idx_kb_agent (knowledge_base_id)                  -- 反向查询索引
```

**规矩 4：唯一约束用 UNIQUE INDEX**

并发场景下代码校验有竞态问题，数据库约束才是最后防线。

```sql
-- ✅ 正确
UNIQUE INDEX uniq_api_key (api_key)

-- ❌ 错误：只在代码层校验，并发下会出问题
```

**规矩 5：禁止在大文本字段建索引**

content、prompt 这类 TEXT 字段不能建索引，需要全文搜索的场景后续引入 ES。

```sql
-- ❌ 禁止
INDEX idx_content (content)  -- TEXT 字段不能建索引

-- ✅ 正确：TEXT 字段不建索引，需要时用 ES
content TEXT NOT NULL
```

### 3.2 索引设计检查清单

建表前自检：
- [ ] 外键字段有索引吗？
- [ ] WHERE 常用字段有索引吗？
- [ ] 组合查询的字段是联合索引的最左前缀吗？
- [ ] 排序字段有对应的索引支持吗？
- [ ] deleted 字段加入索引了吗？（几乎所有查询都带 deleted=0）
- [ ] 多对多关联表两个方向都有索引吗？

---

## 四、大表预判和应对策略

### 4.1 预判哪些表会变大

| 表名 | 预计增速 | 预估行数（1年后） | 策略 |
|------|----------|-------------------|------|
| **tb_message** | 高（每次对话多条消息） | 500万+ | 分表/分区 |
| **tb_document_chunk** | 中（文档分块） | 100万+ | 定期归档 |
| **tb_conversation** | 中（按对话数） | 50万+ | 归档 + 清理 |
| **tb_message_reference** | 中（每个RAG回复有关联） | 50万+ | 定期归档 |
| **tb_api_key** | 低 | 几千 | 不需要特殊处理 |

### 4.2 增长最快两张表的具体应对

#### message 表
每次对话产生 2-N 条记录，50 人每天几百到上千条。

**应对：**
- 建好时间范围索引 `(conversation_id, created_at)`
- 预留按时间归档的能力
- 一期建好索引够用半年

#### document_chunk 表
知识库分块数据，100 篇文档可能产生 5000+ 行。

**应对：**
- 向量数据存 Qdrant（独立向量数据库）
- MySQL 只存元数据（chunk_id、document_id 等）
- 不在 MySQL 里存向量本身

### 4.3 其他表

其他表（provider、agent、workflow）都是配置数据，增长慢，不需要特别关注。

---

## 五、分页查询规范

### 5.1 禁止 OFFSET 深分页

OFFSET 在百万行时极慢，MySQL 先扫描前 N 行再返回。

```sql
-- ❌ 禁止 OFFSET 深分页
SELECT * FROM tb_message ORDER BY id DESC LIMIT 20 OFFSET 100000;

-- ✅ 用游标分页（基于 ID）
SELECT * FROM tb_message
WHERE conversation_id = ?
  AND id < #{lastId}
  AND deleted = 0
ORDER BY id DESC
LIMIT 20;

-- ✅ 用游标分页（基于时间）
SELECT * FROM tb_message
WHERE conversation_id = ?
  AND created_at < #{lastTime}
  AND deleted = 0
ORDER BY created_at DESC
LIMIT 20;
```

### 5.2 分页模式对比

| 模式 | 适用场景 | SQL 示例 |
|------|----------|----------|
| **OFFSET** | 小表（< 1万行）、跳页不频繁 | `LIMIT 20 OFFSET 100` |
| **ID 游标** | 通用场景（推荐） | `WHERE id < #{lastId}` |
| **时间游标** | 按时间排序的列表 | `WHERE created_at < #{lastTime}` |
| **绝对位置** | 管理后台必须用 OFFSET | 限制最大页数 |

### 5.3 管理后台 OFFSET 限制

必须用 OFFSET 的场景，限制最大页数。

```sql
-- 超过 10000 条直接提示缩小查询范围
IF (page - 1) * page_size > 10000:
    raise Exception("查询范围过大，请缩小查询条件")
```

### 5.4 COUNT 查询单独处理

列表页只在第一页返回 total，翻页不重复查。

```python
# ✅ 正确：第一页查 COUNT + 数据，后续只查数据
if page == 1:
    total = await db.execute(count_query)
else:
    total = None  # 翻页不重复查 COUNT

data = await db.execute(data_query)
return {"total": total, "data": data}
```

**为什么重要：** COUNT 查询对大表性能影响很大，翻页时重复查没有意义。

---

## 六、SQL 编写规范

### 6.1 禁止 SELECT *

```sql
-- ❌ 错误
SELECT * FROM tb_message WHERE id = 1;

-- ✅ 正确
SELECT id, conversation_id, role, content, created_at
FROM tb_message WHERE id = 1;
```

### 6.2 批量插入优先

```sql
-- ❌ 错误：循环单条插入
INSERT INTO tb_message (id, conversation_id, role, content) VALUES ('1', 'c1', 'user', 'hello');
INSERT INTO tb_message (id, conversation_id, role, content) VALUES ('2', 'c1', 'user', 'hi');

-- ✅ 正确：批量插入
INSERT INTO tb_message (id, conversation_id, role, content) VALUES
('1', 'c1', 'user', 'hello'),
('2', 'c1', 'user', 'hi'),
('3', 'c1', 'user', 'how are you');
```

### 6.3 控制事务范围

```sql
-- ❌ 错误：长事务
BEGIN;
SELECT * FROM tb_message WHERE conversation_id = 'xxx';  -- 锁住数据
-- 处理业务逻辑（耗时操作）
UPDATE tb_conversation SET updated_at = NOW() WHERE id = 'xxx';
COMMIT;

-- ✅ 正确：短事务
BEGIN;
UPDATE tb_conversation SET updated_at = NOW() WHERE id = 'xxx';
COMMIT;

-- 然后处理其他耗时操作（不加锁）
```

### 6.4 批量操作分批提交

```sql
BATCH_SIZE = 1000
for i in range(0, total_count, BATCH_SIZE):
    batch = records[i:i + BATCH_SIZE]
    insert batch
    COMMIT  -- 每批提交，不要等所有完成
```

---

## 七、DDL 建表模板

```sql
-- ============================================
-- Hify 数据库建表模板
-- ============================================

CREATE DATABASE IF NOT EXISTS hify DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hify;

-- ============================================
-- 表名：tb_{功能域}_{实体名}
-- 编码：utf8mb4
-- 存储引擎：InnoDB
-- 主键：BIGINT AUTO_INCREMENT（禁止 UUID）
-- 公共字段：id, created_at, updated_at, deleted
-- ============================================

CREATE TABLE tb_model_provider (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '提供商名称：OpenAI/Anthropic/Gemini/Ollama',
    provider_type VARCHAR(32) NOT NULL COMMENT '类型标识：openai/anthropic/gemini/ollama',
    base_url VARCHAR(500) NOT NULL COMMENT 'API base URL',
    api_key VARCHAR(500) NOT NULL COMMENT 'API Key（加密存储）',
    is_enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用：0-禁用，1-启用',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
    deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',

    UNIQUE INDEX uniq_provider_type (provider_type),
    INDEX idx_is_enabled (is_enabled),
    INDEX idx_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型提供商';

-- ============================================

CREATE TABLE tb_model (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    provider_id BIGINT NOT NULL COMMENT '关联 model_provider.id',
    model_id VARCHAR(100) NOT NULL COMMENT '模型标识：gpt-4/claude-3-opus/gemini-pro',
    model_name VARCHAR(200) NOT NULL COMMENT '模型显示名称',
    model_type VARCHAR(32) COMMENT '模型类型：chat/embedding/vision',
    config JSON COMMENT '模型配置：temperature/max_tokens/etc',
    is_enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
    deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',

    FOREIGN KEY (provider_id) REFERENCES tb_model_provider(id),
    INDEX idx_provider_deleted (provider_id, deleted),
    INDEX idx_model_type (model_type),
    INDEX idx_is_enabled (is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型配置';

-- ============================================
-- 其他表类似，遵循上述规范
-- ============================================
```

---

## 八、快速检查清单

### 新建表时
- [ ] 表名符合 `tb_{功能域}_{实体名}` 规范
- [ ] 主键用 BIGINT AUTO_INCREMENT（禁止 UUID）
- [ ] 四个公共字段：id, created_at, updated_at, deleted
- [ ] 禁止 NULL，空值用空字符串或 0
- [ ] 金额/Token 用 BIGINT，不用 DECIMAL
- [ ] 枚举字段用 VARCHAR(32)，不用 ENUM
- [ ] deleted 必须加入索引
- [ ] 外键字段有索引
- [ ] WHERE 常用字段有索引
- [ ] 组合查询是联合索引最左前缀
- [ ] 多对多关联表两个方向都有索引
- [ ] 唯一约束用 UNIQUE INDEX
- [ ] TEXT 字段不建索引
- [ ] 字符集用 utf8mb4
- [ ] 存储引擎用 InnoDB
- [ ] 加 COMMENT

### 写查询时
- [ ] 不使用 SELECT *，明确列出字段
- [ ] 大表分页用游标，不用 OFFSET
- [ ] OFFSET 深分页最大限制 10000
- [ ] 批量插入用批量 SQL
- [ ] 事务尽量短
- [ ] COUNT 查询只在首页返回，翻页不重复查

### 大表监控
- [ ] 监控 tb_message 行数 > 100 万？
- [ ] 监控 tb_document_chunk 行数 > 50 万？
- [ ] 监控 tb_conversation 行数 > 20 万？