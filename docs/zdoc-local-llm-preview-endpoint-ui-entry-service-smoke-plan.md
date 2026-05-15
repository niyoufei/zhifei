# ZDoc Local LLM Preview Endpoint UI Entry Service Smoke Plan

## 1. Purpose

This document records the ZDoc Step 13 service-smoke pre-design for the local-LLM preview endpoint / UI entry path.

The current stage only designs a future service smoke. It does not start a service, does not run pytest, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal document artifacts, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately start a service.

## 2. Baseline inherited from ZDoc Step 12

ZDoc Step 12 reviewed the fake-only endpoint / UI entry helper stage in:

```text
docs/zdoc-local-llm-preview-endpoint-ui-entry-fake-stage-review.md
```

The inherited baseline is:

- The fake-only helper already exists.
- The fake-only API / task bridge helper already exists.
- The endpoint / UI entry fake helper already exists.
- The current feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- The current endpoint / UI entry fake helper is default-off.
- The current endpoint / UI entry fake helper is fake-only.
- The current endpoint / UI entry fake helper is preview-only.
- The current endpoint / UI entry fake helper is no-write.
- The current endpoint / UI entry fake helper is deterministic.
- The current endpoint / UI entry fake helper remains pure-function level.
- No real endpoint is registered.
- No real UI page has been modified.
- No service startup has been validated.
- No real Ollama call is connected.
- No external model/API call is connected.
- No formal generation chain is connected.
- No formal export chain is connected.
- No ZBid formal writeback is connected.

## 3. Existing fake-only preview capability

The existing fake-only preview capability includes:

- `backend/zhifei_autoplan/ollama_preview.py`
- `run_zdoc_local_llm_preview`
- `run_zdoc_local_llm_preview_task`
- `run_zdoc_local_llm_preview_endpoint_ui_entry`
- `build_zdoc_local_llm_preview_ui_view`
- deterministic fake advisory / suggestions
- stable disabled behavior
- stable failure behavior for missing, empty, illegal, and automatic-trigger inputs

The existing test file is:

```text
backend/tests/test_ollama_preview.py
```

The Step 11 deterministic test command was:

```bash
python3 -m pytest backend/tests/test_ollama_preview.py -q
```

The Step 11 deterministic test result was:

```text
58 passed in 0.63s
```

Those tests were fake-only. They did not start a service, did not run Ollama, did not run `ollama serve`, did not call external model/API transports, did not download or pull models, and did not create formal artifacts.

## 4. Service smoke objective

A future service smoke may verify only that a service-level loopback path can expose the fake-only preview endpoint / UI entry behavior without widening side effects.

The future service smoke objective is limited to:

- starting a local service only if separately authorized;
- binding only to `127.0.0.1`;
- sending bounded loopback requests only;
- checking a disabled feature flag scenario;
- checking an enabled fake-only feature flag scenario;
- confirming preview-only response fields;
- confirming no-write response fields;
- confirming no generation/export/ZBid-writeback effect flags;
- confirming no writes to `output/`, `job/`, or `export/`;
- stopping the service process cleanly;
- returning a smoke report.

The future service smoke must not validate real Ollama, real model availability, production generation behavior, export behavior, or ZBid writeback behavior.

## 5. Non-goals

The following are explicit non-goals for this design stage and for any future smoke unless separately authorized:

- No service startup in this Step 13 document stage.
- No pytest run in this Step 13 document stage.
- No real Ollama call.
- No `ollama serve`.
- No external model/API call.
- No model download.
- No model pull.
- No `ollama pull`.
- No document generation.
- No write to `output/`.
- No write to `job/`.
- No write to `export/`.
- No DOCX generation.
- No formal Markdown generation.
- No formal JSON generation.
- No正文 modification.
- No formal generation-chain trigger.
- No formal export-chain trigger.
- No ZBid formal writeback.
- No service binding to `0.0.0.0`.
- No external-network access.

## 6. Service startup boundary

A future service smoke may start a local service only if a later step explicitly authorizes service startup.

The startup boundary must be:

- Service startup command must be named exactly.
- Service host must be `127.0.0.1`.
- Service must not listen on `0.0.0.0`.
- Service must not expose the smoke endpoint to the LAN.
- Service must not call real Ollama.
- Service must not call external model/API transports.
- Service must not run `ollama serve`.
- Service must not run `ollama pull`.
- Service must not download or pull models.
- Service must use only synthetic bounded smoke payloads.
- Service PID must be recorded.
- Service shutdown method must be recorded.
- Service stopped state must be verified.

