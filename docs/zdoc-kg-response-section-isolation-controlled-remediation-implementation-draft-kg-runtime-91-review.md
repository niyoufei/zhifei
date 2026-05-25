# KG-RUNTIME-91 response-section isolation controlled remediation implementation draft review

## Scope

- Stage: KG-RUNTIME-91
- Result type: controlled remediation implementation draft only.
- Actual modified code files:
  - `backend/kg_read_only_preview_adapter.py`
  - `backend/app/routers/kg_read_only_preview.py`
- Actual added review file:
  - `docs/zdoc-kg-response-section-isolation-controlled-remediation-implementation-draft-kg-runtime-91-review.md`
- Only authorized adapter / route files were modified: yes.
- `backend/app/main.py` modified: no.
- `frontend` / `tests` / `config` / JSON modified: no.

## Non-Execution Record

- Actual real KG body read performed in this stage: no.
- Actual real KG JSON parse performed in this stage: no.
- Service run: no.
- Endpoint call: no.
- `pytest` run: no.
- `py_compile` run: no.
- Directory scan re-run: no.
- Generated body / export / writeback triggered: no.
- RAG / prompt registry / system instruction registry / CI connected: no.
- Concrete hit strings, KG values, entity body text, or knowledge entry body text output: no.

## KG-RUNTIME-90 Residual Sections Used As Basis

KG-RUNTIME-90 diagnosed residual substring overlap count: 24.

Residual response sections used as the implementation basis:

- `detail`
- `structural_profile_summary`
- `structure_contract`
- `structure_summary`
- `top_level_guard`

This review does not record concrete hit strings or KG values.

## Remediation Draft

`detail` section:

- Adapter `status` is reduced to fixed numeric status codes.
- Adapter `source` is reduced to a numeric source code.
- Adapter `authorized_target` response value is reduced to a numeric target code while preserving the existing gate comparison path.
- Adapter `allowlist_status` response values are reduced to numeric status codes.
- Guard / reason / policy / readonly / disabled-class indicators remain numeric or boolean.

`top_level_guard` section:

- Route `status` is reduced to fixed numeric status codes.
- Route `source`, `route_name`, `endpoint_path`, and `feature_flag` response values are reduced to numeric guard codes.
- Route reason output remains numeric.
- Route adapter aggregation now trusts the adapter `ok` boolean instead of comparing a natural-language status string.

`structure_contract` section:

- The section is still returned.
- `authorized_target` and `allowlist_status` response values are reduced to numeric codes.
- `summary_field_whitelist` value is reduced from field-name strings to numeric field codes.
- Contract / policy / guard flags remain numeric or boolean.

`structural_profile_contract` section:

- The section is still returned.
- `authorized_target` and `allowlist_status` response values are reduced to numeric codes.
- `summary_field_whitelist` value is reduced from field-name strings to numeric field codes.
- `redaction_policy` is reduced to a short numeric safe enum.
- Contract / policy / guard flags remain numeric or boolean.

`structure_summary` / `structural_profile_summary` field families:

- `structure_summary` still preserves the 13 required field names.
- `structural_profile_summary` still preserves the 14 required field names.
- Summary target and allowlist values are numeric codes.
- Summary field groups remain non-string structures such as numeric tuples, booleans, empty tuples, and empty lists.
- `module_name_candidates` remains an empty list.
- `redaction_policy` remains present as a short safe enum.

## Path Control

- The existing controlled structure-read path is reused.
- No second uncontrolled read path was added.
- The gate conditions remain centered on feature flag, manual trigger, read-only mode, structure read, structural profile, and the single authorized target comparison.
- This stage did not execute the read path.

## Stage Boundary

- This is only a remediation draft.
- It cannot be treated as a response-section overlap re-smoke pass.
- KG-RUNTIME-92 is still required for static compliance and no-content-leak review.
- KG-RUNTIME-92 was not entered in this stage.
