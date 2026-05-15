# ZDoc real-Ollama preview safe endpoint default real transport gap design

## 1. 阶段背景

ZDoc Step 23 已完成 fake transport deterministic bridge implementation。该阶段在 default-off、preview-only、no-write 前提下，为 `POST /local-llm/preview-safe` 接入到 `run_zdoc_ollama_preview` 的受控 bridge，并通过 fake transport / monkeypatch / dependency injection 覆盖 deterministic tests。

ZDoc Step 24 已完成 fake-stage review，明确 Step 23 只证明 fake transport deterministic bridge 可用，不代表真实 Ollama runtime `/api/generate` 端到端可用。

ZDoc Step 25 已完成 runtime smoke plan，提前指出当前 bridge 默认仍可能要求 injected transport；若 runtime 返回 `fake_transport_required`，必须记录为受控缺口，不得擅自修改代码或扩大测试范围。

ZDoc Step 26 已完成 runtime smoke report。Step 26 关键结论为 enabled 场景返回：

```text
status=failure
error_type=transport_failure
reason=fake_transport_required
calls_ollama=false
```

Step 26 同时确认：

- `GET http://127.0.0.1:11434/api/tags` 可达；
- 本地模型列表包含 `qwen3:0.6b`；
- disabled 场景稳定 disabled；
- adapter-off 场景仍为 fake-only；
- enabled 场景进入了 safe endpoint real-adapter bridge，但未进入默认真实 network transport；
- 未直接请求 Ollama `/api/generate`；
- 未请求 `/generate`、`/export_docx`、`/review/apply`；
- 未写 `output/job/export`。

因此，当前 safe endpoint 默认 real transport 尚未接入，真实 `/api/generate` 端到端仍未证明。

## 2. 当前事实链路分析

只读检查显示，当前 safe endpoint 入口位于：

```text
backend/app/routers/local_llm_preview_safe.py
```

当前 endpoint 允许的请求字段只有：

```text
context_summary
request_id
section_text
section_title
```

当前行为路径如下。

### 2.1 disabled 场景

当 `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` 未开启或为 false-like 时：

```text
POST /local-llm/preview-safe
-> local_llm_preview_safe_endpoint
-> _safe_endpoint_base_response
-> status=disabled
-> calls_ollama=false
```

该路径稳定 disabled，不调用 fake helper，不调用 real adapter，不调用 Ollama，并保持：

```text
preview_only=true
no_write=true
affects_generation=false
affects_export=false
```

### 2.2 adapter-off 场景

当 `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true` 且 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 未开启时：

```text
POST /local-llm/preview-safe
-> endpoint guard
-> _build_safe_helper_payload
-> run_zdoc_local_llm_preview_safe_service_entry
-> fake-only advisory response
```

Step 26 runtime smoke 证明该场景返回 fake-only `status=ok`，`calls_ollama=false`，未触发正式生成、导出或写盘。

### 2.3 enabled 场景

当双开关开启时：

```text
POST /local-llm/preview-safe
-> endpoint guard
-> _build_ollama_adapter_payload
-> _run_ollama_adapter_bridge
-> run_zdoc_ollama_preview
```

`_run_ollama_adapter_bridge` 当前调用：

```text
run_zdoc_ollama_preview(
    payload,
    tags_transport=SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT,
    generate_transport=SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT,
)
```

而 endpoint 模块中的默认值是：

```text
SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT=None
SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT=None
```

`run_zdoc_ollama_preview` 当前在 `tags_transport` 或 `generate_transport` 缺失时返回：

```text
status=failure
error_type=transport_failure
reason=fake_transport_required
calls_ollama=false
```

因此 runtime 下暴露的是 `fake_transport_required` 受控缺口，而不是未处理异常。

## 3. 缺口定义

本次要解决的 `default real transport gap` 具体定义如下：

