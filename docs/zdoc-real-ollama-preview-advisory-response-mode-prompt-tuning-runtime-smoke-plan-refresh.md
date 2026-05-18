# ZDoc response-mode prompt tuning runtime smoke plan refresh

## 1. 阶段背景

本阶段为 ZDoc Step 76：response-mode prompt tuning runtime smoke plan refresh。

前序阶段事实如下：

* Step 70 已完成 response-mode / evidence-aware runtime smoke；
* Step 70 暴露真实 runtime 8/8 enabled payload 均为 `thinking_only_fallback`；
* Step 72 已完成 response-mode prompt tuning + adapter-off schema follow-up design；
* Step 73 已完成 response-mode prompt tuning guard + deterministic tests design；
* Step 74 已完成 response-mode prompt tuning fake-only implementation + deterministic tests；
* Step 75 已完成 fake-stage review；
* 当前 response-first / JSON-first / text-fallback / adapter-off schema follow-up 在 fake-only deterministic tests 下可控；
* 当前尚未验证真实 runtime 下 `thinking_only_fallback` 频率是否下降；
* 当前尚未证明 `response_advisory` / `json_advisory` / `text_fallback` 在真实 runtime 下稳定；
* 当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回；
* 本步目标是刷新 response-mode prompt tuning runtime smoke 边界，不执行 smoke。

本步为 docs-only runtime smoke 计划刷新步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 正式导出，不接 ZBid 正式写回。

## 2. 本次 plan refresh 与 Step 69 / Step 70 的差异

Step 69 / Step 70 重点是验证 response-mode 与 evidence-aware metadata 是否随 runtime 返回。

Step 70 已证明 runtime 受控，但 enabled payload 8/8 均为 `thinking_only_fallback`。也就是说，Step 70 的核心结论不是 response mode 已稳定，而是 response-mode metadata 可追踪，且 thinking fallback 高依赖仍存在。

Step 74 已加入 response-first / JSON-first / text-fallback prompt tuning 的 fake-only 测试基础。新 smoke 的重点应从“识别 thinking fallback 高依赖”转为“验证 prompt tuning 后是否出现非 thinking response mode”。

因此，Step 77 的 smoke 必须继续记录 response_mode 分布，并重点比较：

* `response_advisory` 是否出现；
* `json_advisory` 是否出现；
* `text_fallback` 是否出现；
* `thinking_only_fallback` 是否仍为主路径；
* adapter-off compatible payload 是否不再误触 `illegal_field`；
* adapter-off illegal field 是否仍为 controlled failure。

新 smoke 仍不得把 `response_advisory` / `json_advisory` / `text_fallback` 解释为正式链准入。任何 response mode 改善都只代表 preview runtime 输出可观测性改善，不代表可进入 shadow generation 或正式生成链。

## 3. runtime smoke 目标

后续 Step 77 的目标如下，本步不得执行：

* 验证真实 runtime 下 response-first prompt 是否产生 `response_advisory`；
* 验证真实 runtime 下 JSON-first prompt 是否产生 `json_advisory`；
* 验证真实 runtime 下 text-fallback prompt 是否产生 `text_fallback`；
* 验证 `thinking_only_fallback` 频率是否较 Step 70 降低；
* 验证 adapter-off compatible payload 是否不再误触 `illegal_field`；
* 验证 adapter-off illegal field 仍 controlled failure；
* 验证 generated-preview-as-evidence / evidence anchor / quality gate / input-risk 均不回归；
* 验证所有正式链准入字段仍恒 false；
* 验证不触发正式生成链、导出链、ZBid 写回；
* 验证不写 `output/job/export`。

本次 runtime smoke 的成功不要求所有 payload 都 `preview_ok`，也不要求完全消除 `thinking_only_fallback`。它只要求真实 runtime 返回受控、字段可追踪、正式链隔离稳定、prompt tuning 效果可被客观统计。

## 4. runtime 前置条件

后续真正执行 Step 77 前必须满足：

* 当前工作区 clean；
* HEAD 必须等于 Step 76 plan 对应标签；
* 不允许修改代码/tests；
* 不运行 pytest；
* 如 `127.0.0.1:11434` 已有 listener，可复用并记录 PID；
* 如无 listener，只能由 2号窗口运行 `ollama serve`；
* 不允许下载或拉取模型；
* 必须先检查 `GET http://127.0.0.1:11434/api/tags`；
* 本地模型必须已存在，优先使用 `qwen3:0.6b`；
* 如模型不存在，立即停止；
* FastAPI 只能监听 `127.0.0.1` 临时端口，建议 `18759`；
* 只允许请求 `/local-llm/preview-safe`；
* 不得直接请求 Ollama `/api/generate`。

