# ZDoc Local LLM Preview Isolated Safe Endpoint Implementation Plan

## 1. Purpose

This document records the ZDoc Step 14F isolated safe endpoint guard and fake-only implementation plan.

The current stage only plans an isolated safe endpoint boundary. It does not implement code, does not add or modify tests, does not run pytest, does not start a service, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately implement an endpoint or start service smoke.

## 2. Baseline inherited from ZDoc Step 14E

ZDoc Step 14E confirmed the current repository state after Step 14C and Step 14D:

- the safe fake-only service entry helper has been implemented;
- the helper is still a pure helper / helper-layer capability;
- the helper is located in `backend/zhifei_autoplan/ollama_preview.py`;
- the deterministic helper tests are in `backend/tests/test_ollama_preview.py`;
- the feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`;
- the current safe helper is not called by a real endpoint;
- the current safe helper is not called by a real UI entry;
- no real safe endpoint exists;
- no real safe UI entry exists;
- direct service smoke is not recommended;
- existing business routes still include `/generate`, `/export_docx`, and `/review/apply` risk paths;
- future service smoke requires an isolated safe endpoint first.

The current Step 14E stable baseline is:

```text
v0.1.65-zdoc-local-llm-preview-safe-endpoint-necessity-design
```

## 3. Current helper-only status

The current safe capability exists only at helper level.

The helper file is:

```text
backend/zhifei_autoplan/ollama_preview.py
```

The safe helper capability includes:

- `run_zdoc_local_llm_preview_safe_service_entry`;
- safe fake-only service payload construction;
- default-off behavior through `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`;
- preview-only markers;
- no-write markers;
- route-isolation markers for `/generate`, `/export_docx`, and `/review/apply`;
- deterministic failure behavior for missing, empty, illegal, and automatic-trigger inputs;
- deterministic fake-only advisory / suggestions when enabled.

The helper is not a real FastAPI endpoint. It is not mounted in `backend/app/main.py`, `backend/app/routers/actions_bridge.py`, or `backend/app/routers/zhifei_autoplan.py`.

The helper is not a real UI action. It is not wired into `app.py` or `frontend_web/app.py`.

## 4. Why isolated safe endpoint is required

An isolated safe endpoint is required before any future service smoke because the current repository has real service and UI surfaces with generation, export, job, output, and apply behavior.

Known risk surfaces include:

- `backend/app/main.py`, which defines the real FastAPI app;
- `backend/app/routers/actions_bridge.py`, which contains real business routes including `/generate`, `/export_docx`, and `/review/apply`;
- `backend/app/routers/zhifei_autoplan.py`, which contains real generation, async generation, job, export, and download routes;
- `app.py`, which contains Streamlit UI actions and generation-related buttons;
- `frontend_web/app.py`, which contains a Flask page entry;
- export and artifact modules that can participate in output and formal document creation.

Without a dedicated safe endpoint, a service smoke could accidentally validate or hit an existing business route instead of the safe fake-only helper. That would violate the default-off, preview-only, no-write, no-generation-chain, no-export-chain, and no-ZBid-writeback boundaries.

Therefore, ZDoc should not proceed directly to service smoke. If service smoke is still needed, the next implementation direction must first create a clearly isolated fake-only preview / diagnostics endpoint.

## 5. Proposed endpoint boundary

A future isolated safe endpoint must be a preview / diagnostics entry only.

The endpoint name and path must be clearly different from formal generation, export, review apply, or job routes. A safe candidate path is:

```text
/local-llm/preview-safe
```

An equivalent project-style safe path may be used only if the later implementation request explicitly names it and proves that it is not a generation, export, job, review apply, or ZBid writeback path.

The future endpoint boundary is:

- endpoint is default-off;
- endpoint is preview-only;
- endpoint is no-write;
- endpoint is fake-only;
- endpoint is manually triggered or diagnostic-only;
- endpoint disabled mode does not call the safe helper;
- endpoint enabled mode calls only the fake-only safe helper;
- endpoint returns only preview advisory / suggestions;
- endpoint returns `preview_only=true`;
- endpoint returns `no_write=true`;
- endpoint returns `affects_generation=false`;
- endpoint returns `affects_export=false`;
- endpoint returns `affects_zbid_writeback=false`;
- endpoint does not call `/generate`;
- endpoint does not call `/export_docx`;
- endpoint does not call `/review/apply`;
- endpoint does not write `output/job/export`;
- endpoint does not modify正文 or 正文章节;
- endpoint does not trigger formal generation;
- endpoint does not trigger formal export;
- endpoint does not connect ZBid formal writeback;
- endpoint does not call real Ollama;
- endpoint does not call external model/API transports;
- endpoint does not return fields that can be mistaken for formal generated output.

The response must avoid formal-result field names such as:

- `job_id`;
- `docx_path`;
- `markdown_path`;
- `json_path`;
- `export_path`;
- `output_path`;
- `download_url`.

If a future endpoint needs an identifier, it should use a preview-only diagnostic identifier that cannot be used to fetch a formal artifact.

## 6. Allowed future file scope

This Step 14F does not authorize any code implementation. It only proposes candidate file scopes that a later implementation step must explicitly accept or reject.

Future implementation may consider:

- adding one isolated router file dedicated to local-LLM preview diagnostics;
- adding or modifying a narrow endpoint test file;
- making a minimal call to the safe helper in `backend/zhifei_autoplan/ollama_preview.py`;
- preserving the current helper behavior in `backend/zhifei_autoplan/ollama_preview.py`;
- mounting the isolated router only if `backend/app/main.py` modification is separately authorized.

Any future request must explicitly state whether it allows:

- a new router file;
- a new endpoint path;
- new endpoint tests;
- modification of `backend/app/main.py`;
- modification of `backend/zhifei_autoplan/ollama_preview.py`;
- continued prohibition on existing business routers;
- continued prohibition on UI files.

The default future implementation preference is a new isolated router or endpoint module. The default is not to modify `backend/app/routers/actions_bridge.py` or `backend/app/routers/zhifei_autoplan.py`, because those files already contain business routes and generation/export/writeback-adjacent paths.

## 7. Forbidden future file scope

Unless a later step explicitly authorizes a narrower exception, future work must not modify:

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

Future work must not add external dependencies and must not change dependency configuration.

Future work must not execute `git clean` and must not clear untracked files.

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

Disabled behavior has the highest priority. No endpoint-specific flag may bypass `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.