- 不是 Ollama 不可达问题：Step 26 已确认 `GET /api/tags` HTTP 200；
- 不是本地模型不存在问题：Step 26 已确认 `qwen3:0.6b` 存在；
- 不是 payload 不兼容问题：Step 26 三个场景均使用当前 endpoint 允许字段，且 enabled 场景已进入 adapter bridge；
- 不是双开关未开启问题：Step 26 enabled 场景已设置 `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`、`ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true`、`ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b`；
- 而是 endpoint / adapter 在 runtime 默认路径下仍要求 injected transport，缺少默认 real transport wiring。

换言之，当前实现已经有 fake transport deterministic bridge，但还没有可审计、default-off、loopback-only、no-write 的默认真实 transport 构造与接线。

## 4. 可能缺口位置分析

### 4.1 `local_llm_preview_safe.py` endpoint 桥接层

当前现状：

- endpoint guard 已存在；
- request normalization 已存在；
- 双开关开启时会进入 `_run_ollama_adapter_bridge`；
- `_run_ollama_adapter_bridge` 只把两个模块级 transport 变量传给 adapter；
- 模块级 transport 默认值为 `None`；
- endpoint 层没有默认 real transport builder；
- endpoint 层没有在 injected transport 缺失时构造 loopback transport。

问题表现：

- enabled runtime 下会进入 real-adapter bridge；
- 但由于未注入 transport，adapter 返回 `fake_transport_required`；
- endpoint 会把该结果包装为 no-write controlled failure。

### 4.2 `ollama_preview.py` real preview adapter / transport builder 层

当前现状：

- `run_zdoc_ollama_preview` 支持 `tags_transport` 和 `generate_transport`；
- `select_zdoc_local_ollama_model` 要求 `tags_transport`；
- generate 阶段要求 `generate_transport`；
- 缺少任一 transport 时，`run_zdoc_ollama_preview` 返回 `fake_transport_required`；
- 文件中存在 legacy `run_ollama_preview` 相关的 `urllib.request.urlopen` 调用和 `ZDOC_OLLAMA_PREVIEW_BASE_URL`，但 safe endpoint bridge 当前未使用该 legacy path；
- `build_zdoc_ollama_preview_client` 也要求显式传入两个 transport。

问题表现：

- adapter 具备 model selection、generate payload、normalization 和 controlled failure 逻辑；
- 但 adapter 没有 default real transport fallback；
- 因此 runtime 默认路径不会真实触达 `/api/tags` 或 `/api/generate`。

### 4.3 real transport 默认构造逻辑

当前现状：

- 当前 safe endpoint bridge path 未发现默认 real transport builder；
- 当前 deterministic tests 通过 monkeypatch 注入 fake tags/generate transport；
- 当前 runtime 默认路径没有从 `urllib.request` 构造 loopback transport。

问题表现：

- fake transport tests 可以通过；
- runtime enabled 场景仍停在 `fake_transport_required`；
- `calls_ollama=false` 正确反映真实 transport 未触发。

### 4.4 dependency injection / transport fallback 逻辑

当前现状：

- dependency injection 是当前 deterministic tests 的核心边界；
- endpoint 层通过 `SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT` 和 `SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT` 注入；
- adapter 层通过函数参数注入；
- 缺少“显式 injected transport 优先，否则使用 default real transport builder”的 fallback 规则。

问题表现：

- injected fake transport 场景可验证成功、缺模型、空响应、thinking-only、transport exception；
- 无 injected transport 场景只能返回 `fake_transport_required`；
- `fake_transport_required` 目前是 runtime 默认路径，而不只是特殊注入缺失场景。

### 4.5 environment flags 与 default wiring 衔接

当前现状：

- endpoint 层检查 `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`；
- endpoint 层检查 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- adapter 层再次检查这两个开关；
- adapter 读取 `ZDOC_OLLAMA_PREVIEW_MODEL`；
- adapter 读取 `ZDOC_OLLAMA_PREVIEW_TIMEOUT`；
- adapter 读取 `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`；
- safe endpoint bridge 当前未使用可配置 base URL，固定目标仍应限制为 `http://127.0.0.1:11434`。

问题表现：

