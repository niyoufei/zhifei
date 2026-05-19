# ZDoc Real Ollama Preview Advisory - Formal Writeback Dry-Run Contract Design

## 1. Scope

Step 137 仅定义未来 formal writeback dry-run 的数据契约，不实现 dry-run helper，不执行 dry-run，不执行正式写回，不触发 review/apply，不触发 DOCX 导出，不触发 ZBid 写回。系统仍处于 preview-only / no-write 阶段。

formal writeback dry-run 仅是未来正式写回前的只读模拟与准入验证记录。它用于把 evidence anchor、shadow candidate envelope、shadow candidate patch、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation guard、review/apply isolation guard、DOCX isolation guard、ZBid isolation guard 等上游状态汇总为可审计的 dry-run metadata。

formal writeback dry-run 不等于正式写回动作。它不得修改 source section，不得触发 review/apply，不得写 `output/job/export`，不得生成 DOCX / JSON / Markdown，不得触发 ZBid 写回，不得调用 ZBid API、数据库或写回接口。

dry-run passed 不得自动开放 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed`。当前阶段这些 flags 仍必须保持 false。

本文档不代表 dry-run helper、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。

当前策略为先完成本地化部署基础闭环和 ZDoc / ZBid 小范围对接试用，最后再按约 50 人同时使用场景开展正式部署设计。本步不进入 50 人团队正式部署方案。

## 2. Non-goals

本步明确排除以下事项：

- 不实现 dry-run helper。
- 不执行 dry-run。
- 不执行正式写回。
- 不修改 source section。
- 不触发 review/apply。
- 不触发 `/review/apply`。
- 不触发 `/export_docx`。
- 不生成 DOCX / JSON / Markdown。
- 不触发 ZBid 写回。
- 不调用 ZBid API / DB / 写回接口。
- 不写 `output/job/export`。
- 不调用模型。
- 不调用 Ollama。
- 不调用外部模型或 API。
- 不启动后端服务。
- 不启动前端服务。
- 不访问 `127.0.0.1:11434`。
- 不把 dry-run passed 当作实际写回许可。
- 不把 dry-run passed 当作 DOCX / ZBid / export 准入。
- 不把 dry-run passed 当作 evidence、approval、diff、rollback、formal guard、source hash revalidation、review/apply isolation、DOCX isolation、ZBid isolation 的替代条件。
- 不进入 50 人团队正式部署方案。

formal writeback dry-run contract 不得被 review/apply、export、DOCX、ZBid、orchestrator、generation 或 actions_bridge 链路直接消费。

## 3. Upstream Prerequisites

未来 formal writeback dry-run 至少依赖以下上游信息。本步只定义依赖关系，不实现采集、校验、读取正文、模拟、状态机、写回、导出、持久化或隔离执行：

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
- review/apply isolation guard metadata。
- DOCX isolation guard metadata。
- ZBid isolation guard metadata。
- `source_section_hash`。
- `source_section_version`。
- `current_source_section_hash` placeholder。
- `current_source_section_version` placeholder。
- dry-run request placeholder。
- dry-run payload hash placeholder。
- explicit user approval flow placeholder。

这些上游项均是未来 formal writeback dry-run 进入 passed 类状态的必要但不充分条件。formal writeback dry-run 只能检查和汇总这些条件，不得替代任何条件本身。

缺少真实 evidence anchor 时，不得进入 dry-run passed 状态。缺少 human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation、review/apply isolation、DOCX isolation、ZBid isolation 任一前置条件时，也不得进入 dry-run passed 状态。

## 4. FormalWritebackDryRunContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `dry_run_id` | conditional | 未来 dry-run metadata ID。不得使用随机值；如生成，应基于输入确定性生成。 |
| `request_id` | yes | 关联 preview / candidate / patch / approval / diff / rollback / guard / dry-run 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。dry-run 不得覆盖或修改该章节。 |
| `source_section_hash` | yes | 原始 candidate baseline 中记录的来源章节 hash。缺失时必须 blocked。 |
| `source_section_version` | yes | 原始 candidate baseline 中记录的来源章节版本。缺失时必须 blocked。 |
| `current_source_section_hash` | yes | 未来调用方提供的当前来源章节 hash 占位字段。本步不读取正文、不计算真实 hash。 |
| `current_source_section_version` | yes | 未来调用方提供的当前来源章节版本占位字段。本步不读取正文、不比较真实章节。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope。缺失时不得进入 dry-run passed 状态。 |
| `patch_id` | yes | 关联 shadow candidate patch。缺失时不得进入 dry-run passed 状态。 |
| `approval_id` | yes | 关联 human approval gate。缺失或未批准时不得进入 dry-run passed 状态。 |
| `diff_preview_id` | yes | 关联 diff preview。缺失时不得进入 dry-run passed 状态。 |
| `rollback_plan_id` | yes | 关联 rollback plan。缺失时不得进入 dry-run passed 状态。 |
| `writeback_guard_id` | yes | 关联 formal writeback guard。缺失时不得进入 dry-run passed 状态。 |
| `source_hash_guard_id` | yes | 关联 source hash revalidation guard。缺失时不得进入 dry-run passed 状态。 |
| `review_apply_guard_id` | yes | 关联 review/apply isolation guard。缺失时不得进入 dry-run passed 状态。 |
| `docx_isolation_guard_id` | yes | 关联 DOCX isolation guard。缺失时不得进入 dry-run passed 状态。 |
| `zbid_isolation_guard_id` | yes | 关联 ZBid isolation guard。缺失时不得进入 dry-run passed 状态。 |
| `dry_run_status` | yes | dry-run 生命周期状态。当前阶段只设计，不实现状态机。 |
| `dry_run_decision` | yes | dry-run 决策，例如 none、block、simulate_shadow_only、pass_shadow_only、require_revision、reject。 |
| `dry_run_scope` | yes | dry-run 模拟范围，例如 single_section、selected_sections、full_document、metadata_only。 |
| `dry_run_mode` | yes | dry-run 模式。当前阶段必须是 disabled_current_stage 或 metadata_only 语义。 |
| `dry_run_target_type` | yes | dry-run 目标类型，例如 source_section、section_draft、docx_document、zbid_section、metadata_only。当前阶段不得写入。 |
| `dry_run_request_status` | yes | dry-run 请求状态。当前阶段 requested 或 payload 缺失必须 blocked。 |
| `dry_run_requested` | yes | 是否出现 dry-run 请求。当前阶段 true 必须 blocked。 |
| `dry_run_payload_hash` | conditional | 未来 dry-run payload hash 元数据。只能作为未来字段描述，不得读取真实 payload 或正文生成。缺失时不得进入 passed 状态。 |
| `dry_run_candidate_hash` | conditional | 未来 dry-run candidate hash 元数据。只能作为未来字段描述，不得读取真实正文或正式写回候选生成。缺失时不得进入 passed 状态。 |
| `dry_run_source_snapshot_hash` | conditional | 未来 dry-run source snapshot hash 元数据。不得读取真实正文生成。 |
| `writeback_candidate_hash` | yes | 候选写回内容或 metadata 的 hash。缺失时不得进入 passed 状态。 |
| `docx_candidate_hash` | yes | DOCX candidate hash 元数据。不得替代 DOCX isolation。缺失时不得进入 passed 状态。 |
| `zbid_candidate_hash` | yes | ZBid candidate hash 元数据。不得替代 ZBid isolation。缺失时不得进入 passed 状态。 |
| `zbid_target_mapping_hash` | yes | ZBid target mapping hash 元数据。不得读取真实 ZBid 映射生成。缺失时不得进入 passed 状态。 |
| `source_snapshot_hash` | yes | 写回前 source snapshot hash。缺失时不得进入 passed 状态。 |
| `before_text_hash` | yes | 修改前文本 hash，用于 source hash revalidation、diff 和 rollback。 |
| `after_text_preview_hash` | yes | 修改后预览文本 hash，不代表正式正文。 |
| `patch_operations_preview_hash` | yes | patch operations 预览 hash，不代表可执行 patch。 |
| `diff_preview_hash` | yes | diff preview hash。缺失时不得进入 passed 状态。 |
| `rollback_plan_hash` | yes | rollback plan hash。缺失时不得进入 passed 状态。 |
| `affected_anchor_refs` | yes | 受影响 anchor 引用列表，不得自动等同于 evidence refs。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 时不得进入 dry-run passed 状态。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表，不得包含 advisory、shadow candidate、patch preview、diff preview、rollback plan、DOCX preview 或 ZBid metadata。 |
| `evidence_binding_status` | yes | evidence 绑定状态。generated / shadow-only / patch-only / diff-only / rollback-only 均不得进入 passed 状态。 |
| `response_mode` | yes | 上游 response-mode。thinking_only_fallback 不得进入 dry-run passed 状态。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `advisory_quality_gate_status` | yes | advisory quality gate 结果。缺失或 blocked 时不得进入 passed 状态。 |
| `readiness_status` | yes | shadow readiness 结果。缺失或 blocked 时不得进入 passed 状态。 |
| `shadow_candidate_status` | yes | shadow candidate 状态。blocked / not_created 时不得进入 passed 状态。 |
| `patch_status` | yes | shadow candidate patch 状态。blocked / not_created 时不得进入 passed 状态。 |
| `approval_status` | yes | human approval gate 状态。未达到 approved_shadow_only 时不得进入 passed 状态。 |
| `diff_preview_status` | yes | diff preview 状态。blocked / not_created / stale_source_hash 时不得进入 passed 状态。 |
| `rollback_plan_status` | yes | rollback plan 状态。blocked / not_created / stale_source_hash 时不得进入 passed 状态。 |
| `writeback_guard_status` | yes | formal writeback guard 状态。blocked / not_created / stale_source_hash 时不得进入 passed 状态。 |
| `source_hash_guard_status` | yes | source hash guard 状态。blocked / not_created / stale_source_hash / stale_source_version 时不得进入 passed 状态。 |
| `review_apply_isolation_status` | yes | review/apply isolation 状态。blocked / not_created / stale_source_hash / stale_source_version 时不得进入 passed 状态。 |
| `docx_isolation_status` | yes | DOCX isolation 状态。blocked / not_created / stale_source_hash / stale_source_version 时不得进入 passed 状态。 |
| `zbid_isolation_status` | yes | ZBid isolation 状态。blocked / not_created / stale_source_hash / stale_source_version 时不得进入 passed 状态。 |
| `source_hash_revalidation_status` | yes | source hash revalidation 状态。mismatched / stale_source_hash / missing 时不得进入 passed 状态。 |
| `source_version_revalidation_status` | yes | source version revalidation 状态。mismatched / stale_source_version / missing 时不得进入 passed 状态。 |
| `source_hash_match` | yes | source hash 是否匹配。false 时不得进入 passed 状态。 |
| `source_version_match` | yes | source version 是否匹配。false 时不得进入 passed 状态。 |
| `human_approval_required` | yes | 是否需要人工确认。正式写回 dry-run 前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得进入 passed 状态。 |
| `diff_preview_required` | yes | 是否要求 diff preview。正式写回 dry-run 前必须为 true 并 ready。 |
| `diff_preview_ready` | yes | diff preview 是否 ready。false 时不得进入 passed 状态。 |
| `rollback_required` | yes | 是否要求 rollback plan。正式写回 dry-run 前必须为 true。 |
| `rollback_plan_ready` | yes | rollback plan 是否 ready。false 时不得进入 passed 状态。 |
| `formal_writeback_guard_required` | yes | 是否要求 formal writeback guard。dry-run 前必须为 true。 |
| `formal_writeback_guard_ready` | yes | formal writeback guard 是否 ready。false 时不得进入 passed 状态。 |
| `source_hash_revalidation_required` | yes | 是否要求 source hash revalidation。dry-run 前必须为 true。 |
| `source_hash_revalidation_ready` | yes | source hash revalidation 是否 ready。false 时不得进入 passed 状态。 |
| `review_apply_isolation_required` | yes | 是否要求 review/apply isolation。dry-run 前必须为 true。 |
| `review_apply_isolation_ready` | yes | review/apply isolation 是否 ready。false 时不得进入 passed 状态。 |
| `docx_isolation_required` | yes | 是否要求 DOCX isolation。dry-run 前必须为 true。 |
| `docx_isolation_ready` | yes | DOCX isolation 是否 ready。false 时不得进入 passed 状态。 |
| `zbid_isolation_required` | yes | 是否要求 ZBid isolation。dry-run 前必须为 true。 |
| `zbid_isolation_ready` | yes | ZBid isolation 是否 ready。false 时不得进入 passed 状态。 |
| `generated_at` | conditional | 未来 dry-run metadata 生成时间。应由调用方显式传入，不得使用非确定性时间。 |
| `model_provider` | conditional | 模型提供方元数据，仅用于审计。 |
| `model_name` | conditional | 模型名称元数据，仅用于审计。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `review_apply_allowed` | yes | 当前阶段必须为 false。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked、stale_source_hash 或 stale_source_version 的原因列表。 |

`dry_run_status` 即使为 `passed_shadow_only`，也不得代表当前已可写回。

`dry_run_payload_hash`、`dry_run_candidate_hash` 只能作为未来字段描述，不得读取真实 payload 或正文生成。

`formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 当前阶段必须保持 false。

