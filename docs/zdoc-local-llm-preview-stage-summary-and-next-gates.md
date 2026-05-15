# ZDoc Local LLM Preview Stage Summary and Next Gates

## 1. Purpose

This document summarizes the current ZDoc local-LLM preview stage after the fake-only helper, API/task bridge, endpoint/UI helper, safe service entry, isolated safe endpoint, and isolated safe endpoint service smoke milestones.

It records what has been completed, which capabilities were verified by fake-only deterministic tests, which boundary was verified by loopback service smoke, what remains explicitly disconnected, and what gates must be satisfied before any later real Ollama, formal generation-chain, formal export-chain, or ZBid formal writeback work.

This document is docs-only. It does not modify code, does not add or modify tests, does not run pytest, does not run Ollama, does not run `ollama serve`, does not start services, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

## 2. Stage scope and boundary

The current stage is a controlled ZDoc local-LLM preview foundation.

Its allowed scope has been:

- design and gap analysis;
- fake-only helper implementation;
- fake-only deterministic tests;
- API/task bridge helper implementation;
- endpoint/UI entry helper implementation;
- safe fake-only service entry helper implementation;
- isolated safe endpoint implementation;
- isolated safe endpoint deterministic tests;
- isolated safe endpoint loopback service smoke;
- docs-only stage reviews and gates.

Its hard boundary remains:

- default-off;
- fake-only;
- preview-only;
- no-write;
- no formal generation-chain integration;
- no formal export-chain integration;
- no ZBid formal writeback;
- no real Ollama transport;
- no external model/API transport.

## 3. Completed milestones summary

The stage began with Step 1 gap analysis and Qingtian boundary reuse design. That document established that ZDoc should reuse the default-off, preview-only, no-write, fake-only tests first, and separately authorized runtime smoke boundaries before any local model integration.

The first implementation layer added the fake-only helper guard in `backend/zhifei_autoplan/ollama_preview.py`. That helper made `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` the controlling feature flag, returned stable disabled output when the flag was absent or false-like, and returned deterministic advisory / suggestions only when enabled.

The API/task bridge layer then added fake-only bridge helpers over the local-LLM preview helper. This preserved disabled-first behavior and returned preview-only / no-write response structures without registering a real endpoint or touching generation, export, or ZBid writeback paths.

The endpoint/UI entry helper layer added pure helper support for future endpoint or UI presentation. It still did not register a real endpoint and did not modify real UI pages. It made the display/entry shape explicit while keeping the capability fake-only, preview-only, and no-write.

The safe fake-only service entry helper layer narrowed the service-smoke boundary further. It established that any future service entry must be isolated from `/generate`, `/export_docx`, and `/review/apply`, and that the helper path must not write `output/job/export`.

The isolated safe endpoint design and guard work then determined that a real safe endpoint was required before service smoke. The implementation added `POST /local-llm/preview-safe` as an isolated route in `backend/app/routers/local_llm_preview_safe.py`, included it from `backend/app/main.py`, and added deterministic endpoint tests.

The isolated safe endpoint service smoke verified the endpoint through a local loopback FastAPI service on `127.0.0.1:18749`. It validated disabled and enabled fake-only behavior and confirmed that no high-risk route was requested.

The most recent stage review archived that Step 14K service smoke and confirmed that it does not authorize real Ollama, formal generation, formal export, or ZBid writeback.

## 4. Verified capabilities

The following capabilities have been verified by fake-only deterministic tests:

- feature flag absent / empty / false / `0` / `no` / `off` returns disabled;
- disabled mode does not call fake preview builders or model clients;
- enabled mode returns deterministic fake advisory / suggestions;
- enabled mode returns `preview_only=true`;
- enabled mode returns `no_write=true`;
- enabled mode returns `affects_generation=false`;
- enabled mode returns `affects_export=false`;
- enabled mode does not modify source section text;
- enabled mode does not write `output/job/export`;
- enabled mode does not trigger formal generation;
- enabled mode does not trigger formal export;
- enabled mode does not connect ZBid formal writeback;
- invalid, empty, or missing inputs return stable failure responses;
- API/task bridge behavior remains fake-only;
- endpoint/UI entry helper behavior remains fake-only;
- safe service entry helper behavior remains fake-only;
- isolated safe endpoint behavior remains fake-only.

