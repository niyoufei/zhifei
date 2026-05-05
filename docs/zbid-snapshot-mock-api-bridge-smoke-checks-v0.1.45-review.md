# ZBid Snapshot Mock API Bridge Smoke Checks v0.1.45 Review

## 1. 阶段定位

本文件记录 `v0.1.45-zbid-snapshot-mock-api-bridge-smoke-checks` 阶段的复盘结果。

本阶段只补强 ZBid snapshot mock API bridge 的 in-process HTTP smoke checks，目标是证明已实现 endpoint 可以通过 FastAPI `TestClient` 在不启动服务的情况下完成 disabled / enabled / invalid / forbidden key 场景验证。

本阶段不是生产接入阶段，不代表允许接入前端、Ollama、生成链、导出链、job/result bundle、build/output 或正式写回链。

## 2. 当前基线

- 当前 commit: `daa68c1 test: strengthen ZBid snapshot mock API bridge smoke checks`
- 当前稳定标签: `v0.1.45-zbid-snapshot-mock-api-bridge-smoke-checks`
- 前置 guard spec 标签: `v0.1.44-zbid-snapshot-mock-api-bridge-guard-spec`
- 当前 endpoint: `POST /actions/zbid/snapshot_draft_input/preview`
- 当前 feature flag: `ZDOC_ZBID_MOCK_API_ENABLED=1`
- 当前工作区基线: clean

## 3. 本阶段提交与标签

本阶段提交:

```text
daa68c1 test: strengthen ZBid snapshot mock API bridge smoke checks
```

本阶段稳定标签:

```text
v0.1.45-zbid-snapshot-mock-api-bridge-smoke-checks
```

标签用途是归档 in-process HTTP smoke checks 补强后的稳定测试基线。

## 4. 本阶段修改范围

本阶段只提交了 1 个测试文件:

```text
backend/tests/test_actions_zbid_snapshot_mapper_api.py
```

本阶段未修改:

- API 实现
- 业务代码
- 前端
- `app.py`
- orchestrator
- `LLMClient`
- provider / `OllamaProvider`
- `section_drafts` helper
- `zbid_snapshot_mapper.py`
- guard 程序
- task spec
- 其他测试文件

## 5. smoke checks 补强内容

本阶段在既有 deterministic API tests 基础上补强了 in-process HTTP smoke checks。

补强内容:

- 使用 `fastapi.FastAPI` 构建本地测试 app。
- 使用 `app.include_router(actions_bridge.router)` 挂载真实路由。
- 使用 `fastapi.testclient.TestClient` 调用真实 endpoint。
- 保留既有 direct function tests。
- 复用既有 valid snapshot helper。
- 复用既有 artifact counts helper。
- 复用既有 no-write chain patch helper。
- 通过 HTTP response 验证 disabled / enabled / invalid / forbidden key 场景。

smoke checks 只验证 API bridge 的最小健康状态，不扩大为端到端业务验收。

## 6. endpoint 与 feature flag

endpoint:

```text
POST /actions/zbid/snapshot_draft_input/preview
```

feature flag:

```text
ZDOC_ZBID_MOCK_API_ENABLED=1
```

feature flag 只允许 mock-only preview 调用 mapper 纯函数，不授权任何生产生成、正式 apply、导出、job/result bundle、build/output 或前端正式成果链。

## 7. in-process HTTP smoke test 覆盖范围

本阶段 smoke checks 使用 FastAPI `TestClient` in-process 调用，不启动 `uvicorn`，不启动正式服务。

覆盖范围:

- feature flag 默认关闭时，HTTP 调用返回 `status=disabled`。
- feature flag 默认关闭时，不调用 mapper。
- feature flag 开启后，valid snapshot 返回 `mode=mock_only`。
- feature flag 开启后，valid snapshot 返回 `draft_only=true`。
- feature flag 开启后，valid snapshot 返回 `no_write=true`。
- feature flag 开启后，valid snapshot 返回 `source_system=zbid`。
- invalid snapshot 通过 HTTP 返回 400。
- invalid snapshot 的 response `detail.status=validation_error`。
- forbidden key 通过 HTTP 返回 400。
- forbidden key 的 response `detail.error=validation_error`。
- response 不包含 forbidden exact keys。
- `backend/data/autoplan/jobs`、`build`、`output` 文件数测试前后不变。
- patch 防误触 Ollama、LLMClient、run_autoplan、create_job、update_job、save_output_artifacts、section_drafts apply/reject/rollback 和 export 链路。

## 8. pytest 结果

提交前限定测试命令:

```bash
python -m pytest backend/tests/test_actions_zbid_snapshot_mapper_api.py backend/tests/test_zbid_snapshot_mapper.py
```

pytest 结果:

```text
45 passed
```

该结果包含既有 direct function tests、mapper tests，以及本阶段新增的 in-process HTTP smoke checks。

## 9. guard scope 结果

guard scope 命令:

```bash
python scripts/guards/zdoc_guard.py scope --task tasks/zbid_snapshot_mock_api_bridge_guard.json
```

结果:

```text
changed_files:
  backend/tests/test_actions_zbid_snapshot_mapper_api.py
[PASS] scope check passed
```

该结果证明本阶段变更范围只落在 guard task spec 允许的测试文件内。

## 10. guard verify 结果

guard verify 命令:

```bash
python scripts/guards/zdoc_guard.py verify --task tasks/zbid_snapshot_mock_api_bridge_guard.json
```

结果:

```text
[PASS] verify checks passed
```

