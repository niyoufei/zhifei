# ZDoc Real Ollama Preview Advisory - Source Hash Revalidation Guard Contract Design

## 1. Scope

Step 121 仅定义未来 source hash revalidation guard 的数据契约，不实现 source hash revalidation helper，不读取真实正文计算 hash，不比较真实 source section 内容，不执行正式写回，不修改 source section，不触发 review/apply。系统仍处于 preview-only / no-write 阶段。

source hash revalidation guard 仅是未来正式写回前复核源章节是否仍为原基准版本的门禁。它用于确认原始 candidate baseline 中记录的 `source_section_hash` / `source_section_version` 与未来运行时提供的 `current_source_section_hash` / `current_source_section_version` 是否匹配。它不等于正式写回动作，不得直接修改 source section，不得直接触发 review/apply，不得直接写 `output/job/export`，不得直接进入 DOCX / JSON / Markdown 导出，也不得直接进入 ZBid 写回。

source hash revalidation guard 不得替代 evidence anchor、human approval、diff preview、rollback plan 或 formal writeback guard。缺少 `source_section_hash`、`current_source_section_hash` 或 hash 匹配结果时，不得进入可写回状态。`current_source_section_hash` 与 `source_section_hash` 不一致时，必须 blocked 或 `stale_source_hash`。`source_section_version` 不一致时，必须 blocked 或 `stale_source_version`。

缺少真实 evidence anchor、human approval、diff preview、rollback plan 或 formal writeback guard 任一前置条件时，不得进入可写回状态。DOCX / ZBid / export 必须另行隔离，不得因 source hash revalidation 通过而自动开放。

本文档仅为后续 fake schema tests 和 fake-only helper 提供 contract design，不代表 source hash revalidation helper、真实 hash 计算、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。

## 2. Non-goals

本步明确排除以下事项：

- 不实现 source hash revalidation helper。
- 不读取真实正文计算 hash。
- 不比较真实 source section 内容。
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
- 不把 hash revalidation 通过当作实际写回。
- 不把 hash revalidation 通过当作 DOCX / ZBid / export 准入。
- 不把 hash revalidation 通过当作 evidence、approval、diff、rollback 或 formal guard 的替代条件。

source hash revalidation guard contract 不得被 orchestrator、generation、export、review/apply、actions_bridge、DOCX 或 ZBid 链路直接消费。

## 3. Upstream Prerequisites

未来 source hash revalidation guard 至少依赖以下上游信息。本步只定义依赖关系，不实现采集、真实 hash 计算、状态机、写回、导出、持久化或隔离执行：

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
- `source_section_hash` from original candidate baseline。
- `source_section_version` from original candidate baseline。
- `current_source_section_hash` placeholder。
- `current_source_section_version` placeholder。
- review/apply isolation placeholder。
- DOCX isolation placeholder。
- ZBid isolation placeholder。

这些上游项均是未来正式写回前的必要但不充分条件。source hash revalidation guard 只能检查和汇总这些条件，不得替代任何条件本身。

## 4. SourceHashRevalidationGuardContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `source_hash_guard_id` | conditional | 未来隔离 source hash guard ID。不得使用随机值；如生成，应基于输入确定性生成。 |
| `request_id` | yes | 关联 preview / candidate / patch / approval / diff / rollback / writeback guard 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。guard 不得覆盖该章节。 |
| `source_section_hash` | yes | 原始 candidate baseline 中记录的来源章节 hash。缺失时必须 blocked。 |
| `source_section_version` | yes | 原始 candidate baseline 中记录的来源章节版本。缺失时必须 blocked。 |
| `current_source_section_hash` | yes | 未来调用方提供的当前来源章节 hash 占位字段。本步不读取正文、不计算真实 hash。 |
| `current_source_section_version` | yes | 未来调用方提供的当前来源章节版本占位字段。本步不读取正文、不比较真实章节。 |
| `source_hash_guard_status` | yes | source hash guard 生命周期状态。当前阶段只设计，不实现状态机。 |
| `revalidation_decision` | yes | revalidation 决策，例如 none、block、allow_shadow_only、require_refresh、reject。 |
| `revalidation_mode` | yes | revalidation 模式。当前阶段必须是 disabled_current_stage 或 metadata_only 语义。 |
| `source_hash_revalidation_status` | yes | hash 复核状态，例如 not_checked、missing、matched、mismatched、stale_source_hash、blocked。 |
| `source_version_revalidation_status` | yes | version 复核状态，例如 not_checked、missing、matched、mismatched、stale_source_version、blocked。 |
| `source_hash_match` | yes | `source_section_hash` 与 `current_source_section_hash` 是否匹配。缺失或 false 时不得写回。 |
| `source_version_match` | yes | `source_section_version` 与 `current_source_section_version` 是否匹配。缺失或 false 时不得写回。 |
| `source_hash_revalidation_required` | yes | 是否要求写回前重新校验 source section hash。 |
| `source_hash_revalidation_ready` | yes | source hash revalidation 是否 ready。false 时不得写回。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope。缺失时不得进入可写回状态。 |
| `patch_id` | yes | 关联 shadow candidate patch。缺失时不得进入可写回状态。 |
| `approval_id` | yes | 关联 human approval gate。缺失或未批准时不得进入可写回状态。 |
| `diff_preview_id` | yes | 关联 diff preview。缺失时不得进入可写回状态。 |
| `rollback_plan_id` | yes | 关联 rollback plan。缺失时不得进入可写回状态。 |
| `writeback_guard_id` | yes | 关联 formal writeback guard。缺失时不得进入可写回状态。 |
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
| `writeback_guard_status` | yes | formal writeback guard 状态。blocked / not_created / stale_source_hash 时不得写回。 |
| `human_approval_required` | yes | 是否需要人工确认。正式写回前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得写回。 |
| `diff_preview_required` | yes | 是否要求 diff preview。正式写回前必须为 true 并 ready。 |
| `diff_preview_ready` | yes | diff preview 是否 ready。false 时不得写回。 |
| `rollback_required` | yes | 是否要求 rollback plan。正式写回前必须为 true。 |
| `rollback_plan_ready` | yes | rollback plan 是否 ready。false 时不得写回。 |
| `formal_writeback_guard_required` | yes | 是否要求 formal writeback guard。正式写回前必须为 true。 |
| `formal_writeback_guard_ready` | yes | formal writeback guard 是否 ready。false 时不得写回。 |
| `review_apply_isolation_required` | yes | 是否要求 review/apply isolation。正式写回前必须为 true。 |
| `review_apply_isolation_ready` | yes | review/apply isolation 是否 ready。false 时不得写回。 |
| `docx_isolation_required` | yes | 是否要求 DOCX isolation。不得由 source hash revalidation 自动开放。 |
| `docx_isolation_ready` | yes | DOCX isolation 是否 ready。false 时不得开放 DOCX。 |
| `zbid_isolation_required` | yes | 是否要求 ZBid isolation。不得由 source hash revalidation 自动开放。 |
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

`current_source_section_hash` 和 `current_source_section_version` 当前只能作为未来字段描述。本步不得宣称已读取真实正文、比较真实正文或计算真实 hash。

当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须保持 false。即使 `source_hash_revalidation_status=matched` 或 `source_hash_guard_status=source_hash_matched_shadow_only`，也不得代表当前已可写回。

## 5. Status Enums

### `source_hash_revalidation_status`

- `not_checked`：尚未复核 hash。
- `missing`：缺少原始 hash、当前 hash 或复核 metadata。
- `matched`：未来调用方提供的当前 hash 与原始 baseline hash 匹配。
- `mismatched`：当前 hash 与原始 baseline hash 不匹配。
- `stale_source_hash`：source section hash 已过期，不得写回。
- `blocked`：存在硬性 blocker，不得进入写回链。

### `source_version_revalidation_status`