## 5. Status Enums

### `dry_run_status`

- `not_created`：尚未创建 formal writeback dry-run metadata。
- `blocked`：存在硬性 blocker，不允许进入 dry-run passed 状态。
- `draft_dry_run_shadow_only`：未来仅 shadow-only 的 dry-run metadata 草稿，不等于可写回。
- `simulated_shadow_only`：未来只读模拟完成的 shadow-only 状态，不等于可写回。
- `passed_shadow_only`：未来 shadow-only dry-run 通过状态，不等于正式写回许可。
- `failed_shadow_only`：未来 shadow-only dry-run 失败状态。
- `rejected`：人工或系统拒绝状态，不得写回。
- `stale_source_hash`：source section hash 已过期或不一致，不得写回。
- `stale_source_version`：source section version 已过期或不一致，不得写回。

### `dry_run_decision`

- `none`：未形成决策。
- `block`：阻断。
- `simulate_shadow_only`：仅允许 shadow-only 模拟 metadata，不允许写回。
- `pass_shadow_only`：仅表示 shadow-only dry-run metadata 通过，不允许写回。
- `require_revision`：要求修订候选链路。
- `reject`：拒绝。

### `dry_run_scope`

- `single_section`：单章节范围。
- `selected_sections`：选定章节范围。
- `full_document`：全文档范围。当前阶段不得写入完整文档。
- `metadata_only`：仅元数据范围，不含写回产物。

