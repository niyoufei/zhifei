# ZDoc Local Trial Authorized Smoke Dry-Run Command Plan

## 1. Scope

Step 157 仅设计 local trial authorized smoke dry-run command plan，不执行任何命令。

本文档用于设计未来在用户明确授权后才可执行的本地 smoke dry-run 命令计划，明确未来授权后的命令分组、执行顺序、授权边界、停止条件、no-write 检查、`output/job/export` 差异检查、进程停止要求和回报模板。

本步是 docs-only：

- 不执行命令。
- 不执行 smoke test。
- 不启动服务。
- 不启动后端服务。
- 不启动前端服务。
- 不运行 Ollama。
- 不运行 `ollama serve`。
- 不访问 `127.0.0.1:11434`。
- 不访问任何本地服务端口。
- 不调用外部模型/API。
- 不调用 ZBid。
- 不调用 ZBid API / 数据库 / 写回接口。
- 不写 `output/job/export`。
- 不触发 `/generate`、`/export_docx`、`/review/apply`。
- 不生成 DOCX 文件。
- 不生成 DOCX / JSON / Markdown 正式产物。
- 不进入 ZDoc / ZBid 实际联调。
- 不进入本地化部署执行。
- 不进入 50 人正式部署设计。

本文档不代表已经获得用户授权，不代表已经启动后端，不代表已经启动前端，不代表已经运行 Ollama，不代表已经访问本地端口，不代表已经执行 smoke test，不代表已经调用 ZBid，不代表已经写 `output/job/export`，不代表已经进入本地化部署执行，不代表已经进入 50 人团队正式部署设计。

文档中的所有命令只能作为“未来用户明确授权后可执行的命令占位”。本步不得执行这些命令。后续执行真实 smoke 前，必须先通过单独的授权请求获得用户明确同意。

授权必须列明：

- 允许启动哪些服务。
- 允许访问哪些端口。
- 允许执行哪些命令。
- 允许检查哪些目录。
- 停止条件。
- 回报模板。

当前所有正式链 flags 仍应保持 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

当前总体策略仍为：

- 先完成本地化部署基础闭环。
- 再完成 ZDoc 与 ZBid 的 preview-only 对接。
- 再进行小范围试用和问题修正。
- 最后再按约 50 人同时使用场景进行正式部署设计。

本步不得进入 Mac Studio / NAS / UPS / Redis / PostgreSQL / 50 人并发等正式部署设计。本步不得要求运行 full backend tests。Step 98B 已确认 `backend/tests` full suite 存在既有 collection/order import-isolation 问题。

## 2. Relationship To Runtime Authorization Gate

本文档必须受 Step 154 / Step 155 / Step 156 的 runtime authorization gate 约束。

必须明确：

- command plan 不等于授权。
- command placeholder 不等于执行。
- allowlist 不等于默认允许。
- 部分授权不得扩大解释。
- preview-only 不等于 writeback allowed。
- smoke dry-run 不等于 formal writeback dry-run。
- smoke dry-run 不等于正式 smoke test。
- 检查文档不等于执行命令。
- 设计命令计划不等于启动服务。
- 设计命令计划不等于访问本地端口。

未来任何真实运行行为都必须先通过 runtime authorization gate。授权必须逐项列明动作、目录、命令范围、端口范围、停止条件和回报内容。未授权、授权不清或授权与硬阻断项冲突时，必须停止并回报。

## 3. Authorization Prerequisites Before Real Execution

未来真正执行前，必须获得用户对以下事项的明确授权：

- 允许启动后端服务。
- 允许启动前端服务。
- 允许访问本地服务端口。
- 允许检查 Ollama。
- 允许访问 `127.0.0.1:11434`。
- 允许读取本地配置状态但不得打印敏感信息。
- 允许执行 preview-only 测试请求。
- 允许检查 `output/job/export` 差异。
- 允许生成 smoke report。
- 允许停止启动的本地服务。

未获得上述授权，不得执行。

授权请求必须包含：

- 本次拟执行动作。
- 当前目录。
- 当前分支。
- 当前 HEAD。
- 是否会启动后端服务。
- 是否会启动前端服务。
- 是否会访问本地端口。
- 是否会运行 Ollama。
- 是否会访问 `127.0.0.1:11434`。
- 是否会读取本地配置。
- 是否会写 `output/job/export`。
- 是否会触发 `/generate`。
- 是否会触发 `/export_docx`。
- 是否会触发 `/review/apply`。
- 是否会触发 ZBid 写回。
- 是否会调用 ZBid API / DB / writeback。
- 预计执行命令清单。
- 停止条件。
- 回报格式。
- 用户明确授权确认语。

