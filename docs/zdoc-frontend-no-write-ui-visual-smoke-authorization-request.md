# ZDoc Frontend No-Write UI Visual Smoke Authorization Request

## 1. Purpose

本文档用于起草 Step 174 前端 no-write UI visual smoke 的授权请求。本文档仅为 docs-only / authorization-request-only，不代表用户已经授权，不执行 visual smoke，不启动后端服务，不启动前端服务，不运行 Ollama，不访问任何本地端口，不调用 ZBid，不写 `output/job/export`，不进入本地化部署执行，也不进入 50 人团队正式部署设计。

本授权请求的目的仅限于未来验证 Step 171 前端 UI 修复后的实际页面展示效果：

- 验证“生成 Word 文档”入口是否已禁用或显示“正式导出未开放”。
- 验证 preview-only 提示是否可见。
- 验证 no-write 提示是否可见。
- 验证 `blocked_reasons` 是否可见。
- 验证 advisory / evidence 边界提示是否可见。
- 验证 preview 不会被误认为正式正文。

未收到用户后续明确授权前，不得执行 Step 174。

## 2. Current Baseline

Step 171 已完成前端代码层面的 no-write UI 修复：

- 移除生成设置区提交表单语义。
- 将“生成 Word 文档”入口改为禁用的“正式导出未开放”状态。
- 增加 preview-only / no-write 提示。
- 增加 `blocked_reasons` 展示区域。
- 增加 AI advisory 不是 evidence、preview 不是正式正文的边界提示。

Step 172 已归档 Step 171 的修改范围和未验证事项。当前仍未启动前端服务，未做浏览器视觉验证，未验证页面实际展示效果、按钮实际禁用状态或提示文案实际可见性。

## 3. Requested Authorization Scope

未来 Step 174 如需执行 visual smoke，拟申请用户逐项授权以下动作：

- 允许核验 Git 状态。
- 允许启动后端服务，仅用于支撑本地页面访问和必要健康状态检查。
- 允许启动前端服务，仅用于访问 Step 171 修复后的页面。
- 允许访问本地前端页面。
- 允许只读检查页面视觉状态。
- 允许检查“正式导出未开放”按钮是否禁用。
- 允许检查 preview-only 提示是否可见。
- 允许检查 no-write 提示是否可见。
- 允许检查 `blocked_reasons` 提示是否可见。
- 允许检查 AI advisory 不是 evidence 的提示是否可见。
- 允许检查 preview 不是正式正文的提示是否可见。
- 允许检查 DOCX / ZBid / review/apply / formal writeback 入口是否禁用或提示未开放。
- 允许检查本次启动的服务是否可停止。

授权范围必须限于上述事项。部分授权不得扩大解释为允许正式生成、正式导出、正式写回或 ZBid 调用。

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

## 5. Visual Smoke Checklist

未来 Step 174 visual smoke 应检查：

- 页面可访问。
- preview-only 提示可见。
- no-write 提示可见。
- `blocked_reasons` 可见。
- advisory 不是 evidence 提示可见。
- preview 不是正式正文提示可见。
- “生成 Word 文档”不可提交正式生成。
- “正式导出未开放”按钮显示为禁用状态。
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

## 6. Hard Stop Conditions

未来执行中出现以下任一情况必须立即停止：

- 当前目录错误。
- 当前分支错误。
- HEAD 不一致。
- `git status --short` 非 clean。
- 未授权动作出现。
- 端口启动异常且无可读错误。
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

## 7. Required Smoke Report Template

未来 Step 174 执行后应回报：

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
- “正式导出未开放”按钮禁用状态。
- preview-only 提示可见性。
- no-write 提示可见性。
- `blocked_reasons` 可见性。
- advisory 不是 evidence 提示可见性。
- preview 不是正式正文提示可见性。
- DOCX / ZBid / review/apply / formal writeback 入口状态。
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

## 8. User Confirmation Wording

未来进入 Step 174 前，必须要求用户明确回复以下或等效授权语：

“我授权执行 Step 174 前端 no-write UI visual smoke，授权范围仅限 Step 173 授权请求文档列明事项；允许启动后端和前端并访问本地页面；不得触发 /generate、/export_docx、/review/apply、ZBid 写回，不得生成 DOCX，不得写 output/job/export，不得进入 50 人正式部署设计。”

未收到上述或等效明确授权，不得执行 Step 174。

## 9. Next Step Recommendation

建议下一步为：

ZDoc Step 174：frontend no-write UI visual smoke execution，必须用户明确授权后才可执行。

如用户未明确授权，应停止，不得启动后端或前端服务，不得访问端口，不得执行 visual smoke。

## 10. Safety Conclusion

Step 173 仅完成前端 no-write UI visual smoke 授权请求文档，不代表已获得授权，不代表 visual smoke 已执行，不代表服务已启动，不代表页面实际展示效果已验证，也不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback、本地化部署或 50 人团队正式部署已经实现。