### `dry_run_mode`

- `disabled_current_stage`：当前阶段禁用 dry-run 执行。
- `metadata_only`：仅构造 metadata，不执行模拟。
- `future_dry_run_only`：未来仅 dry-run，不写 source section。
- `future_guarded_dry_run`：未来 guard 保护下 dry-run，当前不实现。

### `dry_run_target_type`

- `source_section`：source section 目标类型。当前阶段不得修改。
- `section_draft`：section draft 目标类型。当前阶段不得接入正式链。
- `docx_document`：DOCX 文档目标类型。当前阶段不得导出。
- `zbid_section`：ZBid 章节目标类型。当前阶段不得写回。
- `metadata_only`：仅 metadata envelope。

### `dry_run_request_status`

- `not_requested`：未出现 formal writeback dry-run 请求。
- `requested_blocked`：出现 dry-run 请求且已阻断。
- `payload_blocked`：dry-run payload 或 payload hash 不满足隔离要求，已阻断。
- `future_dry_run_only`：未来 dry-run-only 状态，当前不实现。

当前阶段只设计状态，不实现状态机，不执行 dry-run。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `dry_run_status=passed_shadow_only` 不等于 `formal_writeback_allowed=true`。
2. `dry_run_decision=pass_shadow_only` 不等于 `formal_writeback_allowed=true`。
3. `dry_run_requested=true` 当前阶段必须 blocked。
4. formal writeback dry-run 不得替代 evidence anchor。
5. formal writeback dry-run 不得替代 human approval。
6. formal writeback dry-run 不得替代 diff preview。
7. formal writeback dry-run 不得替代 rollback plan。
8. formal writeback dry-run 不得替代 formal writeback guard。
9. formal writeback dry-run 不得替代 source hash revalidation。
10. formal writeback dry-run 不得替代 review/apply isolation。
11. formal writeback dry-run 不得替代 DOCX isolation。
12. formal writeback dry-run 不得替代 ZBid isolation。
13. `response_mode=thinking_only_fallback` 时，不得进入 dry-run passed 状态。
14. `shadow_candidate_status=blocked` 或 `not_created` 时，不得进入 dry-run passed 状态。
15. `patch_status=blocked` 或 `not_created` 时，不得进入 dry-run passed 状态。
16. `approval_status` 非 `approved_shadow_only` 时，不得进入 dry-run passed 状态。
17. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入 dry-run passed 状态。
18. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入 dry-run passed 状态。
19. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入 dry-run passed 状态。
20. `source_hash_guard_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 时，不得进入 dry-run passed 状态。
21. `review_apply_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 时，不得进入 dry-run passed 状态。
22. `docx_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 时，不得进入 dry-run passed 状态。
23. `zbid_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 时，不得进入 dry-run passed 状态。
24. `evidence_anchor_status=missing` 时，不得进入 dry-run passed 状态。
25. `evidence_binding_status=generated_advisory_only_blocked`、`shadow_candidate_only_blocked`、`patch_preview_only_blocked`、`diff_preview_only_blocked` 或 `rollback_plan_only_blocked` 时，不得进入 dry-run passed 状态。
26. `source_hash_match=false` 或 `source_version_match=false` 时，不得进入 dry-run passed 状态。
27. 当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须恒 false。
28. formal writeback dry-run contract 不得被 review/apply、export、DOCX、ZBid 直接消费。

