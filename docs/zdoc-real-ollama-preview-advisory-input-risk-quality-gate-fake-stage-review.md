# ZDoc preview advisory input-risk quality gate fake stage review

## 1. 阶段目标回顾

本阶段复盘 ZDoc Step 48：input-risk quality gate fake-only implementation + deterministic tests。

Step 48 的目标是实现 input-risk quality gate 的 fake-only 第一版，通过 deterministic tests 识别输入侧 unsupported claims，补强 Step 45 / Step 46 中 Payload C 暴露的 input-risk 缺口，并继续保持 preview-only、no-write 和正式链准入字段恒 false。

本阶段目标不是 runtime smoke，不是 shadow generation，不是 candidate patch，不是正式正文写回，不是 DOCX 导出，也不是 ZBid 写回。

## 2. 实际完成情况

本阶段已经完成以下变更：

- 修改 `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
- 修改 `backend/tests/test_preview_advisory_quality_gate.py`；
- 修改 `backend/tests/test_ollama_preview.py`；
- 修改 `backend/tests/test_local_llm_preview_safe_endpoint.py`；
- 未新增文件；
- 未修改 docs；
- 未修改正式生成链；
- 未修改正式导出链；
- 未修改 ZBid 写回链；
- 未写 `output/job/export`；
- 未触发 DOCX / JSON / Markdown 正式导出。

实现层面已经将 input-risk 检查纳入 preview advisory quality gate metadata。quality gate 现在不仅评估 advisory 输出，也会读取传入的 input context / payload 字段，并将输入侧风险合并到 `blockers`、`warnings`、`review_reasons`、`failed_checks` 和新增 input-risk metadata 中。

`ollama_preview.py` 继续以 normalized request 作为 quality gate context，未改变 disabled / adapter-off / fake-only / real transport fake fixture 的调用边界。safe endpoint 未修改代码，通过既有 adapter payload 与 response metadata 透传路径完成回归验证。

## 3. 测试结果复盘

测试命令：

```bash
python3 -m pytest backend/tests/test_preview_advisory_quality_gate.py backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

测试过程：

- 首次同命令失败；
- 失败原因集中在 `GB99999-2099` 紧贴中文文本时，input-risk 规范编号识别正则未匹配；
- 在允许文件范围内修复 `suspicious_standard_reference` 的本地启发式正则；
- 仅重跑同一条授权 pytest 命令；
- 最终通过。

最终结果：

```text
191 passed in 3.20s
```

覆盖场景包括：

- input-risk helper；
- Payload C 等价输入；
- `ollama_preview` 传递 input context；
- safe endpoint metadata 回归；
- no-write / preview-only 回归；
- `suspicious_clause_reference`；
- `suspicious_standard_reference`；
- `suspicious_quantity_claim`；
- `suspicious_duration_claim`；
- `suspicious_cost_claim`；
- `unsupported_project_fact`；
- `evidence_required` safe expression；
- input-risk + `thinking_only_fallback`；
- output clean but input high-risk；
- `no_write` / route trigger / output-job-export 写入痕迹叠加；
- existing high-quality / vague / hallucinated output / thinking fallback 回归。

## 4. input-risk 字段复盘

本阶段新增或稳定了以下 input-risk metadata 字段：

- `input_risk_status`；
- `input_risk_score`；
- `input_risk_flags`；
- `input_risk_blockers`；
- `input_risk_warnings`；
- `input_evidence_required`；
- `unsupported_claims_detected`；
- `suspicious_references`；
- `evidence_required_reasons`；
- `input_risk_review_required`；
- `input_risk_blocked`；
- `evidence_anchor_required`。

这些字段只用于 preview quality gate metadata：

- 不触发正式链；
- 不允许写正式正文；
- 不允许进入 `shadow_candidate`；
- 不允许 DOCX 导出；
- 不允许 ZBid 写回；
- 不改变 preview-only / no-write 边界。

