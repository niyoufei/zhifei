# ZDoc KG-RUNTIME-44 Controlled Real-KG File-Metadata Route-Level Smoke Validation Review

## 1. Scope

KG-RUNTIME-44 performed a controlled route-level smoke validation for `/kg/read-only-preview` under the KG-RUNTIME-43 authorization gate.

This review records only the authorized metadata-only smoke result. It does not enter KG-RUNTIME-45.

Authorized target:

- `知识图谱/ZF-KG-12-Municipal-Bridge.json`

Allowed runtime controls used:

- temporary FastAPI service startup;
- temporary feature flag enablement: `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`;
- local access only to `127.0.0.1:8010`;
- `GET /health`;
- `POST /kg/read-only-preview`;
- request body with `manual_trigger=true`, `real_kg_read_only=true`, and the single authorized target.

## 2. Baseline

| Item | Value |
| --- | --- |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `main` |
| Start HEAD | `50656cde5d5bb6a3dfc4d90b40e6087b6c1824a5` |
| Start tag at HEAD | `v0.1.424-zdoc-kg-route-smoke-frozen-audit-gate` |
| Start git status | clean |

## 3. Target File Metadata Check

The authorized target was checked with filesystem metadata commands only. The file body was not opened or read, and the JSON was not parsed.

| Field | Observed value |
| --- | --- |
| authorized_target | `知识图谱/ZF-KG-12-Municipal-Bridge.json` |
| file exists | yes |
| file type | regular file |
| size | `362710` bytes |
| mtime | `1777361111` |
| mtime local | `2026-04-28 15:25:11 +0800` |
| mode | `100644` |
| permission | `644` |
| uid | `501` |
| gid | `20` |

No `python3 -m json.tool` command was run.

## 4. Service Control

| Control | Result |
| --- | --- |
| Service binding | `127.0.0.1:8010` only |
| Feature flag | enabled only for this temporary service process |
| Bytecode control | `PYTHONDONTWRITEBYTECODE=1` |
| Initial sandbox bind attempt | failed before route calls with `operation not permitted`; no usable listener remained |
| Authorized service start | succeeded after local bind permission |
| Service stopped after smoke | yes |
| Port released after stop | yes; no listener remained on `127.0.0.1:8010` |

The service startup caused Matplotlib to build a cache under `/private/tmp/zdoc_mpl_kg_runtime44`. This was outside the repository and not under `output`, `job`, or `export`.

## 5. Calls Performed

Only the following HTTP calls were performed:

| Call | Method | Result |
| --- | --- | --- |
| `/health` | GET | HTTP 200 |
| `/kg/read-only-preview` | POST | HTTP 200 |

No calls were made to `/generate`, `/export_docx`, or `/review/apply`.

## 6. Authorized Preview Request

The `/kg/read-only-preview` request body was limited to:

```json
{
  "request_id": "kg-runtime-44-controlled-real-kg-file-metadata-route-level-smoke",
  "manual_trigger": true,
  "real_kg_read_only": true,
  "authorized_target": "知识图谱/ZF-KG-12-Municipal-Bridge.json"
}
```

No extra request fields were sent.

## 7. Health Result

`/health` returned HTTP 200.

Observed fields:

| Field | Value |
| --- | --- |
| `ok` | `true` |
| `service` | `文档生成系统` |
| `system_id` | `docgen-system` |
| `workspace_root` | `/Users/youfeini/Desktop/文档生成系统` |
| `audit_ready` | `true` |

## 8. Read-Only Preview Result

`/kg/read-only-preview` returned HTTP 200.

Observed route-level fields:

| Field | Value |
| --- | --- |
| `ok` | `true` |
| `enabled` | `true` |
| `status` | `preview_only` |
| `reason` | `adapter_preview_ready` |
| `route_name` | `kg_read_only_preview` |
| `endpoint_path` | `/kg/read-only-preview` |
| `feature_flag` | `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED` |
| `manual_trigger_required` | `true` |
| `preview_only` | `true` |
| `read_only` | `true` |
| `adapter_status` | `preview_only` |
| `authorized_target` | `知识图谱/ZF-KG-12-Municipal-Bridge.json` |
| `target_policy` | `single_authorized_target_identifier_metadata_only_no_io` |
| `read_policy` | `no_file_io_no_content_read_no_json_parse` |
| `content_read_performed` | `false` |
| `json_parse_performed` | `false` |

