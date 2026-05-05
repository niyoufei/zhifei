# ZBid Snapshot Mock API Bridge Smoke Test Design

## 1. 阶段定位

本文件定义 ZBid snapshot mock API bridge 后续 smoke test 的设计边界。当前阶段只做 docs-only 设计，不写测试代码，不修改 API、业务代码、前端或 guard 工具。

smoke test 第一版的定位是验证 `v0.1.41-zbid-snapshot-mock-api-bridge` 已实现 endpoint 的最小可用性和 no-write 边界。它不是生产接入验收，不代表允许接入前端、Ollama、生成链、导出链、job/result bundle、build/output 或正式写回链。

## 2. 当前基线

- 当前 `main` 最新 commit: `a785fa8 docs: add ZBid snapshot mock API bridge stage review`
- 当前稳定标签: `v0.1.42-zbid-snapshot-mock-api-bridge-stage-review`
- 已实现 endpoint: `POST /actions/zbid/snapshot_draft_input/preview`
- 已实现 feature flag: `ZDOC_ZBID_MOCK_API_ENABLED=1`
- 已有 deterministic API tests: `backend/tests/test_actions_zbid_snapshot_mapper_api.py`
- 已有 mapper tests: `backend/tests/test_zbid_snapshot_mapper.py`

## 3. smoke test 设计目标

smoke test 第一版目标:

- 验证 endpoint default-off 行为仍可控。
- 验证 feature flag enabled 后 valid snapshot 能完成 mock-only 映射。
- 验证 invalid snapshot 和 forbidden key 均返回受控 400。
- 验证 response 保持 `mock_only`、`draft_only`、`no_write`。
- 验证 response 不包含正式成果语义字段。
- 验证 `backend/data/autoplan/jobs`、`build`、`output` 文件数测试前后不变。
- 验证不调用 Ollama、LLMClient、run_autoplan、job 写入、output 写入、export 或 section draft apply/reject/rollback。

该 smoke test 只证明 mock API bridge 的最小健康状态，不扩大为端到端业务验收。

## 4. 为什么不启动服务

smoke test 第一版不启动服务，原因如下:

- 当前 endpoint 可以通过 in-process 函数调用验证。
- 启动服务会引入端口、环境变量、后台进程和清理责任。
- 服务级验证容易扩大到真实 HTTP、外部依赖或运行时链路。
- 当前目标是验证 mock-only API bridge 的逻辑边界，而不是验证部署或网络入口。
- no-write 边界更适合用 in-process patch 和 artifact counts 证明。

因此第一版不得新增服务启动脚本，不得调用 `uvicorn`、`streamlit`、`gunicorn`、`hypercorn` 或任何后台服务命令。

## 5. in-process API smoke test 范围

smoke test 第一版只允许复用或补强:

```text
backend/tests/test_actions_zbid_snapshot_mapper_api.py
```

允许方式:

- 直接构造 `ActionsZBidSnapshotDraftInputPreviewRequest`。
- 直接调用 `actions_zbid_snapshot_draft_input_preview(...)`。
- 使用 `patch.dict(os.environ, ...)` 控制 `ZF_ACTIONS_KEY` 和 `ZDOC_ZBID_MOCK_API_ENABLED`。
- 使用 monkeypatch / patch 防误触高风险函数。
- 使用 `_artifact_counts()` 或等价 helper 记录测试前后文件数。

第一版不得新增服务启动脚本，不得新增独立 smoke runner，不得启动 HTTP 服务。

## 6. feature flag 验证路径

当前 feature flag:

```text
ZDOC_ZBID_MOCK_API_ENABLED=1
```

验证路径:

- 未设置时，endpoint 必须返回 disabled。
- 未设置时，endpoint 必须不调用 mapper。
- 设置为 `1` 时，endpoint 才允许调用 mapper。
- 设置为其他值时，应视为 disabled。

feature flag 只允许 mock-only mapper preview，不授权:

- 前端接入
- Ollama
- LLMClient
- run_autoplan
- job/result bundle 写入
- build/output 写入
- export
- 正式 apply

## 7. request / response 验证点

request 验证点:

- request 只需要 `snapshot` dict。
- snapshot 必须经由 `map_zbid_snapshot_to_zdoc_draft_input(snapshot)` 校验。
- request 中不得绕过 helper 校验。

response 基础验证点:

- `ok`
- `status`
- `mode`
- `draft_only`
- `no_write`
- `source_system`
- `data`
- `error`

response 不得包含以下字段:

- `formal_apply`
- `apply`
- `export`
- `generate_async`
- `job`
- `result_bundle`
- `build_output`
- `ollama`
- `llm`

## 8. disabled 场景验证点

feature flag 默认关闭时必须验证:

- 返回 `status=disabled`。
- 返回 `mode=mock_only`。
- 返回 `draft_only=true`。
- 返回 `no_write=true`。
- 返回 `source_system=zbid`。
- `data` 为 `None`。
- 不调用 mapper。
- 不调用任何高风险链路。
- 不写 job/build/output/result bundle。

disabled 场景是第一版 smoke test 的必测路径，因为它证明 endpoint 默认不开放。

## 9. enabled valid snapshot 验证点

feature flag enabled 后，valid snapshot 必须验证:

- 返回 `ok=true`。
- 返回 `status=mapped`。
- 返回 `mode=mock_only`。
- 返回 `draft_only=true`。
- 返回 `no_write=true`。
- 返回 `source_system=zbid`。
- `data` 为 mapper 输出。
- `data.mode=draft_only`。
- `data.source_system=zbid`。
- `data.safety_boundary.no_write=true`。
- `data.safety_boundary.allow_ollama=false`。
- mapper 只被调用一次。
- 未调用任何高风险链路。

## 10. invalid snapshot / forbidden key 验证点

invalid snapshot 必须验证:

- 返回受控 400。
- response detail 中包含 `status=validation_error`。
- response detail 中包含 `error=validation_error`。
- response detail 中包含 `message`。
- `message` 不包含 traceback。
- 不写 job/build/output/result bundle。

forbidden key 必须验证:

- 包含 `formal_apply`、`apply`、`export`、`generate_async`、`job`、`result_bundle`、`build_output`、`ollama` 或 `llm` 时返回受控 400。
- response 中不泄露 traceback。
- 不进入 fallback、生成、导出或写盘链路。

## 11. artifact counts 校验规则

smoke test 第一版必须记录以下路径测试前后文件数:

```text
backend/data/autoplan/jobs
build
output
```

通过条件:

- 三个路径的文件数测试前后一致。
- combined count 测试前后一致。
- 任何 count 变化都视为 no-write 边界失败。

不得把 artifact count 变化解释为可接受副作用。若出现变化，必须停止并回报。

## 12. 高风险链路防误触验证

smoke test 第一版必须 patch 并断言未调用:

- Ollama preview / review 函数
- LLMClient
- `run_autoplan`
- `create_job`
- `update_job`
- `_save_outputs`
- `save_output_artifacts`
- export/docx/xlsx/pptx/html 相关函数
- `build_section_draft`
- `apply_section_draft`
- `reject_section_draft`
- `rollback_section_draft`

第一版不得调用:

- Ollama
- LLMClient
- run_autoplan
- create_job
- update_job
- save_output_artifacts

## 13. 与现有 deterministic API tests 的关系

当前已有 deterministic API tests 已覆盖:

- default-off 不调用 mapper。
- enabled valid snapshot 映射。
- invalid snapshot 受控 400。
- forbidden key 受控 400。
- response 不含 forbidden keys。
- artifact counts 不变。
- 高风险链路 patch 防误触。

后续 smoke test 不应复制出新的宽泛测试套件。第一版应在 `backend/tests/test_actions_zbid_snapshot_mapper_api.py` 内复用现有 sample snapshot、artifact count helper 和 no-write patch helper，必要时只补一个聚合 smoke 场景。

