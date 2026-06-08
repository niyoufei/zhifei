# MODEL-FLEET-GOVERNANCE-041: Controlled Preview-Only Endpoint Validation Execution Record

## 1. Baseline

- Task node: `MODEL-FLEET-GOVERNANCE-041-CONTROLLED-PREVIEW-ONLY-ENDPOINT-VALIDATION-EXECUTION`
- Node type: controlled preview-only endpoint validation execution
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `9cb17c3f43c3653a79c88b38ef1b7731e069ae9f`
- Start tag at HEAD: `v0.1.601-zdoc-controlled-zdoc-service-start-gate`
- Previous node: `MODEL-FLEET-GOVERNANCE-040-CONTROLLED-ZDOC-SERVICE-START-GATE`
- Previous node status: reviewed and accepted as the current baseline

This node executes exactly one controlled HTTP request against the already-running local ZDoc preview-only / no-write endpoint.

This node does not restart ZDoc service, start a new backend service, start frontend, start worker or scheduler, run tests, run Ollama, execute any Ollama command, read real KG, read unknown `.json` bodies, trigger formal generation, trigger export, trigger write-back, write `output`, `job`, or `export`, enter real use, or enter trial.

## 2. Authorized Inputs Reviewed

Required files read:

1. `docs/zdoc-controlled-zdoc-service-start-gate-execution-record-model-fleet-governance-040.md`
2. `docs/zdoc-controlled-preview-only-endpoint-validation-preflight-and-service-start-gate-model-fleet-governance-039.md`
3. `docs/zdoc-controlled-preview-only-endpoint-authorization-gate-model-fleet-governance-038.md`
4. `backend/tests/test_local_trial_preview_only_route.py`
5. `backend/app/routers/local_trial_preview_only.py`

No other repository file was read.

No full-repository `rg` was executed.

No unknown `.json` body was read.

No `知识图谱/**`, `AI知识图谱大全/**`, `output/**`, `job/**`, or `export/**` body was read.

## 3. Pre-Execution Git State

- `git status --short`: clean
- `git rev-parse HEAD`: `9cb17c3f43c3653a79c88b38ef1b7731e069ae9f`
- `git log -1 --oneline`: `9cb17c3 docs: record controlled zdoc service start gate`
- `git tag --points-at HEAD`: `v0.1.601-zdoc-controlled-zdoc-service-start-gate`

The working tree was clean before endpoint access.

## 4. 040 Service Confirmation

040 service record confirmed:

- Service PID: `76906`
- Host: `127.0.0.1`
- Port: `8000`
- Log path: `/tmp/zdoc-service-start-model-fleet-governance-040.log`
- Endpoint status in 040: not accessed
- Trial authorization in 040: not authorized

Runtime confirmation before endpoint access:

- PID `76906` still existed.
- PID `76906` command was `/Library/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`.
- Listener was `TCP 127.0.0.1:8000 (LISTEN)`.
- No listener on `0.0.0.0` was observed.
- 040 service log showed normal Uvicorn startup only before the 041 request.

## 5. Endpoint and Payload Source

Endpoint exact method:

```text
POST
```

Endpoint exact path:

```text
/local-trial/preview-only
```

Endpoint method / path source:

1. `backend/tests/test_local_trial_preview_only_route.py` defines `ROUTE_PATH = "/local-trial/preview-only"` and calls `_client().post(ROUTE_PATH, json=_safe_payload())`.
2. `backend/app/routers/local_trial_preview_only.py` defines `LOCAL_TRIAL_PREVIEW_ONLY_PATH = "/local-trial/preview-only"` and uses `@router.post(LOCAL_TRIAL_PREVIEW_ONLY_PATH)`.
3. `docs/zdoc-controlled-preview-only-endpoint-validation-preflight-and-service-start-gate-model-fleet-governance-039.md` confirms the same route constant, route decorator, route name, and candidate endpoint path.

Payload schema source:

1. `backend/tests/test_local_trial_preview_only_route.py` function `_safe_payload`.
2. `backend/app/routers/local_trial_preview_only.py` function `_packet_payload`.

The route source also confirms the response surface includes `preview_packet`, `validator_result`, `output_post_processing`, `cleaning_applied`, `warnings`, `blocked_reasons`, preview-only/no-write flags, formal generation/export/write-back flags, write flags, and Ollama/external model flags.

## 6. Synthetic Request Summary

HTTP request tool:

```text
python3 urllib.request
```

Request count:

```text
1
```

Request URL:

```text
http://127.0.0.1:8000/local-trial/preview-only
```

Request method:

```text
POST
```

Request log path:

```text
/tmp/zdoc-preview-only-endpoint-validation-model-fleet-governance-041.log
```

Synthetic marker:

```text
SYNTHETIC_PREVIEW_ONLY_TEST_INPUT_MODEL_FLEET_GOVERNANCE_041
```

Payload keys used:

```text
advisory_quality_gate_status
document_id
evidence_anchor_refs
evidence_anchor_status
evidence_binding_status
generated_at
input_risk_level
integration_request_id
model_name
model_provider
preview_advisory_summary
preview_output_post_processing_enabled
preview_output_raw_text
preview_output_target_format
project_id
response_mode
scoring_clause_refs
section_hash
section_id
section_title
section_version
source_system
target_system
tender_file_refs
zbid_preview_mode
```

The request body used only synthetic / dummy / fake values.

The request body did not include real KG, real project materials, real tender document content, real construction organization design content, real business data, user privacy data, real paths, formal generation intent, export intent, write-back intent, `output` path, `job` path, `export` path, or trial intent.

