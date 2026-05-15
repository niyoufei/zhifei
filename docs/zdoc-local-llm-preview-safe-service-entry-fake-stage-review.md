# ZDoc Local LLM Preview Safe Service Entry Fake Stage Review

## 1. Purpose

This document archives the ZDoc Step 14C implementation review for the local-LLM preview safe fake-only service entry helper.

ZDoc Step 14C completed a controlled helper-layer implementation and deterministic tests for a safe fake-only service entry path. This review records implementation scope, feature flag behavior, disabled/enabled behavior, route isolation, deterministic test coverage, explicit non-integrations, remaining risks, and the gate required before any real endpoint or service smoke stage.

This document is docs-only. It does not modify code, tests, endpoint routes, UI pages, formal generation chains, formal export chains, `output/`, `job/`, `export/`, real Ollama transport, external model/API transports, or ZBid formal writeback.

## 2. Baseline before ZDoc Step 14C

ZDoc Step 14C started from the Step 14A and Step 14B design baseline:

- Step 14A design document: `docs/zdoc-local-llm-preview-safe-service-entry-design.md`
- Step 14B guard/test design document: `docs/zdoc-local-llm-preview-safe-service-entry-guard-test-design.md`
- Step 14C stable tag after implementation: `v0.1.63-zdoc-local-llm-preview-safe-service-entry-fake`
- Step 14C commit: `bcdccd451daee6a7bc137f3360727a8c1ecafa98`

The inherited baseline required the safe service entry to remain:

- default-off;
- fake-only;
- preview-only;
- no-write;
- deterministic;
- helper-layer only;
- isolated from `/generate`;
- isolated from `/export_docx`;
- isolated from `/review/apply`;
- disconnected from real endpoint registration;
- disconnected from real UI pages;
- disconnected from service startup;
- disconnected from real Ollama;
- disconnected from external model/API transports;
- disconnected from the formal generation chain;
- disconnected from the formal export chain;
- disconnected from ZBid formal writeback.

## 3. Files changed in ZDoc Step 14C

Actual Step 14C implementation file:

```text
backend/zhifei_autoplan/ollama_preview.py
```

Actual Step 14C test file:

```text
backend/tests/test_ollama_preview.py
```

No other files were modified in Step 14C.

Not modified:

- `backend/app/main.py`
- `backend/app/routers/actions_bridge.py`
- `backend/app/routers/zhifei_autoplan.py`
- `app.py`
- `frontend_web/app.py`
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- `tasks/`
- `output/`
- `job/`
- `export/`
- `build/`
- any formal generation-chain file
- any formal export-chain file
- any ZBid formal writeback file
- any requirements / pyproject / lock file

## 4. Feature flag behavior

Step 14C continues to use:

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

Disabled behavior remains highest priority. When disabled, the safe service entry returns stable disabled output and does not call the fake bridge.

## 5. Disabled safe entry behavior review

Disabled safe entry behavior:

- returns `status=disabled`;
- returns `enabled=false`;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- returns `entry_type=safe_service_entry`;
- returns `entry_source=zdoc_local_llm_preview_safe_service_entry_fake`;
- returns `safe_service_entry_ready=true`;
- returns `safe_endpoint_registered=false`;
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
- does not call fake bridge;
- does not write `output/job/export`;
- does not modify正文.

This proves the default-off boundary at helper level.

## 6. Enabled safe fake-only behavior review

Enabled safe entry behavior:

- calls only the fake-only bridge;
- returns preview advisory / suggestions;
- preserves `preview_only=true`;
- preserves `no_write=true`;
- preserves `affects_generation=false`;
- preserves `affects_export=false`;
- preserves `affects_zbid_writeback=false`;
- preserves `entry_type=safe_service_entry`;
- preserves `entry_source=zdoc_local_llm_preview_safe_service_entry_fake`;
- preserves `safe_endpoint_registered=false`;
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
- rejects automatic trigger with stable failure;
- rejects missing input with stable failure;
- rejects empty text with stable failure;
- rejects illegal fields with stable failure;
- rejects bridge output containing formal result fields.

