# ZDoc Real Ollama Preview Advisory - Source Hash Revalidation Guard Fake Helper Stage Review

## 1. Scope

本文档是 Step 124 对 Step 123 fake-only source hash revalidation guard helper 的实现复盘归档。目标是记录 helper 的能力边界、安全约束、测试结论、未实现事项和后续推进条件。

Step 123 新增的 helper 只构造 source hash revalidation metadata envelope。它不读取真实正文，不计算真实正文 hash，不比较真实 source section 内容，不修改 source section，不触发 review/apply，不执行 formal writeback，不写 `output/job/export`，不生成 DOCX / JSON / Markdown，不接 ZBid 写回，不开放 DOCX export，也不开放 review/apply。

当前系统仍处于 preview-only / no-write 阶段。本文档不代表真实 hash 计算、正式写回、review/apply、DOCX / ZBid 隔离已实现。

## 2. Files added in Step 123

Step 123 新增：

- `backend/zhifei_autoplan/source_hash_revalidation_guard.py`
- `backend/tests/test_source_hash_revalidation_guard.py`

Step 123 未修改：

- 生产主链
- 既有 tests
- docs
- frontend
- `app.py`
- `output/job/export`
- DOCX / ZBid / export / review / generation 链路

## 3. Helper capability summary

helper 当前能力仅限于：

- 构造 source hash revalidation metadata `dict`。
- 固化 Step 121/122 source hash revalidation guard contract 字段。
- 固化 `source_hash_revalidation_status` / `source_version_revalidation_status` / `source_hash_guard_status` / `revalidation_decision` / `revalidation_mode` 枚举。
- 固化稳定的 `blocked_reasons`。
- 固化 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒 false。
- 接收调用方传入 `generated_at`。
- 生成确定性 `source_hash_guard_id`，或使用显式固定 `source_hash_guard_id`。
- 接收 `current_source_section_hash`、`current_source_section_version` 等 fake metadata 字段并保持阻断。

`generated_at` 由调用方显式传入，不使用非确定性时间。`source_hash_guard_id` 必须为确定性生成或显式固定值，不使用 UUID、random 或当前时间。

`current_source_section_hash`、`current_source_section_version` 只能由调用方显式传入。当前阶段 helper 不得由真实正文或真实文件读取、计算或推导这些字段。

## 4. Explicit non-capabilities

helper 明确不具备以下能力：

- 不读取真实正文。
- 不计算真实 hash。
- 不比较真实 source section 内容。
- 不修改 source section。
- 不触发 review/apply。
- 不执行 formal writeback。
- 不写 `output/job/export`。
- 不生成 DOCX / JSON / Markdown。
- 不接 ZBid 写回。
- 不开放 DOCX export。
- 不开放 review/apply。
- 不实现 DOCX / ZBid isolation guard。
- 不实现真实 source hash revalidation。
- 不调用本地模型、外部模型、Ollama、API 或服务。
- 不读写文件。
- 不接 `orchestrator`、`llm_client`、`provider`、`generation`、`export`、`review/apply`、`actions_bridge`、ZBid。
- 不把 hash revalidation 当 evidence。
- 不把 hash revalidation 当 formal writeback permission。
- 不把 hash revalidation 当 DOCX / ZBid / export 准入。
- 不把 hash revalidation 当 evidence / approval / diff / rollback / formal guard 的替代条件。

`source_hash_revalidation_status=matched`、`source_version_revalidation_status=matched`、`source_hash_match=true`、`source_version_match=true` 只表示 fake metadata 条件，不等于 `formal_writeback_allowed=true`。

## 5. Safety invariants confirmed

