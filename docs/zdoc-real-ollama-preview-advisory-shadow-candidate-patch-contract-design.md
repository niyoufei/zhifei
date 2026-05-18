# ZDoc Real Ollama Preview Advisory - Shadow Candidate Patch Contract Design

## 1. Scope

Step 101 仅定义未来 shadow candidate patch 的数据契约，不实现 candidate patch，不生成正文修改内容，不进入 candidate patch implementation。系统仍处于 preview-only / no-write 阶段。

shadow candidate patch 仅是未来候选修改的隔离数据结构，用于描述候选修改范围、patch 预览、证据锚点绑定、human approval 前置条件、diff preview 前置条件和 rollback plan 前置条件。shadow candidate patch 不等于正式正文修改，不得直接写回 source section，不得直接进入 DOCX / JSON / Markdown 导出，不得直接进入 ZBid 写回。

本文档仅为后续 fake schema tests 和 fake-only patch helper 提供数据契约，不代表任何实现已经完成。

## 2. Non-goals

本步明确排除以下事项：

- 不实现真实 candidate patch。
- 不生成正文修改内容。
- 不接正式生成链。
- 不调用模型。
- 不调用 Ollama。
- 不调用外部模型或 API。
- 不启动服务。
- 不写 source section。
- 不写 output / job / export。
- 不接 DOCX 导出。
- 不接 JSON / Markdown 正式导出。
- 不接 ZBid 写回。
- 不实现 human approval UI。
- 不执行 diff / rollback。
- 不触发 review/apply。
- 不触发 /generate。
- 不触发 /export_docx。
- 不触发 /review/apply。
- 不把 advisory 当 evidence。
- 不把 shadow envelope 当 evidence。
- 不把 patch 当 evidence。
- 不把 patch preview 当 evidence。
- 不修改生产代码、测试或既有 docs。

patch contract 不得被 orchestrator、export、review/apply 或 ZBid 链路直接消费。

## 3. Upstream Prerequisites

未来 shadow candidate patch 至少依赖以下上游信息。本步只定义依赖，不实现采集、校验、状态机或写回：

- preview advisory quality gate result。
- input risk snapshot。
- evidence anchor validation result。
- response mode classification。
- shadow generation readiness metadata。
- shadow candidate envelope metadata。
- shadow candidate status。
- source section hash。
- source section version。
- human approval placeholder。
- diff preview placeholder。
- rollback plan placeholder。

缺少真实 evidence anchor 时，不得允许 patch 进入可审查状态。thinking_only_fallback 不得生成 patch。model-generated advisory、shadow candidate envelope 和 shadow candidate patch 均不得作为 evidence。

## 4. ShadowCandidatePatchContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `patch_id` | conditional | 未来隔离 patch ID。不得使用随机值；如生成，应基于输入确定性生成。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope 的 ID。不得把 envelope 当 evidence。 |
| `request_id` | yes | 关联 preview / envelope / patch 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。patch preview 不得覆盖该章节。 |
| `source_section_hash` | yes | 来源章节 hash。缺失或不匹配时不得写回。 |
| `source_section_version` | yes | 来源章节版本，用于 diff / rollback 前置校验。 |
| `patch_status` | yes | patch 生命周期状态。当前默认 `not_created` 或 `blocked`。 |
| `patch_kind` | yes | patch 类型，例如 section_rewrite、paragraph_rewrite、metadata_only。 |
| `patch_scope` | yes | patch 范围，例如 section、paragraph、anchor_range。 |
| `patch_format` | yes | patch 表达格式，例如 text_preview、structured_patch_preview、metadata_only。 |
| `patch_operation_type` | yes | patch 操作类型，例如 no_op、replace、insert、delete、reorder、mixed。 |
| `patch_operations_preview` | conditional | 未来隔离 patch 操作预览字段。本步不得宣称已生成 patch 内容。 |
| `before_text_hash` | yes | 修改前文本 hash，用于 diff 和 rollback。 |
| `after_text_preview` | conditional | 未来隔离修改后文本预览。本步不得宣称已生成正文修改内容。 |
| `affected_anchor_refs` | yes | patch 影响的锚点列表。不得包含生成内容作为 evidence。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 不得进入可审查状态。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表。不得包含 advisory / envelope / patch preview。 |
| `evidence_binding_status` | yes | patch 与 evidence 的绑定状态。generated / shadow-only / patch-only 均 blocked。 |
| `response_mode` | yes | 上游 response-mode 分类。thinking_only_fallback 不得生成 patch。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `advisory_quality_gate_status` | yes | advisory quality gate 结果。缺失时必须 blocked。 |
| `readiness_status` | yes | shadow readiness 结果。缺失或 blocked 时不得生成 patch。 |
| `shadow_candidate_status` | yes | 上游 shadow candidate 状态。blocked / not_created 时不得生成可审查 patch。 |
| `generated_at` | conditional | 未来 patch 生成时间。应由调用方显式传入，不得使用非确定性时间。 |
| `model_provider` | conditional | 模型提供方元数据，仅用于审计。 |
| `model_name` | conditional | 模型名称元数据，仅用于审计。 |
| `human_approval_required` | yes | 是否需要人工确认。写回前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得写回。 |
| `diff_preview_required` | yes | 是否要求 diff preview。写回前必须满足。 |
| `diff_preview_ready` | yes | diff preview 是否已准备。false 时不得写回。 |
| `rollback_required` | yes | 是否要求 rollback plan。写回前必须满足。 |
| `rollback_plan_ready` | yes | rollback plan 是否已准备。false 时不得写回。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked 或 not_created 的原因列表。 |

