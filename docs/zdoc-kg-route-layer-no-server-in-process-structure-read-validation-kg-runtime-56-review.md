# KG-RUNTIME-56 route-layer no-server structure-read validation

## Scope

- Stage: KG-RUNTIME-56.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `508d830b56efdc6b37f52c7277bb6147c2a06faf`.
- Start tag: `v0.1.437-zdoc-kg-no-server-structure-read-smoke-frozen-gate`.
- Authorized target: `知识图谱/ZF-KG-12-Municipal-Bridge.json`.
- Boundary: route-layer no-server in-process validation only.
- Stop line: did not enter KG-RUNTIME-57.

## Method

- Ran one `PYTHONDONTWRITEBYTECODE=1 python3` in-process validation.
- Called `backend.app.routers.kg_read_only_preview.kg_read_only_preview_route` directly.
- Did not use FastAPI `TestClient`.
- Did not import or start `uvicorn`.
- Did not bind a TCP port.
- Did not access `127.0.0.1` or `localhost`.
- Set the route feature flag inside the Python process only.
- Installed in-process guards before route import:
  - `socket.socket.bind` and `socket.socket.connect` fail immediately if called.
  - `Path.open` and `builtins.open` allow only the single authorized KG file under `知识图谱/`.
  - `Path.open` and `builtins.open` fail on any `AI知识图谱大全` access.
  - `os.scandir` and `os.listdir` fail on any KG directory or `AI知识图谱大全` scan.
  - output/job/export write attempts fail immediately.
- Wrapped the route module's adapter callable in memory to capture route-to-adapter arguments, then delegated to the original adapter implementation.

## Payload

The successful structure-read payload used the required gate fields:

- `manual_trigger = true`
- `real_kg_read_only = true`
- `structure_read = true`
- `authorized_target = 知识图谱/ZF-KG-12-Municipal-Bridge.json`

## Route Validation Results

All blocked-input checks returned the expected route-layer reason and did not call the adapter:

- Missing/false manual trigger: `manual_trigger_required`.
- Authorized target without real-KG read-only: `real_kg_read_only_required_for_authorized_target`.
- Explicit false real-KG read-only: `real_kg_read_only_true_required`.
- Explicit false structure read: `structure_read_true_required`.
- Structure read without real-KG read-only: `real_kg_read_only_required_for_structure_read`.
- Structure read without authorized target: `authorized_target_required_for_structure_read`.

## Route To Adapter Passthrough

The successful route call invoked the adapter exactly once with:

- `manual_trigger` passed as true.
- `real_kg_read_only` passed as true.
- `structure_read` passed as true.
- `real_kg_target` matching the authorized target.
- `feature_flag_enabled` passed as true.
- Empty manifest and registry dictionaries for the real-KG read-only route path.

## Returned Contract

The successful route response returned:

- `ok = true`
- `status = preview_only`
- `adapter_status = preview_only`
- `structure_read = true`
- `structure_read_only = true`
- `structure_summary` present.
- `structure_contract` present.

The `structure_summary` key set matched the allowlist exactly. No missing or unexpected keys were reported. Allowlisted keys:

- `top_level_type`
- `top_level_key_names`
- `top_level_key_count`
- `dict_count`
- `list_count`
- `null_count`
- `scalar_type_counts`
- `selected_structure_paths`
- `list_lengths`
- `field_type_sets`
- `max_depth_limited`
- `authorized_target`
- `allowlist_status`

## Structure Output Safety

The validation output and this review intentionally do not expand KG body content or structure details. Only booleans, counts, route reasons, contract field names, and guard counters are recorded.

Observed structure-safety checks:

- `selected_structure_paths` entries are path/type records only.
- `list_lengths` contains lengths and element type counts only.
- `field_type_sets` contains field type names only.
- `scalar_type_counts` contains scalar type counts only.

No JSON scalar values were output.
No list element content was output.
No dict values were output.
No business正文, entity正文, knowledge entry正文, prompt content, system instruction content, evidence content, or scoring content was output.

## Runtime Boundary Evidence

- `uvicorn_imported = false`.
- `fastapi_testclient_used = false`.
- `socket_bind_attempt_count = 0`.
- `socket_connect_attempt_count = 0`.
- `localhost_or_127_attempt_count = 0`.
- `kg_file_open_calls = [authorized target only]`.
- `ai_kg_access_attempt_count = 0`.
- `kg_directory_scan_attempt_count = 0`.
- `output_job_export_write_attempt_count = 0`.

Returned route/runtime flags confirmed:

- No generation route call.
- No export-docx route call.
- No review-apply route call.
- No generation chain.
- No export chain.
- No ZBid writeback.
- No document body write.
- No output/job/export write.
- No Ollama call.
- No external endpoint call.
- No model download or pull.
- No knowledge pack load.
- No manifest registration or registry creation.
- No RAG, evidence, scoring, prompt registry, system instruction registry, or CI connection.

## Cache Status

Before the validation, route/adapter `.pyc` cache files already existed:

- `backend/__pycache__/kg_read_only_preview_adapter.cpython-313.pyc`
- `backend/app/routers/__pycache__/kg_read_only_preview.cpython-313.pyc`

After the validation, the same route/adapter cache listing was observed. `PYTHONDONTWRITEBYTECODE=1` was used. No new route/adapter `.pyc` or `__pycache__` item was identified for this run, so no cache cleanup was performed.

## Result

KG-RUNTIME-56 route-layer no-server in-process structure-read validation passed.

The validation stopped at KG-RUNTIME-56 and did not enter KG-RUNTIME-57.