2号窗口 is not required for this fake-only service smoke. 2号窗口 becomes relevant only if a later, separately authorized real Ollama stage is opened.

## 7. Feature flag scenarios

Future service smoke must cover at least two feature flag scenarios.

### Scenario A: feature flag disabled

Configuration:

- Do not set `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`; or
- set `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=false`; or
- set `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=0`; or
- set `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=no`; or
- set `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=off`.

Required result:

- Must return disabled.
- Must return `enabled=false`.
- Must preserve `preview_only=true`.
- Must preserve `no_write=true`.
- Must preserve `affects_generation=false`.
- Must preserve `affects_export=false`.
- Must not call the fake bridge.
- Must not write `output/`, `job/`, or `export/`.
- Must not modify正文.
- Must not generate documents.
- Must not trigger the export chain.
- Must not connect ZBid formal writeback.
- Must not call real Ollama.
- Must not call external model/API transports.

### Scenario B: feature flag enabled

Configuration:

- Set `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`.

Required result:

- Must call only the fake-only preview bridge.
- Must return preview advisory / suggestions.
- Must return `preview_only=true`.
- Must return `no_write=true`.
- Must return `affects_generation=false`.
- Must return `affects_export=false`.
- Must return `affects_zbid_writeback=false`.
- Must not modify正文.
- Must not write `output/`, `job/`, or `export/`.
- Must not trigger the generation chain.
- Must not trigger the export chain.
- Must not connect ZBid formal writeback.
- Must not call real Ollama.
- Must not call external model/API transports.
- Must not download or pull models.
- Must not execute `ollama pull`.

Both scenarios must use synthetic smoke input only. Neither scenario may rely on real model availability.

## 8. Disabled scenario

The disabled scenario must fail closed.

The future smoke should verify:

- disabled response status;
- disabled warning or reason;
- `enabled=false`;
- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- `affects_zbid_writeback=false`;
- no bridge call evidence, if the implementation exposes instrumentation;
- unchanged `output/`, `job/`, and `export/` counts;
- unchanged正文;
- no generated file paths in the response;
- no `job_id` in the response;
- no `export_path` in the response;
- no ZBid writeback fields in the response.

If any disabled scenario response calls a bridge, writes a file, triggers generation, triggers export, or references ZBid writeback, the smoke must stop and report failure.

## 9. Enabled fake-only scenario

The enabled scenario must remain fake-only.

The future smoke should verify:

- `enabled=true`;
- `status=ok` or the expected fake-only stable result;
- preview advisory / suggestions are present;
- `preview_only=true`;
- `no_write=true`;
- `affects_generation=false`;
- `affects_export=false`;
- `affects_zbid_writeback=false`;
- fake-only source or entry metadata is present;
- endpoint/UI entry metadata does not imply real registration unless that stage explicitly implemented it;
- response contains no formal generated-document fields;
- response contains no DOCX / Markdown / JSON formal artifact fields;
- response contains no `job_id`;
- response contains no `export_path`;
- response contains no ZBid writeback result.

If any enabled scenario calls real Ollama, calls an external model/API, writes `output/job/export`, triggers generation, triggers export, or connects ZBid formal writeback, the smoke must stop and report failure.

## 10. No-write verification

A future service smoke must verify write surfaces before and after the smoke.

Minimum no-write checks:

- Count files under `output/` before and after.
- Count files under `job/` before and after.
- Count files under `export/` before and after.
- If the repository uses `backend/data/autoplan/jobs`, count files there before and after.
- If the repository uses `build/` for generated artifacts, count files there before and after.
- Confirm response payloads do not include generated document paths.
- Confirm response payloads do not include `job_id`.
- Confirm response payloads do not include `export_path`.

The service smoke must not create a smoke report inside `output/`, `job/`, or `export/`. If a later step permits a report file, its path must be explicitly authorized and must not be a generated formal artifact path.

## 11. No-generation-chain verification

A future service smoke must verify that the generation chain is not triggered.

Required checks:

- The smoke request must not call formal generation routes.
- The smoke request must not create generation jobs.
- The smoke request must not start generation workers.
- The smoke request must not update generated document bundles.
- The smoke response must include `affects_generation=false`.
- The smoke response must not return `job_id`.
- The smoke response must not return formal generated content fields.

If a future implementation uses negative-call instrumentation, the report should record that formal generation functions were not called.

## 12. No-export-chain verification

A future service smoke must verify that the export chain is not triggered.

Required checks:

- The smoke request must not call export routes.
- The smoke request must not call DOCX export helpers.
- The smoke request must not call formal Markdown export helpers.
- The smoke request must not call formal JSON export helpers.
- The smoke response must include `affects_export=false`.
- The smoke response must not return `export_path`.
- The smoke response must not return DOCX / Markdown / JSON artifact fields.

If a future implementation uses negative-call instrumentation, the report should record that export helpers were not called.

## 13. No-ZBid-writeback verification

A future service smoke must verify that ZBid formal writeback is not connected.

Required checks:

- The smoke request must not include ZBid apply fields.
- The smoke request must not call ZBid writeback routes.
- The smoke request must not mutate ZBid snapshot mapper behavior.
- The smoke response must include `affects_zbid_writeback=false` or an equivalent explicit no-writeback signal.
- The smoke response must not return ZBid writeback result fields.
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py` must remain unchanged.

If a future implementation uses negative-call instrumentation, the report should record that ZBid writeback functions were not called.

## 14. Process shutdown and cleanup boundary

A future service smoke must leave no running service process.

Required process rules:

- Record service process PID.
- Stop the service with the planned shutdown method.
- Verify the PID has exited.
- Verify the service port is no longer listening.
- Do not use `git clean`.
- Do not remove unrelated untracked files.
- Do not clean smoke evidence by deleting repository files unless a later step explicitly authorizes a specific cleanup path.
- Preserve failure evidence in the report.

If the service cannot be stopped cleanly, the smoke must report the PID, command, port, and stop failure without continuing into additional scenarios.

## 15. Failure stop conditions

A future service smoke must stop immediately if any of the following occur:

- Service binds to `0.0.0.0`.
- Service attempts external-network access.
- Service attempts real Ollama.
- Service attempts `ollama serve`.
- Service attempts `ollama pull`.
- Service attempts model download or pull.
- Service writes `output/`.
- Service writes `job/`.
- Service writes `export/`.
- Service triggers formal generation.
- Service triggers formal export.
- Service generates DOCX.
- Service generates formal Markdown.
- Service generates formal JSON.
- Service connects ZBid formal writeback.
- Service modifies正文.
- Service process cannot be stopped.
- `git status --short` shows unexpected changes.

Any stop condition must be reported as a failed smoke and must not be hidden by cleanup commands.

## 16. Future service smoke report format

A future service smoke report must include at least:

1. Current directory.
2. Current branch.
3. Starting HEAD.
4. Service startup command.
5. Service listen address.
6. Feature flag state.
7. Disabled scenario request and response summary.
8. Enabled fake-only scenario request and response summary.
9. Service process PID.
10. Service stop method.
11. Whether the service has stopped.
12. Whether pytest was run.
13. Whether Ollama was run.
14. Whether external model/API transports were called.
15. Whether documents were generated.
16. Whether `output/job/export` was written.
17. Whether DOCX / JSON / Markdown formal export was triggered.
18. Whether ZBid formal writeback was connected.
19. `git status --short` after smoke.
20. Risk statement.

The report should also include before/after write-surface counts for `output/`, `job/`, `export/`, and any explicitly named job/build surface if the later smoke plan authorizes those checks.

## 17. Recommended next ZDoc step

The recommended next step is:

ZDoc Step 14：ZDoc local-LLM preview endpoint / UI entry fake-only service smoke 验证 + smoke report

Step 14 must not directly enter real Ollama, the formal generation chain, the export chain, or ZBid writeback.

## 18. Closure statement

ZDoc Step 13 is a docs-only service-smoke plan for the local-LLM preview endpoint / UI entry fake-only path.

It confirms that any future service smoke must remain default-off, preview-only, no-write, fake-only, loopback-only, and isolated from real Ollama, external model/API transports, model download/pull, formal generation, formal export, and ZBid formal writeback.

This document does not authorize immediate service startup, endpoint implementation, UI implementation, runtime smoke, real model transport, formal generation, formal export, or ZBid writeback.
