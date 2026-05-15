# ZDoc Local LLM Preview Isolated Safe Endpoint Service Smoke Plan

## 1. Purpose

This document records the ZDoc Step 14J service smoke pre-plan for the local-LLM preview isolated safe endpoint.

The current stage only plans a future service smoke. It does not start a service, does not run pytest, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately start a service.

## 2. Baseline inherited from ZDoc Step 14I

ZDoc Step 14I reviewed and archived the Step 14H fake-only isolated safe endpoint implementation.

The inherited baseline is:

- the isolated safe endpoint has been implemented;
- the endpoint path is `POST /local-llm/preview-safe`;
- the endpoint is implemented in `backend/app/routers/local_llm_preview_safe.py`;
- the endpoint is included by `backend/app/main.py`;
- the endpoint tests are in `backend/tests/test_local_llm_preview_safe_endpoint.py`;
- the helper tests remain in `backend/tests/test_ollama_preview.py`;
- the feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`;
- the endpoint remains default-off;
- the endpoint remains fake-only;
- the endpoint remains preview-only;
- the endpoint remains no-write;
- the endpoint does not call `/generate`;
- the endpoint does not call `/export_docx`;
- the endpoint does not call `/review/apply`;
- the endpoint does not trigger the formal generation chain;
- the endpoint does not trigger the formal export chain;
- the endpoint does not connect ZBid formal writeback;
- the endpoint does not call real Ollama;
- the endpoint does not call external model/API transports.

The Step 14H test command was:

```bash
python3 -m pytest backend/tests/test_local_llm_preview_safe_endpoint.py backend/tests/test_ollama_preview.py -q
```

The Step 14H test result was:

```text
96 passed in 4.97s
```

## 3. Isolated safe endpoint summary

The future service smoke target is:

```text
POST /local-llm/preview-safe
```

The endpoint accepts only a minimal preview payload:

- `section_title`
- `section_text`
- `context_summary`
- `request_id`

The endpoint response is expected to expose safe-preview markers:

- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `affects_zbid_writeback=false`
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `triggers_generation_chain=false`
- `triggers_export_chain=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`
- `calls_ollama=false`
- `calls_external_model_api=false`

The endpoint must not return formal artifact fields such as `job_id`, `docx_path`, `markdown_path`, `json_path`, `export_path`, `output_path`, or `download_url`.

## 4. Service smoke objective

The future service smoke objective is to verify the isolated safe endpoint over a local loopback service process without touching generation, export, writeback, or model runtime surfaces.

The smoke should prove:

- the service can be started on `127.0.0.1`;
- the service does not need `0.0.0.0`;
- disabled mode returns disabled;
- disabled mode does not call the safe helper;
- enabled mode returns fake-only preview advisory / suggestions;
- enabled mode returns preview-only and no-write markers;
- only `POST /local-llm/preview-safe` is requested;
- `/generate` is not requested;
- `/export_docx` is not requested;
- `/review/apply` is not requested;
- no `output/job/export` files are written;
- no DOCX / JSON / Markdown formal export is triggered;
- no ZBid formal writeback occurs;
- no real Ollama call occurs;
- no external model/API call occurs;
- the service process is stopped after smoke;
- the service port has no remaining listener after shutdown;
- git status is still clean or only contains an explicitly authorized smoke report.

## 5. Non-goals

The future service smoke is not a real local model integration.

It must not:

- run Ollama;
- run `ollama serve`;
- call real Ollama;
- call external model/API transports;
- download models;
- pull models;
- execute `ollama pull`;
- generate formal documents;
- write `output/`;
- write `job/`;
- write `export/`;
- trigger DOCX formal export;
- trigger JSON formal export;
- trigger Markdown formal export;
- connect ZBid formal writeback;
- modify正文;
- test `/generate`;
- test `/export_docx`;
- test `/review/apply`;
- smoke Streamlit UI;
- smoke Flask UI;
- create a production service exposure.

The future service smoke does not need 2号窗口 unless a later, separately authorized real Ollama stage is entered.

## 6. Service startup boundary

A future service smoke must explicitly name the startup command before execution.

The service must listen only on:

```text
127.0.0.1
```

The service must not listen on:

```text
0.0.0.0
```

The future smoke step must record:

- service startup command;
- working directory;
- environment variables;
- selected host;
- selected port;
- service PID;
- proof that the listener is bound to `127.0.0.1`;
- service shutdown command or signal;
- proof that the port has no listener after shutdown.

If the application cannot be started on `127.0.0.1` only, service smoke must stop and report the blocker.

## 7. Allowed smoke endpoint

The only allowed service smoke request path is:

```text
POST /local-llm/preview-safe
```

All smoke requests must be made against a local loopback URL, for example:

```text
http://127.0.0.1:<port>/local-llm/preview-safe
```

The request payload must stay minimal and fake-only, for example:

```json
{
  "request_id": "service-smoke-disabled",
  "section_title": "质量保证措施",
  "section_text": "质量控制措施：责任到人，按节点验收。",
  "context_summary": "fake-only service smoke"
}
```

No smoke request may include:

- formal job IDs;
- `output/` paths;
- `job/` paths;
- `export/` paths;
- ZBid writeback parameters;
- real tender file paths;
- real bid file paths;
- model download instructions;
- model pull instructions.

## 8. Forbidden endpoints and chains

The future service smoke must not request:

- `/generate`;
- `/generate_async`;
- `/export_docx`;
- `/review/apply`;
- `/compose`;
- `/export`;
- job creation endpoints;
- job download endpoints;
- DOCX export endpoints;
- audit export endpoints;
- Streamlit UI routes;
- Flask UI routes.

The future service smoke must not trigger:

- formal generation chain;
- formal export chain;
- output artifact writers;
- job writers;
- DOCX generation;
- formal Markdown generation;
- formal JSON generation;
- ZBid formal writeback;
- real Ollama transport;
- external model/API transport.

If the smoke script, curl command, browser request, or logs show any forbidden path, the smoke must stop immediately.

## 9. Disabled scenario plan

The future disabled scenario must be designed as follows:

1. Ensure `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is not set, or explicitly unset it for the service process.
2. Start the service only on `127.0.0.1`.
3. Record the service PID.
4. Confirm the service is not listening on `0.0.0.0`.
5. Send exactly one request to `POST /local-llm/preview-safe`.
6. Confirm the response is disabled.
7. Confirm `enabled=false`.
8. Confirm `preview_only=true`.
9. Confirm `no_write=true`.
10. Confirm `affects_generation=false`.
11. Confirm `affects_export=false`.
12. Confirm `affects_zbid_writeback=false`.
13. Confirm disabled mode did not call the safe helper.
14. Confirm disabled mode did not write `output/job/export`.
15. Confirm disabled mode did not modify正文.
16. Confirm disabled mode did not trigger the generation chain.
17. Confirm disabled mode did not trigger the export chain.
18. Confirm disabled mode did not connect ZBid formal writeback.
19. Confirm disabled mode did not call real Ollama.
20. Confirm disabled mode did not call external model/API transports.