Enabled behavior remains fake-only. It does not modify正文章节, does not generate DOCX, does not generate formal Markdown, does not generate formal JSON, does not call Ollama, and does not call external model/API transports.

## 7. Forbidden route isolation review

Step 14C did not call or wire the safe entry into:

- `/generate`
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
- real FastAPI route registration

The safe entry response explicitly reports:

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `triggers_generation_chain=false`
- `triggers_export_chain=false`

Current route risk still exists elsewhere in the repository, including `backend/app/main.py`, `backend/app/routers/actions_bridge.py`, `backend/app/routers/zhifei_autoplan.py`, `app.py`, and `frontend_web/app.py`. Step 14C did not modify those files.

## 8. Deterministic test coverage

Step 14C modified:

```text
backend/tests/test_ollama_preview.py
```

Test command:

```bash
python3 -m pytest backend/tests/test_ollama_preview.py -q
```

Test result:

```text
78 passed in 1.03s
```

The Step 14C tests cover:

- safe service entry default disabled;
- feature flag absent returns disabled;
- feature flag empty / false / 0 / no / off returns disabled;
- disabled mode does not call fake bridge;
- disabled mode does not write `output/job/export`;
- enabled mode calls fake-only bridge;
- enabled mode returns `preview_only=true`;
- enabled mode returns `no_write=true`;
- enabled mode returns `affects_generation=false`;
- enabled mode returns `affects_export=false`;
- enabled mode reports no `/generate` call;
- enabled mode reports no `/export_docx` call;
- enabled mode reports no `/review/apply` call;
- enabled mode does not write `output/job/export`;
- enabled mode does not modify正文;
- enabled mode does not connect ZBid formal writeback;
- enabled mode does not call Ollama;
- enabled mode does not call external model/API transports;
- enabled mode does not trigger the generation chain;
- enabled mode does not trigger the export chain;
- same input returns deterministic output;
- missing input returns stable failure;
- empty text returns stable failure;
- illegal fields return stable failure;
- formal result fields such as `job_id` and `export_path` are rejected;
- existing local-LLM fake helper tests continue to pass;
- existing API/task bridge fake tests continue to pass;
- existing endpoint/UI entry fake tests continue to pass.

The tests are fake-only. They did not start a service, did not run Ollama, did not run `ollama serve`, did not call external model/API transports, did not download or pull models, did not generate documents, and did not write `output/job/export`.

## 9. Explicit non-integrations

Step 14C did not integrate the safe service entry into:

- real endpoint registration;
- route mounting;
- `backend/app/main.py`;
- `backend/app/routers/actions_bridge.py`;
- `backend/app/routers/zhifei_autoplan.py`;
- `app.py`;
- `frontend_web/app.py`;
- real UI pages;
- service startup;
- real Ollama transport;
- external model/API transports;
- formal generation chains;
- formal export chains;
- output artifact writing;
- job writing;
- ZBid formal writeback.

Current capability remains pure helper + deterministic tests.

## 10. No-write boundary

Step 14C preserves the no-write boundary:

- no正文 modification;
- no `output/` write;
- no `job/` write;
- no `export/` write;
- no formal DOCX output;
- no formal Markdown output;
- no formal JSON output;
- no job ID returned;
- no export path returned;
- no generated document path returned;
- no persisted preview payload;
- no persisted diagnostic payload.

Tests used file-count checks around write surfaces and response-field checks for formal output field names.

## 11. No-generation-chain boundary

Step 14C preserves the no-generation-chain boundary:

- safe entry did not call `/generate`;
- safe entry did not call `/generate_async`;
- safe entry did not call `/generate_async_batch`;
- safe entry did not call `/compose`;
- safe entry did not create generation jobs;
- safe entry did not mutate generated sections;
- safe entry did not return formal generation results;
- safe entry did not modify formal generation-chain files.