即使 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation、review/apply isolation、DOCX isolation、ZBid isolation 均通过，dry-run passed 当前阶段也不得自动开放 formal writeback、DOCX export、ZBid writeback 或 output write。

## 7. Blocked Scenarios

以下场景必须 blocked，或在 source hash / source version 相关场景中进入 `stale_source_hash` / `stale_source_version`：

- no shadow candidate envelope。
- no shadow candidate patch。
- no human approval gate。
- no diff preview。
- no rollback plan。
- no formal writeback guard。
- no source hash revalidation guard。
- no review/apply isolation guard。
- no DOCX isolation guard。
- no ZBid isolation guard。
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
- source hash guard blocked。
- review/apply isolation blocked。
- DOCX isolation blocked。
- ZBid isolation blocked。
- thinking_only_fallback。
- unsupported response mode。
- no evidence anchor。
- advisory used as evidence。
- shadow candidate used as evidence。
- patch preview used as evidence。
- diff preview used as evidence。
- rollback plan used as evidence。
- high input risk without validation。
- missing advisory quality gate result。
- missing readiness metadata。
- missing source_section_hash。
- missing current_source_section_hash。
- missing source_section_version。
- missing current_source_section_version。
- source hash mismatch。
- source version mismatch。
- missing writeback_candidate_hash。
- missing docx_candidate_hash。
- missing zbid_candidate_hash。
- missing zbid_target_mapping_hash。
- missing source_snapshot_hash。
- missing before_text_hash。
- missing after_text_preview_hash。
- missing patch_operations_preview_hash。
- missing diff_preview_hash。
- missing rollback_plan_hash。
- dry-run requested。
- dry-run payload hash missing。
- dry-run candidate hash missing。
- output/job/export write request。
- formal generation request。
- review/apply request。
- DOCX export request。
- ZBid writeback request。

