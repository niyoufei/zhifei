# ZDoc Real Ollama Preview Advisory - Rollback Plan Contract Design

## 1. Scope

Step 113 仅定义未来 rollback plan 的数据契约，不实现 rollback helper，不执行真实 rollback，不恢复正文，不修改 source section。系统仍处于 preview-only / no-write 阶段。

rollback plan 仅是未来“写回前可回退方案”的隔离预览数据结构，用于描述在正式写回前如何具备可审计、可校验、可阻断的回退准备。rollback plan 不等于实际回滚动作，不得直接写回 source section，不得直接触发 review/apply，不得直接进入 DOCX / JSON / Markdown 导出，不得直接进入 ZBid 写回，也不得作为 evidence。

rollback plan 只能作为未来 formal writeback 前的一项必要但不充分的 metadata。它不得替代 evidence anchor、human approval、diff preview、source hash revalidation 或 formal writeback guard。缺少真实 evidence anchor、human approval、diff preview、source hash revalidation 或 formal writeback guard 时，均不得进入可写回状态。

本文档仅为后续 fake schema tests 和 fake-only rollback plan helper 提供 contract design，不代表 rollback helper、真实 rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

## 2. Non-goals

本步明确排除以下事项：

- 不实现 rollback helper。
- 不执行真实 rollback。
- 不恢复正文。
- 不修改 source section。
- 不触发 review/apply。
- 不执行正式写回。
- 不生成 DOCX / JSON / Markdown。
- 不写 `output/job/export`。
- 不接 ZBid 写回。
- 不实现 formal writeback guard。
- 不实现 DOCX / ZBid isolation guard。
- 不调用模型。
- 不调用 Ollama。
- 不调用外部模型或 API。
- 不启动服务。
- 不访问 `127.0.0.1:11434`。
- 不把 rollback plan 当 evidence。
- 不把 rollback plan 当 formal writeback permission。
- 不把 rollback plan 当 evidence anchor、human approval、diff preview、source hash revalidation 或 formal writeback guard 的替代条件。

rollback plan contract 不得被 orchestrator、generation、export、review/apply、actions_bridge、DOCX 或 ZBid 链路直接消费。

## 3. Upstream Prerequisites

未来 rollback plan 至少依赖以下上游信息。本步只定义依赖关系，不实现采集、校验、状态机、rollback 计算、持久化或写回：

- preview advisory quality gate result。
- input risk snapshot。
- evidence anchor validation result。
- response mode classification。
- shadow generation readiness metadata。
- shadow candidate envelope metadata。
- shadow candidate patch metadata。
- human approval gate metadata。
- diff preview metadata。
- source section hash。
- source section version。
- `before_text_hash`。
- `after_text_preview_hash`。
- `patch_operations_preview_hash`。
- `diff_preview_id`。
- source hash revalidation placeholder。
- formal writeback guard placeholder。

缺少真实 evidence anchor 时，不得进入可写回状态。缺少 human approval、diff preview、source hash revalidation 或 formal writeback guard 时，不得进入可写回状态。rollback plan 不得替代任何上游 guard；它只能证明未来写回前存在可回退方案的 metadata 边界。

