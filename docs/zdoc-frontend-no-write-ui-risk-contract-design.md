# ZDoc Frontend No-Write UI Risk Contract Design

## 1. Scope

本文档是 Step 164 的 docs-only contract design，用于针对 Step 162 / Step 163 发现的前端 UI 风险，设计 no-write / preview-only / `blocked_reasons` / evidence 边界提示与“生成 Word 文档”入口风险控制契约。

本步只设计契约，不修改前端代码，不修改测试，不修改既有文档，不启动后端或前端服务，不运行 Ollama，不访问任何本地端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不写 `output/job/export`，不进入本地化部署执行，不进入 50 人团队正式部署设计。

## 2. Step 162 / Step 163 UI Risk Summary

Step 162 第二轮真实 local smoke test 已在用户授权范围内完成，Step 163 已进行 docs-only 复盘归档。

已确认的安全结果：

- 后端 `/local-llm/preview-safe` 仍返回 `preview_only=true`。
- 后端 `/local-llm/preview-safe` 仍返回 `no_write=true`。
- 后端 preview-safe 字段显示未调用 `/generate`、`/export_docx`、`/review/apply`、ZBid writeback、`output/job/export`。
- Ollama serve 已按授权启动并停止。
- Ollama tags / model list 可读。
- `output/job/export` 前后文件数保持 `0 -> 0`。
- `backend/data/autoplan/jobs` 前后文件数保持 `87 -> 87`。
- `build` 前后文件数保持 `1389 -> 1389`。
- `frontend_web/users.db` stat 未变化。
- 五个正式链 flags 恒为 false。

Step 162 / Step 163 发现的前端 UI 风险：

- 主页面存在“生成 Word 文档”入口。
- 页面缺少 preview-only 提示。
- 页面缺少 no-write 提示。
- 页面缺少 `blocked_reasons` 展示。
- 页面缺少 evidence 边界提示。
- 用户可能误认为 preview 已可正式生成或正式导出。
- 未发现 `/export_docx`、`/review/apply`、ZBid 文本或入口。
- Step 162 未点击或提交“生成 Word 文档”入口。

## 3. Current Frontend Risk Points

当前前端风险点必须作为后续 UI 设计和实现的约束输入：

1. “生成 Word 文档”入口存在。
2. 当前页面未明确告知用户系统处于 preview-only 阶段。
3. 当前页面未明确告知用户系统处于 no-write 阶段。
4. 当前页面未展示 `blocked_reasons`。
5. 当前页面未解释为什么不能生成、导出、写回或提交 review/apply。
6. 当前页面未说明 AI advisory 不得作为 evidence。
7. 当前页面未说明 preview advisory 不得作为 evidence。
8. 当前页面未说明 preview 不等于正式正文。
9. 当前页面未说明正式链 flags 必须保持 false。
10. 用户可能误判为正式导出能力已开放。

这些风险不代表 Step 162 触发了正式链；它们是 UI contract 风险，需要先设计，再在后续单独授权步骤中实现。

## 4. Frontend No-Write UI Design Principles

后续前端 UI 必须遵守以下原则：

1. preview-only 必须明示。
2. no-write 必须明示。
3. AI advisory 不得显示为 evidence。
4. preview advisory 不得显示为 evidence。
5. preview 不得显示为正式正文。
6. `blocked_reasons` 必须可读。
7. 正式链入口必须禁用、隐藏或显示“未开放”。
8. DOCX export 不得被暗示为已开放。
9. ZBid writeback 不得被暗示为已开放。
10. review/apply 不得被暗示为已开放。
11. formal writeback 不得被暗示为已开放。
12. output write 不得被暗示为已开放。
13. 所有正式链 flags 必须为 false。

正式链 flags 的当前阶段不变量：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

## 5. “生成 Word 文档” Entry Risk Control Contract

“生成 Word 文档”入口是当前最主要的 UI 误导风险点。

后续前端实现必须满足：

