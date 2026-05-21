# ZDoc Local Trial Preview-Only Route Implementation Plan Design

## 1. Scope

本文档仅设计未来本地小范围试用阶段的 preview-only route 实现方案。Step 179 为 docs-only implementation plan design，不实现 route，不修改代码，不修改 tests，不修改 frontend，不修改既有 docs，不启动后端或前端服务，不运行 Ollama，不访问端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不生成 DOCX，不写 `output/job/export`，不进入真实 ZDoc/ZBid 联调，也不进入 50 人团队正式部署设计。

本文档只定义未来可实施的 route 目标、输入输出、正式链阻断、metadata-only validator 边界、evidence 边界和验收条件。真正改代码必须在后续单独授权步骤中执行。

## 2. Current Baseline

当前基线如下：

- 前端 no-write UI 已修复，并通过截图级 visual smoke。
- Step 177 已确认页面可见 `preview-only`、`no-write`、`blocked_reasons`、`AI advisory 不是 evidence`、`preview 不是正式正文` 和“正式导出未开放”。
- Step 177 已确认“生成 Word 文档”入口不可提交正式生成，按钮 `disabled=true`、`aria-disabled=true`、`type=button`。
- Step 177 已确认 `submit_word_button_count=0`、`generate_hidden_form_count=0`。
- Step 177 已确认 `output/job/export` 前置快照为空、后置快照为空、前后无差异。
- 后端 `/local-llm/preview-safe` 可读，并返回 `preview_only=true`、`no_write=true`。
- fake ZDoc/ZBid preview packet helper 已存在：`backend/zhifei_autoplan/zdoc_zbid_preview_packet.py`。
- fake ZBid preview input validator 已存在：`backend/zhifei_autoplan/zbid_preview_input_validator.py`。
- 当前 helper / validator 仍为 fake-only / metadata-only 能力。
- 当前仍未实现真实 local trial preview-only route。
- 当前仍未进入真实 ZDoc/ZBid 联调。
- 当前仍未开放正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback 或 `output/job/export` 写入。

## 3. Future Preview-Only Route Goal

未来 preview-only route 的目标是为本地小范围试用提供一个安全的、只读的、metadata-only 的预览入口。该 route 只允许生成 preview packet、执行 metadata-only validator，并返回 preview-only / no-write / blocked_reasons / formal flags。

未来 route 必须满足：

- 只生成 preview packet。
- 只执行 metadata-only validator。
- 只返回 preview-only 状态。
- 只返回 no-write 状态。
- 只返回 `blocked_reasons`。
- 只返回 formal flags。
- 不触发正式正文生成。
- 不触发 DOCX 导出。
- 不触发 review/apply。
- 不触发 ZBid 写回。
- 不调用 ZBid API / DB / writeback。
- 不执行 formal writeback。
- 不执行 formal writeback dry-run。
- 不写 `output/job/export`。
- 不生成 DOCX / JSON / Markdown 正式产物。

preview-only route 的返回结果只能用于本地试用中的人工核查、UI 展示和后续问题定位，不得被解释为正式正文、正式 evidence、正式写回许可或 ZBid 接入完成。

## 4. Future Route Design Scope

建议未来仅新增本地试用专用 preview-only route。route 名称仅作为设计占位，本步不实现。

候选占位命名：

- `POST /local-trial/preview-only`
- 或 `POST /zdoc/local-trial/preview-only`

最终命名应在后续实现步骤中结合现有 router 结构确定，但必须保持 local trial / preview-only / no-write 语义清晰，不得复用 `/generate`、`/export_docx`、`/review/apply` 或任何正式写回入口。

未来 route 输入应为 fake/local trial metadata，至少包含：

- `integration_request_id`
- `project_id`
- `document_id`
- `section_id`
- `section_hash`
- `section_version`
- `tender_file_refs`
- `scoring_clause_refs`
- `evidence_anchor_refs`
- `response_mode`
- `input_risk_level`
- `advisory_quality_gate_status`

未来 route 输出应包含：

