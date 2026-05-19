# ZDoc Local Trial Runtime Authorization Gate Design

## 1. Scope

Step 154 仅设计 local trial runtime authorization gate，不执行任何运行时动作。

本文档用于设计未来进入真实 local trial smoke test 前的运行时授权门禁，明确未来哪些动作必须获得用户单独授权，哪些命令可在授权后执行，哪些命令始终禁止，如何停止、如何回报、如何判定越界。

本步是 docs-only：

- 不执行授权。
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

本文档不代表已授权启动后端，不代表已授权启动前端，不代表已授权运行 Ollama，不代表已授权访问本地端口，不代表已授权执行 smoke test，不代表已授权调用 ZBid，不代表已授权写 `output/job/export`，不代表已进入本地化部署执行，不代表已进入 50 人团队正式部署设计。

后续任何真实运行行为必须由用户明确授权，且授权范围必须逐项列明。

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

## 2. Authorization Principle

运行时授权原则：

- 默认禁止所有运行时动作。
- 所有运行时动作必须由用户单独授权。
- 授权必须明确动作、目录、命令范围、停止条件、回报内容。
- 未授权不得推断允许。
- 部分授权不得扩大解释。
- “检查文档”不等于“执行命令”。
- “设计 smoke plan”不等于“执行 smoke test”。
- “preview-only”不等于 `writeback_allowed=true`。
- “本地试用”不等于“本地化部署执行”。
- “Ollama 可选检查”不等于“运行 Ollama”或“下载模型”。
- “ZBid preview-only”不等于“调用真实 ZBid API / DB / writeback”。

任何授权都应是一次性、当前步骤限定、命令范围限定。授权过期、范围不清或与禁止项冲突时，必须停止并回报，不得继续执行。

## 3. Runtime Action Categories

### 3.1 Always Forbidden In Local Trial Without Separate Higher-Level Authorization

以下动作即使进入本地小范围试用阶段，也必须默认硬阻断，除非未来存在更高层级、单独明确、逐项列明的授权：

- 正式写回。
- formal writeback。
- formal writeback dry-run 作为写回准入。
- `/review/apply`。
- `/export_docx`。
- DOCX 正式导出。
- ZBid 正式写回。
- ZBid API / DB / writeback。
- `output/job/export` 写入。
- 生成 DOCX / JSON / Markdown 正式产物。
- 修改 source section。
- 读取真实正文计算 hash。
- 比较真实 source section 内容。
- 进入真实 shadow generation implementation。
- 生成真实 candidate patch。
- 进入正式正文生成链。
- 进入 50 人正式部署。
- 设计 Mac Studio / NAS / UPS / Redis / PostgreSQL / 50 人并发正式部署架构。
- 修改生产主链。
- 修改既有 tests 修复 full-suite 顺序问题。

### 3.2 Requires Explicit Smoke-Test Authorization

以下动作只有在未来真实 smoke test 阶段，且用户逐项明确授权后才可执行：

- 启动后端服务。
- 启动前端服务。
- 访问本地服务端口。
- 访问 `127.0.0.1:11434`。
- 检查 Ollama 可达性。
- 执行 preview-only 测试请求。
- 生成 smoke report。
- 检查 `output/job/export` 差异。
- 读取本地配置状态但不打印敏感值。
- 停止本地服务。

授权必须说明具体命令或命令类别、预计端口、是否会启动进程、如何停止、如何回报，以及触发哪些 stop conditions 时立即停止。

### 3.3 Allowed Only As Docs-Only Design In Current Stage

当前 Step 154 仅允许以下 docs-only 设计工作：

- 编写设计文档。
- 编写 future command placeholder。
- 设计授权模板。
- 设计 allowlist。
- 设计 hard block list。
- 设计 no-write assertion。
- 设计停止条件。
- 设计回报模板。
- 设计 fake schema tests 的未来验收条件。

当前阶段不得将上述设计内容解释为运行授权。

## 4. Authorization Request Template

未来向用户申请授权时，应使用以下模板。未获得用户明确授权，不得执行。