If a future endpoint-specific flag is added, it must be stricter than this flag. The endpoint must remain disabled unless the global flag allows preview and the endpoint-specific guard also allows preview.

The endpoint must not auto-trigger. It must require a bounded preview / diagnostics request.

## 9. Disabled behavior contract

When `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is disabled, the future isolated safe endpoint must:

- return a stable disabled response;
- return `enabled=false`;
- preserve `preview_only=true`;
- preserve `no_write=true`;
- preserve `affects_generation=false`;
- preserve `affects_export=false`;
- preserve `affects_zbid_writeback=false`;
- not call the safe helper;
- not call `/generate`;
- not call `/export_docx`;
- not call `/review/apply`;
- not write `output/job/export`;
- not modify正文;
- not start generation;
- not trigger export;
- not connect ZBid formal writeback;
- not call real Ollama;
- not call external model/API transports;
- not download or pull models.

Disabled behavior must be deterministic for every disabled flag form.

## 10. Enabled fake-only behavior contract

When `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is enabled, the future isolated safe endpoint must:

- call only the fake-only safe helper;
- return only preview advisory / suggestions;
- return `preview_only=true`;
- return `no_write=true`;
- return `affects_generation=false`;
- return `affects_export=false`;
- return `affects_zbid_writeback=false`;
- mark the response as safe preview / diagnostics;
- not call `/generate`;
- not call `/export_docx`;
- not call `/review/apply`;
- not write `output/job/export`;
- not modify正文 or 正文章节;
- not trigger the formal generation chain;
- not trigger the formal export chain;
- not connect ZBid formal writeback;
- not call real Ollama;
- not call external model/API transports;
- not download or pull models.

