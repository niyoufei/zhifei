# KG-RUNTIME-86 Guard Field Normalization Static Compliance and No-Content-Leak Review

## Scope

- Stage: KG-RUNTIME-86.
- Review target: KG-RUNTIME-85 guard-field normalization remediation implementation draft.
- Baseline branch: `main`.
- Baseline HEAD: `c1c90e58ada12e5ddbb8b9a64c54f03cd625cfd6`.
- Baseline tag: `v0.1.468-zdoc-kg-guard-field-normalization-remediation-draft`.
- Review mode: static docs-only review.
- This review does not enter KG-RUNTIME-87.
- This review does not prove residual overlap re-smoke passed.

## Static Inputs Reviewed

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`
- `docs/zdoc-kg-guard-field-normalization-remediation-implementation-draft-kg-runtime-85-review.md`
- `git show --name-status --oneline --no-renames HEAD`
- `git diff --name-only HEAD^ HEAD`
- `git diff --stat HEAD^ HEAD`

## Change-Scope Compliance

- PASS: KG-RUNTIME-85 modified only the authorized adapter and route files, plus its docs-only review file.
- PASS: KG-RUNTIME-85 modified `backend/kg_read_only_preview_adapter.py`.
- PASS: KG-RUNTIME-85 modified `backend/app/routers/kg_read_only_preview.py`.
- PASS: KG-RUNTIME-85 added `docs/zdoc-kg-guard-field-normalization-remediation-implementation-draft-kg-runtime-85-review.md`.
- PASS: `backend/app/main.py` was not modified.
- PASS: frontend files were not modified.
- PASS: tests were not modified.
- PASS: config files were not modified.
- PASS: JSON files were not modified.
- PASS: no second uncontrolled file-read path was added.
- PASS: existing controlled structure-read path is still reused.

## Guard-Field Normalization Findings

- PASS: route `reason` output is normalized through `ROUTE_REASON_CODES` and `_route_reason_code()`.
- PASS: adapter `reason` output is normalized through `ADAPTER_REASON_CODES` and `_adapter_reason_code()`.
- PASS: adapter `contract_scope` response values are numeric codes.
- PASS: adapter `target_policy`, `read_policy`, and `value_output_policy` response values are numeric codes.
- PASS: structure and structural-profile contract policy fields are reduced to numeric codes or booleans.
- PASS: `allowlist_status` is reduced to short enums: `meta`, `struct`, `profile`, `blocked`, and `unavail`.
- PASS: read-only and disabled boundary fields continue to use booleans, including `enabled`, `structure_read_only`, `content_read_performed`, `json_parse_performed`, `no_write`, `no_evidence`, `no_scoring`, `no_rag`, `no_generation`, `no_export`, and `no_zbid_writeback`.
- PASS: `module_name_candidates` remains fixed to an empty list through `_structural_profile_module_name_candidates()`.
- PASS: `redaction_policy` remains the fixed short enum `redacted`.

## Summary-Shape Preservation

- PASS: `structure_summary` still preserves exactly 13 whitelisted field names:
  - `top_level_type`
  - `top_level_key_names`
  - `top_level_key_count`
  - `dict_count`
  - `list_count`
  - `null_count`
  - `scalar_type_counts`
  - `selected_structure_paths`
  - `list_lengths`
  - `field_type_sets`
  - `max_depth_limited`
  - `authorized_target`
  - `allowlist_status`
- PASS: `structure_summary` field count was not expanded.
- PASS: `structural_profile_summary` still preserves exactly 14 whitelisted field names:
  - `authorized_target`
  - `allowlist_status`
  - `profile_enabled`
  - `profile_scope`
  - `max_depth_limited`
  - `path_count`
  - `path_type_counts`
  - `depth_histogram`
  - `field_name_counts`
  - `field_type_sets`
  - `list_length_buckets`
  - `dict_key_count_buckets`
  - `module_name_candidates`
  - `redaction_policy`
- PASS: `structural_profile_summary` field count was not expanded.
- PASS: `structure_contract` is retained.
- PASS: `structural_profile_contract` is retained.
- PASS: guard, status, and policy content inside the contracts is reduced to numeric codes, booleans, fixed short enums, or field-name whitelists.

## No-Content-Leak Review

- PASS: no scalar value output was added.
- PASS: no list item content output was added.
- PASS: no dict value content output was added.
- PASS: top-level key names remain an empty tuple.
- PASS: selected structure paths are summarized as counts and type/depth code buckets, not raw path strings.
- PASS: field type sets summarize type-code buckets and counts, not field names or values.
- PASS: list details summarize ordinal/count/bucket/type-code counts, not item values.
- PASS: no business body text is output.
- PASS: no entity body text is output.
- PASS: no knowledge-entry body text is output.
- PASS: no prompt text is output.
- PASS: no system instruction text is output.
- PASS: no evidence text is output.
- PASS: no scoring text is output.
- PASS: no generated document body text is output.
- PASS: no RAG-ready text block output was added.
- PASS: no prompt registry content output was added.
- PASS: no system instruction registry content output was added.

## Runtime and Read Boundary Review

- PASS: no import-time file read was introduced.
- PASS: no service-start automatic file read was introduced.
- PASS: no directory scan was introduced.
- PASS: no batch read was introduced.
- PASS: allowlist was not expanded beyond `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- PASS: no new route registration was introduced by KG-RUNTIME-85.
- PASS: no endpoint invocation was required or performed for this review.
- PASS: no service run was required or performed for this review.
- PASS: no TCP port binding was required or performed for this review.
- PASS: no `127.0.0.1` access was required or performed for this review.
- PASS: no `/health` call was required or performed for this review.
- PASS: no `/kg/read-only-preview` call was required or performed for this review.
- PASS: no real KG file body was read during KG-RUNTIME-86.
- PASS: no real KG JSON was parsed during KG-RUNTIME-86.

## Excluded Chains and Registries

- PASS: no pytest run was performed.
- PASS: no py_compile run was performed.
- PASS: no Ollama run was performed.
- PASS: no generation chain integration was added.
- PASS: no export chain integration was added.
- PASS: no writeback chain integration was added.
- PASS: no ZBid writeback integration was added.
- PASS: no output, job, or export file write was added.
- PASS: no RAG integration was added.
- PASS: no prompt registry integration was added.
- PASS: no system instruction registry integration was added.
- PASS: no CI integration was added.
- PASS: KG-RUNTIME-85 draft output is not evidence.
- PASS: KG-RUNTIME-85 draft output is not scoring.
- PASS: KG-RUNTIME-86 review output is not evidence.
- PASS: KG-RUNTIME-86 review output is not scoring.

## Residual Gate

- KG-RUNTIME-87 is still required for guard-field remediation frozen audit and no-server re-smoke authorization gate.
- KG-RUNTIME-86 is a static compliance and no-content-leak review only.
- KG-RUNTIME-86 does not represent, replace, or imply residual overlap re-smoke success.
- No real-use stage is authorized by this review.

## Verdict

PASS: KG-RUNTIME-85 guard-field normalization remediation implementation draft remains within the authorized adapter/route/docs scope and preserves the content-safe, structure-only, metadata-only, no-runtime, no-auto-read, no-content-leak, no-generation, no-export, no-writeback, no-evidence, no-scoring, no-RAG, and no-registry boundaries under static review.
