# ZDoc KG-RUNTIME-42 First Controlled Metadata-Only Route Smoke Validation Review

## 1. Scope

KG-RUNTIME-42 performed the first controlled route-level smoke validation for `/kg/read-only-preview`.

This review records only metadata-only route behavior under the authorized runtime gate:

- feature flag: `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`
- `manual_trigger=true`
- `real_kg_read_only=true`
- `authorized_target=知识图谱/ZF-KG-12-Municipal-Bridge.json`

This step did not enter KG-RUNTIME-43.

## 2. Baseline

| Item | Value |
| --- | --- |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `main` |
| Start HEAD | `c14c0241f249008605d927ad31dbdc4425781aaf` |
| Start tag at HEAD | `v0.1.422-zdoc-kg-real-route-smoke-authorization-gate` |
| Start git status | clean |

## 3. Service Control

| Control | Result |
| --- | --- |
| Service binding | `127.0.0.1:8010` only |
| Service command scope | temporary FastAPI backend only |
| Feature flag | temporarily enabled only for this service process |
| Initial sandbox bind attempt | failed before any route call with `operation not permitted`; no usable listener remained |
| Authorized service start | succeeded after local bind permission was granted |
| Service stopped after smoke | yes |
| Port released after stop | yes; no listener remained on `127.0.0.1:8010` |

## 4. Calls Performed

Only the following HTTP calls were performed:

| Call | Method | Result |
| --- | --- | --- |
| `/health` | GET | HTTP 200 |
| `/kg/read-only-preview` | POST | HTTP 200 |

No calls were made to `/generate`, `/export_docx`, or `/review/apply`.

## 5. Authorized Preview Request

The `/kg/read-only-preview` request body was limited to:

```json
{
  "request_id": "kg-runtime-42-first-controlled-metadata-only-route-smoke",
  "manual_trigger": true,
  "real_kg_read_only": true,
  "authorized_target": "知识图谱/ZF-KG-12-Municipal-Bridge.json"
}
```

No real KG file body content was opened or read. No real KG JSON was parsed. No `python3 -m json.tool` was run.

## 6. Health Result

`/health` returned HTTP 200.

Observed metadata:

| Field | Value |
| --- | --- |
| `ok` | `true` |
| `service` | `文档生成系统` |
| `system_id` | `docgen-system` |
| `audit_ready` | `true` |

## 7. Read-Only Preview Result

`/kg/read-only-preview` returned HTTP 200 and remained metadata-only.

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

The adapter detail also returned:

| Field | Value |
| --- | --- |
| `detail.status` | `preview_only` |
| `detail.reason` | `real_kg_route_read_only_metadata_only` |
| `detail.contract_scope` | `route-level real-KG metadata-only read-only contract` |
| `detail.target_policy` | `single_authorized_target_identifier_metadata_only_no_io` |
| `detail.value_output_policy` | `contract_metadata_only_no_entity_knowledge_prompt_instruction_evidence_scoring_generation_or_rag_text` |
| `detail.content_read_performed` | `false` |
| `detail.json_parse_performed` | `false` |
| `detail.no_write` | `true` |
| `detail.no_evidence` | `true` |
| `detail.no_scoring` | `true` |
| `detail.no_rag` | `true` |
| `detail.no_generation` | `true` |
| `detail.no_export` | `true` |
| `detail.no_zbid_writeback` | `true` |

## 8. Metadata-Only Content Check

The response contained only route, flag, policy, status, count, and boolean control metadata.

The response did not contain:

- real business body values;
- entity body content;
- knowledge entry body content;
- prompt text;
- system instruction text;
- evidence content;
- scoring content;
- generated document body content;
- RAG-ready text blocks;
- prompt registry content;
- system instruction registry content.

The only KG target value present was the authorized identifier `知识图谱/ZF-KG-12-Municipal-Bridge.json`.

## 9. Forbidden Action Confirmation

KG-RUNTIME-42 did not:

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

## 10. Pycache Cleanup

The temporary service run created the following route / adapter related cache files:

- `backend/app/routers/__pycache__/kg_read_only_preview.cpython-313.pyc`
- `backend/__pycache__/kg_read_only_preview_adapter.cpython-313.pyc`

Only these two newly created cache files were removed.

Pre-existing cache files and directories were not otherwise cleaned or modified.

## 11. Output / Job / Export Check

No newly written files were observed under `output`, `job`, or `export` for this smoke window.

## 12. Conclusion

KG-RUNTIME-42 is complete.

The route-level controlled smoke returned HTTP 200 for `/health` and HTTP 200 for `/kg/read-only-preview`.

The `/kg/read-only-preview` response stayed metadata-only under the required feature flag, manual trigger, read-only control, and single authorized target identifier.

KG-RUNTIME-42 did not enter KG-RUNTIME-43.
