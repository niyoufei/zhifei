# ZDoc Step 79: response-mode second-round prompt tuning design

## 1. 阶段背景

Step 74 已完成 response-mode prompt tuning fake-only implementation + deterministic tests。Step 75 已完成 fake-stage review。Step 76 已完成 runtime smoke plan refresh。Step 77 已完成 runtime smoke。Step 78 已完成 runtime smoke review + follow-up design。

Step 77 首次观察到 `text_fallback=1`。Step 77 `thinking_only_fallback` 从 Step 70 的 8/8 改善为 4/6。Step 77 JSON-first payload 为 `malformed_response`。Step 77 `response_advisory` / `json_advisory` 仍未出现。

当前不得进入 runtime smoke、shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。Step 79 目标是设计二轮 prompt tuning 方案，为后续 fake-only implementation 做前置设计。本步不得实现代码。

## 2. 当前 runtime 结果复述

Step 77 摘要如下：

* enabled 6/6 HTTP 200；
* `response_advisory=0`；
* `json_advisory=0`；
* `text_fallback=1`；
* `thinking_only_fallback=4`；
* `malformed_response=1`；
* PT-A 为 `thinking_only_fallback`；
* PT-B 为 `malformed_response`；
* PT-C 为 `text_fallback`；
* PT-D / PT-E / PT-F 为 `thinking_only_fallback`；
* generated-preview-as-evidence 回归仍有效；
* `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 全部恒 false。

该结果说明 response-mode prompt tuning 已开始改善真实 runtime 分布，但仍没有形成稳定的普通 response advisory 或 JSON advisory。二轮 tuning 的重点应放在更短、更明确、更少推理诱因的 prompt，以及更严格的 JSON 输出模板。

## 3. 二轮 tuning 总体目标

二轮 tuning 目标如下：

* 继续降低 `thinking_only_fallback` 占比；
* 提高 `response_advisory` 出现概率；
* 提高 `json_advisory` 稳定性；
* 保持 `text_fallback` 作为可控兜底；
* 解决 JSON-first `malformed_response` 问题；
* 保持 adapter-off schema 受控；
* 不绕过 quality gate、input-risk gate、evidence anchor；
* 不诱导正式正文；
* 不触发正式链、导出链、ZBid 写回；
* 所有正式链准入字段继续恒 false。

二轮 tuning 的成功标准不是完全消除 thinking fallback，也不是让所有 payload `preview_ok`。它只要求 response-mode 更可观测、更少依赖 thinking fallback，并保持 preview-only / no-write / formal-ineligible。

## 4. response-first 二轮设计

后续 response-first prompt 应更短、更直接，减少推理诱因。

建议设计原则如下：

* 使用 `Return only one short advisory sentence.`；
* 明确 `Do not explain reasoning.`；
* 明确 `Do not include chain-of-thought.`；
* 明确 `Do not write a formal section.`；
* 明确 `Do not cite unprovided evidence.`；
* 明确 `If evidence is missing, say it needs verification.`；
* 避免使用 `review`、`analyze`、`evaluate` 等可能诱发长推理的词；
* 输出长度上限应明确；
* 输出仍必须 preview-only。

二轮 response-first prompt 可优先采用单句指令和短上下文，避免把任务描述成评审、论证或分析。目标是诱导模型把用户可见建议放入普通 response，而不是让 thinking 内容成为唯一可用输出。

## 5. JSON-first 二轮设计

针对 PT-B `malformed_response`，二轮 JSON-first 应设计更严格 JSON 输出策略：

* 要求只返回单行 JSON；
* 明确禁止 Markdown code fence；
* 明确禁止解释性文字；
* 明确字段固定为 `advisory`、`suggestions`、`risk_notes`；
* `suggestions` 和 `risk_notes` 可为空数组；
* `advisory` 为短字符串；
* JSON 不得包含正式正文；
* JSON 不得包含证据臆断；
* malformed JSON 仍必须 controlled failure 或 `text_fallback`；
* 不得为追求 `json_advisory` 而放宽 evidence safety。

建议二轮 JSON 模板控制为单层对象，例如：

```json
{"advisory":"Use a short preview-only advisory.","suggestions":[],"risk_notes":[]}
```

后续实现不得要求生成 JSON 文件，不得生成 Markdown 文档，不得把 JSON advisory 解释为正式章节或正式链准入。

## 6. text-fallback 稳定化设计

基于 PT-C 已出现 `text_fallback`，二轮 tuning 应继续强化 text-fallback 的稳定性：

* 允许短非 JSON 技术建议；
* 不要求正式章节；
* 不要求条款、图纸、清单、规范；
* 如涉及事实性内容，必须提示需资料核验；
* `text_fallback` 可作为 preview advisory；
* `text_fallback` 不得进入 `shadow_candidate`；
* `text_fallback` 不得进入正式链。

text-fallback 的定位是可控兜底，不是正文生成能力。后续 smoke 应通过多个短 advisory payload 验证 `text_fallback` 是否稳定，同时确认 evidence anchor、quality gate 和 input-risk gate 仍然生效。

## 7. thinking fallback 降级策略

`thinking_only_fallback` 仍可作为 preview-only fallback，但必须继续降级：

* `thinking_only_fallback` 必须 `review_required` 或更保守；
* `thinking_only_fallback` 不得进入 candidate patch；
* `thinking_only_fallback` 不得进入正式正文；
* `thinking_only_fallback` 不得触发 DOCX 导出；
* `thinking_only_fallback` 不得写回 ZBid；
* 后续 runtime smoke 应持续统计 `thinking_fallback_detected`；
* 即使 thinking fallback 质量较好，也不得作为正式链准入依据。

如果二轮 prompt tuning 后 thinking fallback 仍高频出现，结果仍应被解释为 preview runtime 稳定性不足，而不是进入 shadow generation 的依据。

## 8. adapter-off schema 二轮设计

Step 77 已证明 adapter-off compatible payload 正常，`illegal_field:content` 仍为 controlled failure。

二轮 adapter-off schema 设计应保持以下边界：

* 后续 payload 应统一 compatible schema；
* literal `content` 字段如不兼容，应在 adapter-off 测试中避免用于正常路径；
* illegal field 测试继续保留；
* adapter-off schema 失败不得被误判为 real runtime failure；
* 不得为了兼容 smoke 而放松安全字段校验。

后续正常 payload 应优先使用 endpoint-compatible 字段，例如 `request_id`、`section_title`、`section_text`、`context_summary`。非法字段 fixture 应保留 `content` 或其他 formal/write 类字段，用于证明 controlled failure。

## 9. output-options 二轮设计

只读代码检查到的相关配置或参数如下：

* `ZDOC_OLLAMA_PREVIEW_MODEL`；
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`；
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`；
* `ZDOC_OLLAMA_PREVIEW_BASE_URL`；
* real adapter generate payload 中存在 `options: {"num_predict": ...}`；
* prompt mode 由 request 内容中的 `response_first` / `json_first` / `text_fallback` 等标记触发。

只读检查未确认已有 temperature 环境变量、stop tokens、`format=json`、response-only 模式或可区分 response-first 与 JSON-first 的 options。相关项目需后续实现前再次只读核验确认。

二轮 output-options 设计应覆盖：

* `num_predict` 是否需要更小；
* temperature 是否保持低值；
* timeout 是否保持短值；
* context 是否进一步压缩；
* stop tokens 是否可用于阻止长 thinking；
* 是否支持 `format=json`；
* 是否可区分 response-first 与 JSON-first 的 options；
* options 调整不得破坏 no-write / preview-only；
* options 调整不得绕过 evidence anchor。

任何 options 调整都必须先通过 fake-only deterministic tests，再单独授权 runtime smoke。不得为了改善 response mode 而扩大生成长度、访问外网、写盘、导出或写回。

## 10. prompt mode data contract 设计

后续可稳定输出或记录以下字段：

* `prompt_mode`；
* `prompt_profile`；
* `prompt_version`；
* `response_mode`；
* `response_mode_confidence`；
* `fallback_reason`；
* `prompt_tuning_applied`；
* `prompt_tuning_warnings`；
* `json_mode_requested`；
* `response_first_requested`；
* `text_fallback_allowed`；
* `evidence_aware_prompt_applied`；
* `adapter_schema_mode`；
* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`。

