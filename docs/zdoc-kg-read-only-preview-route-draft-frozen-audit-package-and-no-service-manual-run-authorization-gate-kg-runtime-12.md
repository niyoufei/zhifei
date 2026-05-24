# ZDoc KG Read-Only Preview Route Draft Frozen Audit Package And No-Service Manual Run Authorization Gate KG-RUNTIME-12

## 1. Execution Summary

KG-RUNTIME-12 is a docs-only frozen audit package and first manual run
authorization gate for the KG read-only preview route draft. This step does not
modify code, does not run services, does not access ports, does not call
endpoints, does not run tests, and does not connect frontend.

Current disposition:

- KG-RUNTIME-10 created a minimal backend route draft.
- KG-RUNTIME-11 confirmed static compliance and default-off behavior.
- The route remains default-off.
- The route remains unrun.
- Service startup has not been verified.
- Endpoint behavior has not been verified.
- KG-RUNTIME-13 is not authorized by this document.

## 2. Baseline

Repository:

`/Users/youfeini/Desktop/文档生成系统`

Start HEAD:

`d61155fc8efe8dadf11350ae426ebec1f267abd8`

Start tag:

`v0.1.392-zdoc-kg-read-only-preview-route-static-review`

This document is the only intended new file for KG-RUNTIME-12.

## 3. KG-RUNTIME-10 Route Draft Summary

KG-RUNTIME-10 implemented the minimal route draft in:

`backend/app/routers/kg_read_only_preview.py`

and included it in:

`backend/app/main.py`

Implemented route path:

`/kg/read-only-preview`

Feature flag:

`ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED`

KG-RUNTIME-10 conclusions carried forward:

- The route is isolated in a new backend router module.
- `backend/app/main.py` only added one import and one `app.include_router(...)`
  line.
- The adapter file `backend/kg_read_only_preview_adapter.py` was not modified.
- The route is default-off.
- The route is read-only.
- The route requires `manual_trigger=True`.
- The route accepts only supplied dictionaries.
- The route does not read `AI知识图谱大全`.
- The route does not write files or正文.
- The route does not write `output/job/export`.
- The route does not connect to generation, export, review apply, ZBid, RAG,
  prompt registry, or system instruction registry.
- No service was run.
- No endpoint was called.

## 4. KG-RUNTIME-11 Static Compliance Summary

KG-RUNTIME-11 statically reviewed:

- `backend/app/main.py`;
- `backend/app/routers/kg_read_only_preview.py`;
- `backend/kg_read_only_preview_adapter.py`;
- `docs/zdoc-kg-read-only-preview-route-minimal-controlled-implementation-draft-kg-runtime-10-review.md`.

KG-RUNTIME-11 conclusions carried forward:

- Route inclusion in `backend/app/main.py` is limited to the established router
  import/include pattern.
- The route is controlled by `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED`.
- If the flag is not enabled, the route returns disabled status.
- After the feature flag gate, the route still requires `manual_trigger=True`.
- The adapter pure function is not called unless the route is explicitly
  enabled and manually triggered with valid dictionary inputs.
- The route does not connect to `/generate`, `/export_docx`, or
  `/review/apply`.
- The route does not write正文 or `output/job/export`.
- The route is not an evidence path and not a scoring path.
- The route does not call Ollama or external endpoints.
- The route does not connect RAG, prompt registry, or system instruction
  registry.
- The route remains a static backend draft and is not a usable feature.

## 5. Frozen Audit Package

The KG-RUNTIME-12 frozen audit package consists of:

| Package item | Path | Frozen role |
| --- | --- | --- |
| Route draft | `backend/app/routers/kg_read_only_preview.py` | Default-off read-only preview route draft |
| App router inclusion | `backend/app/main.py` | One import and one include for the KG route draft |
| Adapter draft | `backend/kg_read_only_preview_adapter.py` | Pure-function adapter consumed by the route only after gates pass |
| KG-RUNTIME-10 review | `docs/zdoc-kg-read-only-preview-route-minimal-controlled-implementation-draft-kg-runtime-10-review.md` | Implementation boundary and no-runtime-use record |
| KG-RUNTIME-11 review | `docs/zdoc-kg-read-only-preview-route-draft-static-compliance-and-default-off-review-kg-runtime-11.md` | Static compliance and default-off review |
| KG-RUNTIME-09 plan | `docs/zdoc-kg-read-only-preview-route-integration-target-static-discovery-and-minimal-implementation-plan-kg-runtime-09.md` | Static discovery and minimal implementation plan |

The package is frozen for manual authorization review only. It is not a service
run plan and does not prove runtime usability.

## 6. Current Non-Authorization Decisions

KG-RUNTIME-12 does not authorize:

- service startup;
- port access;
- endpoint calls;
- route execution;
- adapter execution;
- validator execution;
- frontend integration;
- test execution;
- CI integration;
- `py_compile`;
- `/generate` integration;
- `/export_docx` integration;
- `/review/apply` integration;
- ZBid writeback;
- evidence use;
- scoring use;
-正文 writeback;
- `output/job/export` writes;
- RAG integration;
- prompt registry integration;
- system instruction registry integration;
- real registry creation;
- knowledge pack registration, enablement, or loading;
- local model upgrade, pull, deletion, or replacement.

These remain blocked until ChatGPT separately authorizes a later task.

## 7. Route Current State

The route draft currently remains:

- default-off;
- env-flag gated;
- manual-trigger gated;
- read-only;
- preview-only;
- no-write;
- not verified by service startup;
- not verified by endpoint call;
- not connected to frontend;
- not connected to tests or CI;
- not connected to RAG;
- not connected to prompt registry;
- not connected to system instruction registry.

Static source review shows the route returns disabled when
`ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED` is not enabled.

Runtime review has not been performed.

## 8. No `/generate`, `/export_docx`, `/review/apply` Boundary

The route draft must remain isolated from:

- `/generate`;
- `/export_docx`;
- `/review/apply`;
- `actions_bridge`;
- `zhifei_autoplan` generation routes;
- `zhifei_autoplan` export routes;
- review apply handlers;
- ZBid writeback flows.

No future manual run stage may use the route to trigger generation, export,
review apply, or writeback.

## 9. No正文 / No Output Boundary

The route draft must not write:

- document正文;
- generated content;
- DOCX files;
- JSON outputs;
- Markdown outputs;
- `output/job/export`;
- job state;
- export artifacts;
- ZBid data.

KG-RUNTIME-12 does not authorize any write-path verification.

## 10. No Evidence / No Scoring Boundary

The route draft must not be used as:

- evidence;
- scoring basis;
- generation input;
- bid response proof;
- source citation;
- scoring matrix input;
- scoring trace input.

Any later manual run must treat the response as route health or preview
metadata only, not as evidence or scoring content.

## 11. No RAG / Prompt / System Instruction Boundary

The route draft must not connect to:

- RAG;
- retrieval index;
- prompt registry;
- prompt pack;
- system instruction registry;
- system instruction loading;
- knowledge pack activation.

No later service-level check may promote KG content into runtime generation.

## 12. KG-RUNTIME-13 Authorization Gate

KG-RUNTIME-13 is not entered by this step.

If ChatGPT separately authorizes KG-RUNTIME-13, it should be limited to a first
manual service startup verification under a no-write, no-frontend, no-test, and
no-CI boundary.

KG-RUNTIME-13 must explicitly define:

- start HEAD and tag;
- exact service startup command;
- exact shutdown command;
- allowed environment variables;
- whether the route feature flag remains disabled or may be enabled;
- whether endpoint calls are allowed;
- allowed endpoint path, if any;
- allowed payload, if any;
- forbidden endpoints;
- timeout and cleanup requirements;
- process and port evidence requirements;
- rollback and shutdown requirements;
- output artifact prohibition.

