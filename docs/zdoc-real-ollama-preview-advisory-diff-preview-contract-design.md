# ZDoc Real Ollama Preview Advisory - Diff Preview Contract Design

## 1. Scope

Step 109 仅定义未来 diff preview 的数据契约，不实现 diff preview helper，不执行真实 diff，不比较真实正文并生成可写回差异。系统仍处于 preview-only / no-write 阶段。

diff preview 仅是未来“候选修改前后差异”的隔离预览数据结构，用于描述 shadow candidate patch 对 source section 的预期差异、差异范围、差异格式、证据锚点绑定、human approval、source hash revalidation、rollback plan 和 formal writeback guard 的前置状态。diff preview 不等于正式正文修改，不得直接写回 source section，不得直接触发 review/apply，不得直接进入 DOCX / JSON / Markdown 导出，不得直接进入 ZBid 写回，也不得作为 evidence。

本文档仅为后续 fake schema tests 和 fake-only diff preview helper 提供 contract design，不代表 diff preview helper、真实 diff、rollback plan、formal writeback、DOCX 导出或 ZBid 写回已实现。

## 2. Non-goals

本步明确排除以下事项：

- 不实现 diff preview helper。
- 不执行真实 diff。
- 不比较真实正文并生成可写回差异。
- 不触发 review/apply。
- 不执行正式写回。
- 不生成 DOCX / JSON / Markdown。
- 不写 `output/job/export`。
- 不接 ZBid 写回。
- 不实现 rollback plan。
- 不实现 formal writeback guard。
- 不实现 DOCX / ZBid isolation guard。
- 不调用模型。
- 不调用 Ollama。
- 不调用外部模型或 API。
- 不启动服务。
- 不访问 `127.0.0.1:11434`。
- 不把 diff preview 当 evidence。
- 不把 diff preview 当 formal writeback permission。
- 不把 diff preview 当 human approval、rollback plan 或 formal writeback guard 的替代条件。

diff preview contract 不得被 orchestrator、generation、export、review/apply、actions_bridge、DOCX 或 ZBid 链路直接消费。

## 3. Upstream Prerequisites

未来 diff preview 至少依赖以下上游信息。本步只定义依赖关系，不实现采集、校验、状态机、diff 计算、持久化或写回：

- preview advisory quality gate result。
- input risk snapshot。
- evidence anchor validation result。
- response mode classification。
- shadow generation readiness metadata。
- shadow candidate envelope metadata。
- shadow candidate patch metadata。
- human approval gate metadata。
- source section hash。
- source section version。
- `before_text_hash`。
- `after_text_preview` or `patch_operations_preview`。
- source hash revalidation placeholder。
- rollback plan placeholder。
- formal writeback guard placeholder。

缺少真实 evidence anchor 时，不得进入可写回状态。缺少 source hash revalidation、human approval、rollback plan 或 formal writeback guard 时，不得进入可写回状态。human approval 不得替代 diff preview，diff preview 也不得替代 evidence anchor、human approval、rollback plan 或 formal writeback guard。

