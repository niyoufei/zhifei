# ZDoc preview advisory input-risk quality gate guard and deterministic tests design

## 1. 阶段背景

本阶段执行 ZDoc Step 47：input-risk quality gate guard + deterministic tests design。

前序阶段事实如下：

- Step 42 已完成 preview advisory quality gate fake-only implementation + deterministic tests；
- Step 45 已完成 multi-payload preview quality smoke；
- Step 46 已完成 input-risk quality gate gap design；
- Step 45 中 Payload C 含 unsupported claims，结果仅为 `review_required`，未 `blocked`；
- 当前 quality gate 对 output-risk 已具备第一版拦截能力，但 input-risk 识别不足；
- 当前不得进入 shadow generation；
- 当前不得进入 candidate patch；
- 当前不得进入正式生成链；
- 当前不得进入 DOCX 导出；
- 当前不得进入 ZBid 写回；
- Step 47 目标是锁定 input-risk guard、数据契约、测试设计、允许修改文件和回滚边界；
- 本步不得实现代码。

本步为 docs-only 设计步骤，不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`。

## 2. input-risk 缺口复述

当前缺口如下：

- 现有 quality gate 偏向评估模型输出 advisory；
- 对输入 payload 中的虚构条款、虚构规范、虚构工程量、虚构工期、虚构金额等风险识别不足；
- Payload C 暴露出 input-risk 仅被 `review_required`，而未 `blocked`；
- input-risk 不解决前，不能允许模型进入 shadow generation；
- input-risk 不解决前，不能允许模型进入 candidate patch；
- input-risk 不解决前，不能允许模型进入正式生成链；
- input-risk 应作为证据安全门禁的一部分。

现有 output-risk guard 已能在 fake-only deterministic tests 下识别输出侧虚构条款、虚构规范编号、工程量 / 金额 / 工期、正式正文替换风险、route trigger 痕迹、`output/job/export` 写入痕迹和 no-write 异常。但 Step 45 表明：如果真实模型没有在输出中复述输入侧 unsupported claims，当前 quality gate 不一定能把输入风险显式写入 blockers / warnings / review_reasons。

## 3. input-risk 与 output-risk 边界

### input-risk

input-risk 指输入内容本身存在 unsupported claim 或越权请求，包括：

- 输入内容本身存在 unsupported claim；
- 输入中包含疑似虚构招标条款；
- 输入中包含疑似虚构规范编号；
- 输入中包含疑似虚构工程量；
- 输入中包含疑似虚构工期；
- 输入中包含疑似虚构金额；
- 输入中包含无证据项目事实；
- 输入中要求模型基于未查明资料直接生成正式内容；
- 输入中要求模型直接写入、导出、写回或生成正式文件。

### output-risk

output-risk 指模型输出中出现的风险，包括：

- 模型输出新增虚构内容；
- 模型输出未标明风险；
- 模型输出正式正文替换段落；
- 模型输出“已写入”“已生成正式文档”等误导性表述；
- 模型输出低质、空泛、过长或不可追踪；
- 模型输出缺少 source / model / preview_mode / response_source；
- 模型输出触发生成链、导出链或写回链痕迹。

### 叠加规则

input-risk 与 output-risk 可叠加。

input-risk 即使未被模型扩散，也应进入 `blockers` / `warnings` / `review_reasons`。

在技术标 / 招标响应场景下，input-risk 应优先 `blocked` 或强 `review_required`。如果 input-risk 与 `thinking_only_fallback` 同时出现，应更保守，不得进入 `preview_ok`，不得进入 shadow candidate。

## 4. input-risk guard 分类设计

后续应增加以下 input-risk guard 类型：

- `suspicious_clause_reference`：疑似虚构招标条款；
- `suspicious_standard_reference`：疑似虚构规范编号；
- `suspicious_quantity_claim`：疑似虚构工程量；
- `suspicious_duration_claim`：疑似虚构工期；
- `suspicious_cost_claim`：疑似虚构金额；
- `unsupported_project_fact`：无证据项目事实；
- `evidence_required_marker`：需资料核验；
- `tender_evidence_missing`：招标依据缺失；
- `drawing_or_boq_evidence_missing`：图纸 / 清单依据缺失；
- `formal_content_request_without_evidence`：无证据要求正式生成；
- `direct_write_request_detected`：输入中出现直接写入或导出要求。

建议分类语义：

- `suspicious_*` 代表输入中存在高风险事实或高风险引用；
- `*_evidence_missing` 代表输入中缺少必要证据锚点；
- `evidence_required_marker` 代表输入中存在“需资料核验”“未查明”“待确认”等安全表达；
- `formal_content_request_without_evidence` 和 `direct_write_request_detected` 属于硬边界风险，必须 blocked。

## 5. input-risk 判定策略设计

后续实现应采用 conservative heuristic。

建议策略：

- 疑似虚构招标条款编号，如明显异常编号、测试性编号，应 `blocked`；
- 疑似虚构规范编号，如明显异常 GB 编号，应 `blocked`；
- 明显夸张或 unsupported 的工程量、工期、金额，应 `blocked` 或强 `review_required`；
- 存在“需资料核验”“未查明”“待招标文件确认”等安全表达时，可从 `blocked` 降级为 `review_required`；
- 输入要求生成正式正文、写入、导出、ZBid 写回时，应 `blocked`；
- input-risk 与 `thinking_only_fallback` 同时出现时，应更保守；
- input-risk 不得被 `status=ok` 覆盖；
- input-risk 不得被 `preview_ok` 覆盖；
- input-risk 不得被 response / advisory 内容看似干净而忽略；
- input-risk guard 异常时应 fail-closed。

建议判定顺序：

```text
input_context / original_payload
-> input-risk pattern scan
-> evidence marker scan
-> input-risk status
-> merge into quality gate blockers / warnings / review_reasons
-> P0-P4 final quality status
```

建议状态：

- `input_risk_blocked`：输入含明显高风险 unsupported claims 或直接写回 / 导出请求；
- `input_risk_review_required`：输入含不完整证据、需资料核验或弱 unsupported claims；
- `input_risk_clear`：未发现明显输入风险；
- `input_risk_system_error`：input-risk guard 自身异常，必须 fail-closed。

## 6. Payload C 专项设计

Payload C 类场景必须单独覆盖。

输入风险包括：

- 招标文件第99.99条；
- `GB99999-2099`；
- 工期999天；
- 工程量123456平方米。

这些内容都是测试性 unsupported claims，不应进入正式链路。

后续期望：

- 至少识别 `suspicious_clause_reference`；
- 至少识别 `suspicious_standard_reference`；
- 至少识别 `suspicious_duration_claim` 或 `suspicious_quantity_claim`；
- `quality_status` 应为 `blocked` 或强 `review_required`；
- `blockers` / `review_reasons` 必须体现 input-risk；
- `input_risk_flags` 必须包含上述风险或等价字段；
- `formal_generation_allowed` 必须 false；
- `shadow_candidate_allowed` 必须 false；
- `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 必须 false；
- 不得因模型输出没有复述这些 unsupported claims 而放行。