如果任何前置条件不满足，Step 77 应立即停止并报告，不得启动服务，不得继续 smoke，不得修改文件。

## 5. 环境变量设计

后续 Step 77 至少覆盖以下场景。

disabled 场景：

* unset `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`
* unset `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`

adapter-off 场景：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`
* unset `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`

enabled response-mode prompt tuning 场景：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`
* `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true`
* `ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b`

只读代码检查到的实际变量和参数如下：

* `ZDOC_OLLAMA_PREVIEW_MODEL`；
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`；
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`；
* Ollama base URL 固定为 `http://127.0.0.1:11434`；
* generate payload 使用 `options: {"num_predict": ...}`；
* prompt mode 不是环境变量，而是由 request 内容中的 `response_first` / `json_first` / `text_fallback` 等标记触发；
* 未发现 temperature 环境变量；
* 未确认 stop / format / response-only / JSON format 参数是否可用，该项需 Step 77 执行前再次只读核验确认。

Step 77 如设置 timeout / num_predict，必须保持保守短值；不得扩大生成内容，不得访问外网。

## 6. payload 设计

后续 Step 77 的最小 payload 集如下。全部 payload 必须为测试性、非真实投标正文，不得含真实招标文件内容。

所有 payload 应优先使用 endpoint-compatible schema：

```json
{
  "request_id": "payload-id",
  "section_title": "Short Title",
  "section_text": "Preview-only validation text.",
  "context_summary": "preview-only; do not write, export, patch, or apply."
}
```

### Payload PT-A：response-first advisory

目标：观察是否产生 `response_advisory`。

建议 payload：

```json
{
  "request_id": "pt-a-response-first",
  "section_title": "Response First Advisory Probe",
  "section_text": "For preview-only validation, provide one short advisory on improving a construction organization section. Do not write a formal section.",
  "context_summary": "response_first prompt tuning; preview-only; do not include reasoning; do not write, export, patch, or apply."
}
```

### Payload PT-B：JSON-first advisory

目标：观察是否产生 `json_advisory`。

建议 payload：

```json
{
  "request_id": "pt-b-json-first",
  "section_title": "JSON First Advisory Probe",
  "section_text": "For preview-only validation, return a compact JSON object with advisory, suggestions, and risk_notes. Do not write formal content.",
  "context_summary": "json_first prompt tuning; preview-only; do not create a file; do not export or write back."
}
```

### Payload PT-C：text-fallback advisory

目标：观察是否产生 `text_fallback`。

建议 payload：

```json
{
  "request_id": "pt-c-text-fallback",
  "section_title": "Text Fallback Advisory Probe",
  "section_text": "For preview-only validation, provide a short non-JSON technical advisory about inspection frequency and responsible roles. Do not write a formal section.",
  "context_summary": "text_fallback prompt tuning; preview-only; no formal output."
}
```

### Payload PT-D：thinking fallback observation

目标：继续统计 `thinking_only_fallback`。

建议 payload：

```json
{
  "request_id": "pt-d-thinking-observation",
  "section_title": "Thinking Fallback Observation",
  "section_text": "For preview-only validation, provide one concise advisory and one risk note for a minimal construction organization review.",
  "context_summary": "observe response_mode distribution; preview-only; do not write final content."
}
```

### Payload PT-E：adapter-off compatible payload

目标：验证 adapter-off compatible schema 不误触 `illegal_field`。

该 payload 应在 adapter-off 场景执行：

```json
{
  "request_id": "pt-e-adapter-off-compatible",
  "section_title": "Adapter Off Compatible Payload",
  "section_text": "This is a minimal adapter-off compatible payload for preview-only validation.",
  "context_summary": "adapter-off compatible schema; preview-only."
}
```

### Payload PT-F：adapter-off illegal field control

目标：验证非法字段仍 controlled failure。

该 payload 应在 adapter-off 场景执行：

```json
{
  "request_id": "pt-f-adapter-off-illegal-field",
  "section_title": "Adapter Off Illegal Field",
  "section_text": "This payload intentionally includes an illegal formal field for controlled validation.",
  "context_summary": "adapter-off illegal field control.",
  "content": "This illegal formal field must be rejected."
}
```

预期：HTTP 200 受控返回，`status=failure`，`error_type=illegal_field`，`reason=illegal_field:content`，`calls_ollama=false`。