模糊表达不得视为授权，例如“继续”“看一下”“试试看”“按计划执行”。部分授权不得扩大解释为完整 smoke test 授权。

## 4. Command Group Overview

未来 smoke dry-run 命令分组设计如下：

1. Git preflight group。
2. Environment preflight group。
3. Output isolation snapshot group。
4. Backend service dry-run group。
5. Frontend service dry-run group。
6. Ollama optional check group。
7. ZDoc preview-only packet group。
8. ZBid preview validator group。
9. Formal chain hard block group。
10. Output isolation diff group。
11. Service shutdown group。
12. Smoke report group。

本步只设计分组，不执行分组。未来执行必须按顺序推进，且任一高风险 stop condition 出现时必须立即停止，不得继续后续分组。

## 5. Git Preflight Command Placeholders

以下命令仅为未来命令占位。Step 157 不执行这些命令。

```bash
# FUTURE ONLY - do not run in Step 157.
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git tag --points-at HEAD
```

未来通过标准：

- `pwd` 必须为 `/Users/youfeini/Desktop/文档生成系统`。
- 当前分支必须为 `main`。
- HEAD 必须与授权请求中的 smoke baseline commit 一致。
- `git status --short` 必须为空。
- 当前 tag 或 baseline tag 必须在 smoke report 中明确记录。

未来停止条件：

- 当前目录错误。
- 当前分支不是 `main`。
- HEAD 与授权请求不一致。
- `git status --short` 非空。
- baseline tag 不明确且用户未授权继续。

## 6. Environment Preflight Command Placeholders

以下命令仅为未来命令占位。Step 157 不执行这些命令，不读取或修改 `.env`、local config、数据库、模型、缓存或运行时文件。

```bash
# FUTURE ONLY - do not run in Step 157.
python --version
node --version
pnpm --version
test -f .env && echo "LOCAL_ENV_PRESENT_UNCOMMITTED_CHECK_REQUIRED"
git status --short -- .env
```

未来检查项：

- Python 环境可重建。
- Node / pnpm 环境可重建。
- 本地 `.env` / local config 如存在，只能作为本机试用配置，不得提交。
- 不打印敏感配置。
- 不修改配置文件。
- 本地资料目录明确。
- 日志目录明确。
- no-write flag 默认开启。
- preview-only flag 默认开启。
- DOCX export flag 默认关闭。
- ZBid writeback flag 默认关闭。
- review/apply flag 默认关闭。
- formal writeback flag 默认关闭。

未来停止条件：

- `.env` / local config 出现在待提交变更中。
- 配置显示正式写回、DOCX export、ZBid writeback、review/apply 或 output write 默认开启。
- 配置缺少 preview-only / no-write 试用边界。
- 任何命令打印敏感配置。

## 7. Output Isolation Snapshot Group

以下命令仅为未来命令占位。Step 157 不执行这些命令，不写 `output/job/export`。

```bash
# FUTURE ONLY - do not run in Step 157.
find output/job/export -type f 2>/dev/null | sort
find output/job/export -type f 2>/dev/null | wc -l
find backend/data/autoplan/jobs -type f 2>/dev/null | wc -l
find build -type f 2>/dev/null | wc -l
```

未来检查项：

- smoke 前记录 `output/job/export` 文件列表和文件数。
- smoke 前记录 job / build 等运行目录文件数。
- 记录结果只用于后续差异对比。
- 不写入 `output/job/export`。
- 不生成替代性正式产物。

未来停止条件：

- baseline 记录命令本身造成写入。
- `output/job/export` 中已存在未解释的正式产物且用户未授权继续。
- baseline 无法记录且后续无法做 no-write 差异判断。

## 8. Backend Service Dry-Run Group

以下命令仅为未来命令占位。Step 157 不启动后端服务，不访问任何本地端口。

```bash
# FUTURE ONLY - do not run in Step 157.
# Start backend in preview-only / no-write mode with the approved local command.
# <backend-start-command-placeholder>

# FUTURE ONLY - do not run in Step 157.
# Record backend PID or process handle for later shutdown.
# <backend-pid-record-placeholder>

# FUTURE ONLY - do not run in Step 157.
# Read backend health endpoint only after backend startup is explicitly approved.
# <backend-health-check-command-placeholder>
```

