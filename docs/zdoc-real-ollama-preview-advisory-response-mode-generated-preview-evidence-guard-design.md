# ZDoc response-mode generated-preview evidence guard design

## 1. 阶段背景

本阶段执行 ZDoc Step 66：response-mode / generated-preview-as-evidence guard design。

前序阶段事实如下：

* Step 64 已完成 evidence-aware multi-payload smoke；
* Step 65 已完成 evidence-aware smoke review + response-mode follow-up design；
* Step 64 显示 enabled payload 8/8 均为 `status=ok`、`calls_ollama=true`；
* Step 64 同时显示 8/8 enabled payload 均为 `thinking_only_fallback`；
* EA-G 未把 generated preview 当作 evidence，但 `evidence_anchor_status` 为 `not_required`；
* 当前 response-mode 稳定性与 generated-preview-as-evidence 门禁仍未闭环；
* 当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回；
* Step 66 目标是锁定 response-mode guard 与 generated-preview-as-evidence guard 的规则、数据契约、测试设计、允许修改文件和回滚边界；
* 本步不得实现代码。

本步为 docs-only 设计步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 导出，不接 ZBid 正式写回。

## 2. 当前缺口复述

当前存在两个主要缺口。

缺口 1：response-mode high dependency。

* 真实 runtime 8/8 enabled payload 仍依赖 `thinking_only_fallback`；
* 普通 response、JSON response、结构化 advisory 未证明稳定；
* `thinking_only_fallback` 只能作为 preview-only fallback；
* `thinking_only_fallback` 不得进入 `shadow_candidate` 或 formal chain。

该缺口不是本地 Ollama transport 不通，也不是 safe endpoint 不返回，而是模型真实 runtime 输出模式仍高度依赖 fallback。后续如果忽略 response-mode，只看 HTTP 200、`status=ok` 或 advisory 是否存在，可能误判模型质量稳定。

缺口 2：generated-preview-as-evidence guard。

* generated preview 不能作为 `tender_document`、`drawing`、`boq`、`scoring_criteria` 等事实证据；
* EA-G 未失控，但 `evidence_anchor_status=not_required` 可能偏弱；
* 如果输入要求“将模型生成建议作为招标条款或图纸依据”，应至少 `review_required`，必要时 `invalid_anchor` 或 `blocked`；
* `generated_content_must_not_be_evidence` 必须稳定透出。

该缺口属于 evidence anchor 的 invalid source 子类。模型生成内容可以是 suggestion source，但不能是事实证据来源。

## 3. response-mode 分类设计

后续应稳定识别以下 response mode：

* `response_advisory`：普通 response 字段形成 advisory；
* `json_advisory`：JSON response 提取 advisory / suggestions / risk_notes；
* `text_fallback`：非 JSON 技术建议文本 fallback；
* `thinking_only_fallback`：response 为空或不可用，仅 thinking 可形成 bounded advisory；
* `empty_response`：response 与 thinking 均为空；
* `malformed_response`：响应结构异常；
* `normalization_failure`：normalization 异常；
* `system_error`：系统异常。

分类优先级与约束：

* `response_advisory` / `json_advisory` 优先级高于 `thinking_only_fallback`；
* `thinking_only_fallback` 必须降级；
* `empty_response` / `malformed_response` / `normalization_failure` 必须 controlled failure 或 `review_required`；
* `status=ok` 不等于 response_mode 合格；
* response_mode 不得触发正式链准入字段。

response-mode 应成为 preview quality metadata 的独立维度。后续 smoke 和 deterministic tests 应同时记录 `response_mode`、`response_source`、`preview_mode`、fallback reason 和 quality/evidence gate 的联动结果。

## 4. response-mode guard 设计

后续 response-mode guard 应满足：

* `thinking_only_fallback` 默认不得高于 `review_required`；
* `thinking_only_fallback` + evidence missing 必须 `review_required` 或 `blocked`；
* `thinking_only_fallback` + input-risk 必须更保守；
* `thinking_only_fallback` + generated-preview-as-evidence 请求必须 `blocked` 或 `invalid_anchor`；
* `response_advisory` / `json_advisory` 也必须经过 quality gate、input-risk gate、evidence anchor；
* future shadow generation 只能考虑 `response_advisory` / `json_advisory` 等更稳定模式，且仍需单独授权；
* 当前阶段 `shadow_candidate_allowed` 必须 false。

response-mode guard 不应替代 quality gate 或 evidence anchor。它只回答“输出来自哪种模式、是否稳定、是否 fallback”，而 quality gate 和 evidence anchor 继续判断内容质量、输入风险与证据状态。

## 5. generated-preview-as-evidence 定义设计

以下情况应识别为 generated-preview-as-evidence risk：