当前阶段所有正式链准入字段仍恒为 false：

- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`。

## 5. input-risk guard 复盘

### suspicious_clause_reference

虚构招标条款输入已被识别并 `blocked`。

测试覆盖了类似“招标文件第99.99条要求采用特殊工艺”的输入。该风险会进入：

- `input_risk_flags`；
- `input_risk_blockers`；
- `blockers` 中的 `input_risk:suspicious_clause_reference`。

### suspicious_standard_reference

`GB99999-2099` 等测试性规范编号已被识别并 `blocked`。

实现修复了规范编号与中文文本相邻时的匹配问题，避免 Payload C 等价输入漏识别。

### suspicious_quantity_claim / suspicious_duration_claim / suspicious_cost_claim

虚构工程量、工期、金额均已覆盖，进入 `blocked` 或强门禁路径。

测试覆盖了：

- `工程量为123456平方米`；
- `工期999天`；
- `造价999万元`。

这些输入会进入 `input_risk_flags` / `input_risk_blockers`，并通过 `input_risk:*` 合并到总 quality gate blockers。

### unsupported_project_fact

无证据项目事实进入 `review_required`。

测试覆盖了类似“本项目必须采用指定品牌泵站设备”的输入。该类风险不会被误判为 `preview_ok`，并会进入：

- `input_risk_flags`；
- `input_risk_warnings`；
- `review_reasons` 中的 `input_risk:unsupported_project_fact`。

### evidence_required_marker

含“需资料核验”等安全表达时降级为 `review_required`，不误判 `preview_ok`。

测试覆盖了带有“需资料核验”的高风险输入组合。该路径会保留 input-risk flags 和 evidence reasons，但不直接 blocked，避免把明确标注为待核验的输入误判为最终事实。

### direct_write_request_detected / route trigger / output-job-export 痕迹

直接写入、导出 DOCX、写回 ZBid 等输入请求会被 `blocked`。

当 input-risk 与 `no_write=false`、route trigger 痕迹、`output/job/export` 写入痕迹叠加时，均保持 `blocked`，并保持 P0 / 正式链安全边界。

## 6. Payload C 等价场景复盘

Payload C 等价输入包含：

- 招标文件第99.99条；
- `GB99999-2099`；
- 工期999天；
- 工程量123456平方米。

当前 fake-only deterministic tests 下的结果：

- 条款风险已识别；
- 规范编号风险已识别；
- 工期 / 工程量风险已识别；
- `quality_status=blocked`；
- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`。

该结果修复了 Step 45 / Step 46 暴露的 Payload C 仅 `review_required` 未 `blocked` 的缺口。

需要注意：当前证明仍仅限 fake-only deterministic tests。真实 runtime 或 multi-payload regression smoke 尚未执行，不能据此判断真实链路下 Payload C 类输入一定稳定 blocked。

## 7. input-risk 与 output-risk 集成复盘

本阶段保持了现有 output-risk guard 不回归：

- high-quality advisory 仍可 `preview_ok`；
- vague advisory 仍 `review_required`；
- hallucinated output 仍 `blocked`；
- thinking fallback 仍降级；
- suggestions / risk_notes 上限仍保持；
- no-write / preview-only 边界仍保持。

新增 input-risk 后，以下集成规则已经通过 deterministic tests 验证：

- input high-risk + output clean 时不得 `preview_ok`；
- input-risk 不被 `status=ok` 掩盖；
- input-risk 不被 advisory 文本质量掩盖；
- input-risk + `thinking_only_fallback` 时更保守；
- input-risk 不得让任何正式链准入字段变 true。

## 8. P0-P4 边界复盘

本阶段未破坏既有 P0-P4 guard：

- P0 安全边界仍有效；
- P1 响应完整性仍有效；
- P2 输出模式 guard 仍有效；
- P3 技术质量 guard 仍有效；
- P4 正式链准入 guard 仍有效。

以下字段所有状态下仍恒为 false：