未来检查项：

- 后端启动必须单独授权。
- 后端启动命令必须在授权请求中逐项列明。
- 后端启动后必须记录 PID 或停止方式。
- 健康检查可读。
- 配置加载可读。
- no-write 状态可读。
- preview-only 状态可读。
- ZBid writeback 默认 blocked。
- DOCX export 默认 blocked。
- review/apply 默认 blocked。
- formal writeback 默认 blocked。
- 错误返回包含 `blocked_reasons`。
- 日志记录 `request_id`。

未来停止条件：

- 后端启动失败。
- 健康检查不可读。
- 后端 PID 或停止方式不明确。
- no-write / preview-only 状态不可读。
- 任一正式链 flag 为 true。
- 错误缺少 `blocked_reasons`。
- 后端启动检查触发正式生成、正式写回、DOCX 导出、review/apply 或 ZBid 写回。
- 出现未授权服务或未知后台进程。

## 9. Frontend Service Dry-Run Group

以下命令仅为未来命令占位。Step 157 不启动前端服务，不访问任何本地端口。

```bash
# FUTURE ONLY - do not run in Step 157.
# Check frontend dependencies only after explicit authorization.
# <frontend-dependency-check-placeholder>

# FUTURE ONLY - do not run in Step 157.
# Start frontend with the approved local command.
# <frontend-start-command-placeholder>

# FUTURE ONLY - do not run in Step 157.
# Record frontend PID or process handle for later shutdown.
# <frontend-pid-record-placeholder>

# FUTURE ONLY - do not run in Step 157.
# Open or check frontend URL only after frontend startup is explicitly approved.
# <frontend-access-check-command-placeholder>
```

未来检查项：

- 前端启动必须单独授权。
- 前端启动命令必须在授权请求中逐项列明。
- 前端启动后必须记录 PID 或停止方式。
- 页面可访问。
- 本地模型状态只读显示。
- preview-only 结果展示为预览。
- `blocked_reasons` 可读。
- DOCX / ZBid / review/apply / formal writeback 按钮默认禁用或提示未开放。
- 用户不得误认为 preview 已写回。
- 用户不得误认为 advisory 是 evidence。
- 用户不得误认为 accepted preview 已经进入正式正文。
- 用户不得误认为 ZBid preview scoring 可作为 evidence。

未来停止条件：

- 前端启动失败。
- 页面不可访问。
- 前端 PID 或停止方式不明确。
- preview 被误显示为正式正文。
- advisory 被显示为 evidence。
- 正式链按钮可执行且未 blocked。
- UI 不显示 `blocked_reasons`。
- 出现未授权服务或未知后台进程。

## 10. Ollama Optional Check Group

以下命令仅为未来命令占位。Step 157 不运行 Ollama，不运行 `ollama serve`，不访问 `127.0.0.1:11434`。

```bash
# FUTURE ONLY - do not run in Step 157.
# Optional local model availability check only after explicit authorization.
# <ollama-version-command-placeholder>
# <ollama-list-command-placeholder>
# <ollama-127-0-0-1-11434-health-check-placeholder>
```

未来检查项：

- Ollama 检查为可选。
- 运行 `ollama serve` 必须单独授权。
- 访问 `127.0.0.1:11434` 必须单独授权。
- 模型列表可读时，仅用于状态显示。
- 模型不可用时进入 fallback。
- 模型不可用不得自动下载。
- 模型不可用不得自动拉取。
- 模型不可用不得写回。
- 模型输出不得作为 evidence。
- `thinking_only_fallback` 不得作为正式正文能力。
- 模型失败不得触发 DOCX / ZBid / review/apply / formal writeback。
- 模型输出不得自动进入 ZBid scoring。

未来停止条件：

- Ollama 检查触发模型下载或拉取。
- Ollama 检查触发正式生成。
- 模型输出被作为 evidence。
- 模型失败后仍触发写回、导出、review/apply 或 ZBid 请求。
- 未授权访问 `127.0.0.1:11434`。

## 11. ZDoc Preview-Only Packet Group

以下命令仅为未来命令占位。Step 157 不触发 `/generate`，不进入正式正文生成链，不生成真实 candidate patch。

