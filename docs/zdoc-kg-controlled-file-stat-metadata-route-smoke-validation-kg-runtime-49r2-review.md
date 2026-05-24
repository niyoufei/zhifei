# KG-RUNTIME-49R2 Controlled File-Stat Metadata Route Smoke Validation Review

## 1. Scope

KG-RUNTIME-49R2 retried the controlled file-stat metadata route smoke validation for `/kg/read-only-preview`.

This step validated only whether the route returned file-stat metadata for the single authorized target:

`知识图谱/ZF-KG-12-Municipal-Bridge.json`

No code was modified. No adapter, route, `main.py`, frontend, tests, config, or JSON files were modified.

## 2. Baseline

| Item | Value |
| --- | --- |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `main` |
| Start HEAD | `361b9f11ae8e0dfb0867d8904cc69fe9860259bb` |
| Start tag | `v0.1.429-zdoc-kg-file-stat-metadata-smoke-gate` |
| Start status | clean |

## 3. Command-Level Authorization Boundary

The first default-sandbox uvicorn bind attempt to `127.0.0.1:8011` failed with `operation not permitted`.

The validation then used command-level minimal authorization only for:

- starting the local uvicorn temporary service on `127.0.0.1:8011`;
- calling `http://127.0.0.1:8011/health`;
- calling `http://127.0.0.1:8011/kg/read-only-preview`;
- stopping the temporary uvicorn service;
- confirming port `8011` was released.

No full-access mode was used.

The temporary service was started with:

```text
PYTHONDONTWRITEBYTECODE=1
MPLCONFIGDIR=/private/tmp/zdoc_kg_runtime_49r2_mpl
ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8011 --log-level warning
```

## 4. Request Contract

The `/kg/read-only-preview` request body was limited to:

```json
{
  "request_id": "kg-runtime-49r2-controlled-file-stat-metadata-route-smoke",
  "manual_trigger": true,
  "real_kg_read_only": true,
  "authorized_target": "知识图谱/ZF-KG-12-Municipal-Bridge.json"
}
```

No real KG file body content was opened or read. No real KG JSON was parsed. No `python3 -m json.tool` was run.

## 5. HTTP Results

| Endpoint | Method | HTTP status |
| --- | --- | --- |
| `/health` | GET | `200` |
| `/kg/read-only-preview` | POST | `200` |

`/health` returned `ok=true`, `service="文档生成系统"`, `system_id="docgen-system"`, and `audit_ready=true`.

`/kg/read-only-preview` returned `ok=true`, `enabled=true`, `status="preview_only"`, `reason="adapter_preview_ready"`, and `adapter_status="preview_only"`.

## 6. File-Stat Metadata Result

The route returned the authorized file-stat metadata fields.

| Field | Result |
| --- | --- |
| `authorized_target` | `知识图谱/ZF-KG-12-Municipal-Bridge.json` |
| `allowlist_status` | `authorized_single_target` |
| `exists` | `true` |
| `is_file` | `true` |
| `size_bytes` | `362710` |
| `mtime` | `1777361111` |
| `mode` | `100644` |
| `permission` | `644` |

Required field presence:

| Field | Present |
| --- | --- |
| `authorized_target` | yes |
| `allowlist_status` | yes |
| `exists` | yes |
| `is_file` | yes |
| `size_bytes` | yes |
| `mtime` | yes |
| `mode` | yes |
| `permission` | yes |

## 7. Metadata-Only Boundary

The response remained metadata-only.

Confirmed returned boundary fields included:

| Field | Value |
| --- | --- |
| `read_policy` | `file_stat_metadata_only_no_content_read_no_json_parse` |
| `content_read_performed` | `false` |
| `json_parse_performed` | `false` |
| `writeback_allowed` | `false` |
| `output_write_allowed` | `false` |
| `calls_generate_route` | `false` |
| `calls_export_docx_route` | `false` |
| `calls_review_apply_route` | `false` |
| `writes_document_body` | `false` |
| `writes_output` | `false` |
| `writes_job` | `false` |
| `writes_export` | `false` |
| `calls_ollama` | `false` |
| `loads_knowledge_pack` | `false` |
| `registers_manifest` | `false` |
| `creates_registry` | `false` |

No business body, entity body, knowledge-entry body, generated document body, or generated-ready/RAG-ready text blocks appeared.

The strings `prompt`, `evidence`, and `scoring` appeared only as safety-boundary field names or policy text, such as disabled registry/evidence/scoring flags and the value-output policy. They did not appear as prompt content, evidence content, scoring content, business content, entity content, or KG item content.

## 8. Runtime Side Effects

No generation, export, review apply, ZBid writeback, RAG, registry creation, registry enablement, CI, tests, `py_compile`, `pytest`, Ollama, model pull, model replacement, output write, job write, or export write was triggered.

The service was stopped after validation. Port `8011` was confirmed released.

`PYTHONDONTWRITEBYTECODE=1` was used. No git-visible `.pyc` or `__pycache__` change was produced by this run. Existing ignored `__pycache__` / `.pyc` files were observed but not modified or cleaned.

## 9. Validation Summary

KG-RUNTIME-49R2 completed successfully.

The controlled route smoke confirmed that `/kg/read-only-preview` returns the required file-stat metadata fields for the single authorized target under:

- `ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED=1`;
- `manual_trigger=true`;
- `real_kg_read_only=true`;
- `authorized_target="知识图谱/ZF-KG-12-Municipal-Bridge.json"`.

This step did not enter KG-RUNTIME-50.
