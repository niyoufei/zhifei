# ZDoc Preview-Only Route Frontend Integration Controlled Smoke Report

## 1. Scope

本报告归档 Step 193：`/local-trial/preview-only` 前端接入受控 smoke。

本步在用户明确授权下执行，仅用于验证前端页面、后端 preview-only route、以及当前本地运行方式下的同源 route / proxy 是否成立。

本步保持 preview-only / no-write / no-formal-chain 边界：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不运行 pytest。
- 不运行 Ollama。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入约 50 人团队正式部署设计。

## 2. Git Baseline

- 当前目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`2bf33676e807feb326e6851ff2bd4bc5ed85d5d2`
- 结束后 HEAD：`2bf33676e807feb326e6851ff2bd4bc5ed85d5d2`
- smoke 前 `git status --short`：空
- smoke 后 `git status --short`：空
- HEAD tag：`v0.1.246-zdoc-preview-only-route-frontend-integration-controlled-smoke-authorization-request`

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
- PID：`7014`
- 停止结果：已停止
- 端口停止后状态：`127.0.0.1:18760` 无监听

前端：

- 启动命令：`PYTHONDONTWRITEBYTECODE=1 TDOCSYS_BYPASS_LOGIN=1 TDOCSYS_PORT=18761 python app.py`
- 工作目录：`/Users/youfeini/Desktop/文档生成系统/frontend_web`
- 地址：`http://127.0.0.1:18761`
- PID：`7027`
- 停止结果：已停止
- 端口停止后状态：`127.0.0.1:18761` 无监听

## 5. Accessed Addresses and Interfaces

本步访问了以下本地地址：

- `GET http://127.0.0.1:18761/index`
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

## 6. Frontend Page Result

前端页面访问结果：

- `GET /index`：HTTP `200`

页面 HTML 中已确认存在 preview-only 元数据面板：

- `/local-trial/preview-only 元数据预览` 可见。
- `id="loadPreviewOnlyRoute"` 按钮存在。
- `preview_packet` 展示区域存在。
- `validator_result` 展示区域存在。
- `blocked_reasons` 展示区域存在。
- `generate_called=false` 静态初始标志存在。
- `export_docx_called=false` 静态初始标志存在。
- `review_apply_called=false` 静态初始标志存在。
- `zbid_writeback_called=false` 静态初始标志存在。
- `output_job_export_written=false` 静态初始标志存在。

前端页面仍保持 no-write / preview-only 提示：

- 仅调用 preview-only / no-write route。
- 不触发正式生成。
- 不触发 DOCX 导出。
- 不触发 review/apply。
- 不触发 ZBid 写回。
- 失败时只显示错误，不 fallback 到正式接口。

## 7. Backend Route Result

后端直接调用结果：

- `POST http://127.0.0.1:18760/local-trial/preview-only`：HTTP `200`
- `route_name=local_trial_preview_only`
- `endpoint_path=/local-trial/preview-only`
- `preview_only=true`
- `no_write=true`
- `metadata_only=true`
- `preview_packet`：可读
- `validator_result`：可读
- `blocked_reasons`：可读

`blocked_reasons` 包含：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

## 8. Formal Chain Flags

后端 route 返回的正式链 flags 均为 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

后端 route 返回的调用 / 写入标志均为 false：

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `affects_zbid_writeback=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`

前端页面已提供五个面向用户的正式链 false flags 展示位：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

## 9. Same-Origin Route / Proxy Result

前端代码当前使用：

```javascript
fetch("/local-trial/preview-only")
```

在本次运行方式下：

- 前端服务地址：`http://127.0.0.1:18761`
- 后端服务地址：`http://127.0.0.1:18760`
- 后端 origin 直接 `POST /local-trial/preview-only`：HTTP `200`
- 前端 origin 同源 `POST /local-trial/preview-only`：HTTP `404`

结论：

当前双端口本地运行方式下，`fetch("/local-trial/preview-only")` 的同源 route / proxy 不成立。

因此：

- 前端页面静态展示区域已存在。
- 后端 preview-only route 可直接访问。
- 但前端通过当前同源路径无法动态加载后端 preview-only 数据。
- 本步按要求只记录失败原因，不修改代码修复。

## 10. Strict Non-Occurrence Confirmation

本步严格未发生：

- 未运行 pytest。
- 未运行 Ollama。
- 未运行 `ollama serve`。
- 未访问 `127.0.0.1:11434`。
- 未调用外部模型/API。
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
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

## 11. Service Shutdown Result

- 后端 PID `7014` 已停止。
- 前端 PID `7027` 已停止。
- `127.0.0.1:18760` 停止后无监听。
- `127.0.0.1:18761` 停止后无监听。
- 未发现本步启动进程残留。

## 12. Risk Assessment

未发现 high risk 写入或正式链触发。

当前主要风险：

1. 前端静态面板已存在，但同源 route / proxy 未成立，前端当前不能通过 `fetch("/local-trial/preview-only")` 动态加载后端数据。
2. 后端 `/local-trial/preview-only` route 自身 runtime 调用通过，但前端接入还缺少同源代理、统一服务入口，或前端请求 URL 调整方案。
3. 本步未修改代码，不解决同源失败。
4. 本步未点击任何正式生成、导出、写回入口。
5. 本步不代表真实 ZDoc/ZBid 联调已完成。
6. 本步不代表正式生成、DOCX 导出、review/apply 或 ZBid 写回已开放。

## 13. Recommendation

建议下一步为：

`ZDoc Step 194：preview-only route frontend same-origin/proxy fix plan design`

建议性质：

- docs-only / plan-only。
- 先设计同源 route / proxy 或前端请求 URL 的最小修复方案。
- 不直接改代码。
- 不触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入约 50 人团队正式部署设计。

## 14. Conclusion

Step 193 完成本地受控 smoke：

- 后端 `/local-trial/preview-only` 可达并返回 preview-only / no-write 数据。
- `preview_packet`、`validator_result`、`blocked_reasons` 可读。
- 正式链与写入标志均保持 false。
- 前端页面已具备 preview-only 元数据展示面板。
- 当前同源 route / proxy 未成立，前端相对路径调用返回 HTTP 404。
- 未触发正式链。
- 未写 `output/job/export`。
- 服务均已停止。
