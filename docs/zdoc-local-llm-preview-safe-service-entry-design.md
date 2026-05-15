# ZDoc Local LLM Preview Safe Service Entry Design

## 1. Purpose

This document records the ZDoc Step 14A pre-design for a safe fake-only local-LLM preview service entry.

The current stage only designs a safe service entry. It does not implement endpoint code, does not modify UI code, does not modify tests, does not run pytest, does not start a service, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not run formal document generation, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately modify endpoint / UI files or start a service.

## 2. Baseline inherited from service-entry read-only audit

The service-entry read-only audit found that ZDoc already has real service and UI entry points, plus generation, export, and write/apply paths that are not safe smoke targets for the local-LLM preview fake-only helper.

The current baseline is:

- The current branch is `main`.
- The current stable Step 13 baseline tag is `v0.1.60-zdoc-local-llm-preview-endpoint-ui-service-smoke-plan`.
- The current fake-only helper exists in `backend/zhifei_autoplan/ollama_preview.py`.
- The current fake-only API / task bridge helper exists.
- The current endpoint / UI entry fake helper exists.
- The current feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- The helper-level fake entry remains default-off.
- The helper-level fake entry remains preview-only.
- The helper-level fake entry remains no-write.
- The helper-level fake entry remains disconnected from real endpoint registration.
- The helper-level fake entry remains disconnected from real UI page files.
- The helper-level fake entry remains disconnected from formal generation chains.
- The helper-level fake entry remains disconnected from formal export chains.
- The helper-level fake entry remains disconnected from ZBid formal writeback.

The audit conclusion is that immediate service smoke is not recommended until a clearly isolated fake-only preview endpoint / service entry exists.

## 3. Existing service and UI entry inventory

Current service and UI inventory includes:

- `backend/app/main.py` exists and defines a real FastAPI application.
- `backend/app/main.py` includes routers for ingest, retrieve, publish, score, ZDoc autoplan, actions bridge, and auth.
- `app/main.py` exists and re-exports the canonical FastAPI app from `backend.app.main`.
- `backend/app/routers/actions_bridge.py` exists and contains real business routes.
- `backend/app/routers/zhifei_autoplan.py` exists and contains real business routes.
- `app.py` exists and is a Streamlit UI entry.
- `app.py` contains Streamlit buttons, including local model preview / section review controls and a one-click generation control.
- `frontend_web/app.py` exists and is a Flask page entry.
- `frontend_web/templates/index.html` contains a Word document generation button.

These entries are real application surfaces. They are not, by themselves, a safe fake-only local-LLM preview smoke entry.

## 4. Existing generation/export/writeback risk paths

The current repository contains risk paths that must not be targeted by local-LLM preview service smoke:

- `backend/app/main.py` contains real FastAPI routes such as `/compose` and `/export`.
- `backend/app/routers/actions_bridge.py` contains business route risk.
- `backend/app/routers/zhifei_autoplan.py` contains business route risk.
- `/generate` may trigger the formal generation chain.
- `/export_docx` may trigger the formal export chain.
- `/review/apply` may trigger writeback or apply-style logic.
- `app.py` contains Streamlit UI entry and buttons.
- `frontend_web/app.py` contains a Flask page entry.
- `backend/zhifei_autoplan/export_docx_service.py` belongs to the export risk chain.
- `backend/zhifei_autoplan/output_artifacts.py` belongs to the output artifact risk chain.
- `backend/zhifei_autoplan/job_store.py` and related routes belong to job write risk.
- ZBid mock preview exists, but it is not a local-LLM fake-only smoke entry and must not be confused with ZBid formal writeback.

Without an isolated fake-only endpoint, service smoke could accidentally validate or touch a route that has generation, export, job, output, review-apply, or writeback behavior.

## 5. Why immediate service smoke is not recommended

Immediate service smoke is not recommended because Step 11 prepared only pure-function endpoint / UI fake helper behavior. It did not register a real endpoint, did not modify a real UI page, and did not create a service-level route that can be safely called by loopback smoke.

The unsafe immediate-smoke conditions are:

- There is no clear fake-only service route dedicated to local-LLM preview diagnostics.
- Existing FastAPI apps include `/generate`, `/export_docx`, `/review/apply`, `/compose`, and `/export`.
- Existing Streamlit UI includes buttons that can interact with preview, review, generation, and export-related flows.
- Existing Flask UI includes a document generation affordance.
- Existing export and output artifact modules can write files.
- Existing job-related modules can create or update job state.
- Existing review-apply routes can alter generated content state.

