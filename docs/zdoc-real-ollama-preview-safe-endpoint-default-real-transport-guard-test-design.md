# ZDoc real-Ollama preview safe endpoint default real transport guard + deterministic tests design

## 1. 阶段背景

Step 26 runtime smoke 已证明当前 `/local-llm/preview-safe` 在双开关 enabled 场景下没有完成真实 Ollama generate 端到端接通。该场景返回：

- `status=failure`
- `error_type=transport_failure`
- `reason=fake_transport_required`
- `calls_ollama=false`

Step 27 已归档 default real transport gap design，结论是当前缺口不是 Ollama loopback 不可达，也不是本地模型不存在，也不是 smoke payload 与 endpoint 不兼容，而是 runtime 默认路径缺少 real transport wiring。

Step 28 的目标是锁定后续实现前的 guard、deterministic tests、允许修改文件、失败响应和回滚边界。本步仅归档设计，不实现 default real transport，不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`。

## 2. 当前缺口复述

基于 Step 26 smoke report、Step 27 gap design 以及当前代码只读检查，当前事实如下：

- disabled 场景：`ZDOC_LOCAL_LLM_PREVIEW_ENABLED` 未开启时，endpoint 返回 stable disabled，`calls_ollama=false`，不会进入 adapter。
- adapter-off 场景：`ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true` 且 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 未开启时，endpoint 走 fake-only 或 controlled non-real path，`calls_ollama=false`。
- enabled 场景：双开关均开启后，endpoint 会进入需要 transport 的 adapter bridge path，但 runtime 默认 real transport 未注入。
- runtime 结果为 `status=failure`、`error_type=transport_failure`、`reason=fake_transport_required`、`calls_ollama=false`。
- 因此真实 Ollama `/api/generate` 端到端仍未证明，当前 `/local-llm/preview-safe` 的 enabled smoke 不能被解释为 real-Ollama generate 已接通。

该缺口应被视为受控 wiring 缺口，而不是模型运行质量问题。

## 3. 后续目标链路

后续实现完成后的目标链路为：

```text
POST /local-llm/preview-safe
-> endpoint guard
-> request normalization
-> run_zdoc_ollama_preview
-> default real transport builder
-> GET /api/tags
-> POST /api/generate
-> normalize_zdoc_ollama_response
-> bounded preview-only advisory response
```

目标状态必须持续满足：

- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- 不触发 `/generate`
- 不触发 `/export_docx`
- 不触发 `/review/apply`
- 不写 `output/job/export`
- 不接 ZBid 写回
- 不修改正式章节内容
- 不影响正式文档生成结果

后续实现即便进入真实 Ollama path，也只能产生 preview advisory，不得将 advisory 写入正式方案。

## 4. default real transport guard 设计

后续实现 default real transport wiring 时必须具备以下 guard：

- 总开关 `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true` 未开启时，不得构造 real transport。
- adapter 开关 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true` 未开启时，不得构造 real transport。
- 只有双开关均开启且 endpoint payload 合法时，才允许构造 default real transport。
- default real transport 只能指向 loopback，例如 `http://127.0.0.1:11434`，或当前代码中已有的 loopback 默认值。
- 不得访问外网，不得读取远端模型服务，不得引入非 loopback host。
- 不得下载、拉取、更新或安装模型。
- 模型不存在时必须返回 controlled failure，不得隐式执行 pull。
- timeout 必须有保守默认值，并允许通过既有环境变量设置上限内的短超时。
- `num_predict` 必须有保守默认值，并限制为低 token 输出，避免长文本和不可控响应。
- transport 初始化异常、tags 异常、generate 异常均必须转为 controlled failure。
- response 中 `calls_ollama` 必须准确反映是否进入 real transport 边界。
- transport failure 不得作为未处理异常穿透到 endpoint，更不得穿透到正式生成链。

`calls_ollama` 的建议语义：

- 未构造 transport：`calls_ollama=false`
- 构造失败且未触达 transport：`calls_ollama=false`
- 已触达 tags 或 generate transport：`calls_ollama=true`
- generate 失败但已进入 transport：`calls_ollama=true`

## 5. endpoint 层设计

`backend/app/routers/local_llm_preview_safe.py` 后续可能需要调整以下设计点：

