# ZDoc Local LLM Preview Isolated Safe Endpoint Guard Implementation Design

## 1. Purpose

This document records the ZDoc Step 14G isolated safe endpoint guard and fake-only implementation design.

The current stage only designs the guard, implementation boundary, future file scope, deterministic tests, and service-smoke gate for a future isolated safe endpoint. It does not implement code, does not add or modify tests, does not run pytest, does not start a service, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately implement an endpoint or start service smoke.

## 2. Baseline inherited from ZDoc Step 14F

ZDoc Step 14F archived the isolated safe endpoint implementation plan in:

```text
docs/zdoc-local-llm-preview-isolated-safe-endpoint-implementation-plan.md
```

The inherited baseline is:

- the safe fake-only helper already exists;
- the helper is located in `backend/zhifei_autoplan/ollama_preview.py`;
- the helper remains pure helper-layer capability;
- the isolated safe endpoint has not been implemented;
- no real safe endpoint exists;
- no real safe UI entry exists;
- service smoke is not currently recommended;
- future service smoke requires an isolated safe endpoint first;
- existing business routes still include `/generate`, `/export_docx`, and `/review/apply`;
- future endpoint work must stay default-off, fake-only, preview-only, and no-write;
- future endpoint work must stay isolated from the formal generation chain, formal export chain, and ZBid formal writeback.

The current Step 14F stable baseline tag is:

```text
v0.1.66-zdoc-local-llm-isolated-safe-endpoint-plan
```

## 3. Current helper-only state

The current safe capability is not a service endpoint. It is a helper-only capability in:

```text
backend/zhifei_autoplan/ollama_preview.py
```

The current helper-level capability includes:

- `run_zdoc_local_llm_preview_safe_service_entry`;
- safe service payload construction;
- default-off behavior through `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`;
- deterministic disabled output;
- deterministic fake-only advisory / suggestions when enabled;
- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- `affects_zbid_writeback=false`;
- route isolation metadata for `/generate`, `/export_docx`, and `/review/apply`;
- no-write metadata for `output/`, `job/`, and `export/`;
- stable failure handling for missing input, empty text, illegal fields, and automatic triggers.

The helper is not mounted by:

- `backend/app/main.py`;
- `backend/app/routers/actions_bridge.py`;
- `backend/app/routers/zhifei_autoplan.py`;
- `app.py`;
- `frontend_web/app.py`.

Therefore, the current state is still helper-only. It is not safe to run service smoke against the real application until a dedicated safe endpoint exists.

## 4. Isolated safe endpoint objective

The future isolated safe endpoint objective is to provide one unambiguous preview / diagnostics service entry that can later be used for fake-only service smoke without touching existing business routes.

The endpoint must:

- be independent from `/generate`;
- be independent from `/export_docx`;
- be independent from `/review/apply`;
- be default-off;
- be preview-only;
- be no-write;
- call only the fake-only safe helper;
- return only preview advisory / suggestions;
- not modify正文章节;
- not write `output/`;
- not write `job/`;
- not write `export/`;
- not trigger the formal generation chain;
- not trigger the formal export chain;
- not connect ZBid formal writeback;
- not call real Ollama;
- not call external model/API transports;
- not auto-trigger;
- be suitable for a later 127.0.0.1 loopback smoke after separate authorization.

The endpoint implementation stage must not start a service. Service startup belongs only to a later service-smoke stage.

## 5. Proposed endpoint path and naming

The future endpoint must be named and routed as a preview / diagnostics entry, not as a generation, export, job, review, or writeback entry.

A safe candidate path is:

```text
/local-llm/preview-safe
```

An equivalent project-style safe path may be used if the later implementation request names it explicitly and proves that it is isolated from formal chains.

Endpoint naming must make the boundary visible:

- include `local-llm`;
- include `preview`;
- include `safe` or an equivalent diagnostics-only marker;
- avoid `generate`;
- avoid `export`;
- avoid `apply`;
- avoid `job`;
- avoid `docx`;
- avoid wording that can be interpreted as formal document production.

The endpoint disabled behavior must not call the safe helper.

The endpoint enabled behavior must call only the fake-only safe helper.

The endpoint response must include clear preview and no-write markers:

- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- `affects_zbid_writeback=false`.

The endpoint response must not be mistaken for a formal generation result. It must not return formal artifact fields such as:

- `job_id`;
- `docx_path`;
- `markdown_path`;
- `json_path`;
- `export_path`;
- `output_path`;
- `download_url`.

The endpoint must not be associated with:

- `/generate`;
- `/export_docx`;
- `/review/apply`;
- `/compose`;
- `/export`;
- any formal output route.

## 6. Allowed future file scope

