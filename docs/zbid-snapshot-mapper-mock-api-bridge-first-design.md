# ZBid Snapshot Mapper Mock-only API Bridge First Design

## 1. 阶段定位

本文件定义 ZBid snapshot mapper mock-only API bridge 第一版实现设计。当前阶段只新增 docs-only 设计文档，不写 API 代码，不新增测试文件，不修改任何现有文件。

第一版 bridge 的定位是默认关闭、只读、mock-only、draft-only、no-write 的映射预览入口。它只为后续最小实现提供接口边界、输入输出草案、安全约束和验收条件，不代表 ZBid 已接入 ZDoc 正式生成、正式写回、job/result bundle、build/output 或 export 链路。

## 2. 当前基线

- 工作目录: `/Users/youfeini/Desktop/文档生成系统`
- 当前 `main` 最新 commit: `b7d32ea docs: add local llm sandbox test review`
- 当前稳定标签: `v0.1.39-local-llm-sandbox-test`
- 当前工作区状态: clean
- 已存在 helper: `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- 已存在 helper deterministic tests: `backend/tests/test_zbid_snapshot_mapper.py`
- 已存在前置设计:
  - `docs/zbid-snapshot-mapper-api-bridge-design.md`
  - `docs/zbid-snapshot-mapper-mock-api-bridge-design.md`

当前 helper 是纯函数映射层，只负责把 ZBid input snapshot 转为 ZDoc draft-only input，并拒绝 `apply`、`formal_apply`、`export`、`generate_async`、`job`、`result_bundle`、`build_output`、`ollama`、`llm` 等高风险字段。

## 3. API bridge 设计目标

第一版 API bridge 只允许完成以下目标:

- 提供一个默认关闭的 mock-only endpoint。
- 接收调用方传入的 ZBid snapshot 内存对象。
- feature flag 启用后，仅调用 `map_zbid_snapshot_to_zdoc_draft_input(snapshot)`。
- 返回 ZDoc draft-only input 预览结果。
- response 显式标注 `draft_only`、`mock_only`、`no_write`。
- helper 抛出 `ValueError` 时返回结构化 validation error。
- 不写文件、不建 job、不更新 job、不保存 result bundle、不写 build/output、不触发 export。

第一版不解决正式接入、前端展示、正式正文替换、人工确认流、批量导入、持久化审计和真实生成问题。

## 4. 默认关闭策略

API bridge 必须 default-off。

默认关闭时:

- 不调用 mapper helper。
- 不读取 job/build/output/result bundle。
- 不连接 Ollama。
- 不初始化 `LLMClient`。
- 返回 `ok=false`。
- 返回 `status=disabled`。
- 返回 `warning=zbid_snapshot_mapper_disabled`。
- 返回 `mode=draft_only`。
- 返回 `bridge_type=mock_only`。
- 返回 `write_policy=no_write`。

只有显式设置 feature flag 后，才允许调用 mapper 纯函数。feature flag 只代表允许 mock-only preview，不代表允许生成、写回、job 写入或导出。

## 5. 允许调用的 helper / 输入映射

唯一允许调用的 helper:

- `map_zbid_snapshot_to_zdoc_draft_input(snapshot: dict) -> dict`

允许 request 输入:

- `snapshot`: 必填，ZBid input snapshot dict。
- `requested_by`: 可选，仅用于 response metadata 或 audit context，不代表正式写回确认。
- `request_id`: 可选，仅用于调用侧追踪，不得作为 job id。

API 层约束:

- 不重新实现 mapper 逻辑。
- 不绕过 helper 的 forbidden fields 校验。
- 不在 API 层补写正式成果字段。
- 不把 `requested_by` 解释为 ZDoc 正式 apply 确认人。
- 不从 job/build/output/result bundle 或外部服务补充输入。

## 6. 不允许调用链路

API bridge 不得调用:

- Ollama。
- `LLMClient`。
- `run_autoplan`。
- `create_job`。
- `update_job`。
- `_save_outputs`。
- `save_output_artifacts`。
- `/actions/generate_async`。
- `/actions/review/apply`。
- `run_ollama_preview`。
- `run_ollama_section_review`。
- `build_section_draft`。
- `apply_section_draft`。
- `reject_section_draft`。
- `rollback_section_draft`。
- DOCX/XLSX/PPTX/HTML export。
- 正式 apply 或正式正文替换。

API bridge 不得接前端正式成果按钮，不得修改当前章节正文，不得修改 `run_result`，不得创建任何新产物目录。

## 7. request / response schema 草案

建议 endpoint:

```text
POST /actions/zbid/snapshot/map_preview
```

建议 request:

```json
{
  "snapshot": {},
  "requested_by": "user@example.com",
  "request_id": "optional-request-id"
}
```

建议 disabled response:

```json
{
  "ok": false,
  "status": "disabled",
  "mode": "draft_only",
  "bridge_type": "mock_only",
  "write_policy": "no_write",
  "draft_input": null,
  "audit": [],
  "warning": "zbid_snapshot_mapper_disabled",
  "error": null
}
```

建议 mapped response:

```json
{
  "ok": true,
  "status": "mapped",
  "mode": "draft_only",
  "bridge_type": "mock_only",
  "write_policy": "no_write",
  "draft_input": {},
  "audit": [
    {
      "action_type": "mapped",
      "source_system": "zbid",
      "request_id": "optional-request-id",
      "requested_by": "user@example.com"
    }
  ],
  "warning": null,
  "error": null
}
```

建议 validation error response:

```json
{
  "ok": false,
  "status": "validation_error",
  "mode": "draft_only",
  "bridge_type": "mock_only",
  "write_policy": "no_write",
  "draft_input": null,
  "audit": [],
  "warning": null,
  "error": "..."
}
```

response 不得包含正式 apply、export、job、result bundle、build/output 写入目标或 Ollama 执行信息。

## 8. feature flag 草案

建议 feature flag:

```text
ZBID_SNAPSHOT_MAPPER_API_ENABLED=1
```

规则:

- 未设置时 disabled。
- 设置为 `1` 时 enabled。
- 设置为其他值时 disabled。
- disabled 时不得调用 mapper helper。
- enabled 时只允许调用 mapper helper。
- enabled 不代表允许前端、Ollama、生成链、写回链、job/result bundle 或 export。

## 9. no-write 安全边界

第一版 API bridge 必须保持 no-write:

- 不写 job/result bundle。
- 不写 build/output。
- 不写本地文件。
- 不创建 job。
- 不更新 job。
- 不保存 output artifacts。
- 不触发 DOCX/XLSX/PPTX/HTML export。
- 不执行正式 apply。
- 不修改 section draft helper。
- 不修改 `run_result`。
- 不修改当前章节正文。
- 不写系统剪贴板。
- 不安装依赖。
- 不启动服务。

后续实现验收必须记录 job/build/output 文件数前后一致，并 patch 高风险函数证明没有调用写入链。

## 10. 与现有 section draft / Ollama API 隔离关系

第一版 API bridge 必须与现有 section draft / Ollama API 隔离:

- 不复用 `/actions/ollama/section_draft/build`。
- 不复用 `/actions/ollama/section_draft/apply_preview`。
- 不复用 `/actions/ollama/section_draft/reject`。
- 不复用 `/actions/ollama/section_draft/rollback`。
- 不调用 `run_ollama_preview`。
- 不调用 `run_ollama_section_review`。
- 不连接 Ollama。
- 不初始化 Ollama provider。
- 不修改 `backend/zhifei_autoplan/section_drafts.py`。
- 不修改 `backend/zhifei_autoplan/utils/llm_client.py`。

如未来需要把 ZBid mapped draft input 串到 section draft build，必须单独设计、单独实现、单独验收，不得在第一版 bridge 中顺手完成。

## 11. deterministic API tests 设计思路

后续进入代码实现时，deterministic API tests 至少覆盖:

- feature flag 默认关闭返回 disabled。
- 默认关闭时不调用 mapper helper。
- feature flag enabled 后 valid snapshot 返回 mapped。
- mapped response 包含 `draft_only`、`mock_only`、`no_write`。
- helper `ValueError` 转换为 validation error。
- request 中 forbidden fields 返回 validation error。
- response 不包含 apply/export/job/result bundle/build/output/Ollama 字段。
- patch 并断言未调用 Ollama、`LLMClient`、`run_autoplan`、`create_job`、`update_job`、`_save_outputs`、`save_output_artifacts`、export/docx/xlsx/pptx/html。
- job/build/output 文件数前后一致。

测试方式:

- 使用 in-process FastAPI TestClient 或直接 endpoint 函数调用。
- 不启动服务。
- 不连接 Ollama。
- 不运行真实生成。
- 不写 job/build/output/result bundle。
- 不触发 export。

## 12. 风险清单与控制措施

风险: mock-only endpoint 被误认为正式生成入口。

- 控制: endpoint 使用 `map_preview` 命名，response 强制标注 `draft_only`、`mock_only`、`no_write`。

风险: API 层误触发高风险链路。

- 控制: tests patch 高风险函数并断言未调用，同时记录 job/build/output 文件数。

风险: helper 校验被绕过。

- 控制: API 层只调用 `map_zbid_snapshot_to_zdoc_draft_input`，不重写 mapper 逻辑。

风险: 与 Ollama section draft API 混线。

- 控制: 使用独立 endpoint、独立 feature flag、独立 tests，不复用 Ollama endpoints。

风险: 前端误接正式成果按钮。

- 控制: 第一版不接前端；后续前端如需展示，也只能做只读 preview。

风险: docs-only 设计被误解为已实现。

- 控制: 文档、提交说明和后续任务必须持续标注 docs-only / design-only，进入实现前重新确认 allowed files。

## 13. 后续实现准入条件

进入代码实现前必须满足:

- 明确本阶段已从 docs-only 切换到实现阶段。
- 明确 allowed files。
- 明确 forbidden files。
- 明确 feature flag 名称和默认值。
- 明确 endpoint 名称。
- 明确 disabled / mapped / validation_error response。
- 明确 patch 禁止调用清单。
- 明确 job/build/output 文件数验证方法。
- 明确不接前端。
- 明确不接 Ollama。
- 明确不接生成链。
- 明确不接导出链。
- 明确不做正式 apply。

建议第一版实现允许文件仅包括:

- `backend/app/routers/actions_bridge.py`
- `backend/tests/test_actions_zbid_snapshot_mapper_api.py`

不建议修改:

- `app.py`
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- `backend/zhifei_autoplan/section_drafts.py`
- `backend/zhifei_autoplan/orchestrator.py`
- `backend/zhifei_autoplan/utils/llm_client.py`
- provider 文件
- 前端 UI 文件
- job/build/output/export 相关代码

## 14. Codex 后续执行约束

后续 Codex 执行 API bridge 相关任务时:

- 未经明确授权，不修改代码。
- 未经明确授权，不新增测试文件。
- 未经明确授权，不启动服务。
- 未经明确授权，不连接 Ollama。
- 未经明确授权，不运行真实生成。
- 未经明确授权，不触发 `/actions/generate_async`。
- 未经明确授权，不触发 `/actions/review/apply`。
- 未经明确授权，不写 job/build/output/result bundle。
- 未经明确授权，不触发 DOCX/XLSX/PPTX/HTML export。
- 未经明确授权，不执行正式 apply。
- 未经明确授权，不修改前端。
- 未经明确授权，不修改 section draft helper。
- 未经明确授权，不执行 `git add`、commit、PR、merge 或 tag。
- 未经明确授权，不执行 `git clean`、`git reset --hard`、删除、移动或清理文件。
- 未经明确授权，不安装依赖。

## 15. 结论

ZBid snapshot mapper mock-only API bridge 第一版应只提供默认关闭、无写盘、无生成、无导出的映射预览入口。endpoint 只允许调用 `map_zbid_snapshot_to_zdoc_draft_input` 纯函数，并必须在 response 中明确标注 draft-only、mock-only 和 no-write。

本阶段仅完成 docs-only 实现设计。下一步如进入实现，必须先重新确认实现边界和 allowed files，再做严格 scoped API bridge 与 deterministic API tests；不得直接接前端、Ollama、生成链、导出链或正式成果链。
