# ZDoc response-mode prompt tuning design

## 1. 阶段背景

本阶段为 ZDoc Step 72：response-mode prompt tuning + adapter-off schema follow-up design。

前序阶段事实如下：

* Step 70 已完成 response-mode / evidence-aware runtime smoke + smoke report；
* Step 71 已完成 runtime smoke review + follow-up design；
* Step 70 enabled payload 8/8 HTTP 200、8/8 `status=ok`、8/8 `calls_ollama=true`；
* Step 70 generated-preview-as-evidence 相关场景可 blocked / `invalid_anchor`；
* Step 70 正式链准入字段全部恒为 false；
* 但 Step 70 显示 enabled payload 8/8 均为 `thinking_only_fallback`；
* `response_advisory` / `json_advisory` / `text_fallback` 在真实 runtime 下仍未出现；
* adapter-off literal payload 出现 controlled `illegal_field:content`；
* 当前不得进入 runtime smoke、shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回；
* Step 72 目标是设计 response-mode prompt tuning、output-options、payload schema follow-up 与后续 deterministic tests 边界；
* 本步不得实现代码。

本步为 docs-only 设计步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 正式导出，不接 ZBid 正式写回。

## 2. 当前问题复述

当前存在两个主要问题。

问题 1：response-mode 真实 runtime 不稳定。

* 真实 runtime 8/8 enabled payload 均为 `thinking_only_fallback`；
* 说明 `qwen3:0.6b` 在当前 prompt / options / payload 下普通 response 字段未稳定产出；
* `status=ok` 不等于 response mode 合格；
* `thinking_only_fallback` 不得进入 `shadow_candidate` 或 formal chain。

该问题不是 transport 不通，也不是 endpoint 不返回，而是模型输出模式仍高度依赖 thinking fallback。后续需要通过 prompt tuning 和 output-options 设计，观察是否能让 advisory 进入普通 response、JSON response 或稳定 text fallback。

问题 2：adapter-off payload schema 不一致。

* adapter-off 场景 HTTP 200，但返回 controlled `illegal_field:content`；
* 说明 adapter-off 路径对 literal payload 字段更严格；
* 该问题未造成正式链风险；
* 但后续 smoke 应统一 payload schema，避免 adapter-off 与 enabled 场景因字段不一致造成解释偏差。

只读代码核验显示 safe endpoint enabled/fake-only 路径更偏向 `context_summary`、`request_id`、`section_text`、`section_title` 等字段。后续 smoke payload 应尽量使用 endpoint-compatible schema。

## 3. prompt tuning 目标

后续 prompt tuning 的目标如下：

* 降低 `thinking_only_fallback` 依赖；
* 尽量诱导模型在普通 response 字段输出短 advisory；
* 支持 JSON advisory 场景稳定输出 `advisory` / `suggestions` / `risk_notes`；
* 支持 `text_fallback` 场景稳定输出短文本；
* 保持 preview-only；
* 不要求正式章节正文；
* 不要求 DOCX / Markdown / JSON 文件生成；
* 不要求写回；
* 不包含真实招标文件或敏感项目资料；
* 不破坏 no-write / evidence anchor / quality gate / input-risk gate。

prompt tuning 的评价重点不是追求 `preview_ok`，而是观察 response mode 分布是否改善、fallback 是否减少、evidence safety 是否继续 fail-closed、正式链准入字段是否继续恒 false。

## 4. prompt tuning 分层设计

### A. response-first prompt

目标：让模型直接在 response 中输出 1 条短 advisory。

要求：

* 明确“仅输出用户可见建议”；
* 明确“不要输出推理过程”；
* 明确“不写正式正文”；
* 明确“不导出、不写回、不应用”；
* 控制字数和结构。

建议 prompt 方向：

```text
Return only one user-visible advisory sentence.
Do not include reasoning, analysis, hidden thoughts, or drafting process.
Do not write a formal bid section.
Do not export, patch, apply, or write back anything.
Keep it under 60 words.
```

