# ZDoc Frontend No-Write UI Code Patch Design

## 1. Scope

本文档是 Step 169 的 docs-only frontend no-write UI code patch design。

目标是为后续真正修改前端代码提供最小、安全、可验收的 patch 设计，明确修改范围、按钮处理、提示文案、状态展示、验收标准和禁止触发项。

本步不修改代码，不修改 frontend，不修改 tests，不修改既有 docs，不运行 pytest，不启动后端或前端服务，不运行 Ollama，不访问端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不写 `output/job/export`，不进入本地化部署执行，不进入 50 人团队正式部署设计。

## 2. Current UI Risk Restatement

Step 162 / Step 163 已确认当前前端 UI 风险，Step 164 / Step 165 / Step 167 已分别完成契约设计、fake schema tests 和实施方案设计。

当前风险仍未修复：

- “生成 Word 文档”入口仍存在。
- 页面缺少 preview-only 提示。
- 页面缺少 no-write 提示。
- 页面缺少 `blocked_reasons` 展示。
- 页面缺少 evidence 边界提示。
- 用户可能误认为 Word 正式生成已开放。
- 用户可能误认为 Word 正式导出已开放。
- 用户可能误认为 preview 是正式正文。
- 用户可能误认为 advisory 是 evidence。

这些风险是前端 UI 风险，不代表正式链已经被触发。

## 3. Future Code Patch Scope

以下仅为未来代码修复范围设计，本步不得执行。

后续真正改代码前，需要先定位：

- 前端页面文件。
- “生成 Word 文档”按钮或入口。
- 页面状态提示区域。
- `blocked_reasons` 展示区域。
- advisory / evidence 边界提示区域。

基于 Step 162 的页面观察，未来授权修复时的候选范围可能包括：

- `frontend_web/templates/index.html`
- `frontend_web/static/style.css`

如后续需要从后端注入 no-write / preview-only 状态字段，必须另行设计并单独授权；默认 patch 应优先采用最小前端模板和静态提示修改，不进入正式生成链、DOCX 导出链、review/apply、ZBid 写回链或 `output/job/export` 写入链。

## 4. Button Patch Design

“生成 Word 文档”入口必须作为后续 patch 的首要风险控制点。

未来代码修复应满足：

1. preview-only 阶段禁用“生成 Word 文档”。
2. 按钮文案改为“正式导出未开放”或同等提示。
3. 在按钮附近显示 no-write 说明。
4. 不得表现为可提交正式生成。
5. 不得触发 `/generate`。
6. 不得触发 `/export_docx`。
7. 不得生成 DOCX。
8. 不得写 `output/job/export`。

推荐最小 patch 方案：

- 将按钮增加 `disabled`。
- 将按钮文案改为“正式导出未开放”。
- 将相关 form 设为不可提交或移除正式生成语义。
- 在入口附近添加说明：“当前仅预览，不写回正式正文，不生成 DOCX，不写 output/job/export。”

禁止方案：

- 保留可提交的“生成 Word 文档”按钮。
- 只改颜色但仍可点击。
- 通过前端隐藏风险但保留可执行 form 提交。
- 引入任何 `/generate` 或 `/export_docx` 调用。

## 5. Status Copy Patch Design

未来代码修复必须在页面上明确展示当前状态。

### 5.1 Preview-Only Copy

页面必须显示：

> 当前为 preview-only 预览阶段。

并解释：

- preview 不是正式正文。
- preview 不代表已写回。
- preview 不代表 DOCX 已可导出。
- preview 不代表 ZBid 写回已开放。

### 5.2 No-Write Copy

页面必须显示：

> 当前为 no-write 状态：不写回正式正文，不更新成果，不触发导出，不写 output/job/export。

并解释：

- 不写正式正文。
- 不写 `output/job/export`。
- 不触发 DOCX 导出。
- 不触发 review/apply。
- 不触发 ZBid 写回。
- 不执行 formal writeback。

### 5.3 Blocked Reasons Copy

页面必须展示 `blocked_reasons`。

