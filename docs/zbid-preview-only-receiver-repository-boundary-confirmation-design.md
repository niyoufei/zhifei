# ZBid Preview-Only Receiver Repository Boundary Confirmation Design

## 1. Scope

本文档对应 Step 204：ZBid preview-only receiver repository boundary confirmation design。

本步仅起草 ZBid preview-only 接收方仓库边界确认设计，用于为后续是否进入 ZBid 侧 preview-only receiver 实现做准备。

本步性质为 docs-only / boundary-design-only / no-code-change / no-service / no-port-access / no-writeback：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不运行 pytest。
- 不启动服务。
- 不访问端口。
- 不运行 Ollama。
- 不调用 `/local-trial/preview-only`。
- 不调用任何 ZBid endpoint。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入 50 人正式部署设计。

本文档不代表已授权修改 ZBid 代码，不代表已授权访问 ZBid 仓库，不代表已授权启动服务、访问端口、调用接口或执行跨系统联调。

## 2. Current ZDoc-Side Baseline

当前 ZDoc 侧已完成以下 preview-only 能力：

1. `/local-trial/preview-only` 后端 route 可达。
2. 前端同源 `/local-trial/preview-only` proxy 已验证成立。
3. 前端可动态展示：
   - `preview_packet`
   - `validator_result`
   - `blocked_reasons`
   - `generate_called=false`
   - `export_docx_called=false`
   - `review_apply_called=false`
   - `zbid_writeback_called=false`
   - `output_job_export_written=false`
4. ZDoc 侧 default-off preview-only outbound adapter 已实现。

当前 ZDoc 侧已归档的关键结论：

- 后端 `POST 127.0.0.1:18760/local-trial/preview-only` 返回 HTTP `200`。
- 前端同源 `POST 127.0.0.1:18761/local-trial/preview-only` 返回 HTTP `200`。
- 前端 `fetch("/local-trial/preview-only")` 已能通过同源 proxy 动态加载 preview-only 数据。
- ZDoc outbound adapter 默认 `disabled/default-off`。
- 即使配置 endpoint，ZDoc outbound adapter 也只返回 `configured_not_sent`，不发送网络请求。
- no-write / no-formal-chain flags 恒为 false。

## 3. Current Missing Items

当前尚未完成：

- ZBid preview-only receiver 未实现。
- ZBid 仓库路径尚未最终确认。
- ZBid 分支尚未最终确认。
- ZBid 开始前 HEAD 尚未确认。
- ZBid `git status --short` clean 状态尚未确认。
- ZBid 允许文件范围尚未确认。
- ZBid 禁止修改范围尚未确认。
- 尚未进行 ZDoc/ZBid 跨系统 preview-only 调用。
- 尚未授权任何 ZBid 写回。
- 尚未授权任何 ZBid 业务数据写入。
- 尚未授权启动 ZBid 服务。
- 尚未授权访问 ZBid 端口。
- 尚未授权调用任何 ZBid endpoint。

这些事项必须在后续步骤中由用户明确授权后才能执行。

## 4. Candidate ZBid Repository Information

拟确认的 ZBid 仓库候选信息如下：

- 建议候选路径：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 建议候选分支：`local-llm-integration-clean`

重要边界：

- 以上仅为候选信息。
- 本步未访问该候选仓库。
- 本步未核验该候选仓库是否存在。
- 本步未核验该候选仓库当前分支。
- 本步未核验该候选仓库 HEAD。
- 本步未核验该候选仓库 `git status --short`。
- 本步未读取或修改任何 ZBid 文件。
- 后续进入 ZBid 代码修改前，仍需用户明确授权确认 ZBid 仓库路径、分支、HEAD、clean 状态、允许文件范围和禁止写回边界。

## 5. Required ZBid Repository Preflight for Future Steps

如后续用户授权进入 ZBid 侧 preview-only receiver 实现，开始前必须核验：

1. ZBid 仓库绝对路径。
2. ZBid 当前分支。
3. ZBid 开始前 HEAD。
4. ZBid `git status --short` 必须为空。
5. ZBid 允许新增/修改文件清单。
6. ZBid 禁止修改文件清单。
7. 是否允许启动 ZBid 服务。
8. 是否允许访问 ZBid 本地端口。
9. 是否允许调用 ZBid preview-only receiver。
10. 是否允许写任何运行时目录。

任一信息缺失、不一致或工作区不 clean，应立即停止，不得修改 ZBid 代码。

## 6. ZBid Preview-Only Receiver Allowed Boundary

ZBid 侧 preview-only receiver 的允许边界应严格限定为接收或展示 preview-only metadata。

允许接收或展示：

- `preview_packet`
- `validator_result`
- `blocked_reasons`
- `preview_only=true`
- `no_write=true`
- `metadata_only=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`
- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

允许状态：

- preview-only
- no-write
- no-evidence
- blocked
- requires_human_review
- metadata-only
- display-only

ZBid receiver 只能将这些数据作为人工核查和只读展示材料，不得作为自动评分、审批、写回或归档依据。

## 7. Evidence Boundary

ZBid 侧 preview-only receiver 必须保持 evidence 边界：

- advisory 不得作为 evidence。
- preview 不得作为 evidence。
- preview 不得作为正式正文。
- shadow candidate 不得作为 evidence。
- patch preview 不得作为 evidence。
- diff preview 不得作为 evidence。
- rollback plan 不得作为 evidence。
- dry-run result 不得作为 evidence。
- ZBid preview scoring 不得作为 evidence。
- `accepted_preview_only` 不得作为 writeback permission。

