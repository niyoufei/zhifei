# ZDoc evidence anchor guard and deterministic tests design

## 1. 阶段背景

本阶段执行 ZDoc Step 60：evidence anchor guard + deterministic tests design。

前序阶段事实如下：

- Step 57 已完成 `unsupported_project_fact` targeted runtime regression smoke；
- Step 58 已完成 targeted runtime smoke review + thinking fallback follow-up design；
- Step 59 已完成 evidence anchor framework design；
- 当前已明确 evidence anchor 是正式生成链前置证据安全底座；
- 当前尚未实现 evidence anchor guard；
- 当前 thinking fallback 高依赖仍存在；
- 当前 input-risk / `unsupported_project_fact` 虽已有门禁，但缺少统一证据锚点约束；
- 当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回；
- Step 60 目标是锁定 evidence anchor guard、数据契约、测试设计、允许修改文件和回滚边界；
- 本步不得实现代码。

本步为 docs-only 设计步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 导出，不接 ZBid 正式写回。

## 2. evidence anchor 目标复述

evidence anchor 的核心目标如下：

- 为招标条款、评分项、图纸、清单、踏勘、补疑、规范、工程量、工期、金额、现场条件等事实性内容提供证据锚点；
- 支持标记 `anchored` / `partially_anchored` / `missing` / `conflicting` / `unverified` / `invalid_anchor` 等状态；
- 防止模型生成内容被误当作证据；
- 防止 `unsupported_project_fact` 进入 shadow generation；
- 防止无证据内容进入正式正文、DOCX 导出或 ZBid 写回；
- 为后续 candidate patch、人工确认写回、diff 展示、版本回滚提供 evidence trace 基础；
- 当前仍保持 preview-only / no-write。

该目标不是允许模型直接写正文，而是在 preview advisory 与后续 shadow/candidate 阶段之间建立证据安全门禁。

## 3. evidence source 类型 guard 设计

基于 Step 59，后续 evidence anchor guard 应识别以下 evidence source 类型：

- `tender_document`；
- `tender_addendum`；
- `scoring_criteria`；
- `drawing`；
- `boq`；
- `site_survey`；
- `photos`；
- `contract_or_owner_requirement`；
- `standard_or_code`；
- `user_provided_context`；
- `system_generated_preview`；
- `unknown_or_unverified`。

source 类型 guard 规则如下：

- `system_generated_preview` 不得作为事实证据；
- `unknown_or_unverified` 必须触发 `review_required` 或 `blocked`；
- `standard_or_code` 必须具备编号、版本或来源；
- `user_provided_context` 只能作为用户输入来源，不等同于已核验证据；
- 图纸、清单、招标条款等必须具备位置、页码、条款号或等价定位信息，才能视为 strong anchor；
- 对来源类型为空、未知枚举值、模型生成内容伪装成证据的情况，应 fail-closed。

## 4. evidence anchor 状态 guard 设计

后续 evidence anchor 状态规则如下。

### anchored

- 证据来源明确；
- `source_type` 有效；
- `source_id` 或 `source_title` 可追踪；
- `location` / `clause` / `page` 至少具备一种定位方式；
- 但仍不得自动进入正式链。

`anchored` 只表示证据链具备下一阶段评审基础，不代表 `formal_generation_allowed=true`。

### partially_anchored

- 部分证据明确，但仍需人工核验；
- 可展示为 `review_required`；
- 不得进入 `shadow_candidate`。

### missing

- 缺少证据；
- 对事实性内容必须 `review_required` 或 `blocked`。

### conflicting

- 证据冲突；
- 必须 `blocked`。

### unverified

- 未查明；
- 必须 `review_required`；
- 不得 `preview_ok` 或 `shadow_candidate`。

### not_required

- 仅限低风险泛化建议；
- 如出现具体事实、条款、参数，应升级为 required。

### invalid_anchor

- 证据格式无效；
- 引用模型生成内容作为证据；
- 引用不存在来源；
- 必须 `blocked`。

### system_error