- flags 已能控制进入 adapter；
- 但 flags 开启并不等于 default real transport 已接线；
- 双开关与 default real transport builder 之间缺少明确的 runtime wiring。

## 5. 目标状态设计

后续目标链路应为：

```text
POST /local-llm/preview-safe
-> endpoint guard
-> request normalization
-> real preview adapter enabled
-> default real transport builder
-> GET /api/tags
-> POST /api/generate
-> normalize response
-> bounded preview-only advisory response
```

目标结果应满足：

- `status=ok` 或 controlled failure；
- `calls_ollama=true` 仅当真实 transport 已触发；
- 始终保持 `preview_only=true`；
- 始终保持 `no_write=true`；
- 始终保持 `affects_generation=false`；
- 始终保持 `affects_export=false`；
- 不生成正式正文；
- 不写正式输出；
- 不触发正式生成、导出或 ZBid 写回。

建议目标状态还应明确区分：

```text
fake-only: calls_ollama=false, fake_only=true, real_adapter_bridge=false
real transport success: calls_ollama=true, fake_only=false, real_adapter_bridge=true, real_transport_enabled=true
real transport controlled failure: calls_ollama=true if /api/tags or /api/generate was touched, no_write=true
builder failure before transport touch: calls_ollama=false, controlled failure
special injected-transport missing: fake_transport_required, controlled failure
```

## 6. 设计约束

后续 real transport 接入时必须保持：

- default-off；
- preview-only；
- no-write；
- 不触发 `/generate`；
- 不触发 `/export_docx`；
- 不触发 `/review/apply`；
- 不写 `output/job/export`；
- 不修改正式正文；
- 不接 ZBid 正式写回；
- 不自动下载或拉取模型；
- 不访问外部 API；
- 不监听 `0.0.0.0`；
- 不绕过双开关；
- 不删除 fake-only 路径；
- 不把 preview advisory 写入正式章节。

允许的真实 transport 目标只能是本地 loopback：

```text
http://127.0.0.1:11434/api/tags
http://127.0.0.1:11434/api/generate
```

模型不存在时必须 controlled failure，不得执行 `ollama pull`，不得下载模型，不得自动更新模型。

## 7. 需要增加/调整的实现点设计

本节仅列出后续实现设计，不在本步修改代码。

### 7.1 endpoint 层 enabled 场景调用 real adapter

保留当前 endpoint guard、字段白名单和 formal field 拒绝逻辑。

双开关开启后，endpoint 仍应进入 `_run_ollama_adapter_bridge`。该函数可以继续作为 bridge 边界，但需要明确：

- injected transport 优先；
- 未注入时尝试使用 default real transport builder；
- builder 只允许构造 loopback `/api/tags` 与 `/api/generate` transport；
- builder failure 必须转换为 controlled failure；
- endpoint 不得直接请求正式 `/generate`、`/export_docx`、`/review/apply`。

### 7.2 real transport builder 默认 loopback transport

后续可在 `ollama_preview.py` 中增加 default real transport builder，或在 endpoint 层引入 adapter 暴露的 builder。

设计要求：

- 使用标准库 HTTP client 即可，不新增依赖；
- 只允许 `http://127.0.0.1:11434`；
- 拒绝非 loopback base URL；
- 对 tags 使用 GET 或受控 transport 语义读取 `/api/tags`；
- 对 generate 使用 POST 到 `/api/generate`；
- 强制 `stream=false`；
- 使用 `ZDOC_OLLAMA_PREVIEW_TIMEOUT` 的受控超时；
- 使用 `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT` 的受控输出上限；
- 返回 dict，不返回原始响应对象；
- 网络异常、JSON 解析异常、timeout 均转为 controlled failure。

### 7.3 injected transport 缺失时的 fallback

当前 `fake_transport_required` 是默认 runtime 结果。后续设计应将其收缩为特殊场景，例如：

- deterministic tests 显式要求 fake-only transport 且禁用 default builder；
- default builder 被配置为不可用；
- builder 缺失或被 monkeypatch 为 `None`；
- 注入策略要求必须手动传 transport。

