# ZBid Snapshot Mapper Mock API Bridge Design

## 1. 阶段定位

本文件记录 ZBid snapshot mapper mock-only API bridge 第一版实现前的设计边界。当前阶段只做 docs-only 设计，不写 API 代码，不新增测试文件，不修改任何现有文件。

第一版 API bridge 的定位是默认关闭、只读映射、mock-only preview。它不得进入正式生成、正式写回、job/result bundle、build/output 或 export 链路。

## 2. 当前基线

- 当前 `main` 基线 commit: `593fe33 docs: add ZBid snapshot mapper API bridge design`.
- 当前稳定标签: `v0.1.37-zbid-snapshot-mapper-api-bridge-design`.
- 已存在 helper: `backend/zhifei_autoplan/zbid_snapshot_mapper.py`.
- 已存在 helper deterministic tests: `backend/tests/test_zbid_snapshot_mapper.py`.
- 当前 helper 仅为纯函数映射，未接入 API、前端、Ollama、生成链、导出链或正式成果链。

## 3. mock-only API bridge 第一版目标

第一版目标:

- 新增一个 mock-only API endpoint，用于把 ZBid snapshot 映射为 ZDoc draft-only input。
- endpoint 默认关闭。
- endpoint 启用后只调用 `map_zbid_snapshot_to_zdoc_draft_input`。
- response 明确标注 `draft_only`、`mock_only`、`no_write`。
- helper 抛出 `ValueError` 时返回结构化 validation error。
- 不写任何文件。
- 不触发任何生成、写回或导出链路。

第一版不做:

- 不接前端。
- 不接 Ollama。
- 不接 LLMClient。
- 不接 `run_autoplan`。
- 不接正式 apply。
- 不接 job/result bundle。
- 不接 build/output。
- 不接 export。

## 4. 默认关闭策略

API bridge 必须 default-off。

默认关闭时:

- 不调用 helper。
- 返回 `ok=false`。
- 返回 `status=disabled`。
- 返回 `warning=zbid_snapshot_mapper_disabled`。
- 返回 `mode=draft_only`。
- 返回 `bridge_type=mock_only`。
- 返回 `write_policy=no_write`。
- 不读取 job/build/output。
- 不写 job/build/output/result bundle。

只有显式 feature flag 开启后，才允许调用 helper 纯函数。

## 5. 允许调用的 helper / 输入映射

endpoint 只允许调用:

- `map_zbid_snapshot_to_zdoc_draft_input(snapshot: dict) -> dict`

允许输入:

- request body 中的 `snapshot` dict。
- 可选 `requested_by`，只进入 audit 或 response metadata，不代表正式确认。
- 可选 `request_id`，只用于调用侧追踪。

API 层不应重新实现 mapper 逻辑，不应绕过 helper 校验，不应补写正式成果字段。

## 6. 不允许调用链路

endpoint 不得调用:

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
- `build_section_draft`、`apply_section_draft`、`reject_section_draft`、`rollback_section_draft`。
- DOCX/XLSX/PPTX/HTML export。
- 正式 apply。

endpoint 不得接前端正式成果按钮，不得修改当前章节正文，不得修改 `run_result`。

## 7. request / response schema 草案

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
  "audit": [],
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

response 不得包含正式 apply、export、job、result bundle 或 build/output 写入目标。

## 8. feature flag 草案

建议 feature flag:

```text
ZBID_SNAPSHOT_MAPPER_API_ENABLED=1
```

规则:

- 未设置时 disabled。
- 设置为 `1` 时 enabled。
- 其他值视为 disabled。
- disabled 时不调用 helper。
- enabled 只代表允许 mock-only mapper preview，不代表允许生成、写回、job 写入或导出。

## 9. no-write 安全边界

API bridge 必须保持 no-write:

- 不写 job/result bundle。
- 不写 build/output。
- 不写本地文件。
- 不创建 job。
- 不更新 job。
- 不保存 output artifacts。
- 不触发 DOCX/XLSX/PPTX/HTML export。
- 不执行正式 apply。
- 不修改 section_drafts helper。
- 不修改 `run_result`。
- 不修改当前章节正文。

