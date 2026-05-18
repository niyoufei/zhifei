# ZDoc response-mode prompt tuning guard test design

## 1. 阶段背景

本阶段为 ZDoc Step 73：response-mode prompt tuning guard + deterministic tests design。

前序阶段事实如下：

* Step 70 已完成 response-mode / evidence-aware runtime smoke + smoke report；
* Step 71 已完成 runtime smoke review + follow-up design；
* Step 72 已完成 response-mode prompt tuning + adapter-off schema follow-up design；
* Step 70 暴露真实 runtime 8/8 enabled payload 均为 `thinking_only_fallback`；
* `response_advisory` / `json_advisory` / `text_fallback` 在真实 runtime 下尚未出现；
* adapter-off literal payload 出现 controlled `illegal_field:content`；
* Step 73 目标是锁定后续 prompt tuning 实现前的 guard、测试、允许修改文件、失败分类和回滚边界；
* 本步不得实现代码。

本步为 docs-only response-mode prompt tuning guard + deterministic tests 设计步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 正式导出，不接 ZBid 正式写回。

## 2. 当前问题复述

当前主要问题如下：

* 真实 runtime 仍高度依赖 `thinking_only_fallback`；
* 普通 response 字段未稳定产出；
* JSON advisory 未稳定产出；
* text fallback 未稳定产出；
* adapter-off 与 enabled payload schema 存在兼容性差异；
* `status=ok` 不等于 response-mode 合格；
* `thinking_only_fallback` 不得进入 `shadow_candidate`、candidate patch、正式正文、DOCX 导出或 ZBid 写回。

这些问题的共同边界是：response-mode tuning 只能改善 preview advisory 的输出模式和可观测性，不能放开正式链准入，不能绕过 evidence anchor / input-risk / quality gate，也不能把 generated preview 当作 evidence。

## 3. prompt tuning guard 总体目标

后续实现必须满足以下总体目标：

* 优先诱导 `response_advisory`；
* 可选支持 `json_advisory`；
* 保留 `text_fallback` 兜底；
* 降低 `thinking_only_fallback` 占比；
* 不要求模型生成正式章节正文；
* 不要求生成 DOCX、Markdown、JSON 文件；
* 不要求写回；
* 不包含真实招标文件或敏感项目资料；
* 不绕过 quality gate、input-risk gate、evidence anchor；
* `formal_generation_allowed=false`；
* `shadow_candidate_allowed=false`；
* `writeback_allowed=false`；
* `export_allowed=false`；
* `zbid_writeback_allowed=false`。

prompt tuning guard 的成功标准不是“让所有 payload preview_ok”，而是让 response-mode 更可控、更可测、更少依赖 thinking fallback，并保持 preview-only / no-write / formal-ineligible。

## 4. prompt 模式 guard 设计

### A. response-first prompt

目标：普通 response 字段输出 1 条短 advisory。

guard 要求：

* 明确“只输出用户可见建议”；
* 明确“不要输出推理过程”；
* 明确“不写正式正文”；
* 明确“不导出、不写回、不应用”；
* 控制字数；
* 不得输出招标条款、图纸、清单、工程量等未核验证据内容。

建议后续 fake fixture 应验证：

* response 字段存在短 advisory 时，`response_mode=response_advisory`；
* response-first prompt 不应降低 evidence safety；
* response-first prompt 不得打开任何 formal chain flag；
* response-first prompt 如果输出正式正文，应 blocked 或 `review_required`。

### B. JSON-first prompt

目标：输出短 JSON 对象。

字段建议为：

* `advisory`
* `suggestions`
* `risk_notes`

guard 要求：

* 不生成 Markdown 文档；
* 不生成正式章节；
* 不写入任何系统；
* malformed JSON 必须 controlled failure 或 `text_fallback`。

建议后续 fake fixture 应验证：

* 合法 JSON advisory 可进入 `json_advisory`；
* fenced Markdown JSON 不应导致未处理异常；
* malformed JSON 应 controlled failure 或 `text_fallback`；
* JSON advisory 仍不得 formal eligible。

### C. text-fallback prompt

目标：非 JSON 技术建议文本稳定返回。

guard 要求：

* 内容必须短；
* 必须 preview-only；
* 不得输出正式正文；
* 不得虚构条款、图纸、清单、规范。

建议后续 fake fixture 应验证：