```bash
# FUTURE ONLY - do not run in Step 157.
# Generate or inspect preview-only metadata packet through the approved future smoke route.
# <zdoc-preview-only-packet-command-placeholder>
```

未来检查项：

- preview packet 包含 `integration_request_id`。
- `project_id` / `document_id` / `section_id` 完整。
- `section_hash` / `section_version` 完整。
- `tender_file_refs` 存在。
- `scoring_clause_refs` 存在。
- `evidence_anchor_refs` 存在。
- `response_mode` 明确。
- `input_risk_level` 明确。
- `advisory_quality_gate_status` 明确。
- `blocked_reasons` 可读。
- `preview_advisory_summary` 只作为提示性 preview 字段。
- `shadow_candidate_id`、`patch_id`、`diff_preview_id`、`rollback_plan_id`、`dry_run_id` 仅作为追踪字段。
- 正式链 flags 恒 false。

未来停止条件：

- preview packet 缺少关键审计字段。
- evidence anchor 缺失但未 blocked。
- scoring refs 缺失但未 blocked 或未 `requires_human_review`。
- preview advisory 被当作 evidence。
- shadow / patch / diff / rollback / dry-run 被当作 evidence。
- preview packet 触发正式正文生成链。
- 任一正式链 flag 为 true。

## 12. ZBid Preview Validator Group

以下命令仅为未来命令占位。Step 157 不调用 ZBid，不访问 ZBid 数据库，不调用 ZBid 写回接口。

```bash
# FUTURE ONLY - do not run in Step 157.
# Validate fake preview packet through approved future smoke route or local fake validator path.
# <zbid-preview-input-validator-command-placeholder>
```

未来检查项：

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
- `zbid_writeback_allowed=false`。
- `docx_export_allowed=false`。
- `review_apply_allowed=false`。
- `formal_writeback_allowed=false`。
- `output_write_allowed=false`。

未来停止条件：

- validator 接受不安全输入。
- validator 将 preview advisory、shadow candidate、patch、diff、rollback 或 dry-run 视为 evidence。
- `accepted_preview_only` 打开任何正式链 flag。
- validator 触发 ZBid API / DB / writeback。
- validator 触发 DOCX export、review/apply 或 formal writeback。

## 13. Formal Chain Hard Block Group

以下命令仅为未来命令占位。Step 157 不触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回或 formal writeback。

```bash
# FUTURE ONLY - do not run in Step 157.
# Verify blocked behavior through approved future smoke route only.
# <generate-formal-block-check-placeholder>
# <export-docx-block-check-placeholder>
# <review-apply-block-check-placeholder>
# <zbid-writeback-block-check-placeholder>
# <formal-writeback-block-check-placeholder>
# <output-write-block-check-placeholder>
```

未来阻断项：

- `/generate` 正式生成必须 blocked。
- `/export_docx` 请求必须 blocked。
- DOCX 文件不得生成。
- `/review/apply` 请求必须 blocked。
- ZBid writeback 请求必须 blocked。
- ZBid API / DB / writeback 不得调用。
- formal writeback 请求必须 blocked。
- `output/job/export` 写入必须 blocked。
- dry-run passed 不得开放 formal writeback。
- source hash matched 不得开放 formal writeback。
- DOCX isolation passed 不得开放 ZBid。
- ZBid isolation passed 不得开放 ZBid writeback。

未来停止条件：

- `/generate` 未 blocked。
- `/export_docx` 未 blocked。
- DOCX 文件生成。
- `/review/apply` 未 blocked。
- ZBid writeback 未 blocked。
- ZBid API / DB / writeback 被调用。
- formal writeback 未 blocked。
- `output/job/export` 出现写入。
- 任一正式链 flag 为 true。

## 14. Output Isolation Diff Group

以下命令仅为未来命令占位。Step 157 不执行这些命令，不写 `output/job/export`。

```bash
# FUTURE ONLY - do not run in Step 157.
find output/job/export -type f 2>/dev/null | sort
find output/job/export -type f 2>/dev/null | wc -l
find backend/data/autoplan/jobs -type f 2>/dev/null | wc -l
find build -type f 2>/dev/null | wc -l
```

未来检查项：

- smoke 后再次记录 `output/job/export` 文件列表和文件数。
- smoke 后再次记录 job / build 等运行目录文件数。
- 与 baseline snapshot 比较。
- 必须记录差异。
- 未授权写入不得出现。

