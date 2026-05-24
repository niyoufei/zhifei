# ZDoc KG Read-Only Preview Manual-Trigger Success-Path Smoke Validation Authorization Gate KG-RUNTIME-15

## 1. Execution Summary

KG-RUNTIME-15 is a docs-only authorization gate for a future
manual-trigger success-path smoke validation. It does not run the backend
service, does not call the route, and does not trigger the adapter success path.

Current disposition:

- KG-RUNTIME-13 confirmed the route returns disabled when the feature flag is
  not enabled.
- KG-RUNTIME-14 confirmed the route returns blocked when the feature flag is
  enabled but `manual_trigger=True` is not provided.
- KG-RUNTIME-16 is not entered by this document.
- KG-RUNTIME-16, if separately authorized by ChatGPT, may validate the success
  path only with inline synthetic disabled manifest and registry entity
  dictionaries.
- KG-RUNTIME-16 must not read real KG files, real entity JSON, source archives,
  or `AI知识图谱大全`.

## 2. Baseline

Repository:

`/Users/youfeini/Desktop/文档生成系统`

Start HEAD:

`eda712ae507d8e90fdc97dd07b0b57a59ecb1044`

Start tag:

`v0.1.395-zdoc-kg-read-only-preview-manual-trigger-blocked-validation`

Review time:

`2026-05-24 11:22:00 CST`

This document is the only intended new file for KG-RUNTIME-15.

## 3. KG-RUNTIME-13 Carried Conclusion

KG-RUNTIME-13 file:

`docs/zdoc-kg-read-only-preview-route-first-manual-service-startup-and-default-off-smoke-validation-kg-runtime-13-review.md`

Carried facts:

- Service startup used the repository documented backend startup command.
- `/health` returned HTTP 200.
- `/kg/read-only-preview` returned HTTP 200.
- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED` was not enabled.
- The route returned `status="disabled"` and
  `reason="feature_flag_disabled"`.
- The route request did not pass `manual_trigger=True`.
- The adapter success path was not invoked.
- The service was stopped.
- No generation, export, review apply, ZBid writeback, RAG, prompt registry,
  system instruction registry, Ollama, validator, test, CI, DOCX generation, or
  `output/job/export` write was performed.

KG-RUNTIME-13 proved only the default-off disabled boundary. It did not prove
success-path usability.

## 4. KG-RUNTIME-14 Carried Conclusion

KG-RUNTIME-14 file:

`docs/zdoc-kg-read-only-preview-route-feature-flag-enabled-manual-trigger-blocked-smoke-validation-kg-runtime-14-review.md`

Carried facts:

- Service startup used the README backend startup command.
- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1` was set only for the temporary
  service process.
- `/health` returned HTTP 200.
- `/kg/read-only-preview` returned HTTP 200.
- The route request payload contained only `request_id`.
- The route returned `status="blocked"` and
  `reason="manual_trigger_required"`.
- The route request did not pass `manual_trigger=True`.
- The adapter success path was not invoked.
- The service was stopped.
- No generation, export, review apply, ZBid writeback, RAG, prompt registry,
  system instruction registry, Ollama, validator, test, CI, DOCX generation, or
  `output/job/export` write was performed.

KG-RUNTIME-14 proved only the manual-trigger blocked boundary. It did not prove
success-path usability.

## 5. KG-RUNTIME-16 Authorization Boundary

KG-RUNTIME-16 is not authorized by this file alone. It may proceed only if
ChatGPT separately authorizes it with a new start HEAD and tag.

If authorized, KG-RUNTIME-16 may validate the route success path under these
minimum limits:

- use the README backend startup command;
- set `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1` only for the temporary
  service process;
- pass `manual_trigger=True` exactly once in the KG route payload;
- call `/health` or root only for service startup confirmation;
- call `/kg/read-only-preview` only once for the success-path smoke;
- use inline synthetic disabled manifest and registry entity dictionaries;
- stop the temporary service immediately after the allowed requests;
- write only the KG-RUNTIME-16 review document, if that stage authorizes one.

KG-RUNTIME-16 must remain a smoke validation, not a usable feature release.

## 6. Synthetic Entity Data Requirement

KG-RUNTIME-16 must use inline synthetic disabled data in the request payload.
The synthetic data must be written directly in the request body and must not be
loaded from a file.

Allowed synthetic manifest entity shape:

```json
{
  "pilot_name": "kg-runtime-16-synthetic-pilot",
  "pilot_direction": "synthetic read-only preview smoke",
  "domain_tags": ["synthetic", "read_only_preview"],
  "risk_level": "synthetic_review_only",
  "enabled": false,
  "registration_status": "not_registered",
  "runtime_loadable": false,
  "evidence_allowed": false,
  "scoring_allowed": false
}
```

Allowed synthetic registry entity shape:

```json
{
  "registry_candidate_id": "kg-runtime-16-synthetic-registry",
  "domain_tags": ["synthetic", "read_only_preview"],
  "risk_level": "synthetic_review_only",
  "enabled": false,
  "registration_status": "not_registered",
  "runtime_loadable": false,
  "evidence_allowed": false,
  "scoring_allowed": false
}
```

Forbidden payload sources:

- `AI知识图谱大全`;
- KG-31 disabled manifest entity JSON;
- KG-33 disabled registry entity JSON;
- KG-08 manifest candidate JSON;
- KG-15 registry candidate JSON;
- any source archive file;
- any real knowledge pack;
- any RAG corpus;
- any prompt pack;
- any system instruction file.

## 7. KG-RUNTIME-16 Allowed Command Set If Authorized

KG-RUNTIME-16 may use only commands equivalent to the following, with the final
exact values restated in that stage.

Startup:

```bash
env ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/youfeini/Desktop/文档生成系统 MPLCONFIGDIR=/private/tmp/zdoc_kg_runtime_16_mpl python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl -sS -i http://127.0.0.1:8000/health
```

Route smoke:

```bash
curl -sS -i -X POST http://127.0.0.1:8000/kg/read-only-preview -H 'Content-Type: application/json' --data '<inline synthetic payload>'
```

Shutdown:

```bash
kill <temporary_uvicorn_pid>
```

Post-shutdown confirmation:

```bash
ps -p <temporary_uvicorn_pid> -o pid=,command=
```

KG-RUNTIME-16 must not run validators, tests, CI, `py_compile`, Ollama, model
commands, generation commands, export commands, review apply commands, registry
commands, or knowledge pack activation commands.

## 8. KG-RUNTIME-16 Payload Restriction

The only allowed route request for KG-RUNTIME-16 is one POST to:

`/kg/read-only-preview`

The request may contain only these top-level fields:

- `request_id`;
- `manual_trigger`;
- `manifest_entity`;
- `registry_entity`.

Required values:

- `request_id`: a KG-RUNTIME-16 smoke identifier;
- `manual_trigger`: `true`;
- `manifest_entity`: inline synthetic disabled dictionary;
- `registry_entity`: inline synthetic disabled dictionary.

The payload must not contain:

- file paths;
- original source text;
- system instruction text;
- prompt text;
- evidence text;
- scoring rules;
- document body content;
- real project data;
- customer or personal information;
- `source_path` pointing to real files;
- any field intended to load or register a knowledge pack.

## 9. KG-RUNTIME-16 Expected Return

If KG-RUNTIME-16 is authorized and the route behaves as currently designed, the
expected success-path response should include:

- HTTP status `200 OK`;
- `enabled=true`;
- `status="preview_only"`;
- `adapter_status="preview_only"`;
- `reason="adapter_preview_ready"`;
- `preview_only=true`;
- `read_only=true`;
- `no_write=true`;
- `runtime_access=false`;
- `writeback_allowed=false`;
- `output_write_allowed=false`;
- `evidence_allowed=false`;
- `scoring_allowed=false`;
- `rag_allowed=false`;
- `prompt_registry_allowed=false`;
- `system_instruction_registry_allowed=false`;
- `calls_generate_route=false`;
- `calls_export_docx_route=false`;
- `calls_review_apply_route=false`;
- `calls_ollama=false`;
- `calls_external_endpoint=false`;
- `loads_knowledge_pack=false`;
- `registers_manifest=false`;
- `creates_registry=false`.

The response must be treated only as a smoke payload. It must not be treated as
evidence, scoring basis, generation input, formal preview feature availability,
or production readiness.

## 10. Hard Prohibitions For KG-RUNTIME-16

KG-RUNTIME-16 must not:

- read `AI知识图谱大全` source files;
- read KG-31 or KG-33 entity JSON;
- read KG-08 or KG-15 candidate JSON;
- load real knowledge packs;
- create a registry;
- register, enable, or load knowledge packs;
- connect RAG;
- connect prompt registry;
- connect system instruction registry;
- access `/generate`;
- access `/export_docx`;
- access `/review/apply`;
- trigger ZBid writeback;
- write document body content;
- write `output/job/export`;
- use the response as evidence;
- use the response as scoring;
- run Ollama;
- upgrade, pull, delete, or replace local models;
- run validator;
- run `py_compile`;
- run tests or CI;
- modify frontend, tests, config, JSON, KG-41 validator draft, or
  KG-RUNTIME-03 skeleton;
- modify `backend/app/main.py`;
- modify `backend/app/routers/kg_read_only_preview.py`;
- modify `backend/kg_read_only_preview_adapter.py`;
- clean or modify existing `__pycache__` or `.pyc` files.

## 11. Stop And Rollback Requirements

KG-RUNTIME-16 must stop immediately and report without repair if:

- service startup fails;
- the route cannot be reached after startup;
- `/health` fails;
- the route response is not `preview_only`;
- the route response omits required no-write, no-evidence, no-scoring, or
  no-registry false flags;
- any unexpected file is modified;
- any `.pyc` related to the route or adapter is created;
- any forbidden endpoint is accessed;
- any output, job, export, DOCX, registry, model, test, validator, or CI side
  effect appears.

Rollback and cleanup expectations:

- stop the temporary service;
- confirm the temporary process exited;
- confirm the port is no longer listening if the KG-RUNTIME-16 authorization
  permits that check;
- leave source code unchanged;
- leave JSON unchanged;
- leave existing docs unchanged except for the authorized KG-RUNTIME-16 review
  document;
- do not delete or clean existing `__pycache__` or `.pyc` files;
- do not remove user data or source archives.

## 12. No Current Runtime Action

KG-RUNTIME-15 performed no runtime action.

This step did not:

- run service;
- call endpoint;
- access port;
- trigger adapter;
- run validator;
- run `py_compile`;
- run tests or CI;
- run Ollama;
- upgrade, pull, delete, or replace local models;
- modify code;
- modify JSON;
- modify existing docs;
- write `output/job/export`;
- enter KG-RUNTIME-16.

## 13. KG-RUNTIME-16 Gate

KG-RUNTIME-16 remains pending separate ChatGPT authorization.

The next authorization must explicitly restate:

- start HEAD and tag;
- exact startup command;
- exact feature flag setting;
- exact request payload;
- whether `manual_trigger=True` is permitted;
- health path;
- KG route path;
- shutdown command;
- post-shutdown checks;
- no-write and no-evidence boundaries;
- forbidden endpoints;
- expected response fields;
- rollback requirements.

Without separate authorization, KG-RUNTIME-16 must not start.
