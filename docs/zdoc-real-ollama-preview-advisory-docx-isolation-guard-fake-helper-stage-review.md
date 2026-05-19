# ZDoc Real Ollama Preview Advisory - DOCX Isolation Guard Fake Helper Stage Review

## 1. Scope

Step 132 仅为 Step 131 fake-only DOCX isolation guard helper 的实现复盘归档。本文档只记录 helper 的能力边界、安全约束、测试结论、未实现事项和后续推进条件，不新增实现，不修改既有实现，不触发任何运行时链路。

Step 131 新增的 helper 只构造 DOCX isolation metadata envelope，用于把 Step 129 / Step 130 的 DOCX isolation guard contract 固化为可测试、可审计的 fake-only metadata dict。当前系统仍处于 preview-only / no-write 阶段。

本文档不代表真实 DOCX isolation、DOCX 导出、正式写回、review/apply 或 ZBid 写回已实现。

## 2. Files Added in Step 131

Step 131 新增文件：

- `backend/zhifei_autoplan/docx_isolation_guard.py`
- `backend/tests/test_docx_isolation_guard.py`

Step 131 未修改：

- 生产主链。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- DOCX / ZBid / export / review / generation 链路。
- orchestrator / llm_client / provider / actions_bridge / ZBid 相关链路。

## 3. Helper Capability Summary

Step 131 helper 当前能力仅限于：

- 构造 DOCX isolation metadata dict。
- 固化 Step 129 / Step 130 DOCX isolation guard contract 字段。
- 固化 `docx_isolation_status` / `docx_export_decision` / `docx_export_scope` / `docx_export_mode` / `docx_target_type` / `docx_export_request_status` 枚举。
- 固化 `blocked_reasons` 稳定字符串。
- 固化 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒 false。
- 接收调用方传入 `generated_at`。
- 生成确定性 `docx_isolation_guard_id`，或使用调用方显式固定的 `docx_isolation_guard_id`。
- 接收 `docx_export_route`、`docx_export_payload_hash`、`docx_candidate_hash`、`docx_source_snapshot_hash` 等 fake metadata 字段并保持阻断。
- 接收 ZBid / output / formal generation / review apply / export docx request 的 fake trigger metadata 并保持阻断。

helper 仅汇总 metadata 和 blocker，不执行 isolation，不生成导出产物，不执行写回。

## 4. Explicit Non-Capabilities

Step 131 helper 明确不具备以下能力：

- 不触发 `/export_docx`。
- 不执行 DOCX 导出。
- 不生成 DOCX / JSON / Markdown。
- 不读取真实 DOCX。
- 不读取真实正文。
- 不修改 source section。
- 不写 `output/job/export`。
- 不执行 formal writeback。
- 不触发 review/apply。
- 不触发 `/review/apply`。
- 不接 ZBid 写回。
- 不开放 DOCX export。
- 不开放 ZBid writeback。
- 不读取真实 payload。
- 不实现真实 DOCX isolation。
- 不实现 ZBid isolation guard。
- 不调用本地模型。
- 不调用外部模型。
- 不调用 Ollama。
- 不调用 API 或服务。
- 不读写文件。
- 不接 orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge、ZBid。
- 不 import `docx`、`python-docx` 或任何 DOCX 导出模块。
- 不把 DOCX isolation 当 evidence。
- 不把 DOCX isolation 当 export permission。
- 不把 DOCX isolation 当 ZBid / export 准入。
- 不把 DOCX isolation 当 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation 或 review/apply isolation 的替代条件。

`generated_at` 由调用方显式传入，不使用非确定性时间。`docx_isolation_guard_id` 必须为确定性生成或显式固定值，不使用 uuid、random、当前时间。`docx_export_payload_hash`、`docx_candidate_hash` 只能由调用方显式传入，当前阶段不得读取真实 payload、真实 DOCX 或真实正文生成。`docx_export_route` 仅作为 fake metadata 字段，不触发真实路由。

`docx_isolation_status=isolated_shadow_only` 不等于 `docx_export_allowed=true`。`docx_export_decision=isolate_shadow_only` 不等于 `docx_export_allowed=true`。当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒为 false。

## 5. Safety Invariants Confirmed

