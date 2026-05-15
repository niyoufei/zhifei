# ZDoc real-Ollama preview safe endpoint runtime smoke plan

## 1. 阶段背景

ZDoc Step 23 已完成 safe endpoint bridge fake transport deterministic implementation。该阶段在 default-off、preview-only、no-write 前提下，为 `POST /local-llm/preview-safe` 接入了到 `run_zdoc_ollama_preview` 的受控 bridge，并通过 fake transport / monkeypatch / dependency injection 完成 deterministic tests。

ZDoc Step 24 已完成 fake-stage review，明确当前阶段只证明 fake transport deterministic bridge 可用，不代表真实 Ollama runtime `/api/generate` 端到端可用。

当前必须明确：

- fake transport deterministic tests 已通过；
- 真实 `ollama serve` 未在 Step 23 / Step 24 中运行；
- 真实 `127.0.0.1:11434/api/tags` 未在 Step 23 / Step 24 中访问；
- 真实 `127.0.0.1:11434/api/generate` 未验证；
- 本步只是 runtime smoke 前置计划，不执行 runtime smoke。

只读检查还显示，当前 bridge 代码通过 `SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT` 和 `SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT` 注入 transport。默认未注入 transport 时，`run_zdoc_ollama_preview` 会返回受控 `fake_transport_required` 失败，而不是自动访问真实 `127.0.0.1:11434`。因此，后续 runtime smoke 必须把该结果记录为受控失败或 no-go 事实，不能为了追求 `calls_ollama=true` 而临时扩大范围、修改代码或直接请求禁用路径。

## 2. runtime smoke 目标

后续 runtime smoke 的目标是验证或记录以下事实。本步不执行这些动作。

- 验证 `/local-llm/preview-safe` 在双开关开启后是否真实进入 real-Ollama generate path；
- 验证真实 runtime 下 `calls_ollama=true` 是否成立；
- 验证 `qwen3:0.6b` 或指定本地模型在 safe endpoint 下是否返回 bounded preview advisory；
- 验证真实 runtime 仍保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`；
- 验证不会触发 `/generate`、`/export_docx`、`/review/apply`；
- 验证不会写 `output/job/export`。

如果当前代码仍返回 `fake_transport_required`，runtime smoke 的目标应收敛为记录受控失败事实：safe endpoint 未真实进入 Ollama runtime、未写盘、未触发正式链路、未抛未处理异常。

## 3. runtime smoke 前置条件

后续真正执行 runtime smoke 前必须满足：

- 当前工作区 clean；
- HEAD 必须等于 runtime smoke plan 对应标签；
- 2号窗口只允许运行 `ollama serve`；
- 不允许下载或拉取模型；
- 先检查 `GET http://127.0.0.1:11434/api/tags`；
- 本地模型必须已存在，优先使用 `qwen3:0.6b`；
- 如模型不存在，立即停止，不得拉取；
- FastAPI 只能监听 `127.0.0.1` 的临时端口；
- 只允许请求 `/local-llm/preview-safe`；
- 不得请求 `/generate`、`/export_docx`、`/review/apply`。

建议在 runtime smoke 开始前记录 `output/`、`job/`、`export/`、`backend/data/autoplan/jobs/` 和 `build/` 的文件计数；smoke 结束后再次记录并确认未增加。

## 4. runtime smoke 环境变量设计

disabled 场景：

```text
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

adapter-off 场景：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

real-Ollama enabled 场景：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
```

只读代码检查确认，当前 safe endpoint bridge 相关环境变量还包括：

```text
ZDOC_OLLAMA_PREVIEW_TIMEOUT
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT
```

当前实现中的默认值和边界：

```text
LOCAL_LLM_OLLAMA_PREVIEW_DEFAULT_TIMEOUT_SECONDS=10.0
LOCAL_LLM_OLLAMA_PREVIEW_MAX_TIMEOUT_SECONDS=30.0
LOCAL_LLM_OLLAMA_PREVIEW_DEFAULT_NUM_PREDICT=256
LOCAL_LLM_OLLAMA_PREVIEW_MAX_NUM_PREDICT=768
LOCAL_LLM_OLLAMA_PREVIEW_BASE_URL=http://127.0.0.1:11434
```

本次只读检查未确认 safe endpoint bridge path 存在可用于改写 host/base_url 的环境变量。当前 bridge path 使用固定本地 loopback base URL `http://127.0.0.1:11434`。`ZDOC_OLLAMA_PREVIEW_BASE_URL` 存在于同文件中的 legacy `run_ollama_preview` 路径，但不得在 Step 26 前假定其适用于 `/local-llm/preview-safe` bridge；该项需 runtime 前再次只读核验确认。

如需压低 runtime smoke 输出长度，可在 Step 26 单独授权后考虑：

```text
ZDOC_OLLAMA_PREVIEW_TIMEOUT=30
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=64
```

不得通过环境变量触发下载、拉取、正式生成、导出或写回。

## 5. runtime smoke 请求边界

后续 runtime smoke 仅允许：

- `GET http://127.0.0.1:11434/api/tags`
- `POST http://127.0.0.1:<临时端口>/local-llm/preview-safe`

