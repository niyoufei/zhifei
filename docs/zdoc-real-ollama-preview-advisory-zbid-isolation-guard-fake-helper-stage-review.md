# ZDoc Real Ollama Preview Advisory - ZBid Isolation Guard Fake Helper Stage Review

## 1. Scope

Step 136 仅为 Step 135 fake-only ZBid isolation guard helper 的实现复盘归档。本文档用于记录 Step 135 的实现边界、安全约束、测试结论、未实现事项和后续推进条件，不新增运行时代码，不修改既有测试，不改变任何正式生成、导出、review/apply、DOCX 或 ZBid 写回链路。

Step 135 新增的 helper 只构造 ZBid isolation metadata envelope。它把 Step 133/134 设计的 ZBid isolation guard contract 固化为一个可测试的 fake-only metadata dict，用于当前 preview-only / no-write 阶段的隔离边界表达。

本文档不代表真实 ZBid isolation、ZBid 写回、正式写回、DOCX 导出或 review/apply 已实现。

## 2. Files Added in Step 135

Step 135 新增文件：

- `backend/zhifei_autoplan/zbid_isolation_guard.py`
- `backend/tests/test_zbid_isolation_guard.py`

Step 135 未修改：

- 生产主链。
- 既有 tests。
- 既有 docs。
- `frontend/`。
- `app.py`。
- `output/job/export`。
- DOCX / ZBid / export / review / generation 链路。
- `orchestrator`、`llm_client`、`provider`、`generation`、`export`、`review/apply`、`actions_bridge`、ZBid API / DB / writeback 相关链路。

## 3. Helper Capability Summary

`backend/zhifei_autoplan/zbid_isolation_guard.py` 当前能力仅限于：

- 构造 ZBid isolation metadata dict。
- 固化 Step 133/134 ZBid isolation guard contract 字段。
- 固化 `zbid_isolation_status`、`zbid_writeback_decision`、`zbid_writeback_scope`、`zbid_writeback_mode`、`zbid_target_type`、`zbid_writeback_request_status` 枚举。
- 固化 `blocked_reasons`。
- 固化 `formal_writeback_allowed`、`review_apply_allowed`、`docx_export_allowed`、`zbid_writeback_allowed`、`output_write_allowed` 恒 false。
- 接收调用方显式传入的 `generated_at`。
- 基于输入字段确定性生成 `zbid_isolation_guard_id`，或使用调用方显式传入的固定 `zbid_isolation_guard_id`。
- 接收 `zbid_writeback_route`、`zbid_writeback_payload_hash`、`zbid_candidate_hash`、`zbid_target_mapping_hash` 等 fake metadata 字段，并保持当前阶段阻断。

`zbid_writeback_payload_hash`、`zbid_candidate_hash`、`zbid_target_mapping_hash` 只能由调用方显式传入。当前阶段不得读取真实 payload、真实 ZBid 数据、真实 ZBid 映射或真实文件生成这些 metadata。

`zbid_writeback_route` 仅作为 fake metadata 字段，不触发真实接口。

## 4. Explicit Non-Capabilities

Step 135 fake-only helper 明确不具备以下能力：

- 不触发 ZBid 写回。
- 不调用 ZBid API。
- 不访问 ZBid 数据库。
- 不调用 ZBid 写回接口。
- 不读取真实 ZBid 数据。
- 不读取真实 ZBid 映射。
- 不执行正式写回。
- 不读取真实正文。
- 不修改 source section。
- 不写 `output/job/export`。
- 不生成 DOCX / JSON / Markdown。
- 不接 DOCX 导出。
- 不开放 ZBid writeback。
- 不实现真实 ZBid isolation。
- 不调用本地模型、外部模型、Ollama、API 或服务。
- 不读写文件。
- 不接入 `orchestrator`、`llm_client`、`provider`、`generation`、`export`、`review/apply`、`actions_bridge`、ZBid。
- 不把 ZBid isolation 当 evidence。
- 不把 ZBid isolation 当 writeback permission。
- 不把 ZBid isolation 当 DOCX / export 准入。
- 不把 ZBid isolation 当 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation、review/apply isolation、DOCX isolation 的替代条件。