- `formal_generation_allowed`；
- `shadow_candidate_allowed`；
- `writeback_allowed`；
- `export_allowed`；
- `zbid_writeback_allowed`。

`preview_ok` 仍不代表正式链准入。

`blocked` / `review_required` / `preview_ok` 均不得进入 shadow generation。

## 9. 已证明的事实

本阶段已经证明：

- input-risk gate 在 fake-only deterministic tests 下可控；
- Payload C 等价 unsupported claims 已能 `blocked`；
- 输入侧虚构条款、规范编号、工期、工程量、金额可被识别；
- 无证据项目事实可被降级为 `review_required`；
- evidence required safe expression 可被识别并保持人工复核边界；
- input-risk + thinking fallback 更保守；
- output clean but input high-risk 不会 `preview_ok`；
- no-write / preview-only 边界未破坏；
- existing quality gate 回归通过；
- `ollama_preview` 回归通过；
- safe endpoint 回归通过；
- 未触发正式链路；
- 未写 `output/job/export`。

## 10. 尚未证明的事项

本阶段尚未证明：

- 未启动真实 Ollama；
- 未启动 FastAPI；
- 未做 input-risk runtime regression smoke；
- 未验证真实 runtime Payload C 类输入是否 `blocked`；
- 未验证多 payload input-risk 在真实 runtime 下稳定；
- 未验证真实技术标材料的 evidence anchor 识别；
- 未验证更复杂 unsupported claims 的召回率；
- 未验证真实招标文件、图纸、清单、补疑材料的证据锚点体系；
- 未进入 shadow generation；
- 未进入 candidate patch；
- 未进入人工确认写回；
- 未进入 DOCX 导出一致性校核；
- 未进入 ZBid 写回隔离。

## 11. 当前风险

当前主要风险如下：

- conservative heuristic 可能误拦截真实但缺少证据标记的信息；
- input-risk 规则可能仍漏过更复杂的 unsupported claims；
- `review_required` 被误当作可正式采用；
- `blocked` 被误解为系统不可用而非质量拦截；
- 后续 shadow generation 如忽略 input-risk，可能放大输入侧错误；
- evidence anchor 体系尚未建立，正式链仍不可进入。

这些风险不影响当前 preview-only / fake-only deterministic tests 的结论，但会影响后续 runtime regression smoke、shadow generation 和正式链准入设计。

## 12. 回滚边界

回滚与兜底边界如下：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
- 保留 disabled / adapter-off / fake-only 路径；
- quality gate 异常时应 `blocked` 或 `system_error`，不得自动放行；
- input-risk 异常应 fail-closed，不得自动放行；
- 不得删除 fake fixture deterministic tests；
- 当前阶段不涉及正式正文写回；
- 当前阶段不涉及 DOCX 导出；
- 当前阶段不涉及 ZBid 写回。

## 13. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 Step 48 只是 input-risk quality gate 的 fake-only 第一版。正式链前仍需完成：

- input-risk stage review；
- input-risk runtime 或 multi-payload regression smoke plan；
- input-risk runtime 或 multi-payload regression smoke；
- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- evidence anchor 体系。

没有真实 runtime regression、质量稳定性验证、evidence anchor 和人工确认写回机制之前，不得进入正式生成链。

## 14. 当前阶段结论

本阶段仅证明 input-risk quality gate 在 fake-only deterministic tests 下可控，不代表真实 runtime input-risk 多 payload 稳定，不代表可进入 shadow generation，不代表可进入正式生成链。

Step 48 的核心结论是：input-risk 已能作为 preview quality gate metadata 的独立门禁进入 fake-only 测试闭环，并能阻断 Payload C 等价 unsupported claims；但该能力仍需后续 runtime 或 multi-payload regression smoke 单独验证。

## 15. 下一步建议

下一步建议为 ZDoc Step 50：input-risk multi-payload regression smoke plan，先做 docs-only 计划。

不得直接进入 runtime smoke，不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