该模式的期望 response-mode 是 `response_advisory`。如果模型仍只给 thinking，则应继续降级为 `thinking_only_fallback` 并保持 `review_required`。

### B. JSON-first prompt

目标：让模型输出短 JSON 对象。

建议字段：

* `advisory`
* `suggestions`
* `risk_notes`

要求：

* 不要求保存为文件；
* 不生成 Markdown 文档；
* 不生成正式章节；
* 不写入任何系统。

建议 prompt 方向：

```text
Return only a compact JSON object with keys advisory, suggestions, and risk_notes.
Use short string or short array values.
Do not include Markdown fences.
Do not write formal bid content.
Do not export, patch, apply, or write back anything.
```

该模式的期望 response-mode 是 `json_advisory`。如果 JSON malformed，应进入 controlled failure 或 `text_fallback`，不得穿透异常。

### C. text-fallback prompt

目标：允许普通非 JSON 技术建议文本稳定返回。

要求：

* 内容短；
* 明确 preview-only；
* 不输出正式正文；
* 不虚构条款、图纸、清单、规范。

建议 prompt 方向：

```text
Provide a concise non-JSON technical advisory for preview-only review.
Do not include project-specific facts, tender clauses, drawing references, BOQ quantities, or standard numbers unless evidence is provided.
Do not write formal content.
```

该模式的期望 response-mode 是 `text_fallback` 或 `response_advisory`。若涉及证据缺失，应继续由 evidence anchor 和 input-risk gate 降级。

### D. evidence-aware prompt

目标：如涉及条款、图纸、清单、规范、工程量，应提示“需资料核验 / 未查明”。

要求：

* 不臆断证据；
* 不把模型建议当证据；
* 不把 generated preview 作为 evidence。

建议 prompt 方向：

```text
If the input mentions tender clauses, drawings, BOQ, standards, quantities, site conditions, schedule, cost, or scoring criteria without evidence, mark it as requiring verification.
Do not invent evidence.
Do not treat model-generated advice as evidence.
```

该模式的期望不是放行，而是使 response 更清晰、更短、更适合 preview，同时继续保留 evidence anchor / input-risk / quality gate 的保守判断。

## 5. output-options 设计

只读代码检查到的相关变量和参数：

