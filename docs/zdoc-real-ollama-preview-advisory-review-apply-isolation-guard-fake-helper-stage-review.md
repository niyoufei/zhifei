# ZDoc Real Ollama Preview Advisory - Review/Apply Isolation Guard Fake Helper Stage Review

## 1. Scope

Step 128 仅为 Step 127 fake-only review/apply isolation guard helper 的实现复盘归档。本文档归档 `backend/zhifei_autoplan/review_apply_isolation_guard.py` 与 `backend/tests/test_review_apply_isolation_guard.py` 的能力边界、安全约束、测试结论、未实现事项和后续推进条件。

Step 127 新增的 helper 只构造 review/apply isolation metadata envelope。它用于把 Step 125/126 的 review/apply isolation guard contract 固化为隔离 metadata dict，供后续设计和 fake-only 验证参考。

当前系统仍处于 preview-only / no-write 阶段。Step 128 不实现新 helper，不修改生产代码，不修改测试，不运行 pytest，不触发 `/review/apply`，不执行正式写回，不读取或修改真实正文，不写 `output/job/export`，不接 DOCX 或 ZBid。

## 2. Files Added in Step 127

Step 127 新增文件：

- `backend/zhifei_autoplan/review_apply_isolation_guard.py`
- `backend/tests/test_review_apply_isolation_guard.py`

Step 127 未修改以下范围：

- 生产主链。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- DOCX / ZBid / export / review / generation 链路。

Step 128 仅新增本文档，不改变 Step 127 的 helper 或测试实现。

## 3. Helper Capability Summary

Step 127 helper 当前能力仅限于：

- 构造 review/apply isolation metadata dict。
- 固化 Step 125/126 review/apply isolation guard contract 字段。
- 固化 `review_apply_isolation_status` / `review_apply_decision` / `review_apply_scope` / `review_apply_mode` / `review_apply_target_type` / `review_apply_request_status` 枚举。
- 固化 `blocked_reasons` 稳定字符串。
- 固化 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒 false。
- 接收调用方传入 `generated_at`。
- 生成确定性 `review_apply_guard_id`，或使用调用方显式传入的固定 `review_apply_guard_id`。
- 接收 `review_apply_route`、`review_apply_payload_hash` 等 fake metadata 字段并保持阻断。

helper 的输出是 metadata envelope，不是 review/apply 动作、写回动作、导出动作、真实路由调用或真实 payload 读取结果。

## 4. Explicit Non-Capabilities

Step 127 helper 明确不具备以下能力：

- 不触发 `/review/apply`。
- 不执行 review/apply。
- 不执行真实 review/apply isolation。
- 不执行正式写回。
- 不读取真实正文。
- 不修改 source section。
- 不写 `output/job/export`。
- 不生成 DOCX / JSON / Markdown。
- 不接 ZBid 写回。
- 不开放 DOCX export。
- 不开放 review/apply。
- 不读取真实 payload。
- 不实现 DOCX / ZBid isolation guard。
- 不调用模型。
- 不调用本地模型、外部模型、Ollama、API 或服务。
- 不读写文件。
- 不接 orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge 或 ZBid。
- 不把 review/apply isolation 当 evidence。
- 不把 review/apply isolation 当 writeback permission。
- 不把 review/apply isolation 当 DOCX / ZBid / export 准入。
- 不把 review/apply isolation 当 evidence / approval / diff / rollback / formal guard / source hash revalidation 的替代条件。

`generated_at` 由调用方显式传入，不使用非确定性时间。`review_apply_guard_id` 必须为确定性生成或显式固定值，不使用 UUID、random 或当前时间。`review_apply_payload_hash` 只能由调用方显式传入，当前阶段不得读取真实 payload 生成。`review_apply_route` 仅作为 fake metadata 字段，不触发真实路由。

`review_apply_isolation_status=isolated_shadow_only` 不等于 `review_apply_allowed=true`。`review_apply_decision=isolate_shadow_only` 不等于 `review_apply_allowed=true`。

review/apply isolation 不得作为 evidence，不得替代 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard 或 source hash revalidation，也不得作为 DOCX / ZBid / export 准入。

## 5. Safety Invariants Confirmed