## 8. Dry-run Audit Requirements

未来 formal writeback dry-run 审计至少需要以下字段：

- `dry_run_id`
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
- `review_apply_guard_id`
- `docx_isolation_guard_id`
- `zbid_isolation_guard_id`
- `dry_run_status`
- `dry_run_decision`
- `dry_run_scope`
- `dry_run_mode`
- `dry_run_target_type`
- `dry_run_request_status`
- `dry_run_requested`
- `dry_run_payload_hash`
- `dry_run_candidate_hash`
- `generated_at`
- `blocked_reasons`

当前阶段不得写文件，不实现持久化，不生成正式 dry-run 记录，不写 `output/job/export`，不生成 DOCX / JSON / Markdown，不触发正式写回、review/apply、DOCX 导出或 ZBid 写回。

## 9. Future Implementation Acceptance Criteria

后续实现验收条件只作为 future work，不在 Step 137 实现：

- deterministic fake schema tests。
- dry-run status enum tests。
- dry-run request block tests。
- dry-run payload hash block tests。
- dry-run candidate hash block tests。
- missing upstream metadata block tests。
- missing evidence block tests。
- missing approval block tests。
- missing diff preview block tests。
- missing rollback plan block tests。
- missing formal writeback guard block tests。
- missing source hash revalidation block tests。
- missing review/apply isolation block tests。
- missing DOCX isolation block tests。
- missing ZBid isolation block tests。
- source hash mismatch / stale source hash block tests。
- DOCX / export / review apply / ZBid request block tests。
- formal flags false tests。
- no output/job/export filesystem write tests。
- no formal writeback tests。
- no source section mutation tests。
- import-isolation tests。

后续 fake schema tests 和 fake-only helper 仍必须保持 standard-library-only、deterministic、no-write、no-runtime、no-service、no-model、no-ZBid API / DB / writeback 的边界。

## 10. Migration Path

后续可能步骤如下，但 Step 137 不执行：

- Step 138 可做 formal writeback dry-run contract fake schema tests。
- Step 139 可做 fake-only formal writeback dry-run helper。
- Step 140 可做 fake formal writeback dry-run stage review。
- Step 141 可做 local trial integration checklist design。
- Step 142 可做 ZDoc/ZBid preview-only integration contract design。
- 后续先完成本地化部署基础闭环和 ZDoc/ZBid 小范围对接试用，最后再按约 50 人同时使用场景进行正式部署方案设计。

## 11. Safety Conclusion

Step 137 仅完成 formal writeback dry-run contract design，不代表 dry-run helper、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。

当前系统仍处于 preview-only / no-write 阶段。formal writeback dry-run 只能作为未来正式写回前的只读模拟与准入验证记录设计，不开放 formal writeback，不开放 review/apply，不开放 DOCX export，不开放 ZBid writeback，不写 `output/job/export`，不修改 source section。
