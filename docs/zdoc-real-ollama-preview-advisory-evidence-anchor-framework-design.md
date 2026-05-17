# ZDoc evidence anchor framework design

## 1. 阶段背景

本阶段执行 ZDoc Step 59：evidence anchor framework design。

前序阶段事实如下：

- Step 57 已完成 `unsupported_project_fact` targeted runtime regression smoke；
- Step 58 已完成 targeted runtime smoke review + thinking fallback follow-up design；
- Step 57 已证明 `unsupported_project_fact` targeted runtime 受控；
- UPF-A～UPF-E 已进入 `review_required`，UPF-F / UPF-G 已 `blocked`；
- `input_evidence_required / evidence_anchor_required = 7 / 7`；
- 但 6/7 payload 仍依赖 thinking fallback；
- 当前 evidence anchor 体系尚未建立；
- 当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回；
- Step 59 目标是设计 evidence anchor 框架，作为正式生成链前的证据安全底座；
- 本步不得实现代码。

本步为 docs-only 体系设计步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 导出，不接 ZBid 正式写回。

## 2. evidence anchor 的必要性

当前 input-risk gate 已能识别一部分 unsupported claims，`unsupported_project_fact` guard 也已能识别一部分无证据项目事实。例如 Payload C 等价风险可被 `blocked`，IR-D 类无证据现场事实已不再是 `input_risk_status=clear`。

但当前仍缺少统一证据锚点体系。现有 quality gate 只能说明某些输入或输出存在风险，尚不能说明某条建议、参数、条款或事实来自哪份资料、哪一页、哪一条、哪一段，也不能稳定区分“已查明事实”“待核验事实”和“模型生成建议”。

没有 evidence anchor，模型生成的 advisory、candidate patch 或正式正文无法证明来源。招标条款、图纸、清单、踏勘、补疑、评分项等内容容易被模型臆断，也容易在后续人工确认、DOCX 导出或 ZBid 写回时丢失证据链。

因此，evidence anchor 是从 preview-only 走向 shadow generation、candidate patch、人工确认写回、DOCX 导出、ZBid 写回的前置门禁。未完成 evidence anchor 前，不得把本地模型输出接入正式生成链。

## 3. evidence anchor 总体目标

evidence anchor 框架目标如下：

- 为每一条高风险事实、条款、参数、评分项、工程量、图纸/清单信息建立证据来源；
- 支持标记“已查明”“未查明”“需资料核验”“证据不足”；
- 防止模型虚构招标条款、规范编号、工程量、工期、金额、现场条件；
- 防止 `unsupported_project_fact` 进入 shadow generation；
- 为后续 candidate patch / 人工确认写回提供可追溯依据；
- 为 DOCX 导出一致性和 ZBid 写回隔离提供 evidence trace 基础；
- 当前阶段仍保持 preview-only / no-write。

该框架的定位不是生成正式正文，也不是替代人工审核，而是在 preview advisory 之后、shadow generation 之前建立事实来源检查层。

## 4. evidence source 类型设计

后续 evidence anchor 至少应支持以下证据来源类型：

- `tender_document`：招标文件；
- `tender_addendum`：答疑、补遗、澄清；
- `scoring_criteria`：评分办法；
- `drawing`：图纸；
- `boq`：工程量清单；
- `site_survey`：踏勘记录；
- `photos`：现场照片；
- `contract_or_owner_requirement`：合同或建设单位要求；
- `standard_or_code`：规范、标准；
- `user_provided_context`：用户提供的上下文；
- `system_generated_preview`：系统生成的 preview advisory；
- `unknown_or_unverified`：未查明或无证据来源。

约束如下：

- `system_generated_preview` 不得作为事实证据；
- `unknown_or_unverified` 必须触发 `review_required` 或 `blocked`；
- 规范标准必须有编号、版本或明确来源，否则不得作为强证据；
- 用户提供的上下文可以作为待核验证据线索，但在缺少来源定位时不应自动视为强证据；
- 对进入 shadow generation、candidate patch 或正式正文的事实性内容，必须优先使用可定位的 source evidence，而不是模型生成文本。