Observed negative-control fields:

| Field | Value |
| --- | --- |
| `writeback_allowed` | `false` |
| `output_write_allowed` | `false` |
| `evidence_allowed` | `false` |
| `scoring_allowed` | `false` |
| `rag_allowed` | `false` |
| `prompt_registry_allowed` | `false` |
| `system_instruction_registry_allowed` | `false` |
| `knowledge_pack_load_allowed` | `false` |
| `calls_generate_route` | `false` |
| `calls_export_docx_route` | `false` |
| `calls_review_apply_route` | `false` |
| `triggers_generation_chain` | `false` |
| `triggers_export_chain` | `false` |
| `affects_generation` | `false` |
| `affects_export` | `false` |
| `affects_zbid_writeback` | `false` |
| `writes_document_body` | `false` |
| `writes_output` | `false` |
| `writes_job` | `false` |
| `writes_export` | `false` |
| `calls_ollama` | `false` |
| `calls_external_endpoint` | `false` |
| `downloads_models` | `false` |
| `pulls_models` | `false` |
| `loads_knowledge_pack` | `false` |
| `registers_manifest` | `false` |
| `creates_registry` | `false` |

## 9. File-Metadata Route Observation

The route response stayed metadata-only and did not expose real KG business content, entity content, knowledge entry content, prompt content, system instruction content, evidence content, scoring content, generated document body content, RAG-ready content, registry content, or writeback content.

However, the current route / adapter response did not return filesystem file-stat metadata fields such as:

- file existence;
- file type;
- size;
- mtime;
- mode / permission.

Those filesystem metadata values were verified externally by metadata-only `stat` / `test` checks in this smoke window, without reading file body content or parsing JSON. The actual route response remains contract metadata-only, with `read_policy=no_file_io_no_content_read_no_json_parse`.

Therefore KG-RUNTIME-44 completed the controlled smoke execution and captured one route-level gap: the endpoint currently returns authorized target and contract metadata, but not file-stat metadata.

## 10. Forbidden Action Confirmation

KG-RUNTIME-44 did not:

- modify code;
- modify adapter, route, or `main.py`;
- modify frontend, tests, config, or JSON;
- read real KG file body content;
- parse real KG JSON;
- run `python3 -m json.tool`;
- read, copy, move, or delete `AI知识图谱大全`;
- load a real knowledge package;
- create, register, or enable any registry or knowledge package;
- call `/generate`, `/export_docx`, or `/review/apply`;
- trigger ZBid writeback;
- write document body content;
- write `output`, `job`, or `export`;
- run Ollama;
- upgrade, pull, delete, or replace any model;
- run `py_compile`;
- run `pytest`;
- connect tests or CI;
- enter real use;
- use the response as evidence;
- use the response as scoring.

## 11. Pycache And Repository Artifact Check

No route / adapter related `.pyc` file was produced for:

- `backend/app/routers/kg_read_only_preview.py`;
- `backend/kg_read_only_preview_adapter.py`.

No cleanup was required for route / adapter `.pyc` files.

The repository did not contain `output`, `job`, or `export` directories at the post-smoke check, so no new files were observed there.

## 12. Validation Commands

| Command | Result |
| --- | --- |
| `git diff --check` | passed with exit code 0 before staging |
| `git diff --cached --check` | passed with exit code 0 after staging |

## 13. Conclusion

KG-RUNTIME-44 controlled route-level smoke validation is complete.

The service returned HTTP 200 for `/health` and HTTP 200 for `/kg/read-only-preview` under the required feature flag, manual trigger, read-only control, and single authorized target.

The route response remained metadata-only and did not expose KG body content or connect to generation, export, writeback, Ollama, RAG, prompt registry, system instruction registry, evidence, scoring, tests, or CI.

The endpoint currently does not return file-stat metadata fields. This review records that gap without modifying code.

KG-RUNTIME-45 was not entered.
