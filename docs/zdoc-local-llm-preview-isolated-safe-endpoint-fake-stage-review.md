# ZDoc Local LLM Preview Isolated Safe Endpoint Fake Stage Review

## 1. Purpose

This document archives the ZDoc Step 14H implementation review for the local-LLM preview isolated safe endpoint fake-only stage.

ZDoc Step 14H completed an isolated safe endpoint implementation for local-LLM preview diagnostics and passed deterministic tests. This review records implementation scope, endpoint path, feature flag behavior, disabled/enabled behavior, test coverage, explicit non-integrations, no-write boundaries, remaining risks, and the gate required before any future service smoke.

This document is docs-only. It does not modify code, does not add or modify tests, does not run pytest, does not start a service, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to directly enter real Ollama, the formal generation chain, the formal export chain, or ZBid formal writeback.

## 2. Baseline before ZDoc Step 14H

ZDoc Step 14H started from the Step 14F and Step 14G design baseline:

- Step 14F plan document: `docs/zdoc-local-llm-preview-isolated-safe-endpoint-implementation-plan.md`
- Step 14G guard design document: `docs/zdoc-local-llm-preview-isolated-safe-endpoint-guard-implementation-design.md`
- Step 14H stable implementation tag: `v0.1.68-zdoc-local-llm-isolated-safe-endpoint-fake`
- Step 14H commit: `6b23d5963d0bf04a93a6bb8e70f92dcd7e3a2cd2`

The inherited baseline required the endpoint to remain:

- default-off;
- fake-only;
- preview-only;
- no-write;
- deterministic;
- isolated from `/generate`;
- isolated from `/export_docx`;
- isolated from `/review/apply`;
- disconnected from real service startup;
- disconnected from real Ollama;
- disconnected from external model/API transports;
- disconnected from the formal generation chain;
- disconnected from the formal export chain;
- disconnected from ZBid formal writeback.

## 3. Files changed in ZDoc Step 14H

Actual Step 14H modified file:

```text
backend/app/main.py
```

The change in `backend/app/main.py` was limited to including the isolated safe router.

Actual Step 14H new router file:

```text
backend/app/routers/local_llm_preview_safe.py
```

Actual Step 14H new test file:

```text
backend/tests/test_local_llm_preview_safe_endpoint.py
```

No other files were modified in Step 14H.

Not modified in Step 14H:

- `backend/zhifei_autoplan/ollama_preview.py`
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- `backend/app/routers/actions_bridge.py`
- `backend/app/routers/zhifei_autoplan.py`
- `backend/tests/test_ollama_preview.py`
- `app.py`
- `frontend_web/app.py`
- `tasks/`
- `output/`
- `job/`
- `export/`
- `build/`
- any formal generation-chain file
- any formal export-chain file
- any ZBid formal writeback file
- any requirements / pyproject / lock file

## 4. Endpoint path and isolation review

ZDoc Step 14H added the isolated endpoint:

```text
POST /local-llm/preview-safe
```

The endpoint is implemented in:

```text
backend/app/routers/local_llm_preview_safe.py
```

The endpoint is registered by the minimal router include in:

```text
backend/app/main.py
```

The endpoint is intentionally named as a local-LLM preview / diagnostics route. It is not named as a generate, export, apply, job, DOCX, JSON, Markdown, or ZBid writeback route.

The request boundary is minimal and preview-only. The accepted payload fields are:

- `section_title`
- `section_text`
- `context_summary`
- `request_id`

The endpoint does not require:

- real tender documents;
- real bid documents;
- formal generation task IDs;
- `output/`, `job/`, or `export/` paths;
- ZBid writeback parameters.

The response is marked as safe preview / diagnostics and avoids formal artifact fields such as `job_id`, `docx_path`, `markdown_path`, `json_path`, `export_path`, `output_path`, and `download_url`.

## 5. Feature flag behavior

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

Disabled behavior remains highest priority. Disabled mode returns stable disabled output and does not call the safe helper / fake bridge.

## 6. Disabled behavior review

When `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is absent, empty, `false`, `0`, `no`, or `off`, `POST /local-llm/preview-safe` returns disabled.

Disabled response behavior:

- returns `ok=false`;
- returns `enabled=false`;
- returns `status=disabled`;
- returns `warning=local_llm_preview_safe_endpoint_disabled`;
- returns `reason=feature_flag_disabled`;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- returns `entry_type=isolated_safe_endpoint`;
- returns `entry_source=zdoc_local_llm_preview_isolated_safe_endpoint_fake`;
- returns `endpoint_path=/local-llm/preview-safe`;
- returns `safe_endpoint_registered=true`;
- returns `service_started=false`;
- returns `fake_only=true`;
- returns `calls_generate_route=false`;
- returns `calls_export_docx_route=false`;
- returns `calls_review_apply_route=false`;
- returns `triggers_generation_chain=false`;
- returns `triggers_export_chain=false`;
- returns `writes_output=false`;
- returns `writes_job=false`;
- returns `writes_export=false`;
- returns `calls_ollama=false`;
- returns `calls_external_model_api=false`;
- does not call the safe helper / fake bridge;
- does not write `output/job/export`;
- does not modify正文.

This proves the default-off boundary for the isolated endpoint.

## 7. Enabled fake-only behavior review

When `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is enabled, `POST /local-llm/preview-safe` calls only the fake-only safe helper:

```text
run_zdoc_local_llm_preview_safe_service_entry
```

Enabled response behavior:

- returns preview advisory / suggestions;
- preserves `preview_only=true`;
- preserves `no_write=true`;
- preserves `affects_generation=false`;
- preserves `affects_export=false`;
- preserves `affects_zbid_writeback=false`;
- preserves `entry_type=isolated_safe_endpoint`;
- preserves `entry_source=zdoc_local_llm_preview_isolated_safe_endpoint_fake`;
- preserves `endpoint_path=/local-llm/preview-safe`;
- preserves `safe_endpoint_registered=true`;
- preserves `service_started=false`;
- preserves `fake_only=true`;
- preserves `calls_generate_route=false`;
- preserves `calls_export_docx_route=false`;
- preserves `calls_review_apply_route=false`;
- preserves `triggers_generation_chain=false`;
- preserves `triggers_export_chain=false`;
- preserves `writes_output=false`;
- preserves `writes_job=false`;
- preserves `writes_export=false`;
- preserves `calls_ollama=false`;
- preserves `calls_external_model_api=false`;
- rejects missing input with stable failure;
- rejects empty text with stable failure;
- rejects illegal fields with stable failure;
- rejects safe helper output containing formal artifact fields.

Enabled behavior remains fake-only. It does not modify正文章节, does not generate DOCX, does not generate formal Markdown, does not generate formal JSON, does not call Ollama, and does not call external model/API transports.

## 8. Forbidden route isolation review

Step 14H did not call or wire the endpoint into:

- `/generate`
- `/generate_async`
- `/export_docx`
- `/review/apply`
- `/compose`
- `/export`
- formal generation-chain helpers
- formal export-chain helpers
- job writers
- output artifact writers
- ZBid formal writeback
- Streamlit UI buttons
- Flask page routes

The endpoint response explicitly reports:

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `triggers_generation_chain=false`
- `triggers_export_chain=false`

The Step 14H tests also patch forbidden route functions and fail if the safe endpoint calls generation, export, or review apply handlers.

## 9. Deterministic test coverage

Step 14H added:

```text
backend/tests/test_local_llm_preview_safe_endpoint.py
```

The existing helper test file continued to pass:

```text
backend/tests/test_ollama_preview.py
```

Test command:

```bash
python3 -m pytest backend/tests/test_local_llm_preview_safe_endpoint.py backend/tests/test_ollama_preview.py -q
```

Test result:

```text
96 passed in 4.97s
```

The Step 14H tests cover:

- safe endpoint exists;
- feature flag absent returns disabled;
- feature flag empty / false / 0 / no / off returns disabled;
- disabled mode does not call the safe helper;
- disabled mode does not write `output/job/export`;
- enabled mode calls fake-only safe helper;
- enabled mode returns `preview_only=true`;
- enabled mode returns `no_write=true`;
- enabled mode returns `affects_generation=false`;
- enabled mode returns `affects_export=false`;
- enabled mode does not call `/generate`;
- enabled mode does not call `/export_docx`;
- enabled mode does not call `/review/apply`;
- enabled mode does not write `output/job/export`;
- enabled mode does not modify正文;
- enabled mode does not connect ZBid formal writeback;
- enabled mode does not call real Ollama;
- enabled mode does not call external model/API transports;
- enabled mode does not trigger generation chain;
- enabled mode does not trigger export chain;
- missing input returns stable failure;
- empty text returns stable failure;
- illegal fields return stable failure;
- same input returns deterministic output;
- tests do not start a real service;
- tests do not run Ollama;
- tests do not write `output/job/export`;
- existing `backend/tests/test_ollama_preview.py` continues to pass.

## 10. Explicit non-integrations

Step 14H did not integrate the isolated endpoint with:

- real service startup;
- service smoke;
- real Ollama;
- external model/API transports;
- formal document generation;
- formal export;
- DOCX generation;
- formal Markdown generation;
- formal JSON generation;
- ZBid formal writeback;
- Streamlit UI;
- Flask UI;
- existing business routes in `actions_bridge.py`;
- existing business routes in `zhifei_autoplan.py`.

Current capability is an isolated fake-only endpoint plus deterministic tests. It is not a verified service-smoke result.

