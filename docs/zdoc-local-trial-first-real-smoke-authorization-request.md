# ZDoc Local Trial First Real Smoke Authorization Request

## 1. Purpose

Step 158 仅起草首次真实 local smoke test 授权请求，不执行任何命令。

本文档用于向用户提交首次真实 local smoke test 的授权请求草案。本文档是 docs-only / authorization-request-only：

- 不执行命令。
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
- 不执行 smoke test。
- 不进入 ZDoc / ZBid 实际联调。
- 不进入本地化部署执行。
- 不进入 50 人正式部署设计。

本文档不是授权本身。只有用户在后续明确回复授权，才可进入真实 smoke 执行步骤。不得把本授权请求文档视为用户已经授权。

用户授权必须逐项明确：

- 是否允许启动后端服务。
- 是否允许启动前端服务。
- 是否允许访问本地端口。
- 是否允许检查 Ollama。
- 是否允许访问 `127.0.0.1:11434`。
- 是否允许读取本地配置状态但不打印敏感内容。
- 是否允许执行 preview-only 测试请求。
- 是否允许检查 `output/job/export` 差异。
- 是否允许生成 smoke report。
- 是否允许停止启动的本地服务。

当前所有正式链 flags 仍必须保持 false：

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

## 2. Current Baseline

当前阶段已完成以下设计与 fake-only 固化工作：

- 已完成 local trial smoke checklist。
- 已完成 local trial smoke checklist fake schema tests。
- 已完成 local trial smoke execution plan。
- 已完成 local trial smoke execution plan fake schema tests。
- 已完成 local trial runtime authorization gate。
- 已完成 local trial runtime authorization gate fake schema tests。
- 已完成 local trial authorized smoke dry-run command plan。

当前仍未执行以下事项：

- 仍未执行真实 smoke test。
- 仍未启动后端服务。
- 仍未启动前端服务。
- 仍未运行 Ollama。
- 仍未访问 `127.0.0.1:11434`。
- 仍未访问任何本地服务端口。
- 仍未完成本地化部署执行。
- 仍未完成 ZDoc / ZBid 实际联调。
- 仍未完成正式写回。
- 仍未完成 DOCX 导出。
- 仍未完成 ZBid 写回。
- 仍未进入 50 人团队正式部署设计。

当前系统仍处于 preview-only / no-write 的设计与 fake metadata 固化阶段。

## 3. Authorization Request Summary

本次未来真实 smoke test 仅申请验证：

- 本地服务是否可启动。
- 后端健康状态是否可读。
- 前端页面是否可访问。
- Ollama 是否可选检查。
- preview-only 数据链是否可用。
- ZBid preview validator 是否可用。
- 所有正式链是否保持 blocked。
- `output/job/export` 是否无非授权写入。
- 启动的服务是否可停止。

该授权不包括：

- 正式生成。
- 正式导出。
- 正式写回。
- DOCX 正式导出。
- review/apply。
- ZBid 写回。
- ZBid API / DB / writeback。
- formal writeback。
- formal writeback dry-run。
- 50 人团队正式部署设计。

即使用户授权未来真实 smoke test，授权范围也仅限本文件第 4 节列明的事项。任何未列明动作均不得执行。

## 4. Requested Authorization Items

以下为未来执行 Step 159 前需要用户逐项确认的授权清单。

1. 允许核验 Git 状态：

   ```bash
   pwd
   git branch --show-current
   git rev-parse HEAD
   git status --short
   git tag --points-at HEAD
   ```

   目的仅限确认当前目录、分支、HEAD、工作区 clean 状态和 baseline tag。若目录、分支、HEAD 或工作区状态不符合授权基线，必须停止。

2. 允许检查本地环境版本：

   ```bash
   python --version
   node --version
   pnpm --version
   ```

   目的仅限确认 Python、Node、pnpm 环境状态。不得安装依赖，不得修改环境，不得写配置文件。

3. 允许检查本地配置状态：

   ```bash
   test -f .env && echo "LOCAL_ENV_PRESENT_UNCOMMITTED_CHECK_REQUIRED"
   git status --short -- .env
   ```

   目的仅限检查 `.env` / local config 是否存在以及是否被提交。不得打印敏感配置，不得提交配置文件，不得修改配置文件。