- preview packet。
- validator result。
- `preview_only=true`。
- `no_write=true`。
- `blocked_reasons`。
- `formal_writeback_allowed=false`。
- `review_apply_allowed=false`。
- `docx_export_allowed=false`。
- `zbid_writeback_allowed=false`。
- `output_write_allowed=false`。
- `accepted_preview_only` 或 `blocked` / `requires_human_review` 等 metadata-only decision。

未来 route 不得输出可直接写回的正文 payload，不得输出正式 DOCX 产物路径，不得输出 ZBid writeback payload，不得输出任何可被前端误用为正式写回许可的字段。

## 5. Input Contract Design

未来 route 的输入契约应保持 fake/local trial metadata-only：

- 输入只能表达本地试用 metadata。
- 输入不得携带正式正文写回请求。
- 输入不得携带 DOCX 导出请求。
- 输入不得携带 review/apply 请求。
- 输入不得携带 ZBid 写回请求。
- 输入不得携带 output/job/export 写入请求。
- 输入不得携带真实 candidate patch 写入请求。

必填字段缺失时，route 应返回 blocked，并在 `blocked_reasons` 中列明原因。

必须 blocked 的输入情况包括：

- 非 `dict` 或非结构化 metadata 输入。
- 缺少 `integration_request_id`。
- 缺少 `project_id` / `document_id` / `section_id`。
- 缺少 `section_hash` / `section_version`。
- 缺少 `tender_file_refs`。
- 缺少 `scoring_clause_refs`。
- 缺少 `evidence_anchor_refs`。
- `evidence_anchor_refs` 不可验证。
- `scoring_clause_refs` 不可验证。
- generated advisory / preview advisory / shadow candidate / patch / diff / rollback / dry-run 被作为 evidence。
- `thinking_only_fallback` 被作为正式正文能力。
- high input risk without validation。
- 任一正式链请求为 true。

## 6. Output Contract Design

未来 route 的输出契约应同时服务前端展示和审计检查：

- `request_id`
- `integration_request_id`
- `project_id`
- `document_id`
- `section_id`
- `section_hash`
- `section_version`
- `preview_packet`
- `validator_result`
- `blocked_reasons`
- `response_mode`
- `input_risk_level`
- `advisory_quality_gate_status`
- `generated_at`
- `preview_only=true`
- `no_write=true`
- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

输出必须明确：

- preview packet 只是预览包。
- validator result 只是 metadata-only 校验结果。
- `accepted_preview_only` 不等于 evidence。
- `accepted_preview_only` 不等于写回许可。
- `accepted_preview_only` 不等于 ZBid 联调完成。
- `blocked_reasons` 必须可读。
- 所有正式链 flags 必须恒 false。

## 7. Formal Flags Contract

未来 route 中五个正式链 flags 必须恒 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

任一 flag 为 true 时必须视为 stop condition，不得继续试用、不得展示为可写回状态、不得允许前端触发正式链。

## 8. Safety Boundary

未来 preview-only route 必须保持以下安全边界：

- 不得调用 orchestrator 正式生成链。
- 不得调用 `llm_client` 正式正文生成。
- 不得调用 provider 正式生成能力。
- 不得调用 generation 链。
- 不得调用 export / `export_docx`。
- 不得调用 review/apply。
- 不得调用 actions_bridge 中的正式动作。
- 不得调用 ZBid API。
- 不得访问 ZBid DB。
- 不得调用 ZBid writeback。
- 不得执行 formal writeback。
- 不得执行 formal writeback dry-run。
- 不得写 `output/job/export`。
- 不得生成 DOCX。
- 不得生成正式 JSON / Markdown 导出产物。
- 不得修改 source section。
- 不得生成真实 candidate patch。
- 不得进入真实 shadow generation implementation。
- 不得进入本地化部署执行。
- 不得进入 50 人团队正式部署设计。

evidence 边界必须保持：

- advisory 不得作为 evidence。
- preview advisory 不得作为 evidence。
- shadow candidate / patch / diff / rollback / dry-run 不得作为 evidence。
- ZBid scoring preview 不得作为 evidence。
- preview 不得作为正式正文。
- evidence 必须来自可验证资料锚点。
- scoring refs 必须指向可验证评分条款。
- 不得臆造评分条款。

## 9. Backend Integration Boundary

