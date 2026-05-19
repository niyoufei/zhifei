# ZDoc Local Trial Smoke Execution Plan Design

## 1. Scope

Step 151 仅设计 local trial smoke execution plan，不执行 smoke test。

本文档用于设计未来本地小范围试用 smoke test 的执行计划，只定义未来 smoke test 的执行顺序、命令占位、前置条件、停止条件、回报格式、风险边界和人工验收标准。

本步是 docs-only：

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

本文档不代表本地化部署已执行，不代表后端服务已启动，不代表前端服务已启动，不代表 Ollama 已运行，不代表 ZDoc / ZBid 已实际联调，不代表 DOCX 导出、ZBid 写回、review/apply、formal writeback 已实现。

所有命令必须作为“未来执行占位”写入本文档，不得在 Step 151 执行。

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

## 2. Execution Strategy

未来 smoke test 的执行策略为顺序执行、单点停止、人工验收：

1. 先人工核验 Git 状态。
2. 再核验配置文件是否存在但不提交。
3. 再记录 `output/job/export` 等写入敏感目录的前置状态。
4. 再进行后端启动检查。
5. 再进行前端启动检查。
6. 再进行 Ollama 可选可达性检查。
7. 再进行 ZDoc preview-only 数据链检查。
8. 再进行 ZBid preview input validator 检查。
9. 再进行 DOCX / review/apply / ZBid / formal writeback 阻断检查。
10. 再记录 `output/job/export` 等写入敏感目录的后置状态。
11. 最后形成 smoke report。

任一高风险项失败必须立即停止，不得继续后续链路。高风险项包括正式链 flag 为 true、出现非预期写入、出现 ZBid API / DB / writeback 调用、出现 DOCX 文件、出现 `/review/apply` 调用、出现 `/generate` 正式生成、advisory 被当作 evidence、preview 被误显示为正式正文、source hash / version 不一致但未 blocked、缺少 `blocked_reasons`。

## 3. Preflight Command Placeholders

以下命令仅为未来执行占位。Step 151 不执行这些命令。

```bash
# FUTURE ONLY - do not run in Step 151.
pwd
git branch --show-current
git rev-parse HEAD
git status --short
```

未来通过标准：

- `pwd` 必须为 `/Users/youfeini/Desktop/文档生成系统`。
- branch 必须为 `main`。
- HEAD 必须与 smoke test 执行记录中的基准 commit 一致。
- `git status --short` 必须为空。

未来停止条件：

- 当前目录不正确。
- 当前分支不是 `main`。
- HEAD 与 smoke 基准不一致。
- 工作区不 clean。

## 4. Local Configuration Precheck Placeholders

以下命令仅为未来执行占位。Step 151 不执行这些命令，不读取或修改 `.env`、local config、数据库、模型、缓存或运行时文件。

```bash
# FUTURE ONLY - do not run in Step 151.
test -f .env && echo "LOCAL_ENV_PRESENT_UNCOMMITTED_CHECK_REQUIRED"
git status --short -- .env
python --version
node --version
pnpm --version
```

未来通过标准：

- 本地 `.env` / local config 如存在，只能作为本机试用配置，不得提交。
- Python 环境可重建。
- Node / pnpm 环境可重建。
- 项目资料目录已明确。
- 日志目录已明确。
- `output/job/export` 保持隔离。
- no-write flag 默认开启。
- preview-only flag 默认开启。
- DOCX export flag 默认关闭。
- ZBid writeback flag 默认关闭。
- review/apply flag 默认关闭。
- formal writeback flag 默认关闭。

未来停止条件：

- `.env` / local config 出现在待提交变更中。
- 配置显示正式写回、DOCX export、ZBid writeback、review/apply 或 output write 默认开启。
- 配置不支持 preview-only / no-write 试用。

## 5. Output And Runtime Baseline Placeholders