The disabled scenario must not request `/generate`, `/export_docx`, or `/review/apply`.

## 10. Enabled fake-only scenario plan

The future enabled scenario must be designed as follows:

1. Set `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true` for the service process.
2. Start the service only on `127.0.0.1`.
3. Record the service PID.
4. Confirm the service is not listening on `0.0.0.0`.
5. Send exactly one request to `POST /local-llm/preview-safe`.
6. Confirm the response is a fake-only preview.
7. Confirm the response includes advisory / suggestions.
8. Confirm `enabled=true`.
9. Confirm `preview_only=true`.
10. Confirm `no_write=true`.
11. Confirm `affects_generation=false`.
12. Confirm `affects_export=false`.
13. Confirm `affects_zbid_writeback=false`.
14. Confirm `calls_generate_route=false`.
15. Confirm `calls_export_docx_route=false`.
16. Confirm `calls_review_apply_route=false`.
17. Confirm `triggers_generation_chain=false`.
18. Confirm `triggers_export_chain=false`.
19. Confirm `writes_output=false`.
20. Confirm `writes_job=false`.
21. Confirm `writes_export=false`.
22. Confirm `calls_ollama=false`.
23. Confirm `calls_external_model_api=false`.

The enabled scenario must not request `/generate`, `/export_docx`, or `/review/apply`.

The enabled scenario must not write `output/job/export`, must not connect ZBid formal writeback, and must not call real Ollama.

## 11. No-write verification

