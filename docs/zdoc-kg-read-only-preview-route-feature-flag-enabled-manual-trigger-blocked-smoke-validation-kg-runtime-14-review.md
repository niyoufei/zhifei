# ZDoc KG Read-Only Preview Route Feature-Flag-Enabled Manual-Trigger-Blocked Smoke Validation KG-RUNTIME-14

## 1. Execution Summary

KG-RUNTIME-14 performed a controlled smoke validation of the KG read-only
preview route with the route feature flag temporarily enabled and
`manual_trigger=True` intentionally omitted.

Result:

- Backend service startup succeeded with the README manual startup command.
- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1` was set only for the temporary
  service process.
- `/health` returned HTTP 200.
- `/kg/read-only-preview` returned HTTP 200 with `status="blocked"` and
  `reason="manual_trigger_required"`.
- The request payload contained only `request_id`.
- The request did not pass `manual_trigger=True`.
- The adapter success path was not reached.
- The temporary service was stopped after validation.
- This step does not make the KG preview route a usable feature.

## 2. Baseline

Repository:

`/Users/youfeini/Desktop/文档生成系统`

Start HEAD:

`2c33666b3237ccdf3964da7344ad3222f03cc5c8`

Start tag:

`v0.1.394-zdoc-kg-read-only-preview-default-off-smoke-validation`

Review time:

`2026-05-24 11:16:46 CST`

This document is the only intended new file for KG-RUNTIME-14.

## 3. Startup Command

Startup method source:

`README.md`

Documented command:

```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Actual startup command:

```bash
env ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/youfeini/Desktop/文档生成系统 MPLCONFIGDIR=/private/tmp/zdoc_kg_runtime_14_mpl python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Boundary controls in the command:

- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1` was set only for this temporary
  service process.
- `PYTHONDONTWRITEBYTECODE=1` was used to avoid creating new `.pyc` files.
- No reload mode was used.
- `MPLCONFIGDIR` was pointed to `/private/tmp/zdoc_kg_runtime_14_mpl`, outside
  the repository.
- No model, Ollama, validator, test, CI, export, or writeback command was run.

## 4. Service Startup Result

Startup evidence:

- Uvicorn reported `Application startup complete`.
- Uvicorn reported `Uvicorn running on http://127.0.0.1:8000`.
- Process checked during the run: PID `97109`.
- Port used during the run: `127.0.0.1:8000`.

Service startup conclusion:

`success`

This only proves the backend could start for this controlled smoke. It does not
prove feature usability, frontend integration, generation behavior, export
behavior, model behavior, or production readiness.

## 5. Accessed Paths

Allowed service startup check:

```text
GET /health
```

Health response conclusion:

- HTTP status: `200 OK`
- Body included `ok=true`
- Body included `service="文档生成系统"`
- Body included `audit_ready=true`

Allowed KG route smoke check:

```text
POST /kg/read-only-preview
```

KG route request payload:

```json
{"request_id":"kg-runtime-14-manual-trigger-blocked-smoke"}
```

The request intentionally did not include `manual_trigger`, and therefore did
not pass `manual_trigger=True`.

No other endpoint was called by this step.

## 6. Manual-Trigger Blocked Result

The KG read-only preview route returned:

```json
{
  "ok": false,
  "enabled": true,
  "status": "blocked",
  "reason": "manual_trigger_required",
  "request_id": "kg-runtime-14-manual-trigger-blocked-smoke",
  "endpoint_path": "/kg/read-only-preview",
  "feature_flag": "ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED",
  "default_off": true,
  "manual_trigger_required": true,
  "preview_only": true,
  "read_only": true,
  "no_write": true,
  "runtime_access": false,
  "writeback_allowed": false,
  "output_write_allowed": false,
  "evidence_allowed": false,
  "scoring_allowed": false,
  "rag_allowed": false,
  "prompt_registry_allowed": false,
  "system_instruction_registry_allowed": false,
  "calls_generate_route": false,
  "calls_export_docx_route": false,
  "calls_review_apply_route": false,
  "calls_ollama": false,
  "calls_external_endpoint": false,
  "loads_knowledge_pack": false,
  "registers_manifest": false,
  "creates_registry": false
}
```

Blocked-path conclusion:

- The route recognized the feature flag as enabled for the temporary process.
- The route blocked the request because `manual_trigger=True` was not provided.
- The adapter success path was not invoked.
- No manifest, registry, or knowledge pack was loaded.
- No KG source content was read.
- No evidence or scoring path was created.
- No generation, export, review apply, ZBid writeback, RAG, prompt registry, or
  system instruction registry path was triggered.

## 7. Shutdown Result

The temporary service was stopped after the two allowed requests.

Shutdown evidence:

- Uvicorn reported `Shutting down`.
- Uvicorn reported `Application shutdown complete`.
- Uvicorn reported `Finished server process [97109]`.
- `ps -p 97109` returned no process after shutdown.
- `lsof -nP -iTCP:8000 -sTCP:LISTEN` returned no listener after shutdown.

Shutdown conclusion:

`stopped`

## 8. Forbidden Action Review

KG-RUNTIME-14 did not:

- pass `manual_trigger=True`;
- call the adapter success path;
- read `AI知识图谱大全` source files;
- register, enable, or load a knowledge pack;
- connect RAG, prompt registry, or system instruction registry;
- access `/generate`;
- access `/export_docx`;
- access `/review/apply`;
- trigger ZBid writeback;
- generate DOCX;
- write `output/job/export`;
- run the KG validator;
- run `py_compile`;
- run tests or CI;
- run Ollama;
- upgrade, pull, delete, or replace local models;
- modify frontend, tests, config, JSON, KG-41 validator draft, or
  KG-RUNTIME-03 skeleton;
- modify `backend/app/main.py`;
- modify `backend/app/routers/kg_read_only_preview.py`;
- modify `backend/kg_read_only_preview_adapter.py`;
- clean or modify existing `__pycache__` or `.pyc` files.

## 9. File And Working Tree Review

No code file was intentionally changed in KG-RUNTIME-14.

Protected files remained unmodified:

- `backend/app/main.py`
- `backend/app/routers/kg_read_only_preview.py`
- `backend/kg_read_only_preview_adapter.py`
- JSON candidate/entity files under `docs/`
- KG-41 validator draft
- KG-RUNTIME-03 adapter skeleton
- frontend files
- tests
- config files

No KG route or adapter related `.pyc` file was found after the smoke.

## 10. Not A Usability Acceptance

This step is not a usability acceptance and must not be treated as a runtime
feature release.

The route remains:

- gated by explicit feature flag;
- gated by `manual_trigger=True`;
- not frontend-connected;
- not a generation input;
- not an evidence source;
- not a scoring basis;
- not connected to RAG, prompt registry, or system instruction registry;
- not connected to `AI知识图谱大全` source file loading.

## 11. KG-RUNTIME-15 Gate

KG-RUNTIME-15 is not entered by this step.

If ChatGPT separately authorizes KG-RUNTIME-15, it must restate:

- start HEAD and tag;
- whether `manual_trigger=True` may be used;
- exact allowed endpoint paths;
- exact allowed payloads;
- service startup and shutdown requirements;
- forbidden endpoints;
- no-write boundaries;
- rollback and cleanup expectations.

Without a separate ChatGPT authorization, no further KG runtime stage may start.
