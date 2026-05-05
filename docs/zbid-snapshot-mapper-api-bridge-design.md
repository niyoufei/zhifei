# ZBid Snapshot Mapper API Bridge Design

## 1. 阶段定位

本文件定义 ZBid snapshot mapper 后续如需接入 API bridge 时的 mock-only、default-off、no-write 设计边界。当前阶段只做文档设计，不修改 API 代码，不修改 `backend/app/routers/actions_bridge.py`，不新增 API 测试文件。

该设计的目标不是开放 ZBid 到正式成果链，而是为未来可能的只读 API bridge 明确准入条件、feature flag、安全边界和测试要求。

## 2. 当前基线

- 当前 `main` 基线 commit: `8f3ffb6 docs: add ZBid snapshot mapper stage review`.
- 当前稳定标签: `v0.1.36-zbid-snapshot-mapper-stage-review`.
- 已实现 helper: `backend/zhifei_autoplan/zbid_snapshot_mapper.py`.
- 已实现 deterministic tests: `backend/tests/test_zbid_snapshot_mapper.py`.
- 当前 helper 仅为纯函数映射，未接入 API、前端、Ollama、生成链、job/result bundle、build/output、export 或正式 apply。

## 3. 为什么暂不直接改 actions_bridge.py

当前不直接修改 `backend/app/routers/actions_bridge.py`，原因如下:

- `actions_bridge.py` 同时包含主生成、job、review、export、Ollama preview 和 section draft API，误改风险高。
- 该文件已导入 `run_autoplan`、`create_job`、`update_job`、`save_output_artifacts` 等高风险链路。
- ZBid snapshot mapper 当前仍处于 mock-only helper 阶段，尚未完成 API bridge 专项设计和默认关闭验收。
- 直接接 API 容易被误认为 ZBid 已接入正式成果链。
- 后续 API bridge 必须先证明不会写 job/result bundle、build/output，不触发 export，不调用 Ollama，不执行正式 apply。

因此本阶段只记录设计，不写 API 代码。

## 4. API bridge 设计目标

后续如实现 API bridge，其目标只能是:

- 接收 ZBid input snapshot。
- 在 feature flag 启用时调用 `map_zbid_snapshot_to_zdoc_draft_input` 纯函数。
- 返回 draft-only / mock-only / no-write 的映射结果。
- 在 feature flag 未启用时返回 disabled 状态。
- 对 helper 抛出的 `ValueError` 返回结构化错误。
- 不写任何文件。
- 不更新任何 job。
- 不触发任何生成或导出链路。

API bridge 不得成为正式生成入口、正式写回入口或正式导出入口。

## 5. 默认关闭策略

API bridge 必须 default-off。

默认关闭时:

- 不调用 `map_zbid_snapshot_to_zdoc_draft_input`。
- 返回 `ok=false`。
- 返回 `status=disabled`。
- 返回 `warning=zbid_snapshot_mapper_disabled`。
- 不写日志文件。
- 不写 job/build/output/result bundle。
- 不调用任何外部服务。

只有显式 feature flag 开启后，才允许调用 mapper 纯函数。

## 6. 建议 endpoint 草案

建议 endpoint:

```text
POST /actions/zbid/snapshot/map_preview
```

命名原则:

- 使用 `zbid` 明确业务来源。
- 使用 `snapshot` 明确输入是快照。
- 使用 `map_preview` 明确只是映射预览，不是生成、写回或导出。

第一版不建议增加批量 endpoint，不建议增加 apply/reject/rollback endpoint，不建议接入前端按钮。

## 7. request schema 草案

建议 request 结构:

```json
{
  "snapshot": {},
  "requested_by": "user@example.com",
  "request_id": "optional-request-id"
}
```

字段说明:

- `snapshot`: 必填，ZBid input snapshot dict。
- `requested_by`: 可选，仅用于 response audit context，不代表正式写回确认。
- `request_id`: 可选，仅用于调用侧追踪。

request 不得包含:

- `apply`
- `formal_apply`
- `export`
- `generate_async`
- `job`
- `result_bundle`
- `build_output`
- `ollama`
- `llm`

## 8. response schema 草案

建议 enabled 成功响应:

```json
{
  "ok": true,
  "status": "mapped",
  "mode": "draft_only",
  "bridge_type": "mock_only",
  "write_policy": "no_write",
  "source_system": "zbid",
  "draft_input": {},
  "audit": [],
  "warning": null,
  "error": null
}
```

建议 disabled 响应:

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

建议 validation error 响应:

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

response 必须标注 `draft_only` / `mock_only` / `no_write`。

## 9. feature flag 草案

建议 feature flag:

```text
ZBID_SNAPSHOT_MAPPER_API_ENABLED=1
```

默认值:

```text
disabled
```

建议规则:

- 未设置时 disabled。
- 设置为 `1` 时 enabled。
- 其他值视为 disabled。
- disabled 时不得调用 mapper helper。
- feature flag 只控制 mock-only bridge，不代表允许正式写回、生成、job 写入或导出。

