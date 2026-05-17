# ZDoc unsupported_project_fact input-risk guard and deterministic tests design

## 1. 阶段背景

本阶段执行 ZDoc Step 53：unsupported_project_fact input-risk guard + deterministic tests design。

前序阶段事实如下：

- Step 51 已完成 input-risk multi-payload regression smoke + smoke report；
- Step 52 已完成 unsupported_project_fact runtime gap design；
- Step 51 已证明 Payload C 等价 unsupported claims 可 `blocked`；
- Step 51 也暴露 IR-D unsupported project fact 未触发 input-risk；
- IR-D 当前为 `review_required / clear / P2`，仅因 thinking fallback 或一般质量降级支撑；
- 当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回；
- Step 53 目标是锁定 unsupported_project_fact guard、数据契约、测试设计、允许修改文件和回滚边界；
- 本步不得实现代码。

本步为 docs-only 设计步骤，不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 导出，不接 ZBid 正式写回。

## 2. unsupported_project_fact 缺口复述

当前缺口如下：

- 现有 input-risk gate 对明显异常编号、规范编号、工程量、工期、金额等规则化风险已有覆盖；
- 对无证据项目事实的识别仍偏弱；
- IR-D 输入中明确写明 no drawings or site records are provided，但仍断言现场已有 3 台塔吊、2 座拌合站、5 个固定材料堆场；
- 该类内容没有异常编号，不一定触发 `suspicious_reference`；
- 但在技术标/施工组织设计场景中属于 evidence safety 风险；
- unsupported_project_fact 不解决前，不得进入 shadow generation 或正式链。

只读检查显示，当前 `unsupported_project_fact` 规则主要覆盖类似“本项目必须/要求/采用/位于/包含/设置/配置”的表达。IR-D 的表达是“现场已有具体设施与数量”，且用英文明确声明 no drawings or site records are provided，因此需要 evidence-aware 的项目事实断言识别，而不是仅依赖异常编号或固定动词。

## 3. unsupported_project_fact 定义设计

后续应将以下内容识别为 `unsupported_project_fact`：

- 未提供图纸、清单、踏勘记录、招标文件，却断言现场已有机械、设备、道路、堆场、作业面；
- 未提供依据，却断言项目已有特定数量塔吊、拌合站、材料堆场、临建、道路、管线、作业面；
- 未提供依据，却断言工程量已确认、设计参数已确定、评分项已满分；
- 未提供依据，却断言工期、质量目标、资金金额、清单数量、设备数量；
- 以肯定句输出项目事实，但缺少“需资料核验 / 未查明 / 待确认”等安全表达；
- 输入中出现“no drawings or site records are provided”“未提供图纸/清单/踏勘记录”等证据缺失提示，同时又断言具体事实。

建议把 unsupported project fact 分成两类：

- weak unsupported fact：存在项目事实断言，但证据缺失提示不强或没有具体数量，应至少 `review_required`；
- strong unsupported fact：存在证据缺失提示，并同时断言具体数量、设施、设备、道路、堆场、作业面、清单或评分项，应 strong `review_required` 或 `blocked`。

在当前 preview 阶段，宁可保守拦截或要求人工复核，也不得把无证据项目事实包装为可直接使用的 advisory。

## 4. evidence safety 判定策略

后续实现应采用 conservative heuristic。

判定策略建议如下：

- 存在证据缺失提示 + 具体项目事实断言时，应至少 `review_required`；
- 存在证据缺失提示 + 明确数量断言时，应 strong `review_required` 或 `blocked`；
- 存在“需资料核验”“未查明”“待招标文件确认”等安全表达时，可降级为 `review_required`，但不得 `preview_ok`；
- 断言现场已有机械/设备/材料堆场/作业面/道路/管线等项目事实，且无证据锚点时，应 `input_risk_status` 非 `clear`；
- `unsupported_project_fact` 与 `thinking_only_fallback` 叠加时，应更保守；
- `unsupported_project_fact` 不得被 `status=ok`、`preview_ok` 或 advisory 文本质量掩盖。

建议识别维度：

- evidence missing marker：`no drawings`、`no site records`、`未提供图纸`、`未提供清单`、`未提供踏勘记录`、`未提供现场记录`、`无依据`、`缺少证据`；
- project fact noun：塔吊、拌合站、材料堆场、道路、管线、临建、作业面、加工棚、设备、机械、清单、工程量、设计参数、评分项；
- assertion verb：已有、已设置、已确认、已具备、必须达到、全部无误、确定、达到满分；
- specific quantity marker：数字 + 台/座/个/处/套/条/平方米/米/吨等；
- safe expression marker：需资料核验、未查明、待确认、不得作为正式响应依据。

## 5. IR-D 等价场景专项设计

必须单独设计 IR-D 等价 fixture。

输入：

```text
本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。No drawings or site records are provided.
```

期望：