以下命令仅为未来执行占位。Step 151 不执行这些命令，不写 `output/job/export`。

```bash
# FUTURE ONLY - do not run in Step 151.
find output/job/export -type f 2>/dev/null | wc -l
find backend/data/autoplan/jobs -type f 2>/dev/null | wc -l
find build -type f 2>/dev/null | wc -l
```

未来通过标准：

- smoke test 前后应记录 `output/job/export` 文件数。
- smoke test 前后应记录 job / build 等运行目录文件数。
- preview-only smoke 不得造成 `output/job/export` 非预期写入。

未来停止条件：

- `output/job/export` 出现非预期新增文件。
- 试用链路生成 DOCX / JSON / Markdown 正式产物。
- 试用链路写入正式 job / build / export 产物。

## 6. Backend Startup Check Placeholders

以下命令仅为未来执行占位。Step 151 不启动后端服务，不访问任何本地端口。

```bash
# FUTURE ONLY - do not run in Step 151.
# Start backend in preview-only / no-write mode with the approved local command.
# <backend-start-command-placeholder>

# FUTURE ONLY - do not run in Step 151.
# Read backend health endpoint only after backend startup is explicitly approved.
# <backend-health-check-command-placeholder>
```

未来检查项：

- 后端可启动。
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
- no-write / preview-only 状态不可读。
- 任一正式链 flag 为 true。
- 错误缺少 `blocked_reasons`。
- 后端启动检查触发正式生成、正式写回、DOCX 导出或 ZBid 写回。

## 7. Frontend Startup Check Placeholders

以下命令仅为未来执行占位。Step 151 不启动前端服务，不访问任何本地端口。

```bash
# FUTURE ONLY - do not run in Step 151.
# Start frontend with the approved local command.
# <frontend-start-command-placeholder>

# FUTURE ONLY - do not run in Step 151.
# Open or check frontend URL only after frontend startup is explicitly approved.
# <frontend-access-check-command-placeholder>
```

未来检查项：

- 前端可启动。
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
- preview 被误显示为正式正文。
- advisory 被显示为 evidence。
- 正式链按钮可执行且未 blocked。
- UI 不显示 `blocked_reasons`。

## 8. Ollama Optional Availability Check Placeholders

以下命令仅为未来执行占位。Step 151 不运行 Ollama，不运行 `ollama serve`，不访问 `127.0.0.1:11434`。

```bash
# FUTURE ONLY - do not run in Step 151.
# Optional local model availability check only after explicit approval.
# <ollama-version-or-list-command-placeholder>
# <ollama-health-check-command-placeholder>
```

未来检查项：

- Ollama 仅作为可选服务检查。
- 本地模型列表可读时，仅用于状态显示。
- 模型不可用时进入 fallback。
- `thinking_only_fallback` 不得作为正式正文能力。
- 模型失败不得写回。
- 模型失败不得触发 DOCX / ZBid / review/apply。
- 模型失败不得触发 formal writeback。
- 模型输出不得作为 evidence。
- 模型输出不得自动进入 ZBid scoring。

未来停止条件：

- Ollama 检查触发模型下载或拉取。
- Ollama 检查触发正式生成。
- 模型输出被作为 evidence。
- 模型失败后仍触发写回、导出、review/apply 或 ZBid 请求。

## 9. ZDoc Preview-Only Data Chain Check Placeholders

以下命令仅为未来执行占位。Step 151 不触发 `/generate`，不进入正式正文生成链，不生成真实 candidate patch。

```bash
# FUTURE ONLY - do not run in Step 151.
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

## 10. ZBid Preview Input Validator Check Placeholders

以下命令仅为未来执行占位。Step 151 不调用 ZBid，不访问 ZBid 数据库，不调用 ZBid 写回接口。

```bash
# FUTURE ONLY - do not run in Step 151.
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
- `accepted_preview_only` 不得打开写回权限。
- `zbid_writeback_allowed=false`。

