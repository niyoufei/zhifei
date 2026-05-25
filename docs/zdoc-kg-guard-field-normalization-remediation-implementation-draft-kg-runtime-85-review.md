# KG-RUNTIME-85 Guard Field Normalization Remediation Draft Review

## Scope

- Stage: KG-RUNTIME-85.
- Goal: guard/status/contract/policy/disabled/read-only field normalization draft.
- Status: implementation draft only.
- Next stage: KG-RUNTIME-86 still required for static compliance and no-content-leak review.
- This stage does not prove residual overlap re-smoke passed.

## Actual Changes

- Modified files:
  - `backend/kg_read_only_preview_adapter.py`
  - `backend/app/routers/kg_read_only_preview.py`
- Added file:
  - `docs/zdoc-kg-guard-field-normalization-remediation-implementation-draft-kg-runtime-85-review.md`
- Only authorized adapter/route files were modified.
- `backend/app/main.py` was not modified.
- Frontend, tests, config, and JSON files were not modified.

## Non-Execution Confirmation

- Real KG body content was not read during this stage.
- Real KG JSON was not parsed during this stage.
- No service was started.
- No endpoint was called.
- No TCP port was bound or accessed.
- No directory scan was executed.
- No pytest run was executed.
- No py_compile run was executed.
- No Ollama call was executed.
- No generation, export, review apply, or ZBid writeback was triggered.
- No output, job, or export file was written.
- No RAG, prompt registry, system instruction registry, or CI integration was added.
- No KG scalar value, list item value, dict value, business body, entity body, knowledge entry body, prompt, system instruction, evidence, or scoring output was added.

## Normalization Summary

- Guard fields:
  - Route `reason` now emits numeric reason codes.
  - Adapter `reason` now emits numeric reason codes.
  - Illegal request field names are no longer echoed in route `reason`.
- Status fields:
  - Existing short fixed `status` enums are preserved.
  - `allowlist_status` values are reduced to short fixed enums: `meta`, `struct`, `profile`, `blocked`, `unavail`.
- Contract fields:
  - `contract_scope` response values are reduced to numeric codes.
  - `structure_contract` and `structural_profile_contract` keep their field names and reduce contract scope/policy values to numeric codes or booleans.
- Policy fields:
  - `target_policy`, `read_policy`, and `value_output_policy` response values are numeric codes.
  - `redaction_policy` remains the short fixed enum `redacted`.
- Disabled/read-only fields:
  - `enabled`, `structure_read_only`, `content_read_performed`, `json_parse_performed`, and runtime boundary fields remain booleans.
  - Empty collections remain empty tuple/list where used by summary fields.

## Required Shape Preservation

- `structure_read_only` is still returned by the controlled structure-read path.
- `structure_summary` is still returned by the controlled structure-read path.
- `structure_contract` is still returned by the controlled structure-read path.
- `structural_profile_only` is still returned by the controlled structural-profile path.
- `structural_profile_summary` is still returned by the controlled structural-profile path.
- `structural_profile_contract` is still returned by the controlled structural-profile path.
- The 13 `structure_summary` field names are preserved.
- The 14 `structural_profile_summary` field names are preserved.
- `module_name_candidates` remains an empty list.
- `redaction_policy` remains `redacted`.
- No second uncontrolled KG read path was added.
- The existing controlled structure-read path is reused.

## Gate Preservation

- Feature flag gating is preserved.
- `manual_trigger = true` gating is preserved.
- `real_kg_read_only = true` gating is preserved.
- `structure_read = true` gating is preserved.
- `structural_profile = true` gating is preserved.
- `authorized_target` strict match to `知识图谱/ZF-KG-12-Municipal-Bridge.json` is preserved.

## Residual Risk

- This is a static remediation draft, not a runtime smoke result.
- KG-RUNTIME-86 must perform static compliance and no-content-leak review before any later runtime claim.
- This stage cannot be used as evidence that residual overlap re-smoke passed.
