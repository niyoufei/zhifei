# ZDoc Local Trial Preview-Only Route Runtime Smoke Authorization Request

## 1. Purpose

本文档用于起草 Step 184：preview-only route runtime smoke execution 的授权请求。本文档仅为 docs-only / authorization-request-only，不代表用户已经授权，不执行 runtime smoke，不启动后端服务，不启动前端服务，不运行 Ollama，不访问端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不生成 DOCX，不写 `output/job/export`，不进入真实 ZDoc/ZBid 联调，也不进入 50 人团队正式部署设计。

本授权请求的目的仅限于未来验证 Step 181 新增的本地试用专用 route 在真实后端服务中可访问：

- 验证 `/local-trial/preview-only` route 在真实后端服务中可访问。
- 验证 route 返回 `preview_only=true`。
- 验证 route 返回 `no_write=true`。
- 验证 `preview_packet` 可读。
- 验证 `validator_result` 可读。
- 验证 `blocked_reasons` 可读。
- 验证五个正式链 flags 恒 false。
- 验证 route 不触发正式生成、DOCX 导出、review/apply、ZBid 写回或 `output/job/export` 写入。

未收到用户后续明确授权前，不得执行 Step 184。

## 2. Current Baseline

当前基线如下：

- Step 181 已新增本地试用专用 preview-only route：`POST /local-trial/preview-only`。
- Step 181 route 只调用 fake preview packet helper。
- Step 181 route 只调用 fake ZBid preview input validator。
- Step 181 route 返回 `preview_packet`、`validator_result`、`blocked_reasons`、`preview_only=true`、`no_write=true`。
- Step 181 route 顶层、`preview_packet`、`validator_result` 均保持五个正式链 flags 为 false。
- Step 181 已通过 TestClient 层 route 测试，但尚未启动真实后端服务做 runtime smoke。
- Step 182 已完成 docs-only stage review，明确 route 未接入 frontend、未做真实 ZDoc/ZBid 联调、未开放正式链。

当前仍不代表本地化部署已完成，不代表真实 ZDoc/ZBid 联调已完成，不代表正式生成、DOCX 导出、review/apply、ZBid 写回或 formal writeback 已开放。

## 3. Requested Authorization Scope

未来 Step 184 如需执行 runtime smoke，拟申请用户逐项授权以下动作：

- 允许核验 Git 状态。
- 允许只读检查 `output/job/export` 前置快照。
- 允许启动后端服务。
- 允许访问本地后端端口。
- 允许检查 `/health`。
- 允许检查 `/local-llm/preview-safe`。
- 允许 POST `/local-trial/preview-only`。
- 允许只读检查 `/local-trial/preview-only` 返回字段。
- 允许只读检查 `output/job/export` 后置快照。
- 允许比对 `output/job/export` 前后差异。
- 允许停止本次启动的后端服务。
- 允许确认本次启动的后端端口无监听。

授权范围必须限于上述事项。部分授权不得扩大解释为允许正式生成、正式导出、正式写回、ZBid 调用、模型调用、前端启动或部署设计。

## 4. Explicitly Not Authorized

本授权请求不包含以下权限：

- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不生成 DOCX。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不调用 ZBid API / DB / writeback。
- 不执行 formal writeback。
- 不执行 formal writeback dry-run。
- 不运行 Ollama。
- 不运行 `ollama serve`。
- 不访问 `127.0.0.1:11434`。
- 不调用模型。
- 不调用外部模型/API。
- 不下载或拉取模型。
- 不写 `output/job/export`。
- 不启动前端服务。
- 不修改 source section。
- 不生成真实 candidate patch。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入本地化部署执行。
- 不进入 50 人团队正式部署设计。

## 5. Runtime Smoke Checklist

未来 Step 184 runtime smoke 应检查并归档：

- `/health` 返回 OK。
- `/local-llm/preview-safe` 返回 `no_write=true`。
- `/local-llm/preview-safe` 返回 `preview_only=true`。
- `/local-trial/preview-only` 返回 200。
- `/local-trial/preview-only` 返回 `preview_only=true`。
- `/local-trial/preview-only` 返回 `no_write=true`。
- `/local-trial/preview-only` 返回 `route_name=local_trial_preview_only`。
- `/local-trial/preview-only` 返回 `preview_packet`。
- `/local-trial/preview-only` 返回 `validator_result`。
- `/local-trial/preview-only` 返回可读 `blocked_reasons`。
- `formal_writeback_allowed=false`。
- `review_apply_allowed=false`。
- `docx_export_allowed=false`。
- `zbid_writeback_allowed=false`。
- `output_write_allowed=false`。
- `calls_generate_route=false`。
- `calls_export_docx_route=false`。
- `calls_review_apply_route=false`。
- `affects_zbid_writeback=false`。
- `writes_output=false`。
- `writes_job=false`。
- `writes_export=false`。
- `calls_ollama=false`。
- `calls_external_model_api=false`。
- `downloads_models=false`。
- `pulls_models=false`。
- `output/job/export` 前后无差异。
- 本次启动的后端服务可停止。

