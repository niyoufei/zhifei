# ZDoc Local LLM Preview Safe Endpoint Necessity Design

## 1. Purpose

This document records the ZDoc Step 14E read-only audit and pre-design for deciding whether a real isolated safe endpoint is required before any local-LLM preview service smoke.

The current stage combines read-only verification and docs-only design. It does not modify code, does not add or modify tests, does not run pytest, does not start a service, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately implement an endpoint or start service smoke.

## 2. Baseline inherited from ZDoc Step 14D

ZDoc Step 14D reviewed the Step 14C safe fake-only service entry helper implementation in:

```text
docs/zdoc-local-llm-preview-safe-service-entry-fake-stage-review.md
```

The inherited baseline is:

- The safe fake-only service entry helper has been implemented.
- The helper implementation is in `backend/zhifei_autoplan/ollama_preview.py`.
- The deterministic tests are in `backend/tests/test_ollama_preview.py`.
- The feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- Disabled mode returns stable disabled output.
- Disabled mode does not call the fake bridge.
- Enabled mode calls only the fake-only bridge.
- Enabled mode returns preview advisory / suggestions.
- Enabled mode remains `preview_only=true`.
- Enabled mode remains `no_write=true`.
- Enabled mode remains `affects_generation=false`.
- Enabled mode remains `affects_export=false`.
- Enabled mode remains `affects_zbid_writeback=false`.
- The Step 14C test command was `python3 -m pytest backend/tests/test_ollama_preview.py -q`.
- The Step 14C test result was `78 passed in 1.03s`.
- Step 14C did not modify `backend/app/main.py`.
- Step 14C did not modify `backend/app/routers/actions_bridge.py`.
- Step 14C did not modify `backend/app/routers/zhifei_autoplan.py`.
- Step 14C did not modify `app.py`.
- Step 14C did not modify `frontend_web/app.py`.
- Step 14C did not register a real endpoint.
- Step 14C did not start a service.

## 3. Current helper-only capability

The current safe service entry capability is helper-only.

The relevant helper symbols are in:

```text
backend/zhifei_autoplan/ollama_preview.py
```

The helper-level capability includes:

- `run_zdoc_local_llm_preview_safe_service_entry`
- `build_zdoc_local_llm_preview_safe_service_payload`
- safe service metadata
- safe endpoint path metadata: `/diagnostics/local-llm-preview/safe`
- fake-only bridge delegation
- route isolation flags for `/generate`, `/export_docx`, and `/review/apply`
- no-write flags for output, job, and export surfaces
- stable failure behavior for missing, empty, illegal, and automatic-trigger inputs

The current helper reports that a safe endpoint path is intended, but it does not register that path in FastAPI, Streamlit, Flask, or any service router.

## 4. Endpoint / UI call-site audit

The Step 14E read-only audit checked the expected service and UI call sites:

- `backend/app/main.py`
- `backend/app/routers/actions_bridge.py`
- `backend/app/routers/zhifei_autoplan.py`
- `app.py`
- `frontend_web/app.py`

The audit found:

- `run_zdoc_local_llm_preview_safe_service_entry` exists in `backend/zhifei_autoplan/ollama_preview.py`.
- `run_zdoc_local_llm_preview_safe_service_entry` is referenced by `backend/tests/test_ollama_preview.py`.
- `run_zdoc_local_llm_preview_safe_service_entry` is referenced by docs.
- No call to `run_zdoc_local_llm_preview_safe_service_entry` was found in `backend/app/main.py`.
- No call to `run_zdoc_local_llm_preview_safe_service_entry` was found in `backend/app/routers/actions_bridge.py`.
- No call to `run_zdoc_local_llm_preview_safe_service_entry` was found in `backend/app/routers/zhifei_autoplan.py`.
- No call to `run_zdoc_local_llm_preview_safe_service_entry` was found in `app.py`.
- No call to `run_zdoc_local_llm_preview_safe_service_entry` was found in `frontend_web/app.py`.
- No real safe endpoint was found.
- No real safe UI entry was found.

Therefore, the current safe service entry remains a pure helper and deterministic test capability, not a service-callable endpoint.

## 5. Why service smoke is not yet safe

Service smoke is not yet safe because there is no isolated real endpoint that calls only the safe fake-only helper.

The repository still contains real service and UI surfaces, including:

- `backend/app/main.py`
- `backend/app/routers/actions_bridge.py`
- `backend/app/routers/zhifei_autoplan.py`
- `app.py`
- `frontend_web/app.py`

The repository still contains business routes and UI actions that may trigger generation, export, write, apply, or job behavior, including:

- `/generate`
- `/generate_async`
- `/export_docx`
- `/review/apply`
- `/compose`
- `/export`
- Streamlit buttons including local model preview, section review, review apply, and one-click generation controls
- Flask page actions related to document generation

Direct service smoke against the current app could accidentally target or validate a business route instead of the safe fake-only helper. Until a real isolated safe endpoint exists, service smoke is not recommended.

## 6. Need for isolated safe endpoint

If ZDoc needs a future service smoke, it should first add an isolated safe endpoint.

The endpoint is needed because:

- the helper is not callable through a real service route;
- the intended safe path is currently only metadata;
- the existing service routes include generation, export, job, and review-apply surfaces;
- smoke must have one unambiguous target;
- smoke must not target `/generate`;
- smoke must not target `/export_docx`;
- smoke must not target `/review/apply`;
- smoke must not rely on UI buttons;
- smoke must not depend on real Ollama availability.

