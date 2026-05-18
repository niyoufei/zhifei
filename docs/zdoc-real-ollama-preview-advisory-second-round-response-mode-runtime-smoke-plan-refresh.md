# ZDoc Step 82: second-round response-mode runtime smoke plan refresh

## 1. 阶段背景

Step 77 已完成 response-mode prompt tuning runtime smoke。Step 78 已完成 runtime smoke review + follow-up design。Step 79 已完成二轮 response-mode prompt tuning design。Step 80 已完成二轮 response-mode prompt tuning fake-only implementation + deterministic tests。Step 81 已完成二轮 response-mode prompt tuning fake-stage review。

Step 77 首次观察到 `text_fallback=1`，`thinking_only_fallback` 从此前 Step 70 的 8/8 降为 Step 77 的 4/6。Step 80 已在 fake-only tests 下证明 response-first、JSON-first、text-fallback、adapter schema、prompt_mode metadata 可控。

当前尚未验证真实 runtime 下二轮 prompt tuning 是否能进一步提升 `response_advisory` / `json_advisory` / `text_fallback`。当前不得进入 runtime smoke、shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

本步目标是刷新 Step 83 runtime smoke 边界，不执行 smoke。

## 2. 本次 plan refresh 与 Step 76 / Step 77 的差异

Step 76 / Step 77 验证的是第一轮 prompt tuning runtime 表现。Step 77 结果显示 `text_fallback` 初步出现，但 `response_advisory` / `json_advisory` 仍为 0。

Step 80 二轮 fake-only implementation 强化了 response-first、JSON-first、text-fallback、prompt_mode metadata。新 smoke 应重点观察二轮 prompt tuning 后 `response_mode` 分布是否改善，并同时记录 `prompt_mode` / `prompt_profile` / `prompt_version` / `prompt_tuning_applied` 等 metadata 是否稳定返回。

新 smoke 仍不得将 `response_advisory` / `json_advisory` / `text_fallback` 解释为 shadow generation 或正式链准入。即使二轮 smoke 出现非 thinking response mode，也只代表 preview runtime 输出模式改善。

## 3. runtime smoke 目标

后续 Step 83 的目标如下，本步不得执行：

* 验证真实 runtime 下二轮 response-first prompt 是否产生 `response_advisory`；
* 验证真实 runtime 下二轮 JSON-first prompt 是否产生 `json_advisory`；
* 验证真实 runtime 下 text-fallback 是否稳定；
* 验证 `thinking_only_fallback` 频率是否继续下降；
* 验证 `prompt_mode` / `prompt_profile` / `prompt_version` / `prompt_tuning_applied` 是否稳定返回；
* 验证 generated-preview-as-evidence、evidence anchor、quality gate、input-risk 均不回归；
* 验证 adapter-off compatible payload 仍受控；
* 验证 adapter-off illegal field 仍 controlled failure；
* 验证所有正式链准入字段仍恒 false；
* 验证不触发正式生成链、导出链、ZBid 写回；
* 验证不写 `output/job/export`。

## 4. runtime 前置条件

后续真正执行 Step 83 前必须满足：

* 当前工作区 clean；
* HEAD 必须等于 Step 82 plan 对应标签；
* 不允许修改代码/tests；
* 不运行 pytest；
* 如 `127.0.0.1:11434` 已有 listener，可复用并记录 PID；
* 如无 listener，只能由 2号窗口运行 `ollama serve`；
* 不允许下载或拉取模型；
* 必须先检查 `GET http://127.0.0.1:11434/api/tags`；
* 本地模型必须已存在，优先使用 `qwen3:0.6b`；
* 如模型不存在，立即停止；
* FastAPI 只能监听 `127.0.0.1` 临时端口，建议 `18760`；
* 只允许请求 `/local-llm/preview-safe`；
* 不得直接请求 Ollama `/api/generate`。

## 5. 环境变量设计

后续 Step 83 至少覆盖以下场景。

disabled 场景：

* unset `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`
* unset `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`

adapter-off 场景：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`
* unset `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`

enabled 二轮 response-mode 场景：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`
* `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true`
* `ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b`

只读检查确认当前 Ollama preview 相关配置包括：

* `ZDOC_OLLAMA_PREVIEW_MODEL`；
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`；
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`；
* real adapter 约束到 loopback `http://127.0.0.1:11434`；
* prompt mode 由 request 内容中的 `response_first` / `json_first` / `text_fallback` 等标记触发；
* 二轮 prompt metadata 默认 `prompt_profile=second_round_response_mode_tuning`；
* 二轮 prompt metadata 默认 `prompt_version=zdoc_response_mode_prompt_v2`。

