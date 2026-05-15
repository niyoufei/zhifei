# ZDoc Local LLM Preview Isolated Safe Endpoint Service Smoke Report

## Purpose

This report records ZDoc Step 14K. The step only performed an isolated safe endpoint fake-only service smoke for the local LLM preview path.

The smoke target was limited to:

- `POST /local-llm/preview-safe`
- loopback service binding on `127.0.0.1:18749`
- fake-only preview behavior
- default-off, preview-only, no-write behavior

This step did not request `/generate`, `/export_docx`, or `/review/apply`.

## Baseline

- Working directory: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `648ee08452a0c913234085a880cf84d00609c2ad`
- Required baseline tag present: `v0.1.70-zdoc-local-llm-isolated-safe-endpoint-service-smoke-plan`
- Smoke report file: `docs/zdoc-local-llm-preview-isolated-safe-endpoint-service-smoke-report.md`

## Service Boundary

The service was started only for loopback verification.

- Listen address: `127.0.0.1`
- Port: `18749`
- Forbidden listen address: `0.0.0.0`
- Service command used only FastAPI loopback startup.
- No Ollama-related environment variable was used.
- `PYTHONDONTWRITEBYTECODE=1` was set to avoid bytecode artifact writes.

## Scenario A: Disabled

Feature flag behavior:

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` was unset.
- Endpoint requested: `POST /local-llm/preview-safe`
- Payload was synthetic and minimal.
- No real bid, tender, job, output, export, or ZBid writeback payload was used.

Startup command:

```bash
sh -c 'unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED; export PYTHONDONTWRITEBYTECODE=1; python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18749 --log-level warning & echo SERVER_PID=$!; wait $!'
```

Observed PID:

- `26956`

Request summary:

```http
POST http://127.0.0.1:18749/local-llm/preview-safe
Content-Type: application/json
```

Response summary:

- `status`: `disabled`
- `ok`: `false`
- `enabled`: `false`
- `preview_only`: `true`
- `no_write`: `true`
- `affects_generation`: `false`
- `affects_export`: `false`
- `affects_zbid_writeback`: `false`
- `reason`: `feature_flag_disabled`
- `calls_generate_route`: `false`
- `calls_export_docx_route`: `false`
- `calls_review_apply_route`: `false`
- `triggers_generation_chain`: `false`
- `triggers_export_chain`: `false`
- `writes_output`: `false`
- `writes_job`: `false`
- `writes_export`: `false`
- `calls_ollama`: `false`
- `calls_external_model_api`: `false`

Shutdown result:

- Service process stopped with `SIGTERM`.
- Port `18749` was released.
- No background service remained.

## Scenario B: Enabled Fake-Only

Feature flag behavior:

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`
- Endpoint requested: `POST /local-llm/preview-safe`
- Payload was synthetic and minimal.
- No real bid, tender, job, output, export, or ZBid writeback payload was used.

Startup command:

```bash
sh -c 'export ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true; export PYTHONDONTWRITEBYTECODE=1; python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18749 --log-level warning & echo SERVER_PID=$!; wait $!'
```

Observed PID:

- `27008`

Request summary:

```http
POST http://127.0.0.1:18749/local-llm/preview-safe
Content-Type: application/json
```

Response summary:

- `status`: `ok`
- `ok`: `true`
- `enabled`: `true`
- `preview_only`: `true`
- `no_write`: `true`
- `affects_generation`: `false`
- `affects_export`: `false`
- `affects_zbid_writeback`: `false`
- `source`: `zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- `entry_type`: `isolated_safe_endpoint`
- `fake_only`: `true`
- `advisory`: returned deterministic fake preview text
- `suggestions`: returned deterministic advisory suggestions
- `calls_generate_route`: `false`
- `calls_export_docx_route`: `false`
- `calls_review_apply_route`: `false`
- `triggers_generation_chain`: `false`
- `triggers_export_chain`: `false`
- `writes_output`: `false`
- `writes_job`: `false`
- `writes_export`: `false`
- `calls_ollama`: `false`
- `calls_external_model_api`: `false`

Shutdown result:

- Service process stopped with `SIGTERM`.
- Port `18749` was released.
- No background service remained.

## Forbidden Endpoint Verification

The smoke only requested:

- `POST /local-llm/preview-safe`

The smoke did not request:

- `/generate`
- `/export_docx`
- `/review/apply`

The response fields also reported:

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`

## No-Write Verification

Filesystem counts were checked before and after the smoke.

- `output/` file count before: `0`
- `output/` file count after: `0`
- `job/` file count before: `0`
- `job/` file count after: `0`
- `export/` file count before: `0`
- `export/` file count after: `0`
- `backend/data/autoplan/jobs` file count before: `87`
- `backend/data/autoplan/jobs` file count after: `87`

No output, job, export, DOCX, JSON, Markdown export, or ZBid writeback artifact was produced by the smoke.

## Explicit Non-Integrations

This step did not:

- run pytest
- run Ollama
- run `ollama serve`
- call a real Ollama transport
- call an external model/API
- download or pull models
- execute `ollama pull`
- generate formal documents
- write `output/`
- write `job/`
- write `export/`
- trigger DOCX export
- trigger JSON export
- trigger Markdown formal export
- connect to ZBid formal writeback
- modify backend code
- modify endpoint/router code
- modify tests
- modify UI files

## Port Cleanup

The service was stopped after each scenario.

- Disabled scenario port release: `yes`
- Enabled scenario port release: `yes`
- Final `18749` listen check: no listener

## Risk Notes

The smoke verified the isolated safe endpoint through a local FastAPI process on `127.0.0.1`.

Remaining risks:

- This was fake-only smoke, not real Ollama validation.
- This did not authorize real model access.
- This did not authorize `/generate`, `/export_docx`, or `/review/apply` smoke.
- This did not authorize formal generation, export, or ZBid writeback integration.
- Any future real Ollama phase still requires separate design, authorization, and 2号窗口 handling.

## Closure Statement

ZDoc Step 14K completed an isolated safe endpoint fake-only service smoke and wrote this report only. It did not continue into real Ollama, formal generation, formal export, UI integration, or ZBid writeback.