Step 123 的 helper 和限定测试确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. helper 只输出 `not_created`、`blocked`、`stale_source_hash` 或 `stale_source_version`。
7. helper 不输出 `source_hash_matched_shadow_only`。
8. matched source hash 不等于可写回。
9. matched source version 不等于可写回。
10. missing `shadow_candidate_id` 必须 blocked。
11. missing `patch_id` 必须 blocked。
12. missing `approval_id` 必须 blocked。
13. missing `diff_preview_id` 必须 blocked。
14. missing `rollback_plan_id` 必须 blocked。
15. missing `writeback_guard_id` 必须 blocked。
16. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
17. `patch_status=blocked` 或 `not_created` 必须 blocked。
18. `approval_status` 非 `approved_shadow_only` 必须 blocked。
19. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
20. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
21. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
22. `thinking_only_fallback` 必须 blocked。
23. missing evidence anchor 必须 blocked。
24. empty evidence refs 必须 blocked。
25. advisory / shadow candidate / patch preview / diff preview / rollback plan 作为 evidence 均必须 blocked。
26. `source_section_hash` 缺失必须 blocked。
27. `current_source_section_hash` 缺失必须 blocked。
28. `source_hash_revalidation_ready=false` 必须 blocked。
29. `source_hash_revalidation_status=missing`、`mismatched`、`stale_source_hash` 必须 blocked 或 `stale_source_hash`。
30. `source_hash_match=false` 必须 `stale_source_hash` 或 blocked。
31. `source_section_hash` 与 `current_source_section_hash` 不一致必须 `stale_source_hash` 或 blocked。
32. `source_section_version` 缺失必须 blocked。
33. `current_source_section_version` 缺失必须 blocked。
34. `source_version_revalidation_status=missing`、`mismatched`、`stale_source_version` 必须 blocked 或 `stale_source_version`。
35. `source_version_match=false` 必须 `stale_source_version` 或 blocked。
36. `source_section_version` 与 `current_source_section_version` 不一致必须 `stale_source_version` 或 blocked。
37. `writeback_candidate_hash` 缺失必须 blocked。
38. `source_snapshot_hash` 缺失必须 blocked。
39. `before_text_hash` 缺失必须 blocked。
40. `after_text_preview_hash` 缺失必须 blocked。
41. `patch_operations_preview_hash` 缺失必须 blocked。
42. `diff_preview_hash` 缺失必须 blocked。
43. `rollback_plan_hash` 缺失必须 blocked。
44. human approval 缺失必须 blocked。
45. `diff_preview_ready=false` 必须 blocked。
46. `rollback_plan_ready=false` 必须 blocked。
47. `formal_writeback_guard_ready=false` 必须 blocked。
48. `review_apply_isolation_ready=false` 必须 blocked。
49. DOCX isolation not ready 不得开放 `docx_export_allowed`。
50. ZBid isolation not ready 不得开放 `zbid_writeback_allowed`。
51. DOCX / ZBid / output / formal generation / review apply requests 必须 blocked。
52. helper 不读取真实正文计算 hash。
53. helper 不比较真实 source section 内容。
54. helper import 不得拉入主链模块。

source hash revalidation 不得作为 evidence，不得替代 evidence anchor、human approval、diff preview、rollback plan 或 formal writeback guard，也不得作为 DOCX / ZBid / export 准入。

## 6. Test evidence from Step 123

Step 123 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_source_hash_revalidation_guard.py -vv`
  - `22 passed in 0.06s`

- `python -m pytest backend/tests/test_source_hash_revalidation_guard_contract_schema.py backend/tests/test_source_hash_revalidation_guard.py -vv`
  - `45 passed in 0.07s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py backend/tests/test_human_approval_gate_contract_schema.py backend/tests/test_human_approval_gate.py backend/tests/test_diff_preview_contract_schema.py backend/tests/test_diff_preview.py backend/tests/test_rollback_plan_contract_schema.py backend/tests/test_rollback_plan.py backend/tests/test_formal_writeback_guard_contract_schema.py backend/tests/test_formal_writeback_guard.py backend/tests/test_source_hash_revalidation_guard_contract_schema.py backend/tests/test_source_hash_revalidation_guard.py -vv`
  - `273 passed in 0.29s`

- `python -m pytest backend/tests/test_source_hash_revalidation_guard.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `25 passed in 1.65s`

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题；本复盘不得将该既有 full-suite 问题扩大解释为生产功能风险。

Step 124 为 docs-only stage review，不运行 pytest。

## 7. Boundary against formal generation chain

Step 123 未接入以下链路：

- `orchestrator`
- `llm_client`
- `provider`
- `generation`
- `export`
- `review/apply`
- `actions_bridge`
- DOCX export
- ZBid writeback
- `output/job/export`

helper 只返回 fake-only source hash revalidation metadata envelope，不执行真实 source hash revalidation、真实正文读取、真实正文 hash 计算、真实 source section 比较、写回、导出、review/apply、模型调用、网络调用或文件读写。

## 8. Remaining blockers before any actual writeback

未来进入正式写回前仍缺少：

- real evidence anchor validation
- real shadow generation implementation
- real candidate patch generation
- approval UI
- approval persistence / audit storage
- real diff implementation
- real rollback implementation
- real source hash computation
- real source section comparison
- review/apply isolation guard
- DOCX export isolation guard
- ZBid writeback isolation guard
- explicit user approval flow
- no-write regression tests
- formal writeback dry-run tests
- actual writeback apply implementation
- rollback execution verification
- DOCX/ZBid post-write isolation verification

这些能力均未由 Step 123 或 Step 124 实现。

## 9. Recommended next step

建议下一步为：

ZDoc Step 125: review/apply isolation guard contract design, docs-only.

Step 125 不得实现 review/apply isolation helper，不得触发 review/apply，不得执行写回，不得读取或修改真实正文，不得写 `output/job/export`，不得进入 DOCX 或 ZBid。

## 10. Safety conclusion

Step 123 仅完成 fake-only source hash revalidation guard metadata helper。Step 124 仅完成该 helper 的 docs-only stage review。

当前系统仍处于 preview-only / no-write 阶段。本文档不代表真实 hash 计算、正式写回、review/apply、DOCX 导出或 ZBid 写回已实现。
