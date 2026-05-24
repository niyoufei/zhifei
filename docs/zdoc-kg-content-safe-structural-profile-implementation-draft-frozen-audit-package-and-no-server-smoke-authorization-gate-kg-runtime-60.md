# KG-RUNTIME-60 content-safe structural profile frozen audit package and no-server smoke authorization gate

## Scope

- Stage: KG-RUNTIME-60.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `32422610e177f4c98a560e0f2d065bcd5e660699`.
- Start baseline tag: `v0.1.441-zdoc-kg-structural-profile-static-review`.
- This stage is docs-only.
- This stage freezes the KG-RUNTIME-58 and KG-RUNTIME-59 structural profile audit package.
- This stage sets the KG-RUNTIME-61 no-server in-process structural-profile smoke authorization gate.
- This stage does not execute KG-RUNTIME-61.

## Static Inputs

Reviewed static inputs for this frozen audit package:

- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`
- `docs/zdoc-kg-content-safe-structural-profile-controlled-implementation-draft-kg-runtime-58-review.md`
- `docs/zdoc-kg-content-safe-structural-profile-implementation-draft-static-compliance-and-no-content-leak-review-kg-runtime-59.md`

Not performed in this stage:

- No adapter, route, or `main.py` modification.
- No frontend, test, config, or JSON modification.
- No real KG file body read.
- No real KG JSON parse.
- No service start.
- No TCP port binding.
- No `127.0.0.1` access.
- No `/health` call.
- No `/kg/read-only-preview` call.
- No `/generate`, `/export_docx`, or `/review/apply` call.
- No ZBid writeback.
- No output, job, or export write.
- No Ollama run.
- No `pytest`.
- No `py_compile`.
- No RAG, prompt registry, system instruction registry, or CI connection.
- No real-use entry.
- No evidence use.
- No scoring use.

## Frozen Results

KG-RUNTIME-58 is frozen as a content-safe structural profile controlled implementation draft.

KG-RUNTIME-59 is frozen as the static compliance and no-content-leak review for that implementation draft.

The structural profile is still in draft status. It has not passed runtime smoke validation. KG-RUNTIME-60 does not convert the draft into a runtime-validated feature, a production-ready feature, an evidence source, or a scoring input.

## Current Structural Profile Gate

The current structural profile gate requires all of the following conditions:

- feature flag enabled;
- `manual_trigger = true`;
- `real_kg_read_only = true`;
- `structure_read = true`;
- `structural_profile = true`;
- `authorized_target = 知识图谱/ZF-KG-12-Municipal-Bridge.json`.

The structural profile reuses the existing controlled `structure_read` path. It does not add a second uncontrolled file-read path, second JSON-parse path, directory scan, batch read, or allowlist expansion.

## Structural Profile Summary Whitelist

`structural_profile_summary` is limited to these fields:

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

No other `structural_profile_summary` field is authorized by this KG-RUNTIME-60 frozen audit package.

## Static No-Content-Leak Boundary

KG-RUNTIME-59 statically confirmed that the structural profile no-content-leak boundary is not broken:

- scalar handling does not output scalar values;
- list handling does not output list element content;
- dict handling does not output dict value content;
- `module_name_candidates` are not derived from body values;
- business body text is not output;
- entity body text is not output;
- knowledge-entry body text is not output;
- prompt content is not output;
- system instruction content is not output;
- evidence content is not output;
- scoring content is not output.

KG-RUNTIME-60 preserves that conclusion as a static frozen-audit conclusion only. It does not prove runtime output against the real KG file because KG-RUNTIME-60 does not run the route, does not call the adapter in-process, does not read the real KG file body, and does not parse the real KG JSON.

## Chain, Registry, Evidence, And Scoring Boundary

Static frozen-audit status:

- The generation chain is not connected.
- The export chain is not connected.
- The writeback chain is not connected.
- ZBid writeback is not connected.
- RAG is not connected.
- Prompt registry is not connected.
- System instruction registry is not connected.
- CI is not connected.
- Structural profile is not evidence.
- Structural profile is not scoring input.

KG-RUNTIME-60 does not authorize using structural profile output in generation, export, writeback, RAG, prompt registry, system instruction registry, CI, evidence, scoring, or real use.

## KG-RUNTIME-61 No-Server Smoke Authorization Gate Draft

KG-RUNTIME-61 may execute no-server in-process structural-profile smoke validation only if KG-RUNTIME-61 is separately authorized in a later stage.

The KG-RUNTIME-61 authorization boundary must be all of the following:

- Do not start `uvicorn`.
- Do not bind any TCP port.
- Do not access `127.0.0.1`.
- Direct route or adapter in-process invocation is allowed.
- If FastAPI `TestClient` is used, it must not create service binding or app startup side effects.
- The payload must set `manual_trigger = true`.
- The payload must set `real_kg_read_only = true`.
- The payload must set `structure_read = true`.
- The payload must set `structural_profile = true`.
- `authorized_target` must strictly equal `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- Only the single authorized target may be read and parsed.
- The only allowed purpose of that read and parse is to generate whitelist `structure_summary`, `structural_profile_summary`, and `structural_profile_contract`.
- No file outside the authorized target may be read.
- No directory scan, batch read, or allowlist expansion is allowed.
- No real business body value may be output.
- No real entity body may be output.
- No real knowledge-entry body may be output.
- No prompt may be output.
- No system instruction may be output.
- No evidence may be output.
- No scoring may be output.
- Do not trigger `/generate`.
- Do not trigger `/export_docx`.
- Do not trigger `/review/apply`.
- Do not write output, job, or export artifacts.
- Do not run Ollama.
- Do not run `pytest`.
- Do not run `py_compile`.
- Do not connect CI.
- Do not enter real-use stage.

KG-RUNTIME-61 must remain a validation-only smoke stage. Passing KG-RUNTIME-61, if later authorized and executed, would still not authorize generation, export, writeback, RAG, registry connection, evidence use, scoring use, CI use, or real use unless a later stage explicitly grants that authority.

## KG-RUNTIME-60 Stop Line

KG-RUNTIME-60 only sets the no-server structural-profile smoke authorization gate.

KG-RUNTIME-60 does not execute smoke validation, does not execute KG-RUNTIME-61, does not run the route, does not call an endpoint, does not call the adapter in-process, does not read real KG body content, and does not parse real KG JSON.

## Conclusion

KG-RUNTIME-60 freezes the KG-RUNTIME-58 content-safe structural profile controlled implementation draft and the KG-RUNTIME-59 static compliance and no-content-leak review.

The structural profile remains a draft pending a separately authorized KG-RUNTIME-61 no-server in-process structural-profile smoke validation.

This document is the only authorized artifact for KG-RUNTIME-60.