* `ZDOC_OLLAMA_PREVIEW_MODEL`
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`
* generate payload 中存在 `options: {"num_predict": ...}`

只读代码检查未发现 temperature 环境变量；未确认当前 real adapter 是否支持 stop / format / response-only / JSON format 运行参数。以上项目需后续实现前再次只读核验确认。

后续 output-options 设计应覆盖：

* `num_predict` 小值策略：继续采用保守短输出，避免长 thinking 占据主要结果；
* temperature 保守策略：若后续代码支持，应偏低以提升格式稳定性；
* timeout 保守策略：继续使用短 timeout，超时应 controlled failure；
* context 长度控制：压缩 prompt 和 payload，避免过大 context 触发模型报错；
* stop / format / options 是否可用：实现前再次只读核验；
* 是否需要 response-only 模式：如 Ollama 或模型支持，应单独设计并 fake-only 验证；
* 是否需要 JSON format 模式：如可用，应只用于 JSON-first prompt，且不得保存文件；
* 如何避免过大 context 触发模型报错：限制 context_summary 与 section_text 长度；
* 如何避免长 thinking 输出占据主要结果：prompt 中明确“不要输出推理过程”，并以 response-mode gate 继续降级 thinking fallback。

说明：

* 本步只设计，不修改配置；
* 后续实现必须通过 fake-only tests 验证；
* 后续 runtime smoke 必须单独授权。

## 6. response-mode 成功指标设计

后续评估指标应至少包括：

* `response_advisory` 数量；
* `json_advisory` 数量；
* `text_fallback` 数量；
* `thinking_only_fallback` 数量；
* `empty_response` 数量；
* `malformed_response` 数量；
* `normalization_failure` 数量；
* `response_mode_confidence` 分布；
* `response_mode_review_required` 次数；
* `thinking_fallback_detected` 次数；
* `generated_preview_as_evidence_detected` 次数；
* `evidence_anchor_status` 分布；
* `quality_status` 分布；
* formal chain flags 是否恒 false。

成功不要求完全消除 `thinking_only_fallback`，但应观察是否能出现至少部分非 thinking response mode。若仍 8/8 或多数 payload 为 `thinking_only_fallback`，说明 prompt tuning 或 output-options 仍需继续迭代。

任何成功指标都不得解释为正式链准入。即使出现 `response_advisory` 或 `json_advisory`，也必须继续经过 evidence anchor、input-risk gate、quality gate 和人工后续流程。

## 7. adapter-off schema follow-up 设计

Step 70 adapter-off 场景出现 `illegal_field:content` 是 controlled failure。该结果说明字段校验受控，没有触发 real runtime，也没有触发正式链风险。

后续需要统一 smoke payload schema：

* disabled / adapter-off / enabled 的 payload 应尽可能采用 endpoint 兼容字段；
* 如果 endpoint 只允许 `section_title` / `section_text` / `context_summary` / `request_id` 等字段，应按代码实际校验设计 payload；
* adapter-off 路径不应因测试 payload 误触字段错误而影响对功能状态的判断；
* 后续 deterministic tests 应覆盖 adapter-off payload schema；
* 本步不得修改代码。

建议后续 smoke 使用统一结构：

```json
{
  "request_id": "response-mode-payload-a",
  "section_title": "Response Advisory Probe",
  "section_text": "For preview-only validation...",
  "context_summary": "preview-only runtime smoke; do not write, export, patch, or apply."
}
```

如后续需要保留用户展示层的 `section` / `title` / `content` 结构，应在 smoke 执行脚本中明确映射到 endpoint-compatible 字段，不应直接把 literal payload 传入 enabled/fake-only endpoint。

## 8. deterministic tests 设计

后续实现前必须覆盖以下 tests，本步不得运行 pytest：

* response-first prompt fixture -> `response_mode=response_advisory`；
* JSON-first prompt fixture -> `response_mode=json_advisory`；
* text-fallback prompt fixture -> `response_mode=text_fallback`；
* thinking-heavy fixture -> `response_mode=thinking_only_fallback` 且 `review_required`；
* empty response fixture -> controlled failure；
* malformed JSON fixture -> controlled failure 或 `text_fallback`；
* prompt output contains generated-preview-as-evidence -> `invalid_anchor` / blocked；
* prompt attempts formal section -> blocked 或 `review_required`；
* prompt attempts DOCX / ZBid / apply -> blocked；
* adapter-off compatible payload fixture；
* adapter-off illegal field fixture -> controlled failure；
* evidence-aware prompt with missing source -> `review_required`；
* all formal chain flags remain false；
* existing evidence anchor / quality gate / input-risk / safe endpoint tests 不回归。

测试必须使用 fake fixture / monkeypatch / dependency injection。不得真实访问 `127.0.0.1:11434`，不得运行 Ollama，不得下载模型，不得写 `output/job/export`，不得触发正式生成链。

## 9. future implementation boundary

后续如进入实现，应先单独授权，原则上允许修改范围可包括：

* `backend/zhifei_autoplan/ollama_preview.py`；
* `backend/tests/test_ollama_preview.py`；
* `backend/tests/test_local_llm_preview_safe_endpoint.py`；
* `backend/zhifei_autoplan/evidence_anchor.py`；
* `backend/tests/test_evidence_anchor.py`；
* `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
* `backend/tests/test_preview_advisory_quality_gate.py`。

原则上不新增新 helper 文件。原则上不修改 endpoint。如必须修改 endpoint schema，需 ChatGPT 单独授权。

