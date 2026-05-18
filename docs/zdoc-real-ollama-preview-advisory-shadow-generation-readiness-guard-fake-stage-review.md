# ZDoc Shadow Generation Readiness Guard Fake Stage Review

## 1. 阶段目标回顾

Step 95 的目标是实现 shadow generation readiness guard 的 fake-only 第一版，通过 deterministic tests 验证 readiness 状态、quality/input-risk/evidence/response-mode guard、thinking fallback guard、generated-preview-as-evidence guard、candidate patch 防护、human approval、diff/rollback、DOCX/ZBid 防护，并继续保持所有正式链准入字段恒 false。

该阶段不是 shadow generation implementation，不生成 candidate patch，不写正式正文，不进入 DOCX 导出，不接 ZBid 写回。

## 2. 实际完成情况

本阶段已经完成：

* 新增 `backend/zhifei_autoplan/shadow_generation_readiness.py`；
* 新增 `backend/tests/test_shadow_generation_readiness.py`；
* 修改 `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
* 未修改正式生成链；
* 未修改正式导出链；
* 未修改 ZBid 写回链；
* 未写 `output/job/export`；
* 未触发 DOCX/JSON/Markdown 正式导出；
* 未启动服务；
* 未运行 Ollama；
* 未真实访问 `127.0.0.1:11434`。

`backend/zhifei_autoplan/preview_advisory_quality_gate.py` 的修改仅用于在 preview quality gate metadata 中合并 shadow readiness metadata，未引入正式写回、导出或 candidate patch 生成逻辑。

## 3. 测试结果复盘

测试命令：

```bash
python3 -m pytest backend/tests/test_shadow_generation_readiness.py backend/tests/test_evidence_anchor.py backend/tests/test_preview_advisory_quality_gate.py backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

测试结果：

```text
279 passed in 3.62s
```

覆盖场景包括：

* shadow readiness helper；
* readiness 状态；
* quality blocked；
* input-risk blocked；
* evidence missing；
* invalid_anchor；
* conflicting evidence；
* unknown/unstable response；
* thinking_only_fallback；
* generated-preview-as-evidence；
* candidate patch 防护；
* human approval；
* diff / rollback；
* DOCX / ZBid 防护；
* evidence anchor、quality gate、Ollama preview、safe endpoint 回归。

## 4. shadow readiness helper 复盘

Step 95 新增 fake-only `evaluate_shadow_generation_readiness`。

该 helper 只返回 readiness metadata：

* 不生成 candidate patch；
* 不生成 `proposed_text`；
* 不写正式正文；
* 不触发生成链；
* 不触发导出链；
* 不触发 ZBid 写回；
* 不调用模型；
* 不访问 Ollama；
* 不访问外部 API；
* 不写 `output/job/export`。

helper 输出包括 shadow readiness 状态、level、reasons、blockers、warnings、candidate patch blockers、human approval、diff、rollback、evidence trace、trace_id 与正式链准入字段。所有正式链准入字段继续固定为 false。

## 5. readiness 状态复盘

Step 95 已覆盖以下 readiness 状态：

* `not_ready`；
* `review_required`；
* `blocked`；
* `shadow_candidate_forbidden`；
* `system_error`。

边界说明：

* 当前阶段不启用 `shadow_ready_candidate_only`；
* 即使未来预留 `shadow_ready_candidate_only`，也不得等同于 `formal_generation_allowed`；
* 即使未来预留 `shadow_ready_candidate_only`，也不得等同于 `writeback_allowed`、`export_allowed` 或 `zbid_writeback_allowed`；
* `system_error` 必须 fail-closed；
* readiness 状态不等于正式链准入。

## 6. quality / input-risk / evidence / response-mode guard 复盘

本阶段已验证以下 guard：

* `quality_status=blocked` 时不放行；
* `input_risk_status=blocked` 时不放行；
* `evidence_anchor_status=missing` / `invalid_anchor` / `conflicting` / `system_error` 时不放行；
* `response_mode` unknown 或 unstable 时不放行；
* `response_advisory` 不等于 shadow readiness；
* `json_advisory` 不等于 shadow readiness；
* `text_fallback` 不等于 shadow readiness；
* quality `preview_ok` 不等于 shadow readiness；
* evidence `anchored` 不等于 `formal_generation_allowed`。

这些 guard 的目的不是让 preview advisory 进入 shadow candidate，而是确保所有风险先停留在 not_ready、review_required、blocked 或 shadow_candidate_forbidden。

## 7. thinking_only_fallback guard 复盘

本阶段明确并测试：

* `thinking_only_fallback` 永远 `shadow_candidate_allowed=false`；
* `thinking_only_fallback` 不得进入 candidate patch；
* `thinking_only_fallback` 不得写正式正文；
* `thinking_only_fallback` 不得触发 DOCX 导出；
* `thinking_only_fallback` 不得写回 ZBid；
* `thinking_only_fallback` 只能保持 preview-only / review_required 级别。

该策略延续 Step 92 的 B + D 推荐路线：短期接受 thinking fallback 作为人工参考，但不得将其升级为 shadow candidate 或正式生成能力。

## 8. generated-preview-as-evidence guard 复盘

本阶段明确并测试：

* generated preview 作为 evidence 被 blocked；
* `generated_preview_as_evidence_detected=true` 时不得 shadow candidate；
* `system_generated_preview` 不得作为事实证据；
* model-generated advisory 不得作为 tender / drawing / boq / scoring evidence；
* generated preview 与 formal chain request 叠加时继续 blocked。

generated preview 可以作为待审建议来源，但不得成为招标文件、图纸、清单、评分办法或规范依据。

