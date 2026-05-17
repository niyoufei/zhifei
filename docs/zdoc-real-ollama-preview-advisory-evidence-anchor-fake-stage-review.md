# ZDoc Evidence Anchor Fake Stage Review

## 1. 阶段目标回顾

Step 61 的目标是实现 evidence anchor fake-only 第一版，通过 deterministic tests 验证证据来源类型、证据锚点状态、必须锚定内容、not_required 内容、input-risk / quality gate 集成、thinking fallback 防护、DOCX / ZBid / candidate patch 防护，并继续保持 preview-only、no-write、正式链准入字段恒 false。

本阶段只面向 preview metadata 与 fake-only deterministic tests，不代表真实 runtime 多 payload 稳定，也不代表可以进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

## 2. 实际完成情况

Step 61 已经完成：

* 新增 `backend/zhifei_autoplan/evidence_anchor.py`；
* 新增 `backend/tests/test_evidence_anchor.py`；
* 修改 `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
* 修改 `backend/tests/test_preview_advisory_quality_gate.py`；
* 修改 `backend/tests/test_ollama_preview.py`；
* 修改 `backend/tests/test_local_llm_preview_safe_endpoint.py`；
* 未修改正式生成链；
* 未修改正式导出链；
* 未修改 ZBid 写回链；
* 未写 `output/job/export`；
* 未触发 DOCX/JSON/Markdown 正式导出。

`backend/zhifei_autoplan/ollama_preview.py` 与 `backend/app/routers/local_llm_preview_safe.py` 在 Step 61 中未作为实现改动文件，但相关回归测试覆盖了 Ollama preview 与 safe endpoint metadata 行为。

## 3. 测试结果复盘

测试命令：

```bash
python3 -m pytest backend/tests/test_evidence_anchor.py backend/tests/test_preview_advisory_quality_gate.py backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

测试过程：

首次同命令失败后，在允许文件范围内修复，最终通过。

最终结果：

```text
228 passed in 3.55s
```

覆盖场景包括：

* evidence anchor helper；
* quality gate 集成；
* Ollama preview 回归；
* safe endpoint metadata 回归；
* evidence source 类型；
* evidence anchor 状态；
* 必须 evidence anchor 内容；
* not_required 内容；
* input-risk / quality gate 集成；
* thinking fallback + evidence anchor；
* DOCX / ZBid / candidate patch 防护；
* formal/write/export/zbid 准入字段恒 false。

## 4. evidence anchor helper 复盘

Step 61 新增 `evaluate_evidence_anchor`，定位是 evidence anchor fake-only helper。

该 helper 只返回 preview metadata：

* 不生成正式正文；
* 不触发生成链；
* 不触发导出链；
* 不触发 ZBid 写回；
* 不调用模型；
* 不访问 Ollama；
* 不访问外部 API；
* 不写 `output/job/export`。

helper 输出包括 evidence anchor required/status/level、evidence source 摘要、missing reasons、unsupported claims、unsupported project facts、unverified parameters、trace 字段以及正式链准入字段。所有正式链准入字段继续固定为 false。

## 5. evidence source 类型复盘

Step 61 已覆盖以下 evidence source 类型：

* `tender_document`；
* `tender_addendum`；
* `scoring_criteria`；
* `drawing`；
* `boq`；
* `site_survey`；
* `photos`；
* `contract_or_owner_requirement`；
* `standard_or_code`；
* `user_provided_context`；
* `system_generated_preview`；
* `unknown_or_unverified`。

规则复盘：

* `system_generated_preview` 不得作为事实证据；
* `unknown_or_unverified` 必须进入 review_required 或 blocked；
* `standard_or_code` 缺编号、版本或来源时不得 anchored；
* `user_provided_context` 只能作为用户输入来源，不等同于已核验证据。

强证据来源如招标文件、答疑补遗、评分办法、图纸、清单、踏勘记录、照片、合同或建设单位要求、规范标准，需要可追踪的 source identity，并需要 location / page / clause 至少一种定位方式。

## 6. evidence anchor 状态复盘

Step 61 已覆盖以下状态：

* `anchored`；
* `partially_anchored`；
* `missing`；
* `conflicting`；
* `unverified`；
* `not_required`；
* `invalid_anchor`；
* `system_error`。

状态边界：

* `anchored` 只表示证据来源满足第一版锚点条件，也不代表正式链准入；
* `missing` / `conflicting` / `unverified` / `invalid_anchor` / `system_error` 均不得进入 shadow_candidate；
* `not_required` 仅适用于低风险泛化建议；
* 当前阶段 `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 仍全部为 false。

## 7. 必须 evidence anchor 内容复盘

Step 61 已覆盖或纳入规则的必须 evidence anchor 内容包括：

* 招标条款；
* 评分办法；
* 答疑 / 补遗 / 澄清；
* 图纸内容；
* 工程量清单；
* 工程量、工期、金额、质量目标、安全文明目标；
* 现场条件、临时道路、材料堆场、机械设备、作业面、管线；
* 规范编号和版本；
* 施工参数、验收标准、检查频次；
* 项目名称、建设单位、工期节点、分区、专业系统；
* formal chain attempt 相关内容。

一旦 advisory、input context 或 future formal attempt 涉及事实性内容、正式链写回、DOCX 导出、ZBid 写回或 candidate patch，均应进入 evidence anchor 检查。

## 8. not_required 内容复盘

高质量但不含具体事实的 advisory 可为 `not_required`。

结构优化、语言精简、风险提醒、资料补充提醒、参数需核验提醒、人工确认提醒等低风险建议，可在不含具体条款、参数、数量、金额、规范编号、现场事实时标记为 `not_required`。

`not_required` 不等于正式链准入。即使 evidence anchor 不要求证据，`formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 仍为 false。

