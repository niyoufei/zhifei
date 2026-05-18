# ZDoc Real Ollama Preview Advisory - Shadow Candidate Data Contract Design

## 1. Scope

Step 97 仅定义未来 shadow candidate 的数据契约，不实现 shadow candidate 生成，不生成 candidate patch，不写正式正文。本文档为 docs-only data contract design，仍处于 preview-only / no-write 阶段。

shadow candidate 仅是未来候选正文的隔离数据结构，用于承载模型建议、证据锚点、质量门禁、人审、diff 和 rollback 等元数据。shadow candidate 不等于正式正文，不得直接覆盖章节正文，不得直接进入 DOCX / JSON / Markdown 导出，不得直接进入 ZBid 写回，也不得被当作 evidence source。

当前阶段所有 formal / write / export / zbid / docx 相关准入字段必须保持 false。本文档仅为后续实现提供数据契约，不代表任何实现已经完成。

## 2. Non-goals

本步明确不做以下事项：

- 不实现 shadow generation。
- 不生成 candidate patch。
- 不接正式生成链。
- 不写 output / job / export。
- 不接 DOCX 导出。
- 不接 ZBid 写回。
- 不实现 human approval UI。
- 不实现 diff / rollback 执行。
- 不把 advisory 当 evidence。
- 不修改 backend / frontend / tests。
- 不运行 pytest。
- 不启动服务。
- 不运行 Ollama 或 ollama serve。
- 不访问 127.0.0.1:11434。
- 不调用外部模型或 API。

## 3. Upstream Prerequisites

未来 shadow candidate 必须依赖下列上游信息。本步只定义依赖关系，不实现采集、校验或状态机：

- preview advisory quality gate result：用于判断 advisory 是否被 blocked、review_required 或 preview_ok。
- input risk snapshot：用于记录 direct write、DOCX export、ZBid writeback、unsupported project fact 等输入风险。
- evidence anchor validation result：用于区分 missing、invalid_anchor、conflicting、source_verified 等 evidence 状态。
- response mode classification：用于区分 preview_advisory、thinking_only_fallback、unsupported、blocked 等输出模式。
- shadow generation readiness metadata：用于承接 Step 95 的 readiness guard 结果。
- human approval placeholder：用于表达 future approval required / received 状态，不代表本步已有人审流程。
- diff / rollback requirement placeholder：用于表达写回前必须存在 diff 与 rollback，但本步不执行 diff 或 rollback。

缺少真实 evidence anchor 时，candidate 不得进入可审查状态。thinking_only_fallback 不得生成 shadow candidate。model-generated advisory 不得作为 evidence。

## 4. ShadowCandidateContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `request_id` | yes | 关联 preview / readiness 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向生成内容作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。shadow candidate 不得覆盖该章节。 |
| `source_section_hash` | yes | 来源章节内容 hash，用于 diff / rollback 前置校验。 |
| `response_mode` | yes | 上游 response-mode 分类。`thinking_only_fallback` 不得生成 shadow candidate。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing / generated_advisory_only_blocked 不得进入 review-ready。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表。不得包含 model-generated advisory 作为 evidence。 |
| `advisory_quality_gate_status` | yes | advisory quality gate 结果。缺失时必须 blocked。 |
| `readiness_status` | yes | shadow readiness 结果。当前仅来自 fake-only metadata。 |
| `shadow_candidate_status` | yes | shadow candidate 生命周期状态。当前默认 `not_created` 或 `blocked`。 |
| `shadow_candidate_id` | conditional | 未来隔离候选 ID。本步不生成。 |
| `candidate_kind` | conditional | 未来候选类型，例如 advisory_rewrite、section_patch_preview、risk_note。 |
| `candidate_scope` | conditional | 未来候选范围，例如 section、paragraph、sentence。 |
| `candidate_text_preview` | conditional | 未来隔离预览文本字段。本步不得宣称已生成该内容。 |
| `candidate_patch_preview` | conditional | 未来隔离 patch 预览字段。本步不得宣称已生成该内容。 |
| `model_provider` | conditional | 模型提供方元数据，仅用于审计。 |
| `model_name` | conditional | 模型名称元数据，仅用于审计。 |
| `generated_at` | conditional | 未来候选生成时间。本步不生成候选。 |
| `human_approval_required` | yes | 是否需要人工确认。未来写回前必须为 true。 |
| `human_approval_received` | yes | 是否已收到人工确认。false 时不得写回。 |
| `diff_required` | yes | 是否要求 diff。写回前必须满足。 |
| `rollback_required` | yes | 是否要求 rollback。写回前必须满足。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked 或 not_created 的原因列表。 |

`candidate_text_preview` 和 `candidate_patch_preview` 只能作为未来隔离预览字段描述，不代表 Step 97 已生成候选文本或候选 patch。这两个字段不得被 orchestrator、export、review/apply、DOCX 导出或 ZBid 写回直接消费。

## 5. Status Enums

### `shadow_candidate_status`

