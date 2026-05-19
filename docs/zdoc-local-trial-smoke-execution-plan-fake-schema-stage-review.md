# ZDoc Local Trial Smoke Execution Plan Fake Schema Stage Review

## 1. Scope

Step 153 仅为 Step 152 fake schema tests 的 docs-only 复盘归档。

本复盘对应 Step 152：`local trial smoke execution plan fake schema tests`，目标是归档 local trial smoke execution plan fake schema tests 的覆盖范围、命令占位、执行顺序、停止条件、回报模板、安全边界、未执行事项和后续推进条件。

Step 152 新增的测试文件只固化 local trial smoke execution plan 的结构、命令占位、执行顺序、停止条件和回报模板。它不执行真实 smoke test，不启动服务，不运行 Ollama，不访问本地端口，不调用 ZBid，不写 `output/job/export`，不进入本地化部署执行，不进入 50 人团队正式部署设计。

本文档不代表本地化部署已执行，不代表 smoke test 已执行，不代表 ZDoc / ZBid 已实际联调，不代表 50 人正式部署设计已启动。

当前总体策略仍为：

- 先完成本地化部署基础闭环。
- 再完成 ZDoc 与 ZBid 的 preview-only 对接。
- 再进行小范围试用和问题修正。
- 最后再按约 50 人同时使用场景进行正式部署设计。

## 2. File Added In Step 152

Step 152 新增文件：

- `backend/tests/test_local_trial_smoke_execution_plan_schema.py`

Step 152 未修改：

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

Step 152 已用 deterministic fake schema tests 固化以下 smoke execution plan 内容：

- required sections。
- scope boundary。
- execution strategy order。
- preflight command placeholders。
- environment preflight placeholders。
- backend smoke placeholders。
- frontend smoke placeholders。
- Ollama optional smoke placeholders。
- ZDoc preview-only smoke placeholders。
- ZBid preview validator smoke placeholders。
- formal chain block smoke placeholders。
- `output/job/export` write detection placeholder。
- stop conditions。
- pass criteria。
- smoke report template。
- future implementation boundary。
- formal flags false。
- no execution side effects。
- import isolation。

Step 152 已固化 smoke execution plan 的 sections、scope、execution strategy、preflight commands、environment checks、backend / frontend / Ollama placeholders、ZDoc / ZBid preview placeholders、formal chain block placeholders、`output/job/export` 检测、stop conditions、pass criteria、report template 和 future authorization boundary。

该测试文件仅定义本地 fake local trial smoke execution plan factory、本地 fake validator 和本地常量，用于固化 Step 151 的 execution plan 结构。它不新增生产实现，不从正式生成链导入能力，不调用 `orchestrator`、`llm_client`、`provider`、`generation`、`export`、`review/apply`、`actions_bridge` 或 ZBid 相关模块。

## 4. Explicit Non-Capabilities

Step 152 明确不具备以下能力：

- 不执行 smoke test。
- 不启动后端。
- 不启动前端。
- 不运行 Ollama。
- 不运行 `ollama serve`。
- 不访问 `127.0.0.1:11434`。
- 不访问本地端口。
- 不访问任何本地服务端口。
- 不调用模型。
- 不调用外部模型/API。
- 不调用 ZBid。
- 不调用 ZBid API / 数据库 / 写回接口。
- 不写 `output/job/export`。
- 不生成 DOCX / JSON / Markdown。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不进入真实 shadow generation implementation。
- 不生成真实 candidate patch。
- 不进入真实 candidate patch implementation。
- 不进入正式正文生成链。
- 不执行 formal writeback。
- 不执行 formal writeback dry-run。
- 不读取真实正文计算 hash。
- 不比较真实 source section 内容。
- 不执行 review/apply isolation。
- 不执行 DOCX isolation。
- 不执行 ZBid isolation。
- 不进入 ZDoc / ZBid 实际联调。
- 不进入本地化部署执行。
- 不进入 50 人团队正式部署设计。

## 5. Safety Invariants Confirmed

