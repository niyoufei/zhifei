# ZDoc Preview-Only Route Same-Origin Proxy Controlled Smoke Report

## 1. Scope

本文档归档 Step 198：preview-only route same-origin proxy controlled smoke。

本步在用户明确授权下执行，仅用于验证前端同源 proxy 是否可将 `fetch("/local-trial/preview-only")` 转发至后端 preview-only route，并验证前端动态展示结果。

本步保持 preview-only / no-write / no-formal-chain 边界：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不运行 pytest。
- 不运行 Ollama。
- 不调用 `/generate`。
- 不调用 `/export_docx`。
- 不调用 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入正式生成链。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入约 50 人团队正式部署设计。

## 2. Git Baseline

- 当前目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`ac692805ac739a51b5a224b3aae0f55bce122b6f`
- 结束后 HEAD：`ac692805ac739a51b5a224b3aae0f55bce122b6f`
- smoke 前 `git status --short`：空
- smoke 后 `git status --short`：空

## 3. Output Isolation

smoke 前后只读检查 `output/job/export`：

- 前置快照文件数：`0`
- 后置快照文件数：`0`
- 前后 diff：无差异

结论：

- 未写 `output/job/export`。
- 未生成 DOCX。
- 未生成正式 JSON / Markdown / job / export 产物。
- 未删除或清理任何文件。

## 4. Services Started

本步仅启动验证所需的本地后端与前端服务。

后端：

- 启动命令：`PYTHONDONTWRITEBYTECODE=1 ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18760`
- 工作目录：`/Users/youfeini/Desktop/文档生成系统`
- 地址：`http://127.0.0.1:18760`
- PID：`17626`
- 停止结果：已停止
- 端口停止后状态：`127.0.0.1:18760` 无监听

前端：

- 启动命令：`PYTHONDONTWRITEBYTECODE=1 TDOCSYS_BYPASS_LOGIN=1 TDOCSYS_PORT=18761 TDOCSYS_BACKEND_BASE_URL=http://127.0.0.1:18760 python app.py`
- 工作目录：`/Users/youfeini/Desktop/文档生成系统/frontend_web`
- 地址：`http://127.0.0.1:18761`
- PID：`17651`
- 停止结果：已停止
- 端口停止后状态：`127.0.0.1:18761` 无监听

## 5. Accessed Addresses and Interfaces

本步访问了以下本地地址：

- `GET http://127.0.0.1:18761/index`
- `GET http://127.0.0.1:18761/static/style.css`
- `POST http://127.0.0.1:18760/local-trial/preview-only`
- `POST http://127.0.0.1:18761/local-trial/preview-only`

本步未访问：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid API / DB / writeback
- `127.0.0.1:11434`
- Ollama
- 外部模型/API

## 6. Direct Backend Route Result

后端直接调用结果：

- `POST http://127.0.0.1:18760/local-trial/preview-only`：HTTP `200`
- `preview_only=true`
- `no_write=true`
- `preview_packet`：可读
- `validator_result`：可读
- `blocked_reasons`：可读

`blocked_reasons` 包含：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

后端返回的安全标志：

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

## 7. Frontend Same-Origin Proxy Result

前端同源 proxy 调用结果：

- `POST http://127.0.0.1:18761/local-trial/preview-only`：HTTP `200`
- `preview_only=true`
- `no_write=true`
- `preview_packet`：可读
- `validator_result`：可读
- `blocked_reasons`：可读

前端同源 proxy 返回的 `blocked_reasons` 包含：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

前端同源 proxy 返回的安全标志：

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

结论：

- Step 193 中前端端口 `POST /local-trial/preview-only` 返回 HTTP `404`。
- Step 198 中前端端口 `POST /local-trial/preview-only` 返回 HTTP `200`。
- 同源 proxy 已成立。
- Step 193 的 404 问题已修复。

## 8. Frontend Dynamic Display Result

本步使用本地浏览器访问：

- `http://127.0.0.1:18761/index`

并点击页面中的 preview-only 加载按钮，该按钮仅触发：

- `fetch("/local-trial/preview-only")`

动态展示结果：

- 页面状态显示：`preview-only metadata 已加载；结果仅供人工核查，不是 evidence，不是正式正文。`
- `preview_packet`：动态展示成功。
- `validator_result`：动态展示成功。
- `blocked_reasons`：动态展示成功。

页面动态展示的 `blocked_reasons`：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

页面动态展示的五个正式链 false flags：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

结论：

- 前端 `fetch("/local-trial/preview-only")` 已能通过前端端口 `18761` 同源 proxy 动态加载后端 preview-only 数据。
- 页面已能动态展示 `preview_packet`、`validator_result`、`blocked_reasons` 和五个正式链 false flags。

## 9. Strict Non-Occurrence Confirmation

本步严格未发生：

- 未运行 pytest。
- 未运行 Ollama。
- 未运行 `ollama serve`。
- 未访问 `127.0.0.1:11434`。
- 未调用外部模型/API。
- 未调用 `/generate`。
- 未调用 `/export_docx`。
- 未调用 `/review/apply`。
- 未触发 ZBid 写回。
- 未调用 ZBid API / DB / writeback。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未进入正式生成链。
- 未进入真实 ZDoc/ZBid 联调。
- 未进入约 50 人团队正式部署设计。
- 未修改代码。
- 未修改 tests。
- 未修改 frontend。
- 未修改既有 docs。

## 10. Service Shutdown Result

- 后端 PID `17626` 已停止。
- 前端 PID `17651` 已停止。
- `127.0.0.1:18760` 停止后无监听。
- `127.0.0.1:18761` 停止后无监听。
- 未发现本步启动进程残留。

## 11. Risk Assessment

未发现 high risk 写入或正式链触发。

当前限制：

1. 本步只验证本地双端口环境下的同源 proxy。
2. 本步未进入真实 ZDoc/ZBid 联调。
3. 本步未验证生产部署入口。
4. 本步未运行 pytest。
5. 本步未验证 Ollama 或模型链路。
6. 本步不代表正式生成、DOCX 导出、review/apply 或 ZBid 写回已开放。

## 12. Recommendation

建议下一步为：

`ZDoc Step 199：preview-only route same-origin proxy controlled smoke stage review`

建议性质：

- docs-only / stage-review-only。
- 归档 Step 198 runtime smoke 结果。
- 不启动服务。
- 不访问端口。
- 不运行 pytest。
- 不运行 Ollama。
- 不触发正式链。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入约 50 人团队正式部署设计。

## 13. Conclusion

Step 198 controlled smoke 通过：

- 后端 `POST /local-trial/preview-only` 返回 HTTP `200`。
- 前端同源 `POST /local-trial/preview-only` 返回 HTTP `200`。
- Step 193 的前端端口 HTTP `404` 已修复。
- 前端 `fetch("/local-trial/preview-only")` 已能通过同源 proxy 动态加载 preview-only 数据。
- 页面动态展示 `preview_packet`、`validator_result`、`blocked_reasons` 和五个正式链 false flags。
- 未触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 服务均已停止。
