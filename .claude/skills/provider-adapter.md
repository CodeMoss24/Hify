> name: provider-adapter
> description: >
>   接入新 LLM 供应商的标准化流程。覆盖 API 分析、Adapter 实现、Factory 注册、端到端验证。
>   当用户说"接入新供应商"、"新增 XX 提供商支持"、"加一个 Adapter"、"支持 XX 模型"时，
>   按此流程推进。
> allowed-tools:
>   - Read
>   - Write
>   - Bash
>   - Glob
>   - Grep
> ---
> 
> # Provider Adapter 接入 Skill
> 
> 按步骤完成新 LLM 供应商的连通性测试适配器开发。每步有明确产出物和验证方式，关键决策点必须等用户确认后再继续。
> 
> ---
> 
> ## 流程
> 
> ### Step 1：分析供应商 API
> 
> **做什么：** 确认供应商的连通性测试方案——用哪个端点、什么请求方式、如何鉴权。
> 
> **产出物：** 供应商 API 分析结论，包含：
> - 连通性测试端点及 HTTP 方法
> - 认证方式（Bearer Token / x-api-key / 无认证 / 其他）
> - 请求体结构（如需 POST）
> - 错误响应格式
> 
> **注意事项：**
> - 国内厂商（火山引擎、DeepSeek、通义等）大多不支持 `GET /v1/models`，连通性测试必须用 `POST /chat/completions` 发最小请求（`max_tokens=1`）
> - Ollama 是例外，走原生 `GET /api/tags`
> - 如果供应商兼容 OpenAI 协议（如 DeepSeek、Moonshot），直接复用 `OpenAiAdapter`，不需要写新 Adapter
> 
> **⚠️ 等待用户确认：** 供应商 API 分析结论、是否需要新建 Adapter
> 
> ---
> 
> ### Step 2：实现 Adapter 类
> 
> **做什么：** 在 `app/provider/adapters/` 下新建 Adapter 类，继承 `ProviderAdapter`，实现 `test_connection` 方法。
> 
> **产出物：** `app/provider/adapters/{provider}_adapter.py`
> 
> **模板：**
> 
> ```python
> """{ProviderName} provider adapter"""
> from app.provider.adapter import ProviderAdapter
> from app.provider.models import ProviderModel
> from app.provider.schemas import ConnectionTestResult
> 
> _DEFAULT_TEST_MODEL = "..."
> 
> 
> class {ProviderName}Adapter(ProviderAdapter):
>     """处理 {provider_type} 类型"""
> 
>     async def test_connection(self, provider: ProviderModel) -> ConnectionTestResult:
>         base_url = provider.base_url.rstrip("/")
>         extra_config = provider.extra_config or {}
>         test_model = extra_config.get("test_model", _DEFAULT_TEST_MODEL)
> 
>         url = f"{base_url}/..."
>         headers = { ... }
>         body = { "model": test_model, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}] }
>         return await self._do_test_post(url, headers, body, timeout=10.0)
> ```
> 
> **注意事项：**
> - `test_connection` 方法里网络错误/超时必须返回 `success=False` 的 `ConnectionTestResult`，不能抛异常——基类 `_do_test_get` / `_do_test_post` 已处理，不要自己 try/except 后再 raise
> - 认证失败（401/403）也返回 `success=False`，不能抛异常——这是用户配置问题，不是系统错误
> - 优先使用基类的 `_do_test_post`（POST 方式）或 `_do_test_get`（GET 方式），不要自己直接调 `llm_client`
> - `extra_config` 中可预留 `test_model` 字段，让用户覆盖默认测试模型
> - `timeout` 建议 10s（管理请求，非对话流式）
> 
> **验证方式：** 代码 review，确认继承正确、方法签名匹配、异常不会逃逸
> 
> ---
> 
> ### Step 3：在 Factory 注册
> 
> **做什么：** 在 `ProviderAdapterFactory._registry` 中添加 provider_type → Adapter 实例的映射。
> 
> **产出物：** `app/provider/adapter_factory.py` 变更
> 
> **注意事项：**
> - `openai` 和 `openai_compatible` 共用同一个 `OpenAiAdapter` 实例，这是有意为之，不要拆成两个 Adapter 或注册两次
> - key 必须和数据库中 `tb_model_provider.provider_type` 的值一致
> - 注册的是实例（`XxxAdapter()`），不是类
> 
> **验证方式：** 确认 `get_adapter("new_type")` 能返回正确实例、不支持的类型抛 `BizException`
> 
> **⚠️ 等待用户确认：** provider_type 命名（需与前端、数据库对齐）
> 
> ---
> 
> ### Step 4：导出 Adapter
> 
> **做什么：** 在 `app/provider/adapters/__init__.py` 中添加新 Adapter 的 import。
> 
> **产出物：** `app/provider/adapters/__init__.py` 变更
> 
> **注意事项：**
> - 格式：`from app.provider.adapters.{provider}_adapter import {ProviderName}Adapter`
> - 按字母序排列，保持整洁
> 
> **验证方式：** `from app.provider.adapters import {ProviderName}Adapter` 不报错
> 
> ---
> 
> ### Step 5：端到端验证
> 
> **做什么：** 用真实 Provider 配置调用连通性测试接口，验证新 Adapter 工作正常。
> 
> **产出物：** 验证通过记录
> 
> **验证方式：**
> - 调用 `POST /api/v1/providers` 创建该类型的 Provider
> - 调用 `POST /api/v1/providers/{id}/test-connection` 验证连通性
> - 测试成功场景：正确配置 → `success=True`
> - 测试失败场景：错误 API Key → `success=False`，error_message 可读
> - 测试失败场景：错误 base_url → `success=False`，不抛异常
> - 确认响应格式符合 `ApiResponse` 规范
> 
> **⚠️ 等待用户确认：** 端到端验证通过
> 
> ---
> 
> ## 注意事项汇总
> 
> | # | 坑 | 说明 |
> |---|---|---|
> | 1 | 国内厂商不支持 GET /v1/models | 火山引擎、DeepSeek、通义等必须用 POST /chat/completions（max_tokens=1）测试连通性 |
> | 2 | Ollama 走原生 GET /api/tags | OllamaAdapter 是唯一用 GET 测试的 Adapter |
> | 3 | openai 和 openai_compatible 共用 Adapter | 在 Factory 里分别注册，但指向同一个 OpenAiAdapter 实例，不要写两个 Adapter |
> | 4 | test_connection 不能抛异常 | 网络/超时/认证失败都返回 success=False 的 ConnectionTestResult，基类已处理 |
> | 5 | 401/403 返回 success=False | 认证失败是用户配置问题，不是系统错误，不能抛异常 |
> | 6 | 新 Adapter 要在 adapters/__init__.py 导出 | 否则 Factory import 会失败 |
> | 7 | OpenAI 兼容协议复用 OpenAiAdapter | DeepSeek、Moonshot 等兼容 OpenAI 的供应商不需要新 Adapter，直接用 openai_compatible 类型 |
> ```

---