1. preview-only 阶段不得将该入口呈现为可提交的正式生成按钮。
2. 如保留入口，必须禁用。
3. 如显示按钮，按钮或邻近提示必须标注“正式导出未开放”。
4. 如显示按钮，必须标注“不写回正式正文”。
5. 如显示按钮，必须标注“不生成 DOCX”。
6. 如显示按钮，必须标注“不写 output/job/export”。
7. 如显示按钮，必须标注“当前仅支持 preview-only / no-write 检查”。
8. 不得触发 `/generate`。
9. 不得触发 `/export_docx`。
10. 不得写 `output/job/export`。
11. 不得生成 DOCX。
12. 不得让用户误认为 Word 正式生成能力已开放。

推荐 UI 行为：

- 在 preview-only 阶段将“生成 Word 文档”改为禁用态。
- 禁用态文案建议为：“正式 Word 导出未开放”。
- 邻近说明建议包含：“当前仅预览，不写正文，不生成 DOCX，不写 output/job/export。”
- 若按钮隐藏，则页面仍需显示正式导出未开放的说明，避免用户误判功能缺失或状态不明。

## 6. Blocked Reasons Display Contract

前端必须展示 `blocked_reasons`，并使用户能读懂为什么当前不能生成、导出或写回。

展示契约：

1. `blocked_reasons` 必须可读。
2. `blocked_reasons` 必须与后端 preview-safe / no-write 状态一致。
3. `blocked_reasons` 必须说明为什么不能生成。
4. `blocked_reasons` 必须说明为什么不能导出 DOCX。
5. `blocked_reasons` 必须说明为什么不能 review/apply。
6. `blocked_reasons` 必须说明为什么不能 ZBid writeback。
7. `blocked_reasons` 必须说明为什么不能 formal writeback。
8. `blocked_reasons` 必须说明为什么不能写 `output/job/export`。
9. `blocked_reasons` 不得被隐藏在开发者调试信息中。
10. `blocked_reasons` 不得只通过颜色表达，必须有可读文本。