所有正式链字段继续恒 false。

这些字段只用于 preview metadata 和 smoke 统计，不得成为正式链准入。`prompt_mode` 与 `response_mode` 也不得覆盖 evidence anchor、quality gate 或 input-risk gate。

## 11. deterministic tests 设计

后续 Step 80 或 Step 74 后续实现必须覆盖以下 tests，本步不得运行 pytest：

* second-round response-first prompt fixture；
* second-round JSON-first prompt fixture；
* single-line JSON without code fence fixture；
* JSON with Markdown fence -> controlled malformed 或 stripping policy；
* JSON plus explanation -> controlled malformed 或 `text_fallback`；
* response-first no reasoning fixture；
* response-first missing evidence fixture；
* text-fallback stabilized fixture；
* thinking-heavy fixture remains `review_required`；
* adapter-off compatible schema fixture；
* adapter-off illegal field fixture；
* prompt_mode metadata fixture；
* all formal chain flags remain false；
* generated-preview-as-evidence 回归；
* evidence anchor / quality gate / input-risk 回归；
* safe endpoint 回归。

deterministic tests 必须使用 fake fixture / monkeypatch / dependency injection。不得真实访问 `127.0.0.1:11434`，不得运行 Ollama，不得下载模型，不得写 `output/job/export`，不得触发正式生成链。