`patch_operations_preview` 和 `after_text_preview` 只能作为未来隔离预览字段描述，不代表 Step 101 已生成 patch 内容、正文修改内容或 candidate patch。它们不得被 review/apply、export、ZBid、DOCX 导出或正式生成链直接消费。

## 5. Status Enums

### `patch_status`

- `not_created`：尚未创建 shadow candidate patch。当前阶段默认状态之一。
- `blocked`：存在硬性 blocker，不允许进入 patch。
- `draft_patch_shadow_only`：未来仅 shadow 隔离草稿 patch，不等于正式正文修改。
- `ready_for_human_review`：未来可供人工审查的隔离 patch 状态，必须具备真实 evidence anchor、diff preview 和 rollback plan。
- `approved_patch_shadow_only`：未来人工确认后的 shadow-only patch 状态，仍不等于正式写回。
- `rejected`：人工拒绝或系统拒绝状态，不得写回。

### `patch_kind`

- `section_rewrite`：章节级重写候选。
- `paragraph_rewrite`：段落级重写候选。
- `insert_after_anchor`：锚点后插入候选。
- `replace_anchor_range`：替换锚点范围候选。
- `delete_anchor_range`：删除锚点范围候选。
- `metadata_only`：仅元数据候选，不含正文变更。

### `patch_operation_type`

- `no_op`：无正文操作。
- `replace`：替换。
- `insert`：插入。
- `delete`：删除。
- `reorder`：重排。
- `mixed`：混合操作。

### `patch_format`

- `text_preview`：文本预览。
- `structured_patch_preview`：结构化 patch 预览。
- `metadata_only`：仅元数据。

### `evidence_binding_status`

- `missing`：缺少 evidence 绑定。
- `bound_to_user_provided_evidence`：绑定到用户提供 evidence，仍需校验。
- `bound_to_source_verified_evidence`：绑定到已验证 source evidence。
- `generated_advisory_only_blocked`：仅绑定模型生成 advisory，必须 blocked。
- `shadow_candidate_only_blocked`：仅绑定 shadow candidate / envelope，必须 blocked。
- `patch_preview_only_blocked`：仅绑定 patch preview，必须 blocked。