推荐展示内容：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`
- `docx_export_blocked_current_stage`
- `review_apply_blocked_current_stage`
- `zbid_writeback_blocked_current_stage`
- `formal_writeback_blocked_current_stage`
- `output_write_blocked_current_stage`

## 7. Evidence Boundary Display Contract

前端必须明确 evidence 边界，避免用户把 preview/advisory/候选对象误认为证据。

展示契约：

1. AI advisory 不得作为 evidence。
2. preview advisory 不得作为 evidence。
3. shadow candidate 不得作为 evidence。
4. patch preview 不得作为 evidence。
5. diff preview 不得作为 evidence。
6. rollback plan 不得作为 evidence。
7. dry-run result 不得作为 evidence。
8. ZBid preview scoring 不得作为 evidence。
9. evidence 必须来自可验证资料锚点。
10. tender file refs 不自动构成 evidence。
11. scoring clause refs 必须指向可验证评分条款。
12. 缺少 evidence anchor 或 scoring clause refs 时，UI 必须显示 blocked 或 requires human review。

推荐提示文案：

- “AI 建议仅供预览，不是证据。”
- “预览内容不等于正式正文。”
- “证据必须来自可验证资料锚点。”
- “评分条款必须指向可验证来源。”

## 8. Formal Chain Entry Control

前端所有正式链入口必须受当前 no-write 状态约束。

控制契约：

- DOCX export blocked。
- review/apply blocked。
- ZBid writeback blocked。
- formal writeback blocked。
- output write blocked。

入口要求：

1. DOCX export 入口必须禁用、隐藏或显示“未开放”。
2. review/apply 入口必须禁用、隐藏或显示“未开放”。
3. ZBid writeback 入口必须禁用、隐藏或显示“未开放”。
4. formal writeback 入口必须禁用、隐藏或显示“未开放”。
5. output write 入口不得暴露为可执行操作。
6. 禁用态必须配套原因说明。
7. 禁用态不得仅依赖前端样式，后续实现仍需后端 no-write 保护。

禁止事项：

- 不得通过 UI 触发 `/generate`。
- 不得通过 UI 触发 `/export_docx`。
- 不得通过 UI 触发 `/review/apply`。
- 不得通过 UI 触发 ZBid writeback。
- 不得通过 UI 触发 formal writeback。
- 不得通过 UI 写 `output/job/export`。

## 9. Preview-Only Result Display Contract

preview-only 结果展示必须避免与正式正文混淆。

展示契约：

1. 结果区域必须标注“预览”。
2. 结果区域必须标注“preview-only”或等效中文说明。
3. 结果区域必须标注“不写回正式正文”。
4. 结果区域必须标注“不生成 DOCX”。
5. 结果区域必须标注“不写 output/job/export”。
6. advisory 文案必须标注“建议”或“预览建议”。
7. advisory 文案不得使用“证据”“已采纳”“已写回”等表达。
8. 若存在 copy/export 类辅助操作，必须明确其不属于正式 DOCX/export_docx 链路。

## 10. UI Acceptance Criteria

后续 UI 设计和实现必须满足以下验收标准：

1. 用户能明确看到当前是 preview-only。
2. 用户能明确看到当前是 no-write。
3. 用户不能误认为 Word 已可正式生成。
4. 用户不能误认为 DOCX 已可正式导出。
5. 用户不能误认为 ZBid 写回已开放。
6. 用户不能误认为 review/apply 已开放。
7. 用户不能误认为 formal writeback 已开放。
8. 用户不能误认为 advisory 是证据。
9. 用户不能误认为 preview 是正式正文。
10. 用户不能通过 UI 触发正式链。
11. `blocked_reasons` 可读。
12. evidence 边界可读。
13. 所有正式链 flags 保持 false。
14. `output/job/export` 不出现写入。

## 11. Runtime Stop Criteria for Future UI Smoke

后续如果用户单独授权执行 UI smoke，出现以下任一情况必须停止：

- “生成 Word 文档”入口可提交正式生成。
- UI 触发 `/generate`。
- UI 触发 `/export_docx`。
- UI 触发 `/review/apply`。
- UI 触发 ZBid writeback。
- UI 触发 formal writeback。
- UI 写 `output/job/export`。
- UI 生成 DOCX。
- 任一正式链 flag 为 true。
- preview 被显示为正式正文。
- advisory 被显示为 evidence。
- `blocked_reasons` 缺失。
- no-write 状态不可读。
- preview-only 状态不可读。

## 12. Explicit Non-Goals

本契约设计不代表以下事项已经实现：

- 不代表前端代码已修改。
- 不代表测试已新增。
- 不代表后端路由已新增。
- 不代表 DOCX export 已实现。
- 不代表 review/apply 已实现。
- 不代表 ZBid writeback 已实现。
- 不代表 formal writeback 已实现。
- 不代表 `output/job/export` 可写。
- 不代表本地化部署已完成。
- 不代表 50 人团队正式部署设计已启动。

## 13. Recommended Next Step

建议下一步为：

ZDoc Step 165: frontend no-write UI risk contract fake schema tests.

Step 165 应为 tests-only，用 fake schema tests 固化本契约中的 UI 风险点、no-write 展示要求、`blocked_reasons` 展示要求、evidence 边界、正式链入口控制和验收标准。

Step 165 仍不得修改前端代码。代码修复应在后续单独授权步骤执行。

## 14. Safety Conclusion

Step 164 仅完成 frontend no-write UI risk contract design。

本契约把 Step 162 / Step 163 发现的前端风险收束为明确的 UI 边界：preview-only 必须明示，no-write 必须明示，`blocked_reasons` 必须可读，evidence 边界必须可读，“生成 Word 文档”入口不得作为可提交正式生成按钮呈现，所有正式链入口必须禁用、隐藏或显示未开放，五个正式链 flags 必须保持 false。

当前系统仍处于 preview-only / no-write 阶段，不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback、本地化部署或 50 人团队正式部署已经实现。
