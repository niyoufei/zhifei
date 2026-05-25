# KG-RUNTIME-73 field-level overlap diagnosis

## Scope

- Repo: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `5366a6672e43a58aa1e8799295d0b22c46441101`
- Baseline tag: `v0.1.454-zdoc-kg-overlap-no-go-field-diagnosis-gate`
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- New docs-only file: `docs/zdoc-kg-field-level-overlap-diagnosis-kg-runtime-73-review.md`

The local baseline tag was not present at HEAD. The remote baseline tag was verified by `git ls-remote origin refs/tags/v0.1.454-zdoc-kg-overlap-no-go-field-diagnosis-gate` and pointed to the required start HEAD.

KG-RUNTIME-73 is limited to field-level and category-level diagnosis of overlap source fields. This document does not include any concrete overlap hit text, KG scalar value, list item content, dict value content, business body content, entity body content, knowledge entry content, prompt content, system instruction content, evidence content, or scoring content.

## Boundary

- No code was modified.
- `backend/kg_read_only_preview_adapter.py` was not modified.
- `backend/app/routers/kg_read_only_preview.py` was not modified.
- `backend/app/main.py` was not modified.
- Frontend, tests, config, and JSON files were not modified.
- uvicorn was not started.
- No TCP port was bound.
- `127.0.0.1` was not accessed.
- pytest was not run.
- `py_compile` was not run.
- `python3 -m json.tool` was not run.
- Ollama was not run.
- RAG, prompt registry, system instruction registry, and CI were not connected.
- `/generate`, `/export_docx`, and `/review/apply` were not triggered.
- No output, job, or export artifact was written.
- No ZBid writeback was triggered.
- `AI知识图谱大全` was not read, copied, moved, or deleted.
- No KG file other than the authorized target was read.

## Diagnostic call

The diagnosis used a single `PYTHONDONTWRITEBYTECODE=1` no-server direct route in-process Python call.

Payload contract:

- `manual_trigger=true`
- `real_kg_read_only=true`
- `structure_read=true`
- `structural_profile=true`
- `authorized_target=知识图谱/ZF-KG-12-Municipal-Bridge.json`

Route result:

- Direct route in-process call: yes
- `ok`: `true`
- `status`: `preview_only`
- `adapter_status`: `preview_only`

Guard result:

- uvicorn imported: `false`
- socket event count: `0`
- directory scan event count: `0`
- write event count: `0`
- authorized KG read count: `1`
- unauthorized KG read count: `0`
- `127.0.0.1` marker in serialized response: `false`

## Overlap totals

- Authorized source scalar string leaf instance count: `5462`
- Response scalar string leaf count: `2877`
- Scalar full leaf overlap count: `0`
- Serialized substring overlap source leaf instance count: `227`

Because the substring overlap count is non-zero, KG-RUNTIME-74 remediation is recommended.

## Field-level diagnosis

The table below reports only response fields, overlap counts, overlap type, and safe output categories. It does not report any matched value.

