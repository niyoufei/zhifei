# ZDoc/ZBid Preview-Only Integration Contract Design

## 1. Scope

Step 142 仅设计 ZDoc / 文档生成系统与 ZBid / 评标系统在小范围试用阶段的 preview-only integration contract，不实现接口，不调用 ZBid，不启动服务，不运行 Ollama，不进入正式写回，不触发 DOCX / ZBid / review/apply。

本文档用于明确 ZDoc 输出、ZBid 接收、评分矩阵、证据锚点、章节预览、阻断原因、审计字段、禁写边界和后续联调条件。

当前总体策略为：

- 先完成本地化部署基础闭环。
- 再完成 ZDoc 与 ZBid 的 preview-only 对接。
- 再进行小范围试用和问题修正。
- 最后再按约 50 人同时使用场景进行正式部署设计。

本文档不代表 ZDoc / ZBid 已联调，不代表已启动服务，不代表已调用 ZBid API / 数据库 / 写回接口，不代表已实现正式写回、DOCX 导出、ZBid 写回或 review/apply。本步不进入本地化部署执行，不进入 50 人团队正式部署设计。

## 2. Integration Principle

preview-only 对接原则：

- ZDoc 可提供章节预览、证据锚点状态、评分响应建议、blocked reasons 和审计 metadata。
- ZBid 只能接收 preview-only / metadata-only 数据。
- ZDoc 输出进入 ZBid 前必须保持 preview-only / metadata-only。
- ZBid 接收内容不得反向写回 ZDoc 正文。
- ZBid 不得接收未验证 evidence。
- ZBid 不得把模型建议当成评分证据。
- ZBid 不得把 preview advisory 当成评分证据。
- ZBid 不得自动写回 ZDoc。
- ZBid 不得触发正式评标写回。
- ZDoc / ZBid 双向链路均需 no-write 默认关闭。
- ZBid writeback 当前必须 blocked。
- DOCX export 当前必须 blocked。
- review/apply 当前必须 blocked。
- formal writeback 当前必须 blocked。

当前所有正式链 flags 仍应保持 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

小范围试用阶段只验证 preview-only 数据链、阻断链、审计链和错误处理链。

## 3. Upstream ZDoc Objects

未来可作为 ZDoc preview-only 输出的对象类型包括以下 metadata。本文档仅定义契约，不实现采集、接口、状态机、写回、导出或联调：

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
- review/apply isolation metadata。
- DOCX isolation metadata。
- ZBid isolation metadata。
- formal writeback dry-run metadata。

这些对象只能作为 preview-only / metadata-only 审计和阻断输入。generated advisory、shadow candidate、patch preview、diff preview、rollback plan、dry-run result 均不得作为 evidence。

## 4. ZBid Preview-Only Input Contract v0.1

以下为文本化 schema，用于后续实现参考，不是代码实现。