如果 receiver 无法清晰展示 evidence 边界，应进入 blocked 或 requires_human_review，不得写回。

## 8. Explicitly Forbidden Chains

ZBid preview-only receiver 边界中明确禁止：

- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得触发 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得调用 ZBid 正式写回 API。
- 不得访问 ZBid 正式业务数据库做写入。
- 不得写回 ZDoc。
- 不得写回 ZBid 正式业务数据。
- 不得生成 DOCX。
- 不得生成正式 JSON / Markdown / job / export 产物。
- 不得写 `output/job/export`。
- 不得进入正式正文生成链。
- 不得生成真实 candidate patch。
- 不得执行 formal writeback。
- 不得执行 formal writeback dry-run。
- 不得进入 50 人正式部署设计。

任何错误处理都不得 fallback 到正式接口或写回链。

## 9. Future ZBid Receiver Design Constraints

后续如实现 ZBid preview-only receiver，应优先采用最小、隔离、默认关闭的设计：

- preview-only receiver 独立于正式写回链。
- receiver 只接受 preview-only payload。
- receiver 不提供通用 proxy。
- receiver 不提供任意路径转发。
- receiver 不提供正式写回入口。
- receiver 不写数据库正式表。
- receiver 不写业务成果。
- receiver 不生成 DOCX。
- receiver 不写 `output/job/export`。
- receiver 错误时只返回 preview-only / no-write / blocked 状态。
- receiver 必须显示 `blocked_reasons`。
- receiver 必须显示 no-write / no-formal-chain false flags。
- receiver 必须显示 advisory/evidence 边界。

## 10. Future Authorization Requirements

后续真正进入 ZBid 代码修改前，用户授权必须逐项明确：

- ZBid 仓库路径。
- ZBid 分支。
- ZBid 开始前 HEAD。
- ZBid clean 状态要求。
- 允许新增文件。
- 允许修改文件。
- 禁止修改文件。
- 是否允许新增 tests。
- 是否允许运行 tests。
- 是否允许启动 ZBid 服务。
- 是否允许访问 ZBid 端口。
- 是否允许调用 ZBid preview-only receiver。
- 是否允许跨系统 ZDoc -> ZBid preview-only 调用。
- 是否允许生成 smoke report。
- 明确不得写回 ZDoc。
- 明确不得写回 ZBid 正式业务数据。
- 明确不得触发正式生成、DOCX 导出、review/apply 或 ZBid 写回。

未获得上述明确授权，不得修改 ZBid 代码。

## 11. Future Verification Points

后续如果进入 ZBid preview-only receiver 实现或 smoke，验证点至少应包括：

- ZBid 仓库路径与授权一致。
- ZBid 分支与授权一致。
- ZBid HEAD 与授权一致。
- ZBid `git status --short` clean。
- receiver 只接受 preview-only payload。
- receiver 可展示 `preview_packet`。
- receiver 可展示 `validator_result`。
- receiver 可展示 `blocked_reasons`。
- receiver 可展示五个用户可读 false flags。
- receiver 可展示正式链 false flags。
- receiver 不写 ZBid 正式业务数据。
- receiver 不写回 ZDoc。
- receiver 不调用正式写回 API。
- receiver 不访问正式业务数据库做写入。
- receiver 不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
- receiver 不生成 DOCX。
- receiver 不写 `output/job/export`。

## 12. Recommended Next Step

建议下一步可为：

`ZDoc Step 205：ZBid preview-only receiver code implementation authorization request`

Step 205 建议性质：

- docs-only / authorization-request-only。
- 仅起草 ZBid 侧代码实现授权请求。
- 不得视为已授权代码修改。
- 不得访问 ZBid 仓库。
- 不得启动服务。
- 不得访问端口。
- 不得调用接口。
- 不得触发正式生成、DOCX 导出、review/apply 或 ZBid 写回。
- 不得写 `output/job/export`。
- 不得进入真实 ZDoc/ZBid 联调。
- 不得进入 50 人正式部署设计。

真正进入 ZBid 代码修改前，必须由用户明确授权 ZBid 仓库路径、分支、开始前 HEAD、clean 状态、允许文件范围和禁止写回边界。

## 13. Safety Conclusion

当前 ZDoc 侧已完成 preview-only route、前端同源 proxy、前端动态展示和 default-off outbound adapter。

当前 ZBid 侧仍未实现 preview-only receiver；ZBid 仓库、分支、HEAD、允许文件范围和禁止写回边界仍需用户最终确认。

本文档仅完成 ZBid preview-only receiver 仓库边界确认设计：

- 候选路径仅作为候选，不代表已授权访问或修改。
- 候选分支仅作为候选，不代表已核验。
- ZBid receiver 只允许 preview-only / no-write / no-evidence。
- 不得写回 ZDoc。
- 不得写回 ZBid 正式业务数据。
- 不得把 advisory / preview / shadow / patch / diff / rollback / dry-run 作为 evidence。
- 不得触发正式生成、DOCX 导出、review/apply 或 ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。

后续任何 ZBid 代码修改、服务启动、端口访问、接口调用、ZBid 侧接收验证或跨系统联调，均需单独明确授权。
