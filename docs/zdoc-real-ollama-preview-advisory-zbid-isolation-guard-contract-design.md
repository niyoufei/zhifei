# ZDoc Real Ollama Preview Advisory - ZBid Isolation Guard Contract Design

## 1. Scope

Step 133 仅定义未来 ZBid isolation guard 的数据契约，不实现 ZBid isolation helper，不触发 ZBid 写回，不调用 ZBid API / ZBid 数据库 / ZBid 写回接口，不执行正式写回，不修改 source section，不触发 review/apply，不触发 `/export_docx`，不生成 DOCX / JSON / Markdown，不写 `output/job/export`。系统仍处于 preview-only / no-write 阶段。

ZBid isolation guard 仅是未来阻断 ZBid 写回误触发、误写入和越权消费 candidate / diff / rollback / DOCX 的隔离门禁。它用于把 evidence anchor、shadow candidate envelope、shadow candidate patch、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation guard、review/apply isolation guard、DOCX isolation guard 等上游状态汇总为可审计的 ZBid isolation metadata。

ZBid isolation guard 不等于 ZBid 写回动作。它不得触发 ZBid 写回，不得调用 ZBid API、数据库或写回接口，不得写 `output/job/export`，不得直接修改 source section，不得直接触发 review/apply，不得直接触发 `/export_docx`，也不得生成 DOCX / JSON / Markdown。

ZBid isolation guard 不得替代 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation、review/apply isolation 或 DOCX isolation。缺少真实 evidence anchor 时，不得进入可 ZBid 写回状态。缺少 human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation、review/apply isolation、DOCX isolation 任一前置条件时，也不得进入可 ZBid 写回状态。

ZBid 写回请求必须默认 blocked，除非未来明确进入 guarded writeback 阶段。当前阶段不得开放。即使 formal writeback guard、source hash revalidation、review/apply isolation 和 DOCX isolation 均通过，也不得自动开放 ZBid 写回。

当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 仍必须保持 false。

本文档仅为后续 fake schema tests 和 fake-only helper 提供 contract design，不代表 ZBid isolation helper、ZBid 写回、DOCX 导出、正式写回或 review/apply 已实现。

## 2. Non-goals

本步明确排除以下事项：

- 不实现 ZBid isolation helper。
- 不执行 ZBid isolation。
- 不触发 ZBid 写回。
- 不调用 ZBid API。
- 不写 ZBid 数据库。
- 不调用 ZBid 写回接口。
- 不执行正式写回。
- 不修改 source section。
- 不触发 review/apply。
- 不触发 `/review/apply`。
- 不触发 `/export_docx`。
- 不生成 DOCX / JSON / Markdown。
- 不写 `output/job/export`。
- 不进入真实 shadow generation implementation。
- 不生成真实 candidate patch。
- 不进入真实 candidate patch implementation。
- 不进入正式正文生成链。
- 不接 DOCX 导出。
- 不接 ZBid 正式写回。
- 不实现 human approval UI。
- 不实现 approval persistence。
- 不执行真实 diff。
- 不执行真实 rollback。
- 不恢复正文。
- 不读取真实正文计算 hash。
- 不比较真实 source section 内容。
- 不执行 review/apply isolation。
- 不执行 DOCX isolation。
- 不调用模型。
- 不调用 Ollama。
- 不调用外部模型或 API。
- 不启动服务。
- 不访问 `127.0.0.1:11434`。
- 不把 ZBid isolation 通过当作实际 ZBid 写回许可。
- 不把 ZBid isolation 通过当作 DOCX / export 准入。
- 不把 ZBid isolation 通过当作 evidence、approval、diff、rollback、formal guard、source hash revalidation、review/apply isolation、DOCX isolation 的替代条件。

ZBid isolation guard contract 不得被 export、DOCX、review/apply、actions_bridge、orchestrator、generation 或 ZBid 链路直接消费。

## 3. Upstream Prerequisites