4. 允许记录 `output/job/export` smoke 前后差异：

   ```bash
   find output/job/export -type f 2>/dev/null | sort
   find output/job/export -type f 2>/dev/null | wc -l
   find backend/data/autoplan/jobs -type f 2>/dev/null | wc -l
   find build -type f 2>/dev/null | wc -l
   ```

   目的仅限只读检查和差异记录。不得创建目录，不得写文件，不得生成任何正式产物。

5. 允许启动后端服务：

   ```bash
   # Future only. Exact command must be confirmed before execution.
   # <backend-start-command-placeholder>
   # <backend-health-check-command-placeholder>
   # <backend-pid-record-placeholder>
   ```

   授权范围仅限健康检查和 no-write / preview-only 状态检查。不得启动正式写回 worker，不得启动正式导出 worker，不得触发 `/generate`，不得触发 `/export_docx`，不得触发 `/review/apply`，不得触发 ZBid 写回。检查结束后必须停止本次启动的后端服务，并记录 PID 或停止状态。

6. 允许启动前端服务：

   ```bash
   # Future only. Exact command must be confirmed before execution.
   # <frontend-start-command-placeholder>
   # <frontend-access-check-command-placeholder>
   # <frontend-pid-record-placeholder>
   ```

   授权范围仅限访问页面和 UI 状态检查。不得触发 DOCX / ZBid / review/apply / formal writeback。检查结束后必须停止本次启动的前端服务，并记录 PID 或停止状态。

7. 允许可选检查 Ollama：

   ```bash
   # Future only. Exact commands must be confirmed before execution.
   ollama list
   # <127-0-0-1-11434-api-tags-check-placeholder>
   ```

   目的仅限可选检查本地模型状态。可检查 `ollama list`，可检查 `127.0.0.1:11434/api/tags`。不得自动下载模型，不得自动拉取模型，不得将模型输出作为 evidence，不得让模型输出进入正式正文或 ZBid scoring。如需运行 `ollama serve`，必须另行明确授权。

8. 允许执行 preview-only 测试请求：

   ```bash
   # Future only. Exact route and payload must be confirmed before execution.
   # <zdoc-preview-only-packet-command-placeholder>
   # <zbid-preview-input-validator-command-placeholder>
   ```

   授权范围仅限检查 preview packet / validator / `blocked_reasons` / formal flags。不得触发正式生成，不得写回正文，不得写 `output/job/export`，不得调用真实 ZBid API，不得访问 ZBid DB，不得调用 ZBid 写回接口。

9. 允许生成 smoke report：

   授权范围仅限生成回报文本。不得生成 DOCX / JSON / Markdown 正式产物，不得写 `output/job/export`，不得把未执行项标记为通过。

10. 允许停止所有本次启动的本地服务：

    ```bash
    # Future only. Exact commands must be confirmed before execution.
    # <backend-stop-command-placeholder>
    # <frontend-stop-command-placeholder>
    # <started-process-release-check-placeholder>
    # <authorized-port-release-check-placeholder>
    ```

    授权范围仅限停止本次授权并启动的后端服务、前端服务。如另行授权启动 `ollama serve`，则按该授权停止或确认其状态。不得停止未知服务，不得停止用户未授权管理的进程。

## 5. Explicitly Not Authorized

本次授权请求不授权以下动作：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- ZBid API / DB / writeback
- DOCX 文件生成
- JSON / Markdown 正式导出
- `output/job/export` 写入
- formal writeback
- formal writeback dry-run
- 修改 source section
- 读取真实正文计算 hash
- 比较真实 source section 内容
- 真实 shadow generation implementation
- 真实 candidate patch 写入
- 正式正文生成链
- human approval UI
- approval persistence
- 真实 diff
- 真实 rollback
- review/apply isolation 执行
- DOCX isolation 执行
- ZBid isolation 执行
- 50 人正式部署设计
- Mac Studio / NAS / UPS / Redis / PostgreSQL 正式部署配置

如未来 smoke 过程中出现上述任一动作迹象，必须立即停止并回报。

## 6. Proposed Future Command Groups

未来获得用户明确授权后，命令组应按以下顺序执行：

1. Git preflight group。
2. Environment preflight group。
3. Output isolation snapshot group。
4. Backend service group。
5. Frontend service group。
6. Ollama optional check group。
7. ZDoc preview-only packet group。
8. ZBid preview validator group。
9. Formal chain hard block group。
10. Output isolation diff group。
11. Service shutdown group。
12. Smoke report group。