| Field | Required | Description |
| --- | --- | --- |
| `contract_version` | yes | 固定契约版本，例如 `0.1`。 |
| `integration_request_id` | yes | ZDoc 到 ZBid preview-only packet 的请求标识。 |
| `source_system` | yes | 来源系统，应为 ZDoc / 文档生成系统。 |
| `target_system` | yes | 目标系统，应为 ZBid / 评标系统。 |
| `project_id` | conditional | 项目或试用上下文标识。 |
| `document_id` | yes | ZDoc source document 标识。 |
| `section_id` | yes | ZDoc source section 标识。 |
| `section_title` | conditional | 章节标题，仅用于人工识别，不作为 evidence。 |
| `section_hash` | yes | source section hash。缺失、过期或 mismatch 时必须 blocked。 |
| `section_version` | yes | source section version。缺失、过期或 mismatch 时必须 blocked。 |
| `tender_file_refs` | yes | 招标文件原文、答疑澄清原文或用户上传资料原文引用。 |
| `scoring_clause_refs` | yes | 可验证评分条款引用。不得臆造评分项。 |
| `evidence_anchor_refs` | yes | 已验证 evidence anchor 引用。缺失时必须 blocked 或 requires_human_review。 |
| `evidence_anchor_status` | yes | evidence anchor 状态。missing 时不得进入 accepted 状态。 |
| `evidence_binding_status` | yes | evidence 绑定状态。generated / shadow / patch / diff / rollback / dry-run 作为 evidence 时必须 blocked。 |
| `response_mode` | yes | ZDoc response mode。`thinking_only_fallback` 不得作为最终内容。 |
| `input_risk_level` | yes | 输入风险等级。高风险且未验证时必须 blocked 或 requires_human_review。 |
| `advisory_quality_gate_status` | yes | preview advisory quality gate 结果。 |
| `preview_advisory_summary` | conditional | 模型 advisory 摘要，仅为提示，不得作为 evidence。 |
| `shadow_candidate_id` | conditional | shadow candidate 追踪字段，不得作为 evidence。 |
| `patch_id` | conditional | patch preview 追踪字段，不得作为 evidence。 |
| `diff_preview_id` | conditional | diff preview 追踪字段，不得作为 evidence。 |
| `rollback_plan_id` | conditional | rollback plan 追踪字段，不得作为 evidence。 |
| `dry_run_id` | conditional | formal writeback dry-run 追踪字段，不得作为 evidence。 |
| `zbid_preview_mode` | yes | ZBid preview mode。当前阶段不得进入 writeback 模式。 |
| `zbid_input_status` | yes | ZBid preview input 状态。 |
| `zbid_mapping_status` | yes | ZDoc section 到 ZBid 目标的映射状态。当前仅允许 placeholder / preview-only。 |
| `zbid_scoring_matrix_status` | yes | ZBid preview scoring matrix 状态。当前仅用于人工复核，不作为 evidence。 |
| `zbid_writeback_requested` | yes | 是否出现 ZBid 写回请求。当前 true 必须 blocked。 |
| `zbid_writeback_allowed` | yes | 当前阶段必须 false。 |
| `docx_export_allowed` | yes | 当前阶段必须 false。 |
| `formal_writeback_allowed` | yes | 当前阶段必须 false。 |
| `review_apply_allowed` | yes | 当前阶段必须 false。 |
| `output_write_allowed` | yes | 当前阶段必须 false。 |
| `blocked_reasons` | yes | 阻断原因。unsafe input 缺少 blocked reasons 时必须 blocked。 |
| `generated_at` | conditional | metadata 生成时间。后续实现应由调用方显式传入或固定，不得使用非确定性时间。 |

`preview_advisory_summary` 仅为提示，不得作为 evidence。`shadow_candidate_id`、`patch_id`、`diff_preview_id`、`rollback_plan_id`、`dry_run_id` 仅为追踪字段，不得作为 evidence。

ZBid preview-only input contract 不得被 export、DOCX、review/apply、actions_bridge、orchestrator、generation 或 ZBid writeback 链路直接消费为写许可。

## 5. ZBid Preview Status Enums

### `zbid_preview_mode`

- `disabled_current_stage`：当前阶段禁用真实 ZBid 对接执行。
- `metadata_only`：仅接收 metadata，不形成评分预览。
- `preview_only`：仅用于 preview-only 小范围试用，不写回。
- `future_scoring_preview`：未来可用于评分预览，不代表 evidence。
- `future_guarded_writeback`：未来 guard 保护下写回模式，当前不实现。

### `zbid_input_status`

- `not_created`：尚未创建 ZBid preview input。
- `blocked`：存在硬性 blocker。
- `accepted_metadata_only`：仅 metadata 被接受，不形成写回。
- `accepted_preview_only`：preview-only 输入被接受，不形成写回。
- `rejected`：人工或系统拒绝。
- `stale_source_hash`：source section hash 过期或 mismatch。

### `zbid_mapping_status`

- `not_mapped`：尚未建立映射。
- `mapping_placeholder_only`：仅有未来映射占位。
- `mapped_preview_only`：仅 preview-only 映射成功，不代表写回目标可用。
- `mapping_blocked`：映射阻断。