当前阶段只设计状态，不实现状态机。任何状态设计都不改变当前 preview-only / no-write 边界。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `response_mode=thinking_only_fallback` 时，`patch_status` 必须为 `blocked` 或 `not_created`。
2. `evidence_anchor_status=missing` 时，不得进入 `ready_for_human_review`。
3. `evidence_binding_status=generated_advisory_only_blocked` 时，不得进入 `ready_for_human_review`。
4. `evidence_binding_status=shadow_candidate_only_blocked` 时，不得进入 `ready_for_human_review`。
5. `evidence_binding_status=patch_preview_only_blocked` 时，不得进入 `ready_for_human_review`。
6. `human_approval_received=false` 时，`formal_writeback_allowed` 必须为 false。
7. `diff_preview_ready=false` 时，`formal_writeback_allowed` 必须为 false。
8. `rollback_plan_ready=false` 时，`formal_writeback_allowed` 必须为 false。
9. `source_section_hash` 缺失或不匹配时，`formal_writeback_allowed` 必须为 false。
10. `docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 当前阶段必须恒 false。
11. patch preview 不得覆盖 source section。
12. patch preview 不得写 output / job / export。
13. patch preview 不得作为 evidence source。
14. patch contract 不得被 review/apply、export、ZBid 直接消费。
15. patch contract 不得直接进入 DOCX / JSON / Markdown 导出。
16. patch contract 不得直接进入正式正文生成链。

## 7. Blocked Scenarios

以下场景必须 blocked 或保持 `not_created`：

- no shadow candidate envelope。
- shadow candidate status blocked。
- shadow candidate status not_created。
- thinking_only_fallback。
- unsupported response mode。
- no evidence anchor。
- advisory used as evidence。
- shadow candidate used as evidence。
- shadow candidate envelope used as evidence。
- patch preview used as evidence。
- high input risk without validation。
- missing quality gate result。
- missing readiness metadata。
- missing source section hash。
- source section hash mismatch。
- missing human approval。
- missing diff preview。
- missing rollback plan。
- DOCX export request。
- ZBid writeback request。
- output / job / export write request。
- formal generation request。
- review/apply request。
- patch contract direct consumption by export / ZBid / review pipeline。

## 8. Future Implementation Acceptance Criteria

后续如进入实现，至少需要满足以下验收条件。本步不实现、不运行测试：

- deterministic fake schema tests。
- no-write tests。
- `thinking_only_fallback` block tests。
- generated-advisory-as-evidence block tests。
- shadow-candidate-as-evidence block tests。
- shadow-envelope-as-evidence block tests。
- patch-preview-as-evidence block tests。
- missing source hash block tests。
- source hash mismatch block tests。
- missing human approval block tests。
- missing diff preview block tests。
- missing rollback plan block tests。
- DOCX / ZBid / export block tests。
- review/apply block tests。
- formal flags false tests。
- import-isolation tests。
- no output / job / export filesystem write tests。
- deterministic `patch_id` tests if an ID helper is introduced。
- caller-supplied `generated_at` tests if timestamp metadata is introduced。

后续实现验收必须继续证明：

- `formal_writeback_allowed=false`。
- `docx_export_allowed=false`。
- `zbid_writeback_allowed=false`。
- `output_write_allowed=false`。
- 不生成正式正文。
- 不触发 DOCX / JSON / Markdown 正式导出。
- 不接 ZBid 正式写回。
- 不进入 review/apply。

## 9. Migration Path

后续可能步骤如下，但 Step 101 不执行：

- Step 102 可做 shadow candidate patch contract fake schema tests。
- Step 103 可做 fake-only patch envelope helper。
- Step 104 可做 fake patch helper stage review。
- 后续仍需 human approval gate、diff preview、rollback plan、formal writeback guard、DOCX / ZBid isolation guard。

即使未来出现 `draft_patch_shadow_only`、`ready_for_human_review` 或 `approved_patch_shadow_only`，也不得自动进入正式链。formal writeback、DOCX export、ZBid writeback、review/apply 必须分别单独设计、单独授权、单独验证。

## 10. Safety Conclusion

Step 101 仅完成 shadow candidate patch contract design，不代表真实 candidate patch、human approval、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

当前系统仍处于 preview-only / no-write 阶段。shadow candidate patch 仅是未来候选修改的隔离数据结构，不等于正式正文修改。patch contract 不得直接写回 source section，不得直接进入 DOCX / JSON / Markdown 导出，不得直接进入 ZBid 写回，不得被 orchestrator、export、review/apply 或 ZBid 直接消费。

thinking_only_fallback 不得生成 patch。model-generated advisory、shadow candidate envelope 和 shadow candidate patch 均不得作为 evidence。缺少真实 evidence anchor、human approval、diff preview 或 rollback plan 时，均不得写回。formal_writeback_allowed、docx_export_allowed、zbid_writeback_allowed、output_write_allowed 在当前阶段必须保持 false。