不得修改正式生成链、正式导出链、ZBid 写回链。不得写 `output/job/export`。不得将 prompt tuning 作为进入 shadow generation 或正式链的依据。

## 10. future runtime smoke plan 设计

后续建议顺序：

* Step 73：response-mode prompt tuning guard + deterministic tests design 或 fake-only implementation；
* Step 74：response-mode prompt tuning fake-only implementation + deterministic tests；
* Step 75：implementation stage review；
* Step 76：response-mode runtime smoke plan refresh；
* Step 77：response-mode runtime smoke + smoke report；
* 之后才可讨论 shadow generation design。

如果 Step 73 选择 docs-only design，则 Step 74 再进入受控实现。如果 Step 73 被单独授权为 fake-only implementation，也必须限定文件范围、只跑授权 deterministic tests、不得启动服务、不得运行 Ollama、不得进入 runtime smoke。

## 11. 与 evidence anchor / quality gate 的关系

prompt tuning 不能绕过 evidence anchor。prompt tuning 不能绕过 input-risk gate。prompt tuning 不能绕过 quality gate。

集成关系如下：

* `response_advisory` / `json_advisory` 也必须 evidence-aware；
* generated preview 仍不得作为 evidence；
* evidence missing 仍不得 formal eligible；
* input-risk blocked 仍必须 blocked；
* generated-preview-as-evidence 仍必须 `invalid_anchor` 或 blocked；
* thinking fallback 仍不得进入 `shadow_candidate`；
* all formal chain flags remain false。

因此，prompt tuning 只能改善 response-mode 分布和 advisory 可读性，不能改变 preview-only / no-write / formal-ineligible 边界。

## 12. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 response-mode prompt tuning 仍属于 preview runtime 稳定性阶段。未完成 response-mode 稳定、evidence anchor、quality gate、input-risk gate、shadow generation、candidate patch、人工确认、diff、rollback、DOCX 导出一致性、ZBid 写回隔离前，不得进入正式链。

即使后续 runtime smoke 出现 `response_advisory` 或 `json_advisory`，也仅说明 response-mode 有改善，不代表可以写入正式章节、生成 candidate patch、导出 DOCX 或写回 ZBid。

## 13. 风险与回滚

当前风险：

* 风险 1：为降低 thinking fallback 而诱导模型输出过长或正式正文；
* 风险 2：JSON prompt 导致模型输出伪 JSON 或格式不稳定；
* 风险 3：response-first prompt 弱化 evidence safety；
* 风险 4：adapter-off schema 差异导致 smoke 结果误判；
* 风险 5：`response_advisory` 被误解为正式链准入；
* 风险 6：prompt tuning 破坏 no-write / preview-only；
* 风险 7：generated preview 再次被误认为 evidence。

回滚措施：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

* 保留 disabled / adapter-off / fake-only 路径。

异常边界：

* 出现异常时不得扩大到正式链路；
* prompt tuning 失败应保持 controlled failure、`review_required` 或 blocked；
* generated preview 不得成为 evidence；
* formal chain flags 必须继续恒 false。

## 14. 当前阶段结论

本阶段仅完成 response-mode prompt tuning + adapter-off schema follow-up 的 docs-only 设计，未实现代码，未运行测试，未启动服务，未进入 runtime smoke、shadow generation 或正式生成链。

Step 70 已证明 generated-preview-as-evidence guard 在真实 runtime 下初步有效，但 `thinking_only_fallback` 仍为真实 runtime 主路径。Step 72 的结论是：后续应先做 response-first / JSON-first / text-fallback / evidence-aware prompt tuning 的 fake-only 设计与测试，再单独授权 runtime smoke；不得直接进入 shadow generation 或正式生成链。

## 15. 下一步建议

下一步建议为 ZDoc Step 73：response-mode prompt tuning guard + deterministic tests design，或直接进入受控 fake-only implementation 前置设计。

不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