### `zbid_scoring_matrix_status`

- `not_created`：尚未创建评分矩阵预览。
- `preview_only`：仅评分矩阵预览，不代表 evidence。
- `blocked`：评分矩阵预览被阻断。
- `requires_human_review`：需要人工复核评分条款或 evidence anchor。

当前阶段只设计状态，不实现状态机，不调用 ZBid。

## 6. Evidence and Scoring Boundary

evidence 与 scoring 边界必须满足以下约束：

1. 招标文件原文、评分办法原文、答疑澄清原文、用户上传资料原文可作为 evidence 来源。
2. ZBid 仅可读取用户提供证据、招标文件原文、评分办法原文、答疑澄清原文、已验证 evidence anchor。
3. 模型生成建议不得作为 evidence。
4. ZDoc advisory 不得作为 evidence。
5. preview advisory 不得作为 evidence。
6. ZBid preview scoring 不得作为 evidence。
7. ZBid 评分矩阵不得作为 evidence。
8. ZBid 评分建议不得作为 evidence。
9. shadow candidate 不得作为 evidence。
10. patch preview 不得作为 evidence。
11. diff preview 不得作为 evidence。
12. rollback plan 不得作为 evidence。
13. dry-run result 不得作为 evidence。
14. generated advisory 不得作为 evidence。
15. 缺少 evidence anchor 时，ZBid preview input 必须 blocked 或 requires_human_review。
16. `scoring_clause_refs` 必须指向可验证评分条款，不得臆造评分项。

ZBid preview scoring matrix 只能用于人工复核评分响应建议，不得反向写入 ZDoc 正文，不得触发 ZBid 写回，不得开放 DOCX 导出、review/apply 或 formal writeback。

## 7. Blocked Scenarios

以下场景必须 blocked：

- no evidence anchor。
- no scoring clause refs。
- generated advisory used as evidence。
- preview advisory used as evidence。
- model advisory used as evidence。
- ZBid scoring matrix used as evidence。
- ZBid scoring suggestion used as evidence。
- shadow candidate used as evidence。
- patch preview used as evidence。
- diff preview used as evidence。
- rollback plan used as evidence。
- dry-run result used as evidence。
- source hash mismatch。
- stale section version。
- high input risk without validation。
- `thinking_only_fallback` treated as final content。
- `zbid_writeback_requested=true`。
- `docx_export_requested=true`。
- `review_apply_requested=true`。
- `formal_writeback_requested=true`。
- `output/job/export` write requested。
- missing `blocked_reasons` on unsafe input。
- missing `section_hash`。
- missing `section_version`。
- missing `tender_file_refs`。
- missing `evidence_binding_status`。
- missing `zbid_preview_mode`。
- ZBid input attempts to call API / DB / writeback interface。

Blocked 状态不得被 human approval、dry-run passed、source hash matched、ZBid isolation、DOCX isolation 或 review/apply isolation 自动解除。

## 8. Preview-Only Integration Flow

以下为后续设计参考的文字流程，不是代码实现，也不是联调执行步骤：

1. ZDoc 接收项目资料。
2. ZDoc 生成 preview-only advisory。
3. quality gate / input risk / evidence anchor / response mode 执行 metadata 校验。
4. shadow candidate / patch / diff / rollback / approval / dry-run 只保留 metadata。
5. ZDoc 构造 metadata-only preview packet。
6. ZBid 接收 metadata-only preview packet。
7. ZBid 形成 preview scoring matrix draft。
8. 人工检查评分条款和 evidence anchor。
9. 所有写回、导出、review/apply 保持 blocked。
10. 试用人员记录问题。
11. 返回 ZDoc / ZBid 优化清单。

该流程只验证 preview-only 数据链、阻断链、审计链和错误处理链，不验证正式写回能力，不验证高并发，不进入 50 人正式部署设计。

## 9. Audit Fields

preview-only integration 必须可审计字段：

