# ZDoc Real Ollama Preview Advisory - Human Approval Gate Fake Helper Stage Review

## 1. Scope

Step 108 仅为 Step 107 fake-only human approval gate helper 的实现复盘归档，目标是记录 helper 的能力边界、安全约束、测试结论、未实现事项和后续推进条件。

Step 107 新增的 helper 只构造 human approval metadata envelope。当前系统仍处于 preview-only / no-write 阶段，不代表审批 UI、审批持久化、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

本复盘不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不访问 `127.0.0.1:11434`，不写 `output/job/export`，不触发 `/generate`、`/export_docx` 或 `/review/apply`。

## 2. Files Added in Step 107

Step 107 新增文件：

- `backend/zhifei_autoplan/human_approval_gate.py`
- `backend/tests/test_human_approval_gate.py`

Step 107 未修改：

- 生产主链。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- DOCX / ZBid / export / review / generation 链路。

Step 107 未接入 orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge 或 ZBid。

## 3. Helper Capability Summary

`backend/zhifei_autoplan/human_approval_gate.py` 当前能力仅限于：

- 构造 human approval metadata dict。
- 固化 Step 105 / Step 106 approval contract 字段。
- 固化 approval status / decision / scope / mode 枚举。
- 固化 blocked_reasons。
- 固化 `formal_writeback_allowed=false`。
- 固化 `docx_export_allowed=false`。
- 固化 `zbid_writeback_allowed=false`。
- 固化 `output_write_allowed=false`。
- 接收调用方传入 `approved_at`、`approval_expires_at` 或空值。
- 基于输入字段确定性生成 `approval_id`，或使用调用方显式固定 `approval_id`。
- 校验 fake `approver_id_placeholder`，不允许真实个人身份字段。

helper 使用 Python 标准库实现，不读取文件，不写文件，不访问网络，不调用模型，不使用 `datetime.now()`、`time.time()`、`uuid.uuid4()` 或 `random` 生成非确定性 metadata。

## 4. Explicit Non-Capabilities

Step 107 helper 明确不具备以下能力：

- 不实现 human approval UI。
- 不实现审批按钮。
- 不实现审批持久化。
- 不记录真实个人身份。
- 不执行正式写回。
- 不触发 review/apply。
- 不执行 diff / rollback。
- 不接 DOCX 导出。
- 不接 ZBid 写回。
- 不调用模型。
- 不调用本地模型、外部模型、Ollama、API 或服务。
- 不读写 `output/job/export`。
- 不接 orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge 或 ZBid。
- 不把 approval 当 evidence。
- 不把 approval 当 formal writeback permission。
- 不把 approval 当 diff / rollback / formal guard 的替代条件。

`approval_status=approved_shadow_only` 仅表示 shadow-only metadata，不等于 `formal_writeback_allowed=true`。human approval 不得替代 evidence anchor、source hash revalidation、diff preview、rollback plan 或 formal writeback guard。

## 5. Safety Invariants Confirmed

Step 107 helper 和 tests 已确认以下安全约束：

1. `formal_writeback_allowed` 恒 false。
2. `docx_export_allowed` 恒 false。
3. `zbid_writeback_allowed` 恒 false。
4. `output_write_allowed` 恒 false。
5. `approval_status=approved_shadow_only` 不等于可写回。
6. missing `shadow_candidate_id` 必须 blocked。
7. missing `patch_id` 必须 blocked。
8. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
9. `patch_status=blocked` 或 `not_created` 必须 blocked。
10. `thinking_only_fallback` 必须 blocked。
11. missing evidence anchor 必须 blocked。
12. empty evidence refs 必须 blocked。
13. advisory / shadow candidate / patch preview 作为 evidence 均必须 blocked。
14. missing `source_section_hash` 必须 blocked。
15. `source_hash_revalidation_ready=false` 必须 blocked。
16. `diff_preview_ready=false` 必须 blocked。
17. `rollback_plan_ready=false` 必须 blocked。
18. `formal_writeback_guard_ready=false` 必须 blocked。
19. `approval_audit_required=true` 且 `approval_audit_ready=false` 必须 blocked。
20. `approver_id_placeholder` 不得存储真实姓名、邮箱、手机号、身份证号。
21. DOCX / ZBid / output / formal generation / review apply requests 必须 blocked。
22. helper import 不得拉入主链模块。

这些约束说明 helper 只是 fake-only approval metadata guard，不是 writeback guard，也不是正式审批系统。

## 6. Test Evidence from Step 107

Step 107 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_human_approval_gate.py -vv`
  - `20 passed in 0.05s`

- `python -m pytest backend/tests/test_human_approval_gate_contract_schema.py backend/tests/test_human_approval_gate.py -vv`
  - `40 passed in 0.05s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py backend/tests/test_human_approval_gate_contract_schema.py backend/tests/test_human_approval_gate.py -vv`
  - `104 passed in 0.11s`

- `python -m pytest backend/tests/test_human_approval_gate.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `23 passed in 0.78s`

full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。本复盘不得将该既有 full-suite 问题扩大解释为 Step 107 生产功能风险。

## 7. Boundary Against Formal Generation Chain

Step 107 未接入以下链路：

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

helper 不生成正式正文，不生成真实 candidate patch，不触发 `/generate`、`/export_docx` 或 `/review/apply`，不进入正式正文生成链，不接 DOCX 导出，不接 ZBid 正式写回。

## 8. Remaining Blockers Before Any Writeback

未来进入任何正式写回前仍缺少：

- real evidence anchor validation。
- real shadow generation implementation。
- real candidate patch generation。
- approval UI。
- approval persistence / audit storage。
- diff preview contract。
- diff preview fake helper。
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

即使未来审批 metadata 为 `approved_shadow_only`，仍必须同时满足 evidence、source hash revalidation、diff、rollback、formal writeback guard、review/apply isolation、DOCX isolation 和 ZBid isolation 等前置条件，且必须单独授权。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 109：diff preview contract design，docs-only。

Step 109 不得实现 diff preview helper，不得执行 diff，不得写回正文，不得触发 review/apply，不得进入正式生成链。

## 10. Safety Conclusion

Step 107 仅完成 fake-only human approval gate metadata helper。当前系统仍处于 preview-only / no-write 阶段，不代表审批 UI、审批持久化、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

human approval 不得作为 evidence，不得替代 evidence anchor，不得替代 source hash revalidation，不得替代 diff preview，不得替代 rollback plan，不得替代 formal writeback guard。当前阶段 `formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 必须继续恒为 false。