未来 ZBid isolation guard 至少依赖以下上游信息。本步只定义依赖关系，不实现采集、路由、payload 读取、ZBid 数据读取、正文读取、状态机、写回、导出、持久化或隔离执行：

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
- `source_section_hash`。
- `source_section_version`。
- `current_source_section_hash` placeholder。
- `current_source_section_version` placeholder。
- ZBid writeback request placeholder。
- ZBid payload hash placeholder。
- ZBid target mapping placeholder。
- explicit user approval flow placeholder。

这些上游项均是未来 guarded ZBid writeback 的必要但不充分条件。ZBid isolation guard 只能检查和汇总这些条件，不得替代任何条件本身。

## 4. ZBidIsolationGuardContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `zbid_isolation_guard_id` | conditional | 未来 ZBid isolation guard ID。不得使用随机值；如生成，应基于输入确定性生成。 |
| `request_id` | yes | 关联 preview / candidate / patch / approval / diff / rollback / writeback / source hash / review apply / DOCX guard 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。guard 不得覆盖或修改该章节。 |
| `source_section_hash` | yes | 原始 candidate baseline 中记录的来源章节 hash。缺失时必须 blocked。 |
| `source_section_version` | yes | 原始 candidate baseline 中记录的来源章节版本。缺失时必须 blocked。 |
| `current_source_section_hash` | yes | 未来调用方提供的当前来源章节 hash 占位字段。本步不读取正文、不计算真实 hash。 |
| `current_source_section_version` | yes | 未来调用方提供的当前来源章节版本占位字段。本步不读取正文、不比较真实章节。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope。缺失时不得进入可 ZBid 写回状态。 |
| `patch_id` | yes | 关联 shadow candidate patch。缺失时不得进入可 ZBid 写回状态。 |
| `approval_id` | yes | 关联 human approval gate。缺失或未批准时不得进入可 ZBid 写回状态。 |
| `diff_preview_id` | yes | 关联 diff preview。缺失时不得进入可 ZBid 写回状态。 |
| `rollback_plan_id` | yes | 关联 rollback plan。缺失时不得进入可 ZBid 写回状态。 |
| `writeback_guard_id` | yes | 关联 formal writeback guard。缺失时不得进入可 ZBid 写回状态。 |
| `source_hash_guard_id` | yes | 关联 source hash revalidation guard。缺失时不得进入可 ZBid 写回状态。 |
| `review_apply_guard_id` | yes | 关联 review/apply isolation guard。缺失时不得进入可 ZBid 写回状态。 |
| `docx_isolation_guard_id` | yes | 关联 DOCX isolation guard。缺失时不得进入可 ZBid 写回状态。 |
| `zbid_isolation_status` | yes | ZBid isolation 生命周期状态。当前阶段只设计，不实现状态机。 |
| `zbid_writeback_decision` | yes | ZBid isolation 决策，例如 none、block、isolate_shadow_only、require_revision、reject。 |
| `zbid_writeback_scope` | yes | ZBid writeback 隔离范围，例如 single_section、selected_sections、full_document、metadata_only。 |
| `zbid_writeback_mode` | yes | ZBid writeback 模式。当前阶段必须是 disabled_current_stage 或 dry_run_only 语义。 |
| `zbid_target_type` | yes | ZBid writeback 目标类型，例如 zbid_section、zbid_document、zbid_scoring_matrix、zbid_metadata、metadata_only。当前阶段不得写入。 |
| `zbid_writeback_request_status` | yes | ZBid 写回请求状态。当前阶段 requested、route、payload 或 mapping 均必须 blocked。 |
| `zbid_writeback_requested` | yes | 是否出现 ZBid writeback 请求。当前阶段 true 必须 blocked。 |
| `zbid_writeback_route` | conditional | 未来 ZBid 写回 route / endpoint 元数据。只能作为未来字段描述，不得触发真实接口。任何 ZBid 写回接口当前阶段必须 blocked。 |
| `zbid_writeback_payload_hash` | conditional | 未来 ZBid payload hash 元数据。只能作为未来字段描述，不得读取真实 payload 生成。缺失时不得进入可 ZBid 写回状态。 |
| `zbid_candidate_hash` | conditional | 未来 ZBid candidate hash 元数据。只能作为未来字段描述，不得读取真实 ZBid 数据生成。缺失时不得进入可 ZBid 写回状态。 |
| `zbid_target_mapping_hash` | conditional | 未来 ZBid target mapping hash 元数据。不得读取真实 ZBid 数据生成。缺失时不得进入可 ZBid 写回状态。 |
| `zbid_source_snapshot_hash` | conditional | 未来 ZBid source snapshot hash 元数据。不得读取真实正文或真实 ZBid 数据生成。 |
| `docx_candidate_hash` | conditional | 上游 DOCX candidate hash 元数据。不得替代 DOCX isolation。缺失时不得进入可 ZBid 写回状态。 |
| `writeback_candidate_hash` | yes | 候选写回内容或 metadata 的 hash。缺失时不得进入可 ZBid 写回状态。 |
| `source_snapshot_hash` | yes | 写回前 source snapshot hash。缺失时不得进入可 ZBid 写回状态。 |
| `before_text_hash` | yes | 修改前文本 hash，用于 source hash revalidation、diff 和 rollback。 |
| `after_text_preview_hash` | yes | 修改后预览文本 hash，不代表正式正文。 |
| `patch_operations_preview_hash` | yes | patch operations 预览 hash，不代表可执行 patch。 |
| `diff_preview_hash` | yes | diff preview hash。缺失时不得进入可 ZBid 写回状态。 |
| `rollback_plan_hash` | yes | rollback plan hash。缺失时不得进入可 ZBid 写回状态。 |
| `affected_anchor_refs` | yes | 受影响 anchor 引用列表，不得自动等同于 evidence refs。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 时不得进入可 ZBid 写回状态。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表，不得包含 advisory、shadow candidate、patch preview、diff preview、rollback plan 或 DOCX preview。 |
| `evidence_binding_status` | yes | evidence 绑定状态。generated / shadow-only / patch-only / diff-only / rollback-only 均不得进入可 ZBid 写回状态。 |
| `response_mode` | yes | 上游 response-mode。thinking_only_fallback 不得进入可 ZBid 写回状态。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `advisory_quality_gate_status` | yes | advisory quality gate 结果。缺失或 blocked 时不得进入可 ZBid 写回状态。 |
| `readiness_status` | yes | shadow readiness 结果。缺失或 blocked 时不得进入可 ZBid 写回状态。 |
| `shadow_candidate_status` | yes | shadow candidate 状态。blocked / not_created 时不得进入可 ZBid 写回状态。 |
| `patch_status` | yes | shadow candidate patch 状态。blocked / not_created 时不得进入可 ZBid 写回状态。 |
| `approval_status` | yes | human approval gate 状态。未达到 approved_shadow_only 时不得进入可 ZBid 写回状态。 |
| `diff_preview_status` | yes | diff preview 状态。blocked / not_created / stale_source_hash 时不得进入可 ZBid 写回状态。 |
| `rollback_plan_status` | yes | rollback plan 状态。blocked / not_created / stale_source_hash 时不得进入可 ZBid 写回状态。 |
| `writeback_guard_status` | yes | formal writeback guard 状态。blocked / not_created / stale_source_hash 时不得进入可 ZBid 写回状态。 |
| `source_hash_guard_status` | yes | source hash guard 状态。blocked / not_created / stale_source_hash / stale_source_version 时不得进入可 ZBid 写回状态。 |
| `review_apply_isolation_status` | yes | review/apply isolation 状态。blocked / not_created / stale_source_hash / stale_source_version 时不得进入可 ZBid 写回状态。 |
| `docx_isolation_status` | yes | DOCX isolation 状态。blocked / not_created / stale_source_hash / stale_source_version 时不得进入可 ZBid 写回状态。 |
| `source_hash_revalidation_status` | yes | source hash revalidation 状态。mismatched / stale_source_hash / missing 时不得进入可 ZBid 写回状态。 |
| `source_version_revalidation_status` | yes | source version revalidation 状态。mismatched / stale_source_version / missing 时不得进入可 ZBid 写回状态。 |
| `source_hash_match` | yes | source hash 是否匹配。false 时不得进入可 ZBid 写回状态。 |
| `source_version_match` | yes | source version 是否匹配。false 时不得进入可 ZBid 写回状态。 |
| `human_approval_required` | yes | 是否需要人工确认。正式 ZBid 写回前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得进入可 ZBid 写回状态。 |
| `diff_preview_required` | yes | 是否要求 diff preview。正式 ZBid 写回前必须为 true 并 ready。 |
| `diff_preview_ready` | yes | diff preview 是否 ready。false 时不得进入可 ZBid 写回状态。 |
| `rollback_required` | yes | 是否要求 rollback plan。正式 ZBid 写回前必须为 true。 |
| `rollback_plan_ready` | yes | rollback plan 是否 ready。false 时不得进入可 ZBid 写回状态。 |
| `formal_writeback_guard_required` | yes | 是否要求 formal writeback guard。正式 ZBid 写回前必须为 true。 |
| `formal_writeback_guard_ready` | yes | formal writeback guard 是否 ready。false 时不得进入可 ZBid 写回状态。 |
| `source_hash_revalidation_required` | yes | 是否要求 source hash revalidation。正式 ZBid 写回前必须为 true。 |
| `source_hash_revalidation_ready` | yes | source hash revalidation 是否 ready。false 时不得进入可 ZBid 写回状态。 |
| `review_apply_isolation_required` | yes | 是否要求 review/apply isolation。正式 ZBid 写回前必须为 true。 |
| `review_apply_isolation_ready` | yes | review/apply isolation 是否 ready。false 时不得进入可 ZBid 写回状态。 |
| `docx_isolation_required` | yes | 是否要求 DOCX isolation。正式 ZBid 写回前必须为 true。 |
| `docx_isolation_ready` | yes | DOCX isolation 是否 ready。false 时不得进入可 ZBid 写回状态。 |
| `generated_at` | conditional | 未来 guard metadata 生成时间。应由调用方显式传入，不得使用非确定性时间。 |
| `model_provider` | conditional | 模型提供方元数据，仅用于审计。 |
| `model_name` | conditional | 模型名称元数据，仅用于审计。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `review_apply_allowed` | yes | 当前阶段必须为 false。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked、stale_source_hash 或 stale_source_version 的原因列表。 |