- evidence anchor 处理异常；
- 必须受控返回，不得自动放行。

## 5. 必须 evidence anchor 的内容 guard

后续必须要求 evidence anchor 的内容包括：

- 招标条款；
- 评分办法；
- 答疑 / 补遗 / 澄清；
- 图纸内容；
- 工程量清单；
- 工程量、工期、金额、质量目标、安全文明目标；
- 现场条件、临时道路、材料堆场、机械设备、作业面、管线；
- 规范编号和版本；
- 施工参数、验收标准、检查频次；
- 项目名称、建设单位、工期节点、分区、专业系统；
- 任何将进入 shadow generation、candidate patch 或正式正文的事实性内容。

这些内容一旦缺少证据，必须设置 `evidence_anchor_required=true`，并进入 `review_required` 或 `blocked`。如果同时出现 input-risk、thinking fallback、直接写入/导出请求，应采用更保守状态。

## 6. 可暂不 evidence anchor 的内容 guard

以下内容可暂不 evidence anchor，但仍不得进入正式链：

- 泛化写作建议；
- 结构优化建议；
- 语言精简建议；
- 提醒补充资料；
- 提醒风险闭环；
- 提醒参数需核验；
- 提醒人工确认；
- 不含具体事实、条款、参数、数量、规范编号的低风险 advisory。

但一旦包含条款、参数、数量、金额、规范编号、现场事实，则必须 `evidence_anchor_required=true`。

低风险 advisory 即使为 `not_required`，也只代表暂不需要证据锚点，不代表可写入正式正文、导出 DOCX 或写回 ZBid。

## 7. evidence anchor data contract 设计

后续 evidence anchor 输出字段建议如下，本步不得实现：

- `evidence_anchor_required`
- `evidence_anchor_status`
- `evidence_anchor_level`
- `evidence_sources`
- `evidence_source_type`
- `evidence_source_id`
- `evidence_source_title`
- `evidence_location`
- `evidence_page`
- `evidence_clause`
- `evidence_quote_excerpt`
- `evidence_confidence`
- `evidence_missing_reasons`
- `unsupported_claims`
- `unsupported_project_facts`
- `unverified_parameters`
- `evidence_review_required`
- `evidence_blocked`
- `trace_id`
- `source_snapshot_id`
- `generated_from_model`
- `generated_content_must_not_be_evidence`

字段约束如下：

- `evidence_sources` 应为结构化列表，不应只存自然语言说明；
- `evidence_quote_excerpt` 只能保存短摘录，不应保存完整长文；
- `trace_id` 应能贯穿 preview、quality gate、future candidate patch 和 human approval；
- `source_snapshot_id` 应指向输入资料快照或解析结果快照；
- `generated_from_model=true` 时，必须 `generated_content_must_not_be_evidence=true`。

当前阶段必须继续固定：

- `formal_generation_allowed=false`
- `shadow_candidate_allowed=false`
- `writeback_allowed=false`
- `export_allowed=false`
- `zbid_writeback_allowed=false`

## 8. input-risk 与 evidence anchor 集成设计

后续集成规则如下：

- `unsupported_claims_detected=true` 时，`evidence_anchor_required=true`；
- `unsupported_project_fact_detected=true` 时，`evidence_anchor_required=true`；
- `evidence_source_missing=true` 时，`evidence_anchor_status` 不得为 `anchored`；
- `project_fact_without_evidence=true` 时，`evidence_review_required=true`；
- `input_risk_blocked=true` 时，`evidence_anchor_status` 可为 `missing` 或 `invalid_anchor`；
- `direct_write_request_detected` 与 evidence missing 叠加时必须 `blocked`；
- input-risk 不得被 evidence anchor 的 partial 状态掩盖；
- evidence anchor 不得把 `status=ok` 或 `preview_ok` 解释为正式链准入。

input-risk 负责发现输入或输出中的疑似风险；evidence anchor 负责判断这些风险是否有可追溯来源。二者应合并到 preview metadata，但不应触发正式写回或导出。

