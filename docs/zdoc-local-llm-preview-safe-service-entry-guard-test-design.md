# ZDoc Local LLM Preview Safe Service Entry Guard and Test Design

## 1. Purpose

This document records the ZDoc Step 14B pre-design for safe fake-only service entry guards and deterministic tests.

The current stage only designs the safe service entry guard and deterministic tests. It does not implement code, does not add or modify tests, does not run pytest, does not start a service, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately implement code or start a service.

## 2. Baseline inherited from ZDoc Step 14A

ZDoc Step 14A completed the safe fake-only service entry pre-design in:

```text
docs/zdoc-local-llm-preview-safe-service-entry-design.md
```

The inherited Step 14A baseline is:

- ZDoc has real FastAPI entry points.
- ZDoc has real Streamlit / UI entry points.
- ZDoc has a Flask page entry.
- ZDoc has generation, export, job, output, review-apply, and ZBid-adjacent routes or modules.
- The current fake-only helper exists in `backend/zhifei_autoplan/ollama_preview.py`.
- The current fake-only API / task bridge helper exists.
- The current endpoint / UI entry fake helper exists.
- The current feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- The current helper-level behavior remains default-off.
- The current helper-level behavior remains preview-only.
- The current helper-level behavior remains no-write.
- The current helper-level behavior is not registered as a real safe endpoint.
- Immediate service smoke is not recommended.

The current stable baseline tag is:

```text
v0.1.61-zdoc-local-llm-preview-safe-service-entry-design
```

## 3. Guard objective

The guard objective is to define the boundary that a future safe fake-only service entry implementation must satisfy before service smoke can be reconsidered.

Future guards must prove that the safe service entry:

- is isolated from `/generate`;
- is isolated from `/export_docx`;
- is isolated from `/review/apply`;
- is default-off;
- is preview-only;
- is no-write;
- calls only the fake-only bridge;
- does not call real Ollama;
- does not call external model/API transports;
- does not download or pull models;
- does not execute `ollama pull`;
- does not write `output/`;
- does not write `job/`;
- does not write `export/`;
- does not modify正文章节;
- does not trigger formal generation;
- does not trigger formal export;
- does not connect ZBid formal writeback;
- does not listen on `0.0.0.0`;
- can be smoked later only through `127.0.0.1` after separate authorization.

The guard must fail closed. Any uncertain route, write path, export path, generation path, model call, or writeback path must be treated as unsafe.

## 4. Allowed future file scope

This Step 14B does not authorize code implementation. It only defines the future file-scope questions that must be answered before a later implementation step.

Future implementation may be considered only after the implementation request explicitly names the allowed files. Candidate future scopes may include:

- a dedicated safe preview endpoint router;
- a small service-entry adapter around `run_zdoc_local_llm_preview_task`;
- deterministic tests for the safe service entry;
- narrow imports needed to mount the dedicated safe endpoint.

The future implementation request must explicitly state:

- whether a new endpoint file may be added;
- whether an existing router may be modified;
- whether `backend/app/main.py` may include a new router;
- whether `backend/zhifei_autoplan/ollama_preview.py` may be modified;
- whether `backend/tests/test_ollama_preview.py` must remain unchanged;
- whether a new endpoint test file may be added;
- whether any UI file may be modified.

No future implementation may infer permission from this document.

## 5. Forbidden future file scope

Until separately authorized, future work must not modify:

- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`;
- formal generation-chain files;
- formal export-chain files;
- ZBid formal writeback files;
- UI files;
- `tasks/`;
- `output/`;
- `job/`;
- `export/`;
- `build/`;
- requirements files;
- lock files;
- dependency configuration.

Future work must not execute `git clean` and must not clear untracked files.

If a future implementation needs to touch a currently forbidden file, the implementation request must identify that file by path and explain why no narrower route is sufficient.

## 6. Safe endpoint isolation boundary

The future safe endpoint must be a dedicated preview / diagnostics entry. It must not be a wrapper around existing generation, export, job, output, or review-apply endpoints.

The isolation boundary is:

- The safe endpoint must not call `/generate`.
- The safe endpoint must not call `/export_docx`.
- The safe endpoint must not call `/review/apply`.
- The safe endpoint must not call `/compose`.
- The safe endpoint must not call `/export`.
- The safe endpoint must not call formal generation helpers.
- The safe endpoint must not call formal export helpers.
- The safe endpoint must not call `save_output_artifacts`.
- The safe endpoint must not create or update jobs.
- The safe endpoint must not call review apply or remediation logic.
- The safe endpoint must not call ZBid formal writeback.
- The safe endpoint must not call real Ollama.
- The safe endpoint must not call external model/API transports.

The safe endpoint may call only `run_zdoc_local_llm_preview_task` or an equivalent fake-only bridge that returns preview advisory / suggestions with no-write markers.

## 7. Feature flag contract

The feature flag remains:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

Disabled values:

- absent;
- empty;
- `false`;
- `0`;
- `no`;
- `off`.

Enabled values:

- `true`;
- `1`;
- `yes`;
- `on`.

Disabled behavior has highest priority. No endpoint-specific flag may bypass `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`. Any future endpoint-specific or service-entry-specific flag must be stricter than, and subordinate to, this flag.

The safe service entry must not trigger automatically. It must require a bounded manual or diagnostic request.

## 8. Disabled behavior contract

When the feature flag is disabled, the future safe service entry must:

- return a stable disabled response;
- return `enabled=false`;
- preserve `preview_only=true`;
- preserve `no_write=true`;
- preserve `affects_generation=false`;
- preserve `affects_export=false`;
- preserve `affects_zbid_writeback=false`;
- not call the fake bridge;
- not call `/generate`;
- not call `/export_docx`;
- not call `/review/apply`;
- not write `output/job/export`;
- not modify正文;
- not start a formal generation task;
- not trigger formal export;
- not trigger ZBid writeback;
- not call real Ollama;
- not call external model/API transports;
- not download or pull models.

Disabled behavior must be deterministic for all disabled flag forms.

## 9. Enabled fake-only behavior contract

When the feature flag is enabled, the future safe service entry must:

- call only the fake-only bridge;
- return only preview advisory / suggestions;
- return `preview_only=true`;
- return `no_write=true`;
- return `affects_generation=false`;
- return `affects_export=false`;
- return `affects_zbid_writeback=false`;
- avoid fields that look like formal output paths;
- avoid `job_id`;
- avoid `docx_path`;
- avoid `markdown_path`;
- avoid `json_path`;
- avoid `export_path`;
- not modify正文章节;
- not call `/generate`;
- not call `/export_docx`;
- not call `/review/apply`;
- not write `output/job/export`;
- not trigger formal generation;
- not trigger formal export;
- not connect ZBid formal writeback;
- not call real Ollama;
- not call external model/API transports;
- not download or pull models.

Enabled behavior must be deterministic for the same input.

## 10. No-write boundary

The safe service entry must be no-write in both disabled and enabled states.

The no-write boundary includes:

- no `output/` write;
- no `job/` write;
- no `export/` write;
- no `build/` write;
- no generated DOCX;
- no formal Markdown;
- no formal JSON;
- no正文 mutation;
- no generated section mutation;
- no persisted preview payload;
- no persisted diagnostic payload unless a later smoke-report step explicitly authorizes a report file.

Future tests should verify no-write behavior with path counts, monkeypatched writers, forbidden-call counters, or equivalent deterministic checks.

## 11. No-generation-chain boundary

The safe service entry must be isolated from formal generation.

Future guards must check:

- the safe endpoint does not call `/generate`;
- the safe endpoint does not call `/generate_async`;
- the safe endpoint does not call `/generate_async_batch`;
- the safe endpoint does not call `/compose`;
- the safe endpoint does not create generation jobs;
- the safe endpoint does not call autoplan orchestration;
- the safe endpoint does not mutate generated sections;
- the safe endpoint does not return formal generation results.

If a future code path cannot prove these checks, it must be rejected before service smoke.

## 12. No-export-chain boundary

The safe service entry must be isolated from formal export.

Future guards must check:

- the safe endpoint does not call `/export_docx`;
- the safe endpoint does not call `/export`;
- the safe endpoint does not call export service helpers;
- the safe endpoint does not call output artifact helpers;
- the safe endpoint does not write DOCX;
- the safe endpoint does not write formal Markdown;
- the safe endpoint does not write formal JSON;
- the safe endpoint does not expose export file paths.

The safe endpoint response must be recognizable as preview-only and must not be reusable as a formal export response.

## 13. No-ZBid-writeback boundary

The safe service entry must not connect ZBid formal writeback.

Future guards must check:

- the safe endpoint does not call ZBid writeback code;
- the safe endpoint does not call review apply code;
- the safe endpoint does not write ZBid state;
- the safe endpoint does not return writeback action fields;
- the safe endpoint returns `affects_zbid_writeback=false`;
- the safe endpoint remains separate from the ZBid mock snapshot preview route.

ZBid mock preview paths must not be treated as permission to add ZBid formal writeback.

## 14. Deterministic tests matrix

Future tests must be fake-only and deterministic. This Step 14B document does not add tests.

At minimum, the future test matrix must cover:

1. safe endpoint default disabled.
2. disabled mode does not call the fake bridge.
3. disabled mode does not write `output/job/export`.
4. disabled mode does not modify正文.
5. enabled mode calls the fake-only bridge.
6. enabled mode returns `preview_only=true`.
7. enabled mode returns `no_write=true`.
8. enabled mode returns `affects_generation=false`.
9. enabled mode returns `affects_export=false`.
10. enabled mode does not call `/generate`.
11. enabled mode does not call `/export_docx`.
12. enabled mode does not call `/review/apply`.
13. enabled mode does not write `output/job/export`.
14. enabled mode does not modify正文.
15. enabled mode does not connect ZBid formal writeback.
16. enabled mode does not call real Ollama.
17. enabled mode does not call external model/API transports.
18. enabled mode does not trigger the export chain.
19. enabled mode does not trigger the generation chain.
20. tests do not start a real service.
21. tests do not run Ollama.
22. tests do not run `ollama serve`.
23. tests do not write `output/job/export`.
24. existing `backend/tests/test_ollama_preview.py` must continue to pass.

The test matrix should also include stable failure cases:

- missing payload;
- missing section text;
- empty section text;
- illegal `output`, `job`, `export`, `docx`, `generate`, or `writeback` fields;
- automatic trigger metadata;
- repeated identical input returning identical output.

## 15. Future service smoke prerequisites

Future service smoke remains blocked until all of these prerequisites are met:

- Step 14B design has been archived.
- A later implementation request explicitly authorizes safe endpoint implementation.
- The safe endpoint path is named exactly.
- The allowed implementation files are named exactly.
- The safe endpoint implementation is complete.
- Deterministic tests are complete.
- Existing `backend/tests/test_ollama_preview.py` still passes.
- The safe endpoint is proven isolated from `/generate`.
- The safe endpoint is proven isolated from `/export_docx`.
- The safe endpoint is proven isolated from `/review/apply`.
- The safe endpoint is proven no-write for `output/job/export`.
- The safe endpoint is proven not to trigger generation chains.
- The safe endpoint is proven not to trigger export chains.
- The safe endpoint is proven not to connect ZBid formal writeback.
- The safe endpoint is proven not to call real Ollama.
- The safe endpoint is proven not to call external model/API transports.
- The future smoke request authorizes service startup.
- The future smoke binds only to `127.0.0.1`.
- The future smoke does not listen on `0.0.0.0`.
- The future smoke names the service start command.
- The future smoke records PID and shutdown method.
- The future smoke verifies the service stopped state.

If any prerequisite is missing, service smoke must not start.

## 16. Future implementation acceptance criteria

Future implementation may begin only after a later request satisfies all of the following:

- ZDoc Step 14B design has been archived.
- The request clearly says code implementation is allowed.
- The request clearly says whether a new safe endpoint may be added.
- The request clearly names the safe endpoint path.
- The request clearly names every file that may be modified.
- The request clearly says whether `backend/app/main.py` may be modified.
- The request clearly says whether `backend/app/routers/actions_bridge.py` may be modified.
- The request clearly says whether `backend/app/routers/zhifei_autoplan.py` may be modified.
- The request clearly says whether `backend/zhifei_autoplan/ollama_preview.py` may be modified.
- The request clearly says whether tests may be added or modified.
- The request clearly confirms the feature flag name `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- The request clearly defines disabled behavior.
- The request clearly defines enabled fake-only behavior.
- The request clearly defines deterministic test scope.
- The request clearly requires no write to `output/job/export`.
- The request clearly requires no generation-chain trigger.
- The request clearly requires no export-chain trigger.
- The request clearly requires no ZBid formal writeback.
- The request clearly requires no real Ollama call.
- The request clearly states that code implementation does not start a service.
- The request clearly states that service smoke is a later separate stage.
- The request clearly requires completion to stop and wait for ChatGPT review.

Without those acceptance criteria, implementation must not start.

## 17. Recommended next ZDoc step

The recommended next step is:

```text
ZDoc Step 14C：ZDoc local-LLM preview safe fake-only service entry 实现 + deterministic tests
```

Step 14C must not go directly into service smoke, real Ollama, formal generation chains, formal export chains, or ZBid writeback.

## 18. Closure statement

Step 14B defines the guard and deterministic test boundary for a future isolated safe fake-only local-LLM preview service entry.

The safe service entry must remain default-off, preview-only, no-write, fake-only, isolated from `/generate`, isolated from `/export_docx`, isolated from `/review/apply`, isolated from formal generation, isolated from formal export, isolated from ZBid formal writeback, disconnected from real Ollama, and disconnected from external model/API transports.

This document authorizes no code changes, no test changes, no service startup, no pytest run, no Ollama run, no external model/API call, no model download or pull, no formal document generation, no `output/job/export` write, no DOCX / JSON / Markdown formal export, and no ZBid formal writeback.