## 4. DiffPreviewContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `diff_preview_id` | conditional | 未来隔离 diff preview ID。不得使用随机值；如生成，应基于输入确定性生成。 |
| `request_id` | yes | 关联 preview / candidate / patch / approval / diff 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。diff preview 不得覆盖该章节。 |
| `source_section_hash` | yes | 来源章节 hash。缺失或与 diff 基准不一致时不得写回。 |
| `source_section_version` | yes | 来源章节版本，用于 diff / rollback / writeback 前置校验。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope。缺失时不得生成可写回 diff。 |
| `patch_id` | yes | 关联 shadow candidate patch。缺失时不得生成可写回 diff。 |
| `approval_id` | yes | 关联 human approval gate。缺失或未批准时不得生成可写回 diff。 |
| `diff_preview_status` | yes | diff preview 生命周期状态。当前阶段只设计，不实现状态机。 |
| `diff_scope` | yes | diff 范围，例如 single_section、paragraph_range、anchor_range、metadata_only。 |
| `diff_format` | yes | diff 表达格式，例如 text_diff_preview、structured_diff_preview、metadata_only。 |
| `diff_operation_type` | yes | diff 操作类型，例如 no_op、replace、insert、delete、reorder、mixed。 |
| `diff_summary_preview` | conditional | 未来隔离差异摘要预览字段。本步不得宣称已生成真实 diff。 |
| `diff_operations_preview` | conditional | 未来隔离差异操作预览字段。本步不得宣称已生成真实 diff operations。 |
| `before_text_hash` | yes | 修改前文本 hash，用于 diff 基准、rollback 和 source hash revalidation。 |
| `after_text_preview_hash` | conditional | 修改后预览文本 hash。本步不生成真实 after text。 |
| `patch_operations_preview_hash` | conditional | patch operations 预览 hash。本步不生成真实 patch operations。 |
| `affected_anchor_refs` | yes | diff 影响的 anchor 引用列表，不得自动等同于 evidence refs。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 时不得进入可写回状态。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表，不得包含 advisory、shadow candidate、patch preview 或 diff preview。 |
| `evidence_binding_status` | yes | evidence 绑定状态。generated / shadow-only / patch-only / diff-only 均不得写回。 |
| `response_mode` | yes | 上游 response-mode。thinking_only_fallback 不得生成可写回 diff。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `advisory_quality_gate_status` | yes | advisory quality gate 结果。缺失或 blocked 时不得写回。 |
| `readiness_status` | yes | shadow readiness 结果。缺失或 blocked 时不得生成可写回 diff。 |
| `shadow_candidate_status` | yes | shadow candidate 状态。blocked / not_created 时不得生成可写回 diff。 |
| `patch_status` | yes | shadow candidate patch 状态。blocked / not_created 时不得生成可写回 diff。 |
| `approval_status` | yes | human approval gate 状态。未达到 approved_shadow_only 时不得进入可写回状态。 |
| `human_approval_required` | yes | 是否需要人工确认。正式写回前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得写回。 |
| `source_hash_revalidation_required` | yes | 是否要求写回前重新校验 source section hash。 |
| `source_hash_revalidation_ready` | yes | source hash revalidation 是否 ready。false 时不得写回。 |
| `rollback_required` | yes | 是否要求 rollback plan。正式写回前必须为 true。 |
| `rollback_plan_ready` | yes | rollback plan 是否 ready。false 时不得写回。 |
| `formal_writeback_guard_required` | yes | 是否要求 formal writeback guard。 |
| `formal_writeback_guard_ready` | yes | formal writeback guard 是否 ready。false 时不得写回。 |
| `generated_at` | conditional | 未来 diff preview 生成时间。应由调用方显式传入，不得使用非确定性时间。 |
| `model_provider` | conditional | 模型提供方元数据，仅用于审计。 |
| `model_name` | conditional | 模型名称元数据，仅用于审计。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked、not_created 或 stale_source_hash 的原因列表。 |

`diff_summary_preview` 和 `diff_operations_preview` 当前只能作为未来隔离预览字段描述，不代表 Step 109 已生成真实 diff、真实正文修改或可写回 patch。它们不得被 review/apply、export、DOCX、ZBid 或正式生成链直接消费。

## 5. Status Enums

### `diff_preview_status`

- `not_created`：尚未创建 diff preview。当前阶段默认状态之一。
- `blocked`：存在硬性 blocker，不允许进入 diff preview 或写回链。
- `draft_diff_shadow_only`：未来仅 shadow 隔离的 diff 草稿，不等于正式正文修改。
- `ready_for_human_review`：未来可供人工审查的隔离 diff preview，仍不等于写回。
- `approved_diff_shadow_only`：未来人工确认后的 shadow-only diff 状态，不等于正式写回。
- `rejected`：人工或系统拒绝状态，不得写回。
- `stale_source_hash`：source section hash 已过期或与 diff 基准不一致，不得写回。