- `integration_request_id`
- `project_id`
- `document_id`
- `section_id`
- `section_hash`
- `section_version`
- `tender_file_refs`
- `scoring_clause_refs`
- `evidence_anchor_refs`
- `evidence_anchor_status`
- `evidence_binding_status`
- `response_mode`
- `input_risk_level`
- `advisory_quality_gate_status`
- `preview_advisory_summary`
- `shadow_candidate_id`
- `patch_id`
- `diff_preview_id`
- `rollback_plan_id`
- `dry_run_id`
- `zbid_preview_mode`
- `zbid_input_status`
- `zbid_mapping_status`
- `zbid_scoring_matrix_status`
- `zbid_writeback_requested`
- `blocked_reasons`
- `formal_writeback_allowed`
- `review_apply_allowed`
- `docx_export_allowed`
- `zbid_writeback_allowed`
- `output_write_allowed`
- `generated_at`

审计字段仅用于 preview-only 试用复核，不代表持久化、接口或正式审计系统已实现。

## 10. Trial Acceptance Criteria

本地小范围试用前，ZDoc / ZBid preview-only 对接的设计验收标准为：

- ZDoc 可提供 preview-only packet 设计。
- ZBid 可接收 metadata-only packet 设计。
- evidence 与 advisory 边界清楚。
- scoring clause refs 不得臆造。
- ZBid 评分矩阵和评分建议不得作为 evidence。
- `zbid_writeback_allowed=false`。
- `docx_export_allowed=false`。
- `review_apply_allowed=false`。
- `formal_writeback_allowed=false`。
- `output_write_allowed=false`。
- blocked 场景完整。
- audit 字段完整。
- ZBid 接收内容不得反向写回 ZDoc 正文。
- DOCX / ZBid / review/apply / formal writeback 均默认 blocked。
- 不进入本地化部署执行。
- 不进入 50 人正式部署。

达到上述标准仅代表 preview-only integration contract design 可进入后续 fake schema tests，不代表可以启动真实联调或开放写回。

## 11. Future Implementation Acceptance Criteria

后续实现验收条件包括但不限于：

- deterministic fake schema tests。
- ZDoc preview packet fake helper。
- ZBid preview input fake validator。
- evidence anchor missing block tests。
- generated advisory as evidence block tests。
- preview advisory as evidence block tests。
- scoring clause missing block tests。
- ZBid scoring matrix as evidence block tests。
- zbid writeback request block tests。
- DOCX / export / review apply block tests。
- formal writeback request block tests。
- no `output/job/export` filesystem write tests。
- import-isolation tests。
- local trial smoke checklist。
- small-team trial feedback log design。

这些验收条件仍应保持 fake-only / preview-only / no-write，直到后续任务明确允许真实接口、服务启动或联调执行。

## 12. Migration Path

建议后续步骤：

- Step 143 可做 ZDoc / ZBid preview-only integration contract fake schema tests。
- Step 144 可做 fake-only ZDoc / ZBid preview packet helper。
- Step 145 可做 fake-only ZBid preview input validator。
- Step 146 可做 local trial smoke checklist design。
- 后续再进入本地部署执行与小范围试用。
- 最后再按约 50 人同时使用场景做正式部署方案。

Step 143 不得实现接口，不得调用 ZBid，不得启动服务，不得进入正式写回，不得触发 DOCX / ZBid / review/apply，不得写 `output/job/export`，不得进入 50 人正式部署设计。

## 13. Safety Conclusion

Step 142 仅完成 ZDoc / ZBid preview-only integration contract design，不代表 ZDoc / ZBid 已联调，不代表 ZBid 写回、DOCX 导出、review/apply、正式写回或 50 人团队部署已实现。

当前阶段仍必须保持 preview-only / metadata-only / no-write。ZDoc 输出进入 ZBid 前必须保持 preview-only / metadata-only；ZBid 接收内容不得反向写回 ZDoc 正文；所有正式链 flags 仍应保持 false。
