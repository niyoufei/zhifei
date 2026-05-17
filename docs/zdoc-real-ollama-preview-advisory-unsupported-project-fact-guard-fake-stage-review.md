# ZDoc unsupported_project_fact input-risk guard fake-stage review

## 1. 阶段目标回顾

本阶段复盘 ZDoc Step 54：unsupported_project_fact input-risk guard fake-only implementation + deterministic tests。

Step 54 的目标是：实现 `unsupported_project_fact` input-risk guard 的 fake-only 第一版，通过 deterministic tests 修复 IR-D 等价场景 `input_risk_status=clear` 的缺口，并继续保持 preview-only、no-write 和正式链准入字段恒 false。

该目标聚焦 input-risk / evidence safety 子门禁，不进入 runtime smoke，不进入 shadow generation，不接正式生成链、DOCX 导出链或 ZBid 写回链。

## 2. 实际完成情况

本阶段已经完成：

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
- 未触发 DOCX/JSON/Markdown 正式导出。

实现仍然保持在 preview advisory quality gate metadata 范围内。`unsupported_project_fact` 相关判断只影响 quality gate 的状态、flags、warnings、review reasons 和正式链准入字段，不生成正式正文，不触发导出，不写回 ZBid。

## 3. 测试结果复盘

Step 54 授权并执行的测试命令为：

```bash
python3 -m pytest backend/tests/test_preview_advisory_quality_gate.py backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

测试结果：

```text
198 passed in 6.87s
```

覆盖场景包括：

- IR-D 等价输入；
- no drawings / site records + specific fact；
- safe expression；
- `unsupported_project_fact + thinking_only_fallback`；
- output clean but unsupported input；
- Payload C 回归；
- direct write 回归；
- high-quality advisory 回归；
- vague advisory 回归；
- hallucinated output 回归；
- thinking fallback 回归；
- endpoint metadata 回归。

测试均为 fake fixture / monkeypatch / dependency injection 路径，不依赖真实 Ollama runtime，不真实访问 `127.0.0.1:11434`，不启动服务，不运行 `ollama serve`。

## 4. unsupported_project_fact 字段复盘

本阶段新增或稳定了以下字段：

- `unsupported_project_fact_detected`；
- `evidence_source_missing`；
- `project_fact_without_evidence`；
- `evidence_anchor_required`；
- `input_evidence_required`；
- `evidence_required_reasons`；
- `input_risk_status`；
- `input_risk_score`；
- `input_risk_flags`；
- `input_risk_blockers`；
- `input_risk_warnings`；
- `input_risk_review_required`；
- `input_risk_blocked`。

这些字段仅作为 preview quality gate metadata：

- 不触发正式链；
- 不允许写正式正文；
- 不允许进入 `shadow_candidate`；
- 不允许 DOCX 导出；
- 不允许 ZBid 写回。

正式链准入字段继续恒为 false：

- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`。

## 5. IR-D 等价场景复盘

IR-D 等价输入为：

```text
本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。No drawings or site records are provided.
```

当前 fake-only deterministic tests 结果：