## 12. fake fixture 设计

后续 tests 应新增或扩展以下 fake fixtures：

* `second_round_response_first_fixture`；
* `second_round_json_first_valid_fixture`；
* `json_first_code_fence_fixture`；
* `json_first_explanatory_text_fixture`；
* `response_first_short_sentence_fixture`；
* `response_first_missing_evidence_fixture`；
* `text_fallback_stable_fixture`；
* `prompt_mode_metadata_fixture`；
* `adapter_schema_compatible_fixture`；
* `adapter_schema_illegal_field_fixture`；
* `evidence_aware_prompt_fixture`。

这些 fixtures 应覆盖有效输出、格式异常、缺证据、formal chain attempt、adapter schema 和 generated-preview-as-evidence 回归。所有 fixture 都必须保持 fake-only，不得访问真实 Ollama runtime。

## 13. 后续实现边界设计

后续如进入实现，应先单独授权。建议允许修改范围如下：

* `backend/zhifei_autoplan/ollama_preview.py`；
* `backend/tests/test_ollama_preview.py`；
* `backend/tests/test_local_llm_preview_safe_endpoint.py`；
* 必要时 `backend/zhifei_autoplan/evidence_anchor.py`；
* 必要时 `backend/tests/test_evidence_anchor.py`；
* 必要时 `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
* 必要时 `backend/tests/test_preview_advisory_quality_gate.py`。

原则上不新增新 helper 文件。原则上不修改 endpoint。如必须修改 endpoint schema，需 ChatGPT 单独授权。

不得修改正式生成链、正式导出链、ZBid 写回链。不得写 `output/job/export`。

## 14. 后续 runtime smoke 顺序

建议后续顺序如下：

* Step 80：second-round response-mode prompt tuning fake-only implementation + deterministic tests；
* Step 81：implementation stage review；
* Step 82：second-round response-mode runtime smoke plan refresh；
* Step 83：second-round response-mode runtime smoke + report；
* Step 84：runtime smoke review；
* 再讨论 shadow generation design。

如果决定不新增 Step 80，也可按当前编号体系调整，但不得跳过 fake-only implementation 和 stage review。

## 15. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但二轮 response-mode prompt tuning 仍属于 preview runtime 稳定性阶段。未完成 response-mode 稳定、evidence anchor、quality gate、input-risk gate、shadow generation、candidate patch、人工确认、diff、rollback、DOCX 导出一致性、ZBid 写回隔离前，不得进入正式链。

即使二轮 tuning 后出现 `response_advisory` 或 `json_advisory`，也只代表 preview 输出模式改善，不代表正式链准入。所有正式链准入字段必须继续恒 false。

## 16. 风险与回滚

当前风险如下：

* 风险 1：为降低 thinking fallback 诱导输出过短，导致 advisory 低质；
* 风险 2：JSON-first 继续输出 malformed JSON；
* 风险 3：JSON prompt 削弱 evidence safety；
* 风险 4：response-first 过度简化导致遗漏风险；
* 风险 5：`text_fallback` 被误认为正式正文能力成熟；
* 风险 6：adapter-off schema 差异导致误判；
* 风险 7：prompt tuning 破坏 no-write / preview-only。

回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路，不得进入 runtime smoke、shadow generation、candidate patch、DOCX 导出或 ZBid 写回。

## 17. 当前阶段结论

本阶段仅完成 second-round response-mode prompt tuning 的 docs-only 设计，未实现代码，未运行测试，未启动服务，未进入 runtime smoke、shadow generation 或正式生成链。

## 18. 下一步建议

下一步建议为 ZDoc Step 80：second-round response-mode prompt tuning fake-only implementation + deterministic tests。不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
