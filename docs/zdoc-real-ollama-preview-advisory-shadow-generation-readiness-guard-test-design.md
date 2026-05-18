# ZDoc Shadow Generation Readiness Guard Test Design

## 1. 阶段背景

Step 92 已完成 response-mode strategy decision design。Step 93 已完成 shadow generation readiness design。

当前策略为 B + D 为主，C 后续预研，A 暂缓：

* B：接受 `thinking_only_fallback` 仅作为 preview-only / review_required；
* D：优先推进 evidence source mapping、human approval、diff / rollback 与 shadow readiness；
* C：adapter / normalization 抽取策略仅作为后续预研；
* A：暂缓默认继续扩大到 30b / 32b / 80b 等更大模型。

当前已知事实如下：

* `thinking_only_fallback` 仍只能作为 preview-only / review_required；
* `qwen3:0.6b`、`qwen3:8b`、`qwen3:14b` 均未证明 response-mode 满足 shadow generation 条件；
* evidence anchor、quality gate、input-risk、generated-preview-as-evidence 已具备 fake-only 初步门禁；
* 当前 `shadow_candidate_allowed` 必须继续为 false；
* 当前不得进入 shadow generation implementation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

Step 94 的目标是锁定 readiness guard、deterministic tests、数据契约、允许修改文件和回滚边界。本步不得实现代码。

## 2. readiness guard 总体目标

readiness guard 的目标是把 shadow generation 前的所有风险先收口为可测试、可审计、fail-closed 的规则：

* 防止 preview advisory 被误认为 shadow candidate；
* 防止 `thinking_only_fallback` 进入 candidate patch；
* 防止无 evidence trace 的内容进入 candidate patch；
* 防止 generated-preview-as-evidence 被当作证据；
* 防止没有 human approval 的内容写入正式章节；
* 防止没有 diff / rollback 的内容进入写回链；
* 防止 shadow candidate 直接触发 DOCX 导出或 ZBid 写回；
* 当前阶段所有正式链准入字段仍必须为 false。

readiness guard 不负责生成正式正文，也不负责打开导出或写回能力。它只负责判断候选内容是否仍应停留在 preview / review / blocked 范围内。

## 3. readiness guard 与 implementation 的边界

readiness guard design 允许：

* 定义 guard；
* 定义 data contract；
* 定义 deterministic tests；
* 定义 candidate patch metadata；
* 定义 approval / diff / rollback 条件；
* 定义 fail-closed 策略。

readiness guard design 禁止：

* 实现 shadow generation；
* 新增 candidate patch 生成逻辑；
* 修改正式正文；
* 写 `output/job/export`；
* 触发 DOCX 导出；
* 写回 ZBid；
* 调用模型；
* 启动服务；
* 修改正式生成链。

后续若进入实现，必须单独授权，且必须先 fake-only deterministic tests，再做 stage review，不得直接进入 runtime、shadow candidate 或正式链。

## 4. shadow readiness 状态设计

未来 readiness 状态可设计为：

* `not_ready`：默认状态，表示尚未满足 shadow readiness；
* `review_required`：需要人工复核，但不得写回；
* `blocked`：触发安全门禁，不得进入候选；
* `shadow_ready_candidate_only`：未来状态，仅表示可讨论候选生成，不表示可写正式正文；
* `shadow_candidate_forbidden`：明确禁止进入 shadow candidate；
* `system_error`：系统异常，必须 fail-closed。

状态边界：

* 当前阶段应默认 `not_ready` / `blocked` / `review_required`；
* `shadow_ready_candidate_only` 只是未来状态，不得在当前实现中启用；
* `shadow_ready_candidate_only` 不等于 `formal_generation_allowed`；
* `shadow_ready_candidate_only` 不等于 `writeback_allowed`；
* `shadow_ready_candidate_only` 不等于 `export_allowed`；
* `shadow_ready_candidate_only` 不等于 `zbid_writeback_allowed`；
* `system_error` 必须 fail-closed。

## 5. shadow candidate guard 设计

shadow candidate guard 至少应覆盖以下规则：