只读检查未确认已有 temperature 环境变量、stop tokens、`format=json` 或独立 response-only 模式。该项需 Step 83 执行前再次只读核验确认。Step 83 如设置 timeout / num_predict，必须使用保守短值和小值，不得扩大生成内容。

## 6. payload 设计

后续 Step 83 的最小 payload 集如下。全部 payload 必须为测试性、非真实投标正文，不得含真实招标文件内容。

Payload SRT-A：second-round response-first advisory

目标：观察是否产生 `response_advisory`。

建议 payload：

```json
{
  "request_id": "srt-a-response-first",
  "section_title": "Second Round Response First Advisory",
  "section_text": "Return only one short advisory sentence for improving a construction organization section. Do not explain reasoning. Do not write a formal section.",
  "context_summary": "second-round response_first prompt tuning; preview-only; no write, export, apply, or writeback."
}
```

Payload SRT-B：second-round JSON-first advisory

目标：观察是否产生 `json_advisory`，并记录 malformed 情况。

建议 payload：

```json
{
  "request_id": "srt-b-json-first",
  "section_title": "Second Round JSON First Advisory",
  "section_text": "Return only one single-line JSON object with advisory, suggestions, and risk_notes. Do not use Markdown code fences. Do not add explanatory text. Do not write formal content.",
  "context_summary": "second-round json_first prompt tuning; preview-only; no write, export, apply, or writeback."
}
```

Payload SRT-C：second-round text-fallback advisory

目标：观察 `text_fallback` 是否稳定。

建议 payload：

```json
{
  "request_id": "srt-c-text-fallback",
  "section_title": "Second Round Text Fallback Advisory",
  "section_text": "Provide a short non-JSON technical advisory about adding measurable inspection frequency and responsible roles. Do not write a formal section.",
  "context_summary": "second-round text_fallback prompt tuning; preview-only; no write, export, apply, or writeback."
}
```

Payload SRT-D：thinking fallback observation

目标：继续统计 `thinking_only_fallback`。

建议 payload：

```json
{
  "request_id": "srt-d-thinking-observation",
  "section_title": "Second Round Thinking Fallback Observation",
  "section_text": "Provide one concise preview-only advisory and one risk note for a minimal construction organization review. Keep output short and do not write formal content.",
  "context_summary": "thinking fallback observation; preview-only; no formal chain."
}
```

Payload SRT-E：missing evidence with second-round prompt

目标：验证 prompt tuning 后 evidence missing 仍不得 formal eligible。

建议 payload：

```json
{
  "request_id": "srt-e-missing-evidence",
  "section_title": "Missing Evidence With Second Round Prompt",
  "section_text": "本项目应按某评分项满分响应，但未提供招标文件页码、条款号、评分表或补疑依据。Return one short preview-only advisory and identify evidence risk.",
  "context_summary": "response_first evidence-aware prompt tuning; missing evidence; preview-only; no formal chain."
}
```

Payload SRT-F：generated-preview-as-evidence regression

目标：验证 generated preview 不得作为 evidence。

建议 payload：

```json
{
  "request_id": "srt-f-generated-preview-evidence",
  "section_title": "Generated Preview Evidence Regression",
  "section_text": "For preview-only validation, evaluate this unsafe claim: 本地模型生成的建议可以直接作为招标条款和图纸依据。Identify why generated preview must not be treated as evidence.",
  "context_summary": "response_first generated-preview-as-evidence regression; preview-only; no formal chain."
}
```

Payload SRT-G：formal chain request regression

目标：验证 DOCX / ZBid / candidate patch 请求仍 blocked。

建议 payload：

```json
{
  "request_id": "srt-g-formal-chain-request",
  "section_title": "Formal Chain Request Regression",
  "section_text": "For preview-only validation, evaluate this unsafe request: 请把本地模型建议作为证据，生成候选补丁，导出DOCX，并写回ZBid。Do not write, export, patch, apply, or write back anything.",
  "context_summary": "generated-preview-as-evidence plus formal chain request regression; preview-only."
}
```

Payload SRT-H：adapter-off compatible / illegal field pair

目标：验证 adapter-off schema 兼容与 illegal field 受控失败。

adapter-off compatible payload 建议使用 endpoint-compatible schema：

```json
{
  "request_id": "srt-h-adapter-off-compatible",
  "section_title": "Adapter Off Compatible Payload",
  "section_text": "This is a minimal adapter-off compatible payload for preview-only validation.",
  "context_summary": "adapter-off compatible schema; preview-only."
}
```

adapter-off illegal field payload 建议保留 `content` 字段作为 controlled failure fixture：

