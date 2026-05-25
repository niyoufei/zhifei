# KG-RUNTIME-94 no-server in-process response-section remediation re-smoke validation

## Scope

- Stage: KG-RUNTIME-94
- Purpose: validate the KG-RUNTIME-91 response-section remediation through a no-server direct route in-process call.
- Stop line: KG-RUNTIME-95 was not entered.
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Required branch: `main`
- Required start HEAD: `f3082fa366a0beb07469cb1ac2ac1f67f455bf8a`
- Required baseline tag: `v0.1.476-zdoc-kg-response-section-remediation-resmoke-gate`
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`

## Preflight

- `pwd`: `/Users/youfeini/Desktop/文档生成系统`
- `git branch --show-current`: `main`
- `git rev-parse HEAD`: `f3082fa366a0beb07469cb1ac2ac1f67f455bf8a`
- `git status --short`: clean
- Local `v0.1.476-zdoc-kg-response-section-remediation-resmoke-gate` tag: absent.
- Remote baseline tag live verification: not completed. A sandboxed `git ls-remote --tags origin v0.1.476-zdoc-kg-response-section-remediation-resmoke-gate` attempt failed with external SSH network access blocked. Escalating that remote metadata query was rejected because this task forbids broader access. The re-smoke proceeded from the locally verified `main` HEAD and the user-provided remote-tag baseline statement.

## Method

- Used exactly one no-server direct route in-process Python call.
- Used `PYTHONDONTWRITEBYTECODE=1`.
- Did not use TestClient.
- Did not start `uvicorn`.
- Did not bind a TCP port.
- Did not access `127.0.0.1`.
- Did not run `pytest`.
- Did not run `python3 -m json.tool`.
- Did not run `py_compile`.
- Did not run a directory scan.
- Did not read any KG file other than the authorized target.
- Did not read, copy, move, or delete `AI知识图谱大全`.
- Did not modify code, adapter, route, `main.py`, frontend, tests, config, or JSON.

The in-process payload was:

```json
{
  "manual_trigger": true,
  "real_kg_read_only": true,
  "structure_read": true,
  "structural_profile": true,
  "authorized_target": "知识图谱/ZF-KG-12-Municipal-Bridge.json"
}
```

## Validation Result

| Check | Result |
|---|---:|
| Direct route in-process call completed | PASS |
| Route input contract matched required payload | PASS |
| Route returned `ok=true` | PASS |
| Route returned `enabled=true` | PASS |
| Route-to-adapter passthrough check | PASS |
| Route-to-adapter passthrough field count | 22 |
| Returned `structure_read_only` | PASS |
| Returned `structure_summary` | PASS |
| Returned `structure_contract` | PASS |
| Returned `structural_profile_only` | PASS |
| Returned `structural_profile_summary` | PASS |
| Returned `structural_profile_contract` | PASS |
| `structure_summary` whitelist field count | 13 |
| `structure_summary` field set exactly matched whitelist | PASS |
| `structural_profile_summary` whitelist field count | 14 |
| `structural_profile_summary` field set exactly matched whitelist | PASS |
| `module_name_candidates` empty list | PASS |
| `redaction_policy` | `0` safe enum |
| `scalar_full_leaf_overlap_count` | 0 |
| `substring_overlap_count` | 0 |
| Non-empty response string leaf count | 0 |

The re-smoke conclusion is PASS.

## Returned Section Presence

- `structure_read_only`: present and true.
- `structure_summary`: present.
- `structure_contract`: present.
- `structural_profile_only`: present and true.
- `structural_profile_summary`: present.
- `structural_profile_contract`: present.

`structure_summary` returned the 13 allowed fields:

```text
top_level_type
top_level_key_names
top_level_key_count
dict_count
list_count
null_count
scalar_type_counts
selected_structure_paths
list_lengths
field_type_sets
max_depth_limited
authorized_target
allowlist_status
```

`structural_profile_summary` returned the 14 allowed fields:

```text
authorized_target
allowlist_status
profile_enabled
profile_scope
max_depth_limited
path_count
path_type_counts
depth_histogram
field_name_counts
field_type_sets
list_length_buckets
dict_key_count_buckets
module_name_candidates
redaction_policy
```

## Boundary Confirmation

- No business body text was emitted.
- No entity body text was emitted.
- No knowledge-entry body text was emitted.
- No prompt text was emitted.
- No system instruction text was emitted.
- No evidence text was emitted.
- No scoring text was emitted.
- No scalar value content from the authorized KG was emitted.
- No list item content from the authorized KG was emitted.
- No dict value content from the authorized KG was emitted.
- No `/generate` call was triggered.
- No `/export_docx` call was triggered.
- No `/review/apply` call was triggered.
- No ZBid writeback was triggered.
- No output, job, or export write was performed.
- No Ollama call was performed.
- No RAG access was performed.
- No prompt registry access was performed.
- No system instruction registry access was performed.
- No CI connection was performed.

## Cache Observation

- `backend/__pycache__` existed before the re-smoke and had unchanged directory mtime after the re-smoke.
- `backend/app/routers/__pycache__` existed before the re-smoke and had unchanged directory mtime after the re-smoke.
- No route or adapter `.pyc` / `__pycache__` cleanup was needed.

## Files Changed

- Added this docs-only review file:
  - `docs/zdoc-kg-no-server-in-process-response-section-remediation-resmoke-validation-kg-runtime-94-review.md`

No code files were changed.