### Payload PT-G：generated-preview-as-evidence regression

目标：验证 generated preview 不得作为 evidence。

建议 payload：

```json
{
  "request_id": "pt-g-generated-preview-evidence",
  "section_title": "Generated Preview Evidence Regression",
  "section_text": "For preview-only validation, evaluate this unsafe claim: 本地模型生成的建议可以直接作为招标条款和图纸依据。Identify evidence risk only.",
  "context_summary": "response_first generated-preview-as-evidence regression; preview-only; do not write, export, patch, or apply."
}
```

预期：`generated_preview_as_evidence_detected=true`，`evidence_anchor_status` 不得为 `anchored`，应为 `invalid_anchor` / blocked / `review_required` 中的受控状态。

### Payload PT-H：evidence missing + prompt tuning

目标：验证 response mode 即使改善，evidence missing 仍不得 formal eligible。

建议 payload：

```json
{
  "request_id": "pt-h-evidence-missing",
  "section_title": "Evidence Missing Prompt Tuning",
  "section_text": "For preview-only validation, review this statement: 本项目应按某评分项满分响应，但未提供招标文件页码、条款号、评分表或补疑依据。Provide one short advisory and identify evidence risk.",
  "context_summary": "response_first evidence-aware prompt tuning; preview-only; missing source must remain review_required."
}
```

预期：`evidence_anchor_required=true`，`evidence_anchor_status` 不得为 `anchored`，正式链准入字段恒 false。

## 7. 每个 payload 必须记录字段

对每项 payload 记录：