```text
ZDoc Local Trial Runtime Authorization Request

1. 拟执行动作：
2. 当前目录：
3. 当前分支：
4. 当前 HEAD：
5. 是否会启动后端服务：yes/no
6. 是否会启动前端服务：yes/no
7. 是否会访问本地端口：yes/no；端口：
8. 是否会运行 Ollama：yes/no
9. 是否会访问 127.0.0.1:11434：yes/no
10. 是否会读取本地配置：yes/no；是否打印敏感值：no
11. 是否会写 output/job/export：no
12. 是否会触发 /generate：no
13. 是否会触发 /export_docx：no
14. 是否会触发 /review/apply：no
15. 是否会触发 ZBid 写回：no
16. 是否会调用 ZBid API / DB / writeback：no
17. 预计执行命令清单：
18. 停止条件：
19. 回报格式：
20. 用户明确授权确认语：
```

用户确认语必须明确包含授权动作和边界。例如：“我授权本次只启动后端并访问健康检查端口，不授权 Ollama、ZBid、DOCX、review/apply、output/job/export 写入。”

模糊表达不得视为授权，例如“继续”“看一下”“试试看”“按计划执行”。

## 5. Authorized Command Allowlist Design

以下仅为未来 smoke 阶段可被授权的命令类别。allowlist 只是未来授权范围，不代表本步允许执行。

基础核验命令占位：

- `pwd`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`

环境核验命令占位：

- Python 版本检查。
- Node 版本检查。
- pnpm 版本检查。
- `.env` / local config 是否存在但不提交的检查。
- 本地资料目录检查。
- 日志目录检查。

服务与端口命令占位：

- 后端启动命令占位。
- 后端健康检查命令占位。
- 后端停止服务命令占位。
- 前端启动命令占位。
- 前端页面访问检查占位。
- 前端停止服务命令占位。
- Ollama 可选检查命令占位。

写入检测命令占位：

- smoke 前 `output/job/export` 状态记录。
- smoke 后 `output/job/export` 状态记录。
- job / build / export 目录差异检查。

任何命令只有在未来授权请求中逐项列明并获得用户明确授权后，才可执行。未列入授权请求的命令不得执行。

## 6. Runtime Hard Block List

即使进入 smoke 阶段，以下动作也默认硬阻断：

- `/generate` 正式生成。
- `/export_docx`。
- `/review/apply`。
- ZBid 写回。
- ZBid API / DB / writeback。
- `output/job/export` 写入。
- DOCX 文件生成。
- formal writeback。
- formal writeback dry-run 被解释为写回准入。
- `formal_writeback_allowed=true`。
- `review_apply_allowed=true`。
- `docx_export_allowed=true`。
- `zbid_writeback_allowed=true`。
- `output_write_allowed=true`。
- advisory 作为 evidence。
- preview 作为正式正文。
- ZBid scoring preview 作为 evidence。
- source hash mismatch 未 blocked。
- source version mismatch 未 blocked。
- `blocked_reasons` 缺失。

出现任一硬阻断项，必须立即停止并回报。

## 7. No-Write Runtime Assertion Design

未来 smoke 执行时必须验证 no-write 断言：

- smoke 前记录 `output/job/export` 状态。
- smoke 后比对 `output/job/export` 状态。
- 任一新增文件必须 stop。
- 任一 DOCX / JSON / Markdown 正式产物必须 stop。
- 任一 job / export 状态文件必须 stop。
- 任一 formal flag 为 true 必须 stop。
- 任一写回请求未 blocked 必须 stop。
- 任一 `/generate`、`/export_docx`、`/review/apply` 或 ZBid writeback 触发必须 stop。

未来可授权的记录方式只应观察文件数量、路径差异和是否存在正式产物，不得写入 `output/job/export`，不得生成替代性正式产物。

## 8. Service Startup Authorization Boundary

未来启动服务时的边界：

- 后端启动必须单独授权。
- 前端启动必须单独授权。
- 启动后必须有停止命令。
- 启动失败必须停止。
- 不得后台遗留未知进程。
- 不得启动非授权服务。
- 不得同时启动 ZBid 正式服务。
- 不得启动正式写回 worker。
- 不得启动正式导出 worker。
- 不得启动会写 `output/job/export` 的链路。

如果服务无法停止、PID 不明确、端口被未知进程占用，必须停止试用链路并回报，不得继续叠加启动命令。

## 9. Ollama Authorization Boundary

未来 Ollama 检查边界：

- Ollama 检查为可选。
- 运行 `ollama serve` 必须单独授权。
- 访问 `127.0.0.1:11434` 必须单独授权。
- 模型不可用不得自动下载。
- 模型不可用不得自动拉取。
- 模型不可用不得写回。
- 模型输出不得作为 evidence。
- `thinking_only_fallback` 不得作为正式正文能力。
- Ollama 检查不得触发 DOCX / ZBid / review/apply / formal writeback。

Ollama 不可用时，未来 smoke report 应记录 `fallback` 或 `not-run`，不得将未运行模型误报为通过。

## 10. ZDoc/ZBid Preview-Only Authorization Boundary

未来 preview-only 联调边界：

- 可测试 ZDoc preview packet。
- 可测试 ZBid preview validator。
- 可检查 preview-only metadata。
- 可检查 `blocked_reasons`。
- 不得调用真实 ZBid API。
- 不得访问 ZBid DB。
- 不得调用 ZBid 写回接口。
- 不得写回 ZBid。
- 不得把 ZBid scoring preview 作为 evidence。
- 不得把 `accepted_preview_only` 作为 writeback permission。
- `zbid_writeback_allowed` 必须 false。
- `formal_writeback_allowed` 必须 false。
- `review_apply_allowed` 必须 false。
- `docx_export_allowed` 必须 false。
- `output_write_allowed` 必须 false。

未来任何 ZDoc / ZBid preview-only 测试请求必须只验证 metadata-only / preview-only 边界，不得进入真实联调写回链。

## 11. Stop Conditions

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

停止后必须记录 stop reason、最后一个安全检查点、已执行命令、未执行命令、是否存在文件写入、是否仍有进程需要人工处理。

## 12. Required Runtime Report Template

未来运行后应使用以下回报模板：

```text
ZDoc Local Trial Runtime Authorization Report

