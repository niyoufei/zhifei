# ZDoc real-Ollama preview safe endpoint runtime smoke plan refresh

## 1. 阶段背景

Step 26 runtime smoke 曾暴露 `/local-llm/preview-safe` enabled 场景的 `fake_transport_required` 缺口。当时已确认本地 Ollama `/api/tags` loopback 可达，且本地模型包含 `qwen3:0.6b`，但 safe endpoint 双开关 enabled 路径仍未进入默认 real transport。

后续阶段已完成：

- Step 27：完成 default real transport gap design；
- Step 28：完成 default real transport guard + deterministic tests design；
- Step 29：完成 default real transport fake-only implementation + deterministic tests；
- Step 30：完成 default real transport fake-stage review。

当前 default real transport wiring 已通过 fake builder deterministic tests：双开关 enabled 且 no injected transport 时可以进入 default builder；fake builder 返回 fake tags + fake generate 成功时可得到 `status=ok`、`calls_ollama=true`。

但真实 Ollama `/api/generate` runtime 仍未验证。本步目标是基于 Step 29 实现刷新 runtime smoke 边界，不执行 runtime smoke，不启动服务，不运行 Ollama，不运行 `ollama serve`。

## 2. 本次 plan refresh 与旧 plan 的差异

旧 Step 25 plan 允许 enabled 场景出现 `fake_transport_required` 受控缺口，并要求如实记录为当前 bridge 尚未接入默认 real transport。

Step 29 后，双开关 enabled 且 no injected transport 的默认路径理论上应进入 default real transport builder。新的 smoke 重点应从“确认 `fake_transport_required` 缺口”转为“验证 default real transport runtime 是否真实触发”。

本次 plan refresh 的差异如下：

- enabled 场景不应再把 `fake_transport_required` 视为预期缺口；
- enabled 场景应重点记录是否进入 default real transport path；
- enabled 场景应重点记录 `calls_ollama` 是否为 `true`；
- enabled 场景仍不得预设真实 `/api/generate` 必然成功；
- 如果 enabled 场景仍出现 `fake_transport_required`，必须记录为回归风险或 default wiring 未生效；
- runtime smoke 仍只能通过 `/local-llm/preview-safe` 间接验证，不得直接请求 Ollama `/api/generate`，除非后续单独授权。

## 3. runtime smoke 目标

后续 Step 32 runtime smoke 的目标是验证：

- `/local-llm/preview-safe` 在双开关开启后是否进入 default real transport runtime path；
- 真实 runtime 下是否出现 `calls_ollama=true`；
- `qwen3:0.6b` 是否可通过 safe endpoint 形成 bounded preview advisory；
- `fake_transport_required` 是否已不再作为双开关默认路径结果；
- 所有场景是否仍保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`；
- 是否不触发 `/generate`、`/export_docx`、`/review/apply`；
- 是否不写 `output/job/export`。

本计划不执行 runtime smoke。真实 runtime 验证必须等待 Step 32 单独授权。

## 4. runtime smoke 前置条件

后续真正执行 Step 32 前必须满足：

- 当前工作区 clean；
- HEAD 必须等于 Step 31 plan refresh 标签；
- 不允许修改代码/tests；
- 2号窗口仅允许运行 `ollama serve`；
- 不允许下载或拉取模型；
- 先检查 `GET http://127.0.0.1:11434/api/tags`；
- 本地模型必须已存在，优先使用 `qwen3:0.6b`；
- 如模型不存在，立即停止，不得 pull；
- FastAPI 只能监听 `127.0.0.1` 的临时端口，建议使用 `18752`；
- 只允许请求 `/local-llm/preview-safe`；
- 不得请求 `/generate`、`/export_docx`、`/review/apply`；
- 不得直接请求 Ollama `/api/generate`，除非后续单独授权。

如果 `127.0.0.1:11434` 已存在用户持有的 Ollama listener，应记录 PID 和来源判断，不得擅自停止非本步启动的进程。

## 5. runtime smoke 环境变量设计

后续 Step 32 应至少覆盖 3 个场景。

### disabled 场景