未来停止条件：

- `output/job/export` 出现新增文件。
- 出现 DOCX / JSON / Markdown 正式产物。
- 出现 job / export 状态文件。
- 出现无法解释的 build / job / output 变化。
- 输出差异无法记录。

## 15. Service Shutdown Group

以下命令仅为未来命令占位。Step 157 不启动服务，也不停止任何服务。

```bash
# FUTURE ONLY - do not run in Step 157.
# Stop only services that were explicitly authorized and started in the same smoke run.
# <backend-stop-command-placeholder>
# <frontend-stop-command-placeholder>

# FUTURE ONLY - do not run in Step 157.
# Verify started service processes and authorized ports are released.
# <started-process-release-check-placeholder>
# <authorized-port-release-check-placeholder>
```

未来要求：

- 只停止本次授权并启动的服务。
- 不停止未知服务。
- 不停止用户未授权管理的进程。
- 后端服务必须停止并记录状态。
- 前端服务必须停止并记录状态。
- 若本次授权启动了 `ollama serve`，必须按授权范围停止并记录状态。
- 不得后台遗留未知进程。
- 不得留下未知端口监听。

未来停止条件：

- 后端无法停止。
- 前端无法停止。
- 授权启动的 Ollama 无法停止。
- unknown process 持续运行。
- 端口释放状态不明确。
- 停止命令范围超过授权。

## 16. Smoke Report Group

以下为未来 smoke dry-run report 模板。Step 157 不生成真实 smoke report。

```text
ZDoc Local Trial Authorized Smoke Dry-Run Report

1. 授权范围：
2. 实际执行命令：
3. smoke baseline commit：
4. smoke baseline tag：
5. 当前目录：
6. 当前分支：
7. 开始前 HEAD：
8. 结束后 HEAD：
9. git status --short：
10. local config committed：yes/no
11. 是否启动后端：
12. 后端 PID 或停止状态：
13. 后端健康检查：passed/failed/not-run
14. 是否启动前端：
15. 前端 PID 或停止状态：
16. 前端访问检查：passed/failed/not-run
17. 是否运行 Ollama：
18. 是否访问 127.0.0.1:11434：
19. Ollama optional check：passed/failed/not-run/fallback
20. 是否访问其他本地端口：
21. ZDoc preview-only packet：passed/failed/not-run
22. ZBid preview validator：passed/failed/not-run
23. DOCX export blocked：yes/no/not-run
24. review/apply blocked：yes/no/not-run
25. ZBid writeback blocked：yes/no/not-run
26. formal writeback blocked：yes/no/not-run
27. output/job/export before count：
28. output/job/export after count：
29. output/job/export diff：
30. 是否写 output/job/export：
31. 是否触发 /generate：
32. 是否触发 /export_docx：
33. 是否生成 DOCX：
34. 是否触发 /review/apply：
35. 是否触发 ZBid 写回：
36. 是否调用 ZBid API / DB / writeback：
37. formal_writeback_allowed 是否恒 false：
38. review_apply_allowed 是否恒 false：
39. docx_export_allowed 是否恒 false：
40. zbid_writeback_allowed 是否恒 false：
41. output_write_allowed 是否恒 false：
42. blocked_reasons 是否可读：
43. evidence/scoring boundary status：
44. 是否停止所有启动进程：
45. stop condition 是否触发：
46. 失败项：
47. 风险说明：
48. 下一步建议：
```

未来 smoke report 必须明确区分 `passed`、`failed`、`not-run` 和 `fallback`。未执行项必须标记为 `not-run`，不得标记为通过。fallback 项必须标记为 `fallback`，不得标记为通过。

## 17. Stop Conditions

未来执行中出现以下情况必须立即停止：

- 当前目录错误。
- 分支错误。
- HEAD 不一致。
- `git status --short` 非 clean。
- 未授权动作出现。
- 任一正式链 flag 为 true。
- `output/job/export` 出现写入。
- DOCX 文件生成。
- `/generate` 被触发。
- `/export_docx` 被触发。
- `/review/apply` 被触发。
- ZBid 写回被触发。
- ZBid API / DB / writeback 被调用。
- formal writeback 被触发。
- 本地服务无法停止。
- unknown process 持续运行。
- `blocked_reasons` 缺失。
- advisory 被作为 evidence。
- preview 被误显示为正式正文。
- ZBid scoring preview 被作为 evidence。
- source hash / version mismatch 未 blocked。
- 出现未知写回风险。
- 停止命令范围超过授权。
- smoke report 无法区分 `passed`、`failed`、`not-run` 和 `fallback`。