- `not_checked`：尚未复核版本。
- `missing`：缺少原始版本、当前版本或复核 metadata。
- `matched`：未来调用方提供的当前版本与原始 baseline 版本匹配。
- `mismatched`：当前版本与原始 baseline 版本不匹配。
- `stale_source_version`：source section version 已过期，不得写回。
- `blocked`：存在硬性 blocker，不得进入写回链。

### `source_hash_guard_status`

- `not_created`：尚未创建 source hash revalidation guard。
- `blocked`：存在硬性 blocker，不允许进入写回链。
- `draft_guard_shadow_only`：未来仅 shadow 隔离的 source hash guard 草稿，不等于可写回。
- `source_hash_matched_shadow_only`：未来 hash 匹配后的 shadow-only metadata 状态，不等于正式写回。
- `stale_source_hash`：source section hash 已过期或不一致，不得写回。
- `stale_source_version`：source section version 已过期或不一致，不得写回。
- `rejected`：人工或系统拒绝状态，不得写回。

### `revalidation_decision`

- `none`：未形成决策。
- `block`：阻断。
- `allow_shadow_only`：仅允许 shadow-only metadata 进入后续审查，不允许写回。
- `require_refresh`：要求刷新候选链路或重新生成上游 metadata。
- `reject`：拒绝。

### `revalidation_mode`

- `disabled_current_stage`：当前阶段禁用真实 hash revalidation。
- `metadata_only`：仅记录调用方提供的 fake / placeholder metadata。
- `future_hash_check`：未来 hash 检查模式，当前不实现。
- `future_guarded_check`：未来 guard 保护下 hash 检查，当前不实现。

当前阶段只设计状态，不实现状态机，不读取真实正文，不计算真实 hash。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `source_hash_revalidation_status=matched` 不等于 `formal_writeback_allowed=true`。
2. `source_hash_guard_status=source_hash_matched_shadow_only` 不等于 `formal_writeback_allowed=true`。
3. source hash revalidation 不得替代 evidence anchor。
4. source hash revalidation 不得替代 human approval。
5. source hash revalidation 不得替代 diff preview。
6. source hash revalidation 不得替代 rollback plan。
7. source hash revalidation 不得替代 formal writeback guard。
8. `response_mode=thinking_only_fallback` 时，不得进入可写回状态。
9. `shadow_candidate_status=blocked` 或 `not_created` 时，不得进入可写回状态。
10. `patch_status=blocked` 或 `not_created` 时，不得进入可写回状态。
11. `approval_status` 未达到 `approved_shadow_only` 时，不得进入可写回状态。
12. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可写回状态。
13. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可写回状态。
14. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可写回状态。
15. `evidence_anchor_status=missing` 时，不得进入可写回状态。
16. `evidence_binding_status=generated_advisory_only_blocked`、`shadow_candidate_only_blocked`、`patch_preview_only_blocked`、`diff_preview_only_blocked` 或 `rollback_plan_only_blocked` 时，不得进入可写回状态。
17. `source_section_hash` 或 `current_source_section_hash` 缺失时，必须 blocked。
18. `source_section_hash` 与 `current_source_section_hash` 不一致时，必须 `stale_source_hash` 或 blocked。
19. `source_section_version` 或 `current_source_section_version` 缺失时，必须 blocked。
20. `source_section_version` 与 `current_source_section_version` 不一致时，必须 `stale_source_version` 或 blocked。
21. `review_apply_isolation_ready=false` 时，不得进入可写回状态。
22. DOCX / ZBid isolation 未准备时，不得开放 DOCX / ZBid。
23. 当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须恒 false。
24. source hash revalidation guard contract 不得被 review/apply、export、DOCX 或 ZBid 直接消费。

source hash revalidation 通过只是未来正式写回前的必要但不充分条件。它不得作为 evidence、approval、diff preview、rollback plan、formal guard、DOCX/ZBid/export 准入或实际写回许可。

## 7. Blocked Scenarios