Step 131 helper 和测试确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. helper 只输出 `not_created`、`blocked`、`stale_source_hash` 或 `stale_source_version`。
7. helper 不输出 `isolated_shadow_only` 或 `ready_for_future_manual_export`。
8. `isolated_shadow_only` 不等于可导出 DOCX。
9. `isolate_shadow_only` 不等于可导出 DOCX。
10. missing `shadow_candidate_id` 必须 blocked。
11. missing `patch_id` 必须 blocked。
12. missing `approval_id` 必须 blocked。
13. missing `diff_preview_id` 必须 blocked。
14. missing `rollback_plan_id` 必须 blocked。
15. missing `writeback_guard_id` 必须 blocked。
16. missing `source_hash_guard_id` 必须 blocked。
17. missing `review_apply_guard_id` 必须 blocked。
18. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
19. `patch_status=blocked` 或 `not_created` 必须 blocked。
20. `approval_status` 非 `approved_shadow_only` 必须 blocked。
21. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
22. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
23. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
24. `source_hash_guard_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
25. `review_apply_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
26. `thinking_only_fallback` 必须 blocked。
27. missing evidence anchor 必须 blocked。
28. empty evidence refs 必须 blocked。
29. advisory / shadow candidate / patch preview / diff preview / rollback plan 作为 evidence 均必须 blocked。
30. `source_hash_match=false` 必须 `stale_source_hash` 或 blocked。
31. `source_version_match=false` 必须 `stale_source_version` 或 blocked。
32. `current_source_section_hash` 缺失必须 blocked。
33. `current_source_section_version` 缺失必须 blocked。
34. `docx_export_requested=true` 必须 blocked。
35. `docx_export_route=/export_docx` 必须 blocked。
36. `docx_export_payload_hash` 缺失必须 blocked。
37. `docx_candidate_hash` 缺失必须 blocked。
38. `docx_source_snapshot_hash` 缺失必须 blocked。
39. `writeback_candidate_hash` 缺失必须 blocked。
40. `source_snapshot_hash` 缺失必须 blocked。
41. `before_text_hash` 缺失必须 blocked。
42. `after_text_preview_hash` 缺失必须 blocked。
43. `patch_operations_preview_hash` 缺失必须 blocked。
44. `diff_preview_hash` 缺失必须 blocked。
45. `rollback_plan_hash` 缺失必须 blocked。
46. human approval 缺失必须 blocked。
47. `diff_preview_ready=false` 必须 blocked。
48. `rollback_plan_ready=false` 必须 blocked。
49. `formal_writeback_guard_ready=false` 必须 blocked。
50. `source_hash_revalidation_ready=false` 必须 blocked。
51. `review_apply_isolation_ready=false` 必须 blocked。
52. ZBid isolation not ready 不得开放 `zbid_writeback_allowed`。
53. ZBid writeback request 必须 blocked。
54. `output/job/export` write request 必须 blocked。
55. formal generation request 必须 blocked。
56. review/apply request 必须 blocked。
57. `export_docx_request_triggered=true` 必须 blocked。
58. helper 不触发 `/export_docx`。
59. helper 不生成 DOCX / JSON / Markdown。
60. helper 不读取真实 payload、真实 DOCX 或真实正文生成 hash。
61. helper import 不得拉入主链、导出链或 DOCX 模块。

这些不变量确认的是 fake-only metadata helper 的阻断行为，不代表任何真实 DOCX export 或 formal writeback 能力已经存在。

## 6. Test Evidence from Step 131

Step 131 已运行并通过以下限定测试组合：

- `python -m pytest backend/tests/test_docx_isolation_guard.py -vv`
  - `21 passed in 0.05s`

- `python -m pytest backend/tests/test_docx_isolation_guard_contract_schema.py backend/tests/test_docx_isolation_guard.py -vv`
  - `40 passed in 0.07s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py backend/tests/test_human_approval_gate_contract_schema.py backend/tests/test_human_approval_gate.py backend/tests/test_diff_preview_contract_schema.py backend/tests/test_diff_preview.py backend/tests/test_rollback_plan_contract_schema.py backend/tests/test_rollback_plan.py backend/tests/test_formal_writeback_guard_contract_schema.py backend/tests/test_formal_writeback_guard.py backend/tests/test_source_hash_revalidation_guard_contract_schema.py backend/tests/test_source_hash_revalidation_guard.py backend/tests/test_review_apply_isolation_guard_contract_schema.py backend/tests/test_review_apply_isolation_guard.py backend/tests/test_docx_isolation_guard_contract_schema.py backend/tests/test_docx_isolation_guard.py -vv`
  - `353 passed in 0.39s`

- `python -m pytest backend/tests/test_docx_isolation_guard.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `24 passed in 0.74s`

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。该事实不得在本复盘中扩大解释为生产功能风险，也不得用来暗示 DOCX 导出或正式写回已经可用。

## 7. Boundary Against Formal Generation and Export Chains

Step 131 未接入以下链路：

- orchestrator。
- llm_client。
- provider。
- generation。
- export。
- DOCX export。
- review/apply。
- actions_bridge。
- ZBid writeback。
- `output/job/export`。

helper 不触发 `/export_docx`，不生成 DOCX 文件，不读取真实 DOCX，不读取真实正文，不读取真实 payload，不写 `output/job/export`，不调用模型、Ollama、API 或服务。

## 8. Remaining Blockers Before Any Actual DOCX Export or Writeback

未来进入 DOCX 导出或正式写回前仍缺少：

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
- ZBid writeback isolation guard。
- explicit user approval flow。
- no-write regression tests。
- formal writeback dry-run tests。
- actual writeback apply implementation。
- rollback execution verification。
- DOCX post-write isolation verification。
- ZBid post-write isolation verification。

这些 blockers 全部解除前，DOCX isolation helper 仍不得被解释为 DOCX export permission、formal writeback permission、review/apply permission 或 ZBid / export 准入。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 133：ZBid isolation guard contract design，docs-only。

Step 133 不得实现 ZBid isolation helper，不得触发 ZBid 写回，不得执行写回，不得读取或修改真实正文，不得写 `output/job/export`，不得进入 DOCX 导出。

## 10. Safety Conclusion

Step 131 仅完成 fake-only DOCX isolation guard metadata helper。当前系统仍处于 preview-only / no-write 阶段，不代表 DOCX 导出、正式写回、review/apply 或 ZBid 写回已实现。

Step 132 仅完成 Step 131 的 docs-only 实现复盘归档。本文档不开放 DOCX export，不开放 ZBid writeback，不开放 review/apply，不开放 formal writeback，不生成 DOCX / JSON / Markdown，不写 `output/job/export`。