## 10. no-write 安全边界

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

测试必须证明 job/build/output 文件数不变。

## 11. 禁止接入链路

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
- DOCX/XLSX/PPTX/HTML export。
- 正式 apply。

API bridge 不得接前端正式成果按钮，不得被前端标记为正式交付能力。

## 12. 与 zbid_snapshot_mapper.py 的关系

API bridge 只允许调用:

- `map_zbid_snapshot_to_zdoc_draft_input`

API bridge 不应重新实现映射逻辑，不应绕过 helper 校验，不应在 API 层拼装正式成果结构。

helper 抛出 `ValueError` 时，API bridge 应转换为 `validation_error` 响应，而不是进入生成、写盘或 fallback 链路。

## 13. 与现有 section draft / Ollama API 的隔离关系

ZBid snapshot mapper API bridge 应与现有 section draft / Ollama API 隔离:

- 不复用 `/actions/ollama/section_draft/build` 作为入口。
- 不复用 `/actions/ollama/section_draft/apply_preview`。
- 不复用 `/actions/ollama/section_draft/reject`。
- 不复用 `/actions/ollama/section_draft/rollback`。
- 不调用 `run_ollama_preview`。
- 不调用 `run_ollama_section_review`。
- 不修改 `section_drafts.py`。

后续如需把 ZBid draft input 交给 section draft build，必须单独设计默认关闭的 draft-only 串联方式，并进行独立验收。

## 14. deterministic API tests 设计思路

后续 API bridge 实现时，测试至少覆盖:

- 默认关闭时返回 disabled。
- 默认关闭时不调用 mapper helper。
- feature flag 启用时 valid snapshot 返回 mapped。
- feature flag 启用时 response 包含 draft_only / mock_only / no_write。
- helper 抛出 `ValueError` 时返回 validation_error。
- forbidden fields 通过 API 返回 validation_error。
- patch 并断言未调用:
  - Ollama。
  - `LLMClient`。
  - `run_autoplan`。
  - `create_job`。
  - `update_job`。
  - `_save_outputs`。
  - `save_output_artifacts`。
  - export/docx/xlsx/pptx/html。
- job/build/output 文件数前后一致。

测试应使用 in-process FastAPI TestClient，不启动服务，不连接 Ollama，不运行真实生成。

## 15. 风险清单与控制措施

风险: mock-only API bridge 被误认为正式生成入口。

- 控制: endpoint 命名使用 `map_preview`，response 标注 `draft_only` / `mock_only` / `no_write`。

风险: API bridge 误触发 job 或 output 写入。

- 控制: 测试 patch 高风险函数，并验证 job/build/output 文件数不变。

风险: helper 校验被 API 层绕过。

- 控制: API 层只调用 helper，不重新拼装正式成果结构。

风险: ZBid mapper 与 Ollama section draft API 混线。

- 控制: 使用独立 endpoint 和独立 feature flag，不复用 Ollama endpoints。

风险: 前端误接正式成果按钮。

- 控制: 第一阶段不接前端；后续前端也只能做只读展示设计。

## 16. 后续实现准入条件

进入 API bridge 实现前必须满足:

- 本设计已审阅。
- 明确 allowed files。
- 明确 forbidden files。
- 创建 guard task spec。
- 明确 feature flag 名称。
- 明确 disabled 响应格式。
- 明确 patch 的禁止调用清单。
- 明确 job/build/output 文件数验证方法。
- 明确不接前端、不接 Ollama、不接生成链、不接导出链。

不满足以上条件时，不应修改 `actions_bridge.py`。

## 17. Codex 后续执行约束

后续 Codex 执行 API bridge 相关任务时:

- 未经明确授权，不修改 `backend/app/routers/actions_bridge.py`。
- 未经明确授权，不修改 API、前端、orchestrator、LLMClient、provider、section_drafts helper。
- 未经明确授权，不新增 API 测试文件。
- 未经明确授权，不启动服务。
- 未经明确授权，不运行 Ollama。
- 未经明确授权，不运行真实生成。
- 未经明确授权，不触发 `/actions/generate_async`。
- 未经明确授权，不触发 job/build/output/result bundle。
- 未经明确授权，不触发 DOCX/XLSX/PPTX/HTML export。
- 未经明确授权，不执行正式 apply。
- 未经明确授权，不执行 `git clean/reset/delete/move`。

## 18. 结论

ZBid snapshot mapper API bridge 只能作为 mock-only、default-off、no-write 的映射预览入口。endpoint 只允许调用 `map_zbid_snapshot_to_zdoc_draft_input` 纯函数，并且 response 必须明确标注 draft-only、mock-only 和 no-write。

下一步不应直接接前端、Ollama、生成链或导出链。若推进实现，必须先做默认关闭 API bridge 和 deterministic API tests，并证明 job/build/output 文件数不变。