以下场景必须 blocked，或在 source hash / version 相关场景中进入 `stale_source_hash` / `stale_source_version`：

- no shadow candidate envelope。
- no shadow candidate patch。
- no human approval gate。
- no diff preview。
- no rollback plan。
- no formal writeback guard。
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
- formal writeback guard blocked。
- formal writeback guard not_created。
- formal writeback guard stale_source_hash。
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
- missing `source_section_hash`。
- missing `current_source_section_hash`。
- source hash mismatch。
- missing `source_section_version`。
- missing `current_source_section_version`。
- source version mismatch。
- missing source snapshot hash。
- missing `before_text_hash`。
- missing `after_text_preview_hash`。
- missing `patch_operations_preview_hash`。
- missing `diff_preview_hash`。
- missing `rollback_plan_hash`。
- missing `writeback_candidate_hash`。
- missing review/apply isolation。
- DOCX export request。
- ZBid writeback request。
- output / job / export write request。
- formal generation request。
- review/apply request。

## 8. Source Hash Revalidation Audit Requirements

未来 source hash revalidation guard 审计至少需要：

- `source_hash_guard_id`
- `request_id`
- `source_document_id`
- `source_section_id`
- `source_section_hash`
- `source_section_version`
- `current_source_section_hash`
- `current_source_section_version`
- `source_hash_revalidation_status`
- `source_version_revalidation_status`
- `source_hash_match`
- `source_version_match`
- `shadow_candidate_id`
- `patch_id`
- `approval_id`
- `diff_preview_id`
- `rollback_plan_id`
- `writeback_guard_id`
- `writeback_candidate_hash`
- `source_snapshot_hash`
- `before_text_hash`
- `after_text_preview_hash`
- `patch_operations_preview_hash`
- `diff_preview_hash`
- `rollback_plan_hash`
- `affected_anchor_refs`
- `generated_at`
- `blocked_reasons`

当前阶段不得写文件，不实现持久化，不生成正式 hash 校验记录。所有 audit 字段只是后续 fake schema tests 和 fake-only helper 的契约输入。

## 9. Future Implementation Acceptance Criteria

后续实现只能在单独步骤中推进，并至少满足以下验收条件：

- deterministic fake schema tests。
- source hash status enum tests。
- source version status enum tests。
- missing current hash block tests。
- source hash mismatch block tests。
- source version mismatch block tests。
- stale source hash block tests。
- missing evidence block tests。
- missing approval block tests。
- missing diff preview block tests。
- missing rollback plan block tests。
- missing formal writeback guard block tests。
- missing review/apply isolation block tests。
- DOCX / ZBid / export / review apply block tests。
- formal flags false tests。
- no `output/job/export` filesystem write tests。
- no source section mutation tests。
- import-isolation tests。

这些验收条件不得通过修改生产主链、放宽 evidence 约束、开放导出链路或写回 source section 来满足。

## 10. Migration Path

后续可能步骤如下，但本步不得执行：

- Step 122 可做 source hash revalidation guard contract fake schema tests。
- Step 123 可做 fake-only source hash revalidation guard helper。
- Step 124 可做 fake source hash revalidation guard stage review。
- Step 125 可做 review/apply isolation guard contract design。
- 后续仍需 DOCX isolation guard、ZBid isolation guard、formal writeback dry-run、正式写回人工审批闭环。

Step 122 不得实现 source hash revalidation helper，不得读取真实正文计算 hash，不得执行写回，不得触发 review/apply，不得写 `output/job/export`，不得进入 DOCX 或 ZBid。

## 11. Safety Conclusion

Step 121 仅完成 source hash revalidation guard contract design，不代表 source hash revalidation helper、真实 hash 计算、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。

当前系统仍处于 preview-only / no-write 阶段。source hash revalidation guard 即使在未来显示 matched，也只是一项前置复核 metadata，不是正式写回许可，不是 DOCX / ZBid / export 准入，也不是 evidence、approval、diff preview、rollback plan 或 formal writeback guard 的替代条件。
