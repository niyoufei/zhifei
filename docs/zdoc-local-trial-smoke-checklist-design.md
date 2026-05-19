# ZDoc Local Trial Smoke Checklist Design

## 1. Scope

Step 148 仅设计 ZDoc / 文档生成系统本地小范围试用前的 smoke checklist，不执行 smoke test。

本文档用于后续真正执行本地化部署基础闭环、ZDoc / ZBid preview-only 联通和小范围试用前的人工核查与验收。本文档只形成后续执行 smoke test 的检查清单、通过标准、阻断条件、失败处理和回报模板。

本步是 docs-only：

- 不执行 smoke test。
- 不启动服务。
- 不启动后端服务。
- 不启动前端服务。
- 不访问任何本地服务端口。
- 不运行 Ollama。
- 不调用模型。
- 不调用 ZBid。
- 不调用 ZBid API / 数据库 / 写回接口。
- 不写 `output/job/export`。
- 不触发 `/generate`、`/export_docx`、`/review/apply`。
- 不生成 DOCX / JSON / Markdown 正式产物。
- 不进入 ZDoc / ZBid 实际联调。
- 不进入本地化部署执行。
- 不进入 50 人团队正式部署设计。

本文档不代表本地化部署已完成，不代表 ZDoc / ZBid 已实际联调，不代表后端或前端服务已启动，不代表 Ollama 或本地模型已运行，不代表 DOCX 导出、ZBid 写回、review/apply、formal writeback 已实现。

## 2. Trial Positioning

当前总体策略仍为：

- 先完成本地化部署基础闭环。
- 再完成 ZDoc 与 ZBid 的 preview-only 对接。
- 再进行小范围试用和问题修正。
- 最后再按约 50 人同时使用场景进行正式部署设计。

本地小范围试用定位：

- 目标是验证本地系统可启动、可访问、可预览、可阻断、可审计。
- 不验证高并发。
- 不验证正式写回。
- 不验证 DOCX 正式导出。
- 不验证 ZBid 正式写回。
- 不验证 review/apply。
- 不验证 50 人同时使用。
- 不开放任何正式链 flags。

小范围试用阶段只验证 preview-only、metadata-only、no-write、`blocked_reasons` 和审计可读性。当前不得进入 50 人正式部署设计，不得设计 Mac Studio / NAS / UPS / Redis / PostgreSQL 正式部署架构。

当前所有正式链 flags 仍应保持 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

## 3. Pre-Run Manual Checklist

以下为执行 smoke test 前的人工核查项。本文档不执行命令。

版本与工作区：

- 当前目录是否为 `/Users/youfeini/Desktop/文档生成系统`。
- 当前分支是否为 `main`。
- 工作区是否 clean。
- 当前 tag 是否明确。
- 当前 commit 是否与试用记录一致。
- 是否不存在未提交代码、测试、docs、配置或 runtime artifact。

环境与配置：

- 本地 `.env` / local config 是否存在但不提交。
- Python 环境是否可重建。
- Node / pnpm 环境是否可重建。
- Ollama 是否仅作为可选服务检查。
- 项目资料目录是否明确。
- 日志目录是否明确。
- `output/job/export` 是否隔离。
- `.env`、local config、数据库、模型、缓存或运行时文件不得被提交。

安全开关：

- no-write flag 是否默认开启。
- preview-only flag 是否默认开启。
- DOCX export flag 是否默认关闭。
- ZBid writeback flag 是否默认关闭。
- review/apply flag 是否默认关闭。
- formal writeback flag 是否默认关闭。
- formal writeback dry-run execution 是否默认关闭。

## 4. Backend Smoke Checklist

以下为后续执行时应检查的后端 smoke 项。本文档不执行。

- 后端是否可启动。
- 健康检查是否可读。
- 配置加载是否可读。
- no-write 状态是否可读。
- preview-only 状态是否可读。
- ZBid writeback 是否默认 blocked。
- DOCX export 是否默认 blocked。
- review/apply 是否默认 blocked。
- formal writeback 是否默认 blocked。
- 错误返回是否包含 `blocked_reasons`。
- 日志是否记录 `request_id`。
- 后端启动通过不得被解释为正式写回、DOCX 导出、review/apply 或 ZBid 写回已开放。

## 5. Frontend Smoke Checklist

以下为后续执行时应检查的前端 smoke 项。本文档不执行。

- 前端是否可启动。
- 页面是否可访问。
- 本地模型状态是否只读显示。
- preview-only 结果是否展示为预览。
- `blocked_reasons` 是否可读。
- DOCX / ZBid / review/apply / formal writeback 按钮是否默认禁用或提示未开放。
- 用户不得误认为 preview 已写回。
- 用户不得误认为 advisory 是 evidence。
- 用户不得误认为 accepted preview 已经进入正式正文。
- 用户不得误认为 ZBid preview scoring 可作为 evidence。

## 6. Ollama Smoke Checklist

以下为后续执行时应检查的 Ollama smoke 项。本文档不执行。

- Ollama 服务是否可选检查。
- 本地模型列表是否可读。
- 模型不可用时是否 fallback。
- `thinking_only_fallback` 不得作为正式正文能力。
- 模型失败不得写回。
- 模型失败不得触发 DOCX / ZBid / review/apply。
- 模型失败不得触发 formal writeback。
- 模型输出不得作为 evidence。
- 模型输出不得自动进入 ZBid scoring。

## 7. ZDoc Preview Packet Smoke Checklist

ZDoc preview packet 检查项：

- preview packet 是否包含 `integration_request_id`。
- `project_id` / `document_id` / `section_id` 是否完整。
- `section_hash` / `section_version` 是否完整。
- `tender_file_refs` 是否存在。
- `scoring_clause_refs` 是否存在。
- `evidence_anchor_refs` 是否存在。
- `response_mode` 是否明确。
- `input_risk_level` 是否明确。
- `advisory_quality_gate_status` 是否明确。
- `blocked_reasons` 是否可读。
- `preview_advisory_summary` 是否只作为提示性 preview 字段。
- `shadow_candidate_id`、`patch_id`、`diff_preview_id`、`rollback_plan_id`、`dry_run_id` 是否仅作为追踪字段。
- 正式链 flags 是否恒 false。

## 8. ZBid Preview Input Validator Smoke Checklist

ZBid preview input validator 检查项：

- validator 仅接收 fake `dict`。
- 非 `dict` 输入必须 blocked。
- 缺少 required fields 必须 blocked。
- missing evidence anchor 必须 blocked。
- missing scoring clause refs 必须 blocked。
- generated advisory / preview advisory / shadow candidate / patch / diff / rollback / dry-run 作为 evidence 必须 blocked。
- `thinking_only_fallback` 必须 blocked。
- high input risk without validation 必须 blocked。
- `zbid_writeback_requested=true` 必须 blocked。
- `future_guarded_writeback` 当前必须 blocked。
- `accepted_metadata_only` 不得打开写回权限。
- `accepted_preview_only` 不得打开写回权限。
- `zbid_writeback_allowed` 必须 false。
- `docx_export_allowed` 必须 false。
- `review_apply_allowed` 必须 false。
- `formal_writeback_allowed` 必须 false。
- `output_write_allowed` 必须 false。

## 9. DOCX / Review-Apply / ZBid / Formal Writeback Block Checklist

DOCX 阻断项：

- `/export_docx` 请求必须 blocked。
- DOCX 文件不得生成。
- DOCX isolation passed 不得开放 ZBid。
- `docx_export_allowed` 必须 false。

review/apply 阻断项：

- `/review/apply` 请求必须 blocked。
- review/apply 请求不得修改 source section。
- `review_apply_allowed` 必须 false。

ZBid 阻断项：

- ZBid writeback 请求必须 blocked。
- ZBid API / DB / writeback 不得调用。
- ZBid isolation passed 不得开放 ZBid writeback。
- `zbid_writeback_allowed` 必须 false。

formal writeback 阻断项：

- formal writeback 请求必须 blocked。
- output/job/export 写入必须 blocked。
- dry-run passed 不得开放 formal writeback。
- source hash matched 不得开放 formal writeback。
- `formal_writeback_allowed` 必须 false。
- `output_write_allowed` 必须 false。

## 10. Evidence And Scoring Smoke Checklist

evidence / scoring 检查项：

- `evidence_anchor_refs` 必须来源可验证资料。
- `scoring_clause_refs` 必须指向可验证评分条款。
- `tender_file_refs` 不等于自动 evidence。
- preview advisory 不得作为 evidence。
- ZBid scoring preview 不得作为 evidence。
- AI 建议不得作为 evidence。
- generated advisory 不得作为 evidence。
- shadow candidate 不得作为 evidence。
- patch preview 不得作为 evidence。
- diff preview 不得作为 evidence。
- rollback plan 不得作为 evidence。
- dry-run result 不得作为 evidence。
- 缺少 evidence 或评分条款必须 `requires_human_review` 或 blocked。
- 不得臆造评分条款。

## 11. Audit Fields Checklist

smoke test 后续应观察的审计字段包括：

- `request_id`
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
- `shadow_candidate_id`
- `patch_id`
- `diff_preview_id`
- `rollback_plan_id`
- `dry_run_id`
- `blocked_reasons`
- `generated_at`
- `formal_writeback_allowed`
- `review_apply_allowed`
- `docx_export_allowed`
- `zbid_writeback_allowed`
- `output_write_allowed`

这些字段用于试用观察和问题定位，不代表实现持久化、真实审计存储或正式联调。

## 12. Failure Handling Checklist

失败处理规则：

- 后端启动失败：停止，记录错误。
- 前端启动失败：停止，记录错误。
- Ollama 不可用：进入 fallback，不写回。
- evidence 缺失：blocked。
- scoring refs 缺失：blocked 或 `requires_human_review`。
- DOCX 请求出现：blocked。
- ZBid 写回请求出现：blocked。
- review/apply 请求出现：blocked。
- formal writeback 请求出现：blocked。
- `output/job/export` 有非预期写入：立即停止。
- source hash mismatch：`stale_source_hash`。
- source version mismatch：`stale_source_version`。
- advisory 被作为 evidence：立即停止并记录。
- preview 被误显示为正式正文：立即停止并记录。
- full backend tests 既有 collection/order 问题不得在 smoke 阶段擅自修改生产代码修复。

## 13. Smoke Test Pass Criteria

后续真正执行 smoke test 时，通过标准应包括：

- 后端可启动并可读健康状态。
- 前端可访问。
- preview-only 数据链可产生。
- validator 可阻断不安全输入。
- evidence / scoring 边界清楚。
- DOCX / ZBid / review/apply / formal writeback 默认 blocked。
- 所有正式链 flags 恒 false。
- `blocked_reasons` 可读。
- 未写 `output/job/export`。
- 未调用 ZBid。
- 未生成 DOCX。
- 未进入 50 人部署设计。

## 14. Smoke Test Stop Criteria

后续真正执行 smoke test 时，任一以下情况必须停止：

- 任一正式链 flag 为 true。
- 出现 `output/job/export` 写入。
- 出现 DOCX 文件。
- 出现 ZBid API / DB / writeback 调用。
- 出现 `/review/apply` 调用。
- 出现 `/generate` 正式生成。
- advisory 被作为 evidence。
- preview 被误显示为正式正文。
- source hash / version 不一致但未 blocked。
- 缺少 `blocked_reasons`。
- ZBid preview scoring 被作为 evidence。
- accepted preview 被解释为 writeback permission。

## 15. Next Step Recommendation

建议下一步为：

ZDoc Step 149：local trial smoke checklist fake schema tests，tests-only。

Step 149 不得启动服务，不得运行 Ollama，不得执行 smoke test，不得调用 ZBid，不得写 `output/job/export`，仅用 fake schema tests 固化 Step 148 的 checklist 结构和阻断规则。

## 16. Safety Conclusion

Step 148 仅完成 local trial smoke checklist design，不代表本地化部署已执行，不代表 ZDoc / ZBid 已实际联调，不代表正式写回、DOCX 导出、ZBid 写回或 50 人团队部署已实现。
