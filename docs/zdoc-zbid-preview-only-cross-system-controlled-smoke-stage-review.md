# ZDoc-ZBid preview-only cross-system controlled smoke stage review

## 1. Step 222 授权来源与验证范围

Step 222 已由用户明确授权执行 ZDoc-ZBid preview-only cross-system controlled smoke。授权范围仅限验证 ZDoc outbound adapter 向 ZBid receiver endpoint 发送 preview-only payload。

本次 smoke 仅允许调用 ZBid receiver endpoint：

- `POST /local-llm/zdoc-preview-only/receive`

本次 smoke 严格不触发以下链路：

- 正式生成链
- 正式证据链
- 正式评分链
- DOCX 导出链
- review/apply 链
- ZBid 写回链

本次 smoke 不进入 50 人正式部署设计。

## 2. ZDoc 结果

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- Step 222 开始前 HEAD：`0c25ca2e3a1e8c52990a98512b44b4f82c9c4015`
- Step 222 结束后 HEAD：`abbaf0a0c7b7ebf70731517fd1c0c51c4d761993`
- `git status --short`：空
- 新增 smoke report：`docs/zdoc-zbid-preview-only-cross-system-controlled-smoke-report.md`

## 3. ZBid 结果

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 开始前 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 结束时 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- `git status --short`：空
- 未执行 commit
- 未创建 tag
- 未 push

## 4. smoke 执行结果

- 启动 ZBid 服务命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18763`
- ZBid 服务 PID：`57633`
- 访问端口：`127.0.0.1:18763`
- 调用 endpoint：`POST /local-llm/zdoc-preview-only/receive`
- ZDoc outbound adapter 成功发送 preview-only payload
- ZBid 返回：HTTP `200`

## 5. preview-only 结果

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `preview_packet` 可读
- `validator_result` 可读
- `blocked_reasons` 可读

## 6. 五个 no-write / no-formal-chain false flags

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

## 7. 安全边界

- 未运行 Ollama
- 未触发 `/generate`
- 未触发 `/export_docx`
- 未触发 `/review/apply`
- 未触发 ZBid 写回
- 未生成 DOCX
- ZDoc 侧 `output/job/export` 前置快照为空
- ZDoc 侧 `output/job/export` 后置快照为空
- ZBid 侧 `output/job/export` 前置快照为空
- ZBid 侧 `output/job/export` 后置快照为空
- smoke 后已停止 PID `57633`
- `127.0.0.1:18763` 无监听

## 8. 风险结论

本次仅验证本地 controlled smoke 的 preview-only / no-write / no-evidence 跨仓链路。

本次结果不代表以下能力已开放：

- 正式生成
- 正式证据链
- 正式评分链
- DOCX 导出
- review/apply
- ZBid 写回
- 50 人正式部署

`advisory`、`preview`、`shadow`、`patch`、`diff`、`rollback`、`dry-run` 均不得作为 evidence。

## 9. 下一步建议

- Step 224 可做 preview-only 对接阶段总归档。
- 如后续进入小范围试用，必须另行设计授权边界。
- 50 人正式部署设计仍不得提前进入。