* `payload_id`；
* payload 目的；
* HTTP 状态；
* `status`；
* `ok`；
* `preview_only`；
* `no_write`；
* `affects_generation`；
* `affects_export`；
* `calls_ollama`；
* `model`；
* `source`；
* `response_mode`；
* `response_source`；
* `preview_mode`；
* `fallback_reason`；
* `response_mode_confidence`；
* `response_mode_warnings` 数量；
* `response_mode_review_required`；
* `thinking_fallback_detected`；
* advisory 是否存在；
* advisory 长度；
* suggestions 数量；
* risk_notes / warnings 数量；
* `quality_status`；
* `input_risk_status`；
* `evidence_anchor_required`；
* `evidence_anchor_status`；
* `invalid_anchor_reason`；
* `generated_preview_as_evidence_detected`；
* `generated_content_must_not_be_evidence`；
* `generated_content_evidence_blocked`；
* `evidence_review_required`；
* `evidence_blocked`；
* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`；
* `error_type` / `failure_reason`，如存在。

注意：不得在报告中大量粘贴完整模型输出，只记录摘要、长度、数量、状态和关键风险。

## 8. 成功判定标准

本步成功不是要求完全消除 `thinking_only_fallback`，而是要求：

* 所有请求均受控返回；
* 不出现未处理异常；
* `response_mode` 字段可追踪；
* 至少能客观统计 `response_advisory` / `json_advisory` / `text_fallback` / `thinking_only_fallback` 分布；
* adapter-off compatible payload 受控；
* adapter-off illegal field controlled failure；
* generated-preview-as-evidence 风险仍可识别；
* evidence missing 仍不得 formal eligible；
* 所有场景保持 preview-only / no-write；
* 正式链准入字段恒 false；
* 不写 `output/job/export`；
* 不触发正式生成链、导出链、ZBid 写回。

如果 Step 77 中仍多数或全部 enabled payload 为 `thinking_only_fallback`，只要降级和正式链隔离受控，也可作为受控结果记录；但不得解读为 prompt tuning 成功。

## 9. 可接受失败标准

以下情况可接受为受控失败：

* 某个 payload 返回 controlled failure；
* 模型返回 empty response / empty thinking；
* advisory 缺失但 `error_type` / `failure_reason` 清楚；
* `response_mode` 仍为 `thinking_only_fallback`，但已降级；
* adapter-off illegal field 返回 controlled failure；
* timeout 受控返回；
* `quality_status` 或 `evidence_anchor_status` 为 `system_error`，但未抛未处理异常；
* enabled 场景 `calls_ollama=true` 但 `quality_status` 不达标。

这些情况必须在 smoke report 中作为受控失败记录，不得被包装为成功准入。

## 10. 不可接受失败标准

以下结果不可接受：

* 未处理异常导致服务崩溃；
* 写入 `output/job/export`；
* 触发 `/generate`、`/export_docx`、`/review/apply`；
* 下载或拉取模型；
* 访问外网；
* 修改代码/tests；
* 将 advisory 写入正式章节；
* `formal_generation_allowed` 变为 true；
* `shadow_candidate_allowed` 变为 true；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 变为 true；
* generated preview 被当作 evidence；
* `response_mode` 被解释为正式链准入；
* adapter-off schema failure 被误判为 real runtime failure。

如出现不可接受失败，应立即停止并记录，不得继续扩大到正式链路。

## 11. output/job/export 写入检查

后续 Step 77 必须在 smoke 前后检查：

* `output/`
* `job/`
* `export/`

如目录不存在，记录不存在。如目录存在，记录 smoke 前后计数或变更状态。不得主动写入这些目录。

该检查用于证明 smoke 未产生正式输出、未写 job、未产生 export artifact。检查结果应进入 smoke report。

## 12. 进程与端口清理要求

后续 Step 77 必须：

* 记录 FastAPI PID；
* 记录 Ollama PID；
* 本步启动的 FastAPI 必须停止；
* 确认 `127.0.0.1:18759` 无监听；
* 若 Ollama 是本步启动，则本步结束前停止；
* 若 Ollama 是既有用户进程，不得擅自停止，但必须记录 PID 和原因；
* 不得留下僵尸服务进程。

进程与端口清理是 smoke 是否可接受的必要条件之一。若无法确认清理状态，应如实记录并停止，不得进入下一阶段。

## 13. smoke report 内容要求

后续 Step 77 report 必须包含：

* 阶段目标；
* 开始前 Git 状态；
* Ollama listener 处理方式；
* Ollama `/api/tags` 检查结果；
* 本地模型摘要；
* 使用模型；
* FastAPI 启动命令、PID、端口；
* `output/job/export` 前后状态；
* disabled 场景摘要；
* adapter-off 场景摘要；
* enabled response-mode prompt tuning payload 逐项结果表；
* response_mode 统计；
* `response_advisory` / `json_advisory` / `text_fallback` / `thinking_only_fallback` / `empty_response` / `malformed_response` / `normalization_failure` / `system_error` 统计；
* adapter-off compatible / illegal field 结果；
* `generated_preview_as_evidence_detected` 次数；
* `generated_content_evidence_blocked` 次数；
* thinking fallback 出现次数；
* `formal_generation_allowed` 是否恒 false；
* `shadow_candidate_allowed` 是否恒 false；
* writeback/export/zbid_writeback 是否恒 false；
* 是否请求 `/generate`：否；
* 是否请求 `/export_docx`：否；
* 是否请求 `/review/apply`：否；
* 是否直接请求 Ollama `/api/generate`：否；
* 是否写 `output/job/export`：否；
* 是否下载或拉取模型：否；
* 是否修改代码/tests：否；
* 进程停止与端口清理情况；
* 风险说明；
* 下一步建议。

report 不得大量粘贴完整模型输出。只记录摘要、字段、数量、状态、风险和清理结果。

## 14. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 response-mode prompt tuning runtime smoke 仍只是 preview runtime 稳定性验证。

即使 Step 77 成功，也不得直接进入正式生成链。后续仍需：

* runtime smoke review；
* shadow generation design；
* candidate patch design；
* 人工确认写回；
* diff 展示；
* 版本回滚；
* DOCX 导出一致性校核；
* ZBid 写回隔离；
* 真实资料 evidence source 映射。

`response_advisory`、`json_advisory` 或 `text_fallback` 的出现只能说明 preview 输出模式改善，不代表内容可进入正式章节、DOCX、ZBid 或 candidate patch。

## 15. 风险与回滚

当前风险如下：

* 风险 1：真实 runtime 仍高度依赖 thinking fallback；
* 风险 2：response-first / JSON-first prompt 在真实模型下失效；
* 风险 3：JSON 输出不稳定；
* 风险 4：adapter-off schema 差异导致误判；
* 风险 5：`response_advisory` 被误认为正式链准入；
* 风险 6：prompt tuning 弱化 evidence safety；
* 风险 7：prompt tuning 误破坏 no-write / preview-only。

回滚措施：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；

兜底措施：

* 保留 disabled / adapter-off / fake-only 路径；
* 出现异常时不得扩大到正式链路。

如果 runtime smoke 中 prompt tuning 没有改善 response mode 分布，应继续保留 fake-only 和 adapter-off 路径，并回到 docs-only follow-up 设计，不得直接推进 shadow generation。

## 16. 下一步建议

下一步建议为 ZDoc Step 77：response-mode prompt tuning runtime smoke + smoke report。该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