- 双开关开启后，明确选择 real adapter path，而不是仍要求预先注入 fake transport。
- 将 endpoint payload 归一化为 adapter 可接受的 runtime-safe 参数。
- 保持既有 disabled 行为不回归：总开关未开启时应在 endpoint 层稳定返回 disabled，并且不调用 helper、adapter 或 builder。
- 保持 adapter-off 行为不回归：adapter 开关未开启时继续走既有 fake-only 或 controlled non-real path，并且不构造 real transport。
- response 中继续稳定保留 `calls_ollama`、`source`、`model`、`error_type` 或 `failure_reason`。
- endpoint 不得调用正式生成链、正式导出链或 review apply 链。
- payload 缺少可选字段时应使用安全默认值，保证 preview-only 响应可控。
- payload 非法时应返回 422 或 controlled failure，不得写盘，不得继续进入 real transport。
- formal output 字段、导出路径字段、job/output/export 相关字段必须继续被过滤或拒绝。

endpoint 层仍应作为第一道边界，确保任何 adapter 响应都会被补齐 no-write metadata，并移除不允许出现在 safe endpoint response 中的正式输出字段。

## 6. adapter / helper 层设计

`backend/zhifei_autoplan/ollama_preview.py` 后续可能需要调整以下设计点：

- `run_zdoc_ollama_preview` 在未注入 fake transport 时，应能在双开关开启场景下使用 default real transport builder。
- real transport builder 必须只构造 loopback transport，默认目标应限制在 `http://127.0.0.1:11434`。
- tags 检查必须先确认模型存在；如果 `ZDOC_OLLAMA_PREVIEW_MODEL` 指定模型不存在，应返回 controlled failure。
- 如未指定 `ZDOC_OLLAMA_PREVIEW_MODEL`，必须走受控模型选择逻辑，不得尝试下载或更新模型。
- generate 调用必须使用保守 timeout 与低 `num_predict`，并沿用当前 timeout / `num_predict` 上限策略。
- `normalize_zdoc_ollama_response` 应继续处理正常 response、空 response、thinking-only、malformed JSON、transport exception 等情况。
- thinking-only 不得保存完整 thinking，也不得被写入正式正文，只能产出 bounded preview 或 controlled failure。
- fake transport deterministic tests 的注入能力必须保留，且优先级应高于 default real transport builder。
- 新增 default real transport fallback 不得破坏既有 fake-only endpoint 行为。

建议后续设计中区分三类 transport 来源：

- injected fake transport：deterministic tests 使用，source 标明 fake/test path。
- default real transport：runtime 双开关开启且无 injected transport 时使用，source 标明 real/runtime path。
- transport unavailable：builder 不可用或明确测试注入缺失时使用 controlled failure。

## 7. response schema guard

后续 endpoint 响应结构必须稳定保留或兼容以下字段：

- `status`
- `ok`
- `enabled`
- `preview_only`
- `no_write`
- `affects_generation`
- `affects_export`
- `calls_ollama`
- `model`
- `source`
- `advisory`
- `suggestions`
- `warnings` 或 `risk_notes`
- `error_type` 或 `failure_reason`

响应语义应定义如下：

- disabled：`calls_ollama=false`，`preview_only=true`，`no_write=true`。
- adapter-off：`calls_ollama=false`，可保持 fake-only 或 controlled non-real path。
- fake transport success：`calls_ollama=true`，但 `source` 应明确标明 fake/test path。
- default real transport success：`calls_ollama=true`，`source` 应明确标明 real/runtime path。
- default real transport controlled failure：按是否实际触达 transport 设置 `calls_ollama`，但必须 `no_write=true`。
- exception：必须转为 controlled failure，不得返回未处理堆栈给用户。
- `fake_transport_required` 不得再作为双开关 runtime 默认路径的最终结果，除非处于明确的测试注入缺失场景。

所有 response 都必须保持：

- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`

## 8. deterministic tests 设计

后续实现时必须补充或调整 deterministic tests。本步不运行 pytest。

必须覆盖：

- 总开关关闭：不构造 real transport，不调用 default builder，不调用 helper，不调用 adapter，不调用 Ollama。
- adapter 开关关闭：不构造 real transport，不调用 default builder，不进入 real adapter。
- 双开关开启 + no injected transport：调用 default real transport builder 的 fake 替身。
- default builder 返回 fake tags + fake generate 成功：返回 `status=ok`、`calls_ollama=true`。
- default builder tags 缺模型：返回 controlled failure，不下载模型，不拉取模型。
- default builder 初始化异常：返回 controlled failure，`no_write=true`。
- default builder generate 异常：返回 controlled failure，`no_write=true`。
- fake generate 空 response：返回 controlled failure 或 bounded advisory，不写盘。
- fake generate thinking-only：生成 bounded preview，不保存完整 thinking，不写正式正文。
- payload 缺少可选字段：使用默认值，不写盘。
- payload 非法：返回 422 或 controlled failure，不写盘。
- disabled / adapter-off 既有行为不回归。
- 所有响应保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`。
- endpoint 不触发 `/generate`、`/export_docx`、`/review/apply`。
- 不写 `output/job/export`。

