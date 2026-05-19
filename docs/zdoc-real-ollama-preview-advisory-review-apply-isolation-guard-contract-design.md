# ZDoc Real Ollama Preview Advisory - Review/Apply Isolation Guard Contract Design

## 1. Scope

Step 125 仅定义未来 review/apply isolation guard 的数据契约，不实现 review/apply isolation helper，不触发 `/review/apply`，不执行 review/apply，不执行正式写回，不修改 source section，不写 `output/job/export`。系统仍处于 preview-only / no-write 阶段。

review/apply isolation guard 仅是未来阻断 `/review/apply` 误触发、误写回和越权消费 candidate / diff / rollback 的隔离门禁。它用于把 evidence anchor、shadow candidate envelope、shadow candidate patch、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation guard、DOCX isolation 和 ZBid isolation 的状态汇总为可审计的 isolation metadata。它不等于实际 review/apply 动作，不得触发 `/review/apply`，不得直接修改 source section，不得直接写 `output/job/export`，不得直接进入 DOCX / JSON / Markdown 导出，也不得直接进入 ZBid 写回。

review/apply isolation guard 不得替代 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard 或 source hash revalidation。缺少真实 evidence anchor 时，不得进入可 review/apply 状态。缺少 human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation 任一前置条件时，也不得进入可 review/apply 状态。

`/review/apply` 请求必须默认 blocked，除非未来明确进入 dry-run 或 guarded apply 阶段。当前阶段不得开放。即使 formal writeback guard 与 source hash revalidation 均通过，也不得自动开放 review/apply。DOCX / ZBid / export 必须另行隔离，不得因 review/apply isolation 通过而自动开放。

当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 仍必须保持 false。

本文档仅为后续 fake schema tests 和 fake-only helper 提供 contract design，不代表 review/apply isolation helper、review/apply 执行、正式写回、DOCX 导出或 ZBid 写回已实现。

## 2. Non-goals

本步明确排除以下事项：

- 不实现 review/apply isolation helper。
- 不触发 `/review/apply`。
- 不执行 review/apply。
- 不执行正式写回。
- 不修改 source section。
- 不写 `output/job/export`。
- 不生成 DOCX / JSON / Markdown。
- 不接 ZBid 写回。
- 不实现 DOCX isolation guard。
- 不实现 ZBid isolation guard。
- 不调用模型。
- 不调用 Ollama。
- 不调用外部模型或 API。
- 不启动服务。
- 不访问 `127.0.0.1:11434`。
- 不把 review/apply isolation 通过当作实际写回。
- 不把 review/apply isolation 通过当作 DOCX / ZBid / export 准入。
- 不把 review/apply isolation 通过当作 evidence、approval、diff、rollback、formal guard 或 source hash revalidation 的替代条件。

review/apply isolation guard contract 不得被 orchestrator、generation、export、review/apply、actions_bridge、DOCX 或 ZBid 链路直接消费。

## 3. Upstream Prerequisites

未来 review/apply isolation guard 至少依赖以下上游信息。本步只定义依赖关系，不实现采集、路由、payload 读取、状态机、写回、导出、持久化或隔离执行：

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
- formal writeback guard metadata。
- source hash revalidation guard metadata。
- `source_section_hash`。
- `source_section_version`。
- `current_source_section_hash` placeholder。
- `current_source_section_version` placeholder。
- review/apply request placeholder。
- DOCX isolation placeholder。
- ZBid isolation placeholder。
- explicit user approval flow placeholder。

这些上游项均是未来 review/apply 或 formal writeback 的必要但不充分条件。review/apply isolation guard 只能检查和汇总这些条件，不得替代任何条件本身。

## 4. ReviewApplyIsolationGuardContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `review_apply_guard_id` | conditional | 未来隔离 review/apply guard ID。不得使用随机值；如生成，应基于输入确定性生成。 |
| `request_id` | yes | 关联 preview / candidate / patch / approval / diff / rollback / writeback / source hash guard 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。guard 不得覆盖该章节。 |
| `source_section_hash` | yes | 原始 candidate baseline 中记录的来源章节 hash。缺失时必须 blocked。 |
| `source_section_version` | yes | 原始 candidate baseline 中记录的来源章节版本。缺失时必须 blocked。 |
| `current_source_section_hash` | yes | 未来调用方提供的当前来源章节 hash 占位字段。本步不读取正文、不计算真实 hash。 |
| `current_source_section_version` | yes | 未来调用方提供的当前来源章节版本占位字段。本步不读取正文、不比较真实章节。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope。缺失时不得进入可 review/apply 状态。 |
| `patch_id` | yes | 关联 shadow candidate patch。缺失时不得进入可 review/apply 状态。 |
| `approval_id` | yes | 关联 human approval gate。缺失或未批准时不得进入可 review/apply 状态。 |
| `diff_preview_id` | yes | 关联 diff preview。缺失时不得进入可 review/apply 状态。 |
| `rollback_plan_id` | yes | 关联 rollback plan。缺失时不得进入可 review/apply 状态。 |
| `writeback_guard_id` | yes | 关联 formal writeback guard。缺失时不得进入可 review/apply 状态。 |
| `source_hash_guard_id` | yes | 关联 source hash revalidation guard。缺失时不得进入可 review/apply 状态。 |
| `review_apply_isolation_status` | yes | review/apply isolation 生命周期状态。当前阶段只设计，不实现状态机。 |
| `review_apply_decision` | yes | review/apply isolation 决策，例如 none、block、isolate_shadow_only、require_revision、reject。 |
| `review_apply_scope` | yes | 隔离范围，例如 single_section、paragraph_range、anchor_range、metadata_only。 |
| `review_apply_mode` | yes | review/apply 模式。当前阶段必须是 disabled_current_stage 或 dry_run_only 语义。 |
| `review_apply_target_type` | yes | review/apply 目标类型，例如 source_section、section_draft、patch_preview、metadata_only。当前阶段不得实际修改。 |
| `review_apply_request_status` | yes | `/review/apply` 请求状态。当前阶段 requested、route 或 payload 均必须 blocked。 |
| `review_apply_requested` | yes | 是否出现 review/apply 请求。当前阶段 true 必须 blocked。 |
| `review_apply_route` | conditional | 未来 route 元数据。只能作为未来字段描述，不得触发真实路由。`/review/apply` 当前阶段必须 blocked。 |
| `review_apply_payload_hash` | conditional | 未来 payload hash 元数据。只能作为未来字段描述，不得读取真实 payload 生成。缺失且出现 review/apply 请求时必须 blocked。 |
| `writeback_candidate_hash` | yes | 候选写回内容或 metadata 的 hash。缺失时不得进入可 review/apply 状态。 |
| `source_snapshot_hash` | yes | 写回前 source snapshot hash。缺失时不得进入可 review/apply 状态。 |
| `before_text_hash` | yes | 修改前文本 hash，用于 source hash revalidation 和 rollback。 |
| `after_text_preview_hash` | yes | 修改后预览文本 hash，不代表正式正文。 |
| `patch_operations_preview_hash` | yes | patch operations 预览 hash，不代表可执行 patch。 |
| `diff_preview_hash` | yes | diff preview hash。缺失时不得进入可 review/apply 状态。 |
| `rollback_plan_hash` | yes | rollback plan hash。缺失时不得进入可 review/apply 状态。 |
| `affected_anchor_refs` | yes | 受影响 anchor 引用列表，不得自动等同于 evidence refs。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 时不得进入可 review/apply 状态。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表，不得包含 advisory、shadow candidate、patch preview、diff preview 或 rollback plan。 |
| `evidence_binding_status` | yes | evidence 绑定状态。generated / shadow-only / patch-only / diff-only / rollback-only 均不得进入可 review/apply 状态。 |
| `response_mode` | yes | 上游 response-mode。thinking_only_fallback 不得进入可 review/apply 状态。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `advisory_quality_gate_status` | yes | advisory quality gate 结果。缺失或 blocked 时不得进入可 review/apply 状态。 |
| `readiness_status` | yes | shadow readiness 结果。缺失或 blocked 时不得进入可 review/apply 状态。 |
| `shadow_candidate_status` | yes | shadow candidate 状态。blocked / not_created 时不得进入可 review/apply 状态。 |
| `patch_status` | yes | shadow candidate patch 状态。blocked / not_created 时不得进入可 review/apply 状态。 |
| `approval_status` | yes | human approval gate 状态。未达到 approved_shadow_only 时不得进入可 review/apply 状态。 |
| `diff_preview_status` | yes | diff preview 状态。blocked / not_created / stale_source_hash 时不得进入可 review/apply 状态。 |
| `rollback_plan_status` | yes | rollback plan 状态。blocked / not_created / stale_source_hash 时不得进入可 review/apply 状态。 |
| `writeback_guard_status` | yes | formal writeback guard 状态。blocked / not_created / stale_source_hash 时不得进入可 review/apply 状态。 |
| `source_hash_guard_status` | yes | source hash guard 状态。blocked / not_created / stale_source_hash / stale_source_version 时不得进入可 review/apply 状态。 |
| `source_hash_revalidation_status` | yes | source hash revalidation 状态。mismatched / stale_source_hash / missing 时不得进入可 review/apply 状态。 |
| `source_version_revalidation_status` | yes | source version revalidation 状态。mismatched / stale_source_version / missing 时不得进入可 review/apply 状态。 |
| `source_hash_match` | yes | source hash 是否匹配。false 时不得进入可 review/apply 状态。 |
| `source_version_match` | yes | source version 是否匹配。false 时不得进入可 review/apply 状态。 |
| `human_approval_required` | yes | 是否需要人工确认。正式 review/apply 前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得进入可 review/apply 状态。 |
| `diff_preview_required` | yes | 是否要求 diff preview。正式 review/apply 前必须为 true 并 ready。 |
| `diff_preview_ready` | yes | diff preview 是否 ready。false 时不得进入可 review/apply 状态。 |
| `rollback_required` | yes | 是否要求 rollback plan。正式 review/apply 前必须为 true。 |
| `rollback_plan_ready` | yes | rollback plan 是否 ready。false 时不得进入可 review/apply 状态。 |
| `formal_writeback_guard_required` | yes | 是否要求 formal writeback guard。正式 review/apply 前必须为 true。 |
| `formal_writeback_guard_ready` | yes | formal writeback guard 是否 ready。false 时不得进入可 review/apply 状态。 |
| `source_hash_revalidation_required` | yes | 是否要求 source hash revalidation。正式 review/apply 前必须为 true。 |
| `source_hash_revalidation_ready` | yes | source hash revalidation 是否 ready。false 时不得进入可 review/apply 状态。 |
| `docx_isolation_required` | yes | 是否要求 DOCX isolation。不得由 review/apply isolation 自动开放。 |
| `docx_isolation_ready` | yes | DOCX isolation 是否 ready。false 时不得开放 DOCX。 |
| `zbid_isolation_required` | yes | 是否要求 ZBid isolation。不得由 review/apply isolation 自动开放。 |
| `zbid_isolation_ready` | yes | ZBid isolation 是否 ready。false 时不得开放 ZBid。 |
| `generated_at` | conditional | 未来 guard metadata 生成时间。应由调用方显式传入，不得使用非确定性时间。 |
| `model_provider` | conditional | 模型提供方元数据，仅用于审计。 |
| `model_name` | conditional | 模型名称元数据，仅用于审计。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `review_apply_allowed` | yes | 当前阶段必须为 false。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked、stale_source_hash 或 stale_source_version 的原因列表。 |