- `input_risk_status` 不得为 `clear`；
- `input_risk_flags` 应包含 `unsupported_project_fact` 或 `evidence_required`；
- `input_risk_warnings` / `review_reasons` 应体现“无图纸/踏勘/记录支撑的现场事实断言”；
- `quality_status` 至少 `review_required`；
- 如断言数量较具体，可 `blocked`；
- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`；
- 不得 `preview_ok`。

IR-D 等价场景的核心不是数字是否夸张，而是输入同时具备“具体现场事实断言”和“证据缺失提示”。只要该组合存在，input-risk metadata 就必须可追踪。

## 6. safe expression 例外设计

安全表达不应被误杀，但也不能放行。

安全表达包括：

- “需资料核验”
- “未查明”
- “待招标文件确认”
- “待图纸/清单/踏勘记录核验”
- “该条内容未在资料中查明”
- “不得作为正式响应依据”

期望：

- 可从 `blocked` 降级为 `review_required`；
- 不得 `preview_ok`；
- 不得 `shadow_candidate`；
- 不得 `formal_generation_allowed=true`；
- 应设置 `input_evidence_required=true` 或 `evidence_anchor_required=true`。

安全表达的语义是“允许作为人工核验提醒”，不是“允许进入正式生成”。如果输入包含安全表达但同时存在直接写入/导出/写回请求，仍应由 P0 或 input-risk hard guard `blocked`。

## 7. input-risk 与 thinking fallback 叠加设计

`thinking_only_fallback` 已经是质量降级因素。

后续设计应明确：

- `unsupported_project_fact + thinking_only_fallback` 应比单一 thinking fallback 更保守；
- 不得 `preview_ok`；
- 不得 `shadow_candidate`；
- 不得正式链准入；
- 应在 `blockers` / `warnings` / `review_reasons` 中同时体现 input-risk 与 fallback 风险；
- 后续测试应单独覆盖 IR-F 等价形态。

建议判断方式：

- 若 `preview_mode=thinking_only_fallback` 且 `input_risk_status=review_required`，最终 `quality_status` 至少维持 `review_required`，不得升为 `preview_ok`；
- 若 `preview_mode=thinking_only_fallback` 且 `unsupported_project_fact` 为 strong risk，可考虑 `blocked`；
- 若 `preview_mode=thinking_only_fallback` 且存在 direct write / export / ZBid 写回请求，必须 `blocked`。

## 8. data contract 设计

后续应新增或稳定以下字段：

- `input_risk_status`；
- `input_risk_score`；
- `input_risk_flags`；
- `input_risk_blockers`；
- `input_risk_warnings`；
- `unsupported_claims_detected`；
- `unsupported_project_fact_detected`；
- `evidence_required_reasons`；
- `input_evidence_required`；
- `evidence_anchor_required`；
- `input_risk_review_required`；
- `input_risk_blocked`；
- `suspicious_references`；
- `evidence_source_missing`；
- `project_fact_without_evidence`。

字段约束：

- `input_risk_status=clear` 不得用于 IR-D 等价场景；
- `unsupported_project_fact_detected=true` 时，`shadow_candidate_allowed` 必须 false；
- `evidence_anchor_required=true` 时，`formal_generation_allowed` 必须 false；
- 当前阶段所有正式链准入字段仍恒 false。

如果后续实现不新增所有建议字段，也必须保证等价信息可通过既有 `input_risk_flags`、`input_risk_warnings`、`review_reasons`、`input_evidence_required`、`evidence_anchor_required` 稳定追踪。

## 9. 与现有 input-risk guard 的集成设计

后续实现应保持：

- `suspicious_clause_reference` 不回归；
- `suspicious_standard_reference` 不回归；
- `suspicious_quantity_claim` / duration / cost 不回归；
- `direct_write_request_detected` 不回归；
- output-risk guard 不回归；
- high-quality clean advisory 不应被 `unsupported_project_fact` 规则误拦截；
- safe evidence expression 应 `review_required`，不应 `blocked`，除非叠加明显虚构断言；
- disabled / adapter-off / fake-only 行为不变；
- no-write / preview-only 边界不变；
- 所有正式链准入字段不变为 true。

建议集成方式：

- 继续在 `preview_advisory_quality_gate.py` 内扩展 input-risk scan；
- 不新增新 helper 文件；
- 不修改 endpoint；
- 不扩大 runtime transport 边界；
- 不访问 Ollama；
- 不访问外部 API；
- 不写 `output/job/export`。

## 10. deterministic tests 设计

后续实现必须覆盖以下 tests，但本步不得运行 pytest：

- unsupported project fact without evidence -> `review_required` 或 `blocked`；
- unsupported project fact with specific quantities -> strong `review_required` 或 `blocked`；
- unsupported project fact + no drawings/site records provided -> `input_risk_status` 非 `clear`；
- unsupported project fact + safe expression 需资料核验 -> `review_required`，不 `preview_ok`；
- unsupported project fact + `thinking_only_fallback` -> `blocked` 或强 `review_required`；
- output clean but `unsupported_project_fact` input -> 不得 `preview_ok`；
- IR-D equivalent fixture -> `input_risk_status` 非 `clear`；
- IR-F equivalent fixture with thinking fallback -> `blocked` 或强 `review_required`；
- evidence marker present -> 降级但不放行；
- existing Payload C equivalent remains `blocked`；
- existing direct write/export request remains `blocked`；
- existing high-quality advisory remains `preview_ok`；
- all formal chain flags remain false；
- `no_write` / route trigger / output-job-export 痕迹叠加仍 `blocked`。

建议断言：

- `input_risk_status != "clear"`；
- `quality_status != "preview_ok"`；
- `unsupported_project_fact` 或等价字段存在于 `input_risk_flags`；
- `input_risk_warnings` 或 `review_reasons` 体现 evidence missing；
- `input_evidence_required=true`；
- `evidence_anchor_required=true`；
- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`。

