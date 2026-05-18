# ZDoc Real Ollama Preview Advisory - Shadow Candidate Patch Fake Helper Stage Review

## 1. Scope

Step 104 仅为 Step 103 fake-only shadow candidate patch helper 的实现复盘归档，目标是记录实现边界、安全约束、测试结论、未实现事项和后续推进条件。

Step 103 新增的 helper 只构造 shadow candidate patch metadata envelope。该 helper 不是真实 shadow generation implementation，不是真实 candidate patch implementation，不生成真实 candidate patch，不生成真实正文修改内容，不生成真实 patch operations，不读取章节正文并生成改写结果，不进入正式正文生成链。

当前系统仍处于 preview-only / no-write 阶段。本文档不代表真实 candidate patch、human approval、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

## 2. Files Added in Step 103

Step 103 新增文件：

- `backend/zhifei_autoplan/shadow_candidate_patch.py`
- `backend/tests/test_shadow_candidate_patch.py`

Step 103 未修改：

- 生产主链。
- 既有 tests。
- docs。
- frontend。
- `app.py`。
- `output/job/export`。
- orchestrator / llm_client / provider / generation / export / review / actions_bridge / ZBid 链路。
- DOCX / JSON / Markdown 正式导出链路。

## 3. Helper Capability Summary

`backend/zhifei_autoplan/shadow_candidate_patch.py` 当前能力仅限于：

- 构造 shadow candidate patch dict。
- 固化 Step 101 / Step 102 patch contract 字段。
- 固化 patch status / kind / format / operation / evidence binding 枚举。
- 固化 blocked_reasons。
- 固化 `formal_writeback_allowed=false`。
- 固化 `docx_export_allowed=false`。
- 固化 `zbid_writeback_allowed=false`。
- 固化 `output_write_allowed=false`。
- 接收调用方显式传入的 `generated_at`。
- 基于输入字段使用确定性 hash 生成 `patch_id`。
- 接收 fake `patch_operations_preview` / `after_text_preview` 作为隔离预览字段。
- 返回 JSON-friendly dict metadata，便于后续 fake-only 测试或审计。

该 helper 使用 Python 标准库实现，不访问网络，不读写文件，不调用模型，不启动服务。

## 4. Explicit Non-Capabilities

Step 103 helper 明确不具备以下能力：

- 不生成真实 candidate patch。
- 不生成真实正文修改。
- 不生成真实 patch operations。
- 不调用本地模型、外部模型、Ollama、API 或服务。
- 不读取 source section 并生成改写。
- 不写回 source section。
- 不写 `output/job/export`。
- 不接 DOCX 导出。
- 不接 JSON / Markdown 正式导出。
- 不接 ZBid 写回。
- 不实现 human approval UI。
- 不执行 diff / rollback。
- 不触发 review/apply。
- 不进入 formal writeback。
- 不把 advisory 当 evidence。
- 不把 shadow candidate envelope 当 evidence。
- 不把 shadow candidate patch 当 evidence。
- 不把 patch preview 当 evidence。
- 不把 patch preview 当正式正文。
- 不把 `patch_operations_preview` 当作实际 patch operations。
- 不把 `after_text_preview` 当作 source section 新正文。

## 5. Safety Invariants Confirmed

