# Hify 代码组织规范

## 模块内部结构

每个模块（provider/agent/chat/...）内部必须包含以下文件：

```
app/{module}/
├── __init__.py           # 导出 router、service、schemas、interfaces
├── router.py             # API 路由（FastAPI router）
├── service.py            # 业务逻辑实现
├── interfaces.py         # 服务接口（抽象类，定义业务方法）
├── schemas.py            # Pydantic 模型（请求/响应 DTO）
└── models.py             # SQLAlchemy ORM 模型（数据库表）
```

**禁止在模块内部创建更多子目录**。所有模块都是单层 flat 结构。

---

## 各层职责

### router.py（接口层）

**职责：**
- 定义 `APIRouter`，挂载路由
- 接收 HTTP 请求，解析参数
- 调用 service 层，返回响应
- 处理 HTTP 层面的异常（401/403/404）

**严格禁止：**
- ❌ 禁止写业务逻辑
- ❌ 禁止直接操作数据库
- ❌ 禁止调用其他 module 的 service（必须通过 service 接口）
- ❌ 禁止在路由处理函数里写任何计算逻辑

```python
# 正确
@router.post("/agents")
def create_agent(agent: AgentCreate, service: IAgentService = Depends(get_agent_service)):
    return service.create_agent(agent)

# 错误：router 里写业务逻辑
@router.post("/agents")
def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    # 不要在这里写 SQL 或业务逻辑
```

---

### service.py（业务层）

**职责：**
- 业务逻辑实现
- 事务管理（commit/rollback）
- 实现 `interfaces.py` 中定义的接口
- 抛出业务异常（到 common/exceptions.py 定义）

**禁止：**
- ❌ 禁止直接写 SQL（要用 SQLAlchemy Query）
- ❌ 禁止处理 HTTP 请求/响应
- ❌ 禁止导入 router
- ❌ 禁止直接实例化其他 module 的 service（要用接口）

```python
# 正确：实现接口
class AgentService(IAgentService):
    def create_agent(self, data: AgentCreate) -> AgentResponse:
        agent = AgentModel(name=data.name, ...)
        self.db.add(agent)
        self.db.commit()
        return AgentResponse.model_validate(agent)

# 错误：在 service 里写原始 SQL
```

---

### interfaces.py（服务接口层）⭐ 跨模块调用必须通过这里

**职责：**
- 定义该模块对外暴露的业务方法（抽象类）
- 所有跨模块调用必须通过接口，不能直接引用实现类
- 为未来拆分微服务预留远程调用改造空间

**为什么需要：**
模块化单体后续要拆分微服务时，如果直接 import 实现类，所有调用点都要改成 HTTP 调用。但如果通过接口调用，拆分时只需把依赖注入从本地实现换成远程代理，调用方代码不用动。

```python
# app/agent/interfaces.py
from abc import ABC, abstractmethod

class IAgentService(ABC):
    """Agent 模块对外暴露的服务接口"""

    @abstractmethod
    def get_agent(self, agent_id: str) -> AgentResponse:
        """获取 Agent 信息"""
        pass

    @abstractmethod
    def create_agent(self, data: AgentCreate) -> AgentResponse:
        """创建 Agent"""
        pass

    @abstractmethod
    def bind_tools(self, agent_id: str, tool_ids: list[str]) -> None:
        """绑定工具"""
        pass

    @abstractmethod
    def bind_knowledge(self, agent_id: str, kb_id: str) -> None:
        """绑定知识库"""
        pass
```

```python
# app/agent/service.py
class AgentService(IAgentService):
    """Agent 服务实现"""
    ...
```

```python
# app/chat/service.py（跨模块调用）
from app.agent.interfaces import IAgentService
from app.provider.interfaces import IProviderService

class ChatService:
    """Chat 服务，通过接口调用其他模块"""

    def __init__(self, agent_service: IAgentService, provider_service: IProviderService):
        self._agent_service = agent_service   # 只知道接口，不知道实现
        self._provider_service = provider_service

    async def chat(self, request):
        agent = self._agent_service.get_agent(request.agent_id)  # 通过接口调用
        provider = self._provider_service.get_provider(agent.provider_id)
```

