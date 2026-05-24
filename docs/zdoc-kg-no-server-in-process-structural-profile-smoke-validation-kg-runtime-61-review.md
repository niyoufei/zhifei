# KG-RUNTIME-61 ZDoc KG no-server in-process structural-profile smoke validation review

## Scope

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `e3b823dcd7420dbfb7d8dc7748c18f3676ccd10a`
- Start baseline tag: `v0.1.442-zdoc-kg-structural-profile-smoke-authorization-gate`
- Remote baseline tag check: `e3b823dcd7420dbfb7d8dc7748c18f3676ccd10a refs/tags/v0.1.442-zdoc-kg-structural-profile-smoke-authorization-gate`
- Local baseline tag check: local tag was absent.
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`

## Boundary

- No `uvicorn` was started.
- No TCP port was bound by this task.
- No `127.0.0.1` URL was used or accessed.
- No `/generate`, `/export_docx`, or `/review/apply` route was triggered.
- No output, job, or export artifact was written.
- No Ollama command was run.
- No RAG, prompt registry, system instruction registry, or CI path was connected.
- No frontend, tests, config, JSON, adapter, route, or `main.py` file was modified.
- No KG file other than `知识图谱/ZF-KG-12-Municipal-Bridge.json` was read.
- `AI知识图谱大全` was not read, copied, moved, or deleted.

## Invocation

One no-server Python in-process smoke invocation was executed with:

- `PYTHONDONTWRITEBYTECODE=1`
- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`
- direct async route function call: `kg_read_only_preview_route(payload)`
- route path under validation: `/kg/read-only-preview`
- route-to-adapter chain: route response included adapter detail source `kg_runtime_39_real_kg_route_read_only_draft`

Payload keys:

- `authorized_target`
- `manual_trigger`
- `real_kg_read_only`
- `request_id`
- `structural_profile`
- `structure_read`

Payload gate values:

- `manual_trigger = true`
- `real_kg_read_only = true`
- `structure_read = true`
- `structural_profile = true`
- `authorized_target = 知识图谱/ZF-KG-12-Municipal-Bridge.json`

## Smoke Result

Overall result: **NO-GO**.

The route call completed in-process and returned `status = preview_only` with `adapter_status = preview_only`, but the KG-RUNTIME-61 validation did not pass.

Returned field checks:

- `structure_read_only`: returned
- `structure_summary`: **not returned**
- `structural_profile_only`: returned
- `structural_profile_summary`: returned
- `structural_profile_contract`: returned

Whitelist checks:

- Expected `structure_summary` whitelist field count: `13`
- Returned `structure_summary` field count: `0`
- Expected `structural_profile_summary` whitelist field count: `14`
- Returned `structural_profile_summary` field count: `14`
- Returned `structural_profile_summary` keys:
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

Content-safety checks:

- Exact authorized KG scalar string leaf overlap count: `0`
- Authorized KG scalar string substring overlap count: `4`
- `module_name_candidates` count: `3`
- `module_name_candidates` were sourced from field or path names only in the returned structural profile summary check.

Runtime boundary checks from the route response:

- Side-effect false field count checked: `27`
- Side-effect flags were all false.
- Required read-only flags were true.

Validation failures:

- `structure_summary_returned`
- `structure_summary_exact_whitelist`
- `no_authorized_kg_scalar_string_substring_output`

## Pycache Check

Before the smoke, existing route/adapter cache files were present:

- `backend/app/routers/__pycache__/kg_read_only_preview.cpython-313.pyc`
- `backend/__pycache__/kg_read_only_preview_adapter.cpython-313.pyc`

After the smoke, the same route/adapter cache path list was present. The smoke was run with `PYTHONDONTWRITEBYTECODE=1`; no new route/adapter cache path was identified and no cache cleanup was performed.

## Decision

KG-RUNTIME-61 did not pass validation because the structural-profile route path returned `structural_profile_summary` and `structural_profile_contract` without returning `structure_summary`, and the content-safety substring check reported four potential authorized-KG scalar string substring overlaps.

No code was modified. Per the failure rule, this review records the blocking facts only and does not attempt an in-place fix, uvicorn fallback, TCP fallback, pytest fallback, broader KG read, or KG-RUNTIME-62 continuation.
