# KG-RUNTIME-97 content-safe output contract mapping controlled implementation draft review

## Scope

- Stage: KG-RUNTIME-97.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `73d367b0b0e706cdfd1a8dc05ee3fc75d76aa6bb`.
- Start baseline tag: `v0.1.479-zdoc-kg-content-safe-output-contract-design`.
- Baseline note: the local baseline tag is absent in this environment, and the remote tag was verified to point to the start HEAD.
- This stage is a controlled implementation draft for static content-safe output contract mapping.
- This stage does not enter KG-RUNTIME-98.

## Actual Modified Files

Modified code files:

- `backend/kg_read_only_preview_adapter.py`

Added helper file:

- `backend/kg_content_safe_output_contract.py`

Added review document:

- `docs/zdoc-kg-content-safe-output-contract-mapping-controlled-implementation-draft-kg-runtime-97-review.md`

Scope result:

- PASS: only the authorized adapter file and one independent helper file were modified or added.
- PASS: no route file change was required for this draft.
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
- No pytest.
- No py_compile.
- No directory scan rerun.
- No Ollama run.
- No output, job, or export write.
- No ZBid writeback.
- No RAG integration.
- No prompt registry integration.
- No system instruction registry integration.
- No CI integration.

## Mapping Implementation Summary

`backend/kg_content_safe_output_contract.py` defines a static, explicit, whitelist-style mapping with three field classes:

- `preview_only`
- `audit_only`
- `prohibited`

`backend/kg_read_only_preview_adapter.py` imports this helper and binds the static mapping as adapter-side draft contract metadata. The mapping is not added to the adapter output whitelist and does not add a route pass-through field. It does not read KG content, does not parse KG JSON, and does not create a new runtime read path.

## Preview-Only Fields

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

## Audit-Only Fields

Audit-only fields:

- `feature_flag_status`
- `manual_trigger_status`
- `real_kg_read_only_status`
- `authorized_target_hit_status`
- `allowlist_status`
- `route_contract_code`
- `adapter_contract_code`
- `validation_result`
- `overlap_check_result`

Audit-only fields are limited to operator audit, validation, and release-gate review. They are not正文, not generation material, not export material, not writeback material, not evidence, and not scoring.

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

These prohibited classes must not enter正文, the generation chain, export chain, writeback chain, evidence, or scoring. The mapping names these classes only as forbidden categories and does not read or output any actual prohibited KG content.

## Downstream Prohibition

The draft explicitly forbids use of this mapping for:

- `/generate`
- `/export_docx`
- `/review/apply`
- output writes
- job writes
- export writes
- ZBid writeback
- RAG
- prompt registry
- system instruction registry
- evidence
- scoring

Compliance result:

- PASS: the mapping is not connected to `/generate`.
- PASS: the mapping is not connected to `/export_docx`.
- PASS: the mapping is not connected to `/review/apply`.
- PASS: the mapping does not write output, job, or export files.
- PASS: the mapping does not trigger ZBid writeback.
- PASS: the mapping is not connected to RAG or registry surfaces.
- PASS: the mapping is not connected to CI.
- PASS: the mapping is not evidence.
- PASS: the mapping is not scoring.

## Next Stage Boundary

KG-RUNTIME-98 is still required for static compliance and no-runtime review.

This KG-RUNTIME-97 stage is only a contract mapping implementation draft. It cannot be treated as proof that ZDoc is integrated, cannot be treated as proof that any endpoint works, cannot be treated as evidence or scoring, and cannot be treated as entry into trial use.
