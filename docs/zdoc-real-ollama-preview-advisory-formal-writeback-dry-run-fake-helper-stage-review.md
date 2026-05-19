# ZDoc Real Ollama Preview Advisory - Formal Writeback Dry-Run Fake Helper Stage Review

## 1. Scope

Step 140 仅为 Step 139 fake-only formal writeback dry-run helper 的实现复盘归档，目标是明确其能力边界、安全约束、测试结论、未实现事项和后续推进条件。

Step 139 新增的 helper 只构造 formal writeback dry-run metadata envelope。它不执行真实 dry-run，不执行正式写回，不修改 source section，不读取真实正文，不写 `output/job/export`，不触发 review/apply，不触发 `/export_docx`，不生成 DOCX / JSON / Markdown，不触发 ZBid 写回，不调用 ZBid API、数据库或写回接口。

当前系统仍处于 preview-only / no-write 阶段。本文档不代表真实 dry-run、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。

当前总体策略仍为先完成本地化部署基础闭环和 ZDoc / ZBid 小范围对接试用，最后再按约 50 人同时使用场景开展正式部署设计。本步不进入 50 人部署设计。

## 2. Files Added in Step 139

Step 139 新增文件：

- `backend/zhifei_autoplan/formal_writeback_dry_run.py`
- `backend/tests/test_formal_writeback_dry_run.py`

Step 139 未修改：

- 生产主链。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- DOCX / ZBid / export / review / generation 链路。
- orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge、ZBid 相关链路。

## 3. Helper Capability Summary

Step 139 helper 当前能力仅限于：

- 构造 formal writeback dry-run metadata dict。
- 固化 Step 137 / Step 138 formal writeback dry-run contract 字段。
- 固化 `dry_run_status`、`dry_run_decision`、`dry_run_scope`、`dry_run_mode`、`dry_run_target_type`、`dry_run_request_status` 枚举。
- 固化 `blocked_reasons`。
- 固化 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒 false。
- 接收调用方传入 `generated_at`。
- 生成确定性 `dry_run_id`，或使用调用方显式传入的固定 `dry_run_id`。
- 接收 `dry_run_payload_hash`、`dry_run_candidate_hash` 等 fake metadata 字段并保持阻断。

`generated_at` 由调用方显式传入，不使用非确定性时间。`dry_run_id` 必须为确定性生成或显式固定值，不使用 uuid、random、当前时间。

`dry_run_payload_hash`、`dry_run_candidate_hash` 只能由调用方显式传入。当前阶段不得读取真实 payload、真实正文、真实 DOCX 或真实 ZBid 数据生成这些 hash。

## 4. Explicit Non-Capabilities

Step 139 helper 明确不具备以下能力：

- 不执行真实 dry-run。
- 不执行正式写回。
- 不修改 source section。
- 不读取真实正文。
- 不写 `output/job/export`。
- 不触发 review/apply。
- 不触发 `/review/apply`。
- 不触发 `/export_docx`。
- 不生成 DOCX / JSON / Markdown。
- 不触发 ZBid 写回。
- 不调用 ZBid API / DB / 写回接口。
- 不读取真实 payload。
- 不读取真实 DOCX。
- 不读取真实 ZBid 数据。
- 不接正式生成链。
- 不接 orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge、ZBid。
- 不调用本地模型、外部模型、Ollama、API 或服务。
- 不读写文件。
- 不把 dry-run 当 evidence。
- 不把 `passed_shadow_only` 当 formal writeback permission。
- 不把 `pass_shadow_only` 当 formal writeback permission。
- 不把 dry-run passed 当 DOCX / ZBid / export 准入。
- 不把 dry-run 当 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation、review/apply isolation、DOCX isolation 或 ZBid isolation 的替代条件。

`dry_run_status=passed_shadow_only` 不等于 `formal_writeback_allowed=true`。

`dry_run_decision=pass_shadow_only` 不等于 `formal_writeback_allowed=true`。

## 5. Safety Invariants Confirmed