建议初始展示：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `docx_export_blocked_current_stage`
- `review_apply_blocked_current_stage`
- `zbid_writeback_blocked_current_stage`
- `formal_writeback_blocked_current_stage`
- `output_write_blocked_current_stage`

展示要求：

- 文本可读。
- 不仅依赖颜色。
- 不隐藏在调试信息中。
- 与正式链禁用入口邻近展示。

### 5.4 Advisory / Evidence Boundary Copy

页面必须展示：

> AI 建议仅供预览，不是证据。

并解释：

- preview advisory 不得作为 evidence。
- shadow candidate / patch / diff / rollback / dry-run 不得作为 evidence。
- evidence 必须来自可验证资料锚点。
- scoring clause refs 必须指向可验证评分条款。

## 6. Formal Chain Entry Control

未来 patch 必须保证所有正式链入口 disabled、hidden 或明确未开放：

- DOCX export disabled。
- review/apply disabled。
- ZBid writeback disabled。
- formal writeback disabled。
- output write disabled。

前端不得提供以下可执行入口：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback
- formal writeback
- output write

即使某入口暂时不存在，页面也应明确说明该能力当前未开放，避免用户误判。

## 7. Formal Flags Invariant

后续代码修复不得改变正式链 flags 的当前不变量：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

UI 展示、按钮状态、blocked reasons 和 preview-only 文案均不得被解释为正式链授权。

## 8. Acceptance Criteria

后续真实代码 patch 完成后，必须满足以下验收标准：

1. 页面可见 preview-only。
2. 页面可见 no-write。
3. 用户不能误认为 Word 可正式生成。
4. 用户不能误认为 Word 可正式导出。
5. “生成 Word 文档”不得表现为可正式提交。
6. 如保留入口，必须 disabled 或显示“正式导出未开放”。
7. advisory 不得被展示为 evidence。
8. preview 不得被展示为正式正文。
9. `blocked_reasons` 可读。
10. 正式链入口禁用或明确未开放。
11. 五个正式链 flags 恒 false。
12. UI 不触发 `/generate`。
13. UI 不触发 `/export_docx`。
14. UI 不触发 `/review/apply`。
15. UI 不触发 ZBid 写回。
16. UI 不写 `output/job/export`。

## 9. Suggested Future Verification

真正改代码后，验证应另行授权。

建议验证命令范围：

- targeted frontend no-write UI tests。
- fake schema tests。
- import isolation tests。
- 如用户另行授权，再启动前端进行只读页面检查。
- 如用户另行授权，再检查 output/job/export 前后差异。

不得默认运行：

- full backend tests。
- Ollama。
- 后端服务。
- 前端服务。
- 任意本地端口访问。
- 真实 smoke。

## 10. Explicit Non-Goals

本设计不代表以下事项已经执行：

- 未修改前端代码。
- 未修改 tests。
- 未禁用真实按钮。
- 未增加真实页面文案。
- 未增加真实 `blocked_reasons` 展示。
- 未增加真实 evidence 边界提示。
- 未运行 pytest。
- 未启动服务。
- 未运行 Ollama。
- 未访问端口。
- 未执行第三轮 smoke。
- 未进入本地化部署执行。
- 未进入 50 人团队正式部署设计。

## 11. Recommended Next Steps

建议下一步为：

ZDoc Step 170: frontend no-write UI code patch design fake schema tests.

Step 170 应为 tests-only，用 fake schema tests 固化本 code patch design 的结构、按钮修复设计、状态提示设计、正式链入口控制、验收标准和 no-side-effect 边界。

后续：

ZDoc Step 171: frontend no-write UI code patch implementation.

Step 171 需用户单独授权后才可真正修改前端代码。

## 12. Safety Conclusion

Step 169 仅完成 frontend no-write UI code patch design。

当前系统仍处于 preview-only / no-write 阶段。前端 UI 风险尚未实际修复。未来代码 patch 应保持最小范围，仅处理前端展示与按钮状态，明确 preview-only、no-write、`blocked_reasons`、advisory/evidence 边界，并保持所有正式链入口 blocked、所有正式链 flags 为 false。
