# KG-RUNTIME-77 no-server in-process field-level overlap remediation re-smoke validation

## Scope

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `19484287b5872dadb6f9c17534540e75148da7da`
- Expected baseline tag: `v0.1.459-zdoc-kg-field-overlap-remediation-resmoke-gate`
- Authorized KG target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- Mode: no-server direct route in-process validation
- Target review file only: `docs/zdoc-kg-no-server-in-process-field-overlap-remediation-resmoke-validation-kg-runtime-77-review.md`

The local worktree was clean before validation. The local baseline tag was not present. A remote tag lookup was attempted under the existing narrow sandbox and failed with `ssh: connect to host github.com port 22: Operation not permitted`; no full-access permission was requested.

## Payload

The direct in-process route call used this bounded payload shape:

- `manual_trigger=true`
- `real_kg_read_only=true`
- `structure_read=true`
- `structural_profile=true`
- `authorized_target=知识图谱/ZF-KG-12-Municipal-Bridge.json`

## Guardrails

The single Python validation invocation used `PYTHONDONTWRITEBYTECODE=1` and direct route function invocation. During the route call, guards blocked and counted:

- socket bind/connect/create_connection
- directory walk/scandir/glob/rglob
- write-mode file opens
- non-authorized KG file reads

Observed guard counters:

- `socket_event_count=0`
- `scan_event_count=0`
- `write_event_count=0`
- `kg_read_event_count=1`
- `uvicorn_imported=false`
- `python_dont_write_bytecode=true`

## Route and Adapter Result

Validated as true:

- direct route in-process call completed
- route status was `preview_only`
- adapter status was `preview_only`
- route authorized target matched the requested authorized target
- route-to-adapter copied the expected structure/profile fields
- `structure_read_only=true`
- `structure_summary` returned
- `structure_contract` returned
- `structural_profile_only=true`
- `structural_profile_summary` returned
- `structural_profile_contract` returned
- `structure_summary` returned 13 whitelist fields
- `structural_profile_summary` returned 14 whitelist fields
- `module_name_candidates` encoded as an empty list
- `redaction_policy=redacted`
- `scalar_full_leaf_overlap_count=0`

Whitelist field counts:

- `structure_summary_field_count=13`
- `structural_profile_summary_field_count=14`

Overlap counters:

- `source_scalar_string_leaf_count=765`
- `response_scalar_string_count=55`
- `substring_candidate_count_min_len_4=616`
- `scalar_full_leaf_overlap_count=0`
- `substring_overlap_count=9`

## Boundary Result

Validated as true:

- no uvicorn start
- no TCP bind/connect event
- no `127.0.0.1` access event
- no directory scan event during the guarded route call
- no write event
- no output/job/export write flag
- no generate/export_docx/review_apply route flag
- no Ollama call flag
- no RAG allowed flag
- no evidence allowed flag
- no scoring allowed flag
- no frontend, tests, config, JSON, adapter, route, or `main.py` edits

No business body, entity body, knowledge-entry body, prompt content, system-instruction content, evidence content, or scoring content was printed into this review. Only safety counters, metadata field names, and boolean validation results are recorded.

## Conclusion

NO-GO.

Reason: the remediation re-smoke still observed `substring_overlap_count=9`, while the KG-RUNTIME-77 acceptance target requires `substring overlap = 0`.

Per the KG-RUNTIME-77 stop rules, no code was modified, no alternate uvicorn/TCP/pytest path was used, no broader read was performed, and KG-RUNTIME-78 was not entered.
