# ZDoc Frontend No-Write UI Screenshot Visual Smoke Stage Review

## 1. Scope

本文档仅复盘归档 Step 177：frontend no-write UI screenshot visual smoke execution 的执行结果、截图归档、UI 检查结论、严格未发生事项、output/job/export 差异和后续推进条件。

Step 178 为 docs-only stage review。本步不修改代码，不修改 tests，不修改 frontend，不修改既有 docs，不运行 pytest，不启动后端或前端服务，不运行 Ollama，不访问本地端口，不截图，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不生成 DOCX，不写 `output/job/export`，不进入本地化部署执行，也不进入 50 人团队正式部署设计。

## 2. Step 177 Execution Summary

Step 177 在用户明确授权范围内执行前端 no-write UI 截图级 visual smoke，授权范围包括启动后端和前端、访问本地页面、生成页面截图、保存截图到仓库外临时目录，并停止本步启动的服务。

执行摘要如下：

- 后端启动地址：`127.0.0.1:18760`。
- 后端启动命令：`ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18760`。
- 后端 PID：`70866`。
- 后端 `/health` 返回 OK：
  - HTTP 200
  - `ok=true`
  - `service=文档生成系统`
  - `version=autoplan-0.1.0`
- `/local-llm/preview-safe` 返回 no-write / preview-only 安全字段：
  - `ok=true`
  - `enabled=true`
  - `status=ok`
  - `preview_only=true`
  - `no_write=true`
  - `affects_generation=false`
  - `affects_export=false`
  - `affects_zbid_writeback=false`
  - `calls_generate_route=false`
  - `calls_export_docx_route=false`
  - `calls_review_apply_route=false`
  - `triggers_generation_chain=false`
  - `triggers_export_chain=false`
  - `writes_output=false`
  - `writes_job=false`
  - `writes_export=false`
  - `calls_ollama=false`
  - `calls_external_model_api=false`
  - `downloads_models=false`
  - `pulls_models=false`
  - `request_id=step-177-screenshot-smoke`
- 前端启动地址：`127.0.0.1:18761`。
- 前端启动命令：`TDOCSYS_PORT=18761 python frontend_web/app.py`。
- 前端 PID：`70919`。
- 前端 `/` 跳转到 `/index`，`/index` 返回 200。
- 截图路径：`/tmp/zdoc-step177-frontend-no-write-ui-smoke/frontend-no-write-ui.png`。
- 截图大小：`611353` bytes。
- 后端服务已停止，`127.0.0.1:18760` 无监听。
- 前端服务已停止，`127.0.0.1:18761` 无监听。

Step 177 未执行提交、打 tag 或 push；本复盘仅归档其运行观察结果。

## 3. UI Screenshot-Level Verification Result

Step 177 通过 Safari + macOS `screencapture` 生成页面截图，并结合本地页面 GET、DOM/HTML 解析和 CSS 可达性检查完成截图级 visual smoke。检查结果如下：

- 页面可访问，`/index` HTTP status 为 200。
- `preview-only` 可见。
- `no-write` 可见。
- `blocked_reasons` 可见。
- `AI advisory 不是 evidence` 可见。
- `preview 不是正式正文` 可见。
- “正式导出未开放”可见。
- “生成 Word 文档”不可提交正式生成。
- “正式导出未开放”按钮存在。
- 按钮 `disabled=true`。
- 按钮 `aria-disabled=true`。
- 按钮 `type=button`。
- `submit_word_button_count=0`。
- `generate_hidden_form_count=0`。
- DOCX 正式导出未开放提示可见。
- ZBid 写回未开放提示可见。
- review/apply 未开放提示可见。
- formal writeback 未开放提示可见。
- output/job/export 写入未开放提示可见。

本次未点击任何按钮，未提交任何表单。

## 4. Screenshot Artifact Result

Step 177 截图归档结果如下：

