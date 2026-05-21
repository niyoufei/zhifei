# ZDoc Frontend No-Write UI Screenshot Smoke Authorization Request

## 1. Purpose

本文档用于起草 Step 177 前端 no-write UI 截图级 visual smoke 的授权请求。本文档仅为 docs-only / authorization-request-only，不代表用户已经授权，不执行 visual smoke，不启动后端服务，不启动前端服务，不运行 Ollama，不访问任何端口，不截图，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不生成 DOCX，不写 `output/job/export`，不进入本地化部署执行，也不进入 50 人团队正式部署设计。

本授权请求的目的仅限于未来对 Step 171 前端 no-write UI 修复进行截图级视觉归档：

- 验证 preview-only 提示实际可见。
- 验证 no-write 提示实际可见。
- 验证 `blocked_reasons` 实际可见。
- 验证 advisory / evidence 边界提示实际可见。
- 验证 preview 不是正式正文提示实际可见。
- 验证“生成 Word 文档”入口为禁用或“正式导出未开放”状态。

未收到用户后续明确授权前，不得执行 Step 177。

## 2. Current Baseline

Step 171 已完成前端 no-write UI 代码修复：

- 移除生成设置区提交表单语义。
- 将“生成 Word 文档”入口改为禁用的“正式导出未开放”状态。
- 增加 preview-only / no-write 提示。
- 增加 `blocked_reasons` 展示区域。
- 增加 AI advisory 不是 evidence、preview 不是正式正文的边界提示。

Step 174 已完成首次 visual smoke，确认：

- 前端 `/index` 返回 200。
- 未发现可提交正式生成按钮。
- `submit_word_button_count=0`。
- `generate_hidden_form_count=0`。
- “正式导出未开放”可见。
- 按钮 `disabled=true`。
- 按钮 `aria-disabled=true`。
- preview-only / no-write / `blocked_reasons` / evidence 边界提示可见。
- `output/job/export` 前后无差异。

Step 175 已完成上述结果的 docs-only 归档。当前仍未生成浏览器截图，因此如需截图级证据，应另行授权 Step 177。

## 3. Requested Authorization Scope

未来 Step 177 如需执行截图级 visual smoke，拟申请用户逐项授权以下动作：

- 允许核验 Git 状态。
- 允许启动后端服务，仅用于支撑本地页面访问和必要健康状态检查。
- 允许启动前端服务，仅用于访问 Step 171 修复后的页面。
- 允许访问本地前端页面。
- 允许使用浏览器或当前环境可用截图工具进行截图。
- 允许保存截图到指定临时 smoke 目录。
- 允许生成截图 smoke report。
- 允许检查“正式导出未开放”按钮是否禁用。
- 允许检查 preview-only 提示是否可见。
- 允许检查 no-write 提示是否可见。
- 允许检查 `blocked_reasons` 提示是否可见。
- 允许检查 AI advisory 不是 evidence 的提示是否可见。
- 允许检查 preview 不是正式正文的提示是否可见。
- 允许检查本次启动的服务是否可停止。

授权范围必须限于上述事项。部分授权不得扩大解释为允许正式生成、正式导出、正式写回、ZBid 调用、模型调用或部署设计。

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
- 不写 `output/job/export`。
- 不修改 source section。
- 不生成正式文档。
- 不下载或拉取模型。
- 不调用外部模型/API。
- 不进入本地化部署执行。
- 不进入 50 人团队正式部署设计。

## 5. Screenshot Checklist

未来 Step 177 截图级 smoke 应检查并归档：

- 页面整体可访问。
- preview-only 提示可见。
- no-write 提示可见。
- `blocked_reasons` 可见。
- advisory 不是 evidence 可见。
- preview 不是正式正文可见。
- “正式导出未开放”可见。
- “生成 Word 文档”不可提交正式生成。
- DOCX export 入口禁用或提示未开放。
- ZBid writeback 入口禁用或提示未开放。
- review/apply 入口禁用或提示未开放。
- formal writeback 入口禁用或提示未开放。
- 所有正式链 flags 语义仍为 false：
  - `formal_writeback_allowed=false`
  - `review_apply_allowed=false`
  - `docx_export_allowed=false`
  - `zbid_writeback_allowed=false`
  - `output_write_allowed=false`

