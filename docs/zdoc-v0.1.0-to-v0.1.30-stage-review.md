# ZDoc v0.1.0 to v0.1.30 Stage Review

## 1. 阶段定位

本阶段的主线是把 ZDoc 的 Ollama 能力从人工 sidecar 预览，逐步推进到可审计、可验证、但仍不进入正式成果链路的 draft-only 写回预览链路。

截至 `v0.1.30-zdoc-formal-write-back-governance-design`，当前阶段已经完成了 sidecar、provider、no-write smoke、section draft helper、draft-only API、draft-only UI、验收记录和正式写回治理设计。当前阶段仍明确停留在“预览、草稿、治理设计”边界内，未开放正式正文写回、job/result bundle 写入或导出联动。

## 2. 当前基线信息

- 当前 `main` 基线 commit: `d4d4b84c37d69eff194b0e1f4ee2546d55f619a2`.
- 当前稳定标签: `v0.1.30-zdoc-formal-write-back-governance-design`.
- 最新阶段文档:
  - `docs/ollama-write-back-confirmation-design.md`.
  - `docs/ollama-formal-write-back-governance-design.md`.
  - `docs/ppt-html-deck-adapter-design.md`.
- 本阶段仍以 no-write、default-off、单独验收、显式人工确认为核心边界。

## 3. 已完成能力总览

### Ollama sidecar 能力

- 已有手动 Ollama 预览接口和前端入口。
- 已有章节复核相关的人工触发能力和 UI 验证记录。
- sidecar 能力定位为人工触发、默认隔离，不自动进入主生成链路。
- 相关验证记录保留在 `docs/ollama-preview-validation.md`。

### Ollama provider 能力

- 已完成 Ollama provider 设计和分阶段验证记录。
- `OllamaProvider` 通过 feature flag 进入 `LLMClient` 的可选 provider 路径。
- 已记录真实验证和 fallback 行为。
- provider 仍受 default-off 和 no-write 边界约束，不等同于开放正式生成写入。

### no-write 主链烟测

- 已完成 no-write main-chain smoke 设计、端点和验证记录。
- no-write smoke 允许受控验证 Ollama 进入主链的可行性。
- 当前仍不开放 `/actions/generate_async` 给 Ollama 写入路径。
- no-write smoke 不写 job、result bundle、build、output 或 export 文件。

### draft-only 写回预览链路

- 已完成 `section_drafts.py` helper 层，包含 draft build、diff、audit、apply、reject、rollback 的纯数据能力。
- 已完成后端 draft-only endpoints:
  - `POST /actions/ollama/section_draft/build`.
  - `POST /actions/ollama/section_draft/apply_preview`.
  - `POST /actions/ollama/section_draft/reject`.
  - `POST /actions/ollama/section_draft/rollback`.
- 已完成前端 draft-only UI:
  - `生成草稿对比预览（不写回）`.
  - `应用预览（不写回）`.
  - `拒绝草稿`.
  - `回滚预览`.
- 该链路只展示 draft、diff、audit、status 和 decision 数据。
- 该链路不修改 `run_result`，不替换当前章节正文，不写正式成果。

### 正式写回治理设计

- 已新增 `docs/ollama-formal-write-back-governance-design.md`.
- 文档定义了正式写回前的权限、二次确认、审计字段、冲突检查、rollback、job/result bundle、export 和 feature flag 边界。
- 设计结论是正式写回必须继续拆阶段推进，不应直接从 preview UI 进入正式正文写回。

### guard 工具

- 已完成 `scripts/guards/zdoc_guard.py` 及示例 task spec。
- guard 负责 preflight、scope、verify、pr-summary 和 tag-check 等检查。
- guard 定位为检查工具，不自动合并、不自动打标签、不启动服务、不连接 Ollama。
- 常用边界包括文件范围校验、`git diff --check`、指定测试命令和 job/build/output 文件数快照。

### PPT/HTML deck 能力规划

- 已完成 `docs/ppt-html-deck-adapter-design.md`.
- 当前定位是 HTML deck / web presentation sidecar 规划。
- 当前未承诺 native PPTX 输出。
- 当前未接入 DOCX/XLSX/export 主链路。
- 若后续推进，应独立设计 HTML package 或 PPTX 路径，不应混入 ZDoc 正文生成链路。

## 4. 已验证能力与验证方式

- 使用静态源码检查验证前端 draft-only UI 的按钮、endpoint、session state 和禁止路径。
- 使用 `python3 -m py_compile app.py` 验证前端入口语法。
- 使用 in-process FastAPI/TestClient 或直接函数测试验证 draft-only API，不启动服务。
- 使用 patch/mock 断言以下路径未触发:
  - `run_autoplan`.
  - `LLMClient`.
  - `create_job`.
  - `update_job`.
  - `_save_outputs`.
  - `save_output_artifacts`.
  - export/docx/xlsx 相关函数。
- 使用文件数快照验证 job/build/output 未被写入。
- 使用 `git diff --check` 验证 PR diff 基础卫生。
- 使用 `gh pr view`、`gh pr diff --name-only`、`gh pr checks --watch` 和本地 guard 结果作为合并门禁。
- 对 `no checks reported` 的 PR，只在文件范围、local checks、guard 和 diff hygiene 全部通过时接受。

## 5. 当前仍未开放的高风险能力