## 5. evidence anchor data contract 设计

后续 evidence anchor 可新增或稳定以下字段，本步不得实现：

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

建议字段语义如下：

- `evidence_anchor_required` 表示本条 advisory、claim 或 candidate 是否必须绑定证据；
- `evidence_anchor_status` 表示证据锚点状态；
- `evidence_anchor_level` 表示门禁级别，例如 low、medium、high 或 P2/P3/P4；
- `evidence_sources` 保存可追溯证据列表；
- `evidence_quote_excerpt` 只保存短摘录，不保存完整长文；
- `evidence_confidence` 只表达证据匹配置信度，不代表可自动写回；
- `generated_from_model=true` 时必须同时设置 `generated_content_must_not_be_evidence=true`；
- `trace_id` / `source_snapshot_id` 用于后续回溯输入快照和证据来源。

当前阶段仍固定要求：

- `formal_generation_allowed=false`
- `shadow_candidate_allowed=false`
- `writeback_allowed=false`
- `export_allowed=false`
- `zbid_writeback_allowed=false`

## 6. evidence anchor 状态设计

后续 evidence anchor 至少应支持以下状态：

- `anchored`：证据已明确；
- `partially_anchored`：部分证据明确，仍需人工核验；
- `missing`：缺少证据；
- `conflicting`：证据冲突；
- `unverified`：未查明；
- `not_required`：低风险表述暂不需要证据；
- `invalid_anchor`：证据格式或来源无效；
- `system_error`：证据锚点处理异常。

状态约束如下：

- `missing` / `conflicting` / `unverified` / `invalid_anchor` 不得进入 `shadow_candidate`；
- `anchored` 也不等于正式生成链准入；
- `anchored` 仅表示证据链满足进入下一阶段评审的基础条件；
- `partially_anchored` 应至少进入 `review_required`；
- `system_error` 必须 fail-closed，不能自动放行；
- `not_required` 只适用于低风险泛化建议，不适用于条款、参数、数量、金额、规范编号、项目事实。

## 7. 哪些内容必须 evidence anchor

以下内容必须要求 evidence anchor：

- 招标条款；
- 评分办法；
- 答疑 / 补遗 / 澄清；
- 图纸内容；
- 工程量清单；
- 工程量、工期、金额、质量目标、安全文明目标；
- 现场条件、临时道路、材料堆场、机械设备、作业面；
- 规范编号和版本；
- 施工参数、验收标准、检查频次；
- 项目名称、建设单位、工期节点、分区、专业系统；
- 任何将进入 shadow generation、candidate patch 或正式正文的事实性内容。

这些内容一旦缺少证据来源，应触发 `evidence_anchor_required=true`，并进入 `review_required` 或 `blocked`。如果同时出现 input-risk、thinking fallback 或 direct write request，应更保守。

## 8. 哪些内容可以暂不 evidence anchor

以下低风险内容可以暂不 evidence anchor，但仍不得进入正式链：

- 泛化写作建议；
- 结构优化建议；
- 语言精简建议；
- 提醒补充资料；
- 提醒风险闭环；
- 提醒参数需核验；
- 提醒人工确认。

约束如下：

- 这些内容只能作为 preview-only advisory；
- 不得自动进入 shadow generation；
- 不得写入正式正文；
- 不得 DOCX 导出；
- 不得写回 ZBid；
- 如果这些建议包含具体条款、参数、数量、金额、规范编号，则必须升级为 `evidence_anchor_required`。

## 9. input-risk 与 evidence anchor 的关系

input-risk 与 evidence anchor 应形成联动：

