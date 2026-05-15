# ZDoc Real Ollama Preview Adapter Guard and Test Design

## 1. Purpose

This document records the ZDoc Step 16 real-Ollama preview adapter / transport guard and fake-only tests design.

The current stage only designs the adapter, transport, guard, and future deterministic tests. It does not implement code, does not add or modify tests, does not run pytest, does not start services, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately implement a real Ollama adapter, start service smoke, run Ollama, or run `ollama serve`.

## 2. Baseline inherited from ZDoc Step 15

ZDoc Step 15 completed the real-Ollama preview gap analysis in:

```text
docs/zdoc-real-ollama-preview-gap-analysis.md
```

The inherited baseline is:

- ZDoc has completed the fake-only preview stage closure.
- The isolated safe endpoint exists at `POST /local-llm/preview-safe`.
- The fake-only service smoke has passed.
- ZDoc still has not connected real Ollama.
- ZDoc still has not run a real model.
- ZDoc still has not connected the formal generation chain.
- ZDoc still has not connected the export chain.
- ZDoc still has not connected ZBid formal writeback.
- Any real Ollama preview work must remain default-off, preview-only, no-write, no-generation-chain, no-export-chain, and no-ZBid-writeback.

## 3. Existing fake-only preview baseline

The current fake-only baseline includes:

- fake-only helper logic in `backend/zhifei_autoplan/ollama_preview.py`;
- fake-only API / task bridge behavior;
- endpoint / UI entry fake helper behavior;
- safe fake-only service entry helper behavior;
- isolated safe endpoint implementation in `backend/app/routers/local_llm_preview_safe.py`;
- isolated safe endpoint registration in `backend/app/main.py`;
- fake-only deterministic tests in `backend/tests/test_ollama_preview.py`;
- isolated safe endpoint deterministic tests in `backend/tests/test_local_llm_preview_safe_endpoint.py`;
- loopback service smoke evidence for `POST /local-llm/preview-safe`.

The current endpoint response contract includes:

- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- `calls_ollama=false`;
- `calls_external_model_api=false`.

This fake-only baseline is the safety floor for any later real Ollama preview work.

## 4. Real Ollama preview objective

A future real-Ollama preview adapter may only provide advisory preview output from a local Ollama runtime.

The objective is to allow a manually triggered preview path to:

- read a minimal section preview payload;
- optionally query the local Ollama runtime only when explicitly enabled;
- normalize model output into advisory / suggestions;
- return preview-only / no-write metadata;
- fail closed when the model is unavailable, times out, returns invalid data, or is not selected;
- preserve isolation from generation, export, and ZBid writeback paths.

The real-Ollama preview path must not become a正文 rewrite path, a generation step, an export step, a ZBid apply step, or a production scoring path.

## 5. Non-goals

This design does not authorize:

- real Ollama implementation;
- real Ollama runtime smoke;
- `ollama serve`;
- model download;
- model pull;
- `ollama pull`;
- external model/API calls;
- OpenAI / Spark / Gemini / other remote model calls;
- formal generation-chain integration;
- formal export-chain integration;
- ZBid formal writeback;
- production UI integration;
- automatic trigger from existing generation or export flows.

## 6. Feature flag strategy

The existing feature flag remains the preview top-level gate:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

A future real-Ollama adapter must also define an independent adapter / transport gate so that enabling fake-only preview does not automatically enter real model execution.

Candidate real adapter flag:

```text
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

Equivalent naming is acceptable only if the later implementation request names it explicitly and keeps it subordinate to `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.

Required flag behavior:

- If `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is absent or false-like, return disabled immediately.
- If the real adapter flag is absent or false-like, do not access Ollama.
- Real transport is default-off.
- The default enabled preview path must remain fake-only or disabled, not automatic real model execution.
- Both the preview top-level gate and the real adapter gate must be enabled before a real Ollama transport may be called.
- No endpoint-specific flag may bypass these default-off requirements.

False-like values must include:

- absent;
- empty;
- `false`;
- `0`;
- `no`;
- `off`.

True-like values may include:

- `true`;
- `1`;
- `yes`;
- `on`.

## 7. Transport boundary

A future real-Ollama preview transport must be local-only.

Allowed network target:

```text
127.0.0.1:11434
```

Forbidden transport behavior:

- no access to external model providers;
- no access to OpenAI;
- no access to Spark;
- no access to Gemini;
- no access to other remote model APIs;
- no access to arbitrary hostnames;
- no access to `0.0.0.0`;
- no download of models;
- no pull of models;
- no `ollama pull`;
- no write to `output/job/export`;
- no call to `/generate`;
- no call to `/export_docx`;
- no call to `/review/apply`.

Required failure behavior:

- timeout returns stable failure;
- network failure returns stable failure;
- Ollama unavailable returns stable failure;
- model missing returns stable failure;
- invalid JSON returns stable failure;
- invalid response shape returns stable failure;
- empty model content returns stable failure;
- any failure keeps `preview_only=true`;
- any failure keeps `no_write=true`;
- any failure keeps `affects_generation=false`;
- any failure keeps `affects_export=false`;
- any failure must not trigger formal generation, export, or ZBid writeback.

## 8. Model selection boundary

A future model selection design must be explicit.

The design must answer:

- what default model name is used;
- whether `ZDOC_OLLAMA_PREVIEW_MODEL` is reused;
- whether a new preview-specific model variable is introduced;
- whether the adapter can read environment variables;
- whether `/api/tags` may be called in read-only mode against `127.0.0.1:11434`;
- how a missing model is reported;
- how an empty local model list is reported;
- whether model aliases are allowed;
- whether model selection is logged only in response metadata and not persisted.

Required model selection behavior:

- model lookup must be read-only;
- model lookup must not download models;
- model lookup must not pull models;
- model lookup must not modify files;
- model absence must return a stable `model_unavailable` or equivalent failure schema;
- model selection failure must not fall back to external model providers.

## 9. Timeout and num_predict boundary

A future adapter must define bounded runtime parameters.

Timeout design must include:

- default timeout value;
- maximum timeout value;
- minimum timeout value;
- timeout source, such as explicit argument or environment variable;
- failure schema for timeout.

The existing helper concepts include timeout cleaning and default timeout behavior, but a future real-Ollama adapter must define its own exact bounds before implementation.

Recommended timeout boundary:

- default timeout no more than `60` seconds;
- maximum timeout no more than `300` seconds;
- shorter timeout preferred for preview smoke.

`num_predict` design must include:

- default value;
- maximum value;
- whether it can be configured by environment variable;
- how out-of-range values are clamped or rejected.

Recommended `num_predict` boundary:

- default small enough for preview, for example `256`;
- maximum capped, for example `1024`;
- no unbounded generation;
- no long-form formal document generation.

Output boundary:

- do not save complete long model output;
- normalize into advisory / suggestions only;
- do not return正文 replacement fields;
- do not write formal正文;
- do not write output artifacts.

## 10. Failure schema boundary

A future real-Ollama adapter must return stable failure responses.

Failure response must include:

- `status`;
- `enabled`;
- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- `error_type`;
- `reason`;
- source / adapter identity;
- safety metadata.

Required error categories include:

- `real_adapter_disabled`;
- `ollama_unavailable`;
- `model_unavailable`;
- `ollama_timeout`;
- `invalid_response`;
- `empty_response`;
- `transport_error`;
- `invalid_config`;
- `runtime_smoke_not_authorized`.

Failure response must not include:

- formal document content;
- formal正文 replacement;
- `job_id`;
- `output_path`;
- `export_path`;
- `docx_path`;
- `json_path`;
- `markdown_path`;
- ZBid writeback IDs;
- apply results.

## 11. No-write boundary

The real-Ollama preview adapter must remain no-write.

It must not:

- write `output/`;
- write `job/`;
- write `export/`;
- write `backend/data/autoplan/jobs`;
- write DOCX;
- write formal JSON;
- write formal Markdown;
- modify正文;
- persist model output as a formal artifact;
- persist preview output as an adopted result.

The adapter may only return an in-memory response to the caller.

## 12. No-generation-chain boundary

The real-Ollama preview adapter must not trigger the formal generation chain.

It must not:

- call `/generate`;
- call `/generate_async`;
- call compose generation routes;
- call section generation services;
- create generation jobs;
- enqueue generation tasks;
- mutate generation results;
- set `affects_generation=true`.

All responses must keep:

```text
affects_generation=false
```

## 13. No-export-chain boundary

The real-Ollama preview adapter must not trigger the formal export chain.

It must not:

- call `/export_docx`;
- call `/export`;
- call DOCX export services;
- call JSON formal export services;
- call Markdown formal export services;
- create export artifacts;
- return export paths;
- set `affects_export=true`.

All responses must keep:

```text
affects_export=false
```

## 14. No-ZBid-writeback boundary

The real-Ollama preview adapter must not connect ZBid formal writeback.

It must not:

- call `/review/apply`;
- call ZBid writeback routes;
- call ZBid formal apply functions;
- mutate ZBid records;
- build ZBid writeback payloads;
- return ZBid writeback success;
- alter `backend/zhifei_autoplan/zbid_snapshot_mapper.py`;
- set `affects_zbid_writeback=true`.

ZBid-related context may only be read-only preview context in a separately authorized future stage.

## 15. Fake-only deterministic tests matrix

Future tests must be fake-only and deterministic before any real runtime smoke.

The required test matrix includes:

1. Real adapter flag absent: does not access Ollama.
2. Real adapter flag `false` / `0` / `no` / `off`: does not access Ollama.
3. Preview top-level gate disabled: returns disabled immediately.
4. Adapter enabled but fake client unavailable: returns stable failure.
5. Fake `/api/tags` success: selects a local model.
6. Fake `/api/tags` empty: returns `model_unavailable`.
7. Fake generate success: returns preview-only result.
8. Fake generate timeout: returns timeout failure.
9. Fake generate invalid JSON: returns invalid response failure.
10. Fake generate error field: returns stable failure.
11. Any result returns `preview_only=true`.
12. Any result returns `no_write=true`.
13. Any result returns `affects_generation=false`.
14. Any result returns `affects_export=false`.
15. Any result does not write `output/job/export`.
16. Any result does not trigger the generation chain.
17. Any result does not trigger the export chain.
18. Any result does not connect ZBid writeback.
19. Tests do not call real Ollama.
20. Tests do not start a service.
21. Existing fake-only tests continue to pass.

The tests must patch or fake every transport boundary. They must not depend on a local Ollama daemon, installed model, network availability, or service process.

## 16. Runtime smoke prerequisites

Real runtime smoke is a later, separately authorized stage.

Before runtime smoke, all prerequisites must be satisfied:

- Step 16 design is archived.
- Adapter / transport fake-only implementation is complete.
- Fake-only deterministic tests pass.
- The runtime smoke request explicitly authorizes real Ollama contact.
- 2号窗口 usage is defined.
- 2号窗口 only runs `ollama serve`.
- Codex only accesses `127.0.0.1`.
- No external model/API access is allowed.
- No model download is allowed.
- No model pull is allowed.
- `ollama pull` is forbidden.
- No `output/job/export` writes are allowed.
- Formal generation remains disconnected.
- Formal export remains disconnected.
- ZBid writeback remains disconnected.
- Service smoke only requests `POST /local-llm/preview-safe`.
- Service smoke does not request `/generate`.
- Service smoke does not request `/export_docx`.
- Service smoke does not request `/review/apply`.
- Service process shutdown and port cleanup are specified if service startup is used.

If any prerequisite is missing, runtime smoke must not start.

## 17. Future implementation acceptance criteria

A future implementation request must satisfy all of these acceptance criteria before code changes begin:

- It references this Step 16 design.
- It names the exact allowed files.
- It names the exact forbidden files.
- It defines the adapter flag name.
- It defines how `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` remains the top-level gate.
- It defines the real transport target as `127.0.0.1:11434`.
- It forbids external model/API targets.
- It defines model selection.
- It defines timeout bounds.
- It defines `num_predict` bounds.
- It defines stable failure schema.
- It requires fake-only deterministic tests.
- It states that implementation does not run Ollama.
- It states that implementation does not start services.
- It states that implementation does not write `output/job/export`.
- It states that implementation does not connect formal generation, formal export, or ZBid writeback.
- It states that runtime smoke is a later separate stage.
- It requires ChatGPT review before proceeding.

## 18. Recommended next ZDoc step

Recommended next step:

```text
ZDoc Step 17：real-Ollama preview adapter / transport fake-only 实现 + deterministic tests
```

Step 17 must remain fake-only implementation and deterministic tests. It must not directly enter real Ollama runtime smoke, must not run Ollama, must not run `ollama serve`, must not start services, must not connect formal generation, must not connect formal export, and must not connect ZBid writeback.

## 19. Closure statement

ZDoc Step 16 defines the real-Ollama preview adapter / transport guard and fake-only tests boundary only.

The future real-Ollama preview path must remain default-off, preview-only, no-write, local-only, bounded by fake-only tests first, and separated from formal generation, formal export, and ZBid writeback. This document authorizes no code implementation, no test creation, no runtime smoke, no Ollama execution, and no service startup.