截图文件只能用于 smoke 归档，不得作为正式文档导出物，不得写入 `output/job/export`。

## 6. Proposed Screenshot Artifact Boundary

若用户授权保存截图，建议截图归档目录为仓库内单独的临时 smoke 路径，例如：

- `tmp/smoke/frontend-no-write-ui-screenshot/`

该目录仅用于本次截图级 visual smoke 归档。若用户未明确授权写入该目录，不得创建目录或保存截图。

截图 smoke report 也应仅作为本次 smoke 回报文本或用户另行授权的临时归档文件，不得生成 DOCX/JSON/Markdown 正式导出产物，不得写 `output/job/export`。

## 7. Hard Stop Conditions

未来执行中出现以下任一情况必须立即停止：

- 当前目录错误。
- 当前分支错误。
- HEAD 不一致。
- `git status --short` 非 clean。
- 启动失败且无可读错误。
- 截图工具不可用。
- 未授权写入截图目录。
- 出现 `output/job/export` 写入。
- 触发 `/generate`。
- 触发 `/export_docx`。
- 触发 `/review/apply`。
- 生成 DOCX。
- 触发 ZBid 写回。
- 调用 ZBid API / DB / writeback。
- 任一正式链 flag 为 true。
- 服务无法停止。
- 页面仍显示可提交的正式生成入口。
- `blocked_reasons` 缺失。
- advisory 被展示为 evidence。
- preview 被展示为正式正文。

## 8. Required Screenshot Smoke Report Template

未来 Step 177 执行后应回报：

- 用户授权范围。
- 实际执行命令。
- 当前目录。
- 当前分支。
- 开始前 HEAD。
- 结束后 HEAD。
- `git status --short`。
- 是否启动后端服务。
- 后端 PID 或停止状态。
- 是否启动前端服务。
- 前端 PID 或停止状态。
- 是否访问本地前端页面。
- 页面可访问结果。
- 截图工具名称与可用性。
- 截图保存路径。
- “正式导出未开放”按钮可见性与禁用状态。
- preview-only 提示可见性。
- no-write 提示可见性。
- `blocked_reasons` 可见性。
- advisory 不是 evidence 提示可见性。
- preview 不是正式正文提示可见性。
- 是否触发 `/generate`。
- 是否触发 `/export_docx`。
- 是否生成 DOCX。
- 是否触发 `/review/apply`。
- 是否触发 ZBid 写回。
- 是否调用 ZBid API / DB / writeback。
- 是否写 `output/job/export`。
- 是否停止所有启动进程。
- 风险说明。
- 下一步建议。

## 9. User Confirmation Wording

未来进入 Step 177 前，必须要求用户明确回复以下或等效授权语：

“我授权执行 Step 177 前端 no-write UI 截图级 visual smoke，授权范围仅限 Step 176 授权请求文档列明事项；允许启动后端和前端、访问本地页面并生成截图归档；不得触发 /generate、/export_docx、/review/apply、ZBid 写回，不得生成 DOCX，不得写 output/job/export，不得进入 50 人正式部署设计。”

未收到上述或等效明确授权，不得执行 Step 177。

## 10. Next Step Recommendation

建议下一步为：

ZDoc Step 177：frontend no-write UI screenshot visual smoke execution，必须用户明确授权后才可执行。

如用户未明确授权，应停止，不得启动服务，不得访问端口，不得截图，不得执行 visual smoke。

## 11. Safety Conclusion

Step 176 仅完成前端 no-write UI 截图级 visual smoke 授权请求文档，不代表已获得授权，不代表截图级 visual smoke 已执行，不代表服务已启动，不代表页面截图已生成，也不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback、本地化部署或 50 人团队正式部署已经开放或实现。