## 4. RollbackPlanContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `rollback_plan_id` | conditional | 未来隔离 rollback plan ID。不得使用随机值；如生成，应基于输入确定性生成。 |
| `request_id` | yes | 关联 preview / candidate / patch / approval / diff / rollback 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。rollback plan 不得覆盖该章节。 |
| `source_section_hash` | yes | 来源章节 hash。缺失或与 rollback 基准不一致时不得写回。 |
| `source_section_version` | yes | 来源章节版本，用于 rollback / writeback 前置校验。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope。缺失时不得生成可写回 rollback plan。 |
| `patch_id` | yes | 关联 shadow candidate patch。缺失时不得生成可写回 rollback plan。 |
| `approval_id` | yes | 关联 human approval gate。缺失或未批准时不得生成可写回 rollback plan。 |
| `diff_preview_id` | yes | 关联 diff preview。缺失时不得生成可写回 rollback plan。 |
| `rollback_plan_status` | yes | rollback plan 生命周期状态。当前阶段只设计，不实现状态机。 |
| `rollback_scope` | yes | rollback 范围，例如 single_section、paragraph_range、anchor_range、metadata_only。 |
| `rollback_strategy` | yes | rollback 策略，例如 restore_before_text_hash、reverse_patch_preview、restore_source_snapshot。 |
| `rollback_operation_type` | yes | rollback 操作类型，例如 no_op、restore、reverse_replace、reverse_insert。 |
| `rollback_target_type` | yes | rollback 目标类型，例如 source_section、patch_preview、diff_preview、metadata_only。 |
| `rollback_summary_preview` | conditional | 未来隔离 rollback 摘要预览字段。本步不得宣称已生成真实 rollback plan。 |
| `rollback_operations_preview` | conditional | 未来隔离 rollback 操作预览字段。本步不得宣称已生成真实 rollback operations。 |
| `source_snapshot_hash` | yes | 写回前可回退 source snapshot 的 hash。缺失时不得写回。 |
| `before_text_hash` | yes | 修改前文本 hash，用于 rollback 基准和 source hash revalidation。 |
| `after_text_preview_hash` | yes | 修改后预览文本 hash，用于比对候选结果，不代表正式正文。 |
| `patch_operations_preview_hash` | yes | patch operations 预览 hash。本步不生成真实 patch operations。 |
| `diff_preview_hash` | yes | diff preview metadata 或 diff operations preview hash。缺失时不得写回。 |
| `affected_anchor_refs` | yes | rollback 影响的 anchor 引用列表，不得自动等同于 evidence refs。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 时不得进入可写回状态。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表，不得包含 advisory、shadow candidate、patch preview、diff preview 或 rollback plan。 |
| `evidence_binding_status` | yes | evidence 绑定状态。generated / shadow-only / patch-only / diff-only / rollback-only 均不得写回。 |
| `response_mode` | yes | 上游 response-mode。thinking_only_fallback 不得生成可写回 rollback plan。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `advisory_quality_gate_status` | yes | advisory quality gate 结果。缺失或 blocked 时不得写回。 |
| `readiness_status` | yes | shadow readiness 结果。缺失或 blocked 时不得生成可写回 rollback plan。 |
| `shadow_candidate_status` | yes | shadow candidate 状态。blocked / not_created 时不得生成可写回 rollback plan。 |
| `patch_status` | yes | shadow candidate patch 状态。blocked / not_created 时不得生成可写回 rollback plan。 |
| `approval_status` | yes | human approval gate 状态。未达到 approved_shadow_only 时不得进入可写回状态。 |
| `diff_preview_status` | yes | diff preview 状态。blocked / not_created / stale_source_hash 时不得进入可写回状态。 |
| `human_approval_required` | yes | 是否需要人工确认。正式写回前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得写回。 |
| `source_hash_revalidation_required` | yes | 是否要求写回前重新校验 source section hash。 |
| `source_hash_revalidation_ready` | yes | source hash revalidation 是否 ready。false 时不得写回。 |
| `diff_preview_required` | yes | 是否要求 diff preview。正式写回前必须为 true 并 ready。 |
| `diff_preview_ready` | yes | diff preview 是否 ready。false 时不得写回。 |
| `rollback_required` | yes | 是否要求 rollback plan。正式写回前必须为 true。 |
| `rollback_plan_ready` | yes | rollback plan 是否 ready。当前 contract 设计阶段仅定义字段，不执行 rollback。 |
| `formal_writeback_guard_required` | yes | 是否要求 formal writeback guard。 |
| `formal_writeback_guard_ready` | yes | formal writeback guard 是否 ready。false 时不得写回。 |
| `generated_at` | conditional | 未来 rollback plan 生成时间。应由调用方显式传入，不得使用非确定性时间。 |
| `model_provider` | conditional | 模型提供方元数据，仅用于审计。 |
| `model_name` | conditional | 模型名称元数据，仅用于审计。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked、not_created 或 stale_source_hash 的原因列表。 |

`rollback_summary_preview` 和 `rollback_operations_preview` 当前只能作为未来隔离预览字段描述，不代表 Step 113 已生成真实 rollback plan、真实 rollback operations、真实正文恢复动作或可执行回滚流程。它们不得被 review/apply、export、DOCX、ZBid 或正式生成链直接消费。

## 5. Status Enums

### `rollback_plan_status`