- input-risk 识别 unsupported claims；
- evidence anchor 判断 claims 是否有来源支撑；
- input-risk 与 evidence anchor 应联动；
- `unsupported_claims_detected=true` 时，`evidence_anchor_required=true`；
- `unsupported_project_fact_detected=true` 时，`evidence_anchor_required=true`；
- `evidence_source_missing=true` 时，不得 `preview_ok` 或不得进入 `shadow_candidate`；
- `direct_write_request_detected` 与 evidence missing 叠加时必须 `blocked`；
- `thinking_only_fallback` 与 evidence missing 叠加时必须更保守。

后续设计中，input-risk 不应只在质量门禁内作为 warning 存在，还应转化为 evidence anchor 的必查项。换言之，input-risk 发现“可能无证据”，evidence anchor 必须回答“证据在哪里，是否有效，是否冲突，是否仍需人工确认”。

## 10. thinking fallback 与 evidence anchor 的关系

thinking fallback 与 evidence anchor 的关系如下：

- thinking fallback 不得作为 evidence；
- thinking fallback 可作为 preview-only advisory 的来源标记；
- thinking fallback 内容不得写入正式正文；
- thinking fallback 生成的事实性内容必须 `evidence_anchor_required`；
- thinking fallback 高依赖场景应降低 `quality_score` 或进入 `review_required`；
- 若 thinking fallback 含具体项目事实但无证据，必须 `blocked` 或 `review_required`。

Step 57 的 6/7 thinking fallback 说明，当前 runtime 普通 response 稳定性不足。后续 evidence anchor 必须把 thinking fallback 明确标记为不可作为证据、不可作为正式文本来源、不可直接进入 candidate patch。

## 11. quality gate 与 evidence anchor 的关系

quality gate 与 evidence anchor 分工如下：

- quality gate 判断输出质量与安全状态；
- evidence anchor 判断事实来源和证据完整性；
- `quality_status=preview_ok` 不代表 `evidence_anchor_status=anchored`；
- `evidence_anchor_status=anchored` 不代表 `formal_generation_allowed=true`；
- 两者均通过后，也只能进入后续 shadow/candidate 设计阶段；
- 当前阶段所有正式链准入字段仍为 false。

后续应避免把 evidence anchor 简化为 quality gate 的一个普通 warning。证据锚点应是正式链前独立可审计的安全层，并能把缺证据、证据冲突、证据无效等状态明确传递给人工审核界面。

## 12. shadow generation 准入关系

shadow generation 与 evidence anchor 的准入关系如下：

- shadow generation 不得直接接收未锚定事实；
- candidate patch 必须携带 evidence anchors；
- 人工确认写回必须展示 evidence anchors；
- 缺少 evidence anchor 的内容只能作为 `review_required`；
- evidence anchor 冲突时必须 `blocked`；
- `shadow_candidate_allowed` 后续只有在 evidence anchor、quality gate、input-risk gate 均通过后才可能设计为 true；
- 当前阶段 `shadow_candidate_allowed` 必须 false。

这意味着 Step 59 不改变任何正式链准入字段，也不设计自动写回。后续即使 evidence anchor fake-only implementation 通过，也仍需单独设计 shadow generation 才能讨论 candidate patch。

## 13. DOCX 导出与 evidence anchor 的关系

DOCX 导出与 evidence anchor 的关系如下：

- DOCX 导出不能成为证据来源；
- DOCX 仅是输出载体；
- 导出内容中的事实性文本应能追溯 evidence anchor；
- DOCX 导出前必须验证章节内容、证据锚点、图文/表格一致性；
- 无证据内容不得自动进入 DOCX；
- 当前阶段 `export_allowed=false`。

后续 DOCX 一致性校核应检查：正式章节文本中的条款、参数、工程量、规范编号、现场条件是否都能回溯到 evidence anchors；如果无法回溯，应阻断导出或进入人工复核。

## 14. ZBid 写回与 evidence anchor 的关系

ZBid 写回与 evidence anchor 的关系如下：

- ZBid 写回必须保留 evidence trace；
- 不得覆盖原始招标解析数据；
- 不得污染 scoring basis；
- 不得将 model-generated advisory 当作原始证据；
- ZBid 写回前必须区分 source evidence、generated suggestion、human approval；
- 当前阶段 `zbid_writeback_allowed=false`。