### `diff_scope`

- `single_section`：单章节范围。
- `paragraph_range`：段落范围。
- `anchor_range`：锚点范围。
- `metadata_only`：仅元数据范围，不含正文 diff。

### `diff_format`

- `text_diff_preview`：文本差异预览。
- `structured_diff_preview`：结构化差异预览。
- `metadata_only`：仅元数据。

### `diff_operation_type`

- `no_op`：无正文操作。
- `replace`：替换。
- `insert`：插入。
- `delete`：删除。
- `reorder`：重排。
- `mixed`：混合操作。

当前阶段只设计状态，不实现状态机，不执行真实 diff。任何状态设计都不改变 preview-only / no-write 边界。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `diff_preview_status=approved_diff_shadow_only` 不等于 `formal_writeback_allowed=true`。
2. diff preview 不得作为 evidence。
3. diff preview 不得替代 evidence anchor。
4. diff preview 不得替代 human approval。
5. diff preview 不得替代 rollback plan。
6. diff preview 不得替代 formal writeback guard。
7. `response_mode=thinking_only_fallback` 时，不得生成可写回 diff。
8. `shadow_candidate_status=blocked` 或 `not_created` 时，不得生成可写回 diff。
9. `patch_status=blocked` 或 `not_created` 时，不得生成可写回 diff。
10. `approval_status` 未达到 `approved_shadow_only` 时，不得生成可写回 diff。
11. `evidence_anchor_status=missing` 时，不得进入可写回状态。
12. `evidence_binding_status=generated_advisory_only_blocked`、`shadow_candidate_only_blocked` 或 `patch_preview_only_blocked` 时，不得进入可写回状态。
13. diff preview used as evidence 时，不得进入可写回状态。
14. `source_hash_revalidation_ready=false` 时，不得进入可写回状态。
15. `rollback_plan_ready=false` 时，不得进入可写回状态。
16. `formal_writeback_guard_ready=false` 时，不得进入可写回状态。
17. `source_section_hash` 缺失或与 diff 基准不一致时，`diff_preview_status` 必须为 `blocked` 或 `stale_source_hash`。
18. `before_text_hash` 缺失时，不得进入可写回状态。
19. `after_text_preview_hash` 和 `patch_operations_preview_hash` 均缺失时，不得进入可写回状态。
20. `docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 当前阶段必须恒 false。
21. `formal_writeback_allowed` 当前阶段必须恒 false。
22. diff preview contract 不得被 review/apply、export、DOCX 或 ZBid 直接消费。

## 7. Blocked Scenarios

以下场景必须 blocked，或在 source hash 相关场景中进入 `stale_source_hash`：

- no shadow candidate envelope。
- no shadow candidate patch。
- no human approval gate。
- shadow candidate status blocked。
- shadow candidate status not_created。
- patch status blocked。
- patch status not_created。
- approval not received。
- approval revoked、expired、rejected 或 pending。
- thinking_only_fallback。
- unsupported response mode。
- no evidence anchor。
- advisory used as evidence。
- shadow candidate used as evidence。
- shadow candidate envelope used as evidence。
- patch preview used as evidence。
- diff preview used as evidence。
- high input risk without validation。
- missing advisory quality gate result。
- missing readiness metadata。
- missing source section hash。
- source section hash mismatch。
- missing before_text_hash。
- missing after_text_preview_hash。
- missing patch_operations_preview_hash。
- missing source hash revalidation。
- missing rollback plan。
- missing formal writeback guard。
- DOCX export request。
- ZBid writeback request。
- output / job / export write request。
- formal generation request。
- review/apply request。

任何 blocked scenario 都不得通过 human approval 或 diff preview 绕过。diff preview 只能作为 future writeback 的必要前置条件之一，不是充分条件。

## 8. Diff Preview Audit Requirements

未来 diff preview 审计至少需要以下字段：

- `diff_preview_id`
- `request_id`
- `source_document_id`
- `source_section_id`
- `source_section_hash`
- `source_section_version`
- `shadow_candidate_id`
- `patch_id`
- `approval_id`
- `diff_preview_status`
- `diff_scope`
- `diff_format`
- `before_text_hash`
- `after_text_preview_hash`
- `patch_operations_preview_hash`
- `affected_anchor_refs`
- `generated_at`
- `blocked_reasons`

当前阶段不得写文件，不实现持久化，不生成正式 diff 产物，不写 `output/job/export`。diff preview audit metadata 只能作为未来 contract design，不代表已存在 UI、数据库、文件日志、review/apply 集成或正式写回流程。

## 9. Future Implementation Acceptance Criteria

后续如进入实现，至少需要满足以下验收条件。本步不实现、不运行测试：

- deterministic fake schema tests。
- diff status enum tests。
- missing approval block tests。
- diff cannot replace evidence tests。
- diff cannot replace human approval tests。
- diff cannot replace rollback tests。
- diff cannot replace formal writeback guard tests。
- source hash mismatch block tests。
- stale source hash block tests。
- missing before / after hash block tests。
- missing patch operations preview hash block tests。
- thinking_only_fallback block tests。
- generated-advisory-as-evidence block tests。
- shadow-candidate-as-evidence block tests。
- patch-preview-as-evidence block tests。
- diff-preview-as-evidence block tests。
- DOCX / ZBid / export / review apply block tests。
- formal flags false tests。
- no output / job / export filesystem write tests。
- import-isolation tests。
- deterministic `diff_preview_id` tests if an ID helper is introduced。
- caller-supplied `generated_at` tests if timestamp metadata is introduced。

后续实现验收必须继续证明：

- `formal_writeback_allowed=false`。
- `docx_export_allowed=false`。
- `zbid_writeback_allowed=false`。
- `output_write_allowed=false`。
- 不生成正式正文。
- 不触发 review/apply。
- 不触发 DOCX / JSON / Markdown 正式导出。
- 不接 ZBid 正式写回。

## 10. Migration Path

后续可能步骤如下，但 Step 109 不执行：

- Step 110 可做 diff preview contract fake schema tests。
- Step 111 可做 fake-only diff preview helper。
- Step 112 可做 fake diff preview helper stage review。
- 后续仍需 rollback plan contract。
- 后续仍需 rollback fake helper。
- 后续仍需 formal writeback guard。
- 后续仍需 review/apply isolation。
- 后续仍需 DOCX / ZBid isolation guard。

Step 110 也不得实现 diff preview helper，不得执行真实 diff，不得写回正文，不得触发 review/apply，不得进入正式生成链。即使未来出现 `draft_diff_shadow_only`、`ready_for_human_review` 或 `approved_diff_shadow_only`，也不得自动进入 formal writeback。正式写回、DOCX 导出、ZBid 写回、review/apply 必须分别单独设计、单独授权、单独验证。

## 11. Safety Conclusion

Step 109 仅完成 diff preview contract design，不代表 diff preview helper、真实 diff、rollback plan、formal writeback、DOCX 导出或 ZBid 写回已实现。

当前系统仍处于 preview-only / no-write 阶段。diff preview 仅是未来候选修改前后差异的隔离预览数据结构，不等于正式正文修改。diff preview 不得直接写回 source section，不得直接触发 review/apply，不得直接进入 DOCX / JSON / Markdown 导出，不得直接进入 ZBid 写回，也不得作为 evidence。

human approval 不得替代 diff preview。diff preview 不得替代 evidence anchor、human approval、rollback plan 或 formal writeback guard。缺少真实 evidence anchor、source hash revalidation、human approval、rollback plan 或 formal writeback guard 时，均不得进入可写回状态。`formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 当前阶段必须保持 false。
