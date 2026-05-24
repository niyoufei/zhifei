# KG-RUNTIME-67 structural-profile remediation re-smoke NO-GO frozen audit and overlap-source remediation authorization gate

## Scope

- Repo: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `fe5e693801f67b69d792f037feb19cc25369db87`
- Baseline tag: `v0.1.448-zdoc-kg-structural-profile-remediation-resmoke-validation`
- Stage type: docs-only frozen audit and next-stage authorization gate.
- KG-RUNTIME-67 only freezes the KG-RUNTIME-66 NO-GO result and defines the KG-RUNTIME-68 remediation gate. It does not execute KG-RUNTIME-68.

## KG-RUNTIME-66 frozen result

KG-RUNTIME-66 executed a no-server in-process structural-profile remediation re-smoke.

The KG-RUNTIME-66 conclusion is **NO-GO**.

The KG-RUNTIME-66 validation method stayed inside the no-server boundary:

- uvicorn was not started.
- No TCP port was bound.
- `127.0.0.1` was not accessed.
- The route was invoked directly in-process.

The returned contract fields included:

- `structure_read_only`
- `structure_summary`
- `structure_contract`
- `structural_profile_only`
- `structural_profile_summary`
- `structural_profile_contract`

`structure_summary` returned exactly 13 whitelist fields:

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

`structural_profile_summary` returned exactly 14 whitelist fields:

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

Additional returned invariants:

- `module_name_candidates` was an empty list.
- `redaction_policy` was the fixed strategy string `fixed_no_scalar_values_no_list_items_no_dict_values_no_prompt_instruction_evidence_scoring_or_kg_body_text_no_module_candidates`.

## NO-GO reason

The KG-RUNTIME-66 overlap check did not reach the required zero-overlap result:

- Scalar full leaf overlap: `8`
- Substring overlap: `6`

Because the overlap counts were not `0`, the route response cannot currently be confirmed as fully content-safe.

This document intentionally does not include any overlap hit text, field value, KG value, entity content, or knowledge entry content.

Current gated conclusion:

- The structural-profile remediation smoke must not be treated as passed.
- The route must not enter real-use stage.
- The result must not be used as evidence.
- The result must not be used for scoring.

## Safety boundary audit

KG-RUNTIME-67 preserves the following boundaries:

- No code was modified.
- `backend/kg_read_only_preview_adapter.py` was not modified.
- `backend/app/routers/kg_read_only_preview.py` was not modified.
- `main.py` was not modified.
- No KG file outside the authorized target was read.
- The `AI知识图谱大全` directory was not read, copied, moved, or deleted.
- No generation was triggered.
- No export was triggered.
- No writeback was triggered.
- No `output`, `job`, or `export` artifact was written.
- Ollama was not run.
- `frontend`, `tests`, `config`, and JSON files were not modified.
- RAG was not connected.
- Prompt registry was not connected.
- System instruction registry was not connected.
- CI was not connected.

## KG-RUNTIME-68 authorization gate draft

KG-RUNTIME-68 may proceed only if separately authorized. The allowed next step would be a controlled overlap-source remediation implementation draft.

The KG-RUNTIME-68 authorization boundary must be limited to:

- Only minimal adapter and route changes are allowed.
- The remediation must prioritize fixing the overlap source.
- The 13-field `structure_summary` return must be preserved.
- The 14-field `structural_profile_summary` return must be preserved.
- KG-derived identifiers, path fragments, field-name candidates, and strategy text that may cause overlap must be more strictly redacted.
- `module_name_candidates` must remain fixed as an empty list.
- `redaction_policy` must remain fixed as a strategy string and must not concatenate KG content.
- If field names or path names still trigger overlap, they must be replaced by stable placeholders, counts, type sets, or hash-like non-reversible identifiers.
- Scalar values must not be output.
- List item content must not be output.
- Dict value content must not be output.
- Business body text must not be output.
- Entity body text must not be output.
- Knowledge entry body text must not be output.
- Prompt text must not be output.
- System instruction text must not be output.
- Evidence must not be output.
- Scoring must not be output.
- uvicorn must not be started.
- TCP ports must not be bound.
- `127.0.0.1` must not be accessed.
- `pytest` must not be run.
- `py_compile` must not be run.
- Ollama must not be run.
- Generation must not be triggered.
- Export must not be triggered.
- Writeback must not be triggered.
- `output`, `job`, and `export` artifacts must not be written.
- RAG must not be connected.
- Prompt registry must not be connected.
- System instruction registry must not be connected.
- CI must not be connected.
- The route must not enter real-use stage.

KG-RUNTIME-67 stops at this frozen audit and authorization gate. It does not perform remediation and does not enter KG-RUNTIME-68.