```bash
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

预期：

- stable disabled；
- `calls_ollama=false`；
- 不构造 default real transport；
- 不访问 Ollama。

### adapter-off 场景

```bash
export ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

预期：

- stable fake-only 或 controlled non-real path；
- `calls_ollama=false`；
- 不构造 default real transport；
- 不访问 Ollama。

### real-Ollama enabled 场景

```bash
export ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
export ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
export ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
```

代码只读检查确认的可用环境变量：

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`
- `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`
- `ZDOC_OLLAMA_PREVIEW_MODEL`
- `ZDOC_OLLAMA_PREVIEW_TIMEOUT`
- `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`

代码只读检查未发现 safe endpoint real transport path 使用 host 或 temperature 环境变量。当前 default real transport base URL 固定限制为：

```text
http://127.0.0.1:11434
```

后续 runtime smoke 可设置保守值：

```bash
export ZDOC_OLLAMA_PREVIEW_TIMEOUT=10
export ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=128
```

如 runtime 前代码已有变更，必须再次只读核验实际环境变量名称。

## 6. runtime smoke 请求边界

后续 Step 32 仅允许：

```text
GET http://127.0.0.1:11434/api/tags
POST http://127.0.0.1:18752/local-llm/preview-safe
```

明确禁止：

- 直接请求 `POST http://127.0.0.1:11434/api/generate`；
- 请求 `/generate`；
- 请求 `/export_docx`；
- 请求 `/review/apply`；
- 请求任何外部 API；
- 写 `output/job/export`；
- 触发正式文档生成或导出；
- 写回正式章节；
- 接 ZBid 写回。

Step 32 的 `/api/generate` 触达只能由 `/local-llm/preview-safe` 通过 default real transport 间接发生，并且必须由响应中的 `calls_ollama`、`source`、`real_transport_enabled`、`error_type` 或 `failure_reason` 记录结果。

## 7. smoke payload 设计

当前 `backend/app/routers/local_llm_preview_safe.py` 只读检查确认，endpoint 允许字段为：

```text
context_summary
request_id
section_text
section_title
```

推荐最小 payload：

```json
{
  "request_id": "zdoc-step32-enabled",
  "section_title": "Runtime Smoke Preview",
  "section_text": "This is a minimal local runtime smoke payload for preview-only validation.",
  "context_summary": "runtime smoke only; preview advisory; no write; no generation"
}
```

payload 要求：

- 使用最小、非真实投标正文内容；
- 不含敏感项目资料；
- 只用于 preview advisory；
- 字段与当前 endpoint 实现兼容；
- 不包含 `content`、`output`、`job`、`export_path`、`docx_path`、`markdown_path`、`json_path` 等正式输出字段；
- 不得造成生成链或导出链触发。

旧示例中的 `section`、`title`、`content` 字段与当前 endpoint 允许字段不一致，Step 32 不应使用这些字段作为请求 payload。

## 8. 应记录的 smoke 结果字段

后续 Step 32 smoke report 必须记录：

- 当前目录；
- 当前分支；
- 开始前 HEAD；
- 结束后 HEAD；
- git status；
- Ollama PID；
- FastAPI PID；
- 监听端口；
- `/api/tags` HTTP 状态；
- 本地模型列表摘要；
- 使用模型名；
- disabled 场景响应摘要；
- adapter-off 场景响应摘要；
- enabled real-Ollama 场景响应摘要；
- enabled 场景是否 `calls_ollama=true`；
- enabled 场景是否仍出现 `fake_transport_required`；
- enabled 场景是否 controlled failure；
- enabled 场景是否返回 advisory；
- suggestions 数量；
- warnings / risk_notes；
- 是否 `preview_only=true`；
- 是否 `no_write=true`；
- 是否 `affects_generation=false`；
- 是否 `affects_export=false`；
- 是否请求 `/generate`：必须为否；
- 是否请求 `/export_docx`：必须为否；
- 是否请求 `/review/apply`：必须为否；
- 是否写 `output/job/export`：必须为否；
- 所有服务进程是否停止；
- 端口是否无监听。

enabled 场景还应记录：

