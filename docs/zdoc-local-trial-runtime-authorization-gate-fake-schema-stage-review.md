# ZDoc Local Trial Runtime Authorization Gate Fake Schema Stage Review

## 1. Scope

Step 156 仅为 Step 155 fake schema tests 的 docs-only 复盘归档。

本复盘对应 Step 155：`local trial runtime authorization gate fake schema tests`，目标是归档 local trial runtime authorization gate fake schema tests 的测试覆盖、授权分类、命令 allowlist、硬阻断清单、no-write 断言、服务启动授权边界、Ollama 授权边界、ZDoc / ZBid preview-only 授权边界、停止条件、运行后回报模板、安全边界、未执行事项和后续推进条件。

Step 155 新增的测试文件只固化 local trial runtime authorization gate 的结构、授权分类、命令 allowlist、硬阻断清单、no-write 断言、服务启动授权边界、Ollama 授权边界、ZDoc / ZBid preview-only 授权边界、停止条件和运行后回报模板。它不执行真实授权，不启动服务，不运行 Ollama，不访问本地端口，不调用 ZBid，不写 `output/job/export`，不执行 smoke test，不进入本地化部署执行，不进入 50 人团队正式部署设计。

本文档不代表本地化部署已执行，不代表 smoke test 已执行，不代表 ZDoc / ZBid 已实际联调，不代表 50 人正式部署设计已启动。

当前总体策略仍为：

- 先完成本地化部署基础闭环。
- 再完成 ZDoc 与 ZBid 的 preview-only 对接。
- 再进行小范围试用和问题修正。
- 最后再按约 50 人同时使用场景进行正式部署设计。

## 2. File Added In Step 155

Step 155 新增文件：

- `backend/tests/test_local_trial_runtime_authorization_gate_schema.py`

Step 155 未修改：

- 生产代码。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- 部署脚本。
- 启动脚本。
- 服务配置。
- `.env` / local config。
- 数据库、模型、缓存或运行时文件。

## 3. Schema Test Coverage Summary

Step 155 已用 deterministic fake schema tests 固化以下 runtime authorization gate 内容：

- required sections。
- scope boundary。
- authorization principle。
- runtime action categories。
- authorization request template。
- authorized command allowlist。
- runtime hard block list。
- no-write runtime assertion design。
- service startup authorization boundary。
- Ollama authorization boundary。
- ZDoc / ZBid preview-only authorization boundary。
- stop conditions。
- required runtime report template。
- future implementation acceptance criteria。
- migration path。
- formal flags false。
- no execution side effects。
- import isolation。

Step 155 的测试文件仅定义本地 fake local trial runtime authorization gate factory、本地 fake validator 和本地常量，用于固化 Step 154 的 authorization gate 结构。它不新增生产实现，不从正式生成链导入能力，不调用 `orchestrator`、`llm_client`、`provider`、`generation`、`export`、`review/apply`、`actions_bridge` 或 ZBid 相关模块。

## 4. Authorization Categories Confirmed

Step 155 已固化 3 类授权边界。

### 4.1 Always Forbidden Without Higher Authorization

以下动作在本地试用阶段默认禁止，除非未来存在更高层级、单独明确、逐项列明的授权：

- 正式写回。
- `/review/apply`。
- `/export_docx`。
- DOCX 正式导出。
- ZBid 正式写回。
- ZBid API / DB / writeback。
- `output/job/export` 写入。
- 修改 source section。
- 进入 50 人正式部署。
- 修改生产主链。
- 修改既有 tests 修复 full-suite 顺序问题。

### 4.2 Requires Explicit Smoke-Test Authorization

以下动作只有在未来真实 smoke test 阶段，且用户逐项明确授权后才可执行：

- 启动后端服务。
- 启动前端服务。
- 访问本地服务端口。
- 访问 `127.0.0.1:11434`。
- 检查 Ollama 可达性。
- 执行 preview-only 测试请求。
- 生成 smoke report。
- 检查 `output/job/export` 差异。
- 停止本地服务。

### 4.3 Docs-Only Allowed Current Stage

当前阶段仅允许以下 docs-only / fake-only 设计与固化工作：

- 编写设计文档。
- 编写 fake schema tests。
- 编写 fake helper。
- 设计命令占位。
- 设计回报模板。
- 设计停止条件。

这些事项不得被解释为已获得真实运行授权。

## 5. Safety Invariants Confirmed

