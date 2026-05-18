# ZDoc Real Ollama Preview Advisory - Rollback Plan Fake Helper Stage Review

## 1. Scope

Step 116 仅为 Step 115 fake-only rollback plan helper 的实现复盘归档，目标是记录 helper 的能力边界、安全约束、限定测试结论、未实现事项和后续推进条件。

Step 115 新增的 helper 只构造 rollback plan metadata envelope。它服务于 preview-only / no-write 阶段，用于把 Step 113 / 114 的 rollback plan contract 固化为隔离 metadata dict，不代表真实 rollback、review/apply、formal writeback、DOCX 导出或 ZBid 写回已经实现。

## 2. Files Added in Step 115

Step 115 新增文件：

- `backend/zhifei_autoplan/rollback_plan.py`
- `backend/tests/test_rollback_plan.py`

Step 115 未修改以下范围：

- 未修改生产主链。
- 未修改既有 tests。
- 未修改 docs。
- 未修改 frontend。
- 未修改 `app.py`。
- 未写 `output/job/export`。
- 未接 DOCX / ZBid / export / review / generation 链路。

## 3. Helper Capability Summary

Step 115 helper 当前能力仅限于：

- 构造 rollback plan metadata dict。
- 固化 Step 113 / 114 rollback plan contract 字段。
- 固化 `rollback_plan_status`、`rollback_scope`、`rollback_strategy`、`rollback_operation_type`、`rollback_target_type` 枚举。
- 固化稳定的 `blocked_reasons`。
- 固化 `formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒为 false。
- 接收调用方显式传入的 `generated_at`。
- 基于输入字段确定性生成 `rollback_plan_id`，或使用调用方显式固定的 `rollback_plan_id`。
- 接收 fake `rollback_summary_preview` / `rollback_operations_preview` 作为隔离预览字段。

`rollback_summary_preview` 和 `rollback_operations_preview` 仅为 fake preview / metadata preview，不等于真实 rollback plan，不等于可执行 rollback operations，也不代表任何 source section 已被恢复或修改。

## 4. Explicit Non-capabilities

Step 115 helper 明确不具备以下能力：

- 不执行真实 rollback。
- 不恢复正文。
- 不修改 source section。
- 不生成可执行 rollback operations。
- 不触发 review/apply。
- 不执行正式写回。
- 不写 `output/job/export`。
- 不接 DOCX 导出。
- 不接 ZBid 写回。
- 不实现 formal writeback guard。
- 不调用本地模型。
- 不调用外部模型。
- 不调用 Ollama。
- 不调用 API 或服务。
- 不接 orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge 或 ZBid。
- 不把 rollback plan 当 evidence。
- 不把 rollback plan 当 formal writeback permission。
- 不把 rollback plan 当 diff preview、human approval、evidence anchor、source hash revalidation 或 formal writeback guard 的替代条件。

`generated_at` 由调用方显式传入，不使用非确定性时间。`rollback_plan_id` 必须为确定性生成或显式固定值，不使用 uuid、random 或当前时间。

## 5. Safety Invariants Confirmed

Step 115 helper 和测试确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `docx_export_allowed` 恒 false。
3. `zbid_writeback_allowed` 恒 false。
4. `output_write_allowed` 恒 false。
5. helper 只输出 `not_created`、`blocked` 或 `stale_source_hash`。
6. helper 不输出 `ready_for_human_review` 或 `approved_rollback_shadow_only`。
7. missing `shadow_candidate_id` 必须 blocked。
8. missing `patch_id` 必须 blocked。
9. missing `approval_id` 必须 blocked。
10. missing `diff_preview_id` 必须 blocked。
11. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
12. `patch_status=blocked` 或 `not_created` 必须 blocked。
13. `approval_status` 非 `approved_shadow_only` 必须 blocked。
14. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
15. `thinking_only_fallback` 必须 blocked。
16. missing evidence anchor 必须 blocked。
17. empty evidence refs 必须 blocked。
18. advisory / shadow candidate / patch preview / diff preview / rollback plan 作为 evidence 均必须 blocked。
19. missing `source_section_hash` 必须 blocked。
20. `source_hash_revalidation_ready=false` 必须 blocked。
21. `source_section_hash_match=false` 必须 `stale_source_hash` 或 blocked。
22. `rollback_base_hash_match=false` 必须 `stale_source_hash` 或 blocked。
23. `source_snapshot_hash` 缺失必须 blocked。
24. `before_text_hash` 缺失必须 blocked。
25. `after_text_preview_hash` 缺失必须 blocked。
26. `patch_operations_preview_hash` 缺失必须 blocked。
27. `diff_preview_hash` 缺失必须 blocked。
28. human approval 缺失必须 blocked。
29. `diff_preview_ready=false` 必须 blocked。
30. `formal_writeback_guard_ready=false` 必须 blocked。
31. DOCX / ZBid / output / formal generation / review apply requests 必须 blocked。
32. `rollback_summary_preview` / `rollback_operations_preview` 不得作为 evidence。
33. helper import 不得拉入主链模块。

以上不变量不表示写回链已经具备。它们只证明当前 fake-only metadata helper 在隔离阶段保持 no-write 边界。

## 6. Test Evidence from Step 115

Step 115 已运行并通过以下限定测试组合：

- `python -m pytest backend/tests/test_rollback_plan.py -vv`
  - `21 passed in 0.05s`

- `python -m pytest backend/tests/test_rollback_plan_contract_schema.py backend/tests/test_rollback_plan.py -vv`
  - `41 passed in 0.06s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py backend/tests/test_human_approval_gate_contract_schema.py backend/tests/test_human_approval_gate.py backend/tests/test_diff_preview_contract_schema.py backend/tests/test_diff_preview.py backend/tests/test_rollback_plan_contract_schema.py backend/tests/test_rollback_plan.py -vv`
  - `186 passed in 0.19s`

- `python -m pytest backend/tests/test_rollback_plan.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `24 passed in 0.83s`

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。本复盘不得将该既有 full-suite 限制扩大解释为 Step 115 的生产功能风险。