明确禁止：

- 直接请求 Ollama `/api/generate`，除非后续单独授权；
- 请求 `/generate`；
- 请求 `/export_docx`；
- 请求 `/review/apply`；
- 请求任何外部 API；
- 写 `output/job/export`；
- 触发正式文档生成或导出。

如果 enabled 场景未进入真实 `/api/generate`，只能记录该事实，不得追加直接 `/api/generate` 调用来补证。

## 6. smoke payload 设计

推荐使用最小、非真实投标正文内容，不含敏感项目资料，只用于 preview advisory。字段必须与 `backend/app/routers/local_llm_preview_safe.py` 当前允许字段兼容。

推荐 disabled payload：

```json
{
  "request_id": "zdoc-step26-disabled",
  "section_title": "Runtime smoke preview",
  "section_text": "Synthetic preview-only text for disabled runtime smoke.",
  "context_summary": "disabled runtime smoke; no write; no generation"
}
```

推荐 adapter-off payload：

```json
{
  "request_id": "zdoc-step26-adapter-off",
  "section_title": "Runtime smoke preview",
  "section_text": "Synthetic preview-only text for adapter-off runtime smoke.",
  "context_summary": "adapter-off runtime smoke; no write; no generation"
}
```

推荐 enabled payload：

```json
{
  "request_id": "zdoc-step26-enabled",
  "section_title": "Runtime smoke preview",
  "section_text": "Synthetic preview-only text. Check for missing risk notes and keep this advisory bounded.",
  "context_summary": "enabled runtime smoke; local loopback only; no write; no generation"
}
```

当前 endpoint 只允许以下输入字段：

```text
context_summary
request_id
section_text
section_title
```

不得加入 `content`、`job_id`、`output_path`、`docx_path`、`json_path`、`markdown_path`、`generate`、`export_docx`、`review_apply` 或任何正式生成、导出、写回字段。

## 7. 应记录的 smoke 结果字段

后续 smoke report 必须记录：

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
- 是否 `calls_ollama=true`；
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

如 enabled 场景返回 `fake_transport_required`、`model_unavailable`、`timeout`、`invalid_response` 或 `transport_failure`，报告必须记录 `status`、`error_type`、`reason`、`calls_ollama`、`preview_only`、`no_write` 和 no-route/no-write 字段。

## 8. 成功判定标准

后续 runtime smoke 成功标准：

- disabled 场景 stable disabled，`calls_ollama=false`；
- adapter-off 场景 stable fake-only 或 controlled disabled，`calls_ollama=false`；
- enabled 场景真实进入 Ollama path，理想结果为 `calls_ollama=true`；
- 所有场景保持 preview-only/no-write；
- 不触发正式生成链；
- 不触发正式导出链；
- 不写 `output/job/export`；
- 服务结束后端口清理完成。

由于当前只读检查发现默认 bridge 不自动接入真实 network transport，Step 26 如得到 `fake_transport_required` 且其余安全字段保持正确，应判定为受控失败，而不是 runtime smoke 成功。

## 9. 可接受失败标准

如果 enabled 场景失败，也可接受为“受控失败”，条件是：

- 返回 controlled failure；
- 不抛未处理异常；
- 不写盘；
- 不触发生成链；
- 不触发导出链；
- 不拉取模型；
- 不修改正式正文；
- 能明确记录 `failure_reason` 或 `error_type`。

可接受失败包括但不限于：

- 当前实现仍要求 injected transport，返回 `fake_transport_required`；
- `/api/tags` 不可达；
- 指定模型不存在；
- 真实模型返回空响应；
- 真实模型返回 thinking-only 且被 bounded advisory 限制；
- transport timeout 或异常被转换为 controlled failure。

任一失败都不得作为扩大请求范围、直接访问外部 API、下载模型、修改代码或触发正式链路的理由。

## 10. 风险与回滚

主要风险：

- 风险 1：真实 runtime 接入后误触生成链或写盘；
- 风险 2：真实模型输出不稳定；
- 风险 3：thinking-only 输出被误用；
- 风险 4：模型不存在时误触自动拉取；
- 风险 5：服务进程未停止或端口残留。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

- 保留 disabled / fake-only 路径；
- 出现异常时不得继续扩大测试范围；
- 不得删除既有 fake-only 行为；
- 不得将 runtime smoke 失败扩散到正式生成链、导出链或 ZBid 写回链。

## 11. runtime smoke 禁止事项

后续 runtime smoke 禁止：

- 不得下载模型；
- 不得 pull 模型；
- 不得访问外网；
- 不得运行全量测试；
- 不得生成正式文档；
- 不得导出 DOCX/JSON/Markdown；
- 不得写 `output/job/export`；
- 不得接 ZBid 写回；
- 不得修改代码；
- 不得把 preview advisory 写入正式章节。

## 12. 下一步建议

下一步建议为 ZDoc Step 26：real-Ollama preview safe endpoint runtime smoke + smoke report。该步骤必须单独授权，必须使用 2号窗口仅运行 `ollama serve`，并且仍不得接正式生成链、导出链或 ZBid 写回。