未来停止条件：

- validator 接受不安全输入。
- validator 将 preview advisory、shadow candidate、patch、diff、rollback 或 dry-run 视为 evidence。
- `accepted_preview_only` 打开任何正式链 flag。
- validator 触发 ZBid API / DB / writeback。

## 11. Formal Chain Block Check Placeholders

以下命令仅为未来执行占位。Step 151 不触发 `/export_docx`、`/review/apply`、ZBid 写回或 formal writeback。

```bash
# FUTURE ONLY - do not run in Step 151.
# Verify blocked behavior through approved future smoke route only.
# <export-docx-block-check-placeholder>
# <review-apply-block-check-placeholder>
# <zbid-writeback-block-check-placeholder>
# <formal-writeback-block-check-placeholder>
```

未来阻断项：

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

- `/export_docx` 未 blocked。
- DOCX 文件生成。
- `/review/apply` 未 blocked。
- ZBid writeback 未 blocked。
- ZBid API / DB / writeback 被调用。
- formal writeback 未 blocked。
- `output/job/export` 出现写入。
- 任一正式链 flag 为 true。

## 12. Evidence And Scoring Check Placeholders

以下命令仅为未来执行占位。Step 151 不读取真实正文计算 hash，不比较真实 source section 内容。

```bash
# FUTURE ONLY - do not run in Step 151.
# Inspect evidence and scoring metadata through approved future smoke report only.
# <evidence-and-scoring-metadata-check-placeholder>
```

未来检查项：

- `evidence_anchor_refs` 必须来源可验证资料。
- `scoring_clause_refs` 必须指向可验证评分条款。
- `tender_file_refs` 不等于自动 evidence。
- preview advisory 不得作为 evidence。
- ZBid scoring preview 不得作为 evidence。
- AI 建议不得作为 evidence。
- generated advisory 不得作为 evidence。
- shadow candidate 不得作为 evidence。
- patch preview 不得作为 evidence。
- diff preview 不得作为 evidence。
- rollback plan 不得作为 evidence。
- dry-run result 不得作为 evidence。
- 缺少 evidence 或评分条款必须 `requires_human_review` 或 blocked。
- 不得臆造评分条款。

未来停止条件：

- evidence anchor 不可验证。
- scoring clause refs 不可验证。
- generated / preview / model / scoring 内容被当作 evidence。
- 缺少 evidence 或评分条款但仍进入 accepted final path。

## 13. Smoke Report Template

未来 smoke test 完成后，应按以下模板回报。Step 151 不生成真实 smoke report。

```text
ZDoc Local Trial Smoke Report

1. smoke baseline commit:
2. smoke baseline tag:
3. current directory:
4. current branch:
5. git status --short:
6. local config committed: yes/no
7. backend startup: passed/failed/not-run
8. backend health: passed/failed/not-run
9. frontend startup: passed/failed/not-run
10. frontend access: passed/failed/not-run
11. Ollama optional check: passed/failed/not-run/fallback
12. ZDoc preview-only packet: passed/failed/not-run
13. ZBid preview validator: passed/failed/not-run
14. DOCX export blocked: yes/no
15. review/apply blocked: yes/no
16. ZBid writeback blocked: yes/no
17. formal writeback blocked: yes/no
18. output/job/export before count:
19. output/job/export after count:
20. DOCX generated: yes/no
21. ZBid API / DB / writeback called: yes/no
22. /generate triggered: yes/no
23. /export_docx triggered: yes/no
24. /review/apply triggered: yes/no
25. formal_writeback_allowed:
26. review_apply_allowed:
27. docx_export_allowed:
28. zbid_writeback_allowed:
29. output_write_allowed:
30. blocked_reasons observed:
31. evidence/scoring boundary status:
32. stop condition triggered:
33. operator notes:
34. final smoke decision: pass/fail/stop
```

