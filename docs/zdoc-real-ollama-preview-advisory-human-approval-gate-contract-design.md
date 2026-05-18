# ZDoc Real Ollama Preview Advisory - Human Approval Gate Contract Design

## 1. Scope

Step 105 仅定义未来 human approval gate 的数据契约，不实现 human approval UI，不实现审批持久化，不执行正式写回。系统仍处于 preview-only / no-write 阶段。

human approval gate 只负责定义未来审批状态、审批边界、审计字段和写回前置条件。它不得替代 evidence anchor、diff preview、rollback plan、source hash revalidation 或 formal writeback guard，也不得直接触发 review/apply、DOCX 导出、ZBid 写回或任何正式正文生成链路。

本文档仅为后续 fake schema tests 和 fake-only approval gate helper 提供 contract design，不代表 human approval UI、审批持久化、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

## 2. Non-goals

本步明确不做以下事项：

- 不实现 human approval UI。
- 不实现审批持久化。
- 不实现审批按钮。
- 不实现 review/apply。
- 不执行正式写回。
- 不生成 DOCX / JSON / Markdown。
- 不写 `output/job/export`。
- 不接 ZBid 写回。
- 不实现 diff / rollback。
- 不实现 formal writeback guard。
- 不实现 DOCX / ZBid isolation guard。
- 不把 approval 当 evidence。
- 不把 approval 当 formal writeback permission。
- 不把 advisory、shadow candidate envelope、shadow candidate patch 或 patch preview 转化为 evidence。
- 不修改代码、tests、既有 docs、frontend、配置文件或 CI 文件。
- 不运行 pytest。
- 不启动服务。
- 不运行 Ollama 或 `ollama serve`。
- 不访问 `127.0.0.1:11434`。
- 不调用外部模型或 API。

approval contract 不得被 review/apply、export、DOCX 或 ZBid 链路直接消费。approval contract 只能作为未来正式写回前的一项必要但不充分的 metadata。

## 3. Upstream Prerequisites

未来 human approval gate 至少依赖以下上游信息。本步只定义依赖关系，不实现采集、校验、UI、状态机、持久化或写回：

- preview advisory quality gate result。
- input risk snapshot。
- evidence anchor validation result。
- response mode classification。
- shadow generation readiness metadata。
- shadow candidate envelope metadata。
- shadow candidate patch metadata。
- source section hash。
- source section version。
- diff preview placeholder。
- rollback plan placeholder。
- formal writeback guard placeholder。

human approval 不得替代任何上游 guard。即使审批通过，只要 evidence、response-mode、quality gate、readiness、shadow candidate、patch、diff、rollback、source hash 或 formal writeback guard 任一前置条件缺失，仍不得写回。

## 4. HumanApprovalGateContract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `approval_id` | conditional | 未来审批记录 ID。不得使用非确定性随机值；如生成，应基于输入确定性生成或由调用方显式传入。 |
| `request_id` | yes | 关联 preview / envelope / patch / approval 请求的唯一标识。 |
| `source_document_id` | yes | 来源文档标识。不得指向模型生成 advisory 作为 source evidence。 |
| `source_section_id` | yes | 来源章节标识。approval 不得直接覆盖该章节。 |
| `source_section_hash` | yes | 来源章节 hash。缺失或未重新校验时不得写回。 |
| `source_section_version` | yes | 来源章节版本，用于 diff / rollback / writeback 前置校验。 |
| `shadow_candidate_id` | yes | 关联 shadow candidate envelope。缺失时不得审批为可写回。 |
| `patch_id` | yes | 关联 shadow candidate patch。缺失时不得审批为可写回。 |
| `approval_status` | yes | 审批生命周期状态。当前只定义，不实现状态机。 |
| `approval_scope` | yes | 审批范围，例如 shadow_candidate_only、patch_preview_only、single_section_candidate。 |
| `approval_decision` | yes | 审批决策，例如 approve_shadow_only、reject、request_revision。 |
| `approval_mode` | yes | 审批模式，例如 manual_required、manual_received、disabled_current_stage。 |
| `approver_role` | conditional | 未来审批角色元数据，例如 reviewer、owner、operator。不得替代真实权限系统。 |
| `approver_id_placeholder` | conditional | 未来审批人占位字段。当前不得记录真实个人信息。 |
| `approved_at` | conditional | 未来审批时间字段。当前只能作为字段描述，不得使用当前时间生成。 |
| `approval_reason` | conditional | 审批原因摘要。不得作为 evidence source。 |
| `approval_comment` | conditional | 审批备注。不得作为 evidence source。 |
| `approval_expires_at` | conditional | 未来审批过期时间字段。当前只能作为字段描述，不得使用当前时间生成。 |
| `approval_audit_required` | yes | 是否要求审批审计字段。正式写回前必须满足。 |
| `approval_audit_ready` | yes | 审批审计字段是否完备。false 时不得写回。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 时不得写回。 |
| `evidence_anchor_refs` | yes | 真实 evidence anchor 引用列表。不得包含 advisory、envelope、patch 或 patch preview。 |
| `evidence_binding_status` | yes | evidence 绑定状态。generated / shadow-only / patch-only 均 blocked。 |
| `response_mode` | yes | 上游 response-mode。thinking_only_fallback 不得审批为可写回。 |
| `input_risk_level` | yes | 输入风险等级或状态摘要。高风险且未验证时必须 blocked。 |
| `advisory_quality_gate_status` | yes | quality gate 结果。缺失或 blocked 时不得写回。 |
| `readiness_status` | yes | shadow readiness 结果。blocked 或缺失时不得写回。 |
| `shadow_candidate_status` | yes | shadow candidate 状态。blocked / not_created 时不得写回。 |
| `patch_status` | yes | shadow candidate patch 状态。blocked / not_created 时不得写回。 |
| `diff_preview_required` | yes | 是否要求 diff preview。正式写回前必须为 true 并 ready。 |
| `diff_preview_ready` | yes | diff preview 是否 ready。false 时不得写回。 |
| `rollback_required` | yes | 是否要求 rollback plan。正式写回前必须为 true 并 ready。 |
| `rollback_plan_ready` | yes | rollback plan 是否 ready。false 时不得写回。 |
| `source_hash_revalidation_required` | yes | 是否要求写回前重新校验 source section hash。 |
| `source_hash_revalidation_ready` | yes | source hash revalidation 是否 ready。false 时不得写回。 |
| `formal_writeback_guard_required` | yes | 是否要求 formal writeback guard。 |
| `formal_writeback_guard_ready` | yes | formal writeback guard 是否 ready。false 时不得写回。 |
| `formal_writeback_allowed` | yes | 当前阶段必须为 false。approval_status 不得直接改变该字段。 |
| `docx_export_allowed` | yes | 当前阶段必须为 false。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须为 false。 |
| `output_write_allowed` | yes | 当前阶段必须为 false。 |
| `blocked_reasons` | yes | blocked / not_requested / pending 状态的原因列表。 |