1. 授权范围：
2. 实际执行命令：
3. 当前目录：
4. 当前分支：
5. 开始前 HEAD：
6. 结束后 HEAD：
7. git status --short：
8. 是否启动后端：
9. 后端 PID 或停止状态：
10. 是否启动前端：
11. 前端 PID 或停止状态：
12. 是否运行 Ollama：
13. 是否访问 127.0.0.1:11434：
14. 是否访问其他本地端口：
15. 是否调用外部 API：
16. 是否触发 /generate：
17. 是否触发 /export_docx：
18. 是否生成 DOCX：
19. 是否触发 /review/apply：
20. 是否触发 ZBid 写回：
21. 是否调用 ZBid API / DB / writeback：
22. 是否写 output/job/export：
23. formal_writeback_allowed 是否恒 false：
24. review_apply_allowed 是否恒 false：
25. docx_export_allowed 是否恒 false：
26. zbid_writeback_allowed 是否恒 false：
27. output_write_allowed 是否恒 false：
28. blocked_reasons 是否可读：
29. 是否停止所有启动进程：
30. stop condition 是否触发：
31. 风险说明：
32. 下一步建议：
```

未执行项必须标记为 `not-run`，不得标记为通过。fallback 项必须标记为 `fallback`，不得标记为通过。

## 13. Future Implementation Acceptance Criteria

后续实现或测试验收条件包括：

- deterministic fake schema tests。
- authorization categories tests。
- command allowlist tests。
- hard block list tests。
- no-write assertion tests。
- service startup authorization tests。
- Ollama boundary tests。
- ZDoc / ZBid preview-only authorization tests。
- stop conditions tests。
- report template tests。
- import isolation tests。
- no `output/job/export` write tests。

这些验收条件只描述未来测试方向，不构成本步实现。

## 14. Migration Path

建议后续步骤：

- Step 155：local trial runtime authorization gate fake schema tests。
- Step 156：runtime authorization gate stage review。
- Step 157：local trial authorized smoke dry-run command plan。
- Step 158：first real smoke authorization request。
- 后续在用户明确授权后，才可进入真实本地 smoke test 执行。
- 小范围试用稳定后，最后再进入约 50 人同时使用场景的正式部署设计。

任何进入真实运行的步骤都必须从授权门禁开始，不得因前序 docs / tests 已完成而自动获得运行权限。

## 15. Safety Conclusion

Step 154 仅完成 local trial runtime authorization gate design，不代表已经授权或执行任何运行时动作，不代表 smoke test、本地化部署、ZDoc / ZBid 实际联调、正式写回、DOCX 导出、ZBid 写回或 50 人部署已实现。

当前系统仍处于 preview-only / no-write 的设计与 fake metadata 固化阶段。后续任何真实运行行为必须由用户逐项明确授权，且授权范围、命令清单、停止条件和回报模板必须在执行前确认。