后续实现时，建议只在本地试用专用 router 中挂载 preview-only route，并复用现有 fake preview packet helper 与 fake validator 的 metadata-only 能力。

后端实现不得修改：

- orchestrator 正式生成链。
- `llm_client` 正式正文生成链。
- provider 生成链。
- export / DOCX 导出链。
- review/apply 链。
- ZBid 写回链。
- formal writeback 链。
- rollback / source section 正式修改链。

如需要新增 route 测试，应优先使用 fake-only / deterministic tests，验证 route 输出结构、blocked_reasons、formal flags false、import isolation 和 no side effects。

## 10. Frontend Display Boundary

未来 frontend 如接入该 preview-only route，必须延续 Step 171 / Step 177 已验证的 no-write UI 边界：

- 页面必须明确显示 `preview-only`。
- 页面必须明确显示 `no-write`。
- 页面必须展示 `blocked_reasons`。
- 页面必须提示 AI advisory 不是 evidence。
- 页面必须提示 preview 不是正式正文。
- “生成 Word 文档”不得表现为可提交正式生成。
- DOCX / ZBid / review/apply / formal writeback / output write 入口必须禁用或提示未开放。
- route 返回的 `accepted_preview_only` 不得被前端解释为写回许可。
- route 返回的 preview packet 不得被前端展示为正式正文。

## 11. Acceptance Criteria

未来 preview-only route design / implementation 需要满足以下验收标准：

- route design 覆盖输入字段。
- route design 覆盖输出字段。
- route design 覆盖 `blocked_reasons`。
- route design 覆盖五个 formal flags。
- route 明确 no-write。
- route 明确 preview-only。
- route 明确 evidence 边界。
- route 明确 scoring refs 边界。
- route 明确 ZBid 仅 metadata-only。
- route 明确所有正式链 blocked。
- route 不调用正式生成链。
- route 不调用 DOCX 导出链。
- route 不调用 review/apply。
- route 不调用 ZBid API / DB / writeback。
- route 不写 `output/job/export`。
- route 不生成 DOCX。
- route 不产生正式导出物。
- route 测试必须 fake-only / deterministic。
- route 测试不得启动服务、访问端口、运行 Ollama 或调用外部模型/API。

## 12. Remaining Blockers Before Implementation

进入真正代码实现前仍需：

- Step 180 使用 fake schema tests 固化本设计文档的结构与边界。
- 明确未来 route 所属 router 文件。
- 明确是否需要新增 backend route tests。
- 明确是否需要 frontend 调用该 route。
- 明确 preview-only route 的请求样例。
- 明确 local trial metadata 的最小字段集。
- 明确 blocked_reasons 的统一展示格式。
- 明确 output/job/export no-write 回归检查方式。
- 明确 import isolation 约束。
- 明确用户对 Step 181 改代码的单独授权。

## 13. Recommended Next Steps

建议下一步为：

ZDoc Step 180：local trial preview-only route implementation plan fake schema tests。

Step 180 应为 tests-only / fake schema tests，只固化 Step 179 的 route plan 结构、输入输出、blocked_reasons、formal flags、no-write 边界和 import isolation，不实现生产 route，不启动服务，不运行 Ollama，不访问端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不写 `output/job/export`。

后续建议：

- Step 181：preview-only route code implementation，需用户单独授权后才可改代码。
- Step 181 不得修改正式生成链、DOCX 导出链、review/apply、ZBid 写回链或 formal writeback 链。
- Step 181 不得进入真实 ZDoc/ZBid 联调。
- Step 181 不得进入 50 人团队正式部署设计。

## 14. Safety Conclusion

Step 179 仅完成 local trial preview-only route implementation plan design。本文档不代表真实 preview-only route 已实现，不代表 ZDoc/ZBid 已实际联调，不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback、`output/job/export` 写入、本地化部署或 50 人团队正式部署已经开放或实现。

当前安全结论保持不变：

- 当前系统仍处于 preview-only / no-write 约束下。
- 前端 no-write UI 已通过截图级 visual smoke。
- 后端 preview-safe 可读。
- fake preview packet helper 与 fake validator 可作为未来 route 设计基础。
- 真实 preview-only route 仍未实现。
- 所有正式链 flags 必须保持 false。