测试必须记录 job/build/output 文件数前后一致。

## 10. 与现有 section draft / Ollama API 隔离关系

第一版 API bridge 必须与 section draft / Ollama API 隔离:

- 不复用 `/actions/ollama/section_draft/build`。
- 不复用 `/actions/ollama/section_draft/apply_preview`。
- 不复用 `/actions/ollama/section_draft/reject`。
- 不复用 `/actions/ollama/section_draft/rollback`。
- 不调用 `run_ollama_preview`。
- 不调用 `run_ollama_section_review`。
- 不修改 `section_drafts.py`。
- 不连接 Ollama。

如未来需要把 ZBid mapped draft input 串到 section draft build，必须单独设计、单独实现、单独验收。

## 11. deterministic API tests 设计思路

后续实现时，API tests 至少覆盖:

- 默认关闭返回 disabled。
- 默认关闭不调用 helper。
- feature flag enabled 后 valid snapshot 返回 mapped。
- enabled response 包含 `draft_only`、`mock_only`、`no_write`。
- helper `ValueError` 转换为 validation error。
- forbidden fields 返回 validation error。
- patch 并断言未调用 Ollama、LLMClient、run_autoplan、create_job、update_job、save_output_artifacts、export 链路。
- job/build/output 文件数前后一致。

测试方式:

- 使用 in-process FastAPI TestClient。
- 不启动服务。
- 不连接 Ollama。
- 不运行真实生成。
- 不写 job/build/output/result bundle。

## 12. 风险清单与控制措施

风险: mock-only endpoint 被误认为正式生成入口。

- 控制: endpoint 命名使用 `map_preview`，response 强制标注 mock-only/no-write。

风险: API 层误触发高风险链路。

- 控制: 测试 patch 高风险函数并断言未调用。

风险: helper 校验被绕过。

- 控制: API 层只调用 helper，不重新拼装正式成果结构。

风险: 与 Ollama section draft API 混线。

- 控制: 使用独立 endpoint、独立 feature flag、独立测试文件。

风险: 直接接前端按钮导致用户误用。

- 控制: 第一版不接前端，后续前端也只能做只读展示设计。

## 13. 后续实现准入条件

进入代码实现前必须满足:

- 明确 allowed files。
- 明确 forbidden files。
- 创建 guard task spec。
- 明确 feature flag 名称。
- 明确 disabled / mapped / validation_error response。
- 明确 patch 禁止调用清单。
- 明确 job/build/output 文件数验证方式。
- 明确不接前端、不接 Ollama、不接生成链、不接导出链。

建议第一版允许文件仅包括:

- `backend/app/routers/actions_bridge.py`
- `backend/tests/test_actions_zbid_snapshot_mapper_api.py`

不建议修改:

- `app.py`
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- `backend/zhifei_autoplan/section_drafts.py`
- `backend/zhifei_autoplan/orchestrator.py`
- `backend/zhifei_autoplan/utils/llm_client.py`
- provider 文件
- docs 以外的其他业务链路文件

## 14. Codex 后续执行约束

后续 Codex 执行 API bridge 实现时:

- 不得启动服务。
- 不得连接 Ollama。
- 不得运行真实生成。
- 不得触发 `/actions/generate_async`。
- 不得触发 `/actions/review/apply`。
- 不得写 job/build/output/result bundle。
- 不得触发 DOCX/XLSX/PPTX/HTML export。
- 不得执行正式 apply。
- 不得修改前端。
- 不得修改 section_drafts helper。
- 不得执行 `git clean/reset/delete/move`。

## 15. 结论

ZBid snapshot mapper mock-only API bridge 第一版应只提供默认关闭、无写盘、无生成、无导出的映射预览入口。endpoint 只允许调用 `map_zbid_snapshot_to_zdoc_draft_input` 纯函数，并必须在 response 中明确标注 draft-only、mock-only 和 no-write。

下一步若进入实现，应先做严格 scoped API bridge 和 deterministic API tests；不得直接接前端、Ollama、生成链、导出链或正式成果链。