Future service smoke must include pre/post filesystem checks for:

- `output/`
- `job/`
- `export/`
- `backend/data/autoplan/jobs`
- `build/`

The smoke report must record whether counts changed.

If any new file appears in `output/`, `job/`, or `export/`, smoke must stop and report failure.

If any DOCX / JSON / Markdown formal artifact appears as a result of the smoke request, smoke must stop and report failure.

If `build/` or `backend/data/autoplan/jobs` changes unexpectedly, smoke must stop and report the path and count delta.

## 12. Process shutdown and port cleanup

Future service smoke must stop the service process after disabled and enabled scenarios complete.

The smoke report must record:

- service PID;
- shutdown method;
- whether the process exited;
- whether the port remains open;
- whether any child process remains;
- whether the service was listening only on `127.0.0.1`.

After shutdown, the selected port must have no listener.

If the service cannot be stopped cleanly, the smoke must report that state and must not continue to any next stage.

## 13. Git status and artifact verification

Future service smoke must run `git status --short` before and after smoke.

Expected result after smoke:

- clean worktree; or
- only an explicitly authorized smoke report file.

The future smoke step must not modify code, tests, router files, UI files, generation-chain files, export-chain files, or ZBid writeback files.

The future smoke step must not execute `git clean` and must not clear untracked files.

If unexpected files appear, the smoke must stop and report:

- file path;
- whether the file is tracked or untracked;
- why it is unexpected;
- whether it appears under `output/`, `job/`, `export/`, `build/`, or a code/test path.

## 14. Future smoke report format

Future service smoke report must include at least:

1. Current directory
2. Current branch
3. Start HEAD
4. Service startup command
5. Service listen address
6. Service PID
7. Disabled scenario request and response summary
8. Enabled scenario request and response summary
9. Whether `/local-llm/preview-safe` was requested
10. Whether `/generate` was requested
11. Whether `/export_docx` was requested
12. Whether `/review/apply` was requested
13. Whether `output/job/export` was written
14. Whether formal export was triggered
15. Whether ZBid writeback was connected
16. Whether Ollama was run
17. Whether external model/API was called
18. Service shutdown method
19. Whether service is stopped
20. Whether port has no listener
21. Git status after
22. Risk notes

The report must explicitly state that real Ollama was not run, `ollama serve` was not run, and no model was downloaded or pulled.

## 15. Stop conditions

Future service smoke must stop immediately and report if any of the following occurs:

- service cannot listen only on `127.0.0.1`;
- service requires listening on `0.0.0.0`;
- smoke request hits `/generate`;
- smoke request hits `/export_docx`;
- smoke request hits `/review/apply`;
- smoke request hits a generation, export, job, or writeback route;
- new files appear in `output/`;
- new files appear in `job/`;
- new files appear in `export/`;
- DOCX / JSON / Markdown formal export artifacts appear;
- ZBid writeback evidence appears;
- code or tests are unexpectedly modified;
- service smoke requires Ollama;
- service smoke requires `ollama serve`;
- service smoke requires a model download;
- service smoke requires a model pull;
- service smoke requires external model/API access;
- service cannot be stopped;
- port remains listening after shutdown.

If any stop condition is hit, the smoke must not proceed to real Ollama, formal generation, formal export, or ZBid writeback.

## 16. Recommended next ZDoc step

The recommended next step is:

```text
ZDoc Step 14K：ZDoc local-LLM preview isolated safe endpoint fake-only service smoke + smoke report
```

The next step must not enter real Ollama.

The next step must not enter the formal generation chain, formal export chain, or ZBid formal writeback.

The next step must request only `POST /local-llm/preview-safe` and must bind only to `127.0.0.1`.

## 17. Closure statement

ZDoc Step 14J only records the service smoke pre-plan.

It confirms that future service smoke must target only `POST /local-llm/preview-safe`, must verify disabled and enabled fake-only scenarios, must bind only to `127.0.0.1`, must stop the service and confirm port cleanup, and must not touch `/generate`, `/export_docx`, `/review/apply`, the formal generation chain, the formal export chain, real Ollama, external model/API transports, `output/job/export`, or ZBid formal writeback.

This document does not authorize immediate service startup, service smoke, real Ollama calls, external model/API calls, formal generation, formal export, output/job/export writes, or ZBid formal writeback.