- `source`；
- `model`；
- `real_transport_enabled`；
- `fake_transport_only`；
- `error_type`；
- `reason` 或 `failure_reason`；
- 是否为 timeout、empty response、thinking-only、model unavailable 或 transport failure。

## 9. 成功判定标准

后续 Step 32 runtime smoke 成功标准：

- disabled 场景 stable disabled，`calls_ollama=false`；
- adapter-off 场景 stable fake-only 或 controlled non-real，`calls_ollama=false`；
- enabled 场景不再返回 `fake_transport_required`；
- enabled 场景真实进入 default real transport path；
- enabled 场景理想结果为 `calls_ollama=true`；
- enabled 场景返回 `status=ok` 或 controlled failure 均可接受，但必须准确记录；
- 所有场景保持 preview-only/no-write；
- 不触发正式生成链；
- 不触发正式导出链；
- 不写 output/job/export；
- 服务结束后端口清理完成。

如果 enabled 场景返回 `status=ok`，还应确认 advisory 是 bounded preview advisory，且没有正式正文写回字段。

## 10. 可接受失败标准

如果 enabled 场景失败，也可接受为“受控失败”，条件是：

- 返回 controlled failure；
- 不抛未处理异常；
- 不写盘；
- 不触发生成链；
- 不触发导出链；
- 不拉取模型；
- 不修改正式正文；
- 能明确记录 `failure_reason` 或 `error_type`；
- 若 `calls_ollama=true` 但模型返回空 response / thinking-only / timeout，也要单独归类。

可接受的 controlled failure 示例包括：

- `model_unavailable`；
- `ollama_unreachable`；
- `timeout`；
- `invalid_response`；
- `transport_failure`。

但每一类都必须同时满足 no-write、no-generation、no-export、no-ZBid-writeback 边界。

## 11. 不可接受失败标准

以下结果不可接受：

- 未处理异常导致服务崩溃；
- 写入 `output/job/export`；
- 触发 `/generate`、`/export_docx`、`/review/apply`；
- 下载或拉取模型；
- 访问外网；
- 修改代码/tests；
- enabled 场景仍返回 `fake_transport_required` 且无解释；
- 将 preview advisory 写入正式章节；
- 影响正式 DOCX 导出或 ZBid 写回。

如果出现不可接受失败，Step 32 必须停止并记录，不得扩大测试范围，不得现场修代码。

## 12. 进程与端口清理要求

后续 Step 32 必须：

- 记录 FastAPI PID；
- 记录 Ollama PID；
- 每个 FastAPI 场景完成后停止本步启动的 FastAPI；
- 本步结束前确认 `127.0.0.1:18752` 无监听；
- 若 Ollama 是本步启动，则本步结束前停止；
- 若 Ollama 是既有用户进程，不得擅自停止，但必须记录 PID 和原因；
- 不得留下僵尸服务进程。

建议每个 FastAPI 场景独立启动并停止，避免环境变量串场。若复用同一端口，必须确认上一场景进程已退出后再启动下一场景。

## 13. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 Step 31 / Step 32 仍只属于 preview-only real transport runtime 验证阶段。不得因为 runtime smoke 成功就直接接正式生成链。

后续仍需：

- 质量评测层；
- shadow generation；
- 人工确认写回；
- 导出一致性校核；
- ZBid 写回隔离。

preview advisory 必须继续被视为建议性输出，不得自动成为正式章节内容。

## 14. 风险与回滚

主要风险：

- 风险 1：真实 runtime 下 default builder 行为与 fake builder 不一致；
- 风险 2：真实模型输出不稳定；
- 风险 3：thinking-only 输出被误当正式正文；
- 风险 4：模型不存在时误触 pull；
- 风险 5：runtime smoke 误触正式生成链或写盘；
- 风险 6：用户误以为 preview advisory 已写入正式方案。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

- 保留 disabled / adapter-off / fake-only 路径；
- 出现异常时不得扩大到正式链路；
- runtime smoke 失败时先归档受控失败或缺口报告，不得直接进入正式生成链、导出链或 ZBid 写回。

## 15. 下一步建议

下一步建议为 ZDoc Step 32：real-Ollama preview safe endpoint runtime smoke + smoke report。该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得接正式生成链、导出链或 ZBid 写回。
