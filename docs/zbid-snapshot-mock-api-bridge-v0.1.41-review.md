# ZBid Snapshot Mock API Bridge v0.1.41 Review

## 1. 阶段定位

本文件记录 `v0.1.41-zbid-snapshot-mock-api-bridge` 阶段的实现结果、验证结果和后续边界。

本阶段完成 ZBid snapshot mapper mock-only API bridge 第一版实现。该能力只提供默认关闭、mock-only、draft-only、no-write 的 API 映射预览入口，不代表 ZBid 已接入 ZDoc 前端、Ollama、生成链、导出链、job/result bundle、build/output 或正式成果链。

## 2. 当前基线

- 当前 commit: `bdda10b feat: add ZBid snapshot mock API bridge`
- 当前稳定标签: `v0.1.41-zbid-snapshot-mock-api-bridge`
- 前置设计标签: `v0.1.40-zbid-mock-api-bridge-first-design`
- 当前工作区基线: clean

## 3. 本阶段修改 / 新增文件

本阶段只提交了 2 个文件:

- `backend/app/routers/actions_bridge.py`
- `backend/tests/test_actions_zbid_snapshot_mapper_api.py`

未修改:

- 前端
- `app.py`
- orchestrator
- `LLMClient`
- provider / `OllamaProvider`
- `section_drafts` helper
- `zbid_snapshot_mapper.py`

## 4. 已实现能力

已实现一个 ZBid snapshot 到 ZDoc draft-only input 的 mock-only API bridge。

已实现能力:

- 新增默认关闭 endpoint。
- feature flag 开启后接收 ZBid snapshot dict。
- 只调用 `map_zbid_snapshot_to_zdoc_draft_input(snapshot)` 纯函数。
- 返回 mock-only / draft-only / no-write 结构化响应。
- mapper 抛出 `ValueError` 时返回受控 400。
- 400 响应包含 `error` 和 `message`。
- 不泄露 traceback。
- 不写 job/build/output/result bundle。
- 不调用 Ollama、LLMClient、run_autoplan、export 或正式 apply。

## 5. endpoint 与 feature flag

新 endpoint:

```text
POST /actions/zbid/snapshot_draft_input/preview
```

feature flag:

```text
ZDOC_ZBID_MOCK_API_ENABLED=1
```

默认值: disabled。

feature flag 只控制 mock-only API bridge 是否允许调用 mapper，不代表允许前端、Ollama、生成链、导出链、job/result bundle、build/output 或正式写回。

## 6. API 行为说明

默认关闭时:

- 返回 `status=disabled`。
- 返回 `mode=mock_only`。
- 返回 `draft_only=true`。
- 返回 `no_write=true`。
- 返回 `source_system=zbid`。
- 不调用 mapper。
- 不写盘。
- 不触发任何生成链。

开启后:

- 接收 request 中的 `snapshot` dict。
- 只调用 `map_zbid_snapshot_to_zdoc_draft_input(snapshot)`。
- 返回 `ok=true`。
- 返回 `mode=mock_only`。
- 返回 `draft_only=true`。
- 返回 `no_write=true`。
- 返回 `source_system=zbid`。
- `data` 为 mapper 输出。

错误输入:

- mapper 抛出 `ValueError` 时返回受控 400。
- 400 响应包含 `error=validation_error`。
- 400 响应包含 `message`。
- 不泄露 traceback。

## 7. deterministic API tests 覆盖范围

新增测试文件:

```text
backend/tests/test_actions_zbid_snapshot_mapper_api.py
```

测试覆盖:

- feature flag 默认关闭时 endpoint 拒绝。
- 默认关闭时不调用 mapper。
- feature flag 开启时 valid snapshot 返回 mock_only / draft_only / no_write。
- invalid snapshot 返回受控 400。
- forbidden key 返回受控 400。
- 响应不包含 forbidden keys。
- job/build/output 文件数量在测试前后不变。
- patch 防误触:
  - Ollama
  - LLMClient
  - run_autoplan
  - create_job / update_job
  - `_save_outputs`
  - save_output_artifacts
  - export/docx/xlsx 相关函数
  - section_drafts helper

测试方式为直接调用 endpoint 函数，不启动服务，不连接 Ollama，不运行真实生成。

## 8. 已验证结果

限定测试命令:

```bash
python -m pytest backend/tests/test_actions_zbid_snapshot_mapper_api.py backend/tests/test_zbid_snapshot_mapper.py
```

pytest 结果:

```text
41 passed in 1.45s
```

验证结论:

- 新 API bridge 的默认关闭行为已验证。
- 开启后的 mapper 调用路径已验证。
- 受控 400 错误路径已验证。
- forbidden key 拒绝路径已验证。
- no-write 边界已通过测试 patch 和 artifact count 验证。

## 9. artifact counts 结果

artifact 文件数量:

```text
1476
```

该数量来自:

```bash
find backend/data/autoplan/jobs build output -type f 2>/dev/null | wc -l
```

本阶段测试前后未发现 job/build/output 计数变化。

## 10. 当前未接入能力

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
- `section_drafts` helper
- 正式 apply

本阶段没有开放正式生成、正式导出、正式写回或正式成果链能力。

## 11. 明确禁止直接接入的链路

后续不得直接把当前 mock API bridge 接入:

- 前端正式成果按钮
- 生成链
- 导出链
- job/result bundle
- build/output
- 正式写回链
- Ollama 主链
- section draft apply/reject/rollback 链路
- DOCX/XLSX/PPTX/HTML export

任何从 mock-only preview 进入正式成果链的动作都必须另行设计、另行实现、另行验收。

## 12. 风险清单与控制措施

风险: mock-only endpoint 被误认为正式生成入口。

- 控制: endpoint 使用 `snapshot_draft_input/preview` 命名，并在 response 中强制返回 `mock_only`、`draft_only`、`no_write`。

风险: feature flag 开启后被误认为允许写盘或生成。

- 控制: `ZDOC_ZBID_MOCK_API_ENABLED=1` 只允许调用 mapper 纯函数，不授权任何生成、写回、导出或 job 写入。

风险: API bridge 被直接挂到前端正式成果按钮。

- 控制: 后续前端任务必须先做 docs-only 设计和只读展示边界，不得直接接正式成果按钮。

风险: 误触 job/build/output/result bundle。

- 控制: tests patch 高风险函数，并记录 artifact counts。

风险: 误接 Ollama 或 LLMClient。

- 控制: tests patch LLMClient，endpoint 代码只调用 `map_zbid_snapshot_to_zdoc_draft_input`。

风险: mapper 校验被绕过。

- 控制: API 层不重写 mapper 逻辑，错误输入统一由 helper `ValueError` 转受控 400。

## 13. 后续推进建议

后续若继续推进，只能先做以下低风险前置工作:

- 只读 API bridge 集成盘点。
- guard task spec 补强。
- API smoke test 设计。
- docs-only 生产切换前置设计。
- 其他系统接入前置盘点。

后续不得直接接正式成果链。不得直接接:

- 前端正式成果按钮
- 生成链
- 导出链
- job/result bundle
- build/output
- 正式写回链

如果需要从 mock-only API bridge 进入更高阶段，必须先明确 allowed files、forbidden files、feature flag、回滚方式、no-write 验证、artifact count 验证和人工验收标准。

## 14. Codex 后续执行约束

后续 Codex 执行相关任务时:

- 未经明确授权，不修改前端。
- 未经明确授权，不修改 `app.py`。
- 未经明确授权，不修改 orchestrator。
- 未经明确授权，不修改 LLMClient。
- 未经明确授权，不修改 provider / OllamaProvider。
- 未经明确授权，不修改 `section_drafts` helper。
- 未经明确授权，不修改 `zbid_snapshot_mapper.py`。
- 未经明确授权，不启动服务。
- 未经明确授权，不连接或运行 Ollama。
- 未经明确授权，不运行真实生成。
- 未经明确授权，不触发 export。
- 未经明确授权，不创建或更新 job。
- 未经明确授权，不写 job/build/output/result bundle。
- 未经明确授权，不执行正式 apply。
- 未经明确授权，不执行 `git clean`、删除、移动或清理文件。
- 未经明确授权，不安装依赖。

若用户要求 docs-only、只读检查或前置设计，必须严格停留在对应边界内。

## 15. 结论

`v0.1.41-zbid-snapshot-mock-api-bridge` 已完成 ZBid snapshot mapper mock-only API bridge 第一版实现和 deterministic API tests。当前能力仅是默认关闭的 no-write 映射预览入口。

该阶段没有接入前端、Ollama、生成链、导出链、job/result bundle、build/output、section draft helper 或正式 apply。后续不得把该 endpoint 直接接入正式成果链；必须先做只读盘点、guard 补强、smoke test 设计或 docs-only 生产切换前置设计。