If any of these are not explicitly authorized, KG-RUNTIME-13 must stop before
running anything.

## 13. KG-RUNTIME-13 Candidate Scope If Authorized

Candidate first manual service startup verification should stay minimal:

| Area | Candidate allowance if separately authorized | Still forbidden by default |
| --- | --- | --- |
| Service | One explicit ZDoc startup command | ZBid, Ollama, production deployment, background daemon changes |
| Feature flag | Prefer disabled route first | Automatic enablement without explicit authorization |
| Endpoint | Prefer `/health` first; route endpoint only if explicitly allowed | `/generate`, `/export_docx`, `/review/apply`, ZBid writeback |
| Payload | Minimal metadata-only payload if endpoint call is authorized | Source file loading, raw KG content, evidence/scoring payloads |
| Output | Console evidence only | `output/job/export`, DOCX, JSON artifact writes |
| Cleanup | Explicit shutdown and process confirmation | Leaving service running |

Any route endpoint call must preserve:

- no evidence;
- no scoring;
- no writeback;
- no RAG;
- no prompt registry;
- no system instruction registry;
- no knowledge pack load.

## 14. KG-RUNTIME-13 Forbidden Items

Unless separately authorized in exact terms, KG-RUNTIME-13 must not:

- run ZBid;
- run Ollama;
- pull or upgrade models;
- call external endpoints;
- call `/generate`;
- call `/export_docx`;
- call `/review/apply`;
- write正文;
- write `output/job/export`;
- run tests;
- connect CI;
- run KG-41 validator;
- run adapter directly;
- py_compile route, adapter, or validator;
- modify code;
- modify JSON;
- modify config;
- modify frontend;
- modify tests;
- copy, move, delete, or read content from `AI知识图谱大全`;
- create registry;
- register, enable, or load knowledge packs.

## 15. Rollback And Shutdown Requirements For KG-RUNTIME-13

If KG-RUNTIME-13 is later authorized to start a service, it must include:

- exact process start command;
- exact process shutdown command;
- evidence of process termination;
- evidence of no lingering route-specific side effects;
- evidence of no `output/job/export` writes;
- evidence of no route or adapter `.pyc` creation unless that specific side
  effect is explicitly authorized and reviewed;
- no code rollback unless a later step modifies code.

If a service cannot be shut down cleanly, KG-RUNTIME-13 must stop and report
that state instead of continuing.

## 16. Acceptance Criteria For KG-RUNTIME-13

If authorized, KG-RUNTIME-13 can only be accepted if it proves:

- the allowed command was the only service startup command;
- no forbidden endpoint was called;
- no frontend was touched;
- no tests or CI ran;
- no validator or adapter direct execution occurred;
- no Ollama or model call occurred;
- no model was upgraded or pulled;
- no output/job/export write occurred;
- service shutdown completed;
- route remains default-off unless explicit flag enablement was authorized;
- any endpoint response remains non-evidence and non-scoring.

## 17. Current Stage Closure

KG-RUNTIME-12 closes as a docs-only frozen audit package and no-service manual
run authorization gate.

Current status:

- KG-RUNTIME-10 route draft is summarized.
- KG-RUNTIME-11 static compliance review is summarized.
- The frozen audit package is established.
- The route remains default-off.
- The route remains unrun.
- Service startup remains unverified.
- No service is run.
- No endpoint is called.
- No adapter is run.
- No adapter is compiled.
- No validator is run.
- No tests or CI are run.
- No code is modified.
- No JSON is modified.
- No frontend or config files are modified.
- No registry is created.
- No knowledge pack is registered, enabled, or loaded.
- No RAG, prompt registry, or system instruction registry connection is made.
- No model is upgraded or pulled.
- No DOCX is generated.
- No `output/job/export` write occurs.
- Existing `__pycache__` or `.pyc` files are not cleaned or modified.
- KG-RUNTIME-13 is not entered.
