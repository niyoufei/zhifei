# KG-RUNTIME-90 response-section isolation diagnosis

## Scope

- Stage: `KG-RUNTIME-90`
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `b9ee1018479a03aa0cae44b2f86e042b4606a2b2`
- Baseline tag: `v0.1.472-zdoc-kg-guard-field-resmoke-no-go-diagnosis-gate`
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- Review artifact only: `docs/zdoc-kg-response-section-isolation-diagnosis-kg-runtime-90-review.md`

The local baseline tag was not present. The remote baseline tag was verified and pointed to the required start HEAD.

KG-RUNTIME-90 is limited to response-section and field-family level diagnosis of the remaining substring overlap. This review does not include any concrete overlap hit string, KG scalar value, list item, dict value, business body, entity body, knowledge-entry body, prompt, system instruction, evidence, or scoring.

## Boundary

- Code modified: no.
- Adapter, route, or `main.py` modified: no.
- Frontend, tests, config, or JSON modified: no.
- `uvicorn` started: no.
- TCP port bound: no.
- `127.0.0.1` accessed: no.
- Prohibited directory scan command executed: no.
- KG file outside the authorized target read: no.
- `AI知识图谱大全` read, copied, moved, or deleted: no.
- `/generate`, `/export_docx`, `/review/apply`, or ZBid writeback triggered: no.
- `output`, `job`, or `export` written: no.
- Ollama run: no.
- RAG, registry, or CI connected: no.
- Evidence or scoring use: no.

## Diagnostic Call

The completed diagnosis used a no-server direct route in-process Python call with `PYTHONDONTWRITEBYTECODE=1`.

Payload contract:

- `manual_trigger=true`
- `real_kg_read_only=true`
- `structure_read=true`
- `structural_profile=true`
- `authorized_target=知识图谱/ZF-KG-12-Municipal-Bridge.json`

Runtime guard result:

- Direct route in-process call: yes.
- Payload contract matched: yes.
- Authorized KG read count: `1`.
- Unauthorized KG read count: `0`.
- Socket event count: `0`.
- Directory scan event count: `0`.
- Write event count: `0`.
- `127.0.0.1` marker in serialized response: `false`.
- Python bytecode write disabled: `true`.

Execution note: one preliminary Python guard-order attempt failed before route execution, did not complete diagnosis, did not read the KG file, and did not write files. The diagnosis table below comes only from the completed direct route in-process call.

## Strict Overlap Result

| response_section | response_field_family | overlap_count | overlap_type | safe_category |
|---|---|---:|---|---|
| unknown_section | unknown_source | 24 | substring | unknown_source |

## Response-Section Diagnosis Summary

| response_section | response_field_family | overlap_count | overlap_type | safe_category |
|---|---|---:|---|---|
| detail | contract | 1 | substring | contract_code |
| detail | reason | 1 | substring | numeric_code |
| detail | unknown_source | 2 | substring | numeric_code |
| structural_profile_summary | policy | 1 | substring | policy_code |
| structural_profile_summary | summary_field | 4 | substring | numeric_code |
| structure_contract | guard | 1 | substring | boolean_flag |
| structure_contract | policy | 1 | substring | policy_code |
| structure_contract | readonly_flag | 1 | substring | boolean_flag |
| structure_summary | summary_field | 5 | substring | numeric_code |
| structure_summary | summary_field | 2 | substring | short_enum |
| top_level_guard | disabled_flag | 3 | substring | boolean_flag |
| top_level_guard | reason | 2 | substring | numeric_code |

Unattributed overlap count: `0`.

## KG-RUNTIME-91 Recommendation

KG-RUNTIME-91 fix is recommended: yes.

Reason: substring overlap remains non-zero, although this stage only classifies it at response-section, response-field-family, and safe-category level and does not expose matched content.

KG-RUNTIME-90 stops here and does not enter KG-RUNTIME-91.