## 6. Proposed Runtime Smoke Command Groups

未来 Step 184 可在用户明确授权后按以下命令组执行。本步仅列出分组，不执行：

1. Git preflight group。
2. Output isolation pre-snapshot group。
3. Backend startup group。
4. `/health` check group。
5. `/local-llm/preview-safe` no-write check group。
6. `/local-trial/preview-only` route check group。
7. Output isolation post-snapshot group。
8. Backend shutdown group。
9. Runtime smoke report group。

所有命令必须在 Step 184 用户授权范围内执行。任何不在授权范围内的命令不得执行。

## 7. Hard Stop Conditions

未来执行中出现以下任一情况必须立即停止：

- 当前目录错误。
- 当前分支错误。
- HEAD 不一致。
- `git status --short` 非 clean。
- 后端启动失败且无可读错误。
- `/health` 不返回 OK。
- `/local-llm/preview-safe` 不返回 `no_write=true`。
- `/local-trial/preview-only` 非 200。
- `/local-trial/preview-only` 缺少 `preview_only=true`。
- `/local-trial/preview-only` 缺少 `no_write=true`。
- 缺少 `preview_packet`。
- 缺少 `validator_result`。
- 缺少可读 `blocked_reasons`。
- 任一正式链 flag 为 true。
- `calls_generate_route=true`。
- `calls_export_docx_route=true`。
- `calls_review_apply_route=true`。
- `affects_zbid_writeback=true`。
- `writes_output=true`。
- `writes_job=true`。
- `writes_export=true`。
- 出现 `output/job/export` 写入。
- 触发 `/generate`。
- 触发 `/export_docx`。
- 触发 `/review/apply`。
- 触发 ZBid 写回。
- 调用 ZBid API / DB / writeback。
- 生成 DOCX。
- 运行 Ollama 或访问 `127.0.0.1:11434`。
- 服务无法停止。
- 出现未知后端进程残留且无法解释。

## 8. Required Runtime Smoke Report Template

未来 Step 184 执行后应回报：

- 用户授权范围。
- 实际执行命令。
- 当前目录。
- 当前分支。
- 开始前 HEAD。
- 结束后 HEAD。
- `git status --short`。
- 后端启动命令。
- 后端 PID。
- 后端停止状态。
- `/health` 结果。
- `/local-llm/preview-safe` 结果。
- `/local-trial/preview-only` HTTP status。
- `/local-trial/preview-only` `preview_only` / `no_write` 结果。
- `preview_packet` 是否存在。
- `validator_result` 是否存在。
- `blocked_reasons` 是否可读。
- 五个正式链 flags 是否恒 false。
- `calls_generate_route` 是否 false。
- `calls_export_docx_route` 是否 false。
- `calls_review_apply_route` 是否 false。
- `affects_zbid_writeback` 是否 false。
- `writes_output` / `writes_job` / `writes_export` 是否 false。
- 是否触发 `/generate`。
- 是否触发 `/export_docx`。
- 是否生成 DOCX。
- 是否触发 `/review/apply`。
- 是否触发 ZBid 写回。
- 是否调用 ZBid API / DB / writeback。
- 是否运行 Ollama。
- 是否写 `output/job/export`。
- `output/job/export` 前后快照是否有差异。
- 是否停止所有启动进程。
- 风险说明。
- 下一步建议。

## 9. User Confirmation Wording

未来进入 Step 184 前，必须要求用户明确回复以下或等效授权语：

“我授权执行 Step 184 preview-only route runtime smoke，授权范围仅限 Step 183 授权请求文档列明事项；允许启动后端并访问 /health、/local-llm/preview-safe、/local-trial/preview-only；不得触发 /generate、/export_docx、/review/apply、ZBid 写回，不得生成 DOCX，不得写 output/job/export，不得运行 Ollama，不得进入 50 人正式部署设计。”

未收到上述或等效明确授权，不得执行 Step 184。

## 10. Next Step Recommendation

建议下一步为：

ZDoc Step 184：preview-only route runtime smoke execution，必须用户明确授权后才可执行。

如用户未明确授权，应停止，不得启动服务，不得访问端口，不得执行 route runtime smoke。

## 11. Safety Conclusion

Step 183 仅完成 `/local-trial/preview-only` route runtime smoke 授权请求文档，不代表已获得授权，不代表 runtime smoke 已执行，不代表后端服务已启动，不代表 route 已在真实服务中验证，也不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback、本地化部署或 50 人团队正式部署已经开放或实现。