`review_apply_allowed` 当前阶段必须为 false。`review_apply_requested=true` 当前阶段必须 blocked。`review_apply_route` 只能作为未来字段描述，不得触发真实路由。`review_apply_payload_hash` 只能作为未来字段描述，不得读取真实 payload 生成。

## 5. Status Enums

### `review_apply_isolation_status`

- `not_created`：尚未创建 review/apply isolation guard。
- `blocked`：存在硬性 blocker，不允许进入 review/apply。
- `draft_isolation_shadow_only`：未来仅 shadow 隔离的 isolation metadata 草稿，不等于可 review/apply。
- `isolated_shadow_only`：未来已完成 shadow-only 隔离的 metadata 状态，不等于可 review/apply。
- `ready_for_future_manual_review`：未来可进入人工审查的 metadata 状态，当前不开放。
- `rejected`：人工或系统拒绝状态，不得 review/apply。
- `stale_source_hash`：source section hash 已过期或不一致，不得 review/apply。
- `stale_source_version`：source section version 已过期或不一致，不得 review/apply。

### `review_apply_decision`

- `none`：未形成决策。
- `block`：阻断。
- `isolate_shadow_only`：仅允许 shadow-only isolation metadata 进入后续审查，不允许 review/apply。
- `require_revision`：要求修订候选链路。
- `reject`：拒绝。