任一高风险项失败必须立即停止，不得继续后续命令组。任何命令组都不得扩大到未授权动作。

## 7. Hard Stop Conditions

未来执行中出现以下任一情况必须立即停止：

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
- formal writeback dry-run 被执行。
- 本地服务无法停止。
- unknown process 持续运行。
- `blocked_reasons` 缺失。
- advisory 被作为 evidence。
- preview 被误显示为正式正文。
- ZBid scoring preview 被作为 evidence。
- source hash / version mismatch 未 blocked。
- `output/job/export` 差异无法记录。
- smoke report 无法区分 `passed`、`failed`、`not-run` 和 `fallback`。

停止后必须记录 stop reason、最后一个安全检查点、已执行命令、未执行命令、是否存在文件写入、是否仍有进程需要人工处理。

## 8. Smoke Report Template

未来执行后的回报模板如下：

```text
ZDoc Local Trial First Real Smoke Report

1. 用户授权范围：
2. 实际执行命令：
3. 当前目录：
4. 当前分支：
5. 开始前 HEAD：
6. 结束后 HEAD：
7. git status --short：
8. baseline tag：
9. local config committed：yes/no
10. 是否启动后端：
11. 后端 PID 或停止状态：
12. 后端健康检查：passed/failed/not-run
13. 是否启动前端：
14. 前端 PID 或停止状态：
15. 前端访问检查：passed/failed/not-run
16. 是否运行 Ollama：
17. 是否访问 127.0.0.1:11434：
18. Ollama optional check：passed/failed/not-run/fallback
19. 是否访问其他本地端口：
20. 是否调用外部 API：
21. ZDoc preview-only packet：passed/failed/not-run
22. ZBid preview validator：passed/failed/not-run
23. 是否触发 /generate：
24. 是否触发 /export_docx：
25. 是否生成 DOCX：
26. 是否触发 /review/apply：
27. 是否触发 ZBid 写回：
28. 是否调用 ZBid API / DB / writeback：
29. 是否写 output/job/export：
30. output/job/export before count：
31. output/job/export after count：
32. output/job/export diff：
33. formal_writeback_allowed 是否恒 false：
34. review_apply_allowed 是否恒 false：
35. docx_export_allowed 是否恒 false：
36. zbid_writeback_allowed 是否恒 false：
37. output_write_allowed 是否恒 false：
38. blocked_reasons 是否可读：
39. evidence/scoring boundary status：
40. 是否停止所有启动进程：
41. stop condition 是否触发：
42. 失败项：
43. 风险说明：
44. 下一步建议：
```

未来 smoke report 必须明确区分 `passed`、`failed`、`not-run` 和 `fallback`。未执行项必须标记为 `not-run`，不得标记为通过。fallback 项必须标记为 `fallback`，不得标记为通过。

## 9. User Confirmation Wording

未来需要用户明确回复授权确认语。建议确认语如下：

```text
我授权执行 Step 159 首次真实 local smoke test，授权范围仅限本授权请求第 4 节列明事项；不得触发 /generate、/export_docx、/review/apply、ZBid 写回、正式写回，不得写 output/job/export，不得进入 50 人正式部署设计。
```

未收到上述或等效明确授权，不得执行 Step 159。模糊表达不得视为授权，例如“继续”“看一下”“试试看”“按计划执行”。

## 10. Next Step Recommendation

建议下一步为：

ZDoc Step 159：first real local smoke test execution，requires explicit user authorization。

Step 159 只有在用户明确授权后才能执行。如用户未授权，应停止，不得执行任何运行时动作。

## 11. Safety Conclusion

Step 158 仅完成首次真实 local smoke test 授权请求文档，不代表已获得授权，不代表 smoke test 已执行，不代表本地化部署、ZDoc / ZBid 实际联调、正式写回、DOCX 导出、ZBid 写回或 50 人部署已实现。

本授权请求不允许正式生成、DOCX 导出、review/apply、ZBid 写回、ZBid API / DB / writeback、formal writeback、formal writeback dry-run、写 `output/job/export` 或进入 50 人正式部署设计。

当前系统仍处于 preview-only / no-write 的设计与 fake metadata 固化阶段。任何真实运行行为仍必须获得用户逐项明确授权。