## 9. candidate patch 防护复盘

本阶段的 candidate patch 防护为 fake-only readiness guard，不生成实际 candidate patch。

已覆盖规则：

* 无 evidence 不得形成可写回 candidate；
* 无 diff 不得写回；
* 无 rollback 不得写回；
* 无 approval 不得写回；
* candidate patch without evidence blocked；
* candidate patch with missing evidence blocked；
* candidate patch from `thinking_only_fallback` blocked 或 review_required；
* candidate patch with generated-preview-as-evidence blocked；
* 当前未生成任何 candidate patch。

即使测试 fixture 中出现 `candidate_id`、`proposed_text`、`patch_type` 等字段，也仅用于触发 fake-only guard，不代表系统已经实现 candidate patch 输出。

## 10. human approval guard 复盘

本阶段已验证 human approval guard：

* `approval_status=pending` 不得写回；
* `rejected` 不得写回；
* `hold` 不得写回；
* `revised` 需要新 candidate；
* `approved` 也不自动导出 DOCX；
* `approved` 也不自动写回 ZBid；
* approval 缺 `trace_id` / `diff_summary` / evidence anchors 时 blocked 或 review_required。

human approval 在当前阶段只是 readiness metadata 的约束条件，不会启用正式写回。

## 11. diff / rollback guard 复盘

本阶段已验证 diff / rollback guard：

* `diff_summary` 缺失时 blocked；
* `rollback_token` 缺失时 blocked；
* `rollback_available=false` 时 `writeback_allowed=false`；
* rollback 不依赖模型；
* rollback metadata 不写 `output/job/export`；
* diff / rollback 未完成前 formal flags 全 false。

diff / rollback 仍未实现真实展示或执行，只在 fake-only readiness guard 中作为未来写回前置条件被验证。

## 12. DOCX / ZBid guard 复盘

本阶段已验证：

* shadow candidate 触发 DOCX 请求 blocked；
* shadow candidate 触发 ZBid 请求 blocked；
* `export_allowed=false`；
* `zbid_writeback_allowed=false`；
* DOCX 导出必须单独授权；
* ZBid 写回必须单独设计和授权；
* 当前未进入 DOCX 导出链；
* 当前未进入 ZBid 写回链。

DOCX / ZBid guard 仍只是 readiness 层防线，不代表正式导出链或 ZBid 写回链已经接入。

## 13. 正式链准入字段复盘

所有状态下以下字段恒为 false：

* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `candidate_patch_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`。

说明：

* readiness helper 成功不等于 shadow generation；
* readiness helper 成功不等于 candidate patch；
* readiness helper 成功不等于正式链准入。

当前阶段仍为 preview-only / no-write / formal-ineligible。

## 14. 已证明的事实

Step 95 已证明：

* shadow readiness guard 在 fake-only deterministic tests 下可控；
* `thinking_only_fallback` 不得进入 shadow candidate；
* generated-preview-as-evidence 不得进入 shadow candidate；
* missing / invalid / conflicting evidence 不得进入 shadow candidate；
* candidate patch 缺 evidence / diff / rollback / approval 均不得写回；
* DOCX / ZBid 请求在 readiness 层可被 blocked；
* evidence anchor、quality gate、Ollama preview、safe endpoint 回归通过；
* 未触发正式链路；
* 未写 `output/job/export`。

这些事实只适用于 helper 与 deterministic tests 层，不代表真实 shadow generation 能力。

## 15. 尚未证明的事项

当前尚未证明：

* 未启动真实 Ollama；
* 未启动 FastAPI；
* 未做 runtime smoke；
* 未实现 shadow generation；
* 未生成 candidate patch；
* 未生成 `proposed_text`；
* 未进入 human approval UI；
* 未实现 diff 展示；
* 未实现 rollback 执行；
* 未进入正式正文写回；
* 未进入 DOCX 导出一致性校核；
* 未进入 ZBid 写回隔离。

## 16. 当前风险

当前风险包括：

* fake-only readiness tests 不代表真实 shadow generation 可用；
* readiness metadata 可能被误解为 shadow generation 已实现；
* `shadow_candidate_allowed=false` 必须继续保持；
* thinking fallback 仍可能被误用；
* candidate patch 仍未实现；
* human approval / diff / rollback 仍未实现；
* 后续若实现不严，可能误写正文或污染导出链。

后续实现必须继续 fail-closed，避免任何 readiness metadata 被误用为正式链准入。

## 17. 回滚边界

回滚与兜底边界如下：

* 保持 `shadow_candidate_allowed=false`；
* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
* 保留 disabled / adapter-off / fake-only 路径；
* readiness 异常时应 blocked 或 system_error，不得自动放行；
* 不得删除 fake fixture deterministic tests；
* 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

## 18. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 Step 95 只是 shadow generation readiness guard 的 fake-only 第一版。

正式链前仍需完成：

* readiness stage review；
* shadow candidate data contract implementation design；
* candidate patch design；
* human approval design；
* diff / rollback design；
* shadow generation implementation；
* shadow generation runtime smoke；
* formal writeback design；
* DOCX export consistency design；
* ZBid writeback isolation design。

## 19. 当前阶段结论

本阶段仅证明 shadow generation readiness guard 在 fake-only deterministic tests 下可控，不代表已实现 shadow generation，不代表可生成 candidate patch，不代表可写正式正文，不代表可进入 DOCX 导出或 ZBid 写回。

## 20. 下一步建议

下一步建议为 ZDoc Step 97：shadow candidate data contract design，docs-only。不得直接进入 shadow generation implementation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。