- `not_created`：尚未创建 rollback plan。当前阶段默认状态之一。
- `blocked`：存在硬性 blocker，不允许进入 rollback plan 或写回链。
- `draft_rollback_shadow_only`：未来仅 shadow 隔离的 rollback plan 草稿，不等于真实 rollback。
- `ready_for_human_review`：未来可供人工审查的隔离 rollback plan，仍不等于写回或回滚执行。
- `approved_rollback_shadow_only`：未来人工确认后的 shadow-only rollback 状态，不等于正式写回或真实 rollback。
- `rejected`：人工或系统拒绝状态，不得写回。
- `stale_source_hash`：source section hash 已过期或与 rollback 基准不一致，不得写回。

### `rollback_scope`

- `single_section`：单章节范围。
- `paragraph_range`：段落范围。
- `anchor_range`：锚点范围。
- `metadata_only`：仅元数据范围，不含正文 rollback。

### `rollback_strategy`

- `restore_before_text_hash`：基于 before text hash 的恢复策略。
- `reverse_patch_preview`：基于 patch preview 的逆向预览策略。
- `restore_source_snapshot`：基于 source snapshot 的恢复策略。
- `metadata_only`：仅记录元数据。
- `no_op`：无操作。

### `rollback_operation_type`

- `no_op`：无正文操作。
- `restore`：恢复。
- `reverse_replace`：逆向替换。
- `reverse_insert`：逆向插入。
- `reverse_delete`：逆向删除。
- `reverse_reorder`：逆向重排。
- `mixed`：混合操作。

### `rollback_target_type`

- `source_section`：source section 目标类型。当前阶段不得实际修改。
- `patch_preview`：patch preview 目标类型。
- `diff_preview`：diff preview 目标类型。
- `metadata_only`：仅元数据。