- `not_created`：尚未创建 shadow candidate。当前阶段默认状态之一。
- `blocked`：存在硬性 blocker，不允许进入候选。
- `draft_shadow_only`：未来仅 shadow 隔离草稿状态，不等于正式正文。
- `ready_for_human_review`：未来可供人工审查的隔离候选状态，必须具备真实 evidence anchor。
- `approved_shadow_only`：未来人工确认后的 shadow-only 状态，仍不等于正式写回。
- `rejected`：人工拒绝或系统拒绝状态，不得写回。

### `evidence_anchor_status`

- `missing`：缺少 evidence anchor，不得进入可审查状态。
- `user_provided`：用户提供的 evidence 引用，仍需校验。
- `source_verified`：来源 evidence 已通过校验。
- `generated_advisory_only_blocked`：仅有模型生成 advisory，被明确禁止作为 evidence。

### `response_mode`

- `preview_advisory`：仅表示 preview advisory，不等于 shadow readiness。
- `thinking_only_fallback`：thinking fallback 输出，必须 blocked 或 not_created。
- `unsupported`：不支持或无法归类。
- `blocked`：已被上游 guard 阻断。

### `readiness_status`

- `blocked`：readiness guard blocked。
- `fake_ready_metadata_only`：仅 fake-only metadata 层面满足部分前置条件，不等于可生成候选。
- `future_ready_for_shadow_candidate`：未来预留状态，本阶段不启用。

当前阶段只能设计这些状态，不实现状态机。任何状态设计都不改变当前 formal flags false 的边界。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `response_mode=thinking_only_fallback` 时，`shadow_candidate_status` 必须为 `blocked` 或 `not_created`。
2. `evidence_anchor_status=generated_advisory_only_blocked` 时，不得进入 `ready_for_human_review`。
3. `human_approval_received=false` 时，`formal_writeback_allowed` 必须为 false。
4. `diff_required=true` 且 `rollback_required=true` 是写回前置要求，但本阶段不执行 diff 或 rollback。
5. `docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 在当前阶段必须为 false。
6. shadow candidate 不得覆盖 source section。
7. shadow candidate 不得被 orchestrator、export、review/apply 直接消费。
8. shadow candidate 不得作为 evidence source。
9. shadow candidate 不得直接写回章节正文。
10. shadow candidate 不得直接进入 DOCX / JSON / Markdown 导出。
11. shadow candidate 不得直接进入 ZBid 写回。
12. 缺少 diff / rollback 记录时，不得写回。

## 7. Blocked Scenarios

以下场景必须 blocked 或保持 `not_created`：

- no evidence anchor。
- advisory used as evidence。
- `thinking_only_fallback`。
- high input risk without validation。
- missing quality gate result。
- missing readiness metadata。
- missing human approval。
- missing diff preview。
- missing rollback plan。
- DOCX export request。
- ZBid writeback request。
- output / job / export write request。
- formal generation request。
- generated advisory only evidence。
- source section hash mismatch。
- candidate text attempts to overwrite source section directly。
- orchestrator / export / review/apply attempts to consume shadow candidate directly。

## 8. Future Implementation Acceptance Criteria

后续如进入实现，至少需要满足以下验收条件。本步不实现、不运行测试：

- deterministic fake tests 覆盖 contract schema。
- no-write tests 证明不写 output / job / export。
- `thinking_only_fallback` block tests。
- generated-advisory-as-evidence block tests。
- DOCX / ZBid / export block tests。
- formal flags false tests。
- diff / rollback required tests。
- human approval missing block tests。
- missing evidence anchor block tests。
- quality gate missing / blocked tests。
- input-risk blocked tests。
- readiness metadata missing tests。
- source section hash mismatch tests。
- direct orchestrator / export / review/apply consumption blocked tests。

后续实现验收必须继续证明：

- `formal_writeback_allowed=false`。
- `docx_export_allowed=false`。
- `zbid_writeback_allowed=false`。
- `output_write_allowed=false`。
- 不生成正式正文。
- 不触发 DOCX / JSON / Markdown 正式导出。
- 不接 ZBid 正式写回。

## 9. Migration Path

后续可能步骤如下，但 Step 97 不执行：

- Step 98 可做 shadow candidate contract fake schema tests，验证字段、枚举、blocked 场景和 flags false。
- Step 99 可做 fake-only shadow candidate envelope helper，只返回隔离 envelope metadata，不生成正式正文，不写 output / job / export。
- Step 100 后仍不得进入正式写回，必须另设 human approval、diff / rollback、formal writeback 隔离步骤。

即使未来出现 `draft_shadow_only`、`ready_for_human_review` 或 `approved_shadow_only`，也不得自动进入正式链。formal writeback、DOCX export、ZBid writeback 必须分别单独设计、单独授权、单独验证。

## 10. Safety Conclusion

Step 97 仅完成数据契约设计，不代表 shadow generation、candidate patch、human approval、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

当前阶段仍保持 preview-only / no-write。shadow candidate 只是未来候选正文的隔离数据结构，不等于正式正文，不得直接写回章节正文，不得直接进入 DOCX / JSON / Markdown 导出，不得直接进入 ZBid 写回。

`thinking_only_fallback` 不得生成 shadow candidate。model-generated advisory 不得作为 evidence。缺少真实 evidence anchor、human approval、diff 或 rollback 记录时，均不得写回。formal / write / export / zbid / docx 相关 flags 在当前阶段必须保持 false。
