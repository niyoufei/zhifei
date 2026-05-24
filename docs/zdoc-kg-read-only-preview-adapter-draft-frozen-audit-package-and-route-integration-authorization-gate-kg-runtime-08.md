# ZDoc KG Read-Only Preview Adapter Draft Frozen Audit Package And Route Integration Authorization Gate KG-RUNTIME-08

## 1. Execution Summary

KG-RUNTIME-08 is a docs-only frozen audit package and route integration
authorization gate for the read-only preview adapter draft. This step does not
register a route, does not connect frontend, does not run services, and does
not modify the adapter.

Current disposition:

- The KG-RUNTIME-06 adapter remains a pure-function draft.
- KG-RUNTIME-07 confirmed static compliance and no-route status.
- The adapter is not reachable through HTTP routes.
- The adapter is not connected to frontend, generation, export, review apply,
  RAG, prompt registry, or system instruction registry.
- KG-RUNTIME-09 is not authorized by this document.

## 2. Baseline

Repository:

`/Users/youfeini/Desktop/文档生成系统`

Start HEAD:

`846091bb12002ace7ccaccd85ac73fe6f4008372`

Start tag:

`v0.1.388-zdoc-kg-read-only-preview-adapter-static-review`

This document is the only intended new file for KG-RUNTIME-08.

## 3. KG-RUNTIME-06 And KG-RUNTIME-07 Summary

| Stage | File | Conclusion carried forward |
| --- | --- | --- |
| KG-RUNTIME-06 | `backend/kg_read_only_preview_adapter.py` | Created a minimal pure-function adapter draft |
| KG-RUNTIME-06 review | `docs/zdoc-kg-read-only-preview-adapter-minimal-controlled-implementation-draft-kg-runtime-06-review.md` | Confirmed no route, no service, no runtime integration |
| KG-RUNTIME-07 | `docs/zdoc-kg-read-only-preview-adapter-draft-static-compliance-and-no-route-review-kg-runtime-07.md` | Confirmed static compliance, default-off behavior, and no-route status |

The adapter draft remains a candidate only. It is not a system integration.

## 4. Frozen Audit Package Contents

The frozen audit package for route integration authorization consists of:

| Package item | Path | Frozen role |
| --- | --- | --- |
| Adapter draft | `backend/kg_read_only_preview_adapter.py` | Pure-function candidate, no route |
| KG-RUNTIME-06 review | `docs/zdoc-kg-read-only-preview-adapter-minimal-controlled-implementation-draft-kg-runtime-06-review.md` | Creation and no-runtime review |
| KG-RUNTIME-07 static review | `docs/zdoc-kg-read-only-preview-adapter-draft-static-compliance-and-no-route-review-kg-runtime-07.md` | Static compliance and no-route review |
| KG-RUNTIME-05 gate | `docs/zdoc-kg-read-only-preview-adapter-skeleton-frozen-audit-package-and-controlled-implementation-authorization-gate-kg-runtime-05.md` | Controlled implementation authorization boundary |
| KG-RUNTIME-03 skeleton | `docs/kg-runtime-adapters/zdoc_kg_read_only_preview_adapter_skeleton.py` | Earlier docs-only skeleton, unchanged |
| KG-41 validator draft | `docs/kg-controlled-validators/zdoc_kg_disabled_entity_pair_static_validator_draft.py` | Separate validator draft, not executed |

The package is frozen as audit documentation. It is not a route registration
bundle and cannot be loaded by ZDoc runtime by itself.

## 5. Adapter Current State

Adapter path:

`backend/kg_read_only_preview_adapter.py`

Current frozen state:

- File mode remains `100644 / 644`.
- No shebang.
- No CLI entry.
- No `if __name__ == "__main__"`.
- No automatic file read.
- No file write.
- No `output/job/export` access.
- No service call.
- No port access.
- No Ollama call.
- No endpoint call.
- No app import.
- No orchestrator import.
- No LLM client import.
- No generation-chain import.
- No export-chain import.
- No review-apply-chain import.
- No route registration.
- No RAG connection.
- No prompt registry connection.
- No system instruction registry connection.
- Not executed.
- Not compiled with `py_compile`.
- Not connected to tests or CI.

The adapter remains a non-routed pure-function draft.

## 6. Current Non-Authorization Decisions

KG-RUNTIME-08 does not authorize:

- Route registration.
- Backend router changes.
- Frontend integration.
- Config integration.
- Test integration.
- CI integration.
- Service execution.
- Endpoint invocation.
- `/generate` integration.
- `/export_docx` integration.
- `/review/apply` integration.
- ZBid writeback.
- Evidence use.
- Scoring use.
-正文 writeback.
- `output/job/export` writes.
- RAG integration.
- Prompt registry integration.
- System instruction registry integration.
- Real registry creation.
- Knowledge pack registration, enablement, or loading.
- KG-41 validator execution.
- Adapter execution.
- Local model upgrade, pull, deletion, or replacement.

These remain blocked until ChatGPT separately authorizes a later task.

## 7. Evidence, Scoring, And Writeback Boundary

The adapter draft may not be used as:

- evidence;
- scoring basis;
- generation input;
-正文 writeback source;
- DOCX export source;
- ZBid writeback source;
- RAG source;
- prompt registry source;
- system instruction source.

Its disabled output flags remain part of the route-gate acceptance baseline:

- `writeback_allowed=False`;
- `output_write_allowed=False`;
- `evidence_allowed=False`;
- `scoring_allowed=False`;
- `runtime_access=False`;
- `route_registered=False`.

## 8. Existing Cache Files Boundary

The repository already contains existing `backend/**/__pycache__` directories
and `.pyc` files from earlier work. KG-RUNTIME-08 does not clean, delete,
modify, normalize, or use those files.