## 7. Boundary Against Formal Generation Chain

Step 115 未接入以下链路：

- orchestrator
- llm_client
- provider
- generation
- export
- review/apply
- actions_bridge
- DOCX export
- ZBid writeback
- `output/job/export`

rollback plan metadata 不得被 review/apply、export、DOCX 或 ZBid 直接消费。rollback plan metadata 也不得进入正式正文生成链，不能直接触发 source section 修改、正式文档导出或 ZBid 正式写回。

## 8. Remaining Blockers Before Any Writeback

未来进入任何正式写回前仍缺少：

- real evidence anchor validation。
- real shadow generation implementation。
- real candidate patch generation。
- approval UI。
- approval persistence / audit storage。
- real diff implementation。
- real rollback implementation。
- formal writeback guard。
- source section hash revalidation guard。
- review/apply isolation guard。
- DOCX export isolation guard。
- ZBid writeback isolation guard。
- explicit user approval flow。
- no-write regression tests。
- formal writeback dry-run tests。

任何单一 helper、approval、diff preview 或 rollback plan 都不得独立打开正式写回能力。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 117：formal writeback guard contract design，docs-only。

Step 117 不得实现 formal writeback helper，不得执行写回，不得触发 review/apply，不得写 `output/job/export`，不得进入 DOCX / ZBid。

## 10. Safety Conclusion

Step 115 仅完成 fake-only rollback plan metadata helper。当前系统仍处于 preview-only / no-write 阶段。

本文档仅完成 Step 116 的实现复盘归档，不代表真实 rollback、review/apply、formal writeback、DOCX 导出或 ZBid 写回已实现。`formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 在当前阶段必须继续保持 false。