`generated_at` 由调用方显式传入，不使用 `datetime.now()`、`time.time()` 或任何非确定性时间。

`zbid_isolation_guard_id` 必须确定性生成或由调用方显式固定，不使用 `uuid.uuid4()`、`random` 或当前时间。

`zbid_isolation_status=isolated_shadow_only` 不等于 `zbid_writeback_allowed=true`。`zbid_writeback_decision=isolate_shadow_only` 也不等于 `zbid_writeback_allowed=true`。

## 5. Safety Invariants Confirmed

Step 135 测试已确认以下安全不变量：

1. `formal_writeback_allowed` 恒 false。
2. `review_apply_allowed` 恒 false。
3. `docx_export_allowed` 恒 false。
4. `zbid_writeback_allowed` 恒 false。
5. `output_write_allowed` 恒 false。
6. helper 只输出 `not_created`、`blocked`、`stale_source_hash` 或 `stale_source_version`。
7. helper 不输出 `isolated_shadow_only` 或 `ready_for_future_manual_writeback`。
8. `isolated_shadow_only` 不等于可 ZBid 写回。
9. `isolate_shadow_only` 不等于可 ZBid 写回。
10. missing `shadow_candidate_id` 必须 blocked。
11. missing `patch_id` 必须 blocked。
12. missing `approval_id` 必须 blocked。
13. missing `diff_preview_id` 必须 blocked。
14. missing `rollback_plan_id` 必须 blocked。
15. missing `writeback_guard_id` 必须 blocked。
16. missing `source_hash_guard_id` 必须 blocked。
17. missing `review_apply_guard_id` 必须 blocked。
18. missing `docx_isolation_guard_id` 必须 blocked。
19. `shadow_candidate_status=blocked` 或 `not_created` 必须 blocked。
20. `patch_status=blocked` 或 `not_created` 必须 blocked。
21. `approval_status` 非 `approved_shadow_only` 必须 blocked。
22. `diff_preview_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
23. `rollback_plan_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
24. `writeback_guard_status=blocked`、`not_created` 或 `stale_source_hash` 必须 blocked。
25. `source_hash_guard_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
26. `review_apply_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
27. `docx_isolation_status=blocked`、`not_created`、`stale_source_hash` 或 `stale_source_version` 必须 blocked。
28. `thinking_only_fallback` 必须 blocked。
29. missing evidence anchor 必须 blocked。
30. empty evidence refs 必须 blocked。
31. advisory / shadow candidate / patch preview / diff preview / rollback plan 作为 evidence 均必须 blocked。
32. `source_hash_match=false` 必须 `stale_source_hash` 或 blocked。
33. `source_version_match=false` 必须 `stale_source_version` 或 blocked。
34. `current_source_section_hash` 缺失必须 blocked。
35. `current_source_section_version` 缺失必须 blocked。
36. `zbid_writeback_requested=true` 必须 blocked。
37. `zbid_writeback_route` 指向任意 ZBid 写回接口必须 blocked。
38. `zbid_writeback_payload_hash` 缺失必须 blocked。
39. `zbid_candidate_hash` 缺失必须 blocked。
40. `zbid_target_mapping_hash` 缺失必须 blocked。
41. `zbid_source_snapshot_hash` 缺失必须 blocked。
42. `docx_candidate_hash` 缺失必须 blocked。
43. `writeback_candidate_hash` 缺失必须 blocked。
44. `source_snapshot_hash` 缺失必须 blocked。
45. `before_text_hash` 缺失必须 blocked。
46. `after_text_preview_hash` 缺失必须 blocked。
47. `patch_operations_preview_hash` 缺失必须 blocked。
48. `diff_preview_hash` 缺失必须 blocked。
49. `rollback_plan_hash` 缺失必须 blocked。
50. human approval 缺失必须 blocked。
51. `diff_preview_ready=false` 必须 blocked。
52. `rollback_plan_ready=false` 必须 blocked。
53. `formal_writeback_guard_ready=false` 必须 blocked。
54. `source_hash_revalidation_ready=false` 必须 blocked。
55. `review_apply_isolation_ready=false` 必须 blocked。
56. `docx_isolation_ready=false` 必须 blocked。
57. DOCX export request 必须 blocked。
58. `output/job/export` write request 必须 blocked。
59. formal generation request 必须 blocked。
60. review/apply request 必须 blocked。
61. `export_docx_request_triggered=true` 必须 blocked。
62. `zbid_writeback_request_triggered=true` 必须 blocked。
63. helper 不触发 ZBid 写回。
64. helper 不调用 ZBid API / 数据库 / 写回接口。
65. helper 不读取真实 ZBid 数据或真实映射生成 hash。
66. helper import 不得拉入主链、导出链或 ZBid 模块。