## 14. guard task spec 使用建议

后续实现前必须先建立或引用专用 guard task spec:

```text
tasks/zbid_snapshot_mock_api_bridge_guard.json
```

建议 guard task spec 至少包含:

- `allowed_files`
  - `backend/app/routers/actions_bridge.py`
  - `backend/tests/test_actions_zbid_snapshot_mapper_api.py`
  - `docs/zbid-snapshot-mock-api-bridge-smoke-test-design.md`
  - `tasks/zbid_snapshot_mock_api_bridge_guard.json`
- `forbidden_files`
  - `app.py`
  - frontend / Streamlit 页面
  - orchestrator
  - LLMClient
  - provider / OllamaProvider
  - section_drafts helper
  - zbid_snapshot_mapper.py
  - build/output/job/result bundle 相关路径
- `test_commands`
  - `python -m pytest backend/tests/test_actions_zbid_snapshot_mapper_api.py backend/tests/test_zbid_snapshot_mapper.py`
- `count_paths`
  - `backend/data/autoplan/jobs`
  - `build`
  - `output`

guard 只能用于检查，不得承担 merge、tag、push、服务启动或真实生成职责。

## 15. 不允许接入的链路

后续仍不得接:

- 前端正式成果按钮
- `app.py`
- Ollama
- LLMClient
- run_autoplan
- job/result bundle
- build/output
- DOCX/XLSX/PPTX/HTML export
- section_drafts apply/reject/rollback
- `/actions/generate_async`
- `/actions/review/apply`
- 正式写回链

任何从 mock-only preview 进入正式成果链的动作都必须另行设计、另行实现、另行验收。

## 16. 后续实现准入条件

进入 smoke test 实现前必须满足:

- 明确本阶段从 docs-only 设计切换到测试补强阶段。
- 明确 allowed files。
- 明确 forbidden files。
- 建立或引用 `tasks/zbid_snapshot_mock_api_bridge_guard.json`。
- 明确只允许复用或补强 `backend/tests/test_actions_zbid_snapshot_mapper_api.py`。
- 明确不新增服务启动脚本。
- 明确不启动服务。
- 明确不连接 Ollama。
- 明确不触发生成、导出、job/build/output/result bundle 或正式 apply。
- 明确 artifact counts 失败时必须停止。

## 17. Codex 后续执行约束

后续 Codex 执行相关任务时:

- 未经明确授权，不修改业务代码。
- 未经明确授权，不修改 API。
- 未经明确授权，不修改前端或 `app.py`。
- 未经明确授权，不修改 orchestrator。
- 未经明确授权，不修改 LLMClient。
- 未经明确授权，不修改 provider / OllamaProvider。
- 未经明确授权，不修改 section_drafts helper。
- 未经明确授权，不修改 zbid_snapshot_mapper.py。
- 未经明确授权，不新增服务启动脚本。
- 未经明确授权，不启动服务。
- 未经明确授权，不连接或运行 Ollama。
- 未经明确授权，不运行真实生成。
- 未经明确授权，不触发 export。
- 未经明确授权，不创建或更新 job。
- 未经明确授权，不写 job/build/output/result bundle。
- 未经明确授权，不执行正式 apply。
- 未经明确授权，不执行 `git clean`、删除、移动或清理文件。
- 未经明确授权，不安装依赖。

## 18. 结论

ZBid snapshot mock API bridge smoke test 第一版应保持 in-process、mock-only、no-write。它只验证 `POST /actions/zbid/snapshot_draft_input/preview` 在 disabled、enabled、invalid 和 forbidden key 场景下的最小健康状态，并证明 artifact counts 不变。

下一步若进入实现，应先建立或引用 `tasks/zbid_snapshot_mock_api_bridge_guard.json`，再在 `backend/tests/test_actions_zbid_snapshot_mapper_api.py` 内做最小补强。不得新增服务启动脚本，不得接前端、Ollama、生成链、导出链、job/result bundle、build/output 或正式写回链。
