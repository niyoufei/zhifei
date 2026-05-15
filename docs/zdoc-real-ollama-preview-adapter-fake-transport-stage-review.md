# ZDoc Real Ollama Preview Adapter Fake Transport Stage Review

## 1. Purpose

This document records the ZDoc Step 18 stage review after ZDoc Step 17 completed the real-Ollama preview adapter / transport fake-only implementation.

The review archives the implementation scope, feature flags, fake transport behavior, deterministic test coverage, non-integration boundaries, remaining risks, and prerequisites for any later real runtime smoke.

This document is docs-only. It does not modify code, add or modify tests, run pytest, start services, run Ollama, run `ollama serve`, access `127.0.0.1:11434`, call external model/API transports, download or pull models, generate formal documents, write `output/`, `job/`, or `export/`, trigger DOCX / JSON / Markdown formal export, or connect ZBid formal writeback.

This document must not be interpreted as permission to immediately access real Ollama or start service smoke.

## 2. Baseline before ZDoc Step 17

The baseline before Step 17 was the Step 16 adapter / transport guard design:

```text
docs/zdoc-real-ollama-preview-adapter-guard-test-design.md
```

The inherited baseline was:

- ZDoc had completed the fake-only local-LLM preview stage closure.
- The isolated safe endpoint existed as `POST /local-llm/preview-safe`.
- Fake-only service smoke had already passed.
- ZDoc had not connected real Ollama.
- ZDoc had not run a real model.
- ZDoc had not connected the formal generation chain.
- ZDoc had not connected the export chain.
- ZDoc had not connected ZBid formal writeback.
- Any real-Ollama preview work had to remain default-off, preview-only, no-write, no-generation-chain, no-export-chain, and no-ZBid-writeback.

## 3. Files changed in ZDoc Step 17

ZDoc Step 17 changed only implementation and test files that were explicitly in scope.

Actual implementation file changed:

```text
backend/zhifei_autoplan/ollama_preview.py
```

Actual test file changed:

```text
backend/tests/test_ollama_preview.py
```

Step 17 did not change:

- `backend/tests/test_local_llm_preview_safe_endpoint.py`;
- `backend/app/main.py`;
- `backend/app/routers/local_llm_preview_safe.py`;
- `backend/app/routers/actions_bridge.py`;
- `backend/app/routers/zhifei_autoplan.py`;
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`;
- `app.py`;
- `frontend_web/app.py`;
- `output/`;
- `job/`;
- `export/`;
- formal generation-chain files;
- formal export-chain files;
- ZBid formal writeback files.

## 4. Feature flag behavior

The existing preview top-level flag remains:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

ZDoc Step 17 added the real adapter / transport feature flag:

```text
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

The required behavior is:

- if `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is absent or false-like, the adapter returns disabled immediately;
- if `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is disabled, the adapter does not inspect or call transport;
- if `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` is absent or false-like, the adapter returns disabled;
- if the adapter flag is disabled, the adapter does not call fake transport or model transport;
- enabling the fake transport path does not authorize real Ollama runtime access.

False-like values include:

- absent;
- empty;
- `false`;
- `0`;
- `no`;
- `off`.

## 5. Fake transport behavior review

ZDoc Step 17 implemented a fake-only adapter / transport structure.

The adapter entry point is represented by:

```text
run_zdoc_ollama_preview
```

The fake transport path:

- uses injected fake tags transport;
- uses injected fake generate transport;
- does not default to a real network transport;
- does not access `127.0.0.1:11434`;
- does not access external model/API transports;
- does not run Ollama;
- does not run `ollama serve`;
- does not download or pull models;
- does not execute `ollama pull`;
- does not write files;
- does not call generation, export, or ZBid writeback functions.

When fake generation succeeds, the adapter returns preview advisory / suggestions only. It does not return formal正文 replacement content, formal output paths, export paths, job ids, DOCX paths, Markdown paths, or JSON paths.

Every ok and failure response preserves:

- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- `affects_zbid_writeback=false`.

The adapter also reports fake-only guard metadata such as no model downloads, no model pulls, no output writes, no generation-chain trigger, no export-chain trigger, and no ZBid writeback trigger.

## 6. Model selection behavior review

ZDoc Step 17 added fake-only model selection behavior through:

```text
select_zdoc_local_ollama_model
```

The model selection path:

- calls only injected fake tags transport;
- uses the local target shape `http://127.0.0.1:11434/api/tags` in fake tests;
- selects the first available fake model when no explicit model is requested;
- supports an explicit requested model only if it appears in the fake tags list;
- returns stable `model_unavailable` failure when fake tags returns an empty model list;
- returns stable failure when the fake tags transport is unavailable, times out, or returns invalid data;
- does not download models;
- does not pull models;
- does not execute `ollama pull`;
- does not fall back to external model providers.

This is a fake transport structure only. It does not prove that the local Ollama runtime is installed, serving, reachable, or has a usable model.

## 7. Failure schema review

ZDoc Step 17 implemented deterministic success and failure response shapes for the fake transport adapter.

Covered stable states include:

- `disabled`;
- `ollama_preview_disabled`;
- `ollama_unreachable`;
- `model_unavailable`;
- `timeout`;
- `invalid_response`;
- `transport_failure`;
- `ok`.

Failure examples covered by deterministic tests include:

- total preview flag absent or false-like;
- adapter flag absent or false-like;
- fake tags empty;
- fake tags unreachable;
- fake generate timeout;
- fake generate invalid JSON / invalid response;
- fake generate error field;
- fake transport failure;
- adapter enabled without injected fake transports.

Any failure remains advisory-only and no-write. A failure must not modify正文, write `output/job/export`, trigger formal generation, trigger formal export, or connect ZBid formal writeback.

## 8. Deterministic test coverage

ZDoc Step 17 extended deterministic fake-only tests in:

```text
backend/tests/test_ollama_preview.py
```

The test coverage verifies:

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` absent returns disabled;
- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=false/0/no/off` returns disabled;
- total preview flag disabled does not inspect or call adapter transport;
- `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` absent returns disabled;
- adapter flag false-like values return disabled;
- adapter disabled does not call fake transport or model transport;
- adapter enabled with fake tags can select a model;
- fake tags empty returns `model_unavailable`;
- fake tags unreachable returns stable failure;
- fake generate success returns preview-only result;
- fake generate timeout returns `timeout`;
- fake generate invalid JSON returns `invalid_response`;
- fake generate error field returns stable failure;
- fake transport failure returns `transport_failure`;
- enabled without injected fake transport does not access real Ollama;
- ok and failure paths keep `preview_only=true`;
- ok and failure paths keep `no_write=true`;
- ok and failure paths keep `affects_generation=false`;
- ok and failure paths keep `affects_export=false`;
- no path writes `output/job/export`;
- no path triggers generation chain;
- no path triggers export chain;
- no path connects ZBid writeback;
- existing fake-only helper tests continue to pass;
- existing safe endpoint tests continue to pass.

The Step 17 test command was:

