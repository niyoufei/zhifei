# ZDoc Real Ollama Preview Advisory - Formal Writeback Guard Contract Design

## 1. Scope

Step 117 仅定义未来 formal writeback guard 的数据契约，不实现 formal writeback helper，不执行正式写回，不修改 source section，不触发 review/apply。系统仍处于 preview-only / no-write 阶段。

formal writeback guard 仅是未来正式写回前的最终准入门禁，用于把 evidence anchor、shadow candidate envelope、shadow candidate patch、human approval、diff preview、rollback plan、source hash revalidation、review/apply isolation、DOCX isolation 和 ZBid isolation 的前置状态汇总为可审计的 guard metadata。它不等于正式写回动作，不得直接修改 source section，不得直接触发 review/apply，不得直接写 `output/job/export`，不得直接进入 DOCX / JSON / Markdown 导出，也不得直接进入 ZBid 写回。

formal writeback guard 不得替代 evidence anchor、human approval、diff preview、rollback plan 或 source hash revalidation。缺少真实 evidence anchor、source hash revalidation、human approval、diff preview、rollback plan 或 review/apply isolation guard 时，不得进入可写回状态。DOCX / ZBid / export 必须另行隔离，不得因 formal writeback guard 通过而自动开放。

本文档仅为后续 fake schema tests 和 fake-only helper 提供 contract design，不代表 formal writeback helper、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。

## 2. Non-goals

本步明确排除以下事项：

- 不实现 formal writeback helper。
- 不执行正式写回。
- 不修改 source section。
- 不触发 review/apply。
- 不写 `output/job/export`。
- 不生成 DOCX / JSON / Markdown。
- 不接 ZBid 写回。
- 不实现 DOCX isolation guard。
- 不实现 ZBid isolation guard。
- 不实现 review/apply isolation guard。
- 不调用模型。
- 不调用 Ollama。
- 不调用外部模型或 API。
- 不启动服务。
- 不访问 `127.0.0.1:11434`。
- 不把 guard 通过当作实际写回。
- 不把 guard 通过当作 DOCX / ZBid / export 准入。
- 不把 guard 通过当作 evidence、approval、diff、rollback 或 source hash revalidation 的替代条件。

formal writeback guard contract 不得被 orchestrator、generation、export、review/apply、actions_bridge、DOCX 或 ZBid 链路直接消费。

## 3. Upstream Prerequisites

未来 formal writeback guard 至少依赖以下上游信息。本步只定义依赖关系，不实现采集、校验、状态机、写回、导出、持久化或隔离执行：

- preview advisory quality gate result。
- input risk snapshot。
- evidence anchor validation result。
- response mode classification。
- shadow generation readiness metadata。
- shadow candidate envelope metadata。
- shadow candidate patch metadata。
- human approval gate metadata。
- diff preview metadata。
- rollback plan metadata。
- source section hash。
- source section version。
- source hash revalidation placeholder。
- review/apply isolation placeholder。
- DOCX isolation placeholder。
- ZBid isolation placeholder。
- explicit user approval flow placeholder。

这些上游项均是未来 formal writeback 的必要但不充分条件。formal writeback guard 只能检查和汇总这些条件，不得替代任何条件本身。

