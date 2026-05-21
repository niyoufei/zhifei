# ZDoc Preview-Only Route Same-Origin Proxy Controlled Smoke Stage Review

## 1. Scope

本文档归档 Step 198：preview-only route same-origin proxy controlled smoke 的阶段复核结果。

本步为 docs-only / stage-review-only：

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

## 2. Step 198 Authorization and Verification Scope

Step 198 的授权来源为用户明确授权：

- 允许启动必要本地服务。
- 允许访问本地前端页面。
- 允许调用 `/local-trial/preview-only`。
- 仅用于验证前端端口同源 proxy 是否可将 `fetch("/local-trial/preview-only")` 转发至后端。
- 仅用于验证 `preview_packet`、`validator_result`、`blocked_reasons` 和五个正式链 false flags 的动态展示。

Step 198 验证范围限定为 preview-only / no-write / no-formal-chain：

- 启动本地后端服务。
- 启动本地前端服务。
- 访问前端页面。
- 调用后端 `POST /local-trial/preview-only`。
- 调用前端同源 `POST /local-trial/preview-only`。
- 通过前端页面触发 `fetch("/local-trial/preview-only")`。
- 检查 `output/job/export` 前后差异。
- 停止本次启动的服务。

Step 198 不授权也未执行正式生成、DOCX 导出、review/apply、ZBid 写回、Ollama、真实 ZDoc/ZBid 联调或 50 人正式部署设计。

## 3. Service Startup and Shutdown Result

Step 198 启动结果：

后端：

- 地址：`127.0.0.1:18760`
- 启动命令：`PYTHONDONTWRITEBYTECODE=1 ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18760`
- PID：`17626`
- 结果：已启动并已停止
- smoke 结束后：`127.0.0.1:18760` 无监听

前端：

- 地址：`127.0.0.1:18761`
- 启动命令：`PYTHONDONTWRITEBYTECODE=1 TDOCSYS_BYPASS_LOGIN=1 TDOCSYS_PORT=18761 TDOCSYS_BACKEND_BASE_URL=http://127.0.0.1:18760 python app.py`
- PID：`17651`
- 结果：已启动并已停止
- smoke 结束后：`127.0.0.1:18761` 无监听

进程结论：

- 后端服务已停止。
- 前端服务已停止。
- smoke 结束后端口无监听。
- 未发现本步启动进程残留。

## 4. Interface Verification Result

Step 198 已验证以下接口：

- `GET /index` -> HTTP `200`
- `POST 127.0.0.1:18760/local-trial/preview-only` -> HTTP `200`
- `POST 127.0.0.1:18761/local-trial/preview-only` -> HTTP `200`

接口结论：

- 后端 preview-only route 可达。
- 前端端口 `/local-trial/preview-only` 可达。
- 前端同源 proxy 可将请求转发至后端 preview-only route。

## 5. Core Result

Step 198 核心结论：

- 前端端口 `/local-trial/preview-only` 可达。
- 同源 proxy 成立。
- Step 193 的前端同源 HTTP `404` 已修复为 HTTP `200`。
- 前端 `fetch("/local-trial/preview-only")` 已能通过前端端口 `18761` 同源 proxy 动态加载后端 preview-only 数据。

## 6. Frontend Dynamic Display Result

Step 198 通过本地浏览器访问：

- `http://127.0.0.1:18761/index`

并点击页面中的 preview-only 加载按钮，仅触发：

- `fetch("/local-trial/preview-only")`

前端动态展示结果：

- `preview_packet` 展示成功。
- `validator_result` 展示成功。
- `blocked_reasons` 展示成功。
- `generate_called=false` 展示成功。
- `export_docx_called=false` 展示成功。
- `review_apply_called=false` 展示成功。
- `zbid_writeback_called=false` 展示成功。
- `output_job_export_written=false` 展示成功。

动态展示的 `blocked_reasons` 包含：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

页面状态显示：

- `preview-only metadata 已加载；结果仅供人工核查，不是 evidence，不是正式正文。`

## 7. Output Isolation Result

Step 198 对 `output/job/export` 做了前后只读快照：

- 前置快照文件数：`0`
- 后置快照文件数：`0`
- 前后 diff：无差异

结论：

- 未写 `output/job/export`。
- 未生成 DOCX。
- 未生成正式 JSON / Markdown / job / export 产物。
- 未执行删除或清理。

## 8. Safety Boundary Result

Step 198 严格未发生：

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

## 9. Risk Conclusion

本次 smoke 未发现 high risk 写入或正式链触发。

风险与限制：

1. 本次仅验证本地双端口 preview-only 同源 proxy。
2. 本次不代表真实 ZDoc/ZBid 联调。
3. 本次不代表正式生成链已开放。
4. 本次不代表 DOCX 导出已开放。
5. 本次不代表 review/apply 已开放。
6. 本次不代表 ZBid 写回已开放。
7. 本次不代表 50 人正式部署设计已启动。
8. 本次未运行 pytest。
9. 本次未验证 Ollama 或模型链路。

## 10. Next Step Recommendation

后续可进入 ZDoc 与 ZBid preview-only 对接前的接口边界梳理或授权请求。

建议下一步：

`ZDoc Step 200：ZDoc/ZBid preview-only integration boundary design`

建议性质：

- docs-only / design-only。
- 先梳理 ZDoc 与 ZBid preview-only 对接的接口边界、输入输出、blocked_reasons、formal flags 和 no-write 约束。
- 不直接进入真实 ZDoc/ZBid 联调。
- 不触发正式生成链。
- 不触发 DOCX 导出。
- 不触发 review/apply。
- 不触发 ZBid 写回。
- 不写 `output/job/export`。
- 不进入 50 人正式部署设计。

## 11. Safety Conclusion

Step 198 controlled smoke 已证明：

- 后端 `POST /local-trial/preview-only` 返回 HTTP `200`。
- 前端同源 `POST /local-trial/preview-only` 返回 HTTP `200`。
- Step 193 的前端同源 HTTP `404` 已修复为 HTTP `200`。
- 前端 `fetch("/local-trial/preview-only")` 已能通过同源 proxy 动态加载 preview-only 数据。
- 页面动态展示 `preview_packet`、`validator_result`、`blocked_reasons` 和五个正式链 false flags。
- 未触发正式链。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 服务均已停止。

当前系统仍未进入真实 ZDoc/ZBid 联调，正式生成、DOCX 导出、review/apply、ZBid 写回和 50 人正式部署设计仍未开放。