正常 runtime enabled 场景应优先：

```text
injected tags/generate transport if provided
else default real transport builder
else controlled failure
```

### 7.4 response 中准确设置 `calls_ollama`

建议规则：

- disabled：`calls_ollama=false`；
- adapter-off/fake-only：`calls_ollama=false`；
- builder 初始化失败且未触达 loopback：`calls_ollama=false`；
- tags transport 已发起或被调用：`calls_ollama=true`；
- generate transport 已发起或被调用：`calls_ollama=true`；
- model missing after `/api/tags`：`calls_ollama=true`；
- generate timeout / invalid response / empty response / thinking-only bounded response：`calls_ollama=true`。

`calls_ollama=true` 不等于成功写入正文；它只表示真实或 fake-substitute transport 边界已经触达。

### 7.5 failure controlled response

所有失败必须返回 controlled response，而不是未处理异常：

- builder failure；
- invalid base URL；
- `/api/tags` unreachable；
- `/api/tags` invalid JSON；
- model missing；
- `/api/generate` timeout；
- `/api/generate` invalid JSON；
- empty response；
- thinking-only response；
- unexpected transport exception。

所有 failure 均必须保留：

```text
preview_only=true
no_write=true
affects_generation=false
affects_export=false
```

### 7.6 路径状态区分

后续响应应明确区分：

- fake-only；
- real transport success；
- real transport failure；
- fake_transport_required。

建议通过字段组合区分：

```text
fake_only
real_adapter_bridge
fake_transport_only
real_transport_enabled
calls_ollama
source
error_type
reason
risk_notes
```

如果 default real transport 成功构造并触达 loopback，`real_transport_enabled` 应能反映真实 runtime transport 已启用。若仍使用 fake transport deterministic test 替身，则字段应避免误导为真实 runtime 已验证。

## 8. 需要增加/调整的 deterministic tests 设计

后续实现前必须补充或调整 deterministic tests。不得直接依赖真实 Ollama 做 deterministic tests。

### 8.1 enabled 无 injected transport 走 default builder

目标：验证双开关开启、endpoint 未设置 `SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT` / `SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT` 时，可以调用 default real transport builder。

测试方式：

- monkeypatch default builder；
- builder 返回 fake tags/generate transport；
- 禁止真实 `urllib.request.urlopen`；
- 断言 endpoint 进入 builder；
- 断言响应不再是默认 `fake_transport_required`。

### 8.2 default builder 返回 fake tags/generate transport

目标：验证 default builder 的 fake substitute 返回 tags/generate transport 后：

```text
status=ok
calls_ollama=true
preview_only=true
no_write=true
affects_generation=false
affects_export=false
```

同时断言：

- tags URL 为 `http://127.0.0.1:11434/api/tags`；
- generate URL 为 `http://127.0.0.1:11434/api/generate`；
- 不请求 `/generate`；
- 不请求 `/export_docx`；
- 不请求 `/review/apply`；
- 不写 `output/job/export`。

### 8.3 default builder 初始化失败

目标：builder 无法构造 transport 时返回 controlled failure。

期望：

```text
status=failure
error_type=transport_failure 或 builder_failure
calls_ollama=false
no_write=true
```

不得抛未处理异常，不得触发正式链路。

### 8.4 transport builder 异常

目标：builder 抛异常时 endpoint 或 adapter 捕获并返回 controlled failure。

期望：

- `status=failure`；
- `error_type` 或 `reason` 能指向 builder exception；
- `preview_only=true`；
- `no_write=true`；
- no-route/no-write 字段全部保持 false。

### 8.5 `fake_transport_required` 收缩为特殊场景

目标：`fake_transport_required` 不再作为正常 runtime 默认路径要求，而只在显式禁用 default builder 或特殊注入缺失场景出现。

测试应覆盖：

- default builder 可用时不返回 `fake_transport_required`；
- default builder 被显式禁用时返回 `fake_transport_required` 或新的 controlled reason；
- 该结果仍 no-write。

### 8.6 disabled / adapter-off 旧行为不回归