**规则：**
- 每个业务模块必须有一个 `interfaces.py`
- 对外暴露的服务必须继承对应接口
- 跨模块调用方持有的是接口类型，不是实现类型

---

### schemas.py（数据模型层 / DTO）

**职责：**
- Pydantic BaseModel 定义请求体（xxxCreate, xxxUpdate）
- Pydantic BaseModel 定义响应体（xxxResponse）
- 与 router 配合做参数验证
- **控制字段暴露**，防止 Entity 中的敏感字段（如 API Key）泄露到前端

**规则：**
- 请求模型以 `Create`/`Update` 结尾
- 响应模型以 `Response` 结尾
- 用 `Field` 控制字段暴露，不暴露的字段直接省略
- 嵌套模型要注意层级，防止内部敏感字段外泄

```python
class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    api_key: str  # 内部字段，不返回给前端

class ProviderResponse(BaseModel):
    id: UUID
    name: str
    # 注意：api_key 故意不写，不会暴露给前端
    # Entity 里的敏感字段不能直接返回
    class Config:
        from_attributes = True
```

**⚠️ 安全要求：**
`Entity`（models.py 中的 SQLAlchemy 模型）可能有敏感字段（API Key、密钥等），**不能直接把 Entity 返回给前端**。必须通过 schemas.py 转换，控制暴露哪些字段。

---

### models.py（持久化层）

**职责：**
- SQLAlchemy ORM 模型定义（对应数据库表）
- 与数据库表一一对应

**规则：**
- 表名统一使用 `tb_{module}_{entity}` 格式
- 所有模型继承 `Base`（from app.common.database import Base）
- 不在这里定义业务逻辑

```python
from app.common.database import Base
from sqlalchemy import Column, String, UUID

class ProviderModel(Base):
    __tablename__ = "tb_provider"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(100), nullable=False)
    api_key = Column(String(500), nullable=False)  # 敏感字段，存但不返回前端
```

---

## 跨模块调用规则

### 依赖方向（单向）

```
router → service → interfaces → (service of other modules)
```

**允许：** chat 的 service 可以调用 agent 的 service
**禁止：** agent 的 service 不能调用 chat 的 service

### 调用链路（必须遵守）

```
调用方 service
    ↓ 依赖接口（interfaces.py）
被调用方 service 实现（service.py）
```

**正确：**
```python
# app/chat/service.py
from app.agent.interfaces import IAgentService

class ChatService:
    def __init__(self, agent_service: IAgentService):  # ✅ 通过接口
        self._agent = agent_service
```

**错误：**
```python
# app/chat/service.py
from app.agent.service import AgentService  # ❌ 直接引用实现类

class ChatService:
    def __init__(self):
        self._agent = AgentService(db)  # ❌ 直接实例化实现
```

### 具体规则

| 调用方 | 被调用方 | 允许？ | 调用方式 |
|--------|----------|--------|----------|
| chat.service | agent.service | ✅ | 通过 IAgentService 接口 |
| agent.service | chat.service | ❌ | — |
| chat.service | workflow.service | ✅ | 通过 IWorkflowService 接口 |
| workflow.service | chat.service | ❌ | — |
| agent.service | provider.service | ✅ | 通过 IProviderService 接口 |
| provider.service | agent.service | ❌ | — |
| chat.service | mcp.service | ✅ | 通过 IMcpService 接口 |
| mcp.service | chat.service | ❌ | — |
| agent.service | mcp.service | ✅ | 通过 IMcpService 接口 |
| agent.service | knowledge.service | ✅ | 通过 IKnowledgeService 接口 |
| workflow.service | mcp.service | ✅ | 通过 IMcpService 接口 |
| workflow.service | knowledge.service | ✅ | 通过 IKnowledgeService 接口 |

### common 模块规则

`common/` 模块（config/exceptions/utils）被所有模块依赖，但它们之间**不能有循环依赖**。

`common/` 只能定义纯粹的配置、常量、异常、工具函数，不能引入任何业务模块。

---

## 事务边界

- **事务在 service 层开启和提交**
- router 不能开启事务
- 跨模块调用时，事务由调用方管理

```python
# 正确：service 管理事务
class AgentService(IAgentService):
    def create_agent(self, data):
        agent = AgentModel(...)
        self.db.add(agent)
        self.db.commit()  # service 提交事务

# 错误：router 管理事务
@router.post("/agents")
def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    db.add(AgentModel(...))
    db.commit()  # router 不应该管理事务
```