The existing generation routes remain present in the repository, but Step 14C did not touch them.

## 12. No-export-chain boundary

Step 14C preserves the no-export-chain boundary:

- safe entry did not call `/export_docx`;
- safe entry did not call `/export`;
- safe entry did not call export service helpers;
- safe entry did not call output artifact helpers;
- safe entry did not create DOCX;
- safe entry did not create formal Markdown;
- safe entry did not create formal JSON;
- safe entry did not expose export file paths;
- safe entry did not modify formal export-chain files.

The existing export routes and export helpers remain present in the repository, but Step 14C did not touch them.

## 13. No-ZBid-writeback boundary

Step 14C preserves the no-ZBid-writeback boundary:

- safe entry did not call ZBid formal writeback;
- safe entry did not call `/review/apply`;
- safe entry did not modify ZBid snapshot mapper;
- safe entry did not write ZBid state;
- safe entry returns `affects_zbid_writeback=false`;
- safe entry did not modify any ZBid formal writeback chain.

ZBid mock preview or mapper assets must not be interpreted as permission for formal writeback.

## 14. Remaining risks

Remaining risks:

- Current capability is only helper-layer safe fake-only service entry.
- Current capability has no real endpoint.
- Current capability has no real UI page.
- Current capability has no service startup verification.
- Current capability has no real Ollama call.
- Current capability has no formal generation-chain integration.
- Current capability has no formal export-chain integration.
- Current capability has no ZBid formal writeback.
- Fake-only tests do not prove that a future real service endpoint is safe to smoke.
- A future service smoke must first confirm whether a real safe endpoint exists.
- A future service smoke must not target `/generate`.
- A future service smoke must not target `/export_docx`.
- A future service smoke must not target `/review/apply`.
- A future stage must not write `output/job/export`.
- A future stage must not automatically modify正文.
- A future stage must not trigger formal export.
- A future stage must not connect ZBid formal writeback.
- A future real Ollama stage would require separate authorization and a separate runtime boundary.

## 15. Required next-stage gate

Before any true endpoint or service smoke stage, the next gate must clarify:

- whether a real safe endpoint is needed;
- whether endpoint implementation is authorized;
- which endpoint path is allowed;
- which files may be modified;
- whether `backend/app/main.py` may be modified;
- whether a new router file may be added;
- whether `backend/app/routers/actions_bridge.py` remains forbidden;
- whether `backend/app/routers/zhifei_autoplan.py` remains forbidden;
- whether UI files remain forbidden;
- which deterministic tests must run;
- how to prove `/generate` is not called;
- how to prove `/export_docx` is not called;
- how to prove `/review/apply` is not called;
- how to prove no `output/job/export` write occurs;
- whether service startup is still forbidden;
- when, if ever, `127.0.0.1` loopback smoke becomes authorized.

If any of these points is not authorized, service smoke must not start.

## 16. Recommended next ZDoc step

The recommended next step is docs-only or read-only verification:

```text
ZDoc Step 14E：ZDoc safe service entry 是否需要真实 endpoint 实现的只读核验 / 前置设计
```

The next step must not go directly into service smoke.

## 17. Closure statement

ZDoc Step 14C completed a safe fake-only service entry helper and deterministic tests. The implementation remains default-off, fake-only, preview-only, no-write, isolated from `/generate`, isolated from `/export_docx`, isolated from `/review/apply`, disconnected from real endpoint registration, disconnected from service startup, disconnected from real Ollama, disconnected from external model/API transports, disconnected from formal generation, disconnected from formal export, and disconnected from ZBid formal writeback.

This Step 14D review authorizes no code changes, no test changes, no pytest run, no service startup, no Ollama run, no `ollama serve`, no external model/API call, no model download or pull, no formal document generation, no `output/job/export` write, no DOCX / JSON / Markdown formal export, and no ZBid formal writeback.

Completion of this review must not be treated as permission to proceed automatically into service smoke.