`approved_at` 和 `approval_expires_at` 当前只能作为未来字段描述，不得使用当前时间生成。`approver_id_placeholder` 不得记录真实个人信息。`approval_status` 不能直接代表 `formal_writeback_allowed=true`。

## 5. Status Enums

### `approval_status`

- `not_requested`：尚未请求人工审批。
- `blocked`：存在硬性 blocker，不允许审批为可写回。
- `pending_human_review`：等待人工审查。
- `approved_shadow_only`：人工仅批准 shadow-only 候选或 patch 预览，不等于正式写回。
- `rejected`：人工拒绝，不得写回。
- `expired`：审批过期，不得写回。
- `revoked`：审批撤销，不得写回。

### `approval_decision`

- `none`：无审批决策。
- `approve_shadow_only`：仅批准 shadow-only 候选或 patch 预览。
- `reject`：拒绝。
- `request_revision`：要求修订。
- `revoke`：撤销既有审批。

### `approval_scope`

- `shadow_candidate_only`：仅覆盖 shadow candidate envelope。
- `patch_preview_only`：仅覆盖 shadow candidate patch preview。
- `single_section_candidate`：仅覆盖单章节候选。
- `metadata_only`：仅覆盖 metadata 审核。

### `approval_mode`

- `manual_required`：需要人工审批。
- `manual_received`：已收到人工审批 metadata。
- `disabled_current_stage`：当前阶段禁用审批执行。

当前阶段只设计状态，不实现状态机，不实现 UI，不实现审批持久化。任何状态都不改变当前 preview-only / no-write 边界。

## 6. Hard Invariants

以下为强约束，后续实现不得放松：

