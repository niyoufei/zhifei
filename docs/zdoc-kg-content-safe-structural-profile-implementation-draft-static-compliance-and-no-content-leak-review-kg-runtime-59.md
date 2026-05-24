# KG-RUNTIME-59 structural profile static compliance and no-content-leak review

## Scope

- Stage: KG-RUNTIME-59.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `8d1694c8a4f2fd532fd980364b9f798ae768d624`.
- Start baseline tag: `v0.1.440-zdoc-kg-content-safe-structural-profile-draft`.
- Review target: KG-RUNTIME-58 content-safe structural profile controlled implementation draft.
- This stage is a docs-only static compliance review.
- This stage does not enter KG-RUNTIME-60.

## Static Review Inputs

Reviewed static inputs:

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`
- `docs/zdoc-kg-content-safe-structural-profile-controlled-implementation-draft-kg-runtime-58-review.md`
- `git diff --name-only HEAD~1 HEAD`

Not performed in this stage:

- No service start.
- No port access.
- No `/health` call.
- No `/kg/read-only-preview` call.
- No `/generate`, `/export_docx`, or `/review/apply` call.
- No pytest.
- No py_compile.
- No `python3 -m json.tool`.
- No Ollama run.
- No real KG file body read.
- No real KG JSON parse.
- No output, job, or export write.

## Modified File Scope

Static diff review shows KG-RUNTIME-58 changed only:

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`
- `docs/zdoc-kg-content-safe-structural-profile-controlled-implementation-draft-kg-runtime-58-review.md`

Compliance result:

- PASS: KG-RUNTIME-58 code changes are limited to the authorized adapter and route files.
- PASS: KG-RUNTIME-58 added only its review document outside those code files.
- PASS: `backend/app/main.py` is not modified by KG-RUNTIME-58.
- PASS: `frontend` is not modified by KG-RUNTIME-58.
- PASS: `tests` is not modified by KG-RUNTIME-58.
- PASS: `config` is not modified by KG-RUNTIME-58.
- PASS: JSON files are not modified by KG-RUNTIME-58.

## Added Structural Profile Surface

KG-RUNTIME-58 adds or forwards the following structural profile surface:

- `structural_profile`
- `structural_profile_only`
- `structural_profile_summary`
- `structural_profile_contract`

Compliance result:

- PASS: the new surface is explicit and confined to the adapter and route response/request handling.
- PASS: no generation, export, writeback, evidence, scoring, RAG, prompt registry, or system instruction registry surface is added.

## Structural Profile Gate Review

The structural profile path is statically gated by all of the following:

- feature flag enabled through `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED`.
- `manual_trigger = true`.
- `real_kg_read_only = true`.
- `structure_read = true`.
- `structural_profile = true`.
- `authorized_target` strictly equal to `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

Compliance result:

- PASS: the route blocks disabled feature flag before adapter execution.
- PASS: the route blocks missing or non-true `manual_trigger`.
- PASS: the route blocks structural profile without `real_kg_read_only = true`.
- PASS: the route blocks structural profile without `structure_read = true`.
- PASS: the route blocks structural profile without `authorized_target`.
- PASS: the adapter rejects any target other than `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- PASS: the adapter repeats the structural profile requirements before returning structural profile output.

## Read Path And Auto-Read Boundary

Static review result:

- PASS: KG-RUNTIME-58 reuses the existing controlled `structure_read` summary path.
- PASS: KG-RUNTIME-58 does not add a second uncontrolled file-read path for structural profile.
- PASS: KG-RUNTIME-58 does not read a file at import time.
- PASS: KG-RUNTIME-58 does not auto-read a file during service startup.
- PASS: KG-RUNTIME-58 does not add directory scanning, batch reading, or allowlist expansion.
- PASS: the only authorized target remains `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

Important boundary note:

- The implementation draft still contains the already controlled structure-read path that would open and JSON-parse the single authorized target only if the route is called with every required gate enabled.
- KG-RUNTIME-59 did not execute that path, did not read real KG body content, and did not parse real KG JSON.

## Structural Profile Summary Whitelist

`structural_profile_summary` is statically limited to:

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

Compliance result:

- PASS: no additional structural profile summary fields are introduced.
- PASS: the adapter uses the structural profile summary builder instead of returning `structure_summary` in the structural profile response.

## No-Content-Leak Review

Static content-safety rules observed in the KG-RUNTIME-58 draft:

- Scalar handling outputs type and count only; scalar values are not output.
- List handling outputs length buckets and type summaries only; list item content is not output.
- Dict handling outputs key names, key counts, and type sets only; dict values are not output.
- `module_name_candidates` are derived from field names or path names only, not from scalar values, list item content, or dict value content.
- Structural profile output does not include business body text.
- Structural profile output does not include entity body text.
- Structural profile output does not include knowledge-entry body text.
- Structural profile output does not include prompt content.
- Structural profile output does not include system instruction content.
- Structural profile output does not include evidence content.
- Structural profile output does not include scoring content.

Compliance result:

- PASS: static review found no scalar value output in `structural_profile_summary`.
- PASS: static review found no list element content output in `structural_profile_summary`.
- PASS: static review found no dict value content output in `structural_profile_summary`.
- PASS: static review found no prompt, system instruction, evidence, scoring, generation-ready, export-ready, or RAG-ready text output path in the structural profile summary.
- PASS: static review found no content-leak boundary break in KG-RUNTIME-58.

Residual boundary:

- This is a static review only. It does not prove runtime output against the real KG file because KG-RUNTIME-59 did not run the route or read/parse the real KG file.

## Chain, Registry, Evidence, Scoring, And Hook Boundary

Compliance result:

- PASS: no generation chain connection is added.
- PASS: no export chain connection is added.
- PASS: no writeback chain connection is added.
- PASS: no ZBid writeback is added.
- PASS: no RAG connection is added.
- PASS: no prompt registry connection is added.
- PASS: no system instruction registry connection is added.
- PASS: structural profile is not added as evidence.
- PASS: structural profile is not added as scoring input.
- PASS: no new runtime entrypoint is added.
- PASS: no background task is added.
- PASS: no automatic loading is added.
- PASS: no automatic registration is added.
- PASS: no test hook is added.
- PASS: no CI hook is added.

## KG-RUNTIME-60 Gate

KG-RUNTIME-60 is still required before any structural profile runtime validation or real-use authorization.

KG-RUNTIME-60 must remain a separately authorized gate for frozen audit and structural profile smoke review. KG-RUNTIME-59 does not grant permission to run the route, access a port, parse the real KG JSON, or validate the real structural profile output.

## Conclusion

KG-RUNTIME-59 static review is complete.

Based on static review only, KG-RUNTIME-58 remains within the controlled content-safe structural profile draft boundary:

- structure-only output surface;
- metadata-like profile summary only;
- single authorized target;
- manual trigger and feature flag gates;
- no import-time read;
- no service-start auto-read;
- no uncontrolled second read path;
- no directory scan or batch read;
- no generation, export, writeback, evidence, scoring, RAG, registry, test, or CI connection;
- no observed structural profile summary path that outputs scalar values, list item content, dict value content, prompt content, system instruction content, evidence content, scoring content, or business/entity/knowledge-entry body text.

This review does not mean the structural profile feature has passed runtime validation. KG-RUNTIME-59 is static only, and KG-RUNTIME-60 is still required for any authorized frozen audit and structural profile smoke gate.