## 11. fake fixture 设计

后续 tests 应新增或扩展 fake fixtures：

- `unsupported_project_fact_without_evidence_fixture`；
- `unsupported_project_fact_with_quantities_fixture`；
- `no_drawings_site_records_fixture`；
- `evidence_required_safe_expression_fixture`；
- `unsupported_project_fact_with_thinking_fallback_fixture`；
- `clean_output_unsupported_input_fixture`；
- `ir_d_equivalent_fixture`；
- `ir_f_equivalent_thinking_fallback_fixture`；
- `real_but_unverified_project_fact_fixture`；
- `evidence_anchor_required_fixture`。

建议 fixture 文本：

- `本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。No drawings or site records are provided.`
- `未提供图纸和清单，但现场道路、材料堆场和作业面均已具备。`
- `未提供踏勘记录，但本项目已有2处固定加工棚和3台大型机械。`
- `需资料核验：现场塔吊、拌合站、材料堆场数量未查明，不得作为正式响应依据。`
- `本项目清单工程量已确认全部无误，但未提供清单或图纸证据。`
- `本项目评分项已满分，未提供招标文件或评分办法证据。`

明确：

- deterministic tests 不得真实访问 `127.0.0.1:11434`；
- 不得运行 Ollama；
- 不得下载模型；
- 不得写 `output/job/export`；
- 不得触发正式生成链。

## 12. 后续实现边界设计

后续如进入实现，应先单独授权。建议实现范围可包括：

- `backend/zhifei_autoplan/preview_advisory_quality_gate.py`
- `backend/tests/test_preview_advisory_quality_gate.py`
- `backend/tests/test_ollama_preview.py`
- `backend/tests/test_local_llm_preview_safe_endpoint.py`

原则上不新增新 helper 文件。

原则上不修改 endpoint。

如必须调整 endpoint response schema，需 ChatGPT 单独授权。

不得修改：

- 正式生成链；
- 正式导出链；
- ZBid 写回链；
- `output/`；
- `job/`；
- `export/`；
- 正式模板文件；
- 正式生成结果文件；
- 与 preview 无关的 UI 主流程；
- 任何会改变正式文档生成结果的代码。

## 13. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

`unsupported_project_fact` guard 是 evidence safety 的关键子门禁。没有该门禁，不得进入 shadow generation，更不得进入正式正文写回。

正式链前仍需完成：

- `unsupported_project_fact` guard implementation；
- implementation stage review；
- input-risk regression smoke refresh 或 targeted regression；
- evidence anchor 体系；
- 多 payload 多轮稳定性验证；
- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离。

即使后续 fake-only tests 通过，也只代表 deterministic guard 受控，不代表真实 runtime 或正式生成链可用。

## 14. 风险与回滚

风险：

- 风险 1：`unsupported_project_fact` 未识别，导致无证据现场事实进入后续链路；
- 风险 2：规则过严，真实但未标注证据的信息被误拦截；
- 风险 3：safe expression 被误判 `blocked`；
- 风险 4：`review_required` 被误认为可正式采用；
- 风险 5：thinking fallback 高依赖被误读为模型质量稳定；
- 风险 6：未来 shadow generation 放大输入侧事实错误；
- 风险 7：正式链写回前缺少 evidence anchor。

回滚与兜底：

- 回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 兜底措施：保留 disabled / adapter-off / fake-only 路径；
- `unsupported_project_fact` 异常应 fail-closed，不得自动放行；
- quality gate 异常应 `blocked` 或 `system_error`，不得自动放行；
- 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

## 15. 当前阶段结论

本阶段仅完成 unsupported_project_fact input-risk guard + deterministic tests 的 docs-only 设计，未实现 guard，未运行测试，未启动服务，未进入 shadow generation 或正式生成链。

IR-D 等价输入后续必须被 `input_risk_status != clear` 覆盖，且不得 `preview_ok`。该缺口解决前，不得进入 shadow generation 或正式生成链。

## 16. 下一步建议

下一步建议为 ZDoc Step 54：unsupported_project_fact input-risk guard fake-only implementation + deterministic tests。

不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
