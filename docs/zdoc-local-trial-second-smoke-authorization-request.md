# ZDoc Local Trial Second Smoke Authorization Request

## 1. Purpose

本文档用于向用户提交第二轮真实 local smoke test 的授权请求草案。

本步性质为 docs-only / authorization-request-only：

- 不执行命令。
- 不启动后端服务。
- 不启动前端服务。
- 不运行 Ollama。
- 不运行 `ollama serve`。
- 不访问任何本地端口。
- 不调用 ZBid。
- 不写 `output/job/export`。
- 不执行 smoke test。
- 不进入 50 人正式部署设计。

本文档不是授权本身。只有用户在后续明确回复授权后，才可进入第二轮真实 smoke 执行步骤。

## 2. Current baseline from first smoke

Step 159 / Step 160 已记录第一轮真实 local smoke 的当前基线：

- Git preflight 通过。
- Python / Node / pnpm 版本可读。
- `.env` 不存在，且未打印敏感配置。
- `output/job/export` 前后文件数：`0 -> 0`。
- `backend/data/autoplan/jobs` 前后文件数：`87 -> 87`。
- `build` 前后文件数：`1389 -> 1389`。
- 后端可启动，`/health` 返回 OK。
- `/local-llm/preview-safe` 返回 `preview_only=true`、`no_write=true`。
- preview-safe 字段显示未调用 `/generate`、`/export_docx`、`/review/apply`、ZBid writeback、`output/job/export`。
- 前端可启动，`/index` 返回 `200`。
- Ollama CLI 存在，但服务未运行。
- 未运行 `ollama serve`。
- 未下载或拉取模型。
- fake preview packet / validator 返回 `accepted_preview_only` / `accept_preview_only`。
- 五个正式链 flags 全为 false。
- 后端和前端进程均已停止。

当前正式链 flags 仍必须保持：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

## 3. Why a second smoke is needed

第二轮 smoke 的必要性来自第一轮未覆盖的运行时边界：

- 第一轮未验证 Ollama 服务可用链路。
- 第一轮未运行 `ollama serve`。
- 第一轮未验证本地模型列表在服务运行时可读。
- 第一轮未验证前端交互式按钮阻断。
- 第一轮未点击或检查 DOCX / ZBid / review/apply / formal writeback UI 入口。
- 第一轮未直接验证禁止端点的 blocked 行为。
- 第一轮未验证真实 preview-only API 请求。
- 第一轮未验证本地模型不可用或可用状态在 UI 中的只读展示边界。

第二轮 smoke 仍不得扩大到正式写回、DOCX 导出、ZBid 写回或 50 人部署。

## 4. Authorization request summary

本次未来第二轮 smoke test 仅申请验证以下范围：

- 后端服务可再次启动并停止。
- 前端服务可再次启动并停止。
- Ollama 可选服务检查。
- 如用户明确同意，可运行 `ollama serve`。
- Ollama tags / model list 可读。
- 本地模型不可用或可用时均不写回。
- 前端 UI 中 DOCX / ZBid / review/apply / formal writeback 入口保持禁用或提示未开放。
- preview-only 展示不会误导为正式正文。
- advisory 不会误导为 evidence。
- 禁止端点如需检查，只检查 blocked，不执行真实生成或写回。
- `output/job/export` 前后无新增写入。
- formal flags 全程保持 false。
- 启动进程可停止。

该授权不包括正式生成、正式导出、正式写回、ZBid 写回或 50 人部署。

## 5. Requested authorization items

未来执行第二轮 smoke 前，需要用户逐项明确授权。

1. 允许核验 Git 状态：
   - `pwd`
   - `git branch --show-current`
   - `git rev-parse HEAD`
   - `git status --short`
   - `git tag --points-at HEAD`

2. 允许检查本地环境版本：
   - Python 版本
   - Node 版本
   - pnpm 版本

3. 允许记录 `output/job/export` smoke 前后差异：
   - 只读检查
   - 不创建目录
   - 不写文件

4. 允许启动后端服务：
   - 仅用于健康检查、preview-safe、no-write / preview-only 状态检查。
   - 不启动正式写回 worker。
   - 不触发 `/generate`。
   - 检查结束后必须停止。

5. 允许启动前端服务：
   - 仅用于访问页面和 UI 阻断状态检查。
   - 可检查按钮是否禁用或提示未开放。
   - 不触发 DOCX / ZBid / review/apply / formal writeback。
   - 检查结束后必须停止。

6. 允许可选检查 Ollama：
   - 允许 `ollama list`。
   - 允许访问 `127.0.0.1:11434/api/tags`。
   - 是否允许运行 `ollama serve` 必须由用户单独明确。
   - 不自动下载模型。
   - 不自动拉取模型。
   - 不将模型输出作为 evidence。

7. 允许执行 preview-only 测试请求：
   - 不触发正式生成。
   - 不写回正文。
   - 不写 `output/job/export`。
   - 只检查 preview packet / validator / `blocked_reasons` / flags。

8. 允许检查禁止端点是否 blocked：
   - 仅当系统存在明确的 safe/block endpoint 或只读 blocked 检查方式。
   - 不得实际执行正式生成、导出、review/apply 或 ZBid 写回。
   - 如无法确认安全 blocked 检查方式，应跳过并记录。