Step 127 helper 与测试确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. helper 只输出 `not_created`、`blocked`、`stale_source_hash` 或 `stale_source_version`。
7. helper 不输出 `isolated_shadow_only` 或 `ready_for_future_manual_review`。
8. `isolated_shadow_only` 不等于可 review/apply。
9. `isolate_shadow_only` 不等于可 review/apply。
10. missing `shadow_candidate_id` 必须 blocked。
11. missing `patch_id` 必须 blocked。
12. missing `approval_id` 必须 blocked。
13. missing `diff_preview_id` 必须 blocked。
14. missing `rollback_plan_id` 必须 blocked。
15. missing `writeback_guard_id` 必须 blocked。
16. missing `source_hash_guard_id` 必须 blocked。
17. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
18. `patch_status=blocked` 或 `not_created` 必须 blocked。
19. `approval_status` 非 `approved_shadow_only` 必须 blocked。
20. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
21. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
22. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
23. `source_hash_guard_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
24. `thinking_only_fallback` 必须 blocked。
25. missing evidence anchor 必须 blocked。
26. empty evidence refs 必须 blocked。
27. advisory / shadow candidate / patch preview / diff preview / rollback plan 作为 evidence 均必须 blocked。
28. `source_hash_match=false` 必须 `stale_source_hash` 或 blocked。
29. `source_version_match=false` 必须 `stale_source_version` 或 blocked。
30. `current_source_section_hash` 缺失必须 blocked。
31. `current_source_section_version` 缺失必须 blocked。
32. `writeback_candidate_hash` 缺失必须 blocked。
33. `source_snapshot_hash` 缺失必须 blocked。
34. `before_text_hash` 缺失必须 blocked。
35. `after_text_preview_hash` 缺失必须 blocked。
36. `patch_operations_preview_hash` 缺失必须 blocked。
37. `diff_preview_hash` 缺失必须 blocked。
38. `rollback_plan_hash` 缺失必须 blocked。
39. human approval 缺失必须 blocked。
40. `diff_preview_ready=false` 必须 blocked。
41. `rollback_plan_ready=false` 必须 blocked。
42. `formal_writeback_guard_ready=false` 必须 blocked。
43. `source_hash_revalidation_ready=false` 必须 blocked。
44. `review_apply_requested=true` 必须 blocked。
45. `review_apply_route=/review/apply` 必须 blocked。
46. `review_apply_payload_hash` 缺失必须 blocked。
47. DOCX isolation not ready 不得开放 `docx_export_allowed`。
48. ZBid isolation not ready 不得开放 `zbid_writeback_allowed`。
49. DOCX / ZBid / output / formal generation / review apply requests 必须 blocked。
50. helper 不触发 `/review/apply`。
51. helper 不读取真实 payload 生成 hash。
52. helper 不读取或修改真实正文。
53. helper import 不得拉入主链模块。

以上不变量只证明 fake-only metadata helper 的隔离约束，不代表任何正式写回、review/apply、DOCX 导出或 ZBid 写回能力已经实现。

## 6. Test Evidence from Step 127

Step 127 已运行并通过以下限定测试组合：

- `python -m pytest backend/tests/test_review_apply_isolation_guard.py -vv`
  - `21 passed in 0.05s`

- `python -m pytest backend/tests/test_review_apply_isolation_guard_contract_schema.py backend/tests/test_review_apply_isolation_guard.py -vv`
  - `40 passed in 0.07s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py backend/tests/test_human_approval_gate_contract_schema.py backend/tests/test_human_approval_gate.py backend/tests/test_diff_preview_contract_schema.py backend/tests/test_diff_preview.py backend/tests/test_rollback_plan_contract_schema.py backend/tests/test_rollback_plan.py backend/tests/test_formal_writeback_guard_contract_schema.py backend/tests/test_formal_writeback_guard.py backend/tests/test_source_hash_revalidation_guard_contract_schema.py backend/tests/test_source_hash_revalidation_guard.py backend/tests/test_review_apply_isolation_guard_contract_schema.py backend/tests/test_review_apply_isolation_guard.py -vv`
  - `313 passed in 0.34s`

- `python -m pytest backend/tests/test_review_apply_isolation_guard.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `24 passed in 0.77s`

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题；该事实不得在本复盘中扩大解释为生产功能风险。

Step 128 按要求不运行 pytest。

## 7. Boundary Against Formal Generation Chain

Step 127 未接入以下链路：

- orchestrator。
- llm_client。
- provider。
- generation。
- export。
- review/apply。
- actions_bridge。
- DOCX export。
- ZBid writeback。
- `output/job/export`。

Step 127 helper 仅位于 isolated fake-only metadata helper 层，不进入正式正文生成链，不触发 `/review/apply`，不执行 source section 修改，不执行 formal writeback，不生成 DOCX / JSON / Markdown，不写任何导出目录。

## 8. Remaining Blockers Before Any Actual Writeback

未来进入任何实际写回前仍缺少：

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
- DOCX export isolation guard。
- ZBid writeback isolation guard。
- explicit user approval flow。
- no-write regression tests。
- formal writeback dry-run tests。
- actual writeback apply implementation。
- rollback execution verification。
- DOCX / ZBid post-write isolation verification。

这些 blocker 未完成前，不得把 review/apply isolation metadata 解释为可 review/apply、可写回、可导出或可 ZBid 写回。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 129：DOCX isolation guard contract design，docs-only。

Step 129 不得实现 DOCX isolation helper，不得触发 `/export_docx`，不得生成 DOCX，不得执行写回，不得读取或修改真实正文，不得写 `output/job/export`，不得进入 ZBid。

## 10. Safety Conclusion

Step 127 仅完成 fake-only review/apply isolation guard metadata helper。当前系统仍处于 preview-only / no-write 阶段，不代表 review/apply 执行、正式写回、DOCX 导出或 ZBid 写回已实现。

Step 128 仅完成该 fake-only helper 的 docs-only stage review，不代表 review/apply 执行、正式写回、DOCX / ZBid 隔离已实现。当前阶段 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须继续恒为 false。
