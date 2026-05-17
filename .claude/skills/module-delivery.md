# Skill: 业务模块全流程交付
name: module-delivery
触发方式：当用户说"开发 XX 模块"、"实现 XX 功能"、"交付 XX" 时，按此流程推进。

# 模块交付 Skill

按步骤交付 Hify 平台的一个业务模块，从设计到前后端联调验收。每步有明确产出物和验证方式，关键决策点必须等用户确认后再继续。

---

## 流程

### Step 1：需求梳理与选型

**做什么：** 梳理模块功能边界、技术选型、依赖库、数据模型设计。

**产出物：** 模块设计方案（口头或文档），包含：
- 功能范围（做什么 / 不做什么）
- 技术选型及理由
- 依赖库清单（含排除项及原因）
- 数据模型关键字段设计（差异字段用 JSON 存、状态字段放哪、展示名 vs 调用 ID 是否分开）

**验证方式：** 向用户口头汇报方案，用户确认后进入下一步。

**⚠️ 等待用户确认：** 选型方案、数据模型设计

---

### Step 2：更新数据库 Schema

**做什么：** 根据确认的数据模型，更新 `db/schema.sql`。

**产出物：** `db/schema.sql` 中新增或修改的表定义

**注意事项：**
- 表名遵循 `tb_{module}_{entity}` 命名
- 主键 BIGINT 自增，禁止 UUID
- 禁止 NULL，空值用空字符串或 0
- 通用字段：`id`, `created_at`, `updated_at`, `deleted`
- 枚举用 VARCHAR(32)，不用 ENUM
- 不建数据库外键，应用层维护
- 索引命名 `idx_{表名}_{字段名}`，deleted 必须加入组合索引

**验证方式：** 先向用户总结变更内容（新增了哪些表、改了哪些字段），用户确认后再执行变更

**⚠️ 等待用户确认：** Schema 变更（先确认变更范围，再执行）

---

### Step 3：后端 — ORM 模型（models.py）

**做什么：** 编写 SQLAlchemy ORM 模型，对应数据库表。

**产出物：** `app/{module}/models.py`

**注意事项：**
- 模型类名 `{Entity}Model`
- 继承 `TimestampMixin` 和 `SoftDeleteMixin`（如适用）
- 新建 ORM 模型后**必须**在 `app/main.py` 里显式 import，否则 `create_all()` 发现不了表
- 查询用 `Model.find_all(session)`，禁止直接 `session.query(Model)`
- 逻辑删除调用 `model.soft_delete()`，不是 `session.delete()`

**验证方式：** 启动应用，检查日志确认表创建成功（`echo=True` 时可见 CREATE TABLE）

---

### Step 4：后端 — Pydantic DTO（schemas.py）

**做什么：** 编写请求/响应 Pydantic 模型。

**产出物：** `app/{module}/schemas.py`

**命名规则：**
- 请求模型：`{Entity}Create` / `{Entity}Update`
- 响应模型：`{Entity}Response`

**注意事项：**
- **`api_key` 等敏感字段绝不能出现在响应 DTO 中**，必须在 schemas 中显式排除
- **所有 ORM 对象返回前必须先转成 Pydantic DTO**，禁止将 ORM 对象直接暴露给序列化层
- `PageResult` 不能继承 `ApiResponse`，否则 JSON 结构会嵌套（`data: { code, message, data: {...} }`）。`PageResult` 应独立定义，顶层结构为 `{code, message, data: {list, total, page, page_size}}`

**验证方式：** 代码 review，确认无敏感字段泄漏、无 ORM 直接暴露

---

### Step 5：后端 — 服务接口（interfaces.py）

**做什么：** 定义服务抽象接口。

**产出物：** `app/{module}/interfaces.py`

**命名规则：** `I{Entity}Service`

**注意事项：**
- 跨模块调用必须通过 interfaces，不能直接 import 实现类
- import 清单严格遵守 CLAUDE.md 中的模块依赖层级

**验证方式：** 代码 review，确认依赖方向正确

---

### Step 6：后端 — 业务逻辑（service.py）

**做什么：** 实现接口，编写 CRUD + 业务逻辑。

**产出物：** `app/{module}/service.py`

**注意事项：**
- 依赖注入通过构造函数接收接口实例
- 遵守模块依赖层级，不能反向依赖
- 所有外部调用必须有超时设置
- 配置项外化到 `.env`，通过 `app/common/config.py` 读取

**验证方式：** 代码 review

---

### Step 7：后端 — API 路由（router.py）

**做什么：** 编写 RESTful 端点，参数校验，调用 service。

**产出物：** `app/{module}/router.py`

**注意事项：**
- 路径：`/api/v1/{resources}` RESTful 风格
- 统一响应 `ApiResponse`
- 分页：page 从 1 开始，page_size 默认 20 最大 100
- 空 list 返回 `[]`，空字符串返回 `""`，不存在返回 `null`
- router 只做参数校验和调用 service，不写业务逻辑

**验证方式：** curl 逐接口测试 CRUD 全流程

**⚠️ 等待用户确认：** 接口设计（如需非 CRUD 端点）

---

### Step 8：后端 curl 验收

**做什么：** 根据当前模块接口自动生成 curl 验证命令，用 curl 对每个端点做全流程验证。

**产出物：** 自动生成的 curl 验证命令集，验证通过记录

**验证方式：**
- 创建 → 查详情 → 列表 → 更新 → 删除，全流程走通
- 非标准端点（如测试连接、健康检查）单独验证
- 确认响应格式符合 `ApiResponse` 规范
- 确认无敏感字段泄漏

**⚠️ 等待用户确认：** 后端全流程通过后再进入前端对接

---

### Step 9：前端 — API 层

**做什么：** 创建 `hify-web/src/api/{module}.ts`，封装后端 API 调用。

**产出物：** `hify-web/src/api/{module}.ts`

**验证方式：** 代码 review

---

### Step 10：前端 — 页面对接

**做什么：** 将 View 组件的 mock 数据源替换为真实 API 调用，新增后端新增功能对应的前端交互。

**产出物：** 更新后的 Vue 组件

**验证方式：** 浏览器中操作，确认数据正确加载

---

### Step 11：完整验收

**做什么：** 前后端联调全流程验收。

**产出物：** 无代码产出，验收通过记录

**验证方式：**
- 浏览器中完成创建、编辑、删除全流程
- 特殊功能（如测试连接、健康状态查看）在 UI 中验证
- 确认无 console 报错、无接口异常

---

## 注意事项汇总

| # | 坑 | 说明 |
|---|---|---|
| 1 | PageResult 不能继承 ApiResponse | 否则 JSON 结构嵌套，`data` 里再套一层 `{code, message, data}` |
| 2 | api_key 绝不能出现在响应 DTO 中 | 敏感字段必须在 schemas 中显式排除 |
| 3 | ORM 对象必须先转 Pydantic DTO | 禁止将 ORM 对象直接暴露给序列化层，进入响应封装前必须全部转为 DTO |
| 4 | 连通性测试用 POST /chat/completions | 发最小请求（max_tokens=1），不能用 GET /models，国内厂商不支持该端点 |
| 5 | 健康状态放 Redis 不放 MySQL | 避免高频写锁竞争，Redis 适合频繁更新的状态数据 |
| 6 | 新 ORM 模型要在 main.py 显式 import | 否则 `create_all()` 发现不了表，不会自动建表 |
| 7 | 前端 Vite 代理路径和后端 router prefix 必须对齐 | 否则代理转发后路径不匹配，返回 404 |