---

## 异常处理

业务异常定义在 `app/common/exceptions.py`：

```python
class BusinessException(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

class AgentNotFoundException(BusinessException):
    def __init__(self, agent_id: str):
        super().__init__("AGENT_NOT_FOUND", f"Agent {agent_id} not found")
```

service 层抛出异常，router 层捕获：

```python
# service
def get_agent(self, agent_id):
    agent = self.db.query(AgentModel).get(agent_id)
    if not agent:
        raise AgentNotFoundException(agent_id)

# router
@router.get("/agents/{agent_id}")
def get_agent(agent_id: UUID, service: IAgentService = Depends(get_agent_service)):
    try:
        return service.get_agent(str(agent_id))
    except AgentNotFoundException as e:
        raise HTTPException(404, e.message)
```

---

## 文件命名强制规则

| 文件 | 命名规则 | 示例 |
|------|----------|------|
| Pydantic 请求 | `{Entity}Create` / `{Entity}Update` | `AgentCreate`, `ProviderUpdate` |
| Pydantic 响应 | `{Entity}Response` | `AgentResponse`, `ProviderResponse` |
| SQLAlchemy 模型 | `{Entity}Model` | `AgentModel`, `ProviderModel` |
| Service 接口 | `I{Entity}Service` | `IAgentService`, `IProviderService` |
| Service 实现 | `{Entity}Service` | `AgentService`, `ProviderService` |
| Router | `router`（单数） | `router = APIRouter()` |
| 数据库表 | `tb_{module}_{entity}` | `tb_agent`, `tb_provider` |

---

## 目录结构总结

```
hify/
├── app/
│   ├── main.py                    # FastAPI 应用入口
│   ├── common/                    # 公共模块
│   │   ├── config.py              # Settings 配置
│   │   ├── database.py            # SQLAlchemy Base, get_db
│   │   ├── exceptions.py          # 业务异常定义
│   │   └── utils.py               # 工具函数
│   │
│   ├── provider/                   # 模型提供商
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── interfaces.py           # 服务接口（IProviderService）
│   │   ├── service.py             # 服务实现（ProviderService）
│   │   ├── schemas.py
│   │   └── models.py
│   │
│   ├── agent/                      # Agent 管理
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── interfaces.py           # 服务接口（IAgentService）
│   │   ├── service.py
│   │   ├── schemas.py
│   │   └── models.py
│   │
│   ├── chat/                       # 对话引擎
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── interfaces.py           # 服务接口（IChatService）
│   │   ├── service.py
│   │   ├── session.py             # Redis 会话管理
│   │   ├── schemas.py
│   │   └── models.py
│   │
│   ├── knowledge/                  # 知识库 RAG
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── interfaces.py
│   │   ├── service.py
│   │   ├── chunker.py             # 文档分块
│   │   ├── schemas.py
│   │   └── models.py
│   │
│   ├── workflow/                   # 工作流编排
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── interfaces.py
│   │   ├── executor.py            # 流程执行器
│   │   ├── service.py
│   │   ├── schemas.py
│   │   └── models.py
│   │
│   └── mcp/                        # MCP 工具
│       ├── __init__.py
│       ├── router.py
│       ├── interfaces.py
│       ├── service.py
│       ├── schemas.py
│       └── models.py
│
├── tests/                          # 测试
├── hify-web/                       # 前端
├── deploy/                         # Docker
└── requirements.txt
```

---

## 违反规范的检查清单

开发时自检：
- [ ] router 里没有业务逻辑（SQL/业务计算/直接实例化）
- [ ] service 里没有处理 HTTP 请求
- [ ] 跨模块调用只通过 interfaces，不直接 import 实现类
- [ ] 跨模块调用是单向的（从高层调用低层，不能反过来）
- [ ] 事务在 service 层管理
- [ ] 异常抛到 router 层捕获
- [ ] 文件命名符合规范
- [ ] common/ 不依赖任何业务模块
- [ ] schemas.py 承担 DTO 角色，防止 Entity 敏感字段暴露
- [ ] 每个模块有 interfaces.py 定义对外暴露的服务接口