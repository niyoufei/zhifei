# ZDoc-ZBid Preview-Only Integration Code Implementation Authorization Request

## 1. Purpose

本文档对应 Step 201：ZDoc-ZBid preview-only integration code implementation authorization request。

本步仅起草后续 ZDoc-ZBid preview-only 对接代码实现的授权请求文本，用于提交给用户审核。本文档只代表申请授权，不代表用户已经授权。

本步性质为 docs-only / authorization-request-only / no-code-change / no-service / no-port-access / no-writeback：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不运行 pytest。
- 不启动服务。
- 不访问端口。
- 不运行 Ollama。
- 不调用 `/local-trial/preview-only`。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入 50 人正式部署设计。

只有用户后续明确回复授权，才可进入 Step 202；本授权请求文档不得被视为 Step 202 的授权本身。

## 2. Authorization Request Source

本授权请求基于 Step 200：ZDoc-ZBid preview-only integration interface boundary design。

Step 200 已明确：

- 当前 ZDoc 已具备 `/local-trial/preview-only` 后端 route。
- 当前 ZDoc 已具备前端同源 `/local-trial/preview-only` proxy。
- 当前 ZDoc 前端已可动态展示 `preview_packet`、`validator_result`、`blocked_reasons` 和五个正式链 false flags。
- 当前 preview-only 能力仍限定为 local trial / preview-only / no-write / no-formal-chain。
- 当前能力不代表正式生成、DOCX 导出、review/apply、ZBid 写回或真实 ZDoc/ZBid 联调已开放。

Step 198 / Step 199 已归档的当前基线包括：

- 后端 `POST 127.0.0.1:18760/local-trial/preview-only` 返回 HTTP `200`。
- 前端同源 `POST 127.0.0.1:18761/local-trial/preview-only` 返回 HTTP `200`。
- Step 193 的前端同源 HTTP `404` 已修复为 HTTP `200`。
- 前端 `fetch("/local-trial/preview-only")` 已能通过同源 proxy 动态加载 preview-only 数据。
- `output/job/export` 前后无新增写入。

本授权请求仅在上述边界上申请后续最小代码实现权限，不申请运行 smoke、不申请服务启动、不申请端口访问、不申请 ZBid 写回。

## 3. Requested Future Code Implementation Scope

拟向用户申请的后续 Step 202 代码实现范围必须限定为 preview-only / no-write / no-formal-chain。

允许申请的 ZDoc 侧最小实现范围：

- 增加最小 ZDoc 侧 preview-only outbound/client/adapter。
- 增加最小 ZDoc 侧配置占位，用于表达 preview-only 接收方地址或禁用状态。
- 仅传递 `preview_packet`。
- 仅传递 `validator_result`。
- 仅传递 `blocked_reasons`。
- 仅传递 no-write / no-formal-chain flags。
- 仅支持 metadata-only / preview-only payload。
- 仅允许 blocked 或 requires_human_review 语义。
- 仅允许用户授权范围内的静态测试或 fake schema tests。

明确不申请：

- 不申请修改正式生成链。
- 不申请修改 DOCX 导出链。
- 不申请修改 review/apply 链。
- 不申请修改 ZBid 写回链。
- 不申请接入真实模型调用。
- 不申请执行 runtime smoke。
- 不申请启动服务。
- 不申请访问端口。
- 不申请写 `output/job/export`。
- 不申请进入真实 ZDoc/ZBid 联调。
- 不申请进入 50 人正式部署设计。

如果 Step 202 需要涉及 ZBid 侧代码，必须在用户授权前明确：

- ZBid 仓库绝对路径。
- ZBid 当前分支。
- ZBid 开始前 HEAD。
- ZBid `git status --short` 必须为空。
- ZBid 允许修改文件范围。
- ZBid 禁止修改文件范围。
- ZBid 是否允许启动服务。
- ZBid 是否允许访问端口。
- ZBid 是否允许写任何业务数据。

在上述 ZBid 仓库路径、分支、HEAD 和允许文件范围未明确前，不得修改任何 ZBid 代码。

## 4. Preview-Only Payload Boundary

后续实现只允许传递以下 preview-only 数据：

- `preview_packet`
- `validator_result`
- `blocked_reasons`
- `preview_only=true`
- `no_write=true`
- `metadata_only=true`
- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `affects_zbid_writeback=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`

面向前端或人工审核展示时，可继续展示以下五个用户可读 false flags：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

如后续需要新增追踪字段，只能在用户授权后的代码实现设计中明确新增，不得在 Step 201 将其描述为已实现。

## 5. Required Boundary Invariants

后续任何 Step 202 代码实现必须保持以下边界：

1. ZBid 只能作为 preview-only 接收方或展示方。
2. ZBid 不得写回 ZDoc。
3. ZBid 不得写回 ZBid 正式业务数据。
4. ZBid 不得触发正式评分写入。
5. ZBid 不得触发正式审批、流转或归档。
6. `accepted_preview_only` 不等于 writeback permission。
7. `zbid_preview_scoring` 不得作为 evidence。
8. AI advisory 不得作为 evidence。
9. preview advisory 不得作为 evidence。
10. shadow candidate 不得作为 evidence。
11. patch preview 不得作为 evidence。
12. diff preview 不得作为 evidence。
13. rollback plan 不得作为 evidence。
14. dry-run result 不得作为 evidence。
15. preview 不得作为正式正文。
16. source hash / version mismatch 必须 blocked 或 requires_human_review。
17. `blocked_reasons` 必须可读。
18. 任一正式链 flag 为 `true` 必须 stop。
19. 任一写回请求未 blocked 必须 stop。

## 6. Explicitly Forbidden Chains

后续 Step 202 即使获得授权，也不得触发以下链路：

- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得触发 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得调用 ZBid API / DB / writeback。
- 不得生成 DOCX。
- 不得生成正式 JSON / Markdown / job / export 产物。
- 不得写 `output/job/export`。
- 不得进入正式正文生成链。
- 不得生成真实 candidate patch。
- 不得执行 formal writeback。
- 不得执行 formal writeback dry-run。
- 不得修改 source section。
- 不得恢复正文。
- 不得接入 50 人正式部署设计。

任何错误处理不得 fallback 到正式接口或正式写入链。

## 7. Requested Implementation Guardrails

如果用户授权 Step 202，建议 guardrails 如下：

- 开始前核验 `pwd`、分支、HEAD、`git status --short`。
- 只修改授权列明的文件。
- 只新增 preview-only client/adapter 或配置占位。
- 不新增通用 ZBid proxy。
- 不新增任意路径转发。
- 不新增正式写回入口。
- 不修改正式生成链。
- 不修改 DOCX 导出链。
- 不修改 review/apply 链。
- 不修改 ZBid 写回链。
- 不写 `output/job/export`。
- 不启动服务。
- 不访问端口。
- 不执行 runtime smoke。
- 只运行用户明确允许的静态测试或 fake schema tests。
- 如测试或静态检查失败，只允许修改 Step 202 授权范围内文件。

## 8. Future Step 202 Scope Proposal

授权后拟进入的下一步可为：

`ZDoc Step 202：ZDoc-ZBid preview-only integration code implementation`

Step 202 仍必须另有用户明确授权。

Step 202 不得默认获得以下权限：

- 不得默认启动服务。
- 不得默认访问端口。
- 不得默认调用 `/local-trial/preview-only`。
- 不得默认调用 ZBid receiver。
- 不得默认执行 smoke。
- 不得默认修改 ZBid 代码。
- 不得默认进入真实 ZDoc/ZBid 联调。
- 不得默认触发任何正式链。

如 Step 202 只在 ZDoc 仓库内实现 preview-only outbound/client/adapter，则必须明确允许文件范围和测试范围。

如 Step 202 需要跨 ZBid 仓库实现 receiver/display，则必须先补充 ZBid 仓库路径、分支、HEAD、clean 状态、允许文件范围和禁止动作清单。

## 9. Proposed User Authorization Wording

用户如同意进入 Step 202，应明确回复类似以下授权语：

> 我授权执行 Step 202：ZDoc-ZBid preview-only integration code implementation，授权范围仅限 Step 201 授权请求文档列明事项；允许在 ZDoc 仓库内新增最小 preview-only outbound/client/adapter 或配置占位，仅传递 `preview_packet`、`validator_result`、`blocked_reasons` 和 no-write / no-formal-chain false flags；不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回，不得生成 DOCX，不得写 `output/job/export`，不得启动服务，不得访问端口，不得执行 runtime smoke，不得进入真实 ZDoc/ZBid 联调，不得进入 50 人正式部署设计。若需修改 ZBid 侧代码，必须另行列明 ZBid 仓库路径、分支、HEAD、clean 状态和允许文件范围后再授权。

必须说明：

- 未收到上述或等效明确授权，不得执行 Step 202。
- 本文档不是授权本身。
- 部分授权不得扩大解释。
- preview-only 不等于 writeback allowed。
- authorization request 不等于 implementation permission。

## 10. Step 202 Report Template Recommendation

若后续 Step 202 获得授权，完成后至少应回报：

- 当前目录。
- 当前分支。
- 开始前 HEAD。
- 结束后 HEAD。
- `git status --short`。
- 实际新增/修改文件清单。
- 是否只修改授权范围内文件。
- 是否修改正式生成链。
- 是否修改 DOCX 导出链。
- 是否修改 review/apply 链。
- 是否修改 ZBid 写回链。
- 是否修改 frontend。
- 是否修改 tests。
- 是否修改既有 docs。
- 是否运行 pytest 或静态检查。
- 是否启动服务。
- 是否访问端口。
- 是否调用 `/local-trial/preview-only`。
- 是否调用 ZBid receiver。
- 是否触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
- 是否生成 DOCX。
- 是否写 `output/job/export`。
- 五个正式链 flags 是否恒 false。
- `git diff --check` 结果。
- commit hash。
- tag 名称及指向。
- push 结果。
- 风险说明。
- 下一步建议。

## 11. Next Step Recommendation

建议下一步为：

`ZDoc Step 202：ZDoc-ZBid preview-only integration code implementation`

前提：

- 必须用户明确授权。
- 授权必须限定 preview-only / no-write / no-formal-chain。
- 授权必须明确是否只改 ZDoc 侧。
- 如涉及 ZBid 侧，必须先明确 ZBid 仓库路径、分支、HEAD、clean 状态和允许文件范围。

Step 202 不得默认启动服务、访问端口或执行 smoke。后续任何 runtime smoke、跨系统端口访问、ZBid 侧接收验证，都必须再单独授权。

## 12. Safety Conclusion

Step 201 仅完成 ZDoc-ZBid preview-only 对接代码实现授权请求文档。

本步不代表：

- 用户已授权 Step 202。
- 已修改代码。
- 已修改 tests。
- 已修改 frontend。
- 已启动服务。
- 已访问端口。
- 已调用 `/local-trial/preview-only`。
- 已进入真实 ZDoc/ZBid 联调。
- 已触发正式生成。
- 已开放 DOCX 导出。
- 已开放 review/apply。
- 已开放 ZBid 写回。
- 已写 `output/job/export`。
- 已进入 50 人正式部署设计。

当前所有后续代码实现、服务启动、端口访问、接口调用、ZBid 侧接收验证、smoke 执行和跨系统修改仍必须获得用户逐项明确授权。