* 输入要求把本地模型生成建议作为招标条款依据；
* 输入要求把模型输出作为图纸、清单、评分项、规范依据；
* 输入将 `system_generated_preview` 作为 evidence source；
* 输入或输出出现“模型已证明”“本地模型依据显示”“AI 建议可作为证据”等类似表述；
* candidate patch / DOCX / ZBid 写回请求依赖 generated preview 作为事实证据；
* `evidence_source_type=system_generated_preview` 被用于 factual claim 的证据来源。

该风险与一般 low-risk writing advice 不同。只要 generated preview 被用于支撑事实性 claim，尤其是招标文件、图纸、清单、评分办法、规范、工程量、工期、金额、现场条件等内容，就应进入 evidence-risk 路径。

## 6. generated-preview-as-evidence guard 设计

后续 generated-preview-as-evidence guard 应满足：

* `system_generated_preview` 不得作为事实证据；
* `generated_content_must_not_be_evidence` 必须为 true；
* generated-preview-as-evidence detected 时，`evidence_anchor_status` 不得为 `anchored`；
* 可选状态应为 `invalid_anchor`、`review_required` 或 `blocked`；
* 若同时存在 direct write / DOCX export / ZBid writeback 请求，必须 `blocked`；
* generated preview 可作为 suggestion source，但不得作为 evidence source；
* generated preview 不得作为 `tender_document` / `drawing` / `boq` / `scoring_criteria` / `standard_or_code`；
* `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 必须恒 false。

建议后续状态映射：

* 仅提醒“模型建议不是证据”且无事实性 claim：`review_required` 或低风险 warning；
* 明确把 generated preview 当作招标条款、图纸、清单、评分项或规范依据：`invalid_anchor`；
* generated preview + direct write / DOCX export / ZBid writeback / candidate patch：`blocked`；
* metadata 中 `system_generated_preview` 被注册为 factual evidence source：`invalid_anchor` 或 `blocked`。

## 7. data contract 设计

后续可新增或稳定以下字段：

* `response_mode`
* `response_source`
* `preview_mode`
* `fallback_reason`
* `response_mode_confidence`
* `response_mode_warnings`
* `response_mode_review_required`
* `thinking_fallback_detected`
* `generated_preview_as_evidence_detected`
* `generated_content_must_not_be_evidence`
* `generated_content_evidence_blocked`
* `evidence_source_type`
* `evidence_anchor_status`
* `invalid_anchor_reason`
* `evidence_review_required`
* `evidence_blocked`
* `formal_generation_allowed`
* `shadow_candidate_allowed`
* `writeback_allowed`
* `export_allowed`
* `zbid_writeback_allowed`

当前阶段必须继续固定：

* `formal_generation_allowed=false`
* `shadow_candidate_allowed=false`
* `writeback_allowed=false`
* `export_allowed=false`
* `zbid_writeback_allowed=false`

字段语义建议：

* `response_mode` 表示规范化后的输出模式；
* `preview_mode` 可保留现有兼容字段；
* `response_source` 表示原始内容来源，例如 response、json、text、thinking；
* `fallback_reason` 记录为何进入 fallback；
* `thinking_fallback_detected=true` 时，不得进入 shadow_candidate；
* `generated_preview_as_evidence_detected=true` 时，evidence anchor 不得为 `anchored`；
* `generated_content_evidence_blocked=true` 表示 generated preview 被阻止作为 evidence。

## 8. deterministic tests 设计

后续 Step 67 或后续实现必须覆盖以下 tests，本步不得运行 pytest：

* response_advisory fixture -> `response_mode=response_advisory`；
* json_advisory fixture -> `response_mode=json_advisory`；
* text_fallback fixture -> `response_mode=text_fallback`；
* thinking_only_fallback fixture -> `review_required`，`shadow_candidate_allowed=false`；
* empty_response fixture -> controlled failure 或 `review_required`；
* malformed_response fixture -> controlled failure；
* generated preview used as tender evidence -> `invalid_anchor` 或 `blocked`；
* generated preview used as drawing evidence -> `invalid_anchor` 或 `blocked`；
* `system_generated_preview` as `evidence_source_type` -> `blocked`；
* generated preview + direct write request -> `blocked`；
* generated preview + DOCX export request -> `blocked`；
* generated preview + ZBid writeback request -> `blocked`；
* thinking fallback + evidence missing -> `review_required` 或 `blocked`；
* response_mode stable but evidence missing -> not formal eligible；
* all formal chain flags remain false；
* existing evidence anchor tests 不回归；
* existing quality gate / input-risk tests 不回归；
* existing `ollama_preview` tests 不回归；
* safe endpoint tests 不回归。

测试应全部使用 fake fixture / monkeypatch / dependency injection。不得真实访问 `127.0.0.1:11434`，不得运行 Ollama，不得下载模型，不得写 `output/job/export`，不得触发正式生成链。

## 9. fake fixture 设计

后续 tests 应新增或扩展以下 fake fixtures：

* `response_advisory_fixture`；
* `json_advisory_fixture`；
* `text_fallback_fixture`；
* `thinking_only_fallback_response_mode_fixture`；
* `empty_response_mode_fixture`；
* `malformed_response_mode_fixture`；
* `generated_preview_as_tender_evidence_fixture`；
* `generated_preview_as_drawing_evidence_fixture`；
* `system_generated_preview_evidence_source_fixture`；
* `generated_preview_direct_write_fixture`；
* `generated_preview_docx_export_fixture`；
* `generated_preview_zbid_writeback_fixture`；
* `thinking_fallback_missing_evidence_fixture`。

明确边界：

* deterministic tests 不得真实访问 `127.0.0.1:11434`；
* 不得运行 Ollama；
* 不得下载模型；
* 不得写 `output/job/export`；
* 不得触发正式生成链。

fixtures 应覆盖三类入口：raw Ollama response normalization、quality gate/evidence anchor metadata、safe endpoint response metadata。这样可以证明 response-mode 与 generated-preview-as-evidence guard 不依赖真实 runtime。

## 10. 后续实现边界设计

后续如进入实现，应先单独授权。建议允许范围可包括：

* `backend/zhifei_autoplan/ollama_preview.py`；
* `backend/zhifei_autoplan/evidence_anchor.py`；
* `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
* `backend/tests/test_ollama_preview.py`；
* `backend/tests/test_evidence_anchor.py`；
* `backend/tests/test_preview_advisory_quality_gate.py`；
* `backend/tests/test_local_llm_preview_safe_endpoint.py`。

