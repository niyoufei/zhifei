# ZDoc KG Read-Only Preview Route Integration Target Static Discovery And Minimal Implementation Plan KG-RUNTIME-09

## 1. Execution Summary

KG-RUNTIME-09 is a docs-only static discovery and minimal implementation plan
for a future read-only preview route. It does not modify code, does not
register a route, does not run services, and does not execute the KG adapter.

Current conclusion:

- KG-RUNTIME-06 created `backend/kg_read_only_preview_adapter.py` as a
  pure-function draft only.
- KG-RUNTIME-07 confirmed the adapter is static, default-off, no-route, and
  disconnected from runtime chains.
- KG-RUNTIME-08 froze the adapter draft as an audit package and route
  integration authorization gate.
- Static discovery identifies `backend/app/main.py` plus a new isolated router
  module under `backend/app/routers/` as the only reasonable future route
  integration target.
- KG-RUNTIME-10 is not authorized by this document.

## 2. Baseline

Repository:

`/Users/youfeini/Desktop/文档生成系统`

Start HEAD:

`7ae151e905fd97adddb9a4d6cd77238a7a864a4d`

Start tag:

`v0.1.389-zdoc-kg-read-only-preview-adapter-route-integration-gate`

This document is the only intended new file for KG-RUNTIME-09.

## 3. Carried Conclusions From KG-RUNTIME-06 To KG-RUNTIME-08

| Stage | File | Carried conclusion |
| --- | --- | --- |
| KG-RUNTIME-06 | `backend/kg_read_only_preview_adapter.py` | Minimal pure-function adapter draft; no route, no service, no runtime integration |
| KG-RUNTIME-06 review | `docs/zdoc-kg-read-only-preview-adapter-minimal-controlled-implementation-draft-kg-runtime-06-review.md` | Adapter consumes supplied dictionaries only and does not read files or write outputs |
| KG-RUNTIME-07 | `docs/zdoc-kg-read-only-preview-adapter-draft-static-compliance-and-no-route-review-kg-runtime-07.md` | Adapter is default-off through `manual_trigger=False`, no CLI, no route, no file IO, no model or endpoint call |
| KG-RUNTIME-08 | `docs/zdoc-kg-read-only-preview-adapter-draft-frozen-audit-package-and-route-integration-authorization-gate-kg-runtime-08.md` | Route integration remains unauthorized; KG-RUNTIME-09 may only do static discovery and planning |

The adapter is still not a system integration. It remains non-routed,
unexecuted, uncompiled, and disconnected from generation, export, review apply,
RAG, prompt registry, and system instruction registry.

## 4. Static Route Entry Discovery

Primary observed application entry:

`backend/app/main.py`

Static observations:

- Creates the main FastAPI app with `app = FastAPI()`.
- Registers routers through explicit imports and `app.include_router(...)`.
- Existing included routers are `ingest`, `retrieve`, `publish`, `score`,
  `zhifei_autoplan`, `actions_bridge`, `auth`, `local_llm_preview_safe`, and
  `local_trial_preview_only`.
- Exposes direct app-level routes such as `/health`, `/capabilities`, `/config`,
  `/compose`, `/export`, `/retrieve`, and audit/debug routes.

Reasonable future route target:

- Add a new isolated router module under `backend/app/routers/`.
- Include that router from `backend/app/main.py`.
- Keep the adapter module `backend/kg_read_only_preview_adapter.py` unchanged.

Rejected route targets for KG-RUNTIME-10 planning:

| Candidate | Reason not preferred |
| --- | --- |
| `backend/app/routers/actions_bridge.py` | Already contains generation, export, review apply, job, and action bridge routes; adding KG preview here risks proximity to forbidden chains |
| `backend/app/routers/zhifei_autoplan.py` | Contains active KG upload/list/activate/search plus generate/export/job routes; too close to real KG activation and generation flows |
| `backend/app/main.py` direct `@app.post(...)` route | Would mix route logic into the main app file instead of keeping a narrow isolated router |
| `backend/main.py` | Separate minimal/legacy style FastAPI entry; not the active router aggregation pattern identified in `backend/app/main.py` |
| `backend/app/main_backup.py` | Backup file, not a future integration target |

## 5. Static Configuration And Feature Flag Discovery

