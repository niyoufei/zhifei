# ZDoc Real Ollama Preview Advisory - Diff Preview Fake Helper Stage Review

## 1. Scope

Step 112 仅为 Step 111 fake-only diff preview helper 的实现复盘归档，目标是记录 fake-only diff preview helper 的能力边界、安全约束、测试结论、未实现事项和后续推进条件。

Step 111 新增的 helper 只构造 diff preview metadata envelope。当前系统仍处于 preview-only / no-write 阶段，不代表真实 diff、review/apply、rollback、formal writeback、DOCX 导出或 ZBid 写回已经实现。

## 2. Files Added in Step 111

Step 111 新增文件：

- `backend/zhifei_autoplan/diff_preview.py`
- `backend/tests/test_diff_preview.py`

Step 111 未修改：

- 生产主链。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- DOCX / ZBid / export / review / generation 链路。

## 3. Helper Capability Summary

Step 111 helper 当前能力仅限于：

- 构造 diff preview metadata dict。
- 固化 Step 109 / Step 110 diff preview contract 字段。
- 固化 `diff_preview_status` / `diff_scope` / `diff_format` / `diff_operation_type` 枚举。
- 固化 `blocked_reasons`。
- 固化 `formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒 false。
- 接收调用方传入 `generated_at`。
- 生成确定性 `diff_preview_id` 或使用显式固定 `diff_preview_id`。
- 接收 fake `diff_summary_preview` / `diff_operations_preview` 作为隔离预览字段。

helper 不使用非确定性时间。`generated_at` 由调用方显式传入。`diff_preview_id` 基于输入字段确定性生成，或由调用方显式固定；不得使用 `uuid`、`random` 或当前时间。

`diff_summary_preview` 和 `diff_operations_preview` 仅为 fake preview / metadata preview，不等于真实 diff，不等于可写回差异，不等于正式正文修改。

## 4. Explicit Non-Capabilities

Step 111 helper 明确不具备以下能力：

- 不执行真实 diff。
- 不比较真实正文。
- 不生成可写回差异。
- 不读取 source section 并生成正式差异。
- 不触发 review/apply。
- 不写回 source section。
- 不写 `output/job/export`。
- 不接 DOCX 导出。
- 不接 ZBid 写回。
- 不实现 rollback plan。
- 不实现 formal writeback guard。
- 不调用模型。
- 不调用本地模型、外部模型、Ollama、API 或服务。
- 不接 orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge、ZBid。
- 不把 diff preview 当 evidence。
- 不把 diff preview 当 formal writeback permission。
- 不把 human approval 当作 diff preview 的替代条件。
- 不把 diff preview 当 rollback plan 或 formal writeback guard 的替代条件。

本文档不代表真实 diff、review/apply、rollback、formal writeback、DOCX/ZBid 隔离已实现。

## 5. Safety Invariants Confirmed

Step 111 已确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `docx_export_allowed` 恒 false。
3. `zbid_writeback_allowed` 恒 false。
4. `output_write_allowed` 恒 false。
5. helper 只输出 `not_created`、`blocked` 或 `stale_source_hash`。
6. helper 不输出 `ready_for_human_review` 或 `approved_diff_shadow_only`。
7. missing `shadow_candidate_id` 必须 blocked。
8. missing `patch_id` 必须 blocked。
9. missing `approval_id` 必须 blocked。
10. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
11. `patch_status=blocked` 或 `not_created` 必须 blocked。
12. `approval_status` 非 `approved_shadow_only` 必须 blocked。
13. `thinking_only_fallback` 必须 blocked。
14. missing evidence anchor 必须 blocked。
15. empty evidence refs 必须 blocked。
16. advisory / shadow candidate / patch preview / diff preview 作为 evidence 均必须 blocked。
17. missing `source_section_hash` 必须 blocked。
18. `source_hash_revalidation_ready=false` 必须 blocked。
19. `source_section_hash_match=false` 必须 `stale_source_hash` 或 blocked。
20. `diff_base_hash_match=false` 必须 `stale_source_hash` 或 blocked。
21. `before_text_hash` 缺失必须 blocked。
22. `after_text_preview_hash` 缺失必须 blocked。
23. `patch_operations_preview_hash` 缺失必须 blocked。
24. human approval 缺失必须 blocked。
25. `rollback_plan_ready=false` 必须 blocked。
26. `formal_writeback_guard_ready=false` 必须 blocked。
27. DOCX / ZBid / output / formal generation / review apply requests 必须 blocked。
28. `diff_summary_preview` / `diff_operations_preview` 不得作为 evidence。
29. helper import 不得拉入主链模块。

即使未来存在 `approved_diff_shadow_only` 状态，它也不得等同于 `formal_writeback_allowed=true`。diff preview 不得替代 evidence anchor、human approval、rollback plan 或 formal writeback guard。

## 6. Test Evidence From Step 111

Step 111 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_diff_preview.py -vv`
  - `21 passed in 0.04s`

- `python -m pytest backend/tests/test_diff_preview_contract_schema.py backend/tests/test_diff_preview.py -vv`
  - `41 passed in 0.05s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py backend/tests/test_human_approval_gate_contract_schema.py backend/tests/test_human_approval_gate.py backend/tests/test_diff_preview_contract_schema.py backend/tests/test_diff_preview.py -vv`
  - `145 passed in 0.14s`

- `python -m pytest backend/tests/test_diff_preview.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `24 passed in 0.78s`

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题；不得在本复盘中扩大解释为生产功能风险。

## 7. Boundary Against Formal Generation Chain

Step 111 未接入以下链路：

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

helper 不触发 `/generate`、`/export_docx` 或 `/review/apply`。helper 不启动服务，不运行 Ollama，不访问 `127.0.0.1:11434`，不调用外部模型或 API。

## 8. Remaining Blockers Before Any Writeback

未来进入任何正式写回之前仍缺少：

- real evidence anchor validation。
- real shadow generation implementation。
- real candidate patch generation。
- approval UI。
- approval persistence / audit storage。
- real diff implementation。
- rollback plan contract。
- rollback plan fake helper。
- formal writeback guard。
- source section hash revalidation guard。
- review/apply isolation guard。
- DOCX export isolation guard。
- ZBid writeback isolation guard。
- explicit user approval flow。
- no-write regression tests。
- formal writeback dry-run tests。

这些 blocker 未完成前，不得写回正式正文，不得触发 review/apply，不得进入 DOCX / JSON / Markdown 正式导出，不得进入 ZBid 正式写回。

## 9. Recommended Next Step

下一步建议为：

ZDoc Step 113：rollback plan contract design，docs-only。

Step 113 不得实现 rollback helper，不得执行 rollback，不得写回正文，不得触发 review/apply，不得进入正式生成链。

## 10. Safety Conclusion

Step 111 仅完成 fake-only diff preview metadata helper。当前系统仍处于 preview-only / no-write 阶段，不代表真实 diff、review/apply、rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

diff preview 仅是未来候选修改前后差异的隔离 metadata envelope，不等于正式正文修改，不得作为 evidence，不得作为 formal writeback permission，也不得替代 evidence anchor、human approval、rollback plan 或 formal writeback guard。

当前阶段 `formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须继续恒为 false。