guard verify 已执行:

- `git diff --check`
- task spec 中记录的限定 pytest 命令
- artifact counts 前后对比

本阶段未执行 `tag-check`。原因是 `v0.1.44-zbid-snapshot-mock-api-bridge-guard-spec` 已存在，tag-check 对该旧标签失败属于预期，不应删除、覆盖或重建标签。

## 11. artifact counts 结果

guard verify 记录的 artifact counts 前后不变:

```text
backend/data/autoplan/jobs: 87
build: 1395
output: 0
```

验证结论:

- 未新增 job 文件。
- 未新增 build 文件。
- 未新增 output 文件。
- 未写 result bundle。
- 未触发导出产物。

## 12. 当前未接入能力

本阶段明确未接入:

- 前端
- `app.py`
- Ollama
- LLMClient
- `run_autoplan`
- `create_job` / `update_job`
- `save_output_artifacts`
- job/result bundle
- build/output
- DOCX/XLSX/PPTX/HTML export
- `section_drafts` apply/reject/rollback
- `/actions/generate_async`
- `/actions/review/apply`
- 正式 apply / 正式写回链

本阶段只补强测试，不新增任何运行时能力。

## 13. 明确禁止直接接入的链路

后续不得直接把当前 mock API bridge 接入:

- 前端正式成果按钮
- 生产环境默认开启
- Ollama 正式生成链
- job/result bundle
- build/output
- 导出链
- 正式写回链
- `/actions/generate_async`
- `/actions/review/apply`
- `section_drafts` apply/reject/rollback
- DOCX/XLSX/PPTX/HTML export

任何从 mock-only preview 进入正式成果链的动作都必须另行设计、另行实现、另行验收。

## 14. 风险清单与控制措施

风险: smoke checks 被误认为生产接入验收。

- 控制: 本阶段明确只使用 in-process `TestClient`，不启动服务，不验证生产环境，不授权前端或正式成果链。

风险: feature flag 被误认为生产默认开启条件。

- 控制: `ZDOC_ZBID_MOCK_API_ENABLED=1` 只允许 mock-only mapper preview，后续不得直接默认开启到生产环境。

风险: mock API bridge 被直接挂到前端正式成果按钮。

- 控制: 后续如涉及前端，只能先做 docs-only 生产切换前置设计，不得直接接正式成果按钮。

风险: 测试误触 job/build/output/result bundle。

- 控制: smoke checks 使用 no-write patch，并通过 guard verify artifact counts 证明前后不变。

风险: 测试误触 Ollama、LLMClient 或生成链。

- 控制: smoke checks patch 高风险链路，并断言未调用。

风险: 后续扩大文件范围。

- 控制: 继续使用 `tasks/zbid_snapshot_mock_api_bridge_guard.json` 做 scope / verify，任何扩大范围必须先 docs-only 说明并人工确认。

## 15. 后续推进建议

后续若推进，只能先做:

- docs-only 生产切换前置设计。
- local LLM 多系统接入路线文档。
- 评标系统 ZhiFei_BizSystem 接入状态盘点。
- 其他桌面系统接入前置盘点。

后续不得直接接正式成果链。不得直接接:

- 前端正式成果按钮
- 生产环境默认开启
- Ollama 正式生成链
- job/result bundle
- build/output
- 导出链
- 正式写回链

如果后续要进入生产切换或跨系统接入，必须先明确:

- allowed files
- forbidden files
- feature flag 策略
- 回滚策略
- no-write 验证
- artifact counts 验证
- smoke test 范围
- 人工验收标准

## 16. Codex 后续执行约束

后续 Codex 执行相关任务时:

- 未经明确授权，不修改 API 实现。
- 未经明确授权，不修改业务代码。
- 未经明确授权，不修改前端。
- 未经明确授权，不修改 `app.py`。
- 未经明确授权，不修改 orchestrator。
- 未经明确授权，不修改 LLMClient。
- 未经明确授权，不修改 provider / OllamaProvider。
- 未经明确授权，不修改 `section_drafts` helper。
- 未经明确授权，不修改 `zbid_snapshot_mapper.py`。
- 未经明确授权，不修改 guard 程序。
- 未经明确授权，不修改 task spec。
- 未经明确授权，不启动服务。
- 未经明确授权，不连接或运行 Ollama。
- 未经明确授权，不运行真实生成。
- 未经明确授权，不运行导出链。
- 未经明确授权，不写 job/build/output/result bundle。
- 未经明确授权，不执行正式 apply。

## 17. 结论

`v0.1.45-zbid-snapshot-mock-api-bridge-smoke-checks` 已完成 in-process HTTP smoke checks 补强。

当前稳定结论:

- mock API bridge endpoint 可通过 FastAPI `TestClient` 在不启动服务的情况下完成 HTTP smoke 校验。
- disabled / enabled / invalid / forbidden key 场景已覆盖。
- pytest 结果为 `45 passed`。
- guard scope 结果为 `[PASS] scope check passed`。
- guard verify 结果为 `[PASS] verify checks passed`。
- artifact counts 前后不变: `backend/data/autoplan/jobs=87`、`build=1395`、`output=0`。
- 本阶段只修改并提交了 `backend/tests/test_actions_zbid_snapshot_mapper_api.py`。
- 当前仍未接入前端、Ollama、LLMClient、生成链、导出链、job/result bundle、build/output 或正式写回链。

后续只能先进入 docs-only 生产切换前置设计或跨系统接入状态盘点，不得直接接正式成果链。