未来 smoke report 必须明确区分 `passed`、`failed`、`not-run` 和 `fallback`，不得把未执行项写成通过。

## 14. Smoke Test Pass Criteria

未来 smoke test 通过标准：

- Git preflight 通过。
- 本地 config 未被提交。
- 后端可启动并可读健康状态。
- 前端可访问。
- Ollama 不可用时能够 fallback 且不写回。
- preview-only 数据链可产生。
- ZBid preview input validator 可阻断不安全输入。
- evidence / scoring 边界清楚。
- DOCX / ZBid / review/apply / formal writeback 默认 blocked。
- 所有正式链 flags 恒 false。
- `blocked_reasons` 可读。
- 未写 `output/job/export`。
- 未调用 ZBid。
- 未生成 DOCX。
- 未进入 50 人部署设计。

任一未执行项不得计入通过。所有通过结论必须有对应观察记录或命令输出。

## 15. Smoke Test Stop Criteria

未来 smoke test 中任一以下情况必须立即停止：

- 当前目录、分支、HEAD 或工作区状态不符合 smoke 基准。
- `.env` / local config 出现在待提交变更中。
- 任一正式链 flag 为 true。
- 出现 `output/job/export` 写入。
- 出现 DOCX 文件。
- 出现 ZBid API / DB / writeback 调用。
- 出现 `/review/apply` 调用。
- 出现 `/export_docx` 调用。
- 出现 `/generate` 正式生成。
- 出现 formal writeback。
- advisory 被作为 evidence。
- preview 被误显示为正式正文。
- ZBid scoring preview 被作为 evidence。
- source hash / version 不一致但未 blocked。
- 无 `blocked_reasons`。
- backend 或 frontend 失败后仍继续后续链路。
- Ollama 失败后仍触发写回、导出、review/apply 或 ZBid 请求。

停止后应记录 stop reason、最后一个安全检查点、已执行命令、未执行命令和是否存在文件写入。

## 16. Risk Boundary

本计划只面向未来本地小范围试用 smoke test，不面向正式部署设计。

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

Step 98B 已确认 `backend/tests` full suite 存在既有 collection/order import-isolation 问题。未来 smoke test 不得为了 full-suite 既有问题擅自修改生产代码或既有 tests。

## 17. Human Acceptance Checklist

未来人工验收应确认：

- smoke test 执行者理解本阶段为 preview-only / no-write。
- smoke report 中所有未执行项标记为 `not-run`，未冒充通过。
- backend / frontend / Ollama / ZDoc / ZBid 每一项都有明确 pass / fail / fallback / not-run。
- 所有 blocked 场景有 `blocked_reasons`。
- 所有正式链 flags 为 false。
- 无 DOCX 文件生成。
- 无 `output/job/export` 非预期写入。
- 无 ZBid API / DB / writeback 调用。
- 无 `/generate`、`/export_docx`、`/review/apply` 正式链触发。
- evidence 与 scoring 边界未被破坏。
- 若触发 stop criteria，已立即停止并记录。

人工验收通过不代表正式写回、DOCX 导出、ZBid 写回、review/apply 或 50 人部署已实现。

## 18. Recommended Next Step

建议下一步为：

ZDoc Step 152：local trial smoke execution plan fake schema tests，tests-only。

Step 152 不得启动服务，不得运行 Ollama，不得执行 smoke test，不得调用 ZBid，不得写 `output/job/export`，仅用 fake schema tests 固化 Step 151 的执行计划结构、命令占位、停止条件和回报模板。

## 19. Safety Conclusion

Step 151 仅完成 local trial smoke execution plan design，不代表本地化部署已执行，不代表后端服务已启动，不代表前端服务已启动，不代表 Ollama 已运行，不代表 ZDoc / ZBid 已实际联调，不代表 smoke test 已执行，不代表 DOCX 导出、ZBid 写回、review/apply、formal writeback 或 50 人团队正式部署已实现。
