# ZDoc Frontend No-Write UI Implementation Plan Design

## 1. Scope

本文档是 Step 167 的 docs-only frontend no-write UI implementation plan design。

目标是在不修改前端代码的前提下，针对 Step 162 / Step 163 发现并由 Step 164 / Step 165 固化的 UI 风险，制定后续代码修复计划。

本步只设计实施方案，不修改代码，不修改 tests，不修改 frontend，不修改既有 docs，不运行 pytest，不启动后端或前端服务，不运行 Ollama，不访问本地端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不写 `output/job/export`，不进入本地化部署执行，不进入 50 人团队正式部署设计。

## 2. Confirmed UI Risks

Step 162 / Step 163 已确认以下 UI 风险：

1. 主页面存在“生成 Word 文档”入口。
2. 页面缺少 preview-only 提示。
3. 页面缺少 no-write 提示。
4. 页面缺少 `blocked_reasons` 展示。
5. 页面缺少 evidence 边界提示。
6. 用户可能误认为 Word 正式生成已开放。
7. 用户可能误认为 Word 正式导出已开放。
8. 用户可能误认为 preview 是正式正文。
9. 用户可能误认为 advisory 是 evidence。
10. Step 162 未点击或提交“生成 Word 文档”入口。

这些风险不代表正式链已被触发，但会影响后续真实 local trial 的用户理解和误操作防护。

## 3. Implementation Goals

后续前端代码修复应以最小范围实现以下目标：

1. 将当前页面明确标识为 preview-only。
2. 将当前页面明确标识为 no-write。
3. 将“生成 Word 文档”入口改为禁用、隐藏或改为“正式导出未开放”。
4. 增加 `blocked_reasons` 展示区域。
5. 增加 advisory/evidence 边界说明。
6. 增加 preview/formal body 边界说明。
7. 防止 UI 触发 `/generate`。
8. 防止 UI 触发 `/export_docx`。
9. 防止 UI 触发 `/review/apply`。
10. 防止 UI 触发 ZBid 写回。
11. 防止 UI 触发 formal writeback。
12. 防止 UI 写 `output/job/export`。
13. 五个正式链 flags 保持 false。

正式链 flags 不变量：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

## 4. Proposed Future Modification Scope

以下仅为未来代码修复计划范围，本步不得修改。

可能涉及：

- frontend 页面模板。
- “生成 Word 文档”按钮或入口状态。
- preview-only / no-write 状态提示文案。
- `blocked_reasons` 状态展示组件。
- advisory/evidence 边界提示文案。
- formal-chain unavailable 文案。
- 前端只读状态字段映射。

不得触碰：

- 正式生成链。
- DOCX 导出链。
- `/review/apply` 链。
- ZBid 写回链。
- formal writeback 链。
- `output/job/export` 写入链。
- orchestrator。
- llm_client。
- provider。
- generation。
- export。
- review。
- actions_bridge。
- ZBid API / DB / writeback。
- 本地化部署配置。
- 50 人团队正式部署设计。

## 5. UI State Design

后续前端实现应至少表达以下 UI 状态。

### 5.1 Preview-Only State

页面必须明确显示：

- 当前仅为预览阶段。
- preview-only 不等于正式正文。
- preview-only 不等于写回许可。
- preview-only 不触发 DOCX 导出。
- preview-only 不触发 ZBid 写回。

建议文案：

> 当前为预览模式，仅展示检查结果，不写回正式正文，不生成 DOCX，不写 output/job/export。

### 5.2 No-Write State

页面必须明确显示：

- 当前 no-write。
- 不写正式正文。
- 不写 `output/job/export`。
- 不更新成果。
- 不触发导出。
- 不触发 review/apply。
- 不触发 ZBid 写回。

建议文案：

> 当前为 no-write 状态：不写回、不导出、不提交 review/apply、不调用 ZBid 写回。

### 5.3 Blocked State

页面必须展示 `blocked_reasons`，说明当前为什么不能进入正式链。

展示内容至少包括：

- 为什么不能生成。
- 为什么不能导出 DOCX。
- 为什么不能 review/apply。
- 为什么不能 ZBid writeback。
- 为什么不能 formal writeback。
- 为什么不能写 `output/job/export`。

建议展示方式：

- 页面内固定提示区。
- 与按钮禁用态邻近展示。
- 文本可读，不仅依赖颜色或图标。

### 5.4 Evidence Missing State

当 evidence anchor 或 scoring clause refs 不完整时，页面必须显示 blocked 或 requires human review。

必须说明：

- AI advisory 不是 evidence。
- preview advisory 不是 evidence。
- shadow candidate / patch / diff / rollback / dry-run 不是 evidence。
- evidence 必须来自可验证资料锚点。
- scoring clause refs 必须指向可验证评分条款。

### 5.5 Formal Export Disabled State

正式导出禁用状态必须覆盖：

- “生成 Word 文档”入口。
- DOCX export 入口。
- 任何可能让用户误解为正式导出的按钮或链接。

推荐行为：

- 禁用按钮，并显示“正式导出未开放”。
- 或隐藏正式导出入口，并展示“当前仅预览，不支持正式导出”。
- 不得呈现可提交的正式生成按钮。

### 5.6 ZBid Writeback Disabled State

ZBid 写回禁用状态必须覆盖：

- ZBid writeback 入口。
- ZBid scoring preview。
- ZBid mapping preview。

必须说明：

- ZBid preview scoring 不是 evidence。
- accepted preview 不等于 ZBid writeback permission。
- 当前阶段 `zbid_writeback_allowed=false`。

