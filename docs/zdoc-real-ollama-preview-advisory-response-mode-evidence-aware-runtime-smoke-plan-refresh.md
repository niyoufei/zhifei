# ZDoc response-mode evidence-aware runtime smoke plan refresh

## 1. 阶段背景

本阶段执行 ZDoc Step 69：response-mode / evidence-aware runtime smoke plan refresh。

前序阶段事实如下：

* Step 64 已完成 evidence-aware multi-payload smoke，暴露 8/8 enabled payload 均为 `thinking_only_fallback`；
* Step 65 已完成 response-mode / generated-preview evidence follow-up design；
* Step 66 已完成 response-mode / generated-preview-as-evidence guard design；
* Step 67 已完成 response-mode / generated-preview-as-evidence guard fake-only implementation + deterministic tests；
* Step 68 已完成 fake-stage review；
* 当前 response-mode / generated-preview-as-evidence guard 在 fake-only deterministic tests 下可控；
* 当前尚未验证真实 runtime 下 `response_mode` 分布是否改善；
* 当前尚未验证 generated-preview-as-evidence guard 在真实 runtime 下是否稳定；
* 当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回；
* 本步目标是刷新 response-mode / evidence-aware runtime smoke 边界，不执行 smoke。

本步为 docs-only runtime smoke 计划刷新步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 导出，不接 ZBid 正式写回。

## 2. 本次 plan refresh 与 Step 63 / Step 64 的差异

Step 63 / Step 64 与本次计划刷新存在以下差异：

* Step 63 / Step 64 重点是 evidence-aware metadata 是否返回；
* Step 64 已证明 evidence-aware runtime 受控，但 8/8 为 `thinking_only_fallback`；
* Step 67 后新增了 `response_mode` 字段和 generated-preview-as-evidence guard；
* 新 smoke 不再只观察 `evidence_anchor_status`，还必须观察 `response_mode` / `response_source` / `fallback_reason` / `thinking_fallback_detected`；
* 新 smoke 必须验证 `generated_preview_as_evidence_detected` / `generated_content_evidence_blocked` / `invalid_anchor_reason`；
* 新 smoke 仍不得解释为 shadow generation 或正式生成链准入。

换言之，Step 64 的核心问题已经从“metadata 是否存在”推进为“response-mode 是否可观测、是否仍高度 fallback，以及 generated preview as evidence 是否在真实 runtime 下 fail-closed”。

## 3. runtime smoke 目标

后续 Step 70 的目标如下。本步只设计，不执行：

* 验证真实 runtime 下 `response_mode` 是否稳定返回；
* 验证真实 runtime 下是否仍高度依赖 `thinking_only_fallback`；
* 验证 `response_advisory` / `json_advisory` / `text_fallback` 是否有机会出现；
* 验证 generated-preview-as-evidence 场景是否 `invalid_anchor` / blocked / `review_required`；
* 验证 `generated_content_must_not_be_evidence` 是否稳定透出；
* 验证 generated preview + direct write / DOCX / ZBid / candidate patch 是否 blocked；
* 验证 `evidence_anchor_status` 与 `response_mode` 分离；
* 验证所有正式链准入字段仍恒 false；
* 验证不触发正式生成链、导出链、ZBid 写回；
* 验证不写 `output/job/export`。

Step 70 成功不要求所有 payload 都 `preview_ok`，也不要求所有 payload 都非 thinking fallback。成功重点是所有请求受控返回、字段可追踪、门禁 fail-closed、正式链隔离稳定。

## 4. runtime 前置条件

后续真正执行 Step 70 前必须满足：

* 当前工作区 clean；
* HEAD 必须等于 Step 69 plan 对应标签；
* 不允许修改代码/tests；
* 不运行 pytest；
* 如 `127.0.0.1:11434` 已有 listener，可复用并记录 PID；
* 如无 listener，只能由 2号窗口运行 `ollama serve`；
* 不允许下载或拉取模型；
* 必须先检查 `GET http://127.0.0.1:11434/api/tags`；
* 本地模型必须已存在，优先使用 `qwen3:0.6b`；
* 如模型不存在，立即停止；
* FastAPI 只能监听 `127.0.0.1` 临时端口，建议 `18758`；
* 只允许请求 `/local-llm/preview-safe`；
* 不得直接请求 Ollama `/api/generate`。

Ollama listener 处理边界：

* 如已有 listener，不得重复启动 `ollama serve`，不得擅自停止既有 PID；
* 如无 listener，只能由 2号窗口运行 `ollama serve`，且 2号窗口不得运行其他命令；
* 如本步启动 Ollama，Step 70 结束前必须停止本步启动的 Ollama 进程；
* 如模型缺失，不得 pull，不得下载模型，直接停止并记录。

## 5. 环境变量设计