Step 152 已确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. docs-only execution plan 不得启动服务。
7. docs-only execution plan 不得访问端口。
8. docs-only execution plan 不得调用 ZBid。
9. docs-only execution plan 不得写 `output/job/export`。
10. docs-only execution plan 不得执行 smoke test。
11. preflight command 只能作为未来占位，不得在本步执行。
12. backend smoke command 只能作为未来占位，不得在本步执行。
13. frontend smoke command 只能作为未来占位，不得在本步执行。
14. Ollama smoke command 只能作为未来占位，不得在本步执行。
15. ZDoc preview-only smoke command 只能作为未来占位，不得在本步执行。
16. ZBid preview validator smoke command 只能作为未来占位，不得在本步执行。
17. 任一正式链 flag 为 true 必须 stop。
18. 出现 `output/job/export` 写入必须 stop。
19. 出现 DOCX 文件必须 stop。
20. 出现 ZBid API / DB / writeback 调用必须 stop。
21. 出现 `/review/apply` 调用必须 stop。
22. 出现 `/generate` 正式生成必须 stop。
23. advisory 被作为 evidence 必须 stop。
24. preview 被误显示为正式正文必须 stop。
25. source hash / version 不一致但未 blocked 必须 stop。
26. `blocked_reasons` 缺失必须 stop。
27. 未来真正执行 smoke test 前，必须单独授权启动后端、前端、访问本地端口、检查 Ollama、读取本地配置、执行 preview-only 测试请求、生成 smoke report、检查 `output/job/export` 差异。

当前所有正式链 flags 仍应保持 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

## 6. Test Evidence From Step 152

Step 152 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_local_trial_smoke_execution_plan_schema.py -vv`
  - 19 passed in 0.05s。

- `python -m pytest backend/tests/test_local_trial_smoke_checklist_schema.py backend/tests/test_local_trial_smoke_execution_plan_schema.py -vv`
  - 36 passed in 0.05s。

- `python -m pytest backend/tests/test_zdoc_zbid_preview_only_integration_contract_schema.py backend/tests/test_zdoc_zbid_preview_packet.py backend/tests/test_zbid_preview_input_validator.py backend/tests/test_local_trial_smoke_checklist_schema.py backend/tests/test_local_trial_smoke_execution_plan_schema.py -vv`
  - 81 passed in 0.12s。

- `python -m pytest backend/tests/test_local_trial_smoke_execution_plan_schema.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - 22 passed in 0.85s。

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。该事实不得在本复盘中扩大解释为生产功能风险。

Step 153 不运行 pytest；以上为 Step 152 的测试证据归档。

## 7. Boundary Against Actual Smoke Execution

Step 152 未执行以下动作：

- backend startup。
- frontend startup。
- Ollama startup。
- health check execution。
- local port access。
- ZDoc / ZBid actual integration。
- local deployment execution。
- 50-user deployment design。
- any writeback。
- any export。
- any model call。

Step 152 未执行真实 smoke test，未启动后端服务，未启动前端服务，未运行 Ollama，未访问 `127.0.0.1:11434`，未访问任何本地服务端口，未调用外部模型/API，未调用 ZBid API / 数据库 / 写回接口，未写 `output/job/export`，未触发 `/generate`、`/export_docx`、`/review/apply`，未触发 ZBid 写回，未进入 ZDoc / ZBid 实际联调，未进入本地化部署执行，未进入 50 人团队正式部署设计。

## 8. Remaining Blockers Before Real Local Trial

进入真实本地小范围试用前仍缺少：

- explicit user authorization to start backend。
- explicit user authorization to start frontend。
- explicit user authorization to access local ports。
- explicit user authorization to check Ollama。
- explicit user authorization to read local config。
- explicit user authorization to execute preview-only test request。
- explicit user authorization to inspect `output/job/export` diff。
- backend health check execution。
- frontend access check execution。
- Ollama optional availability check execution。
- no-write runtime assertion execution。
- preview-only runtime assertion execution。
- actual preview-only packet route。
- actual ZBid preview input route。
- smoke report generation。
- stop/rollback procedure for local services。

这些事项需要在后续步骤单独设计或执行。当前 fake schema tests 不能替代真实 smoke test，也不能证明本地服务、模型、ZDoc / ZBid preview-only 联通、运行时 no-write 断言或授权门禁已可用。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 154：local trial runtime authorization gate design，docs-only。

Step 154 不得启动服务，不得运行 Ollama，不得执行 smoke test，不得调用 ZBid，不得写 `output/job/export`，只设计未来进入真实 smoke test 前的授权门禁、允许命令清单、停止条件和回报模板。

## 10. Safety Conclusion

Step 152 仅完成 local trial smoke execution plan fake schema tests。当前系统仍未执行 smoke test，未完成本地化部署，未完成 ZDoc / ZBid 实际联调，未进入 50 人正式部署设计。

Step 153 仅完成 Step 152 fake schema tests 的 docs-only 复盘归档。本文档不代表本地化部署已执行，不代表 smoke test 已执行，不代表 ZDoc / ZBid 已实际联调，不代表正式写回、DOCX 导出、ZBid 写回、review/apply、formal writeback、formal writeback dry-run 或 50 人团队正式部署设计已实现。