必须继续证明：

- 总开关关闭：disabled，不调用 builder，不调用 adapter，不调用 Ollama；
- adapter 开关关闭：fake-only 或 controlled disabled，`calls_ollama=false`，不调用 builder，不调用 Ollama；
- 所有响应仍保持 no-write / preview-only。

### 8.7 no-write / negative-call tests

必须继续保留或增强：

- 不调用 `/generate`；
- 不调用 `/export_docx`；
- 不调用 `/review/apply`；
- 不写 `output/`；
- 不写 `job/`；
- 不写 `export/`；
- 不修改正式章节内容；
- 不接 ZBid 正式写回。

如测试使用 count-based proof，应继续记录 `output`、`job`、`export`、`backend/data/autoplan/jobs` 和 `build` 文件计数不变。

## 9. 运行时重新验证前提

后续若完成 real transport default wiring 实现，重新做 runtime smoke 前必须满足：

1. 先完成 docs-only 设计；
2. 再完成 guard + deterministic tests 实现；
3. 再运行授权 pytest；
4. 再单独做 runtime smoke；
5. 不得跳步直接去改生产链。

建议顺序：

```text
Step 28: default real transport guard + deterministic tests design
Step 29: default real transport fake-only implementation + deterministic tests
Step 30: runtime smoke plan update if needed
Step 31: real runtime smoke
```

任何 runtime smoke 前都必须重新核验：

- 当前工作区 clean；
- HEAD 与对应标签一致；
- `qwen3:0.6b` 已存在；
- 不下载或拉取模型；
- FastAPI 只监听 `127.0.0.1` 临时端口；
- 只请求 `/local-llm/preview-safe`；
- 不请求正式生成、导出或写回路径。

## 10. 风险与回滚

风险 1：default real transport 接入后误触生成链。

控制要求：

- default real transport 只能触发 local Ollama `/api/tags` 和 `/api/generate`；
- 不得触发应用正式 `/generate` route；
- negative-call tests 必须覆盖正式生成链。

风险 2：误写 `output/job/export`。

控制要求：

- adapter 不持有 output/job/export path；
- endpoint 不传 formal output fields；
- tests 必须证明文件计数不变。

风险 3：真实模型输出不稳定。

控制要求：

- advisory 必须 bounded；
- empty response / invalid response / timeout 必须 controlled failure；
- 不得把模型输出写入正式正文。

风险 4：thinking-only 被误用。

控制要求：

- thinking-only 只能作为 bounded preview advisory；
- 不得保存完整 thinking；
- 不得作为正式章节内容。

风险 5：默认 transport builder 设计不当导致与 fake transport 测试结构冲突。

控制要求：

- injected fake transport 必须继续优先；
- default builder 必须可 monkeypatch；
- deterministic tests 不得依赖真实 Ollama；
- `fake_transport_required` 特殊场景必须保留可测。

回滚措施：

```text
关闭 ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

兜底措施：

- 保留 disabled / fake-only 路径；
- 不得删除既有 fake-only 行为；
- 出现异常时不得扩散到正式链路；
- 不得扩大到正式生成、导出或 ZBid 写回。

## 11. 当前阶段结论

Step 26 已证明当前 runtime 缺口是“default real transport 未接入”，不是“真实 Ollama 服务不可达”。

证据是 Step 26 中 `GET http://127.0.0.1:11434/api/tags` 返回 HTTP 200，且本地模型列表包含 `qwen3:0.6b`；但 `/local-llm/preview-safe` enabled 场景仍返回：

```text
status=failure
error_type=transport_failure
reason=fake_transport_required
calls_ollama=false
```

因此下一步应优先解决 wiring / builder / adapter 设计缺口，而不是盲目重复 runtime smoke。

## 12. 下一步建议

下一步建议为 ZDoc Step 28：real-Ollama preview safe endpoint default real transport guard + deterministic tests design，或等价的 docs-only 实现前设计步骤。

不得直接修改代码，不得直接进入正式生成链、导出链或 ZBid 写回。
