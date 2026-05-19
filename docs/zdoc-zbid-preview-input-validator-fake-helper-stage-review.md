# ZDoc/ZBid Preview Input Validator Fake Helper Stage Review

## 1. Scope

Step 146 仅为 Step 145 fake-only ZBid preview input validator 的实现复盘归档。本文档用于明确 Step 145 新增 validator 的能力边界、安全约束、测试结论、未实现事项和后续推进条件。

Step 145 新增的 validator 只校验 fake-only preview metadata packet。它仅接收 `dict` 类型 fake preview packet，并返回 `dict` 类型 validation result。当前系统仍处于 preview-only / no-write 阶段，本复盘不代表真实 ZDoc / ZBid 联调、ZBid 写回、DOCX 导出、review/apply、formal writeback 或本地化部署已实现。

## 2. Files Added In Step 145

Step 145 新增文件：

- `backend/zhifei_autoplan/zbid_preview_input_validator.py`
- `backend/tests/test_zbid_preview_input_validator.py`

Step 145 未修改：

- 生产主链。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- DOCX / ZBid / export / review / generation 链路。

## 3. Validator Capability Summary

validator 当前能力仅限于：

- 接收 fake ZDoc / ZBid preview packet `dict`。
- 返回 fake validation result `dict`。
- 固化 `zbid_preview_validation_status` / `zbid_preview_validation_decision` 枚举。
- 校验 required fields。
- 校验 `tender_file_refs`。
- 校验 `scoring_clause_refs`。
- 校验 `evidence_anchor_refs`。
- 阻断 generated advisory / preview advisory / shadow candidate / patch preview / diff preview / rollback plan / dry-run result 作为 evidence。
- 阻断 `thinking_only_fallback`。
- 阻断 high input risk without validation。
- 阻断 failed advisory quality gate。
- 阻断 `future_guarded_writeback`。
- 阻断 `zbid_writeback` / `docx_export` / `review_apply` / `formal_writeback` / `output_write` 请求。
- 固化 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒 false。

validator 不得把 `preview_advisory_summary`、`shadow_candidate_id`、`patch_id`、`diff_preview_id`、`rollback_plan_id`、`dry_run_id` 当作 evidence。`accepted_metadata_only` / `accepted_preview_only` 不等于写回许可，不等于 evidence，也不得打开任何正式链 flag。

## 4. Explicit Non-Capabilities

validator 明确不具备以下能力：

- 不实现真实 ZBid 输入接口。
- 不调用 ZBid。
- 不调用 ZBid API / 数据库 / 写回接口。
- 不启动服务。
- 不启动后端服务。
- 不启动前端服务。
- 不运行 Ollama。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不执行正式写回。
- 不生成 DOCX / JSON / Markdown。
- 不写 `output/job/export`。
- 不进入 ZDoc / ZBid 实际联调。
- 不进入本地化部署执行。
- 不进入 50 人团队正式部署设计。
- 不把 preview advisory / shadow candidate / patch / diff / rollback / dry-run 当 evidence。
- 不把 accepted preview 当 writeback permission。

## 5. Safety Invariants Confirmed

Step 145 已确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. safe metadata-only input 可 `accepted_metadata_only`，但不得打开正式链 flags。
7. safe preview-only input 可 `accepted_preview_only`，但不得打开正式链 flags。
8. 非 `dict` 输入必须 blocked。
9. `integration_request_id` 缺失必须 blocked。
10. `project_id` 缺失必须 blocked。
11. `document_id` 缺失必须 blocked。
12. `section_id` 缺失必须 blocked。
13. `section_hash` 缺失必须 blocked。
14. `section_version` 缺失必须 blocked。
15. `tender_file_refs` 为空必须 blocked。
16. `scoring_clause_refs` 为空必须 blocked。
17. `evidence_anchor_status=missing` 必须 blocked。
18. `evidence_anchor_refs` 为空必须 blocked。
19. generated advisory 作为 evidence 必须 blocked。
20. preview advisory 作为 evidence 必须 blocked。
21. shadow candidate 作为 evidence 必须 blocked。
22. patch preview 作为 evidence 必须 blocked。
23. diff preview 作为 evidence 必须 blocked。
24. rollback plan 作为 evidence 必须 blocked。
25. dry-run result 作为 evidence 必须 blocked。
26. `thinking_only_fallback` 必须 blocked。
27. `unsupported` / `blocked` response mode 必须 blocked。
28. high input risk without validation 必须 blocked。
29. advisory quality gate failed 必须 blocked。
30. `future_guarded_writeback` 当前必须 blocked。
31. `zbid_writeback_requested=true` 必须 blocked。
32. `docx_export_requested=true` 必须 blocked。
33. `review_apply_requested=true` 必须 blocked。
34. `formal_writeback_requested=true` 必须 blocked。
35. `output_write_requested=true` 必须 blocked。
36. validator 不调用 ZBid。
37. validator 不启动服务。
38. validator 不触发 `/generate`、`/export_docx`、`/review/apply`。
39. validator 不写 `output/job/export`。
40. validator import 不得拉入主链或 ZBid 模块。

## 6. Test Evidence From Step 145

Step 145 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_zbid_preview_input_validator.py -vv`
  - 最终 16 passed in 0.04s。
  - 首次发现 1 个新增 validator 内部硬阻断判定问题，已仅修改新增 validator 后通过。

- `python -m pytest backend/tests/test_zdoc_zbid_preview_only_integration_contract_schema.py backend/tests/test_zdoc_zbid_preview_packet.py backend/tests/test_zbid_preview_input_validator.py -vv`
  - 45 passed in 0.08s。

- `python -m pytest` 指定 guard / contract / helper 组合 `-vv`
  - 253 passed in 0.41s。

- `python -m pytest backend/tests/test_zbid_preview_input_validator.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - 19 passed in 0.80s。

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。该事实不得在本复盘中扩大解释为生产功能风险。

## 7. Boundary Against Actual Integration And Deployment

Step 145 未接入以下链路：

- `orchestrator`
- `llm_client`
- `provider`
- `generation`
- `export`
- DOCX export
- review/apply
- `actions_bridge`
- ZBid API / DB / writeback
- `output/job/export`
- backend service startup
- frontend service startup
- Ollama runtime
- local deployment execution
- 50 人团队正式部署设计

## 8. Remaining Blockers Before Actual Local Trial

未来进入实际本地试用前仍缺少：

- local service startup checklist execution。
- backend health check execution。
- frontend access check execution。
- Ollama availability check execution。
- actual preview-only packet route。
- actual ZBid preview input route。
- ZBid preview UI / matrix draft。
- evidence anchor real validation。
- scoring clause real validation。
- `blocked_reasons` UI display。
- local trial feedback log。
- small-team trial data set。
- no-write runtime smoke tests。
- ZDoc / ZBid preview-only integration smoke tests。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 147：ZDoc/ZBid preview packet and validator stage review，docs-only。

Step 147 不得实现接口，不得启动服务，不得调用 ZBid，不得运行 Ollama，不得进入本地化部署执行，不得进入 50 人团队正式部署设计。

## 10. Safety Conclusion

Step 145 仅完成 fake-only ZBid preview input validator。当前系统仍处于 preview-only / no-write 阶段，不代表 ZDoc / ZBid 已联调，不代表 ZBid 写回、DOCX 导出、review/apply、formal writeback 或本地部署已实现。