* 非 JSON 短 advisory 可进入 `text_fallback`；
* text fallback 仍需通过 quality gate；
* text fallback 含未核验证据时仍需 evidence anchor；
* text fallback 不得进入 `shadow_candidate`。

### D. evidence-aware prompt

目标：涉及条款、图纸、清单、规范、工程量时提示“需资料核验 / 未查明”。

guard 要求：

* 不臆断证据；
* 不把模型建议当证据；
* 不把 generated preview 作为 evidence。

建议后续 fake fixture 应验证：

* evidence-aware prompt 遇到 missing source 时进入 `review_required`；
* generated preview as evidence 仍为 `invalid_anchor` 或 blocked；
* evidence missing 不得 formal eligible；
* safe expression 不应被误认为证据充分。

## 5. output-options guard 设计

只读代码检查到的相关变量和参数：

* `ZDOC_OLLAMA_PREVIEW_MODEL`
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`
* real adapter generate payload 中存在 `options: {"num_predict": ...}`

只读代码检查未发现 temperature 环境变量；未确认当前 real adapter 是否支持 stop / format / response-only / JSON format 参数。相关项目需后续实现前再次只读核验确认。

output-options guard 应覆盖：

* `num_predict` 小值策略：避免长 thinking 输出占据主要结果；
* temperature 保守策略：如后续支持，应偏低以提升格式稳定性；
* timeout 保守策略：超时应 controlled failure；
* context 长度控制：限制 prompt、context_summary、section_text，避免过大 context 触发模型报错；
* stop / format / options 是否可用：实现前再次只读核验；
* 是否需要 response-only 模式：如支持，应先 fake-only 验证；
* 是否需要 JSON format 模式：如支持，应只用于 JSON-first prompt；
* 如何避免过大 context 触发模型报错：限制 payload 长度并记录 failure_reason；
* 如何避免长 thinking 输出占据主要结果：prompt 禁止推理过程，并由 response-mode guard 降级；
* 如何保证参数调整不破坏 no-write / preview-only：任何参数只影响 preview adapter 输出，不得触发写盘、导出或写回。

本步只设计，不修改配置。后续任何 output-options 调整都必须先走 fake-only deterministic tests，再单独授权 runtime smoke。

## 6. adapter-off schema guard 设计

Step 70 adapter-off 场景出现 `illegal_field:content` 是受控失败。

后续 adapter-off schema guard 应明确：

* adapter-off 场景出现 `illegal_field:content` 是受控失败；
* 后续应统一 disabled / adapter-off / enabled smoke payload schema；
* adapter-off payload 应使用 endpoint 兼容字段；
* 如果 endpoint 对 `content` 字段有限制，应在 tests 中固定该行为；
* adapter-off schema 差异不得被误判为 real transport 异常；
* adapter-off schema 修正不得影响 disabled、enabled、fake-only、real runtime 路径；
* 本步不得修改代码。

建议 endpoint-compatible smoke payload 固定为：

```json
{
  "request_id": "response-mode-payload-a",
  "section_title": "Response Advisory Probe",
  "section_text": "For preview-only validation, provide one short advisory...",
  "context_summary": "preview-only; do not write, export, patch, or apply."
}
```

后续 tests 应同时覆盖 compatible payload 与 illegal field payload，以证明 schema 收紧是受控行为，不是 runtime transport 失败。

## 7. response-mode 判定指标设计

后续实现或 smoke 应统计：

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

说明：

* 成功不要求完全消除 `thinking_only_fallback`；
* 但后续 smoke 应观察是否能出现至少部分非 thinking response mode；
* 非 thinking response mode 也不得进入正式链。

如果 response-mode 分布改善但 formal chain flags 仍恒 false，说明 preview 输出可观测性改善；如果 response-mode 改善伴随 evidence safety 降级，则不得接受。

## 8. deterministic tests 设计

后续实现必须覆盖以下 tests，本步不得运行 pytest：

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

测试边界：

* deterministic tests 必须使用 fake fixture / monkeypatch / dependency injection；
* 不得真实访问 `127.0.0.1:11434`；
* 不得运行 Ollama；
* 不得下载模型；
* 不得写 `output/job/export`；
* 不得触发正式生成链。

## 9. fake fixture 设计

后续 tests 应新增或扩展以下 fake fixtures：

* `response_first_prompt_fixture`；
* `json_first_prompt_fixture`；
* `text_fallback_prompt_fixture`；
* `thinking_heavy_prompt_fixture`；
* `empty_response_prompt_fixture`；
* `malformed_json_prompt_fixture`；
* `generated_preview_evidence_prompt_fixture`；
* `formal_section_attempt_prompt_fixture`；
* `docx_zbid_apply_attempt_prompt_fixture`；
* `adapter_off_compatible_payload_fixture`；
* `adapter_off_illegal_field_fixture`；
* `evidence_aware_missing_source_prompt_fixture`。

fixture 约束：

* deterministic tests 不得真实访问 `127.0.0.1:11434`；
* 不得运行 Ollama；
* 不得下载模型；
* 不得写 `output/job/export`；
* 不得触发正式生成链。

fixture 应覆盖三层：

* raw preview normalization；
* quality gate / evidence anchor metadata；
* safe endpoint payload validation。

这样可以同时证明 prompt tuning 不破坏 response-mode 分类、schema 校验和正式链隔离。

## 10. future implementation boundary

后续如进入实现，应先单独授权，原则上允许修改范围可包括：

* `backend/zhifei_autoplan/ollama_preview.py`；
* `backend/tests/test_ollama_preview.py`；
* `backend/tests/test_local_llm_preview_safe_endpoint.py`；
* `backend/zhifei_autoplan/evidence_anchor.py`；
* `backend/tests/test_evidence_anchor.py`；
* `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
* `backend/tests/test_preview_advisory_quality_gate.py`。