9. 允许生成 smoke report：
   - 仅生成回报文本。
   - 不生成 DOCX/JSON/Markdown 正式产物。
   - 不写 `output/job/export`。

10. 允许停止所有本次启动的本地服务：
    - 后端服务。
    - 前端服务。
    - 如另行授权启动 `ollama serve`，则按授权停止或确认其独立状态。

未获得上述逐项明确授权，不得执行第二轮真实 smoke。

## 6. Explicitly not authorized

本授权请求不授权以下事项：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- ZBid API / DB / writeback
- DOCX 文件生成
- JSON/Markdown 正式导出
- `output/job/export` 写入
- formal writeback
- formal writeback dry-run
- 修改 source section
- 真实 candidate patch 写入
- 下载模型
- 拉取模型
- 将模型输出作为 evidence
- 50 人正式部署设计
- Mac Studio / NAS / UPS / Redis / PostgreSQL 正式部署配置

第二轮 smoke 不得把 preview-only 当作 writeback allowed，不得把 advisory 当作 evidence。

## 7. Proposed future command groups

以下仅为未来用户明确授权后可执行的命令组设计。本步不执行这些命令组。

- Git preflight group
- Environment preflight group
- Output isolation snapshot group
- Backend service group
- Frontend service group
- Ollama optional service group
- UI block check group
- ZDoc preview-only packet group
- ZBid preview validator group
- Formal chain block group
- Output isolation diff group
- Service shutdown group
- Smoke report group

Command group plan does not equal authorization. Command placeholders do not equal execution.

## 8. Hard stop conditions

未来第二轮 smoke 执行中，出现任一情况必须立即停止：

- 当前目录错误。
- 分支错误。
- HEAD 不一致。
- `git status` 非 clean。
- 未授权动作出现。
- 任一正式链 flag 为 true。
- `output/job/export` 出现写入。
- DOCX 文件生成。
- `/generate` 被触发。
- `/export_docx` 被触发。
- `/review/apply` 被触发。
- ZBid 写回被触发。
- ZBid API / DB / writeback 被调用。
- 未授权下载或拉取模型。
- 模型输出被作为 evidence。
- 本地服务无法停止。
- unknown process 持续运行。
- `blocked_reasons` 缺失。
- advisory 被作为 evidence。
- preview 被误显示为正式正文。
- source hash / version mismatch 未 blocked。

## 9. Smoke report template

未来第二轮 smoke 执行后，回报至少应包含：

- 用户授权范围
- 实际执行命令
- 当前目录
- 当前分支
- 开始前 HEAD
- 结束后 HEAD
- `git status`
- 是否启动后端
- 后端 PID 或停止状态
- 后端 health / preview-safe 结果
- 是否启动前端
- 前端 PID 或停止状态
- 前端访问结果
- UI 阻断状态检查结果
- 是否运行 Ollama
- 是否运行 `ollama serve`
- Ollama PID 或状态
- 是否访问 `127.0.0.1:11434`
- Ollama tags / model list 结果
- 是否下载或拉取模型
- 是否访问其他本地端口
- 是否调用外部 API
- 是否触发 `/generate`
- 是否触发 `/export_docx`
- 是否生成 DOCX
- 是否触发 `/review/apply`
- 是否触发 ZBid 写回
- 是否调用 ZBid API / DB / writeback
- 是否写 `output/job/export`
- formal flags 是否恒 false
- `blocked_reasons` 是否可读
- preview 是否被误显示为正式正文
- advisory 是否被误显示为 evidence
- 是否停止所有启动进程
- 风险说明
- 下一步建议

## 10. User confirmation wording

未来进入 Step 162 前，需要用户明确回复类似以下授权确认语：

> 我授权执行 Step 162 第二轮真实 local smoke test，授权范围仅限 Step 161 授权请求文档中列明事项；允许/不允许运行 ollama serve；不得触发 /generate、/export_docx、/review/apply、ZBid 写回、正式写回，不得写 output/job/export，不得下载或拉取模型，不得进入 50 人正式部署设计。

未收到上述或等效明确授权，不得执行 Step 162。

如果用户没有明确“允许运行 `ollama serve`”，则第二轮 smoke 不得运行 `ollama serve`。

## 11. Next step recommendation

建议下一步为：

ZDoc Step 162: second real local smoke test execution, requires explicit user authorization.

Step 162 只有在用户明确授权后才能执行。如用户未授权，应停止，不得执行任何运行时动作。

## 12. Safety conclusion

Step 161 仅完成第二轮真实 local smoke test 授权请求文档。

本文档不代表已获得授权，不代表 smoke test 已执行，不代表本地化部署、ZDoc/ZBid 实际联调、正式写回、DOCX 导出、ZBid 写回或 50 人部署已实现。

当前总体策略仍为：

- 先完成本地化部署基础闭环。
- 再完成 ZDoc 与 ZBid 的 preview-only 对接。
- 再进行小范围试用和问题修正。
- 最后再按约 50 人同时使用场景进行正式部署设计。

本步不进入 Mac Studio / NAS / UPS / Redis / PostgreSQL / 50 人并发等正式部署设计。

本步不要求运行 full backend tests。Step 98B 已确认 `backend/tests` full suite 存在既有 collection/order import-isolation 问题。