* `quality_status=blocked` -> `shadow_candidate_allowed=false`；
* `input_risk_status=blocked` -> `shadow_candidate_allowed=false`；
* `evidence_anchor_status=missing` -> `shadow_candidate_allowed=false`；
* `evidence_anchor_status=invalid_anchor` -> `shadow_candidate_allowed=false`；
* `evidence_anchor_status=conflicting` -> `shadow_candidate_allowed=false`；
* `evidence_anchor_status=system_error` -> `shadow_candidate_allowed=false`；
* `generated_preview_as_evidence_detected=true` -> `shadow_candidate_allowed=false`；
* `thinking_only_fallback=true` -> `shadow_candidate_allowed=false`；
* `response_mode` 不稳定或 unknown -> `shadow_candidate_allowed=false`；
* `no_write=false` -> blocked；
* `preview_only=false` -> blocked；
* `affects_generation=true` -> blocked；
* `affects_export=true` -> blocked；
* `formal_generation_allowed=true` -> blocked；
* `writeback_allowed=true` -> blocked；
* `export_allowed=true` -> blocked；
* `zbid_writeback_allowed=true` -> blocked。

guard 输出应明确记录触发原因，例如 `quality_blocked`、`input_risk_blocked`、`evidence_missing`、`invalid_anchor`、`generated_preview_as_evidence`、`thinking_only_fallback_not_shadow_candidate`、`no_write_unsafe`、`formal_flag_unsafe` 等。

## 6. candidate patch data contract 设计

未来 candidate patch 字段建议如下，本步不得实现：