停止后必须记录 stop reason、最后一个安全检查点、已执行命令、未执行命令、是否存在文件写入、是否仍有进程需要人工处理。

## 18. No-Write Assertions

未来 smoke dry-run 必须验证以下 no-write 断言：

- smoke 前记录 `output/job/export` 状态。
- smoke 后比对 `output/job/export` 状态。
- 任一新增文件必须 stop。
- 任一 DOCX / JSON / Markdown 正式产物必须 stop。
- 任一 job / export 状态文件必须 stop。
- 任一 formal flag 为 true 必须 stop。
- 任一写回请求未 blocked 必须 stop。
- 任一 `/generate`、`/export_docx`、`/review/apply` 或 ZBid writeback 触发必须 stop。

未来可授权的记录方式只应观察文件数量、路径差异和是否存在正式产物，不得写入 `output/job/export`，不得生成替代性正式产物。

## 19. Risk Boundary

本计划只面向未来用户明确授权后的本地 smoke dry-run，不面向正式部署设计。

边界如下：

- 不验证高并发。
- 不验证 50 人同时使用。
- 不设计 Mac Studio / NAS / UPS / Redis / PostgreSQL。
- 不开放 formal writeback。
- 不开放 review/apply。
- 不开放 DOCX export。
- 不开放 ZBid writeback。
- 不开放 output write。
- 不把 preview-only 结果当作正式正文。
- 不把 advisory、preview、AI 建议或 ZBid scoring preview 当作 evidence。
- 不把 fake helper 或 fake validator 当作真实运行时集成能力。
- 不要求运行 full backend tests。

Step 98B 已确认 `backend/tests` full suite 存在既有 collection/order import-isolation 问题。未来 smoke dry-run 不得为了 full-suite 既有问题擅自修改生产代码或既有 tests。

## 20. Future Authorization Request Template

未来如需进入真实 smoke dry-run，必须先向用户提交授权请求：

```text
ZDoc Local Trial Authorized Smoke Dry-Run Request

1. 本次拟执行动作：
2. 当前目录：
3. 当前分支：
4. 当前 HEAD：
5. 是否会启动后端服务：
6. 是否会启动前端服务：
7. 是否会访问本地端口：
8. 是否会访问 127.0.0.1:11434：
9. 是否会检查 Ollama：
10. 是否会读取本地配置状态：
11. 是否会打印敏感配置：
12. 是否会执行 preview-only 测试请求：
13. 是否会检查 output/job/export 差异：
14. 是否会生成 smoke report：
15. 是否会写 output/job/export：
16. 是否会触发 /generate：
17. 是否会触发 /export_docx：
18. 是否会触发 /review/apply：
19. 是否会触发 ZBid 写回：
20. 是否会调用 ZBid API / DB / writeback：
21. 预计执行命令清单：
22. 预计访问端口清单：
23. 预计启动进程清单：
24. 停止命令：
25. stop conditions：
26. 回报模板：
27. 用户明确授权确认语：
```

未获得用户明确授权，不得执行。授权确认语必须包含授权动作和边界，不得使用“继续”“试试看”等模糊表达。

## 21. Recommended Next Step

建议下一步为：

ZDoc Step 158：first real smoke authorization request，authorization-only。

Step 158 不得在未获得用户明确授权前启动服务、运行 Ollama、访问本地端口、执行 smoke test、调用 ZBid 或写 `output/job/export`。Step 158 应先提交授权请求，等待用户确认授权范围。

## 22. Safety Conclusion

Step 157 仅完成 local trial authorized smoke dry-run command plan design，不代表已经获得用户授权，不代表已经启动服务，不代表已经运行 Ollama，不代表已经访问本地端口，不代表已经执行 smoke test，不代表已经调用 ZBid，不代表已经写 `output/job/export`，不代表已经进入本地化部署执行，不代表已经进入 50 人团队正式部署设计。

当前系统仍处于 preview-only / no-write 的设计与 fake metadata 固化阶段。任何真实运行行为仍必须获得用户逐项明确授权。
