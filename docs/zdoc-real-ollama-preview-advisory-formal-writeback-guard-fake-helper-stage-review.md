# ZDoc Real Ollama Preview Advisory - Formal Writeback Guard Fake Helper Stage Review

## 1. Scope

This document is the Step 120 implementation stage review for the Step 119 fake-only formal writeback guard helper.

Step 119 added an isolated helper that only constructs a formal writeback guard metadata envelope. It does not execute formal writeback, does not modify a source section, does not trigger `review/apply`, and does not write `output/job/export`.

The system remains in a preview-only / no-write stage. This document records the helper boundary, safety constraints, scoped test evidence, known non-capabilities, and the conditions that must still be met before any actual writeback can be considered.

## 2. Files added in Step 119

Step 119 added:

- `backend/zhifei_autoplan/formal_writeback_guard.py`
- `backend/tests/test_formal_writeback_guard.py`

Step 119 did not modify:

- production main-chain code
- existing tests
- existing docs
- frontend files
- `app.py`
- `output/job/export`
- DOCX, ZBid, export, review, or generation chains

## 3. Helper capability summary

The helper capability is limited to isolated metadata construction:

- constructs a formal writeback guard metadata `dict`
- locks the Step 117/118 formal writeback guard contract fields
- locks `writeback_guard_status`, `writeback_decision`, `writeback_scope`, `writeback_mode`, `writeback_target_type`, and `source_hash_revalidation_status` enums
- records stable `blocked_reasons`
- keeps `formal_writeback_allowed`, `review_apply_allowed`, `docx_export_allowed`, `zbid_writeback_allowed`, and `output_write_allowed` always false
- accepts caller-supplied `generated_at`
- generates a deterministic `writeback_guard_id`, or accepts an explicit fixed `writeback_guard_id`
- accepts fake DOCX, ZBid, and `review_apply` isolation metadata fields while keeping the formal chain blocked

`generated_at` is caller supplied and does not use nondeterministic time. `writeback_guard_id` is deterministic or explicitly fixed, and does not use UUID, random values, or current time.

## 4. Explicit non-capabilities

The Step 119 helper explicitly does not:

- execute formal writeback
- modify `source_section`
- trigger `review/apply`
- write `output/job/export`
- generate DOCX, JSON, or Markdown formal exports
- connect to ZBid writeback
- open DOCX export
- open `review/apply`
- implement DOCX or ZBid isolation guards
- implement a source hash revalidation guard
- implement a `review/apply` isolation guard
- call local models, external models, Ollama, APIs, or services
- read or write files
- connect to `orchestrator`, `llm_client`, `provider`, `generation`, `export`, `review/apply`, `actions_bridge`, or ZBid
- treat the guard as evidence
- treat the guard as formal writeback permission
- treat the guard as DOCX, ZBid, or export admission
- treat the guard as a replacement for evidence, approval, diff preview, rollback plan, or source hash revalidation

`writeback_guard_status=approved_guard_shadow_only` and `writeback_decision=allow_shadow_only` are shadow-only metadata states. Neither state means `formal_writeback_allowed=true`.

## 5. Safety invariants confirmed

Step 119 confirms the following invariants for the current fake-only helper stage:

1. `formal_writeback_allowed` is always false.
2. `review_apply_allowed` is always false.
3. `docx_export_allowed` is always false.
4. `zbid_writeback_allowed` is always false.
5. `output_write_allowed` is always false.
6. The helper only emits `not_created`, `blocked`, or `stale_source_hash`.
7. The helper does not emit `ready_for_final_review` or `approved_guard_shadow_only`.
8. `writeback_guard_status=approved_guard_shadow_only` does not mean writeback is allowed.
9. `writeback_decision=allow_shadow_only` does not mean writeback is allowed.
10. A missing `shadow_candidate_id` must be blocked.
11. A missing `patch_id` must be blocked.
12. A missing `approval_id` must be blocked.
13. A missing `diff_preview_id` must be blocked.
14. A missing `rollback_plan_id` must be blocked.
15. `shadow_candidate_status=blocked` or `not_created` must be blocked.
16. `patch_status=blocked` or `not_created` must be blocked.
17. `approval_status` other than `approved_shadow_only` must be blocked.
18. `diff_preview_status=blocked`, `not_created`, or `stale_source_hash` must be blocked.
19. `rollback_plan_status=blocked`, `not_created`, or `stale_source_hash` must be blocked.
20. `response_mode=thinking_only_fallback` must be blocked.
21. A missing evidence anchor must be blocked.
22. Empty evidence refs must be blocked.
23. Generated advisory, shadow candidate, patch preview, diff preview, or rollback plan content used as evidence must be blocked.
24. A missing `source_section_hash` must be blocked.
25. `source_hash_revalidation_ready=false` must be blocked.
26. `source_hash_revalidation_status=missing`, `mismatched`, or `stale_source_hash` must be blocked or stale.
27. `source_section_hash_match=false` must be `stale_source_hash` or blocked.
28. A missing `writeback_candidate_hash` must be blocked.
29. A missing `source_snapshot_hash` must be blocked.
30. A missing `before_text_hash` must be blocked.
31. A missing `after_text_preview_hash` must be blocked.
32. A missing `patch_operations_preview_hash` must be blocked.
33. A missing `diff_preview_hash` must be blocked.
34. A missing `rollback_plan_hash` must be blocked.
35. Missing human approval must be blocked.
36. `diff_preview_ready=false` must be blocked.
37. `rollback_plan_ready=false` must be blocked.
38. `review_apply_isolation_ready=false` must be blocked.
39. DOCX isolation not ready must not open `docx_export_allowed`.
40. ZBid isolation not ready must not open `zbid_writeback_allowed`.
41. DOCX, ZBid, output, formal generation, and `review/apply` requests must be blocked.
42. Importing the helper must not pull main-chain modules.

Formal writeback guard metadata is not evidence. It does not replace an evidence anchor, human approval, diff preview, rollback plan, or source hash revalidation. It is also not DOCX, ZBid, or export admission.

## 6. Test evidence from Step 119

Step 119 ran the following scoped test commands successfully:

- `python -m pytest backend/tests/test_formal_writeback_guard.py -vv`
  - `21 passed in 0.05s`

- `python -m pytest backend/tests/test_formal_writeback_guard_contract_schema.py backend/tests/test_formal_writeback_guard.py -vv`
  - `42 passed in 0.06s`

- `python -m pytest backend/tests/test_shadow_candidate_contract_schema.py backend/tests/test_shadow_candidate_envelope.py backend/tests/test_shadow_candidate_patch_contract_schema.py backend/tests/test_shadow_candidate_patch.py backend/tests/test_human_approval_gate_contract_schema.py backend/tests/test_human_approval_gate.py backend/tests/test_diff_preview_contract_schema.py backend/tests/test_diff_preview.py backend/tests/test_rollback_plan_contract_schema.py backend/tests/test_rollback_plan.py backend/tests/test_formal_writeback_guard_contract_schema.py backend/tests/test_formal_writeback_guard.py -vv`
  - `228 passed in 0.23s`

- `python -m pytest backend/tests/test_formal_writeback_guard.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `24 passed in 0.82s`

Full backend tests were not run in Step 119 because Step 98B already confirmed an existing pytest collection/order import-isolation issue. That known full-suite issue is not expanded here into a production feature risk.

Step 120 is docs-only and does not run pytest.

## 7. Boundary against formal generation chain

Step 119 did not connect the helper to any formal generation or write chain:

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

The helper only returns fake-only guard metadata. It does not perform writeback, export, review, apply, model calls, network calls, or filesystem writes.

## 8. Remaining blockers before any actual writeback

Before any actual writeback can be considered, the system still needs:

- real evidence anchor validation
- real shadow generation implementation
- real candidate patch generation
- approval UI
- approval persistence / audit storage
- real diff implementation
- real rollback implementation
- source section hash revalidation guard
- `review/apply` isolation guard
- DOCX export isolation guard
- ZBid writeback isolation guard
- explicit user approval flow
- no-write regression tests
- formal writeback dry-run tests
- actual writeback apply implementation
- rollback execution verification
- DOCX/ZBid post-write isolation verification

None of these blockers are implemented by Step 119 or Step 120.

## 9. Recommended next step

The recommended next step is:

ZDoc Step 121: source hash revalidation guard contract design, docs-only.

Step 121 must not implement a source hash revalidation helper, must not read real body text to compute a hash, must not execute writeback, must not trigger `review/apply`, must not write `output/job/export`, and must not enter DOCX or ZBid flows.

## 10. Safety conclusion

Step 119 only completed a fake-only formal writeback guard metadata helper. Step 120 only records that stage review.

The current system remains preview-only / no-write. This document does not mean formal writeback, `review/apply`, DOCX export, ZBid writeback, DOCX/ZBid isolation, `review/apply` isolation, or source hash revalidation guard implementation exists.
