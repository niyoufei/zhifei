# KG-RUNTIME-80 residual field-level overlap controlled remediation draft review

## Scope

- Stage: KG-RUNTIME-80
- Purpose: implementation draft only
- Base source: KG-RUNTIME-79 residual field-level overlap diagnosis supplied for this task
- Authorized target gate remains: `知识图谱/ZF-KG-12-Municipal-Bridge.json`

## Actual Changes

- Modified file:
  - `backend/kg_read_only_preview_adapter.py`
- Added file:
  - `docs/zdoc-kg-residual-field-level-overlap-controlled-remediation-implementation-draft-kg-runtime-80-review.md`
- Route file changed: no
- Only authorized adapter or route files changed: yes, adapter only
- `backend/app/main.py` changed: no
- Frontend changed: no
- Tests changed: no
- Config changed: no
- JSON changed: no

## Execution Boundary

- Real KG body read during this stage: no
- Real KG JSON parse during this stage: no
- Service run: no
- Endpoint call: no
- `/health` call: no
- `/kg/read-only-preview` call: no
- `pytest` run: no
- `py_compile` run: no
- Ollama run: no
- Directory scan rerun: no
- Generate/export/writeback triggered: no
- Output/job/export write: no
- RAG, prompt registry, system instruction registry, or CI integration added: no
- Concrete KG scalar value, list item, dict value, business body, entity body, knowledge entry body, prompt, system instruction, evidence, or scoring output added: no

## KG-RUNTIME-79 Residual Sources

- `detail.structure_summary`
  - placeholder overlap count: 1
  - bucket_label overlap count: 2
  - type_label overlap count: 2
- `detail.structural_profile_summary`
  - bucket_label overlap count: 1
  - field_group overlap count: 1
- `detail.structure_contract`
  - policy_string overlap count: 1
- `detail.structural_profile_contract`
  - policy_string overlap count: 1

## Remediation Mapping

- `detail.structure_summary` placeholder source:
  - Removed string placeholder list-group output.
  - Replaced placeholder-keyed mapping with non-string tuple entries using numeric group id.
- `detail.structure_summary` bucket_label source:
  - Replaced string bucket labels with numeric bucket codes.
  - Removed obsolete string bucket helper from the controlled structure summary path.
- `detail.structure_summary` type_label source:
  - Replaced top-level type label with numeric type code.
  - Replaced scalar type count labels with numeric type-code count pairs.
  - Replaced list element type labels with numeric type-code count pairs.
- `detail.structural_profile_summary` bucket_label source:
  - Replaced list length bucket labels with numeric bucket-code count pairs.
- `detail.structural_profile_summary` field_group source:
  - Replaced long profile scope text with numeric scope code.
  - Kept field-group-like values as numeric counts and numeric group codes only.
- `detail.structure_contract` policy_string source:
  - Replaced long policy string values with numeric policy codes.
- `detail.structural_profile_contract` policy_string source:
  - Replaced long policy string values with numeric policy codes.
  - Kept `redaction_policy` as the short fixed value `redacted`.

## Contract Preservation

- `structure_read_only` still returned by the existing controlled path: yes
- `structure_summary` still returned by the existing controlled path: yes
- `structure_contract` still returned by the existing controlled path: yes
- `structural_profile_only` still returned by the existing controlled path: yes
- `structural_profile_summary` still returned by the existing controlled path: yes
- `structural_profile_contract` still returned by the existing controlled path: yes
- `structure_summary` 13 field names preserved: yes
- `structural_profile_summary` 14 field names preserved: yes
- `structure_contract` preserved while reducing policy string content: yes
- `structural_profile_contract` preserved while reducing policy string content: yes
- `module_name_candidates` remains fixed to an empty list: yes
- Second uncontrolled read path added: no
- Existing gates remain required together:
  - feature flag enabled
  - `manual_trigger = true`
  - `real_kg_read_only = true`
  - `structure_read = true`
  - `structural_profile = true`
  - `authorized_target` strictly equals `知识图谱/ZF-KG-12-Municipal-Bridge.json`

## Remaining Gate

- KG-RUNTIME-81 is still required for static compliance and no-content-leak review.
- This stage is only a remediation implementation draft.
- This stage cannot be treated as a passed residual overlap re-smoke.