Observed default-off patterns:

- `backend/app/routers/local_llm_preview_safe.py` uses env-backed feature flags
  and returns disabled responses when flags are not enabled.
- `backend/zhifei_autoplan/ollama_preview.py` defines env flag constants such as
  `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` and keeps preview flows default-off.
- `backend/app/main.py` exposes non-sensitive config metadata but also contains
  write-capable config update behavior under `/config/version`; KG preview route
  planning should not modify or depend on that path.

Recommended future feature flag:

`ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED`

Required behavior:

- default value is disabled;
- route returns `disabled` or `blocked` unless the flag is explicitly enabled;
- even when enabled, `manual_trigger=True` remains required in the request;
- no config file write is required;
- no `backend/data/autoplan/config.json` mutation is allowed;
- no `/config/version` or admin config write path is used.

## 6. Static Adapter Boundary

Adapter path:

`backend/kg_read_only_preview_adapter.py`

Required preservation:

- no shebang;
- no CLI entry;
- no `if __name__ == "__main__"`;
- no automatic file read;
- no file write;
- no `output/job/export` access;
- no service, port, Ollama, or endpoint call;
- no app, orchestrator, LLM client, generation, export, or review apply import;
- no route registration inside the adapter;
- no RAG, prompt registry, or system instruction registry connection.

KG-RUNTIME-10, if authorized, should call the adapter from a separate route
module. It should not change the adapter unless explicitly authorized by
ChatGPT.

## 7. KG-RUNTIME-10 Minimal Allowed File Set If Authorized

KG-RUNTIME-10 is not authorized here. If ChatGPT separately authorizes it, the
minimum file set should be limited to:

| File | Allowed future purpose |
| --- | --- |
| `backend/app/routers/kg_read_only_preview.py` | New isolated route module for preview-only KG adapter calls |
| `backend/app/main.py` | Add exactly one import and one `app.include_router(...)` line for the new router |
| `docs/zdoc-kg-read-only-preview-route-minimal-controlled-implementation-kg-runtime-10-review.md` | Review and boundary record for the KG-RUNTIME-10 implementation |

The preferred route path should be a new, explicit preview-only path such as:

`/kg/read-only-preview`

The route must not be placed under:

- `/generate`;
- `/export_docx`;
- `/review/apply`;
- `/autoplan/generate`;
- `/autoplan/export_docx`;
- `/actions/generate`;
- `/actions/export_docx`;
- `/actions/review/apply`;
- any ZBid writeback path.

## 8. KG-RUNTIME-10 Forbidden Modification Scope

Unless KG-RUNTIME-10 explicitly expands scope, it must not modify:

- `backend/kg_read_only_preview_adapter.py`;
- existing router modules other than adding the new router include in
  `backend/app/main.py`;
- `backend/app/routers/actions_bridge.py`;
- `backend/app/routers/zhifei_autoplan.py`;
- `backend/app/routers/local_llm_preview_safe.py`;
- `backend/app/routers/local_trial_preview_only.py`;
- frontend files;
- tests;
- config files;
- JSON files;
- KG-08 manifest candidate JSON;
- KG-15 registry candidate JSON;
- KG-31 disabled manifest entity JSON;
- KG-33 disabled registry entity JSON;
- KG-41 validator draft;
- KG-RUNTIME-03 adapter skeleton;
- existing docs except the KG-RUNTIME-10 review document;
- files under `/Users/youfeini/Desktop/AI知识图谱大全`.

It must not create:

- real registry;
- real knowledge pack loader;
- RAG connector;
- prompt registry connector;
- system instruction registry connector;
- evidence path;
- scoring path;
- writeback path;
- export path;
- model endpoint path.

## 9. Route Required Behavior If Authorized

A future KG-RUNTIME-10 route must be:

- default-off;
- env-flag gated;
- manually triggered;
- read-only;
- preview-only;
- no-write;
- metadata/dictionary based;
- invalid/blocked on missing disabled fields;
- invalid/blocked on non-disabled entity state;
- invalid/blocked when `manual_trigger` is not true;
- invalid/blocked when the feature flag is not enabled.

The route may only pass supplied request dictionaries into
`build_kg_read_only_preview(...)`. It must not read source files or discover
content paths by itself.