Step 139 helper 和测试固化了以下安全约束：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. helper 只输出 `not_created`、`blocked`、`stale_source_hash` 或 `stale_source_version`。
7. helper 不输出 `simulated_shadow_only` 或 `passed_shadow_only`。
8. `passed_shadow_only` 不等于可正式写回。
9. `pass_shadow_only` 不等于可正式写回。
10. missing `shadow_candidate_id` 必须 blocked。
11. missing `patch_id` 必须 blocked。
12. missing `approval_id` 必须 blocked。
13. missing `diff_preview_id` 必须 blocked。
14. missing `rollback_plan_id` 必须 blocked。
15. missing `writeback_guard_id` 必须 blocked。
16. missing `source_hash_guard_id` 必须 blocked。
17. missing `review_apply_guard_id` 必须 blocked。
18. missing `docx_isolation_guard_id` 必须 blocked。
19. missing `zbid_isolation_guard_id` 必须 blocked。
20. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
21. `patch_status=blocked` 或 `not_created` 必须 blocked。
22. `approval_status` 非 `approved_shadow_only` 必须 blocked。
23. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
24. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
25. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
26. `source_hash_guard_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
27. `review_apply_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
28. `docx_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
29. `zbid_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
30. `thinking_only_fallback` 必须 blocked。
31. missing evidence anchor 必须 blocked。
32. empty evidence refs 必须 blocked。
33. advisory / shadow candidate / patch preview / diff preview / rollback plan 作为 evidence 均必须 blocked。
34. `source_hash_match=false` 必须 `stale_source_hash` 或 blocked。
35. `source_version_match=false` 必须 `stale_source_version` 或 blocked。
36. `current_source_section_hash` 缺失必须 blocked。
37. `current_source_section_version` 缺失必须 blocked。
38. `dry_run_requested=true` 必须 blocked。
39. `dry_run_payload_hash` 缺失必须 blocked。
40. `dry_run_candidate_hash` 缺失必须 blocked。
41. `dry_run_source_snapshot_hash` 缺失必须 blocked。
42. `writeback_candidate_hash` 缺失必须 blocked。
43. `docx_candidate_hash` 缺失必须 blocked。
44. `zbid_candidate_hash` 缺失必须 blocked。
45. `zbid_target_mapping_hash` 缺失必须 blocked。
46. `source_snapshot_hash` 缺失必须 blocked。
47. `before_text_hash` 缺失必须 blocked。
48. `after_text_preview_hash` 缺失必须 blocked。
49. `patch_operations_preview_hash` 缺失必须 blocked。
50. `diff_preview_hash` 缺失必须 blocked。
51. `rollback_plan_hash` 缺失必须 blocked。
52. human approval 缺失必须 blocked。
53. `diff_preview_ready=false` 必须 blocked。
54. `rollback_plan_ready=false` 必须 blocked。
55. `formal_writeback_guard_ready=false` 必须 blocked。
56. `source_hash_revalidation_ready=false` 必须 blocked。
57. `review_apply_isolation_ready=false` 必须 blocked。
58. `docx_isolation_ready=false` 必须 blocked。
59. `zbid_isolation_ready=false` 必须 blocked。
60. DOCX export request 必须 blocked。
61. ZBid writeback request 必须 blocked。
62. `output/job/export` write request 必须 blocked。
63. formal generation request 必须 blocked。
64. review/apply request 必须 blocked。
65. `dry_run_request_triggered=true` 必须 blocked。
66. helper 不执行真实 dry-run。
67. helper 不执行 formal writeback。
68. helper 不触发 `/review/apply`、`/export_docx`、ZBid 写回。
69. helper 不读取真实 payload、真实正文、DOCX 或 ZBid 数据生成 hash。
70. helper import 不得拉入主链、导出链或 ZBid 模块。

这些约束共同保证：fake-only dry-run metadata envelope 不能被误用为正式写回许可、DOCX 导出准入、ZBid 写回准入或任何上游 evidence / approval / guard 的替代品。

## 6. Test Evidence from Step 139

Step 139 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_formal_writeback_dry_run.py -vv`
  - 最终 `19 passed in 0.04s`。
  - 首次运行发现 1 个新增 helper 内部 request 映射问题，已仅修改新增 helper 后通过。

- `python -m pytest backend/tests/test_formal_writeback_dry_run_contract_schema.py backend/tests/test_formal_writeback_dry_run.py -vv`
  - `37 passed in 0.08s`。

- `python -m pytest` 指定 guard / contract / helper 组合 `-vv`
  - `428 passed in 0.54s`。

- `python -m pytest backend/tests/test_formal_writeback_dry_run.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `22 passed in 0.85s`。

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。该事实不得在本复盘中扩大解释为生产功能风险。

Step 140 是 docs-only stage review。本步不运行 pytest。

## 7. Boundary Against Formal Generation and Writeback Chains

Step 139 未接入以下链路：

- orchestrator。
- llm_client。
- provider。
- generation。
- export。
- DOCX export。
- review/apply。
- actions_bridge。
- ZBid API / DB / writeback。
- `output/job/export`。

formal writeback dry-run helper 只在 helper 层构造 metadata dict。它不进入正式正文生成链，不触发真实 shadow generation implementation，不生成真实 candidate patch，不进入真实 candidate patch implementation，不执行真实 diff，不执行真实 rollback，不执行真实 formal writeback，不执行真实 formal writeback dry-run。

## 8. Remaining Blockers Before Actual Writeback / DOCX / ZBid

未来进入正式写回、DOCX 导出或 ZBid 写回前，仍至少缺少：

- real evidence anchor validation。
- real shadow generation implementation。
- real candidate patch generation。
- approval UI。
- approval persistence / audit storage。
- real diff implementation。
- real rollback implementation。
- real source hash computation。
- real source section comparison。
- actual review/apply guarded implementation。
- actual DOCX isolation implementation。
- actual ZBid isolation implementation。
- actual dry-run execution。
- explicit user approval flow。
- no-write regression tests。
- formal writeback dry-run integration tests。
- actual writeback apply implementation。
- rollback execution verification。
- DOCX post-write isolation verification。
- ZBid post-write isolation verification。
- 小范围试用验证。
- ZDoc / ZBid 对接联调验证。

在这些 blocker 解除前，任何 dry-run passed 类状态都不得作为正式写回、DOCX 导出、ZBid 写回、review/apply 或 `output/job/export` 写入的许可。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 141：local trial integration checklist design，docs-only。

Step 141 不得实现部署脚本，不得启动服务，不得运行 Ollama，不得执行 ZDoc / ZBid 联调，不得进入 50 人正式部署设计。Step 141 仅设计本地试用集成检查清单。

## 10. Safety Conclusion

Step 139 仅完成 fake-only formal writeback dry-run metadata helper。当前系统仍处于 preview-only / no-write 阶段，不代表正式 dry-run、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。

Step 140 仅归档上述实现边界与测试结论。本步不修改代码，不修改 tests，不修改既有 docs，不运行 pytest，不启动服务，不调用模型，不触发导出、写回、dry-run、review/apply、DOCX 或 ZBid 链路。
