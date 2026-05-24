# KG-RUNTIME-66 no-server in-process structural-profile remediation re-smoke validation

## Scope

- Repo: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `656b8a970918fab4154962ffc16b99fe613b1062`
- Baseline tag checked remotely: `v0.1.447-zdoc-kg-structural-profile-remediation-resmoke-gate`
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- Next stage boundary: KG-RUNTIME-67 was not entered.

## Method

One no-server in-process Python re-smoke was executed with `PYTHONDONTWRITEBYTECODE=1`.

The call directly invoked `kg_read_only_preview_route` in-process with this required payload contract:

- `manual_trigger=true`
- `real_kg_read_only=true`
- `structure_read=true`
- `structural_profile=true`
- `authorized_target=知识图谱/ZF-KG-12-Municipal-Bridge.json`

The smoke installed a socket guard during the call. Any TCP `bind`, `connect`, `connect_ex`, or `create_connection` attempt would fail the run. It also guarded KG JSON reads so only the authorized target path could be read. The script output only booleans, counts, policy names, and the authorized target path; it did not print KG scalar values, list item contents, dict values, business body text, entity body text, or knowledge entry body text.

## Route and adapter result

- Direct route in-process call completed: yes
- Response status: `preview_only`
- Adapter status: `preview_only`
- `structure_read_only`: returned
- `structure_summary`: returned
- `structure_contract`: returned
- `structural_profile_only`: returned
- `structural_profile_summary`: returned
- `structural_profile_contract`: returned

`structure_summary` returned exactly these 13 whitelist fields:

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

`structural_profile_summary` returned exactly these 14 whitelist fields:

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

Additional structural-profile checks:

- `module_name_candidates` was empty.
- `redaction_policy` matched the fixed policy string:
  `fixed_no_scalar_values_no_list_items_no_dict_values_no_prompt_instruction_evidence_scoring_or_kg_body_text_no_module_candidates`

## Safety and boundary checks

- uvicorn was not imported or started.
- TCP bind attempts: `0`
- TCP connect attempts: `0`
- `127.0.0.1` access attempts: `0`
- KG JSON read paths: only `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- `AI知识图谱大全` was not read, copied, moved, or deleted.
- `/generate`, `/export_docx`, and `/review/apply` were not triggered.
- `output`, `job`, and `export` were not written.
- Ollama was not run.
- RAG, prompt registry, system instruction registry, and CI were not connected.
- Frontend, tests, config, JSON, adapter, route, and `main.py` were not modified.
- No route/adapter `.pyc` or `__pycache__` additions were detected.

The response boundary flags were:

- `no_write=true`
- `no_evidence=true`
- `no_scoring=true`
- `no_rag=true`
- `no_generation=true`
- `no_export=true`
- `no_zbid_writeback=true`

## Content safety result

The controlled safety check compared the serialized route response with scalar string leaves parsed from the single authorized KG file. It did not print or archive any matched scalar values.

- Scalar full leaf overlap count: `8`
- Substring overlap count for content-bearing scalar strings: `6`

Because both required overlap counts must be `0`, the remediation re-smoke is **NO-GO**.

## Conclusion

KG-RUNTIME-66 is completed as a validation/archive task, but the re-smoke result is **NO-GO**.

No code was changed. No workaround using uvicorn, TCP, pytest, broader KG reads, or runtime/service access was attempted. Stop here and wait for the next explicit authorization; KG-RUNTIME-67 was not entered.