ZBid 写回必须是人工确认后的受控动作。evidence anchor 应提供 source trace，但不得替代 ZBid 原始数据，也不得把 preview advisory 反写为事实依据。

## 15. future evidence anchor guard 设计

后续 Step 60 应关注以下 guard：

- missing evidence -> `review_required` 或 `blocked`；
- invalid evidence source -> `blocked`；
- model-generated preview as evidence -> `blocked`；
- unsupported claim with no evidence -> `blocked`；
- project fact without evidence -> `review_required` 或 `blocked`；
- safe expression with missing evidence -> `review_required`；
- evidence conflict -> `blocked`；
- evidence anchored but no human approval -> `formal_generation_allowed=false`；
- evidence anchor fields missing -> `review_required`；
- all formal chain flags remain false。

这些 guard 应继续保持 conservative heuristic。宁可让不确定内容进入人工复核，也不得把无证据事实包装为可用正文。

## 16. deterministic tests 设计方向

后续 deterministic tests 可覆盖以下 fixture，本步不得运行 pytest：

- anchored tender clause fixture；
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
- candidate patch without evidence fixture。

测试原则如下：

- 使用 fake fixture / monkeypatch / dependency injection；
- 不真实访问 `127.0.0.1:11434`；
- 不运行 Ollama；
- 不启动服务；
- 不下载模型；
- 不写 `output/job/export`；
- 不触发正式生成链、导出链或 ZBid 写回链。

## 17. future implementation boundary

后续实现前需另行授权。可能涉及但本步不得实现：

- 新增 evidence anchor helper；
- 扩展 preview quality gate；
- 扩展 input-risk metadata；
- 扩展 `ollama_preview` response schema；
- 增加 deterministic tests；
- 后续接入 shadow generation 前单独设计。

建议后续步骤：

- Step 60：evidence anchor guard + deterministic tests design；
- Step 61：evidence anchor fake-only implementation + deterministic tests；
- Step 62：evidence anchor implementation stage review；
- Step 63：evidence-aware multi-payload smoke plan；
- Step 64：evidence-aware multi-payload smoke。

本阶段不得新增 helper，不得修改 endpoint，不得修改正式生成链，不得修改导出链，不得修改 ZBid 写回链。

## 18. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

evidence anchor 是正式链的证据安全基础。未完成 evidence anchor 前，不得进入 shadow generation，更不得进入正式正文写回、DOCX 导出或 ZBid 写回。

正式链前仍需完成：

- evidence anchor guard design；
- evidence anchor fake-only implementation；
- evidence-aware runtime smoke；
- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离。

## 19. 风险与回滚

当前风险如下：

- 风险 1：将模型生成内容误认为证据；
- 风险 2：无证据项目事实进入 shadow generation；
- 风险 3：evidence anchor 过严导致真实但未标注资料被误拦截；
- 风险 4：evidence anchor 过宽导致虚构条款进入正式链；
- 风险 5：DOCX 导出或 ZBid 写回时 evidence trace 丢失；
- 风险 6：人工确认写回前未展示证据；
- 回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 兜底措施：保留 disabled / adapter-off / fake-only 路径；
- evidence anchor 异常应 fail-closed，不得自动放行。

若后续 evidence anchor 处理异常，应返回 `review_required`、`blocked` 或受控 `system_error`，不得把异常路径解释为可用或可正式生成。

## 20. 当前阶段结论

本阶段仅完成 evidence anchor framework 的 docs-only 设计，未实现 evidence anchor，未运行测试，未启动服务，未进入 shadow generation 或正式生成链。

当前设计只建立证据安全框架和后续 guard/test 方向，不改变 preview advisory helper，不改变 input-risk helper，不改变 endpoint response schema，不改变任何正式链准入字段。

## 21. 下一步建议

下一步建议为 ZDoc Step 60：evidence anchor guard + deterministic tests design。不得直接进入 evidence anchor implementation、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