如果 Payload C 输入中明确写明“测试性表述”“不得当作真实资料”“需资料核验”，可以不一定 blocked，但必须强 `review_required`，且必须明确记录 input-risk。

## 7. data contract 设计

后续 quality gate 输出字段建议新增或稳定：

- `input_risk_status`
- `input_risk_score`
- `input_risk_flags`
- `input_risk_blockers`
- `input_risk_warnings`
- `input_evidence_required`
- `unsupported_claims_detected`
- `suspicious_references`
- `evidence_required_reasons`
- `input_risk_review_required`
- `input_risk_blocked`
- `evidence_anchor_required`

字段约束：

- input-risk 字段只能增强门禁，不得触发正式链；
- input-risk `blocked` 时，`quality_status` 必须 `blocked`；
- input-risk `review_required` 时，不得进入 `shadow_candidate`；
- input-risk `review_required` 时，`shadow_candidate_allowed=false`；
- 当前阶段 `formal_generation_allowed=false`；
- 当前阶段 `shadow_candidate_allowed=false`；
- 当前阶段 `writeback_allowed=false`；
- 当前阶段 `export_allowed=false`；
- 当前阶段 `zbid_writeback_allowed=false`。

建议保留现有 public metadata 字段，并新增 input-risk 字段作为附加 metadata。不得删除既有 `quality_status`、`quality_score`、`gate_level`、`blockers`、`warnings`、`review_reasons`、`passed_checks`、`failed_checks`。

