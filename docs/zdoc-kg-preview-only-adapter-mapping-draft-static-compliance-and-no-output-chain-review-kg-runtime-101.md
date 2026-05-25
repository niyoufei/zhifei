# KG-RUNTIME-101 ZDoc KG preview-only adapter mapping draft static compliance and no-output-chain review

## Scope

- Stage: KG-RUNTIME-101.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `43092053e246501ec4af2c26109447fe8ea514a8`.
- Start baseline tag: `v0.1.483-zdoc-kg-preview-only-adapter-mapping-draft`.
- Baseline tag status: remote tag `refs/tags/v0.1.483-zdoc-kg-preview-only-adapter-mapping-draft` points to `43092053e246501ec4af2c26109447fe8ea514a8`.
- Review type: static compliance review only.
- Allowed output of this stage: this docs-only review file only.
- This stage does not enter KG-RUNTIME-102.

KG-RUNTIME-101 only reviews the KG-RUNTIME-100 preview-only adapter mapping controlled implementation draft. It does not mean ZDoc has integrated KG, does not mean any runtime chain is enabled, and does not enter real-use or trial-use status.

## Reviewed Inputs

Static inputs reviewed:

- `git show --name-status --format=fuller HEAD`.
- `git diff --name-status HEAD^ HEAD`.
- `git diff HEAD^ HEAD -- backend/app/routers/kg_read_only_preview.py`.
- `backend/kg_content_safe_output_contract.py`.
- `backend/kg_read_only_preview_adapter.py`.
- `backend/app/routers/kg_read_only_preview.py`.
- `docs/zdoc-kg-preview-only-adapter-mapping-controlled-implementation-draft-kg-runtime-100-review.md`.

Not performed in this stage:

- No service start.
- No port access.
- No endpoint call.
- No `/health` call.
- No `/kg/read-only-preview` call.
- No real KG file body read.
- No real KG JSON parse.
- No directory scan rerun.
- No `pytest`.
- No `py_compile`.
- No Ollama run.
- No `/generate` call.
- No `/export_docx` call.
- No `/review/apply` call.
- No ZBid writeback.
- No output, job, or export write.
- No RAG, prompt registry, system instruction registry, or CI integration.
- No evidence use.
- No scoring use.

## KG-RUNTIME-100 Modified Scope

`git show --name-status --format=fuller HEAD` and `git diff --name-status HEAD^ HEAD` show that KG-RUNTIME-100 changed only:

- `backend/kg_content_safe_output_contract.py`
- `backend/kg_read_only_preview_adapter.py`
- `docs/zdoc-kg-preview-only-adapter-mapping-controlled-implementation-draft-kg-runtime-100-review.md`

Static compliance result:

- PASS: KG-RUNTIME-100 only modified the authorized helper / adapter files plus its docs-only review file.
- PASS: route code was not modified by KG-RUNTIME-100.
- PASS: `backend/app/main.py` was not modified.
- PASS: frontend files were not modified.
- PASS: tests were not modified.
- PASS: config files were not modified.
- PASS: JSON files were not modified.

## Route Isolation

`git diff HEAD^ HEAD -- backend/app/routers/kg_read_only_preview.py` produced no route diff.

The route file still imports only `build_kg_read_only_preview` from `backend.kg_read_only_preview_adapter`. It does not import or call `build_preview_only_adapter_mapping`.

Static compliance result:

- PASS: route behavior was not changed by KG-RUNTIME-100.
- PASS: the preview-only mapping draft is not route-wired.
- PASS: the mapping draft is not endpoint-wired in KG-RUNTIME-101.

## Helper And Adapter Mapping Presence

`backend/kg_content_safe_output_contract.py` retains or adds these pure helper functions:

- `classify_content_safe_fields`
- `filter_preview_only_fields`
- `filter_audit_only_fields`
- `build_preview_only_payload`

`backend/kg_read_only_preview_adapter.py` adds:

- `build_preview_only_adapter_mapping`

Static compliance result:

- PASS: helper functions are static mapping/filter helpers.
- PASS: `build_preview_only_adapter_mapping` delegates to `build_preview_only_payload`.
- PASS: no helper writes files.
- PASS: no helper starts a service.
- PASS: no helper calls a route.
- PASS: no helper invokes model, RAG, registry, evidence, scoring, generation, export, or writeback chains.

## Preview-Only Field Review

`preview_only` is built from:

- `PREVIEW_ONLY_TOP_LEVEL_FIELDS`.
- `STRUCTURE_CONTRACT_PREVIEW_ONLY_FIELDS`.
- `STRUCTURAL_PROFILE_CONTRACT_PREVIEW_ONLY_FIELDS`.

The top-level preview-only whitelist is limited to:

- `structure_read_only`
- `structure_summary`
- `structural_profile_only`
- `structural_profile_summary`

The contract whitelists are limited to structure / structural-profile contract fields such as:

- `contract_scope`
- `authorized_target`
- `allowlist_status`
- `target_policy`
- `summary_field_whitelist`
- `value_output_policy`
- `profile_scope`
- `redaction_policy`
- `scalar_policy`
- `list_policy`
- `dict_policy`
- `module_name_policy`

Contract field filtering uses `_is_safe_contract_code`, which only allows non-boolean non-negative integers or lists / tuples of those integers.

Static compliance result:

- PASS: `preview_only` only exposes whitelisted structure summaries and safe contract numeric codes.
- PASS: arbitrary contract strings are not passed through by the contract-code filter.
- PASS: `preview_only` is not treated as generation material.
- PASS: `preview_only` is not treated as export material.
- PASS: `preview_only` is not treated as writeback material.
- PASS: `preview_only` is not evidence.
- PASS: `preview_only` is not scoring.

## Audit-Only Field Review

`audit_only` is built from:

- `AUDIT_ONLY_FIELDS`
- `AUDIT_ONLY_RESPONSE_FIELDS`

The reviewed audit-only fields are status / contract / validation / overlap classes, including:

- `feature_flag_status`
- `manual_trigger_status`
- `real_kg_read_only_status`
- `authorized_target_hit_status`
- `allowlist_status`
- `route_contract_code`
- `adapter_contract_code`
- `validation_result`
- `overlap_check_result`
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

Static compliance result:

- PASS: audit-only fields are limited to status / contract / validation / overlap review fields.
- PASS: audit-only fields are not KG正文.
- PASS: audit-only fields are not generation material.
- PASS: audit-only fields are not export material.
- PASS: audit-only fields are not writeback material.
- PASS: audit-only fields are not evidence.
- PASS: audit-only fields are not scoring.

## Prohibited Field Review

`prohibited` remains a forbidden-category list. The reviewed prohibited classes include:

- `KG scalar value`
- `list item 内容`
- `dict value 内容`
- `业务正文`
- `实体正文`
- `知识条目正文`
- `prompt`
- `system instruction`
- `evidence`
- `scoring`
- `原始 KG 文本片段`
- `可反推 KG 正文的字符串`

`build_preview_only_payload` emits:

- `prohibited.fields`
- `prohibited.values_output = False`

Static compliance result:

- PASS: prohibited only preserves forbidden categories.
- PASS: prohibited does not output actual KG values.
- PASS: prohibited is not included inside `preview_only`.
- PASS: prohibited content classes are not downgraded into preview-only content.

## No-Output-Chain Review

KG-RUNTIME-100's changed files define static helper mapping and adapter delegation only. The reviewed route file has no KG-RUNTIME-100 route diff and does not call the new mapping helper.

Static compliance result:

- PASS: mapping is not connected to `/generate`.
- PASS: mapping is not connected to `/export_docx`.
- PASS: mapping is not connected to `/review/apply`.
- PASS: mapping does not write `output`.
- PASS: mapping does not write `job`.
- PASS: mapping does not write `export`.
- PASS: mapping does not trigger ZBid writeback.
- PASS: mapping is not used as evidence.
- PASS: mapping is not used as scoring.
- PASS: mapping is not connected to RAG.
- PASS: mapping is not connected to prompt registry.
- PASS: mapping is not connected to system instruction registry.
- PASS: mapping is not connected to CI.

## Runtime Boundary Review

KG-RUNTIME-101 did not execute runtime behavior. Source inspection was limited to the authorized files and static git diff/show views.

Static compliance result:

- PASS: no service was run.
- PASS: no port was accessed.
- PASS: no endpoint was called.
- PASS: no real KG file body was read.
- PASS: no real KG JSON was parsed.
- PASS: no directory scan was rerun.
- PASS: no frontend, tests, config, or JSON files were changed.
- PASS: no `.pyc` or `__pycache__` was intentionally created.
- PASS: no Ollama run occurred.
- PASS: no generation, export, or writeback chain was triggered.

## Next Stage Gate

KG-RUNTIME-102 is still required before any controlled smoke authorization decision:

- Required next gate: KG-RUNTIME-102 preview-only adapter mapping frozen audit and controlled smoke authorization gate.
- KG-RUNTIME-101 does not authorize smoke execution.
- KG-RUNTIME-101 does not authorize endpoint calls.
- KG-RUNTIME-101 does not authorize real KG body reads.
- KG-RUNTIME-101 does not authorize real KG JSON parsing.
- KG-RUNTIME-101 does not authorize ZDoc integration.
- KG-RUNTIME-101 does not authorize real-use or trial-use status.

## Final Static Review Conclusion

PASS: KG-RUNTIME-100's preview-only adapter mapping controlled implementation draft remains within the static preview-only, content-safe, no-runtime, no-output-chain, no-generation, no-export, no-writeback, no-evidence, no-scoring, no-RAG, and no-registry boundary.

PASS: KG-RUNTIME-101 is a docs-only static review stage. It does not represent ZDoc KG integration, real usage, trial usage, smoke authorization, or entry into KG-RUNTIME-102.
