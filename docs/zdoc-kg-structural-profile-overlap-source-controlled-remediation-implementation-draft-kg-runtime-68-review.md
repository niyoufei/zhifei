# KG-RUNTIME-68 structural-profile overlap-source controlled remediation implementation draft review

## Scope

- Stage: KG-RUNTIME-68
- Target: ZDoc KG structural-profile overlap-source controlled remediation implementation draft
- Baseline HEAD: `1cba3dbaec2e25c276a65cd30df3769792cebf8b`
- Baseline tag: `v0.1.449-zdoc-kg-structural-profile-overlap-no-go-gate`
- New tag target: `v0.1.450-zdoc-kg-structural-profile-overlap-remediation-draft`

## Actual files

- Modified code file: `backend/kg_read_only_preview_adapter.py`
- Modified route file: none
- Added review document: `docs/zdoc-kg-structural-profile-overlap-source-controlled-remediation-implementation-draft-kg-runtime-68-review.md`

## Authorization boundary review

- Only the authorized adapter file was modified.
- `backend/app/routers/kg_read_only_preview.py` was not modified.
- `backend/app/main.py` was not modified.
- No frontend files were modified.
- No tests were modified.
- No config files were modified.
- No JSON files were modified.
- No real KG file body content was actually read during this stage.
- No real KG JSON was actually parsed during this stage.
- No service was run.
- No endpoint was called.
- No TCP port was bound.
- No `pytest` run was performed.
- No `py_compile` run was performed.
- No Ollama run was performed.
- No generation, export, writeback, RAG, registry, or CI integration was added.
- No output, job, or export artifact was written.

## Remediation draft review

- Fix point 1: `structure_summary` still uses the existing 13-field whitelist, and `structural_profile_summary` still uses the existing 14-field whitelist.
- Fix point 2: overlap-prone values are now reduced before response output:
  - `top_level_key_names` returns fixed placeholders such as `key_001`, not real top-level KG keys.
  - `selected_structure_paths` returns placeholder path ids such as `path_001` plus depth/type metadata, not real path segments.
  - `list_lengths` returns placeholder list groups plus length, length bucket, and element type counts, not list path names or item content.
  - `field_type_sets` returns placeholder field groups and placeholder type-set ids, not real field names or path names.
  - `field_name_counts` is reduced to fixed count and count-bucket keys, not real field names.
  - `path_type_counts`, `depth_histogram`, `list_length_buckets`, and `dict_key_count_buckets` remain count/type/bucket outputs.
- Fix point 3: `module_name_candidates` remains fixed as an empty tuple/list-compatible value.
- Fix point 4: `redaction_policy` remains a fixed policy string and does not concatenate KG content.
- The draft continues to reuse the existing controlled structure-read path and does not add a second uncontrolled read path.
- The structural-profile gated response shape remains: `structure_read_only`, `structure_summary`, `structure_contract`, `structural_profile_only`, `structural_profile_summary`, and `structural_profile_contract`.

## Remaining gate

- KG-RUNTIME-69 is still required for independent static compliance and no-content-leak review.
- This stage is only a remediation implementation draft.
- This document does not claim that structural-profile smoke has passed.