This Step 14G does not modify code. It only defines candidate file scope for a later implementation step.

Future implementation may consider adding an isolated router file such as:

```text
backend/app/routers/local_llm_preview_safe.py
```

An equivalent project-style router name may be used only if it remains clearly isolated from existing business routers.

Future implementation may consider adding endpoint tests such as:

```text
backend/tests/test_local_llm_preview_safe_endpoint.py
```

An equivalent project-style test path may be used only if the later step explicitly names it.

Future implementation may call the existing safe helper in:

```text
backend/zhifei_autoplan/ollama_preview.py
```

Future implementation may include the safe router in:

```text
backend/app/main.py
```

but only if the later implementation request separately authorizes modifying `backend/app/main.py`.

The future implementation request must explicitly answer:

- whether a new isolated router file may be added;
- whether `backend/app/main.py` may be modified;
- whether a new endpoint test file may be added;
- whether `backend/zhifei_autoplan/ollama_preview.py` may be modified;
- whether `backend/app/routers/actions_bridge.py` remains forbidden;
- whether `backend/app/routers/zhifei_autoplan.py` remains forbidden;
- whether UI files remain forbidden;
- the exact endpoint path;
- the exact deterministic test command.

Default behavior is that `backend/app/routers/actions_bridge.py` and `backend/app/routers/zhifei_autoplan.py` must not be modified, because they contain existing business routes and generation/export/writeback-adjacent paths.

## 7. Forbidden future file scope

Unless a later step separately designs and authorizes a narrower exception, future implementation must not modify:

- formal generation-chain files;
- formal export-chain files;
- ZBid formal writeback files;
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`;
- `backend/app/routers/actions_bridge.py`;
- `backend/app/routers/zhifei_autoplan.py`;
- `app.py`;
- `frontend_web/app.py`;
- DOCX export services;
- JSON export services;
- Markdown export services;
- output artifact writers;
- job writers;
- `tasks/`;
- `output/`;
- `job/`;
- `export/`;
- `build/`;
- requirements files;
- `pyproject` files;
- lock files.

Future implementation must not add external dependencies.

Future implementation must not change requirements, dependency locks, or project dependency configuration.

Future implementation must not execute `git clean` and must not clear untracked files.

## 8. Feature flag contract

The governing feature flag remains:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

Disabled values are:

- absent;
- empty;
- `false`;
- `0`;
- `no`;
- `off`.

Enabled values are:

- `true`;
- `1`;
- `yes`;
- `on`.

Disabled behavior has highest priority. The isolated safe endpoint must remain disabled unless `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` explicitly enables preview.

No endpoint-specific flag may bypass `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.

If a future endpoint-specific flag is added, it must be stricter than the global flag and subordinate to the global flag.

The endpoint must not auto-trigger. It must require a bounded manual or diagnostics request.

## 9. Disabled behavior contract

When the feature flag is disabled, the future isolated safe endpoint must:

- return a stable disabled response;
- return `enabled=false`;
- return `preview_only=true`;
- return `no_write=true`;
- return `affects_generation=false`;
- return `affects_export=false`;
- return `affects_zbid_writeback=false`;
- not call the safe helper;
- not call `/generate`;
- not call `/export_docx`;
- not call `/review/apply`;
- not write `output/job/export`;
- not modify正文;
- not trigger formal generation;
- not trigger formal export;
- not connect ZBid formal writeback;
- not call real Ollama;
- not call external model/API transports;
- not download or pull models.

Disabled behavior must be deterministic across absent, empty, `false`, `0`, `no`, and `off`.

## 10. Enabled fake-only behavior contract

When the feature flag is enabled, the future isolated safe endpoint must:

- call only the fake-only safe helper;
- return only advisory / suggestions;
- return `preview_only=true`;
- return `no_write=true`;
- return `affects_generation=false`;
- return `affects_export=false`;
- return `affects_zbid_writeback=false`;
- mark the response as preview / diagnostics;
- avoid formal result fields;
- not call `/generate`;
- not call `/export_docx`;
- not call `/review/apply`;
- not write `output/job/export`;
- not modify正文 or 正文章节;
- not trigger formal generation;
- not trigger formal export;
- not connect ZBid formal writeback;
- not call real Ollama;
- not call external model/API transports;
- not download or pull models.

Enabled behavior must be deterministic for the same input.

## 11. Forbidden route and chain boundary

The future isolated safe endpoint must remain separated from all formal or write-capable routes and chains.

It must not call:

- `/generate`;
- `/generate_async`;
- `/export_docx`;
- `/review/apply`;
- `/compose`;
- `/export`;
- job creation routes;
- job download routes;
- DOCX export routes;
- compare export routes;
- audit export routes;
- output artifact writers;
- formal Markdown writers;
- formal JSON writers;
- review apply or remediation functions;
- ZBid formal writeback functions;
- real Ollama transports;
- external model/API transports.