## 8. 与现有 quality gate 的集成设计

后续实现可能需要：

- 扩展 `evaluate_preview_advisory_quality_gate` 输入参数；
- 接收 `input_context` / `original_payload` / `section` / `title` / `content`；
- 在输出中合并 input-risk `blockers` / `warnings` / `review_reasons`；
- 在 `failed_checks` 中体现 input-risk guard；
- 保持现有 output-risk guard 不回归；
- 保持 existing `attach_preview_advisory_quality_gate` 兼容；
- 不改变 disabled / adapter-off / fake-only 行为；
- 不改变 no-write / preview-only 边界；
- 不触发正式链。

建议集成方式：

- `ollama_preview.py` 继续把 normalized request 作为 quality gate context；
- `attach_preview_advisory_quality_gate` 可以在 context 中读取 `section_text`、`section_title`、`review_focus`、`source_context`；
- input-risk guard 只读取 context 和 preview response，不调用模型、不访问 Ollama、不访问外网；
- endpoint 层如果已有 `section_text` / `section_title` / `context_summary`，原则上不需要新增 endpoint 字段；
- 如果确需新增 `input_context` 或 `original_payload` 字段，必须在 Step 48 前由 ChatGPT 单独授权。

## 9. deterministic tests 设计

后续实现必须覆盖以下 deterministic tests，本步不得运行 pytest：

