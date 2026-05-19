# ZDoc/ZBid Preview Packet and Validator Fake Stage Review

## 1. Scope

Step 147 仅为 Step 144 与 Step 145 的 combined docs-only stage review。

本复盘对应：

- Step 144：fake-only ZDoc / ZBid preview packet helper。
- Step 145：fake-only ZBid preview input validator。

本文档目标是归档 preview packet 生成与 validator 校验的联合边界、preview-only 数据流、evidence 边界、scoring refs 边界、`blocked_reasons`、正式链 flags、测试证据和后续推进条件。

Step 144 新增的 preview packet helper 只构造 fake-only / metadata-only preview packet。Step 145 新增的 ZBid preview input validator 只校验 fake preview packet。本文档不代表真实 ZDoc / ZBid 联调、ZBid 写回、DOCX 导出、review/apply、formal writeback 或本地化部署已实现。

## 2. Files Added In Step 144 And Step 145

Step 144 新增：

- `backend/zhifei_autoplan/zdoc_zbid_preview_packet.py`
- `backend/tests/test_zdoc_zbid_preview_packet.py`

Step 145 新增：

- `backend/zhifei_autoplan/zbid_preview_input_validator.py`
- `backend/tests/test_zbid_preview_input_validator.py`

Step 144 / Step 145 未修改：

- 生产主链。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- DOCX / ZBid / export / review / generation 链路。

## 3. Preview Packet Capability Summary

preview packet helper 当前能力仅限于：

- 构造 fake ZDoc / ZBid preview-only integration packet。
- 固化 `zbid_preview_mode` / `zbid_input_status` / `zbid_mapping_status` / `zbid_scoring_matrix_status`。
- 校验 `tender_file_refs`、`scoring_clause_refs`、`evidence_anchor_refs` 的 basic metadata 条件。
- 阻断 generated advisory / preview advisory / shadow candidate / patch preview / diff preview / rollback plan / dry-run result 作为 evidence。
- 阻断 `zbid_writeback`、`docx_export`、`review_apply`、`formal_writeback`、`output_write` 请求。
- 固化 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒 false。

preview packet helper 不实现真实 ZDoc / ZBid 接口，不调用 ZBid，不调用 ZBid API / 数据库 / 写回接口，不启动后端服务，不启动前端服务，不运行 Ollama，不触发 `/generate`、`/export_docx`、`/review/apply`，不触发 ZBid 写回，不执行正式写回，不写 `output/job/export`，不生成 DOCX / JSON / Markdown，不进入本地化部署执行，不进入 50 人团队正式部署设计。

## 4. Validator Capability Summary

ZBid preview input validator 当前能力仅限于：

- 接收 fake preview packet `dict`。
- 返回 fake validation result `dict`。
- 固化 `zbid_preview_validation_status` / `zbid_preview_validation_decision`。
- 校验 required fields。
- 校验 `tender_file_refs`。
- 校验 `scoring_clause_refs`。
- 校验 `evidence_anchor_refs`。
- 阻断 generated advisory / preview advisory / shadow candidate / patch preview / diff preview / rollback plan / dry-run result 作为 evidence。
- 阻断 `thinking_only_fallback`。
- 阻断 high input risk without validation。
- 阻断 failed advisory quality gate。
- 阻断 `future_guarded_writeback`。
- 阻断正式链请求。
- 固化 formal flags 恒 false。

validator 不实现真实 ZBid 输入接口，不调用 ZBid，不调用 ZBid API / 数据库 / 写回接口，不启动后端服务，不启动前端服务，不运行 Ollama，不触发 `/generate`、`/export_docx`、`/review/apply`，不触发 ZBid 写回，不执行正式写回，不写 `output/job/export`，不生成 DOCX / JSON / Markdown，不进入本地化部署执行，不进入 50 人团队正式部署设计。

## 5. Combined Preview-Only Flow

当前 fake-only 逻辑流为：

1. ZDoc 生成 preview-only metadata packet。
2. packet 包含 source / target / project / document / section / evidence / scoring refs。
3. packet 不包含可写回正文。
4. packet 不触发 ZBid。
5. validator 接收 packet `dict`。
6. validator 检查 evidence boundary、scoring refs、risk、quality gate、formal requests。
7. validator 输出 `accepted_metadata_only` / `accepted_preview_only` / `blocked` / `requires_human_review` 等 metadata。
8. 所有正式链 flags 保持 false。
9. 输出仅用于后续小范围试用设计，不进入真实联调。

该流程只固化 preview-only / metadata-only 边界，不构成 ZBid 输入接口实现，不构成 ZBid scoring matrix 实现，不构成 ZBid 写回许可。

## 6. Evidence And Scoring Boundary

联合边界必须满足：