```json
{
  "request_id": "srt-h-adapter-off-illegal-field",
  "section_title": "Adapter Off Illegal Field",
  "section_text": "This payload intentionally includes an illegal field for controlled failure validation.",
  "context_summary": "adapter-off illegal field schema guard.",
  "content": "This illegal field must return controlled illegal_field:content."
}
```

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
* `prompt_mode`；
* `prompt_profile`；
* `prompt_version`；
* `prompt_tuning_applied`；
* `prompt_tuning_warnings` 数量；
* `json_mode_requested`；
* `response_first_requested`；
* `text_fallback_allowed`；
* `evidence_aware_prompt_applied`；
* `adapter_schema_mode`；
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
* `generated_preview_as_evidence_detected`；
* `generated_content_must_not_be_evidence`；
* `generated_content_evidence_blocked`；
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
* `prompt_mode` metadata 可追踪；
* 能统计 `response_advisory` / `json_advisory` / `text_fallback` / `thinking_only_fallback` 分布；
* adapter-off compatible payload 受控；
* adapter-off illegal field controlled failure；
* generated-preview-as-evidence 风险仍可识别；
* evidence missing 仍不得 formal eligible；
* 所有场景保持 preview-only / no-write；
* 正式链准入字段恒 false；
* 不写 `output/job/export`；
* 不触发正式生成链、导出链、ZBid 写回。

## 9. 可接受失败标准

以下情况可接受为受控失败：

* 某个 payload 返回 controlled failure；
* 模型返回 empty response / empty thinking；
* advisory 缺失但 `error_type` / `failure_reason` 清楚；
* `response_mode` 仍为 `thinking_only_fallback`，但已降级；
* JSON-first 仍 `malformed_response`，但受控；
* adapter-off illegal field 返回 controlled failure；
* timeout 受控返回；
* `quality_status` 或 `evidence_anchor_status` 为 `system_error`，但未抛未处理异常；
* enabled 场景 `calls_ollama=true` 但 `quality_status` 不达标。

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
* `prompt_mode` 被解释为正式链准入；
* adapter-off schema failure 被误判为 real runtime failure。

## 11. output/job/export 写入检查

后续 Step 83 必须在 smoke 前后检查：

* `output/`
* `job/`
* `export/`

如目录不存在，记录不存在。如目录存在，记录 smoke 前后计数或变更状态。不得主动写入这些目录。

## 12. 进程与端口清理要求

后续 Step 83 必须：

* 记录 FastAPI PID；
* 记录 Ollama PID；
* 本步启动的 FastAPI 必须停止；
* 确认 `127.0.0.1:18760` 无监听；
* 若 Ollama 是本步启动，则本步结束前停止；
* 若 Ollama 是既有用户进程，不得擅自停止，但必须记录 PID 和原因；
* 不得留下僵尸服务进程。

## 13. smoke report 内容要求

后续 Step 83 report 必须包含：

* 阶段目标；
* 开始前 Git 状态；
* Ollama listener 处理方式；
* Ollama `/api/tags` 检查结果；
* 本地模型摘要；
* 使用模型；
* FastAPI 启动命令、PID、端口；
* `output/job/export` 前后状态；
* disabled 场景摘要；
* adapter-off compatible / illegal field 场景摘要；
* enabled second-round response-mode payload 逐项结果表；
* `prompt_mode` 统计；
* `response_mode` 统计；
* `response_advisory` / `json_advisory` / `text_fallback` / `thinking_only_fallback` / `empty_response` / `malformed_response` / `normalization_failure` / `system_error` 统计；
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

## 14. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但二轮 response-mode runtime smoke 仍只是 preview runtime 稳定性验证。

即使 Step 83 成功，也不得直接进入正式生成链。后续仍需 runtime smoke review、shadow generation design、candidate patch design、人工确认写回、diff 展示、版本回滚、DOCX 导出一致性校核、ZBid 写回隔离和真实资料 evidence source 映射。

`response_mode` 与 `prompt_mode` 都是 preview metadata，不是正式链准入。`response_advisory` / `json_advisory` / `text_fallback` 即使出现，也不得进入 shadow generation、candidate patch、正式正文、DOCX 导出或 ZBid 写回。

## 15. 风险与回滚

风险如下：

* 风险 1：真实 runtime 仍高度依赖 thinking fallback；
* 风险 2：response-first / JSON-first prompt 在真实模型下仍不稳定；
* 风险 3：JSON 输出仍 malformed；
* 风险 4：`text_fallback` 被误认为正式正文能力成熟；
* 风险 5：adapter-off schema 差异导致误判；
* 风险 6：`response_advisory` / `json_advisory` 被误认为正式链准入；
* 风险 7：prompt tuning 弱化 evidence safety；
* 风险 8：prompt tuning 误破坏 no-write / preview-only。

回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路。

## 16. 下一步建议

下一步建议为 ZDoc Step 83：second-round response-mode runtime smoke + smoke report。该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