## 9. thinking fallback 与 evidence anchor 集成设计

后续规则如下：

- thinking fallback 不得作为 evidence；
- thinking fallback 内容不得写入正式正文；
- thinking fallback 如包含事实性内容，必须 `evidence_anchor_required=true`；
- thinking fallback + missing evidence 应 `review_required` 或 `blocked`；
- thinking fallback 高依赖应降低 confidence；
- thinking fallback 不得进入 `shadow_candidate`；
- thinking fallback 不得触发 DOCX 导出或 ZBid 写回。

Step 57 已显示 targeted payload 中 6/7 仍依赖 thinking fallback。因此 evidence anchor guard 必须把 thinking fallback 作为低置信来源处理，而不是把其内容当作可锚定事实。

## 10. quality gate 与 evidence anchor 集成设计

quality gate 与 evidence anchor 的集成规则如下：

- `quality_status=preview_ok` 不代表 `evidence_anchor_status=anchored`；
- `evidence_anchor_status=anchored` 不代表 `formal_generation_allowed=true`；
- quality gate 与 evidence anchor 均通过后，也只能进入后续 shadow/candidate 设计阶段；
- `blocked` / `system_error` / `missing` / `invalid_anchor` 必须 fail-closed；
- 当前阶段所有正式链准入字段仍为 false。

后续实现应将 evidence anchor 结果作为独立 metadata 合并到 preview response，而不是用它覆盖 quality gate。任何一个门禁失败，都不得让正式链准入字段变为 true。

## 11. shadow generation 准入 guard 设计

后续 shadow generation 前必须满足：

- quality gate 不为 `blocked`；
- input-risk 不为 `blocked`；
- `evidence_anchor_status` 不为 `missing` / `conflicting` / `invalid_anchor` / `system_error`；
- facts must carry evidence anchors；
- thinking fallback 不能作为正式事实来源；
- candidate patch 必须保留 `trace_id`；
- `shadow_candidate_allowed` 只有后续单独授权阶段才可能设计为 true；
- 当前阶段 `shadow_candidate_allowed` 必须 false。

即使未来 evidence anchor 返回 `anchored`，也只能表示可进入 shadow/candidate 设计讨论，不代表本阶段可创建 shadow generation。

## 12. DOCX 导出 guard 设计

DOCX 导出 guard 规则如下：

- DOCX 导出不是证据来源；
- DOCX 是输出载体；
- 导出内容中的事实性文本应能追溯 evidence anchor；
- 无证据内容不得自动进入 DOCX；
- 导出前必须校核标题层级、章节内容、证据锚点、图文/表格一致性；
- 当前阶段 `export_allowed=false`。

后续如果进入 DOCX 一致性校核，应验证正文中每个条款、参数、数量、规范编号、现场事实都能追溯到 evidence anchor；不能追溯时不得自动导出。

## 13. ZBid 写回 guard 设计

ZBid 写回 guard 规则如下：

- ZBid 写回必须保留 evidence trace；
- 不得覆盖原始招标解析数据；
- 不得污染 scoring basis；
- 不得将 model-generated advisory 当作原始证据；
- ZBid 写回前必须区分 source evidence、generated suggestion、human approval；
- 当前阶段 `zbid_writeback_allowed=false`。

ZBid 写回应只接受经过人工确认、携带 evidence trace、可回滚的 candidate patch。preview advisory 和 thinking fallback 不得直接成为 ZBid 写回内容。

## 14. deterministic tests 设计

后续 Step 61 或后续实现必须覆盖以下 tests，但本步不得运行 pytest：

- anchored tender clause fixture；
- anchored drawing / boq fixture；
- missing evidence fixture；
- invalid evidence source fixture；
- model-generated preview as evidence fixture；
- unsupported project fact with missing evidence fixture；
- safe expression with evidence required fixture；
- conflicting evidence fixture；
- anchored advisory but formal flags false fixture；
- thinking fallback with factual claim fixture；
- ZBid writeback attempted without evidence fixture；
- DOCX export attempted without evidence fixture；
- candidate patch without evidence fixture；
- evidence_anchor_required with no source -> `review_required` or `blocked`；
- system_generated_preview as evidence -> `blocked`；
- unknown_or_unverified source -> `review_required`；
- standard_or_code without version/source -> `review_required`；
- high-quality advisory without facts -> `not_required` or `review_required` but formal flags false。