如测试需要证明不触发正式链路，应继续使用 monkeypatch、spy、fail-fast stub 或 filesystem count regression，而不是启动服务或运行真实 Ollama。

## 9. fake transport 与 real transport 共存设计

fake transport 仍应是 deterministic tests 的主路径。后续新增 default real transport 后，测试中不得真实访问 `127.0.0.1:11434`，不得依赖本机是否正在运行 Ollama。

共存原则：

- injected fake transport 优先，保证 deterministic tests 可控。
- default real transport 只在 runtime 双开关开启且无 injected transport 时进入。
- tests 中 default builder 必须通过 monkeypatch 或 dependency injection 替身实现。
- tests 不得直接访问真实 Ollama，不得运行 `ollama serve`，不得调用外网。
- 不得删除 fake-only 行为，不得删除 fake transport 注入能力。
- fake-only、fake transport success、default real transport success、default real transport failure 必须在 response `source` 或 `error_type` 中可区分。

## 10. 允许修改文件边界

后续 Step 29 实现阶段原则上只允许修改：

- `backend/app/routers/local_llm_preview_safe.py`
- `backend/zhifei_autoplan/ollama_preview.py`
- `backend/tests/test_local_llm_preview_safe_endpoint.py`
- `backend/tests/test_ollama_preview.py`

不得新增文件。如确需新增测试文件，必须先经 ChatGPT 单独审核，不得在实现阶段擅自新增。

## 11. 禁止触碰范围

后续实现不得修改：

- 正式生成链
- 正式导出链
- ZBid 写回链
- `output/`
- `job/`
- `export/`
- 正式模板文件
- 正式生成结果文件
- 与 preview 无关的 UI 主流程
- 任何会改变正式文档生成结果的代码

不得请求或触发：

- `/generate`
- `/export_docx`
- `/review/apply`
- DOCX / JSON / Markdown 正式导出
- ZBid 正式写回

## 12. 后续 runtime smoke 准入

后续完成 default real transport 实现后，必须先完成以下步骤，才能进入 runtime smoke：

- 运行授权 deterministic tests。
- 归档实现复盘。
- 再单独做 runtime smoke plan，或沿用已有 plan 做必要更新。
- runtime smoke 必须单独授权。
- runtime smoke 才允许启动 Ollama / FastAPI。
- runtime smoke 不得直接请求 Ollama `/api/generate`，除非另行授权。
- runtime smoke 仍只通过 `/local-llm/preview-safe` 验证端到端。

不得在实现完成后跳过 deterministic tests 直接启动真实 runtime。

## 13. 风险与回滚

主要风险：

- 风险 1：default real transport 接入后误触正式生成链。
- 风险 2：误写 `output/job/export`。
- 风险 3：真实模型输出不稳定，导致 advisory 不可控。
- 风险 4：thinking-only 被误用为正式正文。
- 风险 5：模型不存在时误触 pull。
- 风险 6：fake transport 测试结构被破坏，导致 deterministic tests 依赖真实 runtime。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。
- 保留总 preview disabled 路径。
- 保留 adapter-off / fake-only 路径。
- 保留 fake transport 注入能力。

兜底要求：

- 出现异常时不得扩大到正式链路。
- 不得删除既有 fake-only 行为。
- 不得为了 runtime smoke 结果直接修改正式生成链、导出链或 ZBid 写回链。

## 14. 当前阶段结论

本阶段仅完成 default real transport guard + deterministic tests 的实现前设计，未修改代码，未运行测试，未启动服务，未证明真实 `/api/generate` 端到端可用。

Step 26 已证明当前 runtime 缺口是 default real transport 未接入，不是 Ollama 服务不可达，也不是本地模型缺失。下一步应优先通过 fake builder / monkeypatch / dependency injection 完成 default wiring 的 deterministic implementation，而不是盲目重复 runtime smoke。

## 15. 下一步建议

下一步建议为 ZDoc Step 29：real-Ollama preview safe endpoint default real transport fake-only implementation + deterministic tests。不得直接进入 runtime smoke，不得直接接正式生成链、导出链或 ZBid 写回。
