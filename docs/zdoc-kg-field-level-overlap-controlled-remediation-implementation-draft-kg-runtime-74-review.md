# KG-RUNTIME-74 field-level overlap controlled remediation implementation draft review

## 1. Scope

- Stage: KG-RUNTIME-74
- Purpose: form a minimal controlled remediation draft for KG-RUNTIME-73 field-level substring overlap findings.
- Actual modified code file: `backend/kg_read_only_preview_adapter.py`
- Actual modified route file: none
- Actual new review file: `docs/zdoc-kg-field-level-overlap-controlled-remediation-implementation-draft-kg-runtime-74-review.md`
- Scope result: only the authorized adapter file was modified; no route change was required.

## 2. Untouched Surface

- `backend/app/main.py`: not modified.
- Frontend files: not modified.
- Tests: not modified.
- Config files: not modified.
- JSON files: not modified.
- Real KG body content: not read in this stage.
- Real KG JSON: not parsed in this stage.
- Service startup: not run.
- Endpoint calls: not made.
- `pytest`: not run.
- `py_compile`: not run.
- Generation, export, writeback, RAG, registry, and CI: not connected.
- Output/job/export body writing: not performed.
- Ollama: not run.
- Second uncontrolled read path: not added.

## 3. KG-RUNTIME-73 Findings Used

| Response field | KG-RUNTIME-73 overlap count | Overlap type | Safe category | KG-RUNTIME-74 remediation |
|---|---:|---|---|---|
| `structure_summary.top_level_key_names` | 58 | substring | placeholder | Replaced generated key placeholders with an empty tuple; retained `top_level_key_count` for count-only signal. |
| `structure_summary.selected_structure_paths` | 97 | substring | path_group | Replaced placeholder path strings and type labels with a positional numeric summary: path count, depth count pairs, and type-code count pairs. |
| `structure_summary.field_type_sets` | 80 | substring | field_group | Replaced placeholder field/type-set labels with a positional numeric summary: field group count, type-set count, type-code histogram, and group-size bucket counts. |
| `structural_profile_summary.field_name_counts` | 89 | substring | field_group | Replaced named placeholder/count labels with a numeric tuple containing group count, group bucket code, slot count, and slot bucket code. |
| `structural_profile_summary.path_type_counts` | 122 | substring | type_label | Replaced string type labels with numeric type-code count pairs. |
| `structural_profile_summary.field_type_sets` | 80 | substring | field_group | Reused the numeric field/type-set summary from the controlled structure-read output. |
| `structural_profile_summary.redaction_policy` | 39 | substring | policy_string | Replaced the long policy sentence with the fixed short enum value `redacted`. |

## 4. Field Whitelist Preservation

- `structure_summary` still preserves the same 13 whitelist field names:
  `top_level_type`, `top_level_key_names`, `top_level_key_count`, `dict_count`, `list_count`, `null_count`, `scalar_type_counts`, `selected_structure_paths`, `list_lengths`, `field_type_sets`, `max_depth_limited`, `authorized_target`, `allowlist_status`.
- `structural_profile_summary` still preserves the same 14 whitelist field names:
  `authorized_target`, `allowlist_status`, `profile_enabled`, `profile_scope`, `max_depth_limited`, `path_count`, `path_type_counts`, `depth_histogram`, `field_name_counts`, `field_type_sets`, `list_length_buckets`, `dict_key_count_buckets`, `module_name_candidates`, `redaction_policy`.
- `module_name_candidates` remains fixed as an empty tuple.
- No concrete hit values, KG scalar values, list items, dict values, business text, entity body text, knowledge entry body text, prompt text, system instruction text, evidence, or scoring text are introduced by this remediation draft.

## 5. Gate Preservation

The remediation stays inside the existing controlled structure-read path. It does not add a second read path and does not relax the existing gates:

- feature flag enabled
- `manual_trigger = true`
- `real_kg_read_only = true`
- `structure_read = true`
- `structural_profile = true`
- `authorized_target = 知识图谱/ZF-KG-12-Municipal-Bridge.json`

## 6. Result Boundary

- This stage is only a remediation implementation draft.
- This stage cannot be treated as proof that overlap re-smoke has passed.
- KG-RUNTIME-75 is still required for static compliance and no-content-leak review.
- KG-RUNTIME-75 was not entered in this stage.