## 10. Hard Runtime Boundaries

Any future route must not:

- call `/generate`;
- call `/export_docx`;
- call `/review/apply`;
- trigger ZBid writeback;
- call or import generation-chain orchestration;
- call or import export-chain logic;
- call or import review-apply logic;
- call services;
- call ports;
- call Ollama;
- call endpoints;
- load or activate KG packs;
- register manifests;
- create a real registry;
- connect RAG;
- connect prompt registry;
- connect system instruction registry;
- write document正文;
- write files;
- write `output/job/export`;
- generate DOCX;
- upgrade, pull, delete, or replace local models;
- run KG-41 validator;
- compile adapter or validator with `py_compile`;
- run tests or CI unless separately authorized.

## 11. Evidence, Scoring, And Writeback Boundary

The future route response must preserve explicit false/blocked indicators:

- `writeback_allowed=False`;
- `output_write_allowed=False`;
- `evidence_allowed=False`;
- `scoring_allowed=False`;
- `runtime_access=False`;
- `route_registered` may describe the route shell but must not imply KG runtime
  registration;
- `rag_allowed=False`;
- `prompt_registry_allowed=False`;
- `system_instruction_registry_allowed=False`;
- `knowledge_pack_load_allowed=False`.

The route output must not be used as:

- evidence;
- scoring basis;
- generation input;
-正文 writeback source;
- DOCX export source;
- ZBid writeback source;
- RAG source;
- prompt registry source;
- system instruction source.

## 12. Rollback Requirements

If KG-RUNTIME-10 is later authorized and adds the route, rollback must be:

- delete or disable `backend/app/routers/kg_read_only_preview.py`;
- remove the single import from `backend/app/main.py`;
- remove the single `app.include_router(...)` line from `backend/app/main.py`;
- leave `backend/kg_read_only_preview_adapter.py` unchanged unless a separate
  authorization allowed adapter changes;
- leave all JSON files unchanged;
- leave KG-41 validator draft unchanged;
- leave KG-RUNTIME-03 adapter skeleton unchanged;
- leave frontend, tests, and config unchanged unless separately authorized;
- confirm no service was started;
- confirm no endpoint was called;
- confirm no `output/job/export` write occurred;
- confirm no model was upgraded or pulled;
- confirm no adapter-specific `__pycache__` or `.pyc` was introduced unless
  separately authorized and reviewed.

If rollback requires database cleanup, registry cleanup, model cleanup, output
cleanup, or external path cleanup, the planned route scope is too broad and
should be rejected before implementation.

## 13. KG-RUNTIME-10 Static Acceptance Criteria

If KG-RUNTIME-10 is authorized, it should not be accepted unless static review
proves:

- changed files are limited to the authorized file set;
- route is default-off;
- route requires the env feature flag;
- route requires `manual_trigger=True`;
- route is read-only;
- route performs no file IO;
- route does not read `AI知识图谱大全`;
- route does not modify JSON;
- route does not modify adapter behavior;
- route does not modify existing generation, export, review, or ZBid routes;
- route does not connect RAG, prompt registry, or system instruction registry;
- route cannot be used as evidence or scoring basis;
- route cannot write正文 or `output/job/export`;
- no service, adapter, validator, Ollama, port, endpoint, test, CI, or
  `py_compile` action was run unless separately authorized.

## 14. Current Stage Closure

KG-RUNTIME-09 closes as a docs-only static discovery and minimal implementation
plan.

Current status:

- No code was modified.
- No route was registered.
- No service was run.
- No endpoint was called.
- No adapter was run.
- No adapter was compiled.
- No validator was run.
- No JSON was modified.
- No existing docs were modified.
- No tests or CI were run.
- No frontend or config files were modified.
- No `AI知识图谱大全` file was copied, moved, deleted, renamed, or read for
  content.
- No real registry was created.
- No knowledge pack was registered, enabled, or loaded.
- No RAG, prompt registry, or system instruction registry connection was made.
- No model was upgraded, pulled, deleted, or replaced.
- No DOCX was generated.
- No `output/job/export` write occurred.
- Existing backend `__pycache__` or `.pyc` files were not cleaned or modified.
- KG-RUNTIME-10 is not entered.