- input payload 含虚构招标条款 -> `blocked`；
- input payload 含虚构规范编号 -> `blocked`；
- input payload 含虚构工程量 -> `blocked` 或强 `review_required`；
- input payload 含虚构工期 -> `blocked` 或强 `review_required`；
- input payload 含虚构金额 -> `blocked` 或强 `review_required`；
- input payload 含 unsupported project fact -> `review_required` 或 `blocked`；
- input payload 含“需资料核验 / 未查明”安全表达 -> `review_required`，不应错误 blocked；
- input-risk + `thinking_only_fallback` -> `blocked` 或强 `review_required`；
- output clean 但 input high-risk -> 不得 `preview_ok`；
- Payload C 等价 fixture -> `blocked` 或强 `review_required`；
- `formal_generation_allowed` 恒 false；
- `shadow_candidate_allowed` 恒 false；
- `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 恒 false；
- `no_write=false` 与 input-risk 叠加 -> `blocked`；
- route trigger 痕迹与 input-risk 叠加 -> `blocked`；
- `output/job/export` 写入痕迹与 input-risk 叠加 -> `blocked`；
- input-risk guard 内部异常 -> controlled `system_error` 或 fail-closed；
- input-risk 不得被 `status=ok` 覆盖；
- input-risk 不得被 `quality_status=preview_ok` 覆盖。

测试必须证明：input-risk 的判定不依赖模型是否在 advisory 中复述输入风险。

## 10. fake fixture 设计

后续 tests 应新增 fake fixtures：

- `input_fake_tender_clause_fixture`；
- `input_fake_standard_reference_fixture`；
- `input_fake_quantity_claim_fixture`；
- `input_fake_duration_claim_fixture`；
- `input_fake_cost_claim_fixture`；
- `input_unsupported_project_fact_fixture`；
- `input_evidence_required_safe_fixture`；
- `input_risk_with_thinking_fallback_fixture`；
- `input_clean_output_risky_input_fixture`；
- `input_direct_write_request_fixture`。

fixture 设计要求：

- fake response 可以保持 clean advisory，以证明 input-risk 独立生效；
- fake response 可以使用 `thinking_only_fallback`，以证明叠加风险更保守；
- fake context 必须包含 `section_text` / `section_title` 或等价输入内容；
- fake fixture 不得包含真实招标文件内容；
- fake fixture 不得包含真实项目敏感资料；
- fake fixture 中的条款、规范、工程量、工期、金额必须明确为测试占位。

deterministic tests 不得真实访问 `127.0.0.1:11434`，不得运行 Ollama，不得下载模型，不得写 `output/job/export`，不得触发正式生成链。

## 11. 后续实现边界设计

后续 Step 48 如进入 input-risk fake-only implementation，应先由 ChatGPT 单独授权。

建议允许范围可包括：

- `backend/zhifei_autoplan/preview_advisory_quality_gate.py`
- `backend/tests/test_preview_advisory_quality_gate.py`
- `backend/zhifei_autoplan/ollama_preview.py`
- `backend/tests/test_ollama_preview.py`
- 必要时 `backend/tests/test_local_llm_preview_safe_endpoint.py`

原则上不新增新 helper 文件，除非 Step 48 指令另行授权。

原则上不修改 endpoint，除非需要传递 `input_context` 且经 ChatGPT 授权。

后续实现仍必须：

- 不修改正式生成链；
- 不修改正式导出链；
- 不接 ZBid 写回；
- 不写 `output/job/export`；
- 不改变正式文档生成结果；
- 不使任何正式链准入字段变为 true。

## 12. 禁止触碰范围

后续不得修改：

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

后续不得执行：

- 下载或拉取模型；
- 访问外网；
- 启动正式服务；
- 触发 DOCX / JSON / Markdown 正式导出；
- 将 preview advisory 或 input-risk 结果写入正式章节。

## 13. 与正式生成链接入目标的关系

最终目标是让本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

input-risk gate 是正式链前的证据安全门禁。没有 input-risk gate，不得进入 shadow generation，更不得进入正式生成链。

正式链前仍需完成：

- input-risk quality gate implementation；
- input-risk stage review；
- multi-payload input-risk regression smoke；
- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- evidence anchor 体系；
- 证据缺失时的 fail-closed 策略；
- 正式链回滚机制。

即使 input-risk gate 后续实现通过 fake-only deterministic tests，也仍不能直接进入正式链。

## 14. 风险与回滚

主要风险如下：

- 风险 1：input-risk 规则过宽，虚构信息进入后续链路；
- 风险 2：input-risk 规则过严，真实但未标注证据的信息被误拦截；
- 风险 3：`review_required` 被误当作可正式采用；
- 风险 4：thinking fallback 与 input-risk 叠加后仍被误判；
- 风险 5：后续 shadow generation 放大输入侧错误；
- 风险 6：正式链写回前缺少 evidence anchor。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 保留 disabled / adapter-off / fake-only 路径；
- input-risk 异常应 fail-closed，不得自动放行；
- input-risk guard 不得删除现有 output-risk guard；
- 出现异常时不得扩大到正式链路；
- 不得删除 fake fixture deterministic tests。

## 15. 当前阶段结论

本阶段仅完成 input-risk quality gate guard + deterministic tests 的 docs-only 设计，未实现 input-risk gate，未运行测试，未启动服务，未进入 shadow generation 或正式生成链。

Step 47 的核心结论是：input-risk 应作为独立证据安全门禁进入 quality gate，并且不得被 `status=ok`、`calls_ollama=true`、`preview_ok` 或 clean advisory 输出掩盖。

## 16. 下一步建议

下一步建议为 ZDoc Step 48：input-risk quality gate fake-only implementation + deterministic tests。

不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