## 9. input-risk / quality gate 集成复盘

Step 61 已将 input-risk 与 evidence anchor 合并到 preview advisory quality gate：

* input-risk 可驱动 evidence metadata；
* unsupported facts 可进入 `missing` / review；
* strong unsupported claims 可进入 `invalid_anchor` / blocked；
* `quality_status=preview_ok` 不等于 `evidence_anchor_status=anchored`；
* `evidence_anchor_status=anchored` 不等于 `formal_generation_allowed=true`；
* existing input-risk / unsupported_project_fact 行为未回归。

在 quality gate 中，input-risk blockers、unsupported_project_fact、evidence_source_missing、project_fact_without_evidence、thinking fallback 等信号可共同影响 evidence anchor metadata，并通过 blockers / warnings / review_reasons 进入可追踪结果。

## 10. thinking fallback + evidence anchor 复盘

Step 61 明确：

* thinking fallback 不得作为 evidence；
* thinking fallback factual claim 需要 evidence anchor；
* thinking fallback 不得进入 shadow_candidate；
* thinking fallback 不得触发 DOCX 导出；
* thinking fallback 不得触发 ZBid 写回；
* thinking fallback 高依赖仍是后续风险。

如 `preview_mode=thinking_only_fallback` 且内容含事实性 claim，evidence anchor 会要求证据锚点，并进入 review_required 或 blocked 路径；该内容不得作为正式正文或事实依据。

## 11. DOCX / ZBid / candidate patch 防护复盘

Step 61 已覆盖：

* ZBid writeback attempted without evidence -> blocked；
* DOCX export attempted without evidence -> blocked；
* candidate patch without evidence -> blocked；
* model-generated preview as evidence -> blocked；
* `formal_generation_allowed` 恒 false；
* `shadow_candidate_allowed` 恒 false；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 恒 false。

该防护仍属于 preview metadata 与 deterministic tests 层，不代表正式导出链或 ZBid 写回链已经接入。

## 12. 已证明的事实

Step 61 已证明：

* evidence anchor helper 在 fake-only deterministic tests 下可控；
* evidence source 类型、状态机、必须锚定内容、not_required 内容已具备第一版规则；
* model-generated preview 不得作为 evidence；
* input-risk 与 evidence anchor 已可集成；
* thinking fallback factual claim 需要 evidence anchor；
* DOCX / ZBid / candidate patch 无证据尝试可被 blocked；
* existing `ollama_preview` 与 safe endpoint 回归通过；
* 未触发正式链路；
* 未写 `output/job/export`。

## 13. 尚未证明的事项

当前尚未证明：

* 未启动真实 Ollama；
* 未启动 FastAPI；
* 未做 evidence-aware runtime smoke；
* 未验证真实 runtime advisory 的 evidence anchor metadata；
* 未验证真实多 payload 下 evidence anchor 稳定性；
* 未验证真实招标文件、图纸、清单、踏勘资料的 evidence source 映射；
* 未进入 shadow generation；
* 未进入 candidate patch；
* 未进入人工确认写回；
* 未进入 DOCX 导出一致性校核；
* 未进入 ZBid 写回隔离。

## 14. 当前风险

当前风险包括：

* fake-only conservative heuristic 可能误拦截或漏过复杂证据问题；
* evidence source 真实映射尚未接入；
* thinking fallback 高依赖仍可能产生无证据事实；
* `anchored` 可能被误解为正式链准入；
* `not_required` 可能被误解为无需审核；
* 后续 shadow generation 如未强制 evidence trace，可能污染正式正文；
* DOCX / ZBid 写回前 evidence trace 仍未经过端到端验证。

## 15. 回滚边界

回滚与兜底边界：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
* 保留 disabled / adapter-off / fake-only 路径；
* evidence anchor 异常时应 blocked 或 system_error，不得自动放行；
* quality gate 异常时应 blocked 或 system_error，不得自动放行；
* 不得删除 fake fixture deterministic tests；
* 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

## 16. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 Step 61 只是 evidence anchor 的 fake-only 第一版。

正式链前仍需完成：

* evidence anchor stage review；
* evidence-aware multi-payload smoke plan；
* evidence-aware multi-payload smoke；
* shadow generation 设计；
* candidate patch 设计；
* 人工确认写回；
* diff 展示；
* 版本回滚；
* DOCX 导出一致性校核；
* ZBid 写回隔离；
* 真实资料证据源映射。

## 17. 当前阶段结论

本阶段仅证明 evidence anchor 在 fake-only deterministic tests 下可控，不代表真实 runtime evidence anchor 多 payload 稳定，不代表真实招标/图纸/清单资料已完成证据映射，不代表可进入 shadow generation 或正式生成链。

## 18. 下一步建议

下一步建议为 ZDoc Step 63：evidence-aware multi-payload smoke plan，先做 docs-only 计划。不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