后续 Step 70 至少覆盖以下场景。

disabled 场景：

* unset `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`
* unset `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`

adapter-off 场景：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`
* unset `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`

enabled response-mode / evidence-aware 场景：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`
* `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true`
* `ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b`

只读代码核验到的相关运行变量：

* `ZDOC_OLLAMA_PREVIEW_MODEL`
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`

可选保守参数建议：

* `ZDOC_OLLAMA_PREVIEW_TIMEOUT=20`
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=128`

当前只读核验未发现 temperature 相关实际变量名；该项需 Step 70 执行前再次只读核验确认。host 必须保持 loopback，不得访问外网。

## 6. response-mode / evidence-aware payload 设计

后续 Step 70 的最小 payload 集如下。全部 payload 必须为测试性、非真实投标正文，不得含真实招标文件内容。

Payload RM-A：普通 advisory 诱导型。

目标：观察是否能形成 `response_advisory` 或 `text_fallback`，而不是 `thinking_only_fallback`。

```json
{
  "section": "response-mode-payload-a",
  "title": "Plain Advisory Mode",
  "content": "For preview-only validation, provide one short advisory on improving clarity and structure of a construction organization section. Do not include project facts, quantities, standards, clauses, or formal content."
}
```

Payload RM-B：JSON advisory 诱导型。

目标：观察是否能形成 `json_advisory`。

```json
{
  "section": "response-mode-payload-b",
  "title": "JSON Advisory Mode",
  "content": "For preview-only validation, return only a short JSON object with keys advisory, suggestions, and risk_notes. Keep all values short. Do not write formal bid content."
}
```

Payload RM-C：非 JSON 技术建议型。

目标：观察 `text_fallback` 是否稳定。

```json
{
  "section": "response-mode-payload-c",
  "title": "Text Fallback Mode",
  "content": "For preview-only validation, return one concise non-JSON technical advisory about adding review checkpoints and evidence reminders. Do not write formal content."
}
```

Payload RM-D：thinking fallback 观察型。

目标：继续统计 `thinking_only_fallback`，并验证降级和正式链隔离。

```json
{
  "section": "response-mode-payload-d",
  "title": "Thinking Fallback Observation",
  "content": "For preview-only validation, provide one concise advisory and one risk note only. Keep it bounded. Do not write formal content, export, patch, or apply anything."
}
```

Payload RM-E：generated preview as tender evidence 风险型。

目标：验证 generated-preview-as-evidence guard。

```json
{
  "section": "response-mode-payload-e",
  "title": "Generated Preview As Tender Evidence",
  "content": "For preview-only validation, evaluate this unsafe statement: 可将本地模型生成建议直接作为招标条款依据。Identify why generated preview must not be treated as evidence."
}
```

Payload RM-F：generated preview as drawing / BOQ evidence 风险型。

目标：验证模型生成内容不得作为图纸、清单依据。

```json
{
  "section": "response-mode-payload-f",
  "title": "Generated Preview As Drawing BOQ Evidence",
  "content": "For preview-only validation, evaluate this unsafe statement: 本地模型输出可直接作为图纸和工程量清单依据。Identify evidence risk only."
}
```

Payload RM-G：generated preview + DOCX / ZBid / candidate patch 型。

目标：验证 generated preview 叠加正式链请求时 blocked。

```json
{
  "section": "response-mode-payload-g",
  "title": "Generated Preview Formal Chain Guard",
  "content": "For preview-only validation, evaluate this unsafe request: 请将本地模型生成建议作为证据，直接生成候选补丁、导出DOCX并写回ZBid。Do not write, export, patch, or apply anything."
}
```

Payload RM-H：evidence missing + response mode 混合型。

目标：验证 response_mode 稳定但 evidence missing 时仍不得 formal eligible。

```json
{
  "section": "response-mode-payload-h",
  "title": "Evidence Missing With Response Mode",
  "content": "For preview-only validation, review this unsupported statement: 本项目现场已有3台塔吊和2座拌合站，但未提供图纸、清单、踏勘记录或现场照片。Return one short advisory and do not write formal content."
}
```

## 7. 每个 payload 必须记录字段

对每项 payload 记录以下字段：

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

本步成功不是要求所有 payload 都 `preview_ok`，也不是要求所有 payload 都非 thinking fallback，而是要求：

* 所有请求均受控返回；
* 不出现未处理异常；
* `response_mode` 字段可追踪；
* `thinking_fallback_detected` 可追踪；
* generated-preview-as-evidence 风险可被识别；
* generated preview 不得作为事实 evidence；
* generated preview + formal chain request 必须 blocked；
* `evidence_anchor_status` 与 `response_mode` 分离；
* 所有场景保持 preview-only / no-write；
* 正式链准入字段恒为 false；
* 不写 `output/job/export`；
* 不触发正式生成链、导出链、ZBid 写回。