The isolated safe endpoint should be implemented only after a later step authorizes a tightly scoped endpoint implementation.

## 7. Proposed safe endpoint boundary

A future safe endpoint must satisfy:

- default-off through `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`;
- preview-only;
- no-write;
- fake-only;
- manually triggered or diagnostic-only;
- calls only `run_zdoc_local_llm_preview_safe_service_entry` or the equivalent safe fake-only helper;
- returns preview advisory / suggestions only;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- does not modify正文;
- does not write `output/`;
- does not write `job/`;
- does not write `export/`;
- does not create DOCX;
- does not create formal Markdown;
- does not create formal JSON;
- does not call real Ollama;
- does not call external model/API transports;
- does not download or pull models.

The endpoint response must not contain fields that can be mistaken for formal generation or export output, such as `job_id`, `export_path`, `docx_path`, `markdown_path`, `json_path`, or generated document paths.

## 8. Forbidden route and chain boundary

The future safe endpoint must not call or delegate to:

- `/generate`
- `/generate_async`
- `/export_docx`
- `/review/apply`
- `/compose`
- `/export`
- formal generation-chain helpers
- formal export-chain helpers
- output artifact writers
- job writers
- review apply / remediation functions
- ZBid formal writeback functions
- real Ollama transports
- external model/API transports

The future safe endpoint must not write:

- `output/`
- `job/`
- `export/`
- `build/`

The future safe endpoint must not listen on `0.0.0.0` during service smoke. Any later smoke must bind only to `127.0.0.1`.

## 9. Future implementation gate

Before implementing a real safe endpoint, a later request must explicitly state:

- code implementation is allowed;
- the exact endpoint path;
- whether a new router file may be added;
- whether `backend/app/main.py` may be modified;
- whether `backend/app/routers/actions_bridge.py` remains forbidden;
- whether `backend/app/routers/zhifei_autoplan.py` remains forbidden;
- whether tests may be added or modified;
- whether UI files remain forbidden;
- the exact deterministic test command;
- the exact commit / tag / push scope;
- that service startup remains forbidden during implementation.

The preferred implementation shape is a narrow isolated router or endpoint module that calls only the safe helper. It should not be added to an existing generation/export/writeback route body.

## 10. Future deterministic tests gate

Before service smoke, future tests must prove:

- endpoint default disabled;
- disabled mode does not call the helper bridge;
- disabled mode does not write `output/job/export`;
- enabled mode calls only the safe fake-only helper;
- enabled mode returns `preview_only=true`;
- enabled mode returns `no_write=true`;
- enabled mode returns `affects_generation=false`;
- enabled mode returns `affects_export=false`;
- enabled mode returns `affects_zbid_writeback=false`;
- enabled mode does not call `/generate`;
- enabled mode does not call `/export_docx`;
- enabled mode does not call `/review/apply`;
- enabled mode does not trigger generation chain;
- enabled mode does not trigger export chain;
- enabled mode does not connect ZBid formal writeback;
- enabled mode does not call real Ollama;
- enabled mode does not call external model/API transports;
- invalid input returns stable failure;
- existing `backend/tests/test_ollama_preview.py` continues to pass.

Tests must remain fake-only and must not start a real service unless a later service-smoke step explicitly authorizes service startup.

## 11. Future service smoke gate

Future service smoke may be considered only after:

- this Step 14E design is archived;
- a real isolated safe endpoint has been implemented;
- deterministic tests have passed;
- the smoke target is only the safe endpoint;
- the smoke target is not `/generate`;
- the smoke target is not `/export_docx`;
- the smoke target is not `/review/apply`;
- the smoke confirms no `output/job/export` writes;
- the smoke confirms no formal generation;
- the smoke confirms no formal export;
- the smoke confirms no ZBid formal writeback;
- the smoke confirms no real Ollama call;
- the smoke confirms no external model/API call;
- the smoke is separately authorized to start a service;
- the service binds only to `127.0.0.1`;
- the service does not listen on `0.0.0.0`;
- the service process PID and shutdown method are recorded;
- service stopped state is verified.

If any condition is missing, service smoke must not start.

## 12. Recommended next ZDoc step

Because the current repository does not yet have a real safe endpoint, the recommended next step is:

```text
ZDoc Step 14F：ZDoc local-LLM preview isolated safe endpoint guard + fake-only implementation plan
```

The next step must not directly execute service smoke.

## 13. Closure statement

Step 14E confirms that ZDoc currently has a safe fake-only service entry helper, but no real safe endpoint and no real safe UI entry.

The helper remains pure function / helper layer only. It has not been called by `backend/app/main.py`, `backend/app/routers/actions_bridge.py`, `backend/app/routers/zhifei_autoplan.py`, `app.py`, or `frontend_web/app.py`.

Direct service smoke is not recommended because existing routes such as `/generate`, `/export_docx`, and `/review/apply` remain present and can be mistaken for smoke targets. A future service smoke requires a real isolated safe endpoint first.

This document authorizes no endpoint implementation, no UI implementation, no test changes, no pytest run, no service startup, no Ollama run, no `ollama serve`, no external model/API call, no model download or pull, no formal document generation, no `output/job/export` write, no DOCX / JSON / Markdown formal export, and no ZBid formal writeback.