- 未开放正式正文写回。
- 未开放自动覆盖章节正文。
- 未开放 apply 到正式 `run_result`。
- 未开放 job/result bundle 写入。
- 未开放 build/output 写入。
- 未开放 DOCX/XLSX/PPTX/HTML 自动导出。
- 未开放 `/actions/generate_async` 的 Ollama 写入路径。
- 未开放无 audit 的写回。
- 未开放无人工确认的写回。
- 未开放 draft store 持久化。
- 未开放 persisted draft 到正式成果链路的提升路径。

## 6. 关键稳定标签索引

- `v0.1.0-zdoc-pr2-split-baseline`: PR2 拆分基线。
- `v0.1.1-zdoc-ollama-preview-baseline`: Ollama preview 基线。
- `v0.1.8-zdoc-ollama-provider-design-baseline`: Ollama provider 设计基线。
- `v0.1.10-zdoc-llm-client-ollama-provider-flag`: LLMClient Ollama provider flag 基线。
- `v0.1.13-zdoc-ollama-main-chain-no-write-guard`: no-write 主链保护基线。
- `v0.1.17-zdoc-ollama-no-write-smoke-endpoint-validation`: no-write smoke endpoint 验收基线。
- `v0.1.18-zdoc-ollama-write-back-confirmation-design`: 写回确认边界设计基线。
- `v0.1.19-zdoc-guarded-pr-checks`: guard 工作流检查基线。
- `v0.1.20-zdoc-section-draft-helpers`: section draft helper 基线。
- `v0.1.21-zdoc-section-draft-build-endpoint`: section draft build endpoint 基线。
- `v0.1.22-zdoc-guard-risky-command-fix`: guard 风险命令识别修复基线。
- `v0.1.23-zdoc-section-draft-build-validation`: section draft build 验收基线。
- `v0.1.24-zdoc-ppt-html-deck-adapter-design`: PPT/HTML deck adapter 设计基线。
- `v0.1.25-zdoc-section-draft-preview-ui`: section draft preview UI 基线。
- `v0.1.26-zdoc-section-draft-preview-ui-validation`: section draft preview UI 验收基线。
- `v0.1.27-zdoc-section-draft-decision-api`: section draft decision API 基线。
- `v0.1.28-zdoc-section-draft-decision-ui`: section draft decision UI 基线。
- `v0.1.29-zdoc-section-draft-decision-ui-validation`: section draft decision UI 验收记录基线。
- `v0.1.30-zdoc-formal-write-back-governance-design`: 正式写回治理设计基线。

## 7. 架构边界与风险控制原则

- default-off: 新能力默认关闭，必须由 feature flag 明确开启。
- no-write first: 新链路先以 no-write / preview / mock-only 验证，不直接写正式产物。
- docs before code: 高风险写回、持久化、导出联动必须先有设计文档。
- scope first: 每个 PR 必须先确认实际变更文件范围。
- one surface per PR: helper、API、UI、persist、job update、result bundle、export 必须拆开。
- human confirmation: 正式写回前必须有人工确认和二次确认。
- audit required: 没有 audit record 的写回不得进入正式链路。
- rollback before apply: 正式持久化前必须先设计 rollback。
- export separated: 写回不得自动触发 DOCX/XLSX/PPTX/HTML 导出。
- counts as proof: 涉及 no-write 边界时保留 job/build/output 文件数快照。

## 8. 后续路线建议

建议先暂停正式写回代码实现，不要直接从当前 draft-only UI 推进到正式正文覆盖。

更安全的下一步是完成 ZDoc 阶段归档，然后再决定是否进入 ZBid。若继续 ZDoc，建议从低风险到高风险按以下顺序推进:

1. draft store helper 设计或 mock-only helper。
2. draft store 数据结构和 deterministic tests。
3. default-off draft persist API。
4. formal apply preview with audit。
5. persisted draft only 的 apply，不写 result bundle。
6. result bundle 写入专项设计。
7. export 前版本选择设计。

如果转入 ZBid，建议先冻结当前 ZDoc 基线和阶段总结，不在同一轮里混入 ZDoc 正式写回实现。

## 9. Codex 后续执行约束

- 未经明确授权，不启动服务。
- 未经明确授权，不连接 Ollama。
- 未经明确授权，不运行真实生成。
- 未经明确授权，不执行 `/actions/generate_async`。
- 未经明确授权，不触发 DOCX/XLSX/PPTX/HTML 导出。
- 未经明确授权，不写 job/build/output/result bundle。
- 未经明确授权，不执行 `git clean/reset/delete/move`。
- docs-only 任务只修改 docs 文件。
- helper-only 任务只修改 helper 和对应测试。
- API-only 任务不得顺手接前端。
- UI-only 任务不得修改后端和正式成果链路。
- 合并前必须确认实际 diff 文件范围。
- 打标签前必须确认 `main`、HEAD、工作区 clean 和远端标签不存在。

## 10. 结论

ZDoc v0.1.0 到 v0.1.30 已完成从 Ollama sidecar 到 draft-only section draft decision UI 的阶段性闭环，并补齐了正式写回前的治理设计。

当前系统具备受控预览、draft-only 决策展示、审计数据展示、no-write 验收和 guard 检查能力。当前系统仍未开放正式正文写回、job/result bundle 写入、build/output 写入和 export 联动。

建议将 `v0.1.30-zdoc-formal-write-back-governance-design` 视为 ZDoc 当前阶段的冻结基线。下一步应先完成阶段归档或 draft store 的 mock-only 设计，不应直接进入正式写回代码实现。