- 截图工具：Safari + macOS `screencapture`。
- 截图保存目录：`/tmp/zdoc-step177-frontend-no-write-ui-smoke`。
- 截图文件：`/tmp/zdoc-step177-frontend-no-write-ui-smoke/frontend-no-write-ui.png`。
- 文件大小：`611353` bytes。
- 截图保存位置为仓库外 `/tmp` 临时目录。
- 截图未保存到 `output/job/export`。
- 截图未提交到 git。
- 未安装新截图依赖。

截图用于本次 smoke 归档，不代表生成正式文档，不代表 DOCX 导出，也不代表任何正式链路已开放。

## 5. Strict Non-Occurrence Confirmation

Step 177 严格未发生以下事项：

- 未运行 Ollama。
- 未运行 `ollama serve`。
- 未访问 `127.0.0.1:11434`。
- 未调用外部模型/API。
- 未下载或拉取模型。
- 未调用模型生成。
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
- 未修改配置。
- 未修改部署脚本。
- 未执行 `git add` / `git commit` / `git tag` / `git push` / `git clean`。
- 未进入本地化部署执行。
- 未进入 50 人团队正式部署设计。

## 6. Output Isolation Result

Step 177 对 `output/job/export` 执行前后只读快照：

- 前置快照：空。
- 后置快照：空。
- 前后差异：无。

结论：

- 未写 `output/job/export`。
- 未生成 DOCX。
- 未出现正式 JSON / Markdown / DOCX 导出产物。
- 未出现 job/export 状态文件。

## 7. Process Shutdown Result

Step 177 启动并停止的进程如下：

- 后端命令：`ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18760`
- 后端 PID：`70866`
- 后端已停止。
- `127.0.0.1:18760` 无监听。

- 前端命令：`TDOCSYS_PORT=18761 python frontend_web/app.py`
- 前端 PID：`70919`
- 前端已停止。
- `127.0.0.1:18761` 无监听。

本次仅停止 Step 177 记录的后端和前端进程，未使用破坏性批量 kill。

## 8. Risk and Limitation Assessment

本次未发现 high risk。

已知限制如下：

1. 截图使用 Safari + macOS `screencapture`，截图包含浏览器窗口与页面展示状态。
2. 本次未安装新依赖。
3. 本次未点击任何按钮。
4. 本次未提交任何表单。
5. 本次未执行端到端业务交互。
6. 本次未验证真实 DOCX 导出链，因为该链仍禁止触发。
7. 本次未验证 ZBid 写回链，因为该链仍禁止触发。
8. 本次不代表本地化部署已完成。
9. 本次不代表 50 人团队正式部署能力已验证。

这些限制不影响本次截图级 visual smoke 的核心结论：页面截图、实际返回内容与 DOM 检查均显示 no-write / preview-only 边界提示已可见，且原“生成 Word 文档”入口未作为可提交正式生成按钮存在。

## 9. Safety Conclusion

Step 171 前端 no-write UI 修复已通过截图级 visual smoke。

本次确认：

- “生成 Word 文档”入口风险已受控。
- 页面未发现可提交正式生成按钮。
- 页面未发现 hidden `action=generate` 表单。
- “正式导出未开放”提示可见。
- “正式导出未开放”按钮为禁用状态。
- preview-only / no-write / blocked_reasons / evidence 边界提示已可见。
- DOCX / ZBid / review/apply / formal writeback / output write 未开放提示已可见。
- `output/job/export` 前后无差异。
- 后端和前端服务均已停止。

当前结论不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback、本地化部署或 50 人团队正式部署已经开放或实现。

## 10. Recommended Next Step

建议下一步为：

ZDoc Step 179：local trial preview-only route implementation plan design，docs-only。

Step 179 应仅设计 local trial preview-only route 的后续实现计划，不直接进入真实 ZDoc/ZBid 联调，不触发正式生成、DOCX 导出、review/apply 或 ZBid 写回，不写 `output/job/export`，不进入 50 人团队正式部署设计。