- `input_risk_status` 不再为 `clear`；
- 不得 `preview_ok`；
- evidence / source 风险被标记；
- `unsupported_project_fact` 或 `evidence_required` 相关字段可追踪；
- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`。

该结果修复了 Step 51 / Step 52 暴露的 IR-D input-risk 未触发缺口。但这仍是 fake-only deterministic tests 证明，后续仍需 runtime regression smoke 验证真实链路表现。

## 6. no drawings / site records + specific fact 复盘

Step 54 已覆盖“证据缺失 + 具体现场事实数量断言”的 input-risk 判定。

当前规则下，以下组合会进入 `review_required` 或更强门禁：

- `No drawings or site records are provided` 与具体现场事实同现；
- 未提供图纸、清单、踏勘记录、现场记录等证据来源；
- 同时断言具体现场事实数量。

具体现场事实包括：

- 机械；
- 设备；
- 材料堆场；
- 作业面；
- 道路；
- 管线；
- 塔吊；
- 拌合站；
- 临建或加工棚。

该类输入不得 `preview_ok`，不得进入 `shadow_candidate`，正式链准入字段必须恒 false。

## 7. safe expression 复盘

Step 54 已覆盖 safe expression 降级路径。

含以下安全表达时，可降级为 `review_required`：

- “需资料核验”；
- “未查明”；
- “待招标文件确认”；
- “待图纸/清单/踏勘记录核验”；
- “不得作为正式响应依据”。

该路径不应误判为 `blocked`，除非叠加明显虚构断言、直接写入/导出请求或其他 P0/P3 高风险因素。但 safe expression 也不能放行：

- 不得 `preview_ok`；
- 不得进入 `shadow_candidate`；
- `evidence_anchor_required` 或 `input_evidence_required` 仍应可追踪；
- 正式链准入字段仍恒 false。

safe expression 的作用是提醒人工核验证据，不是允许进入正式写回。

## 8. unsupported_project_fact + thinking_only_fallback 复盘

Step 54 已覆盖 `unsupported_project_fact` 与 `thinking_only_fallback` 叠加路径。

当前判定要求：

- `unsupported_project_fact` 与 `thinking_only_fallback` 叠加时保持 `review_required` 或更保守；
- 同时体现 fallback 与 input-risk；
- 不进入 `shadow_candidate`；
- 不进入正式生成链；
- 不触发 DOCX 导出；
- 不触发 ZBid 写回。

这意味着 thinking fallback 不能掩盖 input-risk，input-risk 也不能被模型输出的 `status=ok` 或 advisory 文本质量覆盖。

## 9. output clean but unsupported input 复盘

Step 54 已覆盖 output clean but unsupported input 场景。

即使 advisory 文本干净、具体、质量较好，只要 `input_context` 包含 `unsupported_project_fact`：

- 也不得 `preview_ok`；
- `input_risk_status` 不得为 `clear`；
- input-risk metadata 必须保留；
- `warnings` / `review_reasons` 必须体现 input-risk；
- status=ok 不得覆盖 input-risk；
- output quality 不得掩盖 input-risk。

该规则防止高质量表面输出把无证据输入包装为可用建议。

## 10. 既有行为回归复盘

Step 54 回归确认以下行为未回归：

- Payload C 等价 fixture 仍 `blocked`；
- direct write/export request 仍 `blocked`；
- `suspicious_clause_reference` 不回归；
- `suspicious_standard_reference` 不回归；
- `suspicious_quantity_claim` / duration / cost 不回归；
- high-quality clean advisory 不被误 `blocked`；
- vague advisory 仍 `review_required`；
- hallucinated output 仍 `blocked`；
- `thinking_only_fallback` 仍降级；
- `no_write=false` 仍 `blocked`；
- route trigger 痕迹仍 `blocked`；
- `output/job/export` 写入痕迹仍 `blocked`；
- disabled / adapter-off / fake-only 行为不回归；
- no-write / preview-only 边界不变。

这些回归说明新增 `unsupported_project_fact` guard 没有扩大到正式生成链，也没有破坏既有 output-risk、P0 安全边界、P2 fallback 降级或 P4 formal-ineligible 约束。

## 11. 已证明的事实

本阶段已证明：

- `unsupported_project_fact` guard 在 fake-only deterministic tests 下可控；
- IR-D 等价输入可被识别为 input-risk；
- 证据缺失 + 具体现场事实数量断言不再 `clear`；
- safe expression 可被降级但不误杀；
- `unsupported_project_fact + thinking fallback` 更保守；
- output clean but unsupported input 不得 `preview_ok`；
- existing quality gate、`ollama_preview` 与 safe endpoint 回归通过；
- 未触发正式链路；
- 未写 `output/job/export`。

这些事实只证明 fake-only deterministic behavior，不证明真实 runtime 多 payload 稳定。

## 12. 尚未证明的事项

本阶段尚未证明：

- 未启动真实 Ollama；
- 未启动 FastAPI；
- 未做 runtime regression smoke；
- 未验证真实 runtime IR-D 类输入是否 `input_risk_status` 非 `clear`；
- 未验证多 payload 下 `unsupported_project_fact` 稳定性；
- 未验证真实技术标材料的 evidence anchor 识别；
- 未进入 shadow generation；
- 未进入 candidate patch；
- 未进入人工确认写回；
- 未进入 DOCX 导出一致性校核；
- 未进入 ZBid 写回隔离。

因此，Step 54 不能作为进入 shadow generation 或正式生成链的依据。

## 13. 当前风险

当前风险包括：

- conservative heuristic 可能误拦截真实但缺少证据标记的信息；
- `unsupported_project_fact` 规则可能仍漏过更隐蔽无证据项目事实；
- safe expression 可能被用户误认为可直接正式采用；
- `review_required` 被误当作可写入正式正文；
- 后续 shadow generation 如忽略 evidence anchor，可能放大输入侧事实错误；
- evidence anchor 体系尚未建立，正式链仍不可进入。

这些风险要求后续继续维持 fail-closed 策略：质量门禁异常、input-risk 异常或证据缺失时，不得自动放行到正式链。

## 14. 回滚边界

回滚边界如下：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
- 保留 disabled / adapter-off / fake-only 路径；
- quality gate 异常时应 `blocked` 或 `system_error`，不得自动放行；
- `unsupported_project_fact` 异常应 fail-closed，不得自动放行；
- 不得删除 fake fixture deterministic tests；
- 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

如后续 runtime regression 出现异常，应限制在 preview advisory / input-risk metadata 范围内处理，不得扩大到正式生成链路。

## 15. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 Step 54 只是 `unsupported_project_fact` guard 的 fake-only 第一版。

正式链前仍需完成：

- `unsupported_project_fact` stage review；
- targeted runtime regression smoke plan；
- targeted runtime regression smoke；
- evidence anchor 体系；
- 多 payload 多轮稳定性验证；
- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离。

在这些阶段完成前，`preview_ok`、`review_required` 或 `blocked` 都不得被解释为正式链准入。

## 16. 当前阶段结论

本阶段仅证明 `unsupported_project_fact` guard 在 fake-only deterministic tests 下可控，不代表真实 runtime `unsupported_project_fact` 多 payload 稳定，不代表可进入 shadow generation，不代表可进入正式生成链。

## 17. 下一步建议

下一步建议为 ZDoc Step 56：unsupported_project_fact targeted runtime regression smoke plan，先做 docs-only 计划。不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