### `review_apply_scope`

- `single_section`：单章节范围。
- `paragraph_range`：段落范围。
- `anchor_range`：锚点范围。
- `metadata_only`：仅元数据范围，不含正文写回。

### `review_apply_mode`

- `disabled_current_stage`：当前阶段禁用 review/apply。
- `dry_run_only`：未来仅 dry-run，不写 source section。
- `future_manual_review`：未来人工受控 review，当前不实现。
- `future_guarded_apply`：未来 guard 保护下 apply，当前不实现。

### `review_apply_target_type`

- `source_section`：source section 目标类型。当前阶段不得实际修改。
- `section_draft`：section draft 目标类型。当前阶段不得接入正式链。
- `patch_preview`：patch preview 目标类型。
- `metadata_only`：仅元数据。

### `review_apply_request_status`

- `not_requested`：未出现 review/apply 请求。
- `requested_blocked`：出现 review/apply 请求且已阻断。
- `route_blocked`：`/review/apply` route 请求已阻断。
- `payload_blocked`：review/apply payload 或 payload hash 不满足隔离要求，已阻断。
- `future_dry_run_only`：未来 dry-run-only 状态，当前不实现。

当前阶段只设计状态，不实现状态机，不触发 `/review/apply`。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `review_apply_isolation_status=isolated_shadow_only` 不等于 `review_apply_allowed=true`。
2. `review_apply_decision=isolate_shadow_only` 不等于 `review_apply_allowed=true`。
3. `review_apply_requested=true` 当前阶段必须 blocked。
4. `review_apply_route=/review/apply` 当前阶段必须 blocked。
5. review/apply isolation 不得替代 evidence anchor。
6. review/apply isolation 不得替代 human approval。
7. review/apply isolation 不得替代 diff preview。
8. review/apply isolation 不得替代 rollback plan。
9. review/apply isolation 不得替代 formal writeback guard。
10. review/apply isolation 不得替代 source hash revalidation。
11. `response_mode=thinking_only_fallback` 时，不得进入可 review/apply 状态。
12. `shadow_candidate_status=blocked` 或 `not_created` 时，不得进入可 review/apply 状态。
13. `patch_status=blocked` 或 `not_created` 时，不得进入可 review/apply 状态。
14. `approval_status` 未达到 `approved_shadow_only` 时，不得进入可 review/apply 状态。
15. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可 review/apply 状态。
16. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可 review/apply 状态。
17. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可 review/apply 状态。
18. `source_hash_guard_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 时，不得进入可 review/apply 状态。
19. `evidence_anchor_status=missing` 时，不得进入可 review/apply 状态。
20. `evidence_binding_status=generated_advisory_only_blocked`、`shadow_candidate_only_blocked`、`patch_preview_only_blocked`、`diff_preview_only_blocked` 或 `rollback_plan_only_blocked` 时，不得进入可 review/apply 状态。
21. `source_hash_match=false` 或 `source_version_match=false` 时，不得进入可 review/apply 状态。
22. DOCX / ZBid isolation 未准备时，不得开放 DOCX / ZBid。
23. 当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须恒 false。
24. review/apply isolation guard contract 不得被 review/apply、export、DOCX 或 ZBid 直接消费。

即使 formal writeback guard 与 source hash revalidation 均通过，当前阶段也不得自动开放 review/apply。

## 7. Blocked Scenarios

以下场景必须 blocked，或在 source hash / source version 相关场景中进入 `stale_source_hash` / `stale_source_version`：

- no shadow candidate envelope。
- no shadow candidate patch。
- no human approval gate。
- no diff preview。
- no rollback plan。
- no formal writeback guard。
- no source hash revalidation guard。
- shadow candidate status blocked。
- patch status blocked。
- approval not received。
- diff preview blocked。
- rollback plan blocked。
- formal writeback guard blocked。
- source hash guard blocked。
- thinking_only_fallback。
- unsupported response mode。
- no evidence anchor。
- advisory used as evidence。
- shadow candidate used as evidence。
- patch preview used as evidence。
- diff preview used as evidence。
- rollback plan used as evidence。
- missing `source_section_hash`。
- missing `current_source_section_hash`。
- source hash mismatch。
- source version mismatch。
- missing `writeback_candidate_hash`。
- missing `source_snapshot_hash`。
- missing `before_text_hash`。
- missing `after_text_preview_hash`。
- missing `patch_operations_preview_hash`。
- missing `diff_preview_hash`。
- missing `rollback_plan_hash`。
- review/apply requested。
- `/review/apply` route requested。
- review/apply payload hash missing。
- DOCX export request。
- ZBid writeback request。
- `output/job/export` write request。
- formal generation request。

上述场景不得被解释为 dry-run 通过、正式写回许可、DOCX 导出许可或 ZBid 写回许可。

## 8. Review/apply Isolation Audit Requirements

未来 review/apply isolation guard 审计至少需要记录以下字段：

- `review_apply_guard_id`
- `request_id`
- `source_document_id`
- `source_section_id`
- `source_section_hash`
- `source_section_version`
- `current_source_section_hash`
- `current_source_section_version`
- `shadow_candidate_id`
- `patch_id`
- `approval_id`
- `diff_preview_id`
- `rollback_plan_id`
- `writeback_guard_id`
- `source_hash_guard_id`
- `review_apply_isolation_status`
- `review_apply_decision`
- `review_apply_scope`
- `review_apply_mode`
- `review_apply_target_type`
- `review_apply_request_status`
- `review_apply_requested`
- `review_apply_route`
- `review_apply_payload_hash`
- `generated_at`
- `blocked_reasons`

当前阶段不得写文件，不实现持久化，不生成正式 review/apply 记录，不读取真实 payload，不触发真实 route。

## 9. Future Implementation Acceptance Criteria

后续实现前应至少满足以下验收条件。本节只列验收条件，不写实现：

- deterministic fake schema tests。
- review/apply isolation status enum tests。
- review/apply request block tests。
- review/apply route block tests。
- missing upstream metadata block tests。
- missing evidence block tests。
- missing approval block tests。
- missing diff preview block tests。
- missing rollback plan block tests。
- missing formal writeback guard block tests。
- missing source hash revalidation block tests。
- source hash mismatch / stale source hash block tests。
- DOCX / ZBid / export / review apply block tests。
- formal flags false tests。
- no `output/job/export` filesystem write tests。
- no source section mutation tests。
- import-isolation tests。

任何后续 fake-only helper 必须保持 deterministic，`generated_at` 应由调用方显式传入，guard ID 应为固定值或基于输入确定性生成。不得使用 UUID、random、当前时间、真实路由调用、真实 payload 读取、真实正文读取或网络调用。

## 10. Migration Path

后续可能步骤如下，但 Step 125 不执行这些步骤：

- Step 126 可做 review/apply isolation guard contract fake schema tests。
- Step 127 可做 fake-only review/apply isolation guard helper。
- Step 128 可做 fake review/apply isolation guard stage review。
- Step 129 可做 DOCX isolation guard contract design。
- 后续仍需 ZBid isolation guard、formal writeback dry-run、正式写回人工审批闭环。

Step 126 不得实现 review/apply isolation helper，不得触发 `/review/apply`，不得执行写回，不得读取或修改真实正文，不得写 `output/job/export`，不得进入 DOCX 或 ZBid。

## 11. Safety Conclusion

Step 125 仅完成 review/apply isolation guard contract design，不代表 review/apply isolation helper、review/apply 执行、正式写回、DOCX 导出或 ZBid 写回已实现。

当前系统仍处于 preview-only / no-write 阶段。`review_apply_requested=true`、`review_apply_route=/review/apply`、formal writeback guard 通过、source hash revalidation 通过、DOCX / ZBid isolation metadata 通过，均不得在当前阶段打开 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed` 或 `output_write_allowed`。