The endpoint implementation stage verified:

- `POST /local-llm/preview-safe` exists;
- the endpoint is default-off;
- disabled endpoint mode returns disabled;
- enabled endpoint mode calls only the fake-only safe helper;
- enabled endpoint mode returns preview-only / no-write markers;
- enabled endpoint mode does not call `/generate`;
- enabled endpoint mode does not call `/export_docx`;
- enabled endpoint mode does not call `/review/apply`;
- endpoint tests do not start a real service process;
- endpoint tests do not run Ollama.

The strongest deterministic test baseline for the endpoint stage was:

```text
python3 -m pytest backend/tests/test_local_llm_preview_safe_endpoint.py backend/tests/test_ollama_preview.py -q
96 passed in 4.97s
```

## 5. Verified safety boundaries

The current local-LLM preview stage has verified these safety boundaries:

- `default-off`;
- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- fake-only behavior;
- isolated safe endpoint behavior;
- loopback-only service smoke;
- no request to `/generate`;
- no request to `/export_docx`;
- no request to `/review/apply`;
- no write to `output/`;
- no write to `job/`;
- no write to `export/`;
- no formal DOCX export;
- no formal JSON export;
- no formal Markdown export;
- no formal generation-chain trigger;
- no formal export-chain trigger;
- no ZBid formal writeback;
- no real Ollama call;
- no external model/API call;
- no model download or pull.

The safe endpoint remains a diagnostics / preview surface, not a generation, export, apply, or writeback surface.

## 6. Service smoke validation summary

ZDoc Step 14K performed the only service smoke in this stage.

Service smoke boundary:

- service address: `127.0.0.1`
- service port: `18749`
- requested endpoint: `POST /local-llm/preview-safe`
- forbidden endpoints not requested: `/generate`, `/export_docx`, `/review/apply`

Disabled scenario:

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` unset;
- response returned `status=disabled`;
- response returned `preview_only=true`;
- response returned `no_write=true`;
- response returned `affects_generation=false`;
- response returned `affects_export=false`;
- response reported no generation/export/writeback route calls.

Enabled fake-only scenario:

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`;
- response returned `status=ok`;
- response returned fake-only advisory / suggestions;
- response returned `preview_only=true`;
- response returned `no_write=true`;
- response returned `affects_generation=false`;
- response returned `affects_export=false`;
- response reported no generation/export/writeback route calls.

Process and artifact checks:

- all service processes were stopped;
- port `18749` had no listener after smoke;
- `output/` file count remained `0`;
- `job/` file count remained `0`;
- `export/` file count remained `0`;
- `backend/data/autoplan/jobs` file count remained unchanged at `87`;
- no formal DOCX / JSON / Markdown artifact was produced.

## 7. What is explicitly not connected yet

The current stage has not connected:

- real Ollama;
- real model runtime integration;
- external model/API transports;
- production UI entry;
- production endpoint / UI workflow beyond the isolated safe endpoint;
- formal generation chain;
- formal export chain;
- DOCX / JSON / Markdown formal export;
- ZBid formal writeback;
- formal apply / writeback logic;
- automatic model invocation;
- automatic document revision;
- automatic generation or export actions.

The isolated safe endpoint exists, but it is still a fake-only preview / diagnostics surface. It must not be described as a real local model endpoint, a production generation endpoint, an export endpoint, or a ZBid writeback endpoint.

## 8. What this stage safely enables

This stage safely enables future planning from a controlled baseline:

- ZDoc now has a documented local-LLM preview safety model;
- ZDoc now has a default-off fake-only preview helper;
- ZDoc now has fake-only bridge helpers for API/task style callers;
- ZDoc now has pure helper support for endpoint/UI presentation;
- ZDoc now has a safe fake-only service entry helper;
- ZDoc now has an isolated safe endpoint at `POST /local-llm/preview-safe`;
- ZDoc has deterministic tests for fake-only helper and endpoint boundaries;
- ZDoc has loopback smoke evidence that the isolated safe endpoint can be exercised without touching high-risk routes.

This stage enables the next docs-only analysis for real-Ollama preview integration. It does not enable immediate implementation of real Ollama.

## 9. What this stage still does not allow

This stage still does not allow:

- running Ollama;
- running `ollama serve`;
- calling real Ollama;
- calling external model/API transports;
- downloading or pulling models;
- connecting the preview path to formal generation;
- connecting the preview path to formal export;
- connecting the preview path to ZBid formal writeback;
- calling `/generate`;
- calling `/export_docx`;
- calling `/review/apply`;
- writing `output/`;
- writing `job/`;
- writing `export/`;
- generating formal DOCX / JSON / Markdown artifacts;
- modifying正文 automatically;
- adding a production UI writeback button;
- adding one-click formal document generation from preview output;
- treating fake-only test success as real model validation.

No high-risk chain may be advanced automatically from this milestone.

## 10. Next-phase admission gates

### 10.1 Real Ollama preview admission gate

If a future stage enters real Ollama preview integration, it must first satisfy all of these gates:

1. Complete a docs-only real-Ollama preview gap analysis.
2. Complete a guard + deterministic tests design document.
3. Define the exact allowed file scope and forbidden file scope.
4. Preserve `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` or define a stricter subordinate flag.
5. Preserve default-off behavior.
6. Preserve preview-only behavior.
7. Preserve no-write behavior.
8. Prove real Ollama is never called when disabled.
9. Prove real Ollama output cannot modify正文 automatically.
10. Prove real Ollama output cannot write `output/job/export`.
11. Prove real Ollama output cannot trigger formal generation.
12. Prove real Ollama output cannot trigger formal export.
13. Prove real Ollama output cannot connect ZBid formal writeback.
14. Add fake-only tests before any real transport smoke.
15. Add or update implementation only after the design gate is approved.
16. Run loopback runtime smoke only in a separately authorized stage.
17. Use 2号窗口 only after explicit authorization for a real Ollama stage.
18. Wait for ChatGPT review before moving to the next gate.

Real Ollama preview admission is not a one-step implementation task.

### 10.2 Formal generation / export / writeback admission gate

If a future stage enters the formal generation chain, formal export chain, or ZBid formal writeback, it must first satisfy all of these gates:

1. Complete a separate gap analysis for the target chain.
2. Complete a separate guard design.
3. Complete a separate test design.
4. Identify all write paths and artifact paths.
5. Identify all rollback or non-adoption behavior.
6. Identify exact allowed files and forbidden files.
7. Implement in a separate, explicitly authorized step.
8. Test in a separate, explicitly authorized step.
9. Smoke in a separate, explicitly authorized step.
10. Review in a separate, explicitly authorized step.
11. Avoid crossing directly from preview smoke to production chain integration.
12. Wait for ChatGPT review before moving to the next gate.

Formal generation, export, and writeback must not be combined into a single broad implementation request.

## 11. Recommended next ZDoc step

Recommended next step:

```text
ZDoc Step 15：ZDoc local-LLM real-Ollama preview 接入差距分析（docs-only）
```

This next step should only analyze the gap for real-Ollama preview integration. It should not implement real Ollama, should not run Ollama, should not run `ollama serve`, should not start service smoke, should not connect formal generation, should not connect formal export, and should not connect ZBid formal writeback.

## 12. Closure statement

The current ZDoc local-LLM preview stage has completed a controlled fake-only, default-off, preview-only, no-write preview foundation and validated the isolated safe endpoint by loopback service smoke.

It remains explicitly disconnected from real Ollama, real model runtime integration, formal generation, formal export, and ZBid formal writeback. Any next stage must proceed through a separate design gate and must stop for ChatGPT review before implementation or runtime execution.