| response_field | overlap_count | overlap_type | safe_category |
|---|---:|---|---|
| affects_generation | 26 | substring | unknown_source |
| authorized_target | 52 | substring | policy_string |
| detail | 208 | substring | unknown_source |
| endpoint_path | 17 | substring | unknown_source |
| evidence_allowed | 1 | substring | unknown_source |
| kg_runtime_registered | 8 | substring | unknown_source |
| knowledge_pack_load_allowed | 1 | substring | unknown_source |
| manual_trigger_required | 2 | substring | unknown_source |
| no_generation | 26 | substring | unknown_source |
| output_write_allowed | 1 | substring | unknown_source |
| prompt_registry_allowed | 1 | substring | unknown_source |
| rag_allowed | 1 | substring | unknown_source |
| read_policy | 11 | substring | policy_string |
| reason | 14 | substring | policy_string |
| request_id | 18 | substring | unknown_source |
| runtime_access | 8 | substring | unknown_source |
| scoring_allowed | 1 | substring | unknown_source |
| structural_profile_contract.allowlist_status | 18 | substring | unknown_source |
| structural_profile_contract.authorized_target | 52 | substring | unknown_source |
| structural_profile_contract.contract_scope | 17 | substring | unknown_source |
| structural_profile_contract.dict_policy | 64 | substring | policy_string |
| structural_profile_contract.list_policy | 21 | substring | policy_string |
| structural_profile_contract.manual_trigger_required | 2 | substring | unknown_source |
| structural_profile_contract.module_name_policy | 17 | substring | policy_string |
| structural_profile_contract.no_generation | 26 | substring | unknown_source |
| structural_profile_contract.profile_scope | 64 | substring | policy_string |
| structural_profile_contract.redaction_policy | 39 | substring | policy_string |
| structural_profile_contract.scalar_policy | 54 | substring | policy_string |
| structural_profile_contract.summary_field_whitelist | 84 | substring | field_group |
| structural_profile_contract.target_policy | 17 | substring | unknown_source |
| structural_profile_summary.allowlist_status | 18 | substring | unknown_source |
| structural_profile_summary.authorized_target | 52 | substring | unknown_source |
| structural_profile_summary.depth_histogram | 77 | substring | unknown_source |
| structural_profile_summary.dict_key_count_buckets | 101 | substring | bucket_label |
| structural_profile_summary.field_name_counts | 89 | substring | field_group |
| structural_profile_summary.field_type_sets | 80 | substring | field_group |
| structural_profile_summary.list_length_buckets | 47 | substring | bucket_label |
| structural_profile_summary.max_depth_limited | 17 | substring | unknown_source |
| structural_profile_summary.path_count | 70 | substring | unknown_source |
| structural_profile_summary.path_type_counts | 122 | substring | type_label |
| structural_profile_summary.profile_scope | 64 | substring | policy_string |
| structural_profile_summary.redaction_policy | 39 | substring | policy_string |
| structure_contract.allowlist_status | 18 | substring | unknown_source |
| structure_contract.authorized_target | 52 | substring | unknown_source |
| structure_contract.contract_scope | 21 | substring | unknown_source |
| structure_contract.dict_policy | 64 | substring | policy_string |
| structure_contract.list_policy | 21 | substring | policy_string |
| structure_contract.manual_trigger_required | 2 | substring | unknown_source |
| structure_contract.no_generation | 26 | substring | unknown_source |
| structure_contract.scalar_policy | 7 | substring | policy_string |
| structure_contract.summary_field_whitelist | 69 | substring | field_group |
| structure_contract.target_policy | 17 | substring | unknown_source |
| structure_contract.value_output_policy | 75 | substring | policy_string |
| structure_summary.allowlist_status | 18 | substring | unknown_source |
| structure_summary.authorized_target | 52 | substring | unknown_source |
| structure_summary.dict_count | 77 | substring | unknown_source |
| structure_summary.field_type_sets | 80 | substring | field_group |
| structure_summary.list_count | 63 | substring | unknown_source |
| structure_summary.list_lengths | 134 | substring | bucket_label |
| structure_summary.max_depth_limited | 17 | substring | unknown_source |
| structure_summary.null_count | 47 | substring | unknown_source |
| structure_summary.scalar_type_counts | 67 | substring | type_label |
| structure_summary.selected_structure_paths | 97 | substring | path_group |
| structure_summary.top_level_key_count | 47 | substring | unknown_source |
| structure_summary.top_level_key_names | 58 | substring | placeholder |
| system_instruction_registry_allowed | 6 | substring | unknown_source |
| target_policy | 17 | substring | policy_string |
| triggers_export_chain | 17 | substring | unknown_source |
| triggers_generation_chain | 43 | substring | unknown_source |
| value_output_policy | 33 | substring | policy_string |
| writeback_allowed | 1 | substring | unknown_source |

No `scalar_full_leaf` response field had an overlap count greater than `0`.

## Conclusion

KG-RUNTIME-73 completed the field-level overlap diagnosis. The non-zero substring diagnosis is concentrated in safe output categories such as placeholders, buckets, type labels, field groups, path groups, and policy strings, plus route envelope or boundary flag fields categorized as `unknown_source`.

KG-RUNTIME-74 remediation is recommended, but KG-RUNTIME-74 was not entered.