原则上不新增新 helper 文件。原则上不修改 endpoint。如必须修改 endpoint schema，需 ChatGPT 单独授权。

不得修改正式生成链、正式导出链、ZBid 写回链。不得写 `output/job/export`。不得进入 runtime smoke、shadow generation 或正式生成链。

## 11. future runtime smoke 设计

后续顺序建议：

* Step 74：response-mode prompt tuning fake-only implementation + deterministic tests；
* Step 75：implementation stage review；
* Step 76：response-mode runtime smoke plan refresh；
* Step 77：response-mode runtime smoke + smoke report；
* Step 78：runtime smoke review；
* 之后才可讨论 shadow generation design。

Step 77 之前不得启动 runtime smoke。Step 77 即使成功，也只证明 response-mode preview runtime 受控，不代表可进入正式链。

## 12. 与 quality gate / input-risk / evidence anchor 的关系

prompt tuning 不能绕过 evidence anchor。prompt tuning 不能绕过 input-risk gate。prompt tuning 不能绕过 quality gate。

具体关系如下：

* `response_advisory` / `json_advisory` 也必须 evidence-aware；
* generated preview 仍不得作为 evidence；
* evidence missing 仍不得 formal eligible；
* generated-preview-as-evidence 仍必须 `invalid_anchor` 或 blocked；
* input-risk blocked 仍必须 blocked；
* `thinking_only_fallback` 仍不得进入 `shadow_candidate`；
* all formal chain flags remain false。

response-mode 只回答“输出来自哪里”，quality gate 评估 preview advisory 质量，input-risk gate 判断输入风险，evidence anchor 判断事实证据状态。四者不能互相覆盖。

## 13. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 response-mode prompt tuning 仍属于 preview runtime 稳定性阶段。未完成 response-mode 稳定、evidence anchor、quality gate、input-risk gate、shadow generation、candidate patch、人工确认、diff、rollback、DOCX 导出一致性、ZBid 写回隔离前，不得进入正式链。

即使后续 fake-only tests 证明 response-first / JSON-first prompt 可分类为 `response_advisory` / `json_advisory`，也不得将其解释为正式生成链准入。

## 14. 风险与回滚

风险：

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
* prompt tuning 异常应 fail-closed；
* response-mode 异常应 controlled failure 或 `review_required`；
* evidence anchor 异常应 blocked 或 `system_error`；
* formal chain flags 必须继续恒 false。

## 15. 当前阶段结论

本阶段仅完成 response-mode prompt tuning guard + deterministic tests 的 docs-only 设计，未实现代码，未运行测试，未启动服务，未进入 runtime smoke、shadow generation 或正式生成链。

该设计将后续工作限定为 fake-only prompt tuning guard 与 deterministic tests：先证明 response-first、JSON-first、text-fallback、thinking-heavy、adapter-off schema、generated-preview evidence、formal chain request 等场景受控，再单独授权 runtime smoke。

## 16. 下一步建议

下一步建议为 ZDoc Step 74：response-mode prompt tuning fake-only implementation + deterministic tests。

不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
