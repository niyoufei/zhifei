# ZDoc Frontend No-Write UI Visual Smoke Stage Review

## 1. Scope

本文档仅复盘归档 Step 174：frontend no-write UI visual smoke execution 的执行结果、UI 检查结论、严格未发生事项、output/job/export 差异和后续推进条件。

Step 175 为 docs-only stage review。本步不修改代码，不修改 tests，不修改 frontend，不修改既有 docs，不运行 pytest，不启动后端或前端服务，不运行 Ollama，不访问本地端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不生成 DOCX，不写 `output/job/export`，不进入本地化部署执行，也不进入 50 人团队正式部署设计。

## 2. Step 174 Execution Summary

Step 174 在用户明确授权范围内执行前端 no-write UI visual smoke，执行摘要如下：

- 后端启动于 `127.0.0.1:18760`。
- 前端启动于 `127.0.0.1:18761`。
- 后端 `/health` 返回 OK：
  - HTTP 200
  - `ok=true`
  - `service=文档生成系统`
- `/local-llm/preview-safe` 返回 no-write / preview-only 安全字段：
  - `preview_only=true`
  - `no_write=true`
  - `calls_generate_route=false`
  - `calls_export_docx_route=false`
  - `calls_review_apply_route=false`
  - `affects_zbid_writeback=false`
  - `writes_output=false`
  - `writes_job=false`
  - `writes_export=false`
- 前端 `/index` 返回 200。
- 后端服务已停止，`127.0.0.1:18760` 无监听。
- 前端服务已停止，`127.0.0.1:18761` 无监听。

Step 174 未执行提交、打 tag 或 push；本复盘仅归档其运行观察结果。

## 3. UI Verification Result

Step 174 通过实际本地页面 GET、DOM/HTML 解析和 CSS 可达性检查完成 visual smoke。检查结果如下：

- 页面可访问，HTTP status 为 200。
- 未发现可提交正式生成按钮。
- `submit_word_button_count=0`。
- `generate_hidden_form_count=0`。
- “正式导出未开放”可见。
- “正式导出未开放”按钮存在。
- 按钮 `disabled=true`。
- 按钮 `aria-disabled=true`。
- 按钮 `type=button`。
- `preview-only` 可见。
- `no-write` 可见。
- `blocked_reasons` 可见。
- `AI advisory 不是 evidence` 可见。
- `preview 不是正式正文` 可见。
- DOCX 正式导出未开放提示可见。
- ZBid 写回未开放提示可见。
- review/apply 未开放提示可见。
- formal writeback 未开放提示可见。
- output/job/export 写入未开放提示可见。

本次未点击任何按钮，未提交任何表单。

## 4. Strict Non-Occurrence Confirmation

Step 174 严格未发生以下事项：

- 未运行 Ollama。
- 未运行 `ollama serve`。
- 未访问 `127.0.0.1:11434`。
- 未调用外部模型/API。
- 未下载或拉取模型。
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未调用 ZBid API / DB / writeback。
- 未执行 formal writeback。
- 未执行 formal writeback dry-run。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未修改代码。
- 未修改 tests。
- 未修改 docs。
- 未执行 `git add` / `git commit` / `git tag` / `git push`。
- 未进入本地化部署执行。
- 未进入 50 人团队正式部署设计。

## 5. Output Isolation Result

Step 174 对 `output/job/export` 执行前后只读快照：

- 前置快照：空。
- 后置快照：空。
- 前后差异：无。

结论：

- 未写 `output/job/export`。
- 未生成 DOCX。
- 未出现正式 JSON / Markdown / DOCX 导出产物。
- 未出现 job/export 状态文件。

## 6. Process Shutdown Result

Step 174 启动并停止的进程如下：

- 后端命令：`ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18760`
- 后端 PID：`65542`
- 后端已停止。
- `127.0.0.1:18760` 无监听。

- 前端命令：`TDOCSYS_PORT=18761 python frontend_web/app.py`
- 前端 PID：`65604`
- 前端已停止。
- `127.0.0.1:18761` 无监听。

本次仅停止 Step 174 记录的后端和前端进程，未使用破坏性批量 kill。

## 7. Risk and Limitation Assessment

本次未发现 high risk。

已知限制如下：

1. Playwright 不在当前 Node REPL 环境中，因此未生成浏览器截图。
2. 本次 visual smoke 基于实际本地页面 GET、DOM/HTML 解析和 CSS 可达性检查完成。
3. 本次未点击任何按钮。
4. 本次未提交任何表单。
5. 本次未执行端到端业务交互。
6. 本次未验证真实 DOCX 导出链，因为该链仍禁止触发。
7. 本次未验证 ZBid 写回链，因为该链仍禁止触发。

这些限制不影响本次 no-write UI visual smoke 的核心结论：页面实际返回内容中已包含 no-write / preview-only 边界提示，且原“生成 Word 文档”正式提交入口未作为可提交按钮存在。

## 8. Safety Conclusion

Step 171 前端 no-write UI 修复已通过首次 visual smoke。

本次确认：

- “生成 Word 文档”入口风险已在 UI 层得到控制。
- 页面未发现可提交正式生成按钮。
- 页面未发现 hidden `action=generate` 表单。
- “正式导出未开放”提示可见。
- preview-only / no-write / blocked_reasons / evidence 边界提示已可见。
- DOCX / ZBid / review/apply / formal writeback 未开放提示已可见。
- `output/job/export` 前后无差异。
- 后端和前端服务均已停止。

当前结论不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback、本地化部署或 50 人团队正式部署已经开放或实现。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 176：frontend no-write UI visual smoke screenshot authorization request，docs-only / authorization-request-only。

如果需要截图级归档，必须由用户单独授权后再执行。Step 176 仅起草截图级 visual smoke 授权请求，不得启动服务，不得访问端口，不得执行截图，不得触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不得写 `output/job/export`。