ZBid isolation 不得作为 evidence，不得替代 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation、review/apply isolation 或 DOCX isolation，也不得作为 DOCX/export 准入。

## 6. Test Evidence from Step 135

Step 135 已运行并通过以下限定测试组合：

- `python -m pytest backend/tests/test_zbid_isolation_guard.py -vv`
  - `20 passed in 0.05s`

- `python -m pytest backend/tests/test_zbid_isolation_guard_contract_schema.py backend/tests/test_zbid_isolation_guard.py -vv`
  - `38 passed in 0.08s`

- `python -m pytest` 指定 20 个 guard / contract 文件 `-vv`
  - `391 passed in 0.45s`

- `python -m pytest backend/tests/test_zbid_isolation_guard.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `23 passed in 0.74s`

Step 135 未运行 full backend tests。原因是 Step 98B 已确认 backend/tests full suite 存在既有 collection/order import-isolation 问题。本复盘不应把 full suite 未运行扩大解释为生产功能风险；本阶段验收以限定测试组合、文件边界和 no-write / no-runtime 约束为准。

Step 136 为 docs-only 复盘归档，本步未运行 pytest。

## 7. Push and Remote Verification Note

Step 135 推送过程如下：

- SSH push 初次失败。
- SSH 443 仍失败。
- HTTPS push 成功。
- 远端 `main` 已核验为 `01310789505e4ce43c826b45f4e67b193fe0d6ea`。
- tag `v0.1.194-zdoc-zbid-isolation-guard-fake-helper` 已核验指向同一 commit。

该问题属于网络 / SSH 连接问题，不影响 Step 135 代码边界。后续如再次发生，应优先停止并回报，不得 force push。

## 8. Boundary Against Formal Generation and Writeback Chains

Step 135 未接入以下链路：

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

Step 135 helper 不调用本地模型、外部模型、Ollama、API 或服务；不访问 `127.0.0.1:11434`；不启动后端或前端服务；不触发 `/generate`、`/export_docx`、`/review/apply` 或任何 ZBid writeback route。

## 9. Remaining Blockers Before Any Actual ZBid Writeback or Formal Writeback

未来进入 ZBid 写回或正式写回前仍缺少：

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
- explicit user approval flow。
- no-write regression tests。
- formal writeback dry-run tests。
- actual writeback apply implementation。
- rollback execution verification。
- DOCX post-write isolation verification。
- ZBid post-write isolation verification。
- 小范围试用验证。
- ZDoc / ZBid 对接联调验证。

在上述条件补齐前，ZBid isolation metadata 只能作为 fake-only / preview-only 隔离元数据，不得作为实际 ZBid 写回、DOCX/export、正式写回或 review/apply 的准入。

## 10. Recommended Next Step

建议下一步为：

ZDoc Step 137：formal writeback dry-run contract design，docs-only。

Step 137 不得实现 dry-run helper，不得执行正式写回，不得触发 review/apply，不得触发 DOCX 导出，不得触发 ZBid 写回，不得读取或修改真实正文，不得写 `output/job/export`。

## 11. Safety Conclusion

Step 135 仅完成 fake-only ZBid isolation guard metadata helper。当前系统仍处于 preview-only / no-write 阶段，不代表 ZBid 写回、DOCX 导出、正式写回或 review/apply 已实现。

Step 136 仅归档该 fake-only helper 的实现复盘和边界结论，不执行测试、不运行服务、不调用模型、不触发任何生成、导出、review/apply、DOCX 或 ZBid 写回链路。
