# ZDoc Real Ollama Preview Gap Analysis

## 1. Purpose

This document records the ZDoc Step 15 real-Ollama preview gap analysis.

The current stage is docs-only. It analyzes the gap between the completed fake-only local-LLM preview foundation and any future real Ollama preview integration. It does not implement real Ollama, does not modify code, does not add or modify tests, does not run pytest, does not start services, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately connect real Ollama.

## 2. Current fake-only baseline

ZDoc has completed the fake-only local-LLM preview stage closure.

The completed fake-only baseline includes:

- fake-only helper layer in `backend/zhifei_autoplan/ollama_preview.py`;
- API / task bridge fake-only capability;
- endpoint / UI entry fake-only helper capability;
- safe fake-only service entry helper capability;
- isolated safe endpoint implementation;
- isolated safe endpoint fake-only deterministic tests;
- isolated safe endpoint fake-only loopback service smoke;
- stage summary and next-gate documentation in `docs/zdoc-local-llm-preview-stage-summary-and-next-gates.md`.

The current verified endpoint is:

```text
POST /local-llm/preview-safe
```

Current verified safety markers include:

- `default-off`;
- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- fake-only behavior;
- no request to `/generate`;
- no request to `/export_docx`;
- no request to `/review/apply`;
- no write to `output/job/export`;
- no DOCX / JSON / Markdown formal export;
- no ZBid formal writeback.

The current fake-only conclusion means the preview boundary is established. It does not mean a real model is production-ready.

## 3. Existing safe endpoint capability

The isolated safe endpoint is implemented as:

```text
POST /local-llm/preview-safe
```

The endpoint is registered through `backend/app/main.py` and implemented in `backend/app/routers/local_llm_preview_safe.py`.

The endpoint currently:

- uses `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` as the controlling feature flag;
- returns disabled when the flag is absent or false-like;
- accepts only minimal preview payload fields;
- rejects formal output fields such as `job_id`, `output_path`, `export_path`, `docx_path`, `markdown_path`, and `json_path`;
- calls the fake-only safe service entry when enabled;
- returns advisory / suggestions only;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- reports `calls_ollama=false`;
- reports `calls_external_model_api=false`.

The endpoint is intentionally isolated from:

- `/generate`;
- `/export_docx`;
- `/review/apply`;
- formal generation;
- formal export;
- ZBid formal writeback.

This endpoint is a safe diagnostics / preview surface. It is not a real Ollama endpoint yet.

## 4. Gap to real Ollama preview

The main gap is that the currently verified path is fake-only.

ZDoc still has not connected:

- real Ollama runtime;
- real model selection for preview;
- real request transport from the isolated safe endpoint to Ollama;
- real timeout and retry policy for Ollama preview;
- real failure schema for model unavailability, timeout, invalid response, empty response, and malformed content;
- runtime isolation proof for a real model call;
- no-write proof for real model responses;
- no-generation-chain proof for real model responses;
- no-export-chain proof for real model responses;
- no-ZBid-writeback proof for real model responses.

`backend/zhifei_autoplan/ollama_preview.py` already contains Ollama-related helper concepts, including transport, model, timeout, and fallback behavior. However, the current isolated safe endpoint path remains fake-only and does not call a real Ollama transport.

Before real Ollama preview can be considered, ZDoc needs an explicit adapter / transport design that preserves the existing safety boundary and cannot bypass the fake-only gates by accident.

## 5. Required transport design

A future real-Ollama preview transport must be designed before implementation.

The design must define:

- which function owns the real Ollama transport;
- whether an adapter wraps existing Ollama helper functions or introduces a new preview-specific adapter;
- the exact request payload sent to Ollama;
- the exact response fields accepted from Ollama;
- how model output is normalized into advisory / suggestions only;
- how formal正文 replacement fields are blocked;
- how formal artifact fields are blocked;
- how timeout is configured;
- how timeout failure is represented;
- how connection failure is represented;
- how invalid JSON or invalid response shape is represented;
- how empty model content is represented;
- how model selection is configured;
- how the endpoint remains default-off;
- how real model transport is prevented when disabled;
- how `output/job/export` writes are proven absent;
- how `/generate`, `/export_docx`, and `/review/apply` remain unreachable.

The transport design must not assume that real Ollama output is safe to adopt. Model output must stay advisory-only until a later, separately authorized stage says otherwise.

## 6. Required feature flags

The existing feature flag is:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

A future real-Ollama preview design must decide whether to:

- keep this flag as the top-level preview gate;
- add a stricter subordinate real-transport flag;
- require both flags to be enabled before real Ollama can be contacted.

The required behavior is:

- default-off remains the highest priority;
- absent / empty / `false` / `0` / `no` / `off` must disable the preview;
- disabled mode must not call fake bridge or real Ollama transport;
- enabled fake-only mode must remain available for deterministic tests;
- real transport must not be reachable unless separately authorized;
- no endpoint-specific flag may bypass the default-off top-level guard.

Any future flag design must make fake-only tests possible without running Ollama.

## 7. Required fake-only tests

Before a real Ollama implementation is accepted, fake-only tests must be designed and implemented first.

The tests must cover:

1. Real-Ollama adapter disabled when feature flags are absent.
2. Real-Ollama adapter disabled for false-like flag values.
3. Disabled mode does not call real transport.
4. Disabled mode does not call fake transport unless explicitly in fake-only path.
5. Enabled fake-only mode returns deterministic advisory / suggestions.
6. Fake timeout returns stable failure schema.
7. Fake connection error returns stable failure schema.
8. Fake invalid response returns stable failure schema.
9. Fake empty response returns stable failure schema.
10. Fake success returns normalized preview-only output.
11. All success responses keep `preview_only=true`.
12. All success responses keep `no_write=true`.
13. All success responses keep `affects_generation=false`.
14. All success responses keep `affects_export=false`.
15. No test writes `output/job/export`.
16. No test triggers `/generate`.
17. No test triggers `/export_docx`.
18. No test triggers `/review/apply`.
19. No test connects ZBid formal writeback.
20. No test runs Ollama.
21. No test runs `ollama serve`.
22. Existing fake-only endpoint tests continue to pass.

Passing fake-only tests must not be presented as proof that real Ollama is available or safe. They only prove the adapter and guard behavior before runtime smoke.

## 8. Required runtime smoke plan

Real runtime smoke must be a separate step after docs-only design, guard/test design, fake-only tests, and implementation review.

The runtime smoke plan must define:

- whether real Ollama may be contacted;
- which model is selected;
- how model availability is checked;
- whether 2号窗口 is required;
- the service or helper invocation boundary;
- loopback-only network scope;
- timeout limit;
- failure stop conditions;
- expected disabled response;
- expected enabled real-preview response;
- no-write verification for `output/job/export`;
- no-generation-chain verification;
- no-export-chain verification;
- no-ZBid-writeback verification;
- service shutdown and cleanup rules if a service is started.

The real runtime smoke stage is the first stage where 2号窗口 may be enabled, and only after explicit authorization. This Step 15 document does not authorize 2号窗口 use and does not authorize running Ollama.

## 9. No-write / no-generation / no-export / no-ZBid boundary

All future real-Ollama preview work must preserve the existing safety boundary:

- remain default-off;
- remain preview-only;
- remain no-write;
- keep `preview_only=true`;
- keep `no_write=true`;
- keep `affects_generation=false`;
- keep `affects_export=false`;
- not write `output/`;
- not write `job/`;
- not write `export/`;
- not trigger formal generation;
- not trigger formal export;
- not request `/generate`;
- not request `/export_docx`;
- not request `/review/apply`;
- not produce DOCX / JSON / Markdown formal artifacts;
- not modify正文 automatically;
- not build formal apply payloads;
- not connect ZBid formal writeback.

Real Ollama output may only be returned as controlled preview advisory / suggestions. It must not be interpreted as正文 replacement, formal scoring, final review result, export content, or ZBid writeback content.

## 10. Recommended next step

Recommended next step:

```text
ZDoc Step 16：real-Ollama preview adapter / transport guard + fake-only tests 前置设计文档
```

Step 16 should remain docs-only. It should design the adapter / transport guard and fake-only tests before any code implementation.

Step 16 must not directly implement real Ollama, must not run Ollama, must not run `ollama serve`, must not start services, must not connect formal generation, must not connect formal export, and must not connect ZBid formal writeback.

## 11. Closure statement

ZDoc has completed the fake-only local-LLM preview baseline and isolated safe endpoint service smoke. The current real-Ollama gap is now explicit: transport, feature flags, timeout handling, model selection, failure schema, fake-only tests, and runtime smoke all still require separate design before real Ollama can be introduced.

This document authorizes no code implementation, no real Ollama call, no model runtime, no service startup, no formal generation-chain work, no formal export-chain work, and no ZBid formal writeback.