`zbid_writeback_allowed` 当前阶段必须为 false。`zbid_writeback_requested=true` 当前阶段必须 blocked。`zbid_writeback_route` 只能作为未来字段描述，不得触发真实接口。`zbid_writeback_payload_hash` 只能作为未来字段描述，不得读取真实 payload 生成。`zbid_candidate_hash`、`zbid_target_mapping_hash` 只能作为未来字段描述，不得读取真实 ZBid 数据生成。

## 5. Status Enums

### `zbid_isolation_status`

- `not_created`：尚未创建 ZBid isolation guard。
- `blocked`：存在硬性 blocker，不允许进入 ZBid 写回。
- `draft_isolation_shadow_only`：未来仅 shadow 隔离的 isolation metadata 草稿，不等于可写回。
- `isolated_shadow_only`：未来已完成 shadow-only 隔离的 metadata 状态，不等于可写回。
- `ready_for_future_manual_writeback`：未来可进入人工受控写回的 metadata 状态，当前不开放。
- `rejected`：人工或系统拒绝状态，不得写回。
- `stale_source_hash`：source section hash 已过期或不一致，不得写回。
- `stale_source_version`：source section version 已过期或不一致，不得写回。

### `zbid_writeback_decision`

- `none`：未形成决策。
- `block`：阻断。
- `isolate_shadow_only`：仅允许 shadow-only isolation metadata 进入后续审查，不允许 ZBid 写回。
- `require_revision`：要求修订候选链路。
- `reject`：拒绝。

