# ZDoc KG Read-Only Preview Route First Manual Service Startup And Default-Off Smoke Validation KG-RUNTIME-13

## 1. Execution Summary

KG-RUNTIME-13 performed the first controlled manual backend startup for the KG
read-only preview route draft. The check was limited to service startup, one
minimal health request, and one default-off route request.

Result:

- Backend service startup succeeded with the repository documented manual
  startup command.
- `/health` returned HTTP 200.
- `/kg/read-only-preview` returned HTTP 200 with `status="disabled"` and
  `reason="feature_flag_disabled"`.
- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED` was not enabled.
- The KG route request did not pass `manual_trigger=True`.
- The adapter success path was not reached.
- The temporary service was stopped after validation.
- This step does not make the KG preview route a usable feature.

## 2. Baseline

Repository:

`/Users/youfeini/Desktop/文档生成系统`

Start HEAD:

`99d4566dc374673e760366067f21d9c576ec2792`

Start tag:

`v0.1.393-zdoc-kg-read-only-preview-route-frozen-audit-package`

Review time:

`2026-05-24 09:52:32 CST`

This document is the only intended new file for KG-RUNTIME-13.

## 3. Startup Method Source

The startup method was taken from repository documentation:

- `RUNBOOK.md`: `python3 -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000`
- `README.md`: `python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`

KG-RUNTIME-13 used the non-reload manual startup form from `README.md` to reduce
runtime side effects.

Actual startup command:

```bash
env -u ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/youfeini/Desktop/文档生成系统 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Boundary controls in the command:

- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED` was explicitly unset.
- `PYTHONDONTWRITEBYTECODE=1` was used to avoid creating new `.pyc` files.
- No reload mode was used.
- No model, Ollama, validator, test, CI, export, or writeback command was run.

The first sandboxed startup attempt initialized the app but could not bind
`127.0.0.1:8000` because the sandbox rejected the port bind. It shut down
without endpoint access. The same startup command was then run with approved
local service permission for this manual smoke validation.

## 4. Service Startup Result

Startup evidence:

- Uvicorn reported `Application startup complete`.
- Uvicorn reported `Uvicorn running on http://127.0.0.1:8000`.
- Process checked during the run: PID `93565`.
- Port checked during the run: `127.0.0.1:8000`.

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
{"request_id":"kg-runtime-13-default-off-smoke"}
```

The request intentionally did not include `manual_trigger`, and therefore did
not pass `manual_trigger=True`.

No other endpoint was called by this step.

## 6. Default-Off Route Result

The KG read-only preview route returned:

```json
{
  "ok": false,
  "enabled": false,
  "status": "disabled",
  "reason": "feature_flag_disabled",
  "request_id": "kg-runtime-13-default-off-smoke",
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

Default-off conclusion:

- The route stayed disabled.
- The feature flag was not enabled.
- The request did not satisfy the manual trigger gate.
- The adapter success path was not invoked.
- No KG content was loaded.
- No evidence or scoring path was created.
- No generation, export, review apply, ZBid writeback, RAG, prompt registry, or
  system instruction registry path was triggered.

## 7. Shutdown Result

The temporary service was stopped after the two allowed requests.

Shutdown evidence:

- Uvicorn reported `Shutting down`.
- Uvicorn reported `Application shutdown complete`.
- Uvicorn reported `Finished server process [93565]`.
- `ps -p 93565` returned no process after shutdown.
- `lsof -nP -iTCP:8000 -sTCP:LISTEN` returned no listener after shutdown.

Shutdown conclusion:

`stopped`

## 8. Forbidden Action Review

KG-RUNTIME-13 did not:

- enable `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED`;
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
- clean or modify existing `__pycache__` or `.pyc` files.

## 9. File And Working Tree Review

No code file was intentionally changed in KG-RUNTIME-13.

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

`backend/data/audit` already existed before the health check. The health check
did not require creation of that directory in this run.

No KG route or adapter related `.pyc` file was found after the smoke.

## 10. Not A Usability Acceptance

This step is not a usability acceptance and must not be treated as a runtime
feature release.

The route remains:

- default-off;
- disabled unless explicitly authorized in a later stage;
- not frontend-connected;
- not a generation input;
- not an evidence source;
- not a scoring basis;
- not connected to RAG, prompt registry, or system instruction registry;
- not connected to `AI知识图谱大全` source file loading.

## 11. KG-RUNTIME-14 Gate

KG-RUNTIME-14 is not entered by this step.

If ChatGPT separately authorizes KG-RUNTIME-14, it should be limited to a
separate review or next controlled validation gate. It must restate:

- start HEAD and tag;
- whether the feature flag may remain disabled or be enabled;
- exact allowed endpoint paths;
- exact allowed payloads;
- whether `manual_trigger=True` is allowed;
- service startup and shutdown requirements;
- forbidden endpoints;
- no-write boundaries;
- rollback and cleanup expectations.

Without a separate ChatGPT authorization, no further KG runtime stage may start.
