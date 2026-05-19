# ZDoc Local Trial Smoke Checklist Fake Schema Stage Review

## 1. Scope

Step 150 仅为 Step 149 fake schema tests 的 docs-only 复盘归档。

本复盘对应 Step 149：`local trial smoke checklist fake schema tests`，目标是归档 local trial smoke checklist fake schema tests 的覆盖范围、能力边界、未执行事项、正式链阻断、no-write 约束和后续推进条件。

Step 149 新增的测试文件只固化 local trial smoke checklist 的结构和阻断规则。它不执行真实 smoke test，不启动服务，不运行 Ollama，不调用 ZBid，不写 `output/job/export`，不进入本地化部署执行，不进入 50 人团队正式部署设计。

本文档不代表本地化部署已执行，不代表 smoke test 已执行，不代表 ZDoc / ZBid 已实际联调，不代表 50 人部署设计已启动。

当前总体策略仍为：

- 先完成本地化部署基础闭环。
- 再完成 ZDoc 与 ZBid 的 preview-only 对接。
- 再进行小范围试用和问题修正。
- 最后再按约 50 人同时使用场景进行正式部署设计。

## 2. File Added In Step 149

Step 149 新增文件：

- `backend/tests/test_local_trial_smoke_checklist_schema.py`

Step 149 未修改：

- 生产代码。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- 部署脚本。
- 服务配置。
- `.env` / local config。
- 数据库、模型、缓存或运行时文件。

## 3. Schema Test Coverage Summary

Step 149 已用 deterministic fake schema tests 固化以下 local trial smoke checklist 内容：

- required checklist sections。
- trial positioning。
- pre-run manual checklist。
- backend smoke checklist。
- frontend smoke checklist。
- Ollama smoke checklist。
- ZDoc preview packet checklist。
- ZBid preview input validator checklist。
- DOCX / review/apply / ZBid / formal writeback block checklist。
- evidence and scoring checklist。
- audit fields checklist。
- failure handling checklist。
- smoke test pass criteria。
- smoke test stop criteria。
- formal flags false。
- no execution side effects。
- import isolation。

Step 149 已固化本地试用 smoke checklist 的章节结构、pre-run 检查项、backend / frontend / Ollama / ZDoc / ZBid / DOCX / review/apply / ZBid / formal writeback 阻断项、evidence / scoring 边界、audit fields、failure handling、pass criteria 和 stop criteria。

该测试文件仅定义本地 fake local trial smoke checklist factory、本地 fake validator 和本地常量，用于固化 Step 148 的 checklist 结构。它不新增生产实现，不从正式生成链导入能力，不调用 `orchestrator`、`llm_client`、`provider`、`generation`、`export`、`review/apply`、`actions_bridge` 或 ZBid 相关模块。

## 4. Explicit Non-Capabilities

Step 149 明确不具备以下能力：

- 不执行 smoke test。
- 不启动后端。
- 不启动前端。
- 不运行 Ollama。
- 不运行 `ollama serve`。
- 不访问 `127.0.0.1:11434`。
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

Step 149 已确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. `/export_docx` 请求必须 blocked。
7. DOCX 文件不得生成。
8. `/review/apply` 请求必须 blocked。
9. ZBid writeback 请求必须 blocked。
10. ZBid API / DB / writeback 不得调用。
11. formal writeback 请求必须 blocked。
12. `output/job/export` 写入必须 blocked。
13. dry-run passed 不得开放 formal writeback。
14. source hash matched 不得开放 formal writeback。
15. DOCX isolation passed 不得开放 ZBid。
16. ZBid isolation passed 不得开放 ZBid writeback。
17. `evidence_anchor_refs` 必须来源可验证资料。
18. `scoring_clause_refs` 必须指向可验证评分条款。
19. `tender_file_refs` 不等于自动 evidence。
20. preview advisory 不得作为 evidence。
21. ZBid scoring preview 不得作为 evidence。
22. AI 建议不得作为 evidence。
23. 缺少 evidence 或评分条款必须 `requires_human_review` 或 blocked。
24. 不得臆造评分条款。
25. 任一正式链 flag 为 true 必须 stop。
26. 出现 `output/job/export` 写入必须 stop。
27. 出现 DOCX 文件必须 stop。
28. 出现 ZBid API / DB / writeback 调用必须 stop。
29. 出现 `/review/apply` 调用必须 stop。
30. 出现 `/generate` 正式生成必须 stop。
31. advisory 被作为 evidence 必须 stop。
32. preview 被误显示为正式正文必须 stop。
33. source hash / version 不一致但未 blocked 必须 stop。
34. 无 `blocked_reasons` 必须 stop。

当前所有正式链 flags 仍应保持 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

## 6. Test Evidence From Step 149

Step 149 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_local_trial_smoke_checklist_schema.py -vv`
  - 17 passed in 0.04s。

- `python -m pytest backend/tests/test_zdoc_zbid_preview_only_integration_contract_schema.py backend/tests/test_zdoc_zbid_preview_packet.py backend/tests/test_zbid_preview_input_validator.py backend/tests/test_local_trial_smoke_checklist_schema.py -vv`
  - 62 passed in 0.10s。

- `python -m pytest backend/tests/test_local_trial_smoke_checklist_schema.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - 20 passed in 0.80s。

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。该事实不得在本复盘中扩大解释为生产功能风险。

Step 150 不运行 pytest；以上为 Step 149 的测试证据归档。

## 7. Boundary Against Actual Smoke Execution

Step 149 未执行以下动作：

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

Step 149 未启动后端服务，未启动前端服务，未运行 Ollama，未访问 `127.0.0.1:11434`，未访问任何本地服务端口，未调用外部模型/API，未调用 ZBid API / 数据库 / 写回接口，未写 `output/job/export`，未触发 `/generate`、`/export_docx`、`/review/apply`，未触发 ZBid 写回，未进入 ZDoc / ZBid 实际联调，未进入本地化部署执行，未进入 50 人团队正式部署设计。

## 8. Remaining Blockers Before Real Local Trial

进入真实本地小范围试用前仍缺少：

- local service startup execution plan。
- backend health check command design。
- frontend access check command design。
- Ollama optional availability command design。
- no-write runtime assertion design。
- preview-only runtime assertion design。
- `output/job/export` write detection design。
- ZDoc preview packet route design。
- ZBid preview input route design。
- `blocked_reasons` UI display check。
- local trial dataset selection。
- local trial feedback log design。
- rollback/stop procedure design。

这些事项需要在后续步骤单独设计或执行。当前 fake schema tests 不能替代真实本地试用执行，也不能证明本地服务、模型、ZDoc / ZBid preview-only 联通或运行时 no-write 断言已可用。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 151：local trial smoke execution plan design，docs-only。

Step 151 不得启动服务，不得运行 Ollama，不得执行 smoke test，不得调用 ZBid，不得写 `output/job/export`，只设计未来 smoke test 的执行顺序、命令占位、停止条件和回报格式。

## 10. Safety Conclusion

Step 149 仅完成 local trial smoke checklist fake schema tests。当前系统仍未执行 smoke test，未完成本地化部署，未完成 ZDoc / ZBid 实际联调，未进入 50 人正式部署设计。

Step 150 仅完成 Step 149 fake schema tests 的 docs-only 复盘归档。本文档不代表本地化部署已执行，不代表 smoke test 已执行，不代表 ZDoc / ZBid 已实际联调，不代表正式写回、DOCX 导出、ZBid 写回、review/apply、formal writeback、formal writeback dry-run 或 50 人团队正式部署设计已实现。