### `zbid_writeback_scope`

- `single_section`：单章节范围。
- `selected_sections`：选定章节范围。
- `full_document`：全文档范围。当前阶段不得写入完整 ZBid 文档。
- `metadata_only`：仅元数据范围，不含写回产物。

### `zbid_writeback_mode`

- `disabled_current_stage`：当前阶段禁用 ZBid writeback。
- `dry_run_only`：未来仅 dry-run，不写 ZBid。
- `future_manual_writeback`：未来人工受控 writeback，当前不实现。
- `future_guarded_writeback`：未来 guard 保护下 writeback，当前不实现。

### `zbid_target_type`

- `zbid_section`：ZBid 章节目标类型。当前阶段不得写入。
- `zbid_document`：ZBid 文档目标类型。当前阶段不得写入。
- `zbid_scoring_matrix`：ZBid 评分矩阵目标类型。当前阶段不得写入。
- `zbid_metadata`：ZBid 元数据目标类型。当前阶段不得写入。
- `metadata_only`：仅 metadata envelope。

### `zbid_writeback_request_status`

- `not_requested`：未出现 ZBid writeback 请求。
- `requested_blocked`：出现 ZBid writeback 请求且已阻断。
- `route_blocked`：ZBid writeback route / endpoint 请求已阻断。
- `payload_blocked`：ZBid writeback payload 或 payload hash 不满足隔离要求，已阻断。
- `mapping_blocked`：ZBid target mapping 不满足隔离要求，已阻断。
- `future_dry_run_only`：未来 dry-run-only 状态，当前不实现。