Enabled behavior must be deterministic for the same input.

## 11. Forbidden route and chain boundary

The future endpoint must remain isolated from the following routes and chains:

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

The future endpoint implementation stage must not start a service. Only a later service-smoke stage may start a local service after separate authorization.

Any later service smoke must listen only on:

```text
127.0.0.1
```

It must not listen on:

```text
0.0.0.0
```

The future service smoke stage does not need 2号窗口 unless ZDoc enters a separately authorized real Ollama stage.

## 12. Deterministic tests matrix

Future tests must be fake-only and deterministic. This Step 14F does not add tests.

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
20. tests do not start a real service;
21. tests do not run Ollama;
22. existing `backend/tests/test_ollama_preview.py` continues to pass.

The future test command must be the smallest relevant test command named by that later implementation step. It must not run broad suites unless separately authorized.

## 13. Future service smoke prerequisites

Future service smoke may be considered only after all of the following are true:

- isolated safe endpoint implementation is complete;
- deterministic tests have passed;
- service smoke is explicitly authorized;
- service startup command is explicitly named;
- service smoke requests only the isolated safe endpoint;
- service smoke does not request `/generate`;
- service smoke does not request `/export_docx`;
- service smoke does not request `/review/apply`;
- service smoke does not write `output/job/export`;
- service smoke does not trigger the export chain;
- service smoke does not connect ZBid formal writeback;
- service listens only on `127.0.0.1`;
- service does not listen on `0.0.0.0`;
- service shutdown and cleanup method is explicit;
- no 2号窗口 is required unless a later real Ollama stage is separately authorized.

If any prerequisite is missing, service smoke must stop before service startup.

## 14. Future implementation acceptance criteria

A later isolated safe endpoint implementation step must satisfy at least:

- this Step 14F design has been archived;
- exact allowed files are listed;
- exact forbidden files are listed;
- endpoint path is explicitly named;
- feature flag remains `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`;
- disabled behavior is stable and does not call the helper;
- enabled behavior calls only the fake-only safe helper;
- response is marked preview-only;
- response is marked no-write;
- response sets `affects_generation=false`;
- response sets `affects_export=false`;
- response sets `affects_zbid_writeback=false`;
- implementation does not call `/generate`;
- implementation does not call `/export_docx`;
- implementation does not call `/review/apply`;
- implementation does not write `output/job/export`;
- implementation does not trigger generation;
- implementation does not trigger export;
- implementation does not connect ZBid formal writeback;
- implementation does not call real Ollama;
- implementation does not call external model/API transports;
- deterministic tests are added or updated only within the allowed scope;
- implementation stage does not start a service;
- implementation stage does not run Ollama;
- completion waits for ChatGPT review before any service smoke.

## 15. Recommended next ZDoc step

The recommended next step is:

```text
ZDoc Step 14G：ZDoc local-LLM preview isolated safe endpoint guard + fake-only implementation design
```

The next step must not directly enter code implementation.

The next step must not directly enter service smoke.

The next step must not enter real Ollama, formal generation chain, formal export chain, or ZBid formal writeback.

## 16. Closure statement

ZDoc Step 14F only documents the isolated safe endpoint implementation plan and hard boundaries.

It confirms that the current state is helper-only, that no real safe endpoint or real safe UI entry exists, and that service smoke should not proceed until an isolated safe endpoint has been separately designed, implemented, tested, and reviewed.

This document does not authorize code changes, endpoint registration, UI changes, service startup, real Ollama calls, external model/API calls, formal generation, formal export, output/job/export writes, or ZBid formal writeback.