## 6. “生成 Word 文档” Entry Plan

后续代码修复应优先处理“生成 Word 文档”入口。

推荐实施优先级：

1. 将入口改为禁用态。
2. 将按钮文案改为“正式 Word 导出未开放”。
3. 在按钮附近添加 no-write 说明。
4. 移除或阻断可能提交正式生成的 form action。
5. 保留页面布局稳定性，避免用户误判为功能丢失。

必须避免：

- 可点击提交正式生成。
- POST 到正式生成链。
- 触发 `/generate`。
- 触发 `/export_docx`。
- 生成 DOCX。
- 写 `output/job/export`。

## 7. Blocked Reasons Implementation Plan

后续代码修复应增加 `blocked_reasons` 展示区域。

最小实现建议：

- 在主页面设置一个固定 no-write status panel。
- 以列表方式展示 blocked reasons。
- 初始值可来自前端静态 no-write contract。
- 后续可接入后端 preview-safe 返回字段。

建议初始 blocked reasons：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `docx_export_blocked_current_stage`
- `review_apply_blocked_current_stage`
- `zbid_writeback_blocked_current_stage`
- `formal_writeback_blocked_current_stage`
- `output_write_blocked_current_stage`

实现边界：

- 不得为展示 blocked reasons 而调用正式链。
- 不得为展示 blocked reasons 而写文件。
- 不得把 blocked reasons 隐藏为调试字段。

## 8. Advisory / Evidence Boundary Implementation Plan

后续代码修复应增加 advisory/evidence 边界说明。

建议展示：

- “AI 建议仅供预览，不是证据。”
- “预览内容不等于正式正文。”
- “证据必须来自可验证资料锚点。”
- “评分条款必须指向可验证来源。”

必须避免：

- 将 advisory 区域命名为 evidence。
- 将 preview 文案放入正式正文区域。
- 使用“已采纳”“已写回”“证据成立”等表达。

## 9. Formal Chain Entry Control Plan

后续代码修复应保证以下入口禁用或明确未开放：

- DOCX export。
- review/apply。
- ZBid writeback。
- formal writeback。
- output write。

控制策略：

1. 入口不存在时，页面仍需说明未开放。
2. 入口存在时，必须 disabled。
3. disabled 入口必须有原因说明。
4. 禁用态不得仅依赖 CSS；后续应配合后端 no-write 防护。
5. 所有正式链 flags 必须显示或隐含为 false。

## 10. Acceptance Criteria

后续前端代码修复完成后，应满足以下验收标准：

1. 页面必须明确显示 preview-only。
2. 页面必须明确显示 no-write。
3. “生成 Word 文档”不得表现为可正式提交。
4. “生成 Word 文档”如保留，必须 disabled 或明确显示“正式导出未开放”。
5. advisory 不得被展示为 evidence。
6. preview 不得被展示为正式正文。
7. `blocked_reasons` 必须可读。
8. evidence 边界提示必须可读。
9. 正式链入口必须禁用或明确未开放。
10. UI 不得触发 `/generate`。
11. UI 不得触发 `/export_docx`。
12. UI 不得触发 `/review/apply`。
13. UI 不得触发 ZBid 写回。
14. UI 不得触发 formal writeback。
15. UI 不得写 `output/job/export`。
16. 五个正式链 flags 必须保持 false。

## 11. Verification Plan For Future Authorized Code Patch

真正改代码后，后续验证应另行授权。

建议验证顺序：

1. 运行 targeted fake schema tests。
2. 运行 frontend no-write UI contract tests。
3. 启动前端进行只读页面检查。
4. 确认页面显示 preview-only。
5. 确认页面显示 no-write。
6. 确认“生成 Word 文档”不可提交正式生成。
7. 确认 `blocked_reasons` 可读。
8. 确认 evidence 边界可读。
9. 确认未触发正式链。
10. 确认 `output/job/export` 无新增写入。

未经单独授权，不得启动服务、访问端口或执行 smoke。

## 12. Explicit Non-Goals

本实施方案设计不代表以下事项已经执行：

- 未修复前端 UI。
- 未禁用“生成 Word 文档”入口。
- 未增加 preview-only 提示。
- 未增加 no-write 提示。
- 未增加 `blocked_reasons` 展示。
- 未增加 evidence 边界提示。
- 未修改任何代码。
- 未运行 pytest。
- 未启动服务。
- 未运行 Ollama。
- 未执行第三轮 smoke。
- 未进入本地化部署执行。
- 未进入 50 人团队正式部署设计。

## 13. Recommended Next Steps

建议后续步骤：

1. Step 168: frontend no-write UI implementation plan fake schema tests。
   - tests-only。
   - 固化本实施方案结构、UI 状态、验收标准和边界。
   - 不改前端代码。

2. Step 169: frontend no-write UI code patch design。
   - docs-only。
   - 设计真实代码改动范围、文件、最小 patch、验证命令和回滚条件。
   - 不直接改代码。

真正改代码前必须单独授权。

## 14. Safety Conclusion

Step 167 仅完成 frontend no-write UI implementation plan design。

当前系统仍处于 preview-only / no-write 阶段。前端 UI 风险已经被 Step 164 契约和 Step 165 fake schema tests 固化，但尚未实际修复。本实施方案将后续代码修复收束为最小前端 UI 风险控制：明确 preview-only、明确 no-write、禁用或替换“生成 Word 文档”入口、展示 `blocked_reasons`、展示 evidence 边界，并保持所有正式链 flags 为 false。
