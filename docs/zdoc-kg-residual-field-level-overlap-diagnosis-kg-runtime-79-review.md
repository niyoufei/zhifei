# KG-RUNTIME-79 residual field-level overlap diagnosis

## Scope

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `85dc2da8f658ae9b1fbac67c7abb922eec18be0b`
- Baseline tag: `v0.1.461-zdoc-kg-field-overlap-residual-diagnosis-gate`
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- New docs-only file: `docs/zdoc-kg-residual-field-level-overlap-diagnosis-kg-runtime-79-review.md`

KG-RUNTIME-79 is limited to residual substring-overlap field diagnosis. It does not output any concrete overlap hit string, KG scalar value, list item, dict value, business body, entity body, knowledge-entry body, prompt, system instruction, evidence, or scoring.

## In-Process Diagnosis Boundary

- Direct route in-process invocation: yes
- `manual_trigger=true`: yes
- `real_kg_read_only=true`: yes
- `structure_read=true`: yes
- `structural_profile=true`: yes
- Authorized target matched: yes
- uvicorn started: no
- TCP port bound: no
- `127.0.0.1` accessed: no
- Directory scan executed: no
- KG files outside the authorized target read: no
- `AI知识图谱大全` read, copied, moved, or deleted: no
- Code, adapter, route, or `main.py` modified: no
- Frontend, tests, config, or JSON modified: no
- `/generate`, `/export_docx`, `/review/apply`, or ZBid writeback triggered: no
- `output`, `job`, or `export` written: no
- Ollama run: no
- RAG, registry, or CI connected: no

## Residual Diagnosis Summary

| response_field | overlap_count | overlap_type | safe_category |
|---|---:|---|---|
| detail.structure_summary | 1 | substring | placeholder |
| detail.structure_summary | 2 | substring | bucket_label |
| detail.structure_summary | 2 | substring | type_label |
| detail.structural_profile_summary | 1 | substring | bucket_label |
| detail.structural_profile_summary | 1 | substring | field_group |
| detail.structure_contract | 1 | substring | policy_string |
| detail.structural_profile_contract | 1 | substring | policy_string |

## KG-RUNTIME-80 Recommendation

KG-RUNTIME-80 fix is recommended: yes.

Reason: residual substring overlap remains non-zero even though the remaining sources are limited to safe structural output categories and fixed policy strings. KG-RUNTIME-80 should either reduce the residual substring overlap to zero or introduce an explicitly separated safe-category accounting path without emitting any matched content.

KG-RUNTIME-79 stops here and does not enter KG-RUNTIME-80.