Step 155 已确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. 默认禁止所有运行时动作。
7. 所有运行时动作必须用户单独授权。
8. 授权必须明确动作、目录、命令范围、停止条件、回报内容。
9. 未授权不得推断允许。
10. 部分授权不得扩大解释。
11. 检查文档不等于执行命令。
12. 设计 smoke plan 不等于执行 smoke test。
13. preview-only 不等于 writeback allowed。
14. `/generate` 正式生成必须硬阻断。
15. `/export_docx` 必须硬阻断。
16. `/review/apply` 必须硬阻断。
17. ZBid 写回必须硬阻断。
18. ZBid API / DB / writeback 必须硬阻断。
19. `output/job/export` 写入必须硬阻断。
20. DOCX 文件生成必须硬阻断。
21. `formal_writeback_allowed=true` 必须 stop。
22. `review_apply_allowed=true` 必须 stop。
23. `docx_export_allowed=true` 必须 stop。
24. `zbid_writeback_allowed=true` 必须 stop。
25. `output_write_allowed=true` 必须 stop。
26. advisory 作为 evidence 必须 stop。
27. preview 作为正式正文必须 stop。
28. source hash mismatch 未 blocked 必须 stop。
29. `blocked_reasons` 缺失必须 stop。
30. 后端启动必须单独授权。
31. 前端启动必须单独授权。
32. 运行 `ollama serve` 必须单独授权。
33. 访问 `127.0.0.1:11434` 必须单独授权。
34. 模型不可用不得自动下载。
35. 模型不可用不得写回。
36. 模型输出不得作为 evidence。
37. `thinking_only_fallback` 不得作为正式正文能力。
38. 可测试 ZDoc preview packet。
39. 可测试 ZBid preview validator。
40. 不得调用真实 ZBid API。
41. 不得访问 ZBid DB。
42. 不得写回 ZBid。
43. 不得把 ZBid scoring preview 作为 evidence。
44. 不得把 `accepted_preview_only` 作为 writeback permission。

## 6. Test Evidence From Step 155

Step 155 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_local_trial_runtime_authorization_gate_schema.py -vv`
  - 18 passed in 0.04s。

- `python -m pytest backend/tests/test_local_trial_smoke_checklist_schema.py backend/tests/test_local_trial_smoke_execution_plan_schema.py backend/tests/test_local_trial_runtime_authorization_gate_schema.py -vv`
  - 54 passed in 0.08s。

- `python -m pytest backend/tests/test_zdoc_zbid_preview_only_integration_contract_schema.py backend/tests/test_zdoc_zbid_preview_packet.py backend/tests/test_zbid_preview_input_validator.py backend/tests/test_local_trial_smoke_checklist_schema.py backend/tests/test_local_trial_smoke_execution_plan_schema.py backend/tests/test_local_trial_runtime_authorization_gate_schema.py -vv`
  - 99 passed in 0.13s。

- `python -m pytest backend/tests/test_local_trial_runtime_authorization_gate_schema.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - 21 passed in 0.80s。

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。该事实不得在本复盘中扩大解释为生产功能风险。

Step 156 不运行 pytest；以上为 Step 155 的测试证据归档。

## 7. Boundary Against Actual Runtime Execution

Step 155 未执行以下动作：

- backend startup。
- frontend startup。
- Ollama startup。
- health check execution。
- local port access。
- ZDoc / ZBid actual integration。
- local deployment execution。
- smoke test execution。
- 50-user deployment design。
- any writeback。
- any export。
- any model call。
- any authorization expansion。

Step 155 未启动后端服务，未启动前端服务，未运行 Ollama，未访问 `127.0.0.1:11434`，未访问任何本地服务端口，未调用外部模型/API，未调用 ZBid API / 数据库 / 写回接口，未写 `output/job/export`，未触发 `/generate`、`/export_docx`、`/review/apply`，未触发 ZBid 写回，未进入 ZDoc / ZBid 实际联调，未进入本地化部署执行，未执行 smoke test，未进入 50 人团队正式部署设计，未扩大授权范围。

## 8. Remaining Blockers Before Real Local Trial

进入真实本地小范围试用前仍缺少：

- explicit user authorization to start backend。
- explicit user authorization to start frontend。
- explicit user authorization to access local ports。
- explicit user authorization to check Ollama。
- explicit user authorization to read local config。
- explicit user authorization to execute preview-only test request。
- explicit user authorization to inspect `output/job/export` diff。
- explicit user authorization to generate smoke report。
- backend health check execution。
- frontend access check execution。
- Ollama optional availability check execution。
- no-write runtime assertion execution。
- preview-only runtime assertion execution。
- actual preview-only packet route。
- actual ZBid preview input route。
- smoke report generation。
- stop / rollback procedure for local services。

这些事项需要在后续步骤单独设计或执行。当前 fake schema tests 不能替代真实 smoke test，也不能证明本地服务、模型、ZDoc / ZBid preview-only 联通、运行时 no-write 断言或授权门禁已可用。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 157：local trial authorized smoke dry-run command plan，docs-only。

Step 157 不得启动服务，不得运行 Ollama，不得执行 smoke test，不得调用 ZBid，不得写 `output/job/export`，只设计未来用户授权后才可执行的 smoke dry-run command plan，包括命令分组、执行顺序、停止条件和回报模板。

## 10. Safety Conclusion

Step 155 仅完成 local trial runtime authorization gate fake schema tests。当前系统仍未执行 smoke test，未完成本地化部署，未完成 ZDoc / ZBid 实际联调，未进入 50 人正式部署设计；任何真实运行行为仍必须获得用户逐项明确授权。

Step 156 仅完成 Step 155 fake schema tests 的 docs-only 复盘归档。本文档不代表本地化部署已执行，不代表 smoke test 已执行，不代表 ZDoc / ZBid 已实际联调，不代表正式写回、DOCX 导出、ZBid 写回、review/apply、formal writeback、formal writeback dry-run 或 50 人团队正式部署设计已实现。