## 11. No-write boundary

The isolated endpoint is no-write.

Step 14H tests verify that the endpoint does not write:

- `output/`
- `job/`
- `export/`
- `backend/data/autoplan/jobs`
- `build/`

The endpoint response explicitly reports:

- `writes_output=false`
- `writes_job=false`
- `writes_export=false`
- `no_write=true`

The endpoint does not accept output, job, export, or formal artifact path fields in its request payload.

## 12. No-generation-chain boundary

The isolated endpoint does not trigger the formal generation chain.

Step 14H did not modify formal generation-chain files. Step 14H did not modify `backend/app/routers/actions_bridge.py` or `backend/app/routers/zhifei_autoplan.py`.

The endpoint response explicitly reports:

- `affects_generation=false`
- `calls_generate_route=false`
- `triggers_generation_chain=false`

The tests patch generation handlers and fail if the safe endpoint calls them.

## 13. No-export-chain boundary

The isolated endpoint does not trigger the formal export chain.

Step 14H did not modify formal export-chain files. Step 14H did not modify DOCX / JSON / Markdown export services.

The endpoint response explicitly reports:

- `affects_export=false`
- `calls_export_docx_route=false`
- `triggers_export_chain=false`

The endpoint response strips or rejects formal artifact fields that could be mistaken for export results.

## 14. No-ZBid-writeback boundary

The isolated endpoint does not connect ZBid formal writeback.

Step 14H did not modify:

```text
backend/zhifei_autoplan/zbid_snapshot_mapper.py
```

The endpoint response explicitly reports:

- `affects_zbid_writeback=false`

The endpoint request payload does not accept ZBid writeback parameters.

## 15. Remaining risks

The current state still has the following risks and limits:

- The isolated safe endpoint has been implemented, but service smoke has not been performed.
- A real service process has not been started.
- Fake-only tests do not prove that the endpoint is reachable after service startup.
- Fake-only tests do not prove service process lifecycle behavior.
- Future service smoke must request only `POST /local-llm/preview-safe`.
- Future service smoke must not request `/generate`.
- Future service smoke must not request `/export_docx`.
- Future service smoke must not request `/review/apply`.
- Future service smoke must not write `output/job/export`.
- Future service smoke must not trigger the formal generation chain.
- Future service smoke must not trigger the formal export chain.
- Future service smoke must not connect ZBid formal writeback.
- Future service smoke must not call real Ollama.
- Future service smoke must not call external model/API transports.
- Future service smoke must listen only on `127.0.0.1`.
- Future service smoke must not listen on `0.0.0.0`.
- If a later phase enters real Ollama, that phase must be separately designed and must use 2号窗口 only after explicit authorization.

## 16. Service smoke prerequisites

Future service smoke may be considered only after a separate docs-only plan authorizes it.

Minimum prerequisites for service smoke:

- Step 14I review is archived.
- The service startup command is explicitly named.
- The service listen address is explicitly limited to `127.0.0.1`.
- The service smoke request path is only `POST /local-llm/preview-safe`.
- The smoke request does not hit `/generate`.
- The smoke request does not hit `/export_docx`.
- The smoke request does not hit `/review/apply`.
- The smoke request verifies disabled behavior.
- The smoke request verifies enabled fake-only behavior.
- The smoke verifies `preview_only=true`.
- The smoke verifies `no_write=true`.
- The smoke verifies `affects_generation=false`.
- The smoke verifies `affects_export=false`.
- The smoke verifies no `output/job/export` writes.
- The smoke verifies no DOCX / JSON / Markdown formal export.
- The smoke verifies no ZBid formal writeback.
- The smoke verifies the service process is stopped after completion.
- The smoke report includes `git status --short` after service shutdown.

If any prerequisite is missing, service smoke must stop before service startup.

## 17. Recommended next ZDoc step

The recommended next step is docs-only:

```text
ZDoc Step 14J：ZDoc local-LLM preview isolated safe endpoint service smoke 前置计划文档
```

The next step must not directly start a service.

The next step must not connect real Ollama.

The next step must not connect the formal generation chain, formal export chain, or ZBid formal writeback.

## 18. Closure statement

ZDoc Step 14I only reviews and archives the Step 14H fake-only isolated safe endpoint implementation.

It confirms that `POST /local-llm/preview-safe` exists and remains default-off, fake-only, preview-only, no-write, isolated from `/generate`, isolated from `/export_docx`, isolated from `/review/apply`, disconnected from real Ollama, disconnected from external model/API transports, disconnected from formal generation, disconnected from formal export, and disconnected from ZBid formal writeback.

This document does not authorize service smoke, service startup, real Ollama calls, external model/API calls, formal generation, formal export, output/job/export writes, or ZBid formal writeback.
