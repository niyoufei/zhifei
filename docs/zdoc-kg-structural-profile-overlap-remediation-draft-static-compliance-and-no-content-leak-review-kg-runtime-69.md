# KG-RUNTIME-69 structural-profile overlap remediation draft static compliance and no-content-leak review

## Scope

- Stage: KG-RUNTIME-69
- Target: ZDoc KG structural-profile overlap-source remediation implementation draft static compliance and no-content-leak review
- Baseline HEAD: `94fa11d6d1940cd3d3a94608da4a1867bbd4a883`
- Baseline tag: `v0.1.450-zdoc-kg-structural-profile-overlap-remediation-draft`
- Review-only target file: `backend/kg_read_only_preview_adapter.py`
- Existing route file reviewed read-only: `backend/app/routers/kg_read_only_preview.py`
- Prior KG-RUNTIME-68 review document reviewed read-only: `docs/zdoc-kg-structural-profile-overlap-source-controlled-remediation-implementation-draft-kg-runtime-68-review.md`
- New tag target: `v0.1.451-zdoc-kg-structural-profile-overlap-remediation-static-review`

## Static review method

- Used static git/code/document inspection only.
- Did not read real KG file body content.
- Did not parse real KG JSON.
- Did not run service, bind TCP port, access `127.0.0.1`, call `/health`, or call `/kg/read-only-preview`.
- Did not run `pytest`, `py_compile`, `python3 -m json.tool`, Ollama, CI, generation, export, writeback, RAG, prompt registry, or system instruction registry.
- Did not write output, job, export, generated document body, evidence, or scoring artifacts.

## File-scope compliance

- KG-RUNTIME-68 HEAD file list contains one implementation code file and one review document:
  - `backend/kg_read_only_preview_adapter.py`
  - `docs/zdoc-kg-structural-profile-overlap-source-controlled-remediation-implementation-draft-kg-runtime-68-review.md`
- Static review result: the KG-RUNTIME-68 implementation code change was limited to the authorized adapter file.
- `backend/app/routers/kg_read_only_preview.py` was not modified by KG-RUNTIME-68.
- `backend/app/main.py` was not modified by KG-RUNTIME-68.
- No frontend files were modified.
- No tests were modified.
- No config files were modified.
- No JSON files were modified.

## Whitelist compliance

- `structure_summary` still uses the 13-field whitelist and the field count was not expanded:
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
- `structural_profile_summary` still uses the 14-field whitelist and the field count was not expanded:
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
- The `structural_profile=true` response shape still includes:
  - `structure_read_only`
  - `structure_summary`
  - `structure_contract`
  - `structural_profile_only`
  - `structural_profile_summary`
  - `structural_profile_contract`

## No-content-leak review

- `top_level_key_names` was remediated to placeholder key ids such as `key_001`; it is no longer real top-level KG key output.
- `selected_structure_paths` was remediated to placeholder path ids such as `path_001` plus depth and JSON type metadata; it is no longer real KG path segment output.
- `list_lengths` was remediated to placeholder list groups plus length, length bucket, and element type counts; it does not output list item content.
- `field_type_sets` was remediated to placeholder field groups and placeholder type-set ids; it no longer uses real field names or real path names as keys.
- `field_name_counts` was remediated to aggregate field-group and field-slot counts plus buckets; it no longer outputs real field names.
- `path_type_counts` is derived from placeholder path metadata and type names only; it does not output real paths.
- `module_name_candidates` remains fixed as an empty tuple/list-compatible value.
- `redaction_policy` remains a fixed policy string and does not concatenate KG content.
- The remediation draft does not derive output strings from scalar values, list item values, or dict values.
- The remediation draft does not output scalar values, list item content, or dict value content.
- The remediation draft does not output business body text, entity body text, knowledge entry body text, prompts, system instructions, evidence, or scoring text.

## Read-path and runtime boundary review

- The remediation draft continues to reuse the existing controlled `structure_read` path.
- No second uncontrolled file-read path was added.
- No import-time file read was added.
- No service-start auto-read was added.
- No directory scan, batch read, or allowlist expansion was added.
- KG-RUNTIME-69 did not actually read real KG file body content.
- KG-RUNTIME-69 did not actually parse real KG JSON.
- KG-RUNTIME-69 did not run service, access ports, or call endpoints.
- KG-RUNTIME-69 did not run `pytest`, `py_compile`, or Ollama.
- KG-RUNTIME-69 did not connect the draft to generation, export, or writeback chains.
- KG-RUNTIME-69 did not connect the draft to RAG, prompt registry, or system instruction registry.
- KG-RUNTIME-69 did not use the draft as evidence or scoring.

## Required next gate

- KG-RUNTIME-70 is still required for overlap remediation frozen audit and no-server re-smoke authorization gate.
- KG-RUNTIME-69 is only a static compliance and no-content-leak review.
- KG-RUNTIME-69 does not represent or claim that overlap remediation smoke has passed.

## Static conclusion

- Static compliance review result: passed for the KG-RUNTIME-68 remediation draft boundary.
- No-content-leak review result: no static boundary break found in the KG-RUNTIME-68 remediation draft.
- Runtime/smoke status: not executed and not passed in this stage.