所有测试必须是 deterministic tests，使用 fake fixture / monkeypatch / dependency injection，不得依赖真实 Ollama runtime。

## 15. fake fixture 设计

后续 tests 应新增或扩展以下 fake fixtures：

- `anchored_tender_clause_fixture`；
- `anchored_scoring_criteria_fixture`；
- `anchored_drawing_fixture`；
- `anchored_boq_fixture`；
- `missing_evidence_fixture`；
- `invalid_anchor_fixture`；
- `model_generated_preview_as_evidence_fixture`；
- `unsupported_project_fact_missing_evidence_fixture`；
- `thinking_fallback_fact_claim_fixture`；
- `conflicting_evidence_fixture`；
- `zbid_writeback_without_evidence_fixture`；
- `docx_export_without_evidence_fixture`；
- `candidate_patch_missing_evidence_fixture`；
- `safe_unverified_expression_fixture`；
- `standard_without_version_fixture`。

测试边界如下：

- deterministic tests 不得真实访问 `127.0.0.1:11434`；
- 不得运行 Ollama；
- 不得下载模型；
- 不得写 `output/job/export`；
- 不得触发正式生成链。

## 16. 后续实现边界设计

后续实现前需另行授权。建议实现范围可包括：

- 新增 `backend/zhifei_autoplan/evidence_anchor.py` 或同类 helper；
- 新增 `backend/tests/test_evidence_anchor.py`；
- 扩展 `preview_advisory_quality_gate.py` 以合并 evidence metadata；
- 扩展 `test_preview_advisory_quality_gate.py`；
- 必要时扩展 `ollama_preview.py` response metadata。

但本步不得实现。如后续需要新增文件，必须在 Step 61 指令中单独授权。

后续实现仍不得修改：

- 正式生成链；
- 正式导出链；
- ZBid 写回链；
- `output/`；
- `job/`；
- `export/`；
- 正式模板文件；
- 正式生成结果文件。

## 17. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

evidence anchor 是正式链前证据安全基础。未完成 evidence anchor guard 与 deterministic tests 前，不得进入 shadow generation，更不得进入正式正文写回、DOCX 导出或 ZBid 写回。

正式链前仍需完成：

- evidence anchor fake-only implementation；
- evidence anchor implementation stage review；
- evidence-aware runtime smoke plan；
- evidence-aware runtime smoke；
- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离。

## 18. 风险与回滚

当前风险如下：

- 风险 1：将模型生成内容误认为证据；
- 风险 2：无证据项目事实进入 shadow generation；
- 风险 3：evidence anchor 过严导致真实但未标注资料被误拦截；
- 风险 4：evidence anchor 过宽导致虚构条款进入正式链；
- 风险 5：DOCX 导出或 ZBid 写回时 evidence trace 丢失；
- 风险 6：人工确认写回前未展示证据；
- 风险 7：thinking fallback 生成事实性内容但缺少证据；
- 回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 兜底措施：保留 disabled / adapter-off / fake-only 路径；
- evidence anchor 异常应 fail-closed，不得自动放行。

如果后续 evidence anchor helper 出现异常，应返回 `review_required`、`blocked` 或受控 `system_error`，不得让异常路径默认通过。

## 19. 当前阶段结论

本阶段仅完成 evidence anchor guard + deterministic tests 的 docs-only 设计，未实现 evidence anchor，未运行测试，未启动服务，未进入 shadow generation 或正式生成链。

本阶段不改变 quality gate helper、不改变 input-risk helper、不改变 endpoint response schema、不改变任何正式链准入字段。

## 20. 下一步建议

下一步建议为 ZDoc Step 61：evidence anchor fake-only implementation + deterministic tests。不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