```text
python3 -m pytest backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

The final test result was:

```text
115 passed in 3.04s
```

## 9. Explicit non-integrations

ZDoc Step 17 did not integrate real Ollama.

The stage did not:

- run Ollama;
- run `ollama serve`;
- start any service;
- access `127.0.0.1:11434`;
- call external model/API transports;
- call OpenAI;
- call Spark;
- call Gemini;
- download models;
- pull models;
- execute `ollama pull`;
- generate formal documents;
- write `output/`;
- write `job/`;
- write `export/`;
- trigger DOCX / JSON / Markdown formal export;
- connect formal generation;
- connect formal export;
- connect ZBid formal writeback.

## 10. No-write boundary

The no-write boundary remains active.

The adapter responses must not write:

- `output/`;
- `job/`;
- `export/`;
- formal DOCX artifacts;
- formal JSON artifacts;
- formal Markdown artifacts;
- formal正文 replacements;
- ZBid writeback payloads.

Step 17 tests include write-surface count checks and response-field checks to preserve this boundary.

## 11. No-generation-chain boundary

The real-Ollama preview adapter fake transport path is not a generation-chain step.

It must not:

- call `/generate`;
- invoke formal generation functions;
- create generated sections;
- update generated正文;
- return fields that can be mistaken for formal generated content;
- create formal output artifacts.

The adapter returns advisory / suggestions only.

## 12. No-export-chain boundary

The real-Ollama preview adapter fake transport path is not an export-chain step.

It must not:

- call `/export_docx`;
- trigger DOCX export;
- trigger JSON export;
- trigger Markdown export;
- return export paths;
- write export artifacts;
- update export state.

## 13. No-ZBid-writeback boundary

The real-Ollama preview adapter fake transport path is not a ZBid writeback path.

It must not:

- call `/review/apply`;
- call ZBid formal writeback logic;
- modify `backend/zhifei_autoplan/zbid_snapshot_mapper.py`;
- create writeback payloads;
- apply preview suggestions to formal正文;
- update ZBid state.

## 14. Remaining risks

The remaining risks are:

- current work only completes the fake transport structure;
- current work has not accessed real Ollama;
- fake transport tests do not prove that local Ollama is installed;
- fake transport tests do not prove that local Ollama is serving on `127.0.0.1:11434`;
- fake transport tests do not prove that any local model exists;
- fake transport tests do not prove that real model output can be normalized safely;
- current work has not started a service;
- current work has not generated formal documents;
- current work has not connected formal generation;
- current work has not connected formal export;
- current work has not connected ZBid writeback;
- future real runtime smoke must be separately authorized;
- future real runtime smoke must use Window 2 if `ollama serve` is required;
- future work must not download or pull models unless separately authorized;
- future work must not write `output/job/export`;
- future work must not automatically modify正文;
- future work must not trigger formal export;
- future work must not connect ZBid writeback.

Any high-risk chain must remain blocked until a separate design, implementation, smoke, and ChatGPT review cycle authorizes it.

## 15. Runtime smoke prerequisites

Before any real runtime smoke, all of the following must be true:

- Step 18 stage review is archived.
- A docs-only runtime smoke plan is completed.
- The runtime smoke plan explicitly names the request path.
- The runtime smoke plan confirms whether the isolated safe endpoint is used.
- The runtime smoke plan confirms that `/generate` is not requested.
- The runtime smoke plan confirms that `/export_docx` is not requested.
- The runtime smoke plan confirms that `/review/apply` is not requested.
- Window 2 usage is explicitly authorized if `ollama serve` is needed.
- Codex access is limited to local loopback.
- No model download or model pull is performed.
- No `ollama pull` is performed.
- No `output/job/export` writes occur.
- No formal generation-chain trigger occurs.
- No export-chain trigger occurs.
- No ZBid writeback occurs.
- Completion is followed by a smoke report and ChatGPT review.

Real runtime smoke must be treated as a separate step. It must not be folded into this review.

## 16. Recommended next ZDoc step

The recommended next step is docs-only:

```text
ZDoc Step 19: real-Ollama preview runtime smoke 前置计划文档
```

This next step is a plan document only. It must not directly start real runtime smoke, run Ollama, run `ollama serve`, access `127.0.0.1:11434`, connect formal generation, connect formal export, or connect ZBid writeback.

## 17. Closure statement

ZDoc Step 17 established a fake-only real-Ollama preview adapter / transport structure and verified it with deterministic tests. The implementation keeps the preview top-level flag, adds a subordinate adapter flag, requires injected fake transports, returns stable ok and failure schemas, and preserves preview-only / no-write / no-generation / no-export / no-ZBid boundaries.

The stage does not prove that real Ollama is available or safe to use. It does not authorize real runtime smoke, real model access, service startup, formal generation-chain integration, export-chain integration, or ZBid formal writeback.