Current stage rule:

- Existing backend cache files are not KG-RUNTIME-08 products.
- Existing backend cache files are not modified by KG-RUNTIME-08.
- Cache cleanup is out of scope.
- The only relevant cache check is whether a new adapter-specific cache exists.

Expected adapter-specific cache pattern:

`backend/**/kg_read_only_preview_adapter*.pyc`

No route integration stage may use cache cleanup as a side effect.

## 9. KG-RUNTIME-09 Authorization Gate

KG-RUNTIME-09 is not entered by this step.

If ChatGPT separately authorizes KG-RUNTIME-09, it must explicitly define:

- start HEAD and tag;
- exact allowed files;
- whether route code may be added;
- whether any existing router file may be modified;
- whether tests are allowed or still prohibited;
- whether frontend remains prohibited;
- no-service and no-endpoint validation requirements;
- rollback requirements;
- acceptance criteria.

No KG-RUNTIME-09 work may be inferred from this document.

## 10. KG-RUNTIME-09 Minimum Route Scope If Authorized

If KG-RUNTIME-09 is later authorized as a minimal route integration step, the
safest route scope should remain default-off and preview-only.

Potential minimum route scope:

| Area | Minimum allowable direction | Still prohibited by default |
| --- | --- | --- |
| Route | One explicit preview-only route candidate, only if named by authorization | Any `/generate`, `/export_docx`, or `/review/apply` route change |
| Adapter call | Manual preview-only call shape | Automatic call from generation, export, review, scoring, or ZBid |
| Inputs | Supplied disabled dictionaries or explicitly authorized docs metadata | Reading `AI知识图谱大全` or scanning external sources |
| Output | Preview-only JSON payload |正文 writeback, evidence, scoring, DOCX, job output |
| Runtime | No service start during implementation unless separately authorized | Starting ZDoc, ZBid, Ollama, ports, or endpoints |
| Registry | None | Manifest registration, real registry creation, knowledge pack enablement |
| Retrieval | None | RAG indexing or retrieval |
| Prompt/system | None | prompt registry or system instruction registry connection |
| Validator | None | Running KG-41, adapter execution tests, or CI wiring unless separately authorized |

Route integration, if ever authorized, must preserve default-off behavior and
must not make the adapter reachable from production generation or export flows.

## 11. KG-RUNTIME-09 Forbidden Modification Scope

Unless KG-RUNTIME-09 explicitly authorizes otherwise, it must not modify:

- `backend/kg_read_only_preview_adapter.py`;
- KG-08 manifest candidate JSON;
- KG-15 registry candidate JSON;
- KG-31 disabled manifest entity JSON;
- KG-33 disabled registry entity JSON;
- KG-41 validator draft;
- KG-RUNTIME-03 adapter skeleton;
- existing docs;
- frontend;
- config;
- tests;
- files under `/Users/youfeini/Desktop/AI知识图谱大全`.

It must not create or activate:

- a real registry;
- a real knowledge-pack loader;
- RAG connector;
- prompt registry connector;
- system instruction registry connector;
- evidence path;
- scoring path;
- writeback path;
- export path;
- model endpoint path.

## 12. KG-RUNTIME-09 Rollback Requirements

If KG-RUNTIME-09 is later authorized and creates any route candidate, rollback
must be simple:

- Remove or disable the route candidate.
- Preserve `backend/kg_read_only_preview_adapter.py` behavior unless the task
  explicitly authorizes adapter changes.
- Preserve KG-08, KG-15, KG-31, KG-33, KG-41, and KG-RUNTIME-03 skeleton.
- Confirm no service was started.
- Confirm no endpoint was called.
- Confirm no frontend or config enablement was added.
- Confirm no registry state was created.
- Confirm no output/job/export files were written.
- Confirm no model was upgraded, pulled, deleted, or replaced.

If rollback requires database, registry, model, output, or cache cleanup, the
route scope should be rejected before implementation.

## 13. KG-RUNTIME-09 Acceptance Criteria

Any future route integration cannot be accepted unless it proves:

- the adapter remains default-off;
- manual preview trigger remains required;
- no route enters `/generate`;
- no route enters `/export_docx`;
- no route enters `/review/apply`;
- no route writes to ZBid;
- no evidence use;
- no scoring use;
- no正文 writeback;
- no `output/job/export` write;
- no RAG connection;
- no prompt registry connection;
- no system instruction registry connection;
- no knowledge pack registration, enablement, or loading;
- no KG-41 execution;
- no model upgrade or pull;
- no adapter-specific `__pycache__` or `.pyc` side effect unless explicitly
  authorized and reviewed.

The acceptance check must use exact changed-file scope and static evidence.

## 14. Current Stage Closure

KG-RUNTIME-08 closes as a docs-only frozen audit package and route integration
authorization gate.

Current status:

- KG-RUNTIME-06 adapter draft is summarized and frozen as input.
- KG-RUNTIME-07 static compliance review is summarized and frozen as input.
- The adapter remains unmodified.
- The adapter remains unexecuted.
- The adapter remains uncompiled.
- No route is registered.
- No frontend integration exists.
- No service is run.
- No endpoint is called.
- No JSON is modified.
- KG-41 remains unmodified and unexecuted.
- KG-RUNTIME-03 skeleton remains unmodified and unexecuted.
- Existing `backend/**/__pycache__` and `.pyc` files are not modified or
  cleaned.
- No knowledge pack is registered, enabled, or loaded.
- No RAG, prompt registry, or system instruction registry connection exists.
- No model upgrade or model pull is performed.
- No DOCX is generated.
- No `output/job/export` write occurs.
- KG-RUNTIME-09 is not entered.