当前阶段只设计状态，不实现状态机，不触发 ZBid 写回。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `zbid_isolation_status=isolated_shadow_only` 不等于 `zbid_writeback_allowed=true`。
2. `zbid_writeback_decision=isolate_shadow_only` 不等于 `zbid_writeback_allowed=true`。
3. `zbid_writeback_requested=true` 当前阶段必须 blocked。
4. `zbid_writeback_route` 指向任何 ZBid 写回接口时，当前阶段必须 blocked。
5. ZBid isolation 不得替代 evidence anchor。
6. ZBid isolation 不得替代 human approval。
7. ZBid isolation 不得替代 diff preview。
8. ZBid isolation 不得替代 rollback plan。
9. ZBid isolation 不得替代 formal writeback guard。
10. ZBid isolation 不得替代 source hash revalidation。
11. ZBid isolation 不得替代 review/apply isolation。
12. ZBid isolation 不得替代 DOCX isolation。
13. `response_mode=thinking_only_fallback` 时，不得进入可 ZBid 写回状态。
14. `shadow_candidate_status=blocked` 或 `not_created` 时，不得进入可 ZBid 写回状态。
15. `patch_status=blocked` 或 `not_created` 时，不得进入可 ZBid 写回状态。
16. `approval_status` 未达到 `approved_shadow_only` 时，不得进入可 ZBid 写回状态。
17. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可 ZBid 写回状态。
18. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可 ZBid 写回状态。
19. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 时，不得进入可 ZBid 写回状态。
20. `source_hash_guard_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 时，不得进入可 ZBid 写回状态。
21. `review_apply_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 时，不得进入可 ZBid 写回状态。
22. `docx_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 时，不得进入可 ZBid 写回状态。
23. `evidence_anchor_status=missing` 时，不得进入可 ZBid 写回状态。
24. `evidence_binding_status=generated_advisory_only_blocked`、`shadow_candidate_only_blocked`、`patch_preview_only_blocked`、`diff_preview_only_blocked` 或 `rollback_plan_only_blocked` 时，不得进入可 ZBid 写回状态。
25. `source_hash_match=false` 或 `source_version_match=false` 时，不得进入可 ZBid 写回状态。
26. 当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须恒 false。
27. ZBid isolation guard contract 不得被 export、DOCX、review/apply 或 ZBid 直接消费。

即使 formal writeback guard、source hash revalidation、review/apply isolation 和 DOCX isolation 均通过，当前阶段也不得自动开放 ZBid 写回。

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
- shadow candidate status blocked。
- patch status blocked。
- approval not received。
- diff preview blocked。
- rollback plan blocked。
- formal writeback guard blocked。
- source hash guard blocked。
- review/apply isolation blocked。
- DOCX isolation blocked。
- thinking_only_fallback。
- unsupported response mode。
- no evidence anchor。
- advisory used as evidence。
- shadow candidate used as evidence。
- patch preview used as evidence。
- diff preview used as evidence。
- rollback plan used as evidence。
- missing source_section_hash。
- missing current_source_section_hash。
- source hash mismatch。
- source version mismatch。
- missing writeback_candidate_hash。
- missing source_snapshot_hash。
- missing before_text_hash。
- missing after_text_preview_hash。
- missing patch_operations_preview_hash。
- missing diff_preview_hash。
- missing rollback_plan_hash。
- missing docx_candidate_hash。
- missing zbid_candidate_hash。
- missing zbid_target_mapping_hash。
- ZBid writeback requested。
- ZBid writeback route requested。
- ZBid payload hash missing。
- ZBid target mapping missing。
- output/job/export write request。
- formal generation request。
- review/apply request。
- DOCX export request。

## 8. ZBid Isolation Audit Requirements

未来 ZBid isolation guard 审计至少需要以下字段：

- `zbid_isolation_guard_id`
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
- `zbid_isolation_status`
- `zbid_writeback_decision`
- `zbid_writeback_scope`
- `zbid_writeback_mode`
- `zbid_target_type`
- `zbid_writeback_request_status`
- `zbid_writeback_requested`
- `zbid_writeback_route`
- `zbid_writeback_payload_hash`
- `zbid_candidate_hash`
- `zbid_target_mapping_hash`
- `generated_at`
- `blocked_reasons`

当前阶段不得写文件，不实现持久化，不生成正式 ZBid 写回记录，不调用 ZBid API / ZBid 数据库 / ZBid 写回接口。

## 9. Future Implementation Acceptance Criteria

后续实现验收条件只作为 future work，不在 Step 133 实现：

- deterministic fake schema tests。
- ZBid isolation status enum tests。
- ZBid writeback request block tests。
- ZBid route block tests。
- ZBid payload hash block tests。
- ZBid target mapping hash block tests。
- missing upstream metadata block tests。
- missing evidence block tests。
- missing approval block tests。
- missing diff preview block tests。
- missing rollback plan block tests。
- missing formal writeback guard block tests。
- missing source hash revalidation block tests。
- missing review/apply isolation block tests。
- missing DOCX isolation block tests。
- source hash mismatch / stale source hash block tests。
- DOCX / export / review apply block tests。
- formal flags false tests。
- no output/job/export filesystem write tests。
- no ZBid writeback tests。
- no source section mutation tests。
- import-isolation tests。

## 10. Migration Path

后续可能步骤如下，但 Step 133 不执行：

- Step 134 可做 ZBid isolation guard contract fake schema tests。
- Step 135 可做 fake-only ZBid isolation guard helper。
- Step 136 可做 fake ZBid isolation guard stage review。
- Step 137 可做 formal writeback dry-run contract design。
- 后续仍需正式写回人工审批闭环、dry-run no-write 验证、DOCX / ZBid post-write isolation verification。

## 11. Safety Conclusion

Step 133 仅完成 ZBid isolation guard contract design，不代表 ZBid isolation helper、ZBid 写回、DOCX 导出、正式写回或 review/apply 已实现。

当前系统仍处于 preview-only / no-write 阶段。ZBid isolation guard 只能作为未来 metadata contract 和隔离门禁设计，不开放 ZBid 写回，不开放 DOCX 导出，不开放 review/apply，不开放 formal writeback，不写 `output/job/export`，不修改 source section。