Therefore, service smoke must wait until a safe fake-only service entry is designed, tested, and explicitly authorized.

## 6. Safe fake-only service entry objective

A future safe service entry should provide an isolated preview / diagnostics route or pure service entry for fake-only local-LLM preview behavior.

The safe entry objective is:

- It is independent from formal generation routes.
- It is independent from formal export routes.
- It is independent from review apply routes.
- It is default disabled.
- It accepts only read-only input.
- It returns only preview advisory / suggestions.
- It returns `preview_only=true`.
- It returns `no_write=true`.
- It returns `affects_generation=false`.
- It returns `affects_export=false`.
- It returns `affects_zbid_writeback=false`.
- It does not modify正文.
- It does not write `output/`, `job/`, or `export/`.
- It does not trigger the generation chain.
- It does not trigger the export chain.
- It does not connect ZBid formal writeback.
- It does not call real Ollama.
- It does not call external model/API transports.
- It exists only for later `127.0.0.1` loopback smoke.

The entry may call only `run_zdoc_local_llm_preview_task` or an equivalent fake-only bridge. It must not call real transports or any formal chain.

## 7. Forbidden route and chain boundary

The future safe entry must never call or delegate to:

- `/generate`
- `/export_docx`
- `/review/apply`
- `/compose`
- `/export`
- formal generation-chain functions
- formal export-chain functions
- output artifact save functions
- job create/update functions
- review apply / remediation functions
- ZBid formal writeback functions
- real Ollama transport functions
- external model/API transport functions

The future safe entry must not:

- write `output/`;
- write `job/`;
- write `export/`;
- write `build/`;
- create DOCX;
- create formal Markdown;
- create formal JSON;
- modify正文;
- change generated sections;
- trigger UI writeback;
- trigger UI generation;
- trigger UI export;
- download models;
- pull models;
- execute `ollama pull`;
- listen on `0.0.0.0` during smoke.

## 8. Proposed safe endpoint boundary

If a later step authorizes endpoint implementation, the safe endpoint should be a dedicated preview / diagnostics route.

The proposed endpoint boundary is:

- It must be named as a local-LLM preview diagnostics endpoint.
- It must be disabled by default through `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- Disabled mode must not call the fake bridge.
- Enabled mode may call only the fake-only bridge.
- It must not call `/generate`.
- It must not call `/export_docx`.
- It must not call `/review/apply`.
- It must not call formal generation helpers.
- It must not call formal export helpers.
- It must not call job writers.
- It must not call output artifact writers.
- It must not call ZBid formal writeback.
- It must not call real Ollama.
- It must not call external model/API transports.
- It must return a response clearly marked as preview-only and no-write.
- It must not return fields that can be mistaken for formal generated artifacts, such as `job_id`, `export_path`, `docx_path`, `markdown_path`, `json_path`, or formal result paths.

The endpoint must be safe for later loopback smoke only after deterministic tests prove the boundary.

## 9. Proposed safe UI boundary

If a later step authorizes UI work, the UI entry must remain separate from any one-click generation, export, review-apply, or writeback action.

The proposed UI boundary is:

- UI preview entry must be manually triggered.
- UI preview entry must be hidden or disabled unless the feature flag is enabled.
- UI preview entry must call only the safe fake-only preview entry.
- UI preview entry must display only preview advisory / suggestions.
- UI preview entry must label output as preview / diagnostics.
- UI preview entry must not write preview content to正文.
- UI preview entry must not provide one-click writeback to正文.
- UI preview entry must not start generation.
- UI preview entry must not trigger DOCX / JSON / Markdown export.
- UI preview entry must not trigger ZBid writeback.
- UI preview entry must not save preview content to `output/`, `job/`, or `export/`.
- UI preview entry must not imply formal scoring, formal generation, or formal review conclusion.

The UI boundary must be documented and tested before any real UI file is modified.

## 10. Feature flag and manual trigger boundary

The feature flag remains:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

Disabled values:

- absent
- empty
- `false`
- `0`
- `no`
- `off`

Enabled values:

- `true`
- `1`
- `yes`
- `on`

Disabled behavior has highest priority. Disabled behavior must return a stable disabled response and must not call the fake bridge.

Enabled behavior must remain fake-only and manually triggered. Automatic trigger, background trigger, startup trigger, scheduled trigger, or UI auto-trigger must return stable failure or remain unreachable.

The safe service entry must not create a second flag that bypasses `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`. Any future endpoint-specific or UI-specific flag must be stricter than, and subordinate to, this flag.

## 11. No-write verification boundary

Future safe entry implementation must include no-write verification before service smoke is allowed.

Verification must prove:

- no write to `output/`;
- no write to `job/`;
- no write to `export/`;
- no formal DOCX creation;
- no formal Markdown creation;
- no formal JSON creation;
- no mutation of正文 sections;
- no generation-chain call;
- no export-chain call;
- no ZBid formal writeback call;
- no real Ollama call;
- no external model/API call;
- no model download;
- no model pull.

Where practical, tests should use call counters, stubs, path-count checks, or monkeypatched forbidden functions to prove that forbidden paths are not called.

## 12. Future deterministic tests requirements

Before implementation or service smoke, a later Step 14B design must define the deterministic test matrix. At minimum, future tests must cover:

1. safe endpoint default disabled.
2. disabled mode does not call the fake bridge.
3. disabled mode does not write `output/job/export`.
4. enabled mode calls only the fake-only bridge.
5. enabled mode returns `preview_only=true`.
6. enabled mode returns `no_write=true`.
7. enabled mode returns `affects_generation=false`.
8. enabled mode returns `affects_export=false`.
9. enabled mode does not call `/generate`.
10. enabled mode does not call `/export_docx`.
11. enabled mode does not call `/review/apply`.
12. enabled mode does not write `output/job/export`.
13. enabled mode does not modify正文.
14. enabled mode does not connect ZBid formal writeback.
15. enabled mode does not call real Ollama.
16. enabled mode does not call external model/API transports.
17. tests do not start a real service unless a later service-smoke step explicitly authorizes it.
18. existing `backend/tests/test_ollama_preview.py` must continue to pass.

The tests must remain fake-only. They must not run Ollama, run `ollama serve`, start a service, call external model/API transports, download or pull models, generate documents, write `output/`, write `job/`, write `export/`, trigger formal export, or connect ZBid formal writeback.

## 13. Future service smoke prerequisites

Future service smoke may be reconsidered only after all of the following are true:

- This Step 14A design has been archived.
- A safe fake-only endpoint / service entry implementation has been explicitly authorized and completed.
- Deterministic tests for the safe entry have been completed.
- The smoke target is only the safe endpoint.
- The smoke target is not `/generate`.
- The smoke target is not `/export_docx`.
- The smoke target is not `/review/apply`.
- The smoke target is not `/compose`.
- The smoke target is not `/export`.
- The smoke request uses synthetic bounded input.
- The smoke verifies disabled behavior.
- The smoke verifies enabled fake-only behavior.
- The smoke confirms no write to `output/job/export`.
- The smoke confirms no generation-chain trigger.
- The smoke confirms no export-chain trigger.
- The smoke confirms no ZBid formal writeback.
- The smoke confirms no real Ollama call.
- The smoke confirms no external model/API call.
- The smoke binds only to `127.0.0.1`.
- The smoke does not bind to `0.0.0.0`.
- The smoke records service PID and shutdown method.
- The smoke verifies service stopped state.
- The smoke does not need 2号窗口 unless a later stage enters real Ollama.

If any prerequisite is missing, service smoke must stop before startup.

## 14. Recommended next ZDoc step

The recommended next step is docs-only:

```text
ZDoc Step 14B：ZDoc local-LLM preview safe fake-only service entry guard + deterministic tests 前置设计文档
```

The next step must not go directly into code implementation, service smoke, real Ollama, formal generation chains, formal export chains, or ZBid writeback.

## 15. Closure statement

Step 14A closes with a conservative service-entry boundary: the repository has real FastAPI, Streamlit, Flask, generation, export, job, output, review-apply, and ZBid-adjacent surfaces, but it does not yet have an isolated fake-only preview service entry that is safe to smoke.

The immediate service-smoke path is therefore blocked until a safe fake-only endpoint / service entry is separately designed, guarded, implemented, tested, and approved.

This document authorizes no code changes, no test changes, no service startup, no Ollama execution, no external model/API calls, no formal document generation, no `output/job/export` writes, no DOCX / JSON / Markdown formal export, and no ZBid formal writeback.