1. `tender_file_refs` 可作为资料追踪字段，但不自动构成 evidence。
2. `scoring_clause_refs` 必须指向可验证评分条款，不得臆造。
3. `evidence_anchor_refs` 必须来源于可验证资料。
4. generated advisory 不得作为 evidence。
5. `preview_advisory_summary` 不得作为 evidence。
6. `shadow_candidate_id` 不得作为 evidence。
7. `patch_id` 不得作为 evidence。
8. `diff_preview_id` 不得作为 evidence。
9. `rollback_plan_id` 不得作为 evidence。
10. `dry_run_id` 不得作为 evidence。
11. ZBid preview scoring 不得作为 evidence。
12. `accepted_preview_only` 不得替代人工审核。
13. `accepted_preview_only` 不得替代 evidence anchor。
14. `accepted_preview_only` 不得替代 formal writeback guard。

`preview_advisory_summary` 仅为提示性 preview 字段，不得作为 evidence。`shadow_candidate_id`、`patch_id`、`diff_preview_id`、`rollback_plan_id`、`dry_run_id` 仅为追踪字段，不得作为 evidence。

## 7. Safety Invariants Confirmed

Step 144 / Step 145 已确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. safe metadata-only input 可 `accepted_metadata_only`，但不得打开正式链 flags。
7. safe preview-only input 可 `accepted_preview_only`，但不得打开正式链 flags。
8. preview-only 不等于写回许可。
9. preview-only 不等于 evidence。
10. 非 `dict` 输入必须 blocked。
11. `integration_request_id` 缺失必须 blocked。
12. `project_id` 缺失必须 blocked。
13. `document_id` 缺失必须 blocked。
14. `section_id` 缺失必须 blocked。
15. `section_hash` 缺失必须 blocked。
16. `section_version` 缺失必须 blocked。
17. `tender_file_refs` 为空必须 blocked。
18. `scoring_clause_refs` 为空必须 blocked。
19. `evidence_anchor_status=missing` 必须 blocked。
20. `evidence_anchor_refs` 为空必须 blocked。
21. generated advisory 作为 evidence 必须 blocked。
22. preview advisory 作为 evidence 必须 blocked。
23. shadow candidate 作为 evidence 必须 blocked。
24. patch preview 作为 evidence 必须 blocked。
25. diff preview 作为 evidence 必须 blocked。
26. rollback plan 作为 evidence 必须 blocked。
27. dry-run result 作为 evidence 必须 blocked。
28. `thinking_only_fallback` 必须 blocked。
29. `unsupported` / `blocked` response mode 必须 blocked。
30. high input risk without validation 必须 blocked。
31. advisory quality gate failed 必须 blocked。
32. `future_guarded_writeback` 当前必须 blocked。
33. `zbid_writeback_requested=true` 必须 blocked。
34. `docx_export_requested=true` 必须 blocked。
35. `review_apply_requested=true` 必须 blocked。
36. `formal_writeback_requested=true` 必须 blocked。
37. `output_write_requested=true` 必须 blocked。
38. helper / validator 不调用 ZBid。
39. helper / validator 不启动服务。
40. helper / validator 不触发 `/generate`、`/export_docx`、`/review/apply`。
41. helper / validator 不写 `output/job/export`。
42. import 不得拉入主链或 ZBid 模块。

`accepted_metadata_only` / `accepted_preview_only` 不等于写回许可，不等于 evidence，也不得打开任何正式链 flag。

## 8. Test Evidence From Step 144

Step 144 已运行并通过以下命令：

- `python -m pytest backend/tests/test_zdoc_zbid_preview_packet.py -vv`
  - 16 passed in 0.05s。

- `python -m pytest backend/tests/test_zdoc_zbid_preview_only_integration_contract_schema.py backend/tests/test_zdoc_zbid_preview_packet.py -vv`
  - 29 passed in 0.06s。

- `python -m pytest` 指定 guard / contract 组合 `-vv`
  - 237 passed in 0.39s。

- `python -m pytest backend/tests/test_zdoc_zbid_preview_packet.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - 19 passed in 0.79s。

## 9. Test Evidence From Step 145

Step 145 已运行并通过以下命令：

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

## 10. Boundary Against Actual Integration And Deployment

Step 144 / Step 145 未接入以下链路：

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

二者均不调用 ZBid，不调用 ZBid API / 数据库 / 写回接口，不启动后端服务，不启动前端服务，不运行 Ollama，不触发 `/generate`、`/export_docx`、`/review/apply`，不触发 ZBid 写回，不执行正式写回，不写 `output/job/export`，不生成 DOCX / JSON / Markdown，不进入本地化部署执行，不进入 50 人团队正式部署设计。

## 11. Remaining Blockers Before Actual Local Trial

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

## 12. Recommended Next Step

建议下一步为：

ZDoc Step 148：local trial smoke checklist design，docs-only。

Step 148 不得实现部署脚本，不得启动服务，不得运行 Ollama，不得执行 ZDoc / ZBid 联调，不得进入 50 人正式部署设计，仅设计小范围本地试用 smoke checklist。

## 13. Safety Conclusion

Step 147 仅完成 ZDoc / ZBid preview packet and validator fake stage review。当前系统仍处于 preview-only / no-write 阶段，不代表 ZDoc / ZBid 已联调，不代表 ZBid 写回、DOCX 导出、review/apply、formal writeback 或本地部署已实现。
