# KG-RUNTIME-71 no-server in-process structural-profile overlap remediation re-smoke validation

## Scope

- Repo: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `82307cb6fcb1c234b79f832fb502586ef2a504d6`
- Baseline tag: `v0.1.452-zdoc-kg-structural-profile-overlap-resmoke-gate`
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- New docs-only file: `docs/zdoc-kg-no-server-in-process-structural-profile-overlap-remediation-resmoke-validation-kg-runtime-71-review.md`

The local baseline tag was not present. The remote baseline tag was verified by `git ls-remote origin refs/tags/v0.1.452-zdoc-kg-structural-profile-overlap-resmoke-gate` and pointed to the required start HEAD.

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
- Ollama was not run.
- RAG, prompt registry, system instruction registry, and CI were not connected.
- `/generate`, `/export_docx`, and `/review/apply` were not triggered.
- No output, job, or export artifact was written.
- No ZBid writeback was triggered.
- `AI知识图谱大全` was not read, copied, moved, or deleted.
- No KG file other than the authorized target was read.

The successful validation used `PYTHONDONTWRITEBYTECODE=1` and a direct in-process route call. Two preliminary harness attempts aborted before any KG JSON read because the guard was placed too early: one blocked `asyncio.run()` local `socketpair()` setup, and one affected FastAPI import-time socket class use. Neither preliminary attempt produced a validation result or read the authorized KG file.

## Payload

The successful direct route invocation used the required gated payload:

- `manual_trigger=true`
- `real_kg_read_only=true`
- `structure_read=true`
- `structural_profile=true`
- `structural_profile_only=true`
- `authorized_target=知识图谱/ZF-KG-12-Municipal-Bridge.json`

The route response preserved the request id and returned adapter status through the route response chain.

## Route Result

- Direct route in-process call: yes
- `ok`: `true`
- `status`: `preview_only`
- `adapter_status`: `preview_only`
- `reason`: `adapter_preview_ready`
- KG JSON read paths: only `知识图谱/ZF-KG-12-Municipal-Bridge.json`
- uvicorn imported before route call: `false`
- uvicorn imported after route call: `false`
- TCP/socket guard events during route call: `0`
- `127.0.0.1` marker in serialized response: `false`

Returned structural fields:

- `structure_read_only`: `true`
- `structure_summary`: present
- `structure_contract`: present
- `structural_profile_only`: `true`
- `structural_profile_summary`: present
- `structural_profile_contract`: present

Whitelist checks:

- `structure_summary` field count: `13`
- `structure_summary` exact whitelist match: yes
- `structural_profile_summary` field count: `14`
- `structural_profile_summary` exact whitelist match: yes
- `module_name_candidates`: empty JSON list
- `redaction_policy`: fixed policy string matched

Runtime boundary flags from the route response:

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`
- `calls_ollama=false`
- `no_write=true`
- `no_evidence=true`
- `no_scoring=true`
- `no_rag=true`
- `no_generation=true`
- `no_export=true`
- `no_zbid_writeback=true`
- `prompt_registry_allowed=false`
- `system_instruction_registry_allowed=false`

## Content Safety Result

The controlled check compared the serialized route response with non-empty scalar string leaves captured from the single authorized KG parse. It did not print, copy, or archive any KG scalar value, matched hit text, list item content, dict value content, business body text, entity body text, knowledge entry body text, prompt text, system instruction text, evidence text, or scoring text.

- Authorized source scalar string leaf count: `765`
- Response scalar string leaf count: `148`
- Scalar full leaf overlap count: `0`
- Substring overlap count: `27`

Because substring overlap must be `0`, the KG-RUNTIME-71 re-smoke result is **NO-GO**.

## Pycache

The validation used `PYTHONDONTWRITEBYTECODE=1`. Existing route/adapter cache files were observed before validation, and `git status --short` remained clean before this review file was added. No route/adapter `.pyc` or `__pycache__` additions were detected from this run.

## Conclusion

KG-RUNTIME-71 is completed as a no-server in-process re-smoke validation and archival task, but the result is **NO-GO** because substring overlap was not `0`.

No code remediation was attempted. No uvicorn, TCP, pytest, broader KG read, real-use path, generation, export, writeback, Ollama, RAG, registry, or CI workaround was attempted.

Stop here. KG-RUNTIME-72 was not entered.