原则上不新增新 helper 文件。
原则上不修改 endpoint。
如必须调整 endpoint response schema，需 ChatGPT 单独授权。
不得修改正式生成链、正式导出链、ZBid 写回链。

实现顺序建议：

1. 先在 fake-only normalization 层稳定 response-mode 字段；
2. 再将 response-mode 传入 quality gate；
3. 再补强 generated-preview-as-evidence evidence anchor 映射；
4. 最后补 safe endpoint metadata 回归测试。

## 11. 与 evidence anchor 的关系

response-mode 与 evidence anchor 必须分离但联动：

* generated_preview_as_evidence 是 evidence anchor 的 `invalid_anchor` 子类；
* `thinking_only_fallback` 如产生事实性内容，必须 `evidence_anchor_required`；
* response_mode 与 `evidence_anchor_status` 必须分离；
* `quality_status=preview_ok` 不代表 `evidence_anchor_status=anchored`；
* `evidence_anchor_status=anchored` 不代表 `formal_generation_allowed=true`；
* generated preview 只能作为 suggestion source，不得作为 evidence source。

具体含义：

* response-mode 判断输出从哪里来；
* quality gate 判断 advisory 是否可预览；
* input-risk 判断输入是否包含 unsupported claims；
* evidence anchor 判断 factual claim 是否有证据来源；
* generated-preview-as-evidence guard 判断模型生成内容是否被误用为证据。

这些门禁都通过，也只能作为后续 shadow/candidate 设计的基础，不得自动打开正式链。

## 12. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 response-mode guard 与 generated-preview-as-evidence guard 是正式链前的安全门禁。未完成该门禁前，不得进入 shadow generation，更不得进入正式正文写回、DOCX 导出或 ZBid 写回。

正式链前仍需完成：

* response-mode / generated-preview-as-evidence guard implementation；
* stage review；
* evidence-aware regression smoke 或 multi-payload follow-up；
* shadow generation design；
* candidate patch design；
* human approval / diff / rollback design；
* DOCX export consistency design；
* ZBid writeback isolation design。

当前阶段只设计门禁，不改变任何正式链准入状态。

## 13. 风险与回滚

当前风险：

* 风险 1：thinking fallback 高依赖被误读为模型质量稳定；
* 风险 2：generated preview 被误认为证据；
* 风险 3：`not_required` 被误解为无需审核；
* 风险 4：response_mode 被误用为正式链准入；
* 风险 5：future shadow generation 缺少 response-mode 降级策略；
* 风险 6：DOCX / ZBid 写回时 evidence trace 丢失；
* 风险 7：prompt 优化误破坏 no-write / preview-only。

回滚措施：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
* 保留 disabled / adapter-off / fake-only 路径；
* 出现异常时不得扩大到正式链路；
* response-mode、generated-preview-as-evidence、quality gate 或 evidence anchor 异常时应 fail-closed，不得自动放行。

## 14. 当前阶段结论

本阶段仅完成 response-mode / generated-preview-as-evidence guard 的 docs-only 设计，未实现代码，未运行测试，未启动服务，未进入 shadow generation 或正式生成链。

Step 66 的结论是：在继续推进正式链前，必须先补强 response-mode 分类与 generated-preview-as-evidence guard。`thinking_only_fallback` 高依赖和 EA-G 的 `not_required` 边界未解决前，不得进入 shadow generation、candidate patch、DOCX 导出或 ZBid 写回。

## 15. 下一步建议

下一步建议为 ZDoc Step 67：response-mode / generated-preview-as-evidence guard fake-only implementation + deterministic tests。

不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
