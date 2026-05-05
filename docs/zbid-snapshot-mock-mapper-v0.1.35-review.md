# ZBid Snapshot Mock Mapper v0.1.35 Review

## 1. 阶段定位

本文件记录 `v0.1.35-zbid-snapshot-mock-mapper` 阶段的实现结果、验证结果和后续边界。当前阶段只完成 ZBid input snapshot 到 ZDoc draft-only input 的 mock-only helper 第一版，不代表 ZBid 已接入 ZDoc API、前端、Ollama、生成链或正式成果链。

本复盘用于防止后续误将 helper 直接接入 API、前端、Ollama、`/actions/generate_async`、job/result bundle、build/output 或 export 链路。

## 2. 当前基线

- 当前 `main` 基线 commit: `5af098e feat: add ZBid snapshot mock mapper`.
- 当前稳定标签: `v0.1.35-zbid-snapshot-mock-mapper`.
- 前置设计标签: `v0.1.34-zbid-zdoc-mock-mapper-helper-design`.
- 当前工作状态: helper-only + test-only 已提交并打稳定标签。

## 3. 本阶段新增文件

当前仅新增以下两个文件:

- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- `backend/tests/test_zbid_snapshot_mapper.py`

本阶段未修改任何既有文件。

## 4. 已实现能力

已实现能力:

- 新增 ZBid snapshot 到 ZDoc draft-only input 的纯函数 mapper。
- 支持校验必填顶层字段。
- 支持校验 section task 必填字段。
- 支持校验 draft-only safety boundary。
- 支持递归拒绝 forbidden keys。
- 支持将项目、标段、章节、评分项、素材、审核上下文和版本 hash 映射到 draft-only 输出结构。
- 支持过滤不可用于草稿或敏感的技术素材。
- 支持 deterministic tests 验证无副作用和边界拒绝行为。

该能力仅用于 mock-only helper 层，不写盘、不联网、不触发任何业务运行链路。

## 5. helper 函数行为说明

核心函数:

- `map_zbid_snapshot_to_zdoc_draft_input(snapshot: dict) -> dict`

函数行为:

- 输入为 dict 类型 ZBid snapshot。
- 输出为 dict 类型 ZDoc draft-only input。
- 输出显式包含:
  - `mode: "draft_only"`
  - `source_system: "zbid"`
  - `project_context`
  - `section_input`
  - `review_context`
  - `version_hashes`
  - `safety_boundary`
  - `audit_context`
- 对缺失必填字段抛出 `ValueError`。
- 对 forbidden keys 抛出 `ValueError`。
- 不修改输入对象。
- 不读取文件。
- 不写文件。
- 不访问网络。
- 不依赖外部服务。
- 不导入 OllamaProvider、LLMClient、actions_bridge 或 orchestrator。

## 6. deterministic tests 覆盖范围

测试文件:

- `backend/tests/test_zbid_snapshot_mapper.py`

覆盖范围:

- valid snapshot 映射成功。
- 缺失必填顶层字段报错。
- `section_tasks` 为空报错。
- section task 缺少 `section_id` 报错。
- section task 缺少 `title` 报错。
- section task 缺少 `draft_intent` 报错。
- safety boundary 不满足 draft-only 约束时报错。
- forbidden keys 出现在顶层时报错。
- forbidden keys 出现在嵌套层级时报错。
- 输出不包含 forbidden keys。
- 输入对象不被 helper 修改。
- 敏感素材和不可用于 draft 的素材不会进入输出。

## 7. 已验证结果

已执行验证:

```text
python -m pytest backend/tests/test_zbid_snapshot_mapper.py
```

验证结果:

```text
36 passed in 0.05s
```

本阶段未运行大测试套件，未启动服务，未连接 Ollama，未运行真实生成。

## 8. 当前未接入能力

当前未接入:

- API bridge。
- Streamlit 前端。
- Ollama。
- LLMClient。
- orchestrator。
- section_drafts helper。
- `/actions/generate_async`。
- `/actions/review/apply`。
- job 创建或更新。
- result bundle 写入。
- build/output 写入。
- DOCX/XLSX/PPTX/HTML export。
- 正式 apply。
- 人工确认绕过能力。

当前 helper 仅为纯函数映射，不是生成入口，不是写回入口，不是导出入口。

## 9. 明确禁止直接接入的链路

后续不得直接把 helper 接入以下链路:

- `/actions/generate_async`
- `/actions/review/apply`
- Ollama provider。
- LLMClient。
- orchestrator。
- API 写盘链路。
- 前端正式成果按钮。
- job/result bundle 写入链路。
- build/output 写入链路。
- DOCX/XLSX/PPTX/HTML export 链路。
- 正式正文写回链路。
- 绕过人工确认的 apply 链路。

如需接入任何上述链路，必须先做单独设计、默认关闭实现和专项验收。

## 10. 风险清单与控制措施

风险: helper 被误认为 ZBid 已经接入 ZDoc 正式成果链。

- 控制: 文档和后续任务必须持续标注 mock-only / draft-only。

风险: helper 被直接接到 API 或前端。

- 控制: 先做只读集成盘点和默认关闭 API bridge 设计，不直接接入 UI。

风险: helper 输出被当作正式正文。

- 控制: 输出保留 `mode: "draft_only"` 和 no-write safety boundary，不包含 apply/export/job 字段。

风险: 后续实现绕过人工确认。

- 控制: forbidden keys 包含 apply 相关字段，正式写回必须进入单独治理设计。

风险: 一次 PR 同时接入 helper、API、前端、Ollama、生成和导出。

- 控制: 后续拆分为 helper、import/export 暴露、mock-only API bridge、UI、persist、export 等独立阶段。

## 11. 后续推进建议

若后续推进，只能先做以下低风险任务:

- 只读集成盘点。
- import/export 暴露边界设计。
- 默认关闭的 mock-only API bridge 设计。
- deterministic tests 补强。

不得直接接:

- 前端。
- Ollama。
- 生成链。
- 导出链。
- 正式成果链。
- job/result bundle。
- build/output。
- 正式 apply。

## 12. Codex 后续执行约束

后续 Codex 执行相关任务时:

- docs-only 任务只修改 docs。
- helper-only 任务只修改 helper 和对应测试。
- 未经明确授权，不修改 API、前端、orchestrator、LLMClient、provider、section_drafts helper。
- 未经明确授权，不启动服务。
- 未经明确授权，不运行 Ollama。
- 未经明确授权，不触发 `/actions/generate_async`。
- 未经明确授权，不触发生成链、导出链、job/build/output/result bundle。
- 未经明确授权，不执行正式 apply。
- 未经明确授权，不执行 `git clean/reset/delete/move`。
- 后续任何写盘能力必须单独设计、单独测试、单独验收。

## 13. 结论

`v0.1.35-zbid-snapshot-mock-mapper` 只完成 ZBid snapshot 到 ZDoc draft-only input 的 mock-only 纯函数映射和 deterministic tests。该阶段未接入 API、前端、Ollama、生成链、job/result bundle、build/output、export 或正式 apply。

后续不得直接把 helper 接入正式成果链。建议下一步只做只读集成盘点、import/export 暴露边界设计、默认关闭的 mock-only API bridge 设计或 deterministic tests 补强。