## 7. Response Summary

HTTP status code:

```text
200
```

Top-level response fields observed:

```text
affects_export
affects_generation
affects_zbid_writeback
blocked_reasons
calls_export_docx_route
calls_external_model_api
calls_generate_route
calls_ollama
calls_review_apply_route
cleaning_applied
docx_export_allowed
downloads_models
endpoint_path
formal_writeback_allowed
metadata_only
no_evidence
no_write
ok
output_post_processing
output_write_allowed
preview_only
preview_packet
pulls_models
review_apply_allowed
route_name
triggers_export_chain
triggers_generation_chain
validator_result
warnings
writes_export
writes_job
writes_output
zbid_writeback_allowed
```

Response values:

- `ok`: `true`
- `route_name`: `local_trial_preview_only`
- `endpoint_path`: `/local-trial/preview-only`
- `preview_only`: `true`
- `no_write`: `true`
- `no_evidence`: `true`
- `metadata_only`: `true`
- `preview_packet`: present
- `validator_result`: present
- `blocked_reasons`: present
- `warnings`: present as an empty list
- `cleaning_applied`: present at top level
- `output_post_processing`: present

Observed `blocked_reasons`:

```text
preview_only_is_not_writeback_permission
preview_only_is_not_evidence
zbid_preview_scoring_is_not_evidence
```

Observed `warnings`:

```text
[]
```

Observed `output_post_processing` keys:

```text
blocked_reasons
cleaned_text
cleaning_applied
extracted_payload
post_processing_blocked
raw_text
warnings
```

`cleaned_text` was not a top-level response field in this route response. It was present in `output_post_processing.cleaned_text`:

```text
{"status":"ok","test":"SYNTHETIC_PREVIEW_ONLY_TEST_INPUT_MODEL_FLEET_GOVERNANCE_041"}
```

`extracted_payload` was not a top-level response field in this route response. It was present in `output_post_processing.extracted_payload`:

```text
{"status": "ok", "test": "SYNTHETIC_PREVIEW_ONLY_TEST_INPUT_MODEL_FLEET_GOVERNANCE_041"}
```

`post_processing_blocked` was not a top-level response field in this route response. It was present in `output_post_processing.post_processing_blocked`:

```text
false
```

## 8. Formal / Export / Write-Back Flag Verification

Observed false flags:

- `formal_writeback_allowed`: `false`
- `review_apply_allowed`: `false`
- `docx_export_allowed`: `false`
- `zbid_writeback_allowed`: `false`
- `output_write_allowed`: `false`
- `calls_generate_route`: `false`
- `calls_export_docx_route`: `false`
- `calls_review_apply_route`: `false`
- `triggers_generation_chain`: `false`
- `triggers_export_chain`: `false`
- `affects_generation`: `false`
- `affects_export`: `false`
- `affects_zbid_writeback`: `false`
- `writes_output`: `false`
- `writes_job`: `false`
- `writes_export`: `false`
- `calls_ollama`: `false`

Formal generation triggered: no.

Export triggered: no.

Write-back triggered: no.

Ollama called: no.

ZBid write-back chain called: no.

Trial entered: no.

## 9. Post-Request Runtime and Write-Surface Check

040 service after request:

- PID `76906` still existed.
- Listener remained `TCP 127.0.0.1:8000 (LISTEN)`.
- Service remained localhost only.

040 service log tail after request:

```text
INFO:     Started server process [76906]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:64724 - "POST /local-trial/preview-only HTTP/1.1" 200 OK
```

The log shows exactly the target preview-only endpoint request and does not show `/generate`, `/export_docx`, `/review/apply`, real KG endpoint access, Ollama calls, generation, export, write-back, ZBid write-back, or trial entry.

Write-surface status after request:

- `output`: absent
- `job`: absent
- `export`: absent
- `git status --short -- output job export`: clean
- Files newer than the pre-request marker under `output`, `job`, or `export`: none observed

No `output/**`, `job/**`, or `export/**` body was read.

## 10. Prohibited Actions Confirmation

- Code modified: no
- Tests run: no
- ZDoc service restarted: no
- New backend / frontend / API server started: no
- Frontend started: no
- Worker / scheduler started: no
- Ollama run: no
- Any Ollama command executed: no
- Real KG read: no
- Unknown `.json` body read: no
- `知识图谱/**` body read: no
- `AI知识图谱大全/**` body read: no
- `output/**` body read: no
- `job/**` body read: no
- `export/**` body read: no
- Formal generation triggered: no
- Export triggered: no
- Write-back triggered: no
- `output` / `job` / `export` written: no
- Real use entered: no
- Trial entered: no
- Concurrent request executed: no
- Performance test executed: no
- Image generation executed: no
- Image model called: no

## 11. Validation Result

Endpoint validation status:

```text
passed
```

No stop condition was observed.

The response remained preview-only / no-write.

The response contained the expected preview-only validation surfaces.

Formal generation, export, write-back, Ollama, ZBid write-back, `output` writes, `job` writes, `export` writes, real KG reads, real use, and trial were not observed.

## 12. Next Gate Readiness

The next node may proceed only if separately authorized as an endpoint result review / service shutdown gate.

The next node must not broaden into real KG access, formal generation, export, write-back, real use, or trial unless explicitly authorized by a later attachment.

## 13. Current Decision

`CONTROLLED PREVIEW-ONLY ENDPOINT VALIDATION PASSED / NO FORMAL GENERATION / NO EXPORT / NO WRITE-BACK / NO TRIAL AUTHORIZED`