Step 103 helper 与 deterministic tests 已确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `docx_export_allowed` 恒 false。
3. `zbid_writeback_allowed` 恒 false。
4. `output_write_allowed` 恒 false。
5. missing `shadow_candidate_id` 必须 blocked。
6. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
7. `thinking_only_fallback` 必须 blocked。
8. missing evidence anchor 必须 blocked。
9. empty evidence refs 必须 blocked。
10. advisory 作为 evidence 必须 blocked。
11. shadow candidate / shadow candidate envelope 作为 evidence 必须 blocked。
12. patch preview 作为 evidence 必须 blocked。
13. missing `source_section_hash` 必须 blocked。
14. `source_section_hash_match=false` 必须 blocked。
15. missing `before_text_hash` 必须 blocked。
16. missing human approval 必须 blocked。
17. missing diff preview 必须 blocked。
18. missing rollback plan 必须 blocked。
19. DOCX export request 必须 blocked。
20. ZBid writeback request 必须 blocked。
21. output / job / export write request 必须 blocked。
22. formal generation request 必须 blocked。
23. review/apply request 必须 blocked。
24. `patch_operations_preview` / `after_text_preview` 不得作为 evidence。
25. helper import 不得拉入 orchestrator、llm_client、provider、generation、export、review、actions_bridge、ZBid 等主链模块。

这些不变量只证明 fake-only metadata helper 的 fail-closed 行为，不代表真实 candidate patch 或正式写回能力已经存在。

## 6. Test Evidence from Step 103

Step 103 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_shadow_candidate_patch.py -vv`
  - `19 passed in 0.04s`

- `python -m pytest backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py -vv`
  - `37 passed in 0.05s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py -vv`
  - `64 passed in 0.08s`

- `python -m pytest backend/tests/test_shadow_candidate_patch.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `22 passed in 0.79s`

Full backend tests 未运行，原因是 Step 98B 已确认存在既有 collection/order import-isolation 问题。该情况不得在本复盘中扩大解释为生产功能风险，也不得为了 full-suite 既有问题修改生产代码或既有 tests。

## 7. Boundary Against Formal Generation Chain

Step 103 未接入以下链路：

- orchestrator。
- llm_client。
- provider。
- generation。
- export。
- review/apply。
- actions_bridge。
- DOCX export。
- JSON / Markdown 正式导出。
- ZBid writeback。
- `output/job/export`。

Step 103 helper 不被正式生成链、导出链、review/apply 链或 ZBid 写回链直接消费。patch preview 仍是隔离 metadata，不是正式正文修改，不得写回 source section，不得进入 DOCX / JSON / Markdown 导出，不得进入 ZBid 正式写回。

## 8. Remaining Blockers Before Any Writeback

未来进入任何正式写回前仍缺少：

- real evidence anchor validation。
- real shadow generation implementation。
- human approval gate。
- approval persistence / audit record。
- diff preview contract。
- diff preview fake helper。
- rollback plan contract。
- rollback plan fake helper。
- formal writeback guard。
- source section hash revalidation。
- DOCX export isolation guard。
- ZBid writeback isolation guard。
- explicit user approval。
- no-write regression tests。
- formal writeback dry-run tests。
- review/apply isolation tests。
- output / job / export filesystem no-write regression tests。

在上述能力完成并单独授权前，不得把 patch metadata helper 解释为真实 candidate patch 能力，也不得进入正式正文生成链、DOCX 导出链或 ZBid 写回链。

## 9. Recommended Next Step

下一步建议为：ZDoc Step 105：human approval gate contract design，docs-only。

Step 105 也不得实现 human approval UI，不得写回正文，不得触发 review/apply，不得进入正式生成链，不得进入 DOCX 导出，不得接 ZBid 正式写回。

## 10. Safety Conclusion

Step 103 仅完成 fake-only shadow candidate patch metadata helper。当前系统仍处于 preview-only / no-write 阶段，不代表真实 candidate patch、human approval、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

`generated_at` 由调用方显式传入，不使用非确定性时间。`patch_id` 基于输入字段确定性生成，不使用 uuid、random 或当前时间。当前阶段 `formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒为 false。

thinking_only_fallback 仍不得作为正文能力。model-generated advisory 仍不得作为 evidence。shadow candidate envelope 仍不得作为 evidence。shadow candidate patch 仍不得作为 evidence。patch preview 仍不得作为正式正文修改，不得写回 source section，不得进入 DOCX / JSON / Markdown 导出，不得进入 ZBid 正式写回。