It must not write:

- `output/`;
- `job/`;
- `export/`;
- `build/`.

It must not listen on `0.0.0.0`.

The endpoint implementation stage must not start a service. Only a later service-smoke stage may start a local service after separate authorization.

The later service-smoke stage may only bind to:

```text
127.0.0.1
```

The later service-smoke stage does not need 2号窗口 unless ZDoc enters a separately authorized real Ollama stage.

## 12. Deterministic tests matrix

Future tests must be fake-only and deterministic. This Step 14G does not add tests.

The future test matrix must cover at least:

1. safe endpoint feature flag absent returns disabled;
2. safe endpoint feature flag `false`, `0`, `no`, and `off` returns disabled;
3. disabled mode does not call the safe helper;
4. disabled mode does not write `output/job/export`;
5. enabled mode calls the fake-only safe helper;
6. enabled mode returns `preview_only=true`;
7. enabled mode returns `no_write=true`;
8. enabled mode returns `affects_generation=false`;
9. enabled mode returns `affects_export=false`;
10. enabled mode does not call `/generate`;
11. enabled mode does not call `/export_docx`;
12. enabled mode does not call `/review/apply`;
13. enabled mode does not write `output/job/export`;
14. enabled mode does not modify正文;
15. enabled mode does not connect ZBid formal writeback;
16. enabled mode does not call real Ollama;
17. enabled mode does not call external model/API transports;
18. enabled mode does not trigger the generation chain;
19. enabled mode does not trigger the export chain;
20. tests do not start a real service unless a later service-smoke step separately authorizes service startup;
21. tests do not run Ollama;
22. existing `backend/tests/test_ollama_preview.py` continues to pass.

Future tests must not write `output/job/export`, must not create DOCX / JSON / Markdown formal artifacts, and must not require network access.

## 13. Service smoke prerequisites

Service smoke is not allowed in this Step 14G.

Future service smoke may be considered only after:

- Step 14G is archived;
- isolated safe endpoint implementation is complete;
- deterministic endpoint tests have passed;
- service smoke is separately authorized;
- service startup command is explicitly named;
- service listen address is explicitly limited to `127.0.0.1`;
- service smoke request path is the isolated safe endpoint only;
- service smoke does not request `/generate`;
- service smoke does not request `/export_docx`;
- service smoke does not request `/review/apply`;
- service smoke does not write `output/job/export`;
- service smoke does not trigger the export chain;
- service smoke does not connect ZBid formal writeback;
- service shutdown method is explicit;
- service stopped state is verified after smoke;
- no 2号窗口 is required unless a later real Ollama stage is separately authorized.

If any prerequisite is missing, service smoke must stop before service startup.

## 14. Future implementation acceptance criteria

A later isolated safe endpoint implementation step must satisfy at least:

- ZDoc Step 14G design has been archived;
- allowed file scope is explicitly listed;
- forbidden file scope is explicitly listed;
- whether a new isolated safe router file may be added is explicit;
- whether `backend/app/main.py` may be modified is explicit;
- the safe endpoint path is explicit;
- feature flag name remains `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`;
- disabled behavior is explicit and stable;
- disabled behavior does not call the safe helper;
- enabled behavior is fake-only;
- enabled behavior calls only the safe helper;
- deterministic tests scope is explicit;
- no code implementation stage starts a service;
- no code implementation stage runs Ollama;
- no implementation writes `output/job/export`;
- no implementation triggers the formal generation chain;
- no implementation triggers the formal export chain;
- no implementation connects ZBid formal writeback;
- no implementation calls real Ollama;
- no implementation calls external model/API transports;
- completion waits for ChatGPT review before service smoke.

## 15. Recommended next ZDoc step

The recommended next step is:

```text
ZDoc Step 14H：ZDoc local-LLM preview isolated safe endpoint fake-only 实现 + deterministic tests
```

The next step must not directly enter service smoke.

The next step must not connect real Ollama.

The next step must not connect formal generation chain, formal export chain, or ZBid formal writeback.

## 16. Closure statement

ZDoc Step 14G only records the isolated safe endpoint guard and fake-only implementation design.

It confirms that the safe fake-only helper exists, the isolated safe endpoint has not been implemented, service smoke is not currently allowed, and any future endpoint must remain isolated from `/generate`, `/export_docx`, `/review/apply`, the formal generation chain, the formal export chain, and ZBid formal writeback.

This document does not authorize code changes, endpoint registration, UI changes, service startup, real Ollama calls, external model/API calls, formal generation, formal export, output/job/export writes, or ZBid formal writeback.