1. `approval_status=approved_shadow_only` 不等于 `formal_writeback_allowed=true`。
2. human approval 不得替代 evidence anchor。
3. human approval 不得替代 source hash revalidation。
4. human approval 不得替代 diff preview。
5. human approval 不得替代 rollback plan。
6. human approval 不得替代 formal writeback guard。
7. `evidence_anchor_status=missing` 时，即使 `approval_status=approved_shadow_only`，`formal_writeback_allowed` 也必须为 false。
8. `evidence_binding_status=generated_advisory_only_blocked` 时，不得进入可写回状态。
9. `evidence_binding_status=shadow_candidate_only_blocked` 时，不得进入可写回状态。
10. `evidence_binding_status=patch_preview_only_blocked` 时，不得进入可写回状态。
11. `response_mode=thinking_only_fallback` 时，不得审批为可写回。
12. `shadow_candidate_status=blocked` 或 `not_created` 时，不得审批为可写回。
13. `patch_status=blocked` 或 `not_created` 时，不得审批为可写回。
14. `diff_preview_ready=false` 时，不得写回。
15. `rollback_plan_ready=false` 时，不得写回。
16. `source_hash_revalidation_ready=false` 时，不得写回。
17. `formal_writeback_guard_ready=false` 时，不得写回。
18. `approval_audit_ready=false` 时，不得写回。
19. `docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 当前阶段必须恒 false。
20. approval contract 不得被 review/apply、export、DOCX、ZBid 直接消费。
21. approval contract 不得把 advisory、shadow candidate envelope、shadow candidate patch 或 patch preview 变成 evidence。
22. approval contract 不得触发正式正文生成、正式写回、DOCX 导出或 ZBid 写回。

## 7. Blocked Scenarios

以下场景必须 blocked 或保持 not_requested / pending 状态：

- no shadow candidate envelope。
- no shadow candidate patch。
- shadow candidate status blocked。
- shadow candidate status not_created。
- patch status blocked。
- patch status not_created。
- thinking_only_fallback。
- unsupported response mode。
- no evidence anchor。
- advisory used as evidence。
- shadow candidate used as evidence。
- shadow candidate envelope used as evidence。
- shadow candidate patch used as evidence。
- patch preview used as evidence。
- missing source section hash。
- source section hash mismatch。
- missing approval audit fields。
- approval expired。
- approval revoked。
- approval rejected。
- missing diff preview。
- missing rollback plan。
- missing source hash revalidation。
- missing formal writeback guard。
- DOCX export request。
- ZBid writeback request。
- output / job / export write request。
- formal generation request。
- review/apply request。

这些 blocked scenarios 不得通过 human approval 绕过。approval 只能作为 future writeback 的必要前置条件之一，不是充分条件。

## 8. Approval Audit Requirements

未来审批审计至少需要以下字段：

- `approval_id`
- `request_id`
- `source_document_id`
- `source_section_id`
- `source_section_hash`
- `source_section_version`
- `shadow_candidate_id`
- `patch_id`
- `approval_status`
- `approval_decision`
- `approval_scope`
- `approval_mode`
- `approver_role`
- `approved_at`
- `approval_reason`
- `approval_comment`
- `blocked_reasons`

当前阶段不得记录真实用户身份信息，不实现审批持久化，不写文件，不写 `output/job/export`。审批审计字段只能作为 future metadata contract，不代表已存在 UI、数据库、文件日志或 review/apply 集成。

## 9. Future Implementation Acceptance Criteria

后续如进入实现，至少需要满足以下验收条件。本步不实现、不运行测试：

- deterministic fake schema tests。
- approval status enum tests。
- missing approval block tests。
- approval cannot replace evidence tests。
- approval cannot replace diff tests。
- approval cannot replace rollback tests。
- approval cannot replace source hash revalidation tests。
- approval cannot replace formal writeback guard tests。
- expired approval block tests。
- revoked approval block tests。
- rejected approval block tests。
- missing approval audit fields block tests。
- DOCX / ZBid / export / review apply block tests。
- formal flags false tests。
- no output / job / export filesystem write tests。
- import-isolation tests。
- current timestamp / random ID avoidance tests。
- approval contract not consumed by review/apply / export / ZBid tests。

后续实现验收必须继续证明：

- `formal_writeback_allowed=false`。
- `docx_export_allowed=false`。
- `zbid_writeback_allowed=false`。
- `output_write_allowed=false`。
- approval 不替代 evidence。
- approval 不替代 diff / rollback。
- approval 不替代 formal writeback guard。
- approval 不触发正式写回。

## 10. Migration Path

后续可能步骤如下，但 Step 105 不执行：

- Step 106 可做 human approval gate contract fake schema tests。
- Step 107 可做 fake-only human approval gate helper。
- Step 108 可做 fake approval gate stage review。
- 后续仍需 diff preview contract。
- 后续仍需 rollback plan contract。
- 后续仍需 formal writeback guard。
- 后续仍需 DOCX / ZBid isolation guard。

即使未来出现 `approved_shadow_only`，也不得自动进入 formal writeback。正式写回、DOCX 导出、ZBid 写回、review/apply 必须分别单独设计、单独授权、单独验证。

## 11. Safety Conclusion

Step 105 仅完成 human approval gate contract design，不代表 human approval UI、审批持久化、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

human approval gate 只定义未来审批状态与准入条件，不执行正式写回。human approval 不得替代 evidence anchor，不得替代 diff preview，不得替代 rollback plan，不得替代 source hash revalidation，不得替代 formal writeback guard。

未获得 human approval 时，`formal_writeback_allowed` 必须为 false。即使获得 human approval，只要 evidence、diff、rollback、source hash、formal writeback guard 任一前置条件缺失，也不得写回。

当前阶段 `formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须保持 false。approval contract 不得直接被 review/apply、export、DOCX 或 ZBid 消费，不得把 advisory、shadow candidate envelope、shadow candidate patch 或 patch preview 变成 evidence。