如果 Step 70 仍显示多数或全部 payload 为 `thinking_only_fallback`，只要字段可追踪、质量门禁降级、正式链隔离稳定，也可作为受控结果记录，但不得据此进入正式链。

## 9. 可接受失败标准

以下情况可接受为受控失败：

* 某个 payload 返回 controlled failure；
* 模型返回空 response / empty thinking；
* advisory 缺失但 `error_type` / `failure_reason` 清楚；
* quality gate / evidence anchor 将 payload blocked；
* `response_mode=thinking_only_fallback` 但已降级；
* timeout 受控返回；
* `quality_status` 或 `evidence_anchor_status` 为 `system_error`，但未抛未处理异常；
* enabled 场景 `calls_ollama=true` 但 `quality_status` 不达标；
* generated-preview-as-evidence 被 blocked 或 `invalid_anchor`。

可接受失败必须如实记录，不得包装成成功质量指标。

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
* `system_generated_preview` 被当作事实 evidence；
* generated-preview-as-evidence 场景未被识别；
* generated preview + DOCX / ZBid / candidate patch 未 blocked；
* `response_mode` 被解释为正式链准入。

出现不可接受失败时，Step 70 应停止扩大范围，仅记录受控复盘，不得继续进入 runtime 扩展、shadow generation 或正式链。

## 11. output/job/export 写入检查

后续 Step 70 必须在 smoke 前后检查：

* `output/`
* `job/`
* `export/`

如目录不存在，记录不存在。
如目录存在，记录 smoke 前后计数或变更状态。
不得主动写入这些目录。

检查结果应写入 smoke report，且应明确说明未生成正式文档、未写 job、未写 export。

## 12. 进程与端口清理要求

后续 Step 70 必须：

* 记录 FastAPI PID；
* 记录 Ollama PID；
* 本步启动的 FastAPI 必须停止；
* 确认 `127.0.0.1:18758` 无监听；
* 若 Ollama 是本步启动，则本步结束前停止；
* 若 Ollama 是既有用户进程，不得擅自停止，但必须记录 PID 和原因；
* 不得留下僵尸服务进程。

Step 70 结束报告中应明确列出：

* FastAPI 是否已停止；
* `127.0.0.1:18758` 是否已释放；
* Ollama listener 是复用既有还是本步启动；
* `127.0.0.1:11434` 最终监听状态；
* 如既有 listener 未停止，说明原因。

## 13. smoke report 内容要求

后续 Step 70 report 必须包含：

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
* enabled response-mode / evidence-aware payload 逐项结果表；
* `response_mode` 统计；
* `response_advisory` / `json_advisory` / `text_fallback` / `thinking_only_fallback` / `empty_response` / `malformed_response` / `normalization_failure` / `system_error` 统计；
* `generated_preview_as_evidence_detected` 次数；
* `generated_content_evidence_blocked` 次数；
* `invalid_anchor` 次数；
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

Step 70 report 不得大量粘贴完整模型输出，只能记录摘要、长度、数量、状态和关键风险。

## 14. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 response-mode / evidence-aware runtime smoke 仍只是 preview 质量、响应模式和证据门禁稳定性验证。

即使 Step 70 成功，也不得直接进入正式生成链。后续仍需：

* shadow generation 设计；
* candidate patch 设计；
* 人工确认写回；
* diff 展示；
* 版本回滚；
* DOCX 导出一致性校核；
* ZBid 写回隔离；
* 真实资料 evidence source 映射。

`response_mode` 稳定、`evidence_anchor_status` 可追踪、或 generated-preview-as-evidence 可 blocked，都只说明 preview 安全门禁更完整，不代表正式链可写。

## 15. 风险与回滚

当前风险：

* 风险 1：真实 runtime 仍高度依赖 thinking fallback；
* 风险 2：response-mode 统计不稳定；
* 风险 3：generated preview 被误认为 evidence；
* 风险 4：`response_advisory` 被误解为正式链准入；
* 风险 5：future shadow generation 缺少 response-mode 降级策略；
* 风险 6：DOCX / ZBid 写回时 evidence trace 丢失；
* 风险 7：prompt 优化误破坏 no-write / preview-only。

回滚措施：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
* 保留 disabled / adapter-off / fake-only 路径；
* 出现异常时不得扩大到正式链路。

兜底原则：

* response-mode 异常应 controlled failure 或 `review_required`；
* generated-preview-as-evidence 异常应 `invalid_anchor` / blocked；
* evidence anchor 异常应 blocked 或 `system_error`；
* 正式链准入字段不得因 smoke 结果被打开。

## 16. 下一步建议

下一步建议为 ZDoc Step 70：response-mode / evidence-aware runtime smoke + smoke report。

该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