## 4. FormalWritebackGuardContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `writeback_guard_id` | conditional | 未来隔离 guard ID。不得使用随机值；如生成，应基于输入确定性生成。 |
| `request_id` | yes | 关联 preview / candidate / patch / approval / diff / rollback / writeback guard 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。guard 不得覆盖该章节。 |
| `source_section_hash` | yes | 来源章节 hash。缺失、未重新校验或不匹配时不得写回。 |
| `source_section_version` | yes | 来源章节版本，用于 writeback 前置校验。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope。缺失时不得进入可写回状态。 |
| `patch_id` | yes | 关联 shadow candidate patch。缺失时不得进入可写回状态。 |
| `approval_id` | yes | 关联 human approval gate。缺失或未批准时不得进入可写回状态。 |
| `diff_preview_id` | yes | 关联 diff preview。缺失时不得进入可写回状态。 |
| `rollback_plan_id` | yes | 关联 rollback plan。缺失时不得进入可写回状态。 |
| `writeback_guard_status` | yes | guard 生命周期状态。当前阶段只设计，不实现状态机。 |
| `writeback_decision` | yes | guard 决策，例如 none、block、allow_shadow_only、require_revision、reject。 |
| `writeback_scope` | yes | 写回范围，例如 single_section、paragraph_range、anchor_range、metadata_only。 |
| `writeback_mode` | yes | 写回模式。当前阶段必须是 disabled_current_stage 或 dry_run_only 语义。 |
| `writeback_target_type` | yes | 写回目标类型，例如 source_section、section_draft、patch_preview、metadata_only。 |
| `writeback_candidate_hash` | yes | 候选写回内容或 metadata 的 hash。缺失时不得写回。 |
| `source_snapshot_hash` | yes | 写回前 source snapshot hash。缺失时不得写回。 |
| `before_text_hash` | yes | 修改前文本 hash，用于 source hash revalidation 和 rollback。 |
| `after_text_preview_hash` | yes | 修改后预览文本 hash，不代表正式正文。 |
| `patch_operations_preview_hash` | yes | patch operations 预览 hash，不代表可执行 patch。 |
| `diff_preview_hash` | yes | diff preview hash。缺失时不得写回。 |
| `rollback_plan_hash` | yes | rollback plan hash。缺失时不得写回。 |
| `affected_anchor_refs` | yes | 受影响 anchor 引用列表，不得自动等同于 evidence refs。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 时不得进入可写回状态。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表，不得包含 advisory、shadow candidate、patch preview、diff preview 或 rollback plan。 |
| `evidence_binding_status` | yes | evidence 绑定状态。generated / shadow-only / patch-only / diff-only / rollback-only 均不得写回。 |
| `response_mode` | yes | 上游 response-mode。thinking_only_fallback 不得进入可写回状态。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `advisory_quality_gate_status` | yes | advisory quality gate 结果。缺失或 blocked 时不得写回。 |
| `readiness_status` | yes | shadow readiness 结果。缺失或 blocked 时不得写回。 |
| `shadow_candidate_status` | yes | shadow candidate 状态。blocked / not_created 时不得写回。 |
| `patch_status` | yes | shadow candidate patch 状态。blocked / not_created 时不得写回。 |
| `approval_status` | yes | human approval gate 状态。未达到 approved_shadow_only 时不得写回。 |
| `diff_preview_status` | yes | diff preview 状态。blocked / not_created / stale_source_hash 时不得写回。 |
| `rollback_plan_status` | yes | rollback plan 状态。blocked / not_created / stale_source_hash 时不得写回。 |
| `source_hash_revalidation_required` | yes | 是否要求写回前重新校验 source section hash。 |
| `source_hash_revalidation_ready` | yes | source hash revalidation 是否 ready。false 时不得写回。 |
| `source_hash_revalidation_status` | yes | source hash revalidation 状态，例如 not_checked、missing、matched、mismatched、stale_source_hash。 |
| `human_approval_required` | yes | 是否需要人工确认。正式写回前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得写回。 |
| `diff_preview_required` | yes | 是否要求 diff preview。正式写回前必须为 true 并 ready。 |
| `diff_preview_ready` | yes | diff preview 是否 ready。false 时不得写回。 |
| `rollback_required` | yes | 是否要求 rollback plan。正式写回前必须为 true。 |
| `rollback_plan_ready` | yes | rollback plan 是否 ready。false 时不得写回。 |
| `review_apply_isolation_required` | yes | 是否要求 review/apply isolation。正式写回前必须为 true。 |
| `review_apply_isolation_ready` | yes | review/apply isolation 是否 ready。false 时不得写回。 |
| `docx_isolation_required` | yes | 是否要求 DOCX isolation。不得由 formal writeback guard 自动开放。 |
| `docx_isolation_ready` | yes | DOCX isolation 是否 ready。false 时不得开放 DOCX。 |
| `zbid_isolation_required` | yes | 是否要求 ZBid isolation。不得由 formal writeback guard 自动开放。 |
| `zbid_isolation_ready` | yes | ZBid isolation 是否 ready。false 时不得开放 ZBid。 |
| `generated_at` | conditional | 未来 guard metadata 生成时间。应由调用方显式传入，不得使用非确定性时间。 |
| `model_provider` | conditional | 模型提供方元数据，仅用于审计。 |
| `model_name` | conditional | 模型名称元数据，仅用于审计。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `review_apply_allowed` | yes | 当前阶段必须为 false。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked、not_created 或 stale_source_hash 的原因列表。 |

`formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 当前阶段必须保持 false。`writeback_guard_status` 即使具有 future-ready 或 approved 类语义，也不得代表当前已可写回。

## 5. Status Enums

### `writeback_guard_status`

- `not_created`：尚未创建 formal writeback guard。
- `blocked`：存在硬性 blocker，不允许进入写回链。
- `draft_guard_shadow_only`：未来仅 shadow 隔离的 guard 草稿，不等于可写回。
- `ready_for_final_review`：未来可供最终人工审查的 guard metadata，仍不等于写回。
- `approved_guard_shadow_only`：未来人工确认后的 shadow-only guard 状态，不等于正式写回。
- `rejected`：人工或系统拒绝状态，不得写回。
- `stale_source_hash`：source section hash 已过期或与写回基准不一致，不得写回。

### `writeback_decision`

- `none`：未形成决策。
- `block`：阻断。
- `allow_shadow_only`：仅允许 shadow-only metadata 进入后续审查，不允许写回。
- `require_revision`：要求修订候选链路。
- `reject`：拒绝。

### `writeback_scope`

- `single_section`：单章节范围。
- `paragraph_range`：段落范围。
- `anchor_range`：锚点范围。
- `metadata_only`：仅元数据范围，不含正文写回。

### `writeback_mode`

- `disabled_current_stage`：当前阶段禁用正式写回。
- `dry_run_only`：未来仅 dry-run，不写 source section。
- `future_manual_apply`：未来人工受控 apply，当前不实现。
- `future_guarded_apply`：未来 guard 保护下 apply，当前不实现。

### `writeback_target_type`

- `source_section`：source section 目标类型。当前阶段不得实际修改。
- `section_draft`：section draft 目标类型。当前阶段不得接入正式链。
- `patch_preview`：patch preview 目标类型。
- `metadata_only`：仅元数据。

### `source_hash_revalidation_status`

- `not_checked`：尚未重新校验。
- `missing`：缺少 source hash 或 revalidation metadata。
- `matched`：source hash 与写回基准匹配。
- `mismatched`：source hash 与写回基准不匹配。
- `stale_source_hash`：source hash 已过期。

当前阶段只设计状态，不实现状态机，不执行写回。任何状态设计都不改变 preview-only / no-write 边界。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `writeback_guard_status=approved_guard_shadow_only` 不等于 `formal_writeback_allowed=true`。
2. formal writeback guard 不得替代 evidence anchor。
3. formal writeback guard 不得替代 human approval。
4. formal writeback guard 不得替代 diff preview。
5. formal writeback guard 不得替代 rollback plan。
6. formal writeback guard 不得替代 source hash revalidation。
7. `response_mode=thinking_only_fallback` 时，不得进入可写回状态。
8. `shadow_candidate_status=blocked` 或 `not_created` 时，不得进入可写回状态。
9. `patch_status=blocked` 或 `not_created` 时，不得进入可写回状态。
10. `approval_status` 未达到 `approved_shadow_only` 时，不得进入可写回状态。
11. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可写回状态。
12. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可写回状态。
13. `evidence_anchor_status=missing` 时，不得进入可写回状态。
14. `evidence_binding_status=generated_advisory_only_blocked`、`shadow_candidate_only_blocked`、`patch_preview_only_blocked`、`diff_preview_only_blocked` 或 `rollback_plan_only_blocked` 时，不得进入可写回状态。
15. `source_hash_revalidation_ready=false` 时，不得进入可写回状态。
16. `source_hash_revalidation_status=mismatched` 或 `stale_source_hash` 时，不得进入可写回状态。
17. `review_apply_isolation_ready=false` 时，不得进入可写回状态。
18. DOCX / ZBid isolation 未准备时，不得开放 DOCX / ZBid。
19. `source_section_hash`、`before_text_hash`、`after_text_preview_hash`、`patch_operations_preview_hash`、`diff_preview_hash`、`rollback_plan_hash` 任一缺失时，不得进入可写回状态。
20. `source_snapshot_hash` 或 `writeback_candidate_hash` 缺失时，不得进入可写回状态。
21. 当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须恒 false。
22. formal writeback guard contract 不得被 review/apply、export、DOCX 或 ZBid 直接消费。

## 7. Blocked Scenarios

以下场景必须 blocked，或在 source hash 相关场景中进入 `stale_source_hash`：

- no shadow candidate envelope。
- no shadow candidate patch。
- no human approval gate。
- no diff preview。
- no rollback plan。
- shadow candidate status blocked。
- shadow candidate status not_created。
- patch status blocked。
- patch status not_created。
- approval not received。
- approval revoked、expired、rejected 或 pending。
- diff preview blocked。
- diff preview not_created。
- diff preview stale_source_hash。
- rollback plan blocked。
- rollback plan not_created。
- rollback plan stale_source_hash。
- thinking_only_fallback。
- unsupported response mode。
- no evidence anchor。
- advisory used as evidence。
- shadow candidate used as evidence。
- shadow candidate envelope used as evidence。
- patch preview used as evidence。
- diff preview used as evidence。
- rollback plan used as evidence。
- high input risk without validation。
- missing advisory quality gate result。
- missing readiness metadata。
- missing source section hash。
- source section hash mismatch。
- missing source hash revalidation。
- source hash revalidation mismatched。
- stale source hash。
- missing before_text_hash。
- missing after_text_preview_hash。
- missing patch_operations_preview_hash。
- missing diff_preview_hash。
- missing rollback_plan_hash。
- missing source_snapshot_hash。
- missing writeback_candidate_hash。
- missing review/apply isolation。
- DOCX export request。
- ZBid writeback request。
- output / job / export write request。
- formal generation request。
- review/apply request。

任何 blocked scenario 都不得通过 formal writeback guard、human approval、diff preview 或 rollback plan 绕过。formal writeback guard 是 future writeback 的最终门禁 metadata，不是写回执行器，也不是 DOCX / ZBid / export 准入器。

## 8. Formal Writeback Audit Requirements

未来 formal writeback guard 审计至少需要以下字段：

- `writeback_guard_id`
- `request_id`
- `source_document_id`
- `source_section_id`
- `source_section_hash`
- `source_section_version`
- `shadow_candidate_id`
- `patch_id`
- `approval_id`
- `diff_preview_id`
- `rollback_plan_id`
- `writeback_guard_status`
- `writeback_decision`
- `writeback_scope`
- `writeback_mode`
- `writeback_target_type`
- `source_hash_revalidation_status`
- `source_snapshot_hash`
- `before_text_hash`
- `after_text_preview_hash`
- `patch_operations_preview_hash`
- `diff_preview_hash`
- `rollback_plan_hash`
- `affected_anchor_refs`
- `generated_at`
- `blocked_reasons`

当前阶段不得写文件，不实现持久化，不生成正式写回记录，不写 `output/job/export`。formal writeback guard audit metadata 只能作为未来 contract design，不代表已存在 UI、数据库、文件日志、review/apply 集成、DOCX / ZBid 集成或正式写回流程。

## 9. Future Implementation Acceptance Criteria

后续如进入实现，至少需要满足以下验收条件。本步不实现、不运行测试：

- deterministic fake schema tests。
- writeback guard status enum tests。
- missing evidence block tests。
- missing approval block tests。
- missing diff preview block tests。
- missing rollback plan block tests。
- missing source hash revalidation block tests。
- source hash mismatch / stale source hash block tests。
- missing review/apply isolation block tests。
- DOCX / ZBid / export / review apply block tests。
- formal flags false tests。
- no `output/job/export` filesystem write tests。
- import-isolation tests。
- dry-run-only tests。
- no source section mutation tests。
- guard-is-not-writeback-permission tests。
- guard-is-not-DOCX-or-ZBid-permission tests。

## 10. Migration Path

后续可能步骤如下，但本步不得执行：

- Step 118 可做 formal writeback guard contract fake schema tests。
- Step 119 可做 fake-only formal writeback guard helper。
- Step 120 可做 fake formal writeback guard stage review。
- Step 121 可做 source hash revalidation guard contract design。
- 后续仍需 review/apply isolation guard、DOCX isolation guard、ZBid isolation guard、formal writeback dry-run、正式写回人工审批闭环。

Step 118 不得实现 formal writeback helper，不得执行写回，不得触发 review/apply，不得写 `output/job/export`，不得进入 DOCX / ZBid。

## 11. Safety Conclusion

Step 117 仅完成 formal writeback guard contract design，不代表 formal writeback helper、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。

当前系统仍处于 preview-only / no-write 阶段。`formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 在当前阶段必须继续保持 false。
