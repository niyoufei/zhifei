# ZDoc Real Ollama Preview Advisory - Shadow Candidate Envelope Fake Helper Stage Review

## 1. Scope

本复盘对应 ZDoc Step 99：shadow candidate envelope fake-only helper implementation。Step 100 仅为 Step 99 fake-only helper 的 docs-only 实现复盘归档，目标是明确实现边界、能力范围、安全约束、测试结论、未实现事项和后续推进条件。

Step 99 新增的 helper 只构造 shadow candidate envelope metadata，用于把 Step 97 的 shadow candidate data contract 固化为隔离 envelope。该 helper 不代表 shadow generation implementation，不代表 candidate patch implementation，也不代表正式正文生成链、DOCX 导出链或 ZBid 写回链已接入。

当前系统仍处于 preview-only / no-write 阶段。shadow candidate envelope 仍不得作为 evidence，不得写回正文，不得进入 DOCX / JSON / Markdown 导出，不得进入 ZBid 正式写回。

## 2. Files Added in Step 99

Step 99 实际新增文件：

- `backend/zhifei_autoplan/shadow_candidate_envelope.py`
- `backend/tests/test_shadow_candidate_envelope.py`

Step 99 未修改：

- 未修改生产主链。
- 未修改既有 tests。
- 未修改 docs。
- 未修改 frontend。
- 未修改 app.py。
- 未修改 orchestrator、llm_client、provider、generation、export、review/apply、actions_bridge、DOCX export、ZBid writeback 链路。
- 未写 output / job / export。
- 未触发 DOCX / JSON / Markdown 正式导出。
- 未接正式正文生成链。

## 3. Helper Capability Summary

`backend/zhifei_autoplan/shadow_candidate_envelope.py` 当前能力仅限于：

- 构造 shadow candidate envelope dict。
- 固化 Step 97 / Step 98 数据契约字段。
- 固化 shadow candidate、evidence anchor、response mode、readiness status 枚举。
- 固化 blocked_reasons。
- 固化当前阶段正式链 flags 恒 false。
- 使用调用方显式传入的 `generated_at`。
- 通过标准库 `hashlib` 基于输入字段确定性生成 `shadow_candidate_id`。
- 只使用 Python 标准库。
- 返回可 JSON 化的 dict，而不是对象实例。

helper 不使用 `datetime.now()`、`time.time()`、`uuid.uuid4()` 或其他非确定性生成。`generated_at` 由调用方显式传入。`shadow_candidate_id` 如存在，必须为确定性生成，不使用随机值。

当前阶段 `formal_writeback_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒为 false。

## 4. Explicit Non-capabilities

Step 99 helper 明确不具备以下能力：

- 不生成真实 candidate text。
- 不生成真实 candidate patch。
- 不调用本地模型。
- 不调用外部模型。
- 不调用 Ollama。
- 不调用 API 或服务。
- 不读取章节正文生成候选内容。
- 不写回 source section。
- 不写 output / job / export。
- 不接 DOCX 导出。
- 不接 JSON / Markdown 正式导出。
- 不接 ZBid 写回。
- 不实现 human approval UI。
- 不执行 diff / rollback。
- 不进入 formal writeback。
- 不把 advisory 当 evidence。
- 不把 model-generated advisory 当 evidence。
- 不把 shadow candidate envelope 当 evidence。
- 不把 thinking_only_fallback 当作正文能力。

候选预览字段 `candidate_text_preview` / `candidate_patch_preview` 仍只能作为 fake-only envelope metadata 中的隔离字段，不代表真实候选正文或真实 patch 已生成。

## 5. Safety Invariants Confirmed

Step 99 已通过 deterministic tests 固化以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `docx_export_allowed` 恒 false。
3. `zbid_writeback_allowed` 恒 false。
4. `output_write_allowed` 恒 false。
5. `thinking_only_fallback` 必须 blocked。
6. `generated_advisory_only_blocked` 必须 blocked。
7. missing evidence anchor 必须 blocked。
8. empty evidence refs 必须 blocked。
9. missing human approval 必须 blocked。
10. missing diff readiness 必须 blocked。
11. missing rollback readiness 必须 blocked。
12. DOCX / ZBid / output / formal generation requests 必须 blocked。
13. preview fields 不得作为 evidence。
14. helper import 不得拉入主链模块。
15. helper 不写 output / job / export。
16. helper 只实际输出 `not_created` 或 `blocked`，不得在当前阶段输出 `ready_for_human_review` 或 `approved_shadow_only`。

这些不变量只说明 fake-only envelope metadata helper 可控，不说明 shadow generation、candidate patch、human approval、diff / rollback 或正式写回已实现。

## 6. Test Evidence from Step 99

Step 99 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_shadow_candidate_envelope.py -vv`
  - 结果：`15 passed in 0.04s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py -vv`
  - 结果：`27 passed in 0.04s`

- `python -m pytest backend/tests/test_shadow_candidate_envelope.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - 结果：`18 passed in 0.78s`

Step 99 未运行 full backend tests。原因是 Step 98B 已确认 full backend tests 存在既有 pytest collection/order import-isolation 问题。本复盘不将该既有 full-suite 顺序污染问题扩大解释为 Step 99 的生产功能风险。

## 7. Boundary Against Formal Generation Chain

Step 99 未接入以下链路：

- orchestrator。
- llm_client。
- provider。
- generation。
- export。
- review/apply。
- actions_bridge。
- DOCX export。
- ZBid writeback。
- output / job / export。

helper import 测试已验证不会拉入主要正式链模块。helper 不启动服务，不访问网络，不访问 127.0.0.1:11434，不调用 Ollama，不调用外部模型或 API。

## 8. Remaining Blockers Before Any Writeback

未来进入任何写回前，仍至少缺少以下能力和门禁：

- real evidence anchor validation。
- candidate patch contract。
- candidate patch fake-only helper。
- human approval gate。
- diff preview。
- rollback plan。
- formal writeback guard。
- DOCX export isolation guard。
- ZBid writeback isolation guard。
- explicit user approval。
- full no-write regression tests。
- candidate patch implementation review。
- human approval UI review。
- diff / rollback execution review。
- formal writeback isolation review。

缺少上述能力前，shadow candidate envelope 不得升级为可写回内容，不得进入正式正文，不得进入 DOCX 导出，不得进入 ZBid 写回。

## 9. Recommended Next Step

下一步建议为：

ZDoc Step 101：shadow candidate patch contract design，docs-only。

Step 101 也不得直接实现 candidate patch，不得写回正文，不得进入正式生成链，不得接 DOCX 导出，不得接 ZBid 写回。Step 101 应只定义 future candidate patch 的数据契约、字段边界、diff / rollback 前置条件、human approval 依赖和 no-write 边界。

## 10. Safety Conclusion

Step 99 仅完成 fake-only shadow candidate envelope metadata helper。当前系统仍处于 preview-only / no-write 阶段，不代表 shadow generation、真实 candidate patch、human approval、diff / rollback、formal writeback、DOCX 导出或 ZBid 写回已实现。

shadow candidate envelope 仍不得作为 evidence，仍不得写回正文，仍不得进入 DOCX / JSON / Markdown 导出，仍不得进入 ZBid 正式写回。thinking_only_fallback 仍不得作为正文能力，model-generated advisory 仍不得作为 evidence。

本复盘仅归档 Step 99 的 fake-only helper 实现边界和测试结论，不进入 Step 101，不进入 candidate patch implementation，不进入正式生成链。