* `candidate_id`；
* `candidate_type`；
* `source_section_id`；
* `source_section_title`；
* `source_paragraph_id`；
* `original_text_excerpt`；
* `proposed_text`；
* `proposed_text_bounded`；
* `patch_type`；
* `patch_scope`；
* `patch_reason`；
* `patch_risk_level`；
* `quality_gate_metadata`；
* `input_risk_metadata`；
* `evidence_anchor_metadata`；
* `response_mode_metadata`；
* `generated_preview_metadata`；
* `evidence_sources`；
* `evidence_anchor_status`；
* `unsupported_claims`；
* `unsupported_project_facts`；
* `human_review_required`；
* `approval_status`；
* `approval_actor`；
* `approval_timestamp`；
* `diff_summary`；
* `rollback_token`；
* `trace_id`；
* `model_name`；
* `prompt_profile`；
* `created_at`；
* `no_write`；
* `preview_only`；
* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`。

该 contract 只描述未来候选元数据。当前阶段不得新增实际 candidate patch 输出，也不得让任何字段打开正式链准入。

## 7. candidate patch 必须禁止的输入来源

以下内容不得形成 candidate patch：

* `thinking_only_fallback` 内容；
* generated preview 被当作 evidence 的内容；
* missing evidence 内容；
* `invalid_anchor` 内容；
* conflicting evidence 内容；
* blocked quality gate 内容；
* blocked input-risk 内容；
* direct write request 内容；
* DOCX export request 内容；
* ZBid writeback request 内容；
* 没有 `rollback_token` 的内容；
* 没有 `diff_summary` 的内容；
* 没有 human approval 的内容；
* `output/job/export` 写入痕迹相关内容。

以上来源应统一进入 blocked、review_required 或 shadow_candidate_forbidden，不得被 adapter / normalization 包装为可写候选。

## 8. human approval guard 设计

human approval guard 规则如下：

* human approval 缺失时 `writeback_allowed=false`；
* `approval_status` 可设计为 `pending` / `approved` / `rejected` / `revised` / `hold`；
* `pending` 不得写回；
* `rejected` 不得写回；
* `hold` 不得写回；
* `revised` 需生成新 candidate；
* `approved` 也不等于立即导出 DOCX；
* `approved` 也不等于写回 ZBid；
* approval 必须绑定 `trace_id`、`candidate_id`、`diff_summary`、evidence anchors；
* human approval 只能作为未来写回前置，不得在 readiness 阶段启用写回。

human approval 不得由模型自动生成，不得由 `quality_status=preview_ok`、`evidence_anchor_status=anchored` 或 `response_mode=response_advisory` 自动推导。

## 9. diff guard 设计

diff guard 规则如下：

* candidate patch 必须具备 `diff_summary`；
* diff 必须能展示 original 与 proposed；
* diff scope 必须明确；
* diff 缺失时 blocked；
* diff 不得由模型单独决定；
* diff 结果不得自动写正文；
* diff 只作为人工确认前展示材料。

diff metadata 至少应包含变更范围、原文片段、候选片段、变更原因、evidence anchors、风险提示、approval 状态与 trace_id。

## 10. rollback guard 设计

rollback guard 规则如下：

* candidate patch 必须具备 `rollback_token`；
* `rollback_token` 缺失时 blocked；
* rollback 不得依赖模型；
* rollback 必须能恢复原始文本；
* rollback 必须绑定 `trace_id`；
* rollback 未设计完成前 `writeback_allowed=false`；
* rollback 设计不得写 `output/job/export`。

rollback 是正式写回前的硬门禁。没有 rollback，不允许进入写回链，也不允许以 DOCX 或 ZBid 输出替代回滚能力。

## 11. evidence trace guard 设计

evidence trace guard 规则如下：

* candidate patch 中每个事实性 claim 必须能追踪 evidence anchor；
* `evidence_source_type=system_generated_preview` 不得作为事实证据；
* `unknown_or_unverified` 不得形成 candidate patch；
* missing evidence 只能 `review_required`，不得 shadow_candidate；
* safe expression 可进入 `review_required`，但不得自动写回；
* evidence trace 必须继承至未来 DOCX / ZBid 链路；
* 当前阶段 evidence trace 仅设计，不实现。

evidence trace 应保留 source evidence、generated suggestion、human approval 三者的边界，防止 model advisory 被升级为招标条款、图纸、清单、评分办法或规范依据。

## 12. response-mode guard 与 shadow readiness 关系

response-mode 只是 shadow readiness 的一个输入条件：

* `response_advisory` 不等于 shadow readiness；
* `json_advisory` 不等于 shadow readiness；
* `text_fallback` 不等于 shadow readiness；
* `thinking_only_fallback` 默认不得 shadow_candidate；
* `response_mode` 只作为准入条件之一；
* 即使 `response_mode` 稳定，也必须通过 quality / input-risk / evidence / human approval / diff / rollback；
* 当前阶段 `shadow_candidate_allowed=false`。

现阶段多轮 runtime 已证明 `qwen3:0.6b`、`qwen3:8b`、`qwen3:14b` 均未满足稳定 response-mode 条件，因此 guard 应继续保守。

## 13. DOCX export guard 设计

DOCX export guard 规则如下：

* shadow candidate 不得直接导出 DOCX；
* `export_allowed` 当前必须 false；
* DOCX 导出必须在正式写回后单独授权；
* DOCX 导出前必须校核 evidence trace、章节层级、图文一致性、表格一致性；
* DOCX 导出不得使用 model-generated advisory 作为 evidence；
* DOCX 导出缺 rollback 时不得进行。

DOCX 导出不是 shadow readiness 的输出，不得由 readiness guard、candidate patch 或 human approval 单独触发。

## 14. ZBid writeback guard 设计

ZBid writeback guard 规则如下：

* ZBid 写回不得由 shadow candidate 直接触发；
* `zbid_writeback_allowed` 当前必须 false；
* ZBid 写回必须区分 source evidence、generated suggestion、human approval；
* 不得覆盖原始招标解析数据；
* 不得污染 scoring basis；
* 不得把 model advisory 当作原始证据；
* ZBid 写回必须单独设计和授权。

ZBid 写回链必须与 preview advisory、candidate patch、正式章节正文保持数据隔离，避免把模型建议写成评分依据或招标事实。

## 15. deterministic tests 设计

后续 Step 95 或后续实现必须覆盖以下 tests，本步不得运行 pytest：

* quality blocked -> `shadow_candidate_allowed=false`；
* input-risk blocked -> `shadow_candidate_allowed=false`；
* evidence missing -> `shadow_candidate_allowed=false`；
* `invalid_anchor` -> `shadow_candidate_allowed=false`；
* generated-preview-as-evidence -> `shadow_candidate_allowed=false`；
* `thinking_only_fallback` -> `shadow_candidate_allowed=false`；
* `response_advisory` but missing evidence -> `shadow_candidate_allowed=false`；
* `json_advisory` but no human approval -> `shadow_candidate_allowed=false`；
* `text_fallback` but no rollback -> `shadow_candidate_allowed=false`；
* candidate patch without diff -> blocked；
* candidate patch without rollback token -> blocked；
* candidate patch without human approval -> no writeback；
* approved candidate still `export_allowed=false`；
* DOCX export attempted from shadow candidate -> blocked；
* ZBid writeback attempted from shadow candidate -> blocked；
* formal flags remain false；
* `no_write=false` -> blocked；
* `affects_generation=true` -> blocked；
* `affects_export=true` -> blocked。

Tests should also assert `formal_generation_allowed=false`, `writeback_allowed=false`, `export_allowed=false`, and `zbid_writeback_allowed=false` across all fixtures unless a future separately authorized stage explicitly changes the contract.

## 16. fake fixture 设计

后续 tests 应新增或扩展 fake fixtures：

* `quality_blocked_candidate_fixture`；
* `input_risk_blocked_candidate_fixture`；
* `missing_evidence_candidate_fixture`；
* `invalid_anchor_candidate_fixture`；
* `generated_preview_evidence_candidate_fixture`；
* `thinking_fallback_candidate_fixture`；
* `response_advisory_missing_evidence_fixture`；
* `json_advisory_no_approval_fixture`；
* `text_fallback_no_rollback_fixture`；
* `candidate_without_diff_fixture`；
* `candidate_without_rollback_fixture`；
* `candidate_pending_approval_fixture`；
* `candidate_approved_no_export_fixture`；
* `shadow_candidate_docx_attempt_fixture`；
* `shadow_candidate_zbid_attempt_fixture`；
* `no_write_false_shadow_fixture`；
* `affects_generation_true_shadow_fixture`；
* `affects_export_true_shadow_fixture`。

Fixtures 应保持 fake-only、deterministic，不依赖真实 Ollama、不启动服务、不访问 `127.0.0.1:11434`。

## 17. 后续实现边界设计

后续如进入实现，应先单独授权。建议可能涉及：

* 新增 shadow readiness helper；
* 新增 deterministic tests；
* 扩展 evidence anchor metadata；
* 扩展 quality gate metadata；
* 扩展 response-mode metadata；
* 不得修改正式生成链；
* 不得修改 DOCX 导出链；
* 不得修改 ZBid 写回链；
* 不得写 `output/job/export`；
* 不得新增实际 candidate patch 输出。

实现阶段应先在 helper / tests 层证明 guard 可控，并继续保持 disabled / adapter-off / fake-only 路径。原则上不得修改 endpoint；如必须修改 endpoint schema，需单独授权。

## 18. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 shadow generation readiness guard 只是正式链前的安全门禁设计。未完成 deterministic tests、shadow candidate helper、human approval、diff、rollback、DOCX 导出一致性校核、ZBid 写回隔离前，不得进入正式生成链。

readiness guard 的存在不是为了绕过 response-mode 问题，而是为了保证后续即使出现 candidate，也不会自动污染正式正文、DOCX 或 ZBid。

## 19. 风险与回滚

当前风险：

* 风险 1：误把 readiness 设计当成 shadow generation 实现；
* 风险 2：误把 shadow candidate 当成正式正文；
* 风险 3：thinking fallback 被误用于 candidate patch；
* 风险 4：无证据内容进入 candidate；
* 风险 5：没有 human approval 写正文；
* 风险 6：diff / rollback 不完整；
* 风险 7：DOCX / ZBid 写回缺少隔离。

回滚与兜底：

* 回滚措施：保持 `shadow_candidate_allowed=false`；
* 兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
* 保留 disabled / adapter-off / fake-only 路径；
* 出现异常时不得扩大到正式链路；
* 任一 guard 异常时应 blocked、review_required 或 system_error，不得自动放行。

## 20. 当前阶段结论

本阶段仅完成 shadow generation readiness guard + deterministic tests 的 docs-only 设计，未实现 shadow generation，未生成 candidate patch，未写正式正文，未启动服务，未运行模型，未进入 DOCX 导出或 ZBid 写回。

## 21. 下一步建议

下一步建议为 ZDoc Step 95：shadow generation readiness guard fake-only implementation + deterministic tests。不得直接进入 shadow generation implementation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。
