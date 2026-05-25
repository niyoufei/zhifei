# KG-RUNTIME-100 preview-only adapter mapping controlled implementation draft review

## Scope

- Stage: KG-RUNTIME-100.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `89d5f0f29fb71a592df5925884c1e949e0f055e2`.
- Start baseline tag: `v0.1.482-zdoc-kg-preview-only-adapter-mapping-gate`.
- Baseline note: local HEAD matched the requested baseline. The remote tag was not re-queried in this stage because network access outside the sandbox was not authorized under the no-full-access constraint.
- This stage is only a preview-only adapter mapping implementation draft.
- This stage does not enter KG-RUNTIME-101.

## Actual Modified Files

Modified code files:

- `backend/kg_content_safe_output_contract.py`
- `backend/kg_read_only_preview_adapter.py`

Added review document:

- `docs/zdoc-kg-preview-only-adapter-mapping-controlled-implementation-draft-kg-runtime-100-review.md`

Scope result:

- PASS: only the authorized helper and adapter files were modified.
- PASS: no route-layer change was required for this draft.
- PASS: `backend/app/main.py` was not modified.
- PASS: frontend files were not modified.
- PASS: tests were not modified.
- PASS: config files were not modified.
- PASS: JSON files were not modified.

## Runtime And Read Boundary

Not performed in this stage:

- No real KG body read.
- No real KG JSON parse.
- No service start.
- No port access.
- No endpoint call.
- No `/health` call.
- No `/kg/read-only-preview` call.
- No `/generate` call.
- No `/export_docx` call.
- No `/review/apply` call.
- No directory scan rerun.
- No `pytest`.
- No `py_compile`.
- No Ollama run.
- No output, job, or export write.
- No ZBid writeback.
- No RAG integration.
- No prompt registry integration.
- No system instruction registry integration.
- No CI integration.
- No evidence use.
- No scoring use.

## Implementation Summary

`backend/kg_content_safe_output_contract.py` now adds static, explicit, whitelist-style helper functions:

- `classify_content_safe_fields`
- `filter_preview_only_fields`
- `filter_audit_only_fields`
- `build_preview_only_payload`

`backend/kg_read_only_preview_adapter.py` now binds the static KG-RUNTIME-100 mapping contract and exposes `build_preview_only_adapter_mapping`.

The draft accepts only an already content-safe response mapping. It performs no file IO, no KG read, no JSON parse, no service call, no generation, no export, no writeback, no evidence handling, no scoring, no RAG access, and no registry access.

## Preview-Only Mapping Fields

Top-level preview-only fields:

- `structure_read_only`
- `structure_summary`
- `structural_profile_only`
- `structural_profile_summary`

`structure_contract` safe enum / numeric-code fields:

- `contract_scope`
- `authorized_target`
- `allowlist_status`
- `target_policy`
- `summary_field_whitelist`
- `value_output_policy`
- `scalar_policy`
- `list_policy`
- `dict_policy`

`structural_profile_contract` safe enum / numeric-code fields:

- `contract_scope`
- `authorized_target`
- `allowlist_status`
- `target_policy`
- `summary_field_whitelist`
- `profile_scope`
- `redaction_policy`
- `scalar_policy`
- `list_policy`
- `dict_policy`
- `module_name_policy`

The contract field filter keeps only numeric codes or numeric-code lists / tuples. It does not pass through arbitrary contract values.

## Audit-Only Mapping Fields

Contract-level audit-only fields:

- `feature_flag_status`
- `manual_trigger_status`
- `real_kg_read_only_status`
- `authorized_target_hit_status`
- `allowlist_status`
- `route_contract_code`
- `adapter_contract_code`
- `validation_result`
- `overlap_check_result`

Adapter / route response audit aliases:

- `feature_flag`
- `manual_trigger_required`
- `real_kg_read_only`
- `authorized_target`
- `source`
- `contract_scope`
- `route_name`
- `endpoint_path`
- `status`
- `reason`
- `adapter_status`

Audit-only fields are limited to gate status, contract code, validation result, and overlap-check review. They are not正文, not generation material, not export material, not writeback material, not evidence, and not scoring.

## Prohibited Fields

Prohibited field/content classes:

- KG scalar value.
- list item 内容.
- dict value 内容.
- 业务正文.
- 实体正文.
- 知识条目正文.
- prompt.
- system instruction.
- evidence.
- scoring.
- 原始 KG 文本片段.
- 可反推 KG 正文的字符串.

The prohibited class remains a forbidden-category list only. It does not output any actual KG value.

Compliance result:

- PASS: prohibited fields are not included in `preview_only`.
- PASS: `preview_only` is built only from static top-level whitelists and safe contract-code whitelists.
- PASS: the draft is not connected to `/generate`.
- PASS: the draft is not connected to `/export_docx`.
- PASS: the draft is not connected to `/review/apply`.
- PASS: the draft does not write output, job, or export files.
- PASS: the draft is not connected to RAG, prompt registry, system instruction registry, or CI.
- PASS: the draft is not evidence.
- PASS: the draft is not scoring.

## Next Stage Boundary

KG-RUNTIME-101 is still required for static compliance and no-output-chain review.

This stage is only a preview-only adapter mapping draft. It cannot be treated as proof that ZDoc has integrated KG, cannot be treated as proof that any endpoint works, cannot be treated as real use, and cannot be treated as trial use.