当前阶段只设计状态，不实现状态机，不执行 rollback。任何状态设计都不改变 preview-only / no-write 边界。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `rollback_plan_status=approved_rollback_shadow_only` 不等于 `formal_writeback_allowed=true`。
2. rollback plan 不得作为 evidence。
3. rollback plan 不得替代 evidence anchor。
4. rollback plan 不得替代 human approval。
5. rollback plan 不得替代 diff preview。
6. rollback plan 不得替代 source hash revalidation。
7. rollback plan 不得替代 formal writeback guard。
8. `response_mode=thinking_only_fallback` 时，不得生成可写回 rollback plan。
9. `shadow_candidate_status=blocked` 或 `not_created` 时，不得生成可写回 rollback plan。
10. `patch_status=blocked` 或 `not_created` 时，不得生成可写回 rollback plan。
11. `approval_status` 未达到 `approved_shadow_only` 时，不得生成可写回 rollback plan。
12. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得生成可写回 rollback plan。
13. `evidence_anchor_status=missing` 时，不得进入可写回状态。
14. `evidence_binding_status=generated_advisory_only_blocked`、`shadow_candidate_only_blocked`、`patch_preview_only_blocked`、`diff_preview_only_blocked` 或 `rollback_plan_only_blocked` 时，不得进入可写回状态。
15. `source_hash_revalidation_ready=false` 时，不得进入可写回状态。
16. `diff_preview_ready=false` 时，不得进入可写回状态。
17. `formal_writeback_guard_ready=false` 时，不得进入可写回状态。
18. `source_section_hash` 缺失或与 rollback 基准不一致时，`rollback_plan_status` 必须为 `blocked` 或 `stale_source_hash`。
19. `before_text_hash`、`after_text_preview_hash`、`patch_operations_preview_hash`、`diff_preview_hash` 任一缺失时，不得进入可写回状态。
20. `source_snapshot_hash` 缺失时，不得进入可写回状态。
21. `docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 当前阶段必须恒 false。
22. `formal_writeback_allowed` 当前阶段必须恒 false。
23. rollback plan contract 不得被 review/apply、export、DOCX 或 ZBid 直接消费。

## 7. Blocked Scenarios

以下场景必须 blocked，或在 source hash 相关场景中进入 `stale_source_hash`：

- no shadow candidate envelope。
- no shadow candidate patch。
- no human approval gate。
- no diff preview。
- shadow candidate status blocked。
- shadow candidate status not_created。
- patch status blocked。
- patch status not_created。
- approval not received。
- approval revoked、expired、rejected 或 pending。
- diff preview blocked。
- diff preview not_created。
- diff preview stale_source_hash。
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
- missing before_text_hash。
- missing after_text_preview_hash。
- missing patch_operations_preview_hash。
- missing diff_preview_hash。
- missing source snapshot hash。
- missing source hash revalidation。
- missing diff preview readiness。
- missing formal writeback guard。
- DOCX export request。
- ZBid writeback request。
- output / job / export write request。
- formal generation request。
- review/apply request。

任何 blocked scenario 都不得通过 human approval、diff preview 或 rollback plan 绕过。rollback plan 只能作为 future writeback 的必要前置条件之一，不是充分条件。

## 8. Rollback Plan Audit Requirements

未来 rollback plan 审计至少需要以下字段：

- `rollback_plan_id`
- `request_id`
- `source_document_id`
- `source_section_id`
- `source_section_hash`
- `source_section_version`
- `shadow_candidate_id`
- `patch_id`
- `approval_id`
- `diff_preview_id`
- `rollback_plan_status`
- `rollback_scope`
- `rollback_strategy`
- `rollback_operation_type`
- `rollback_target_type`
- `source_snapshot_hash`
- `before_text_hash`
- `after_text_preview_hash`
- `patch_operations_preview_hash`
- `diff_preview_hash`
- `affected_anchor_refs`
- `generated_at`
- `blocked_reasons`

当前阶段不得写文件，不实现持久化，不生成正式 rollback 产物，不写 `output/job/export`。rollback plan audit metadata 只能作为未来 contract design，不代表已存在 UI、数据库、文件日志、review/apply 集成、rollback 执行或正式写回流程。

## 9. Future Implementation Acceptance Criteria

后续如进入实现，至少需要满足以下验收条件。本步不实现、不运行测试：

- deterministic fake schema tests。
- rollback status enum tests。
- missing approval block tests。
- missing diff preview block tests。
- rollback cannot replace evidence tests。
- rollback cannot replace human approval tests。
- rollback cannot replace diff tests。
- rollback cannot replace source hash revalidation tests。
- rollback cannot replace formal writeback guard tests。
- source hash mismatch block tests。
- stale source hash block tests。
- missing before / after / patch / diff / source snapshot hash block tests。
- thinking_only_fallback block tests。
- generated-advisory-as-evidence block tests。
- shadow-candidate-as-evidence block tests。
- patch-preview-as-evidence block tests。
- diff-preview-as-evidence block tests。
- rollback-plan-as-evidence block tests。
- DOCX / ZBid / export / review apply block tests。
- formal flags false tests。
- no output / job / export filesystem write tests。
- import-isolation tests。
- deterministic `rollback_plan_id` tests if an ID helper is introduced。
- caller-supplied `generated_at` tests if timestamp metadata is introduced。

后续实现验收必须继续证明：

- `formal_writeback_allowed=false`。
- `docx_export_allowed=false`。
- `zbid_writeback_allowed=false`。
- `output_write_allowed=false`。
- 不恢复正文。
- 不触发 review/apply。
- 不触发 DOCX / JSON / Markdown 正式导出。
- 不接 ZBid 正式写回。

## 10. Migration Path

后续可能步骤如下，但 Step 113 不执行：

- Step 114 可做 rollback plan contract fake schema tests。
- Step 115 可做 fake-only rollback plan helper。
- Step 116 可做 fake rollback plan helper stage review。
- 后续仍需 formal writeback guard。
- 后续仍需 source section hash revalidation guard。
- 后续仍需 review/apply isolation。
- 后续仍需 DOCX / ZBid isolation guard。

Step 114 也不得实现 rollback helper，不得执行 rollback，不得写回正文，不得触发 review/apply，不得进入正式生成链。即使未来出现 `draft_rollback_shadow_only`、`ready_for_human_review` 或 `approved_rollback_shadow_only`，也不得自动进入 formal writeback。正式写回、DOCX 导出、ZBid 写回、review/apply 必须分别单独设计、单独授权、单独验证。

## 11. Safety Conclusion

Step 113 仅完成 rollback plan contract design，不代表 rollback helper、真实 rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

当前系统仍处于 preview-only / no-write 阶段。rollback plan 仅是未来写回前可回退方案的隔离预览数据结构，不等于实际回滚动作。rollback plan 不得直接写回 source section，不得直接触发 review/apply，不得直接进入 DOCX / JSON / Markdown 导出，不得直接进入 ZBid 写回，也不得作为 evidence。

rollback plan 不得替代 evidence anchor、human approval、diff preview、source hash revalidation 或 formal writeback guard。缺少真实 evidence anchor、human approval、diff preview、source hash revalidation 或 formal writeback guard 时，均不得进入可写回状态。`formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 当前阶段必须保持 false。
