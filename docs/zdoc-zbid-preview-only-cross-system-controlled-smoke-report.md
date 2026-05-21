# ZDoc-ZBid Preview-Only Cross-System Controlled Smoke Report

## 1. Scope

This report records Step 222: ZDoc-ZBid preview-only cross-system controlled smoke.

The smoke was limited to:

- Starting the local ZBid receiver API service.
- Temporarily enabling ZDoc outbound adapter preview-only network-send.
- Sending one preview-only payload from ZDoc outbound adapter to ZBid receiver API.
- Verifying preview-only / no-write / no-evidence response fields.
- Verifying five no-write / no-formal-chain flags remain false.
- Confirming both repositories remained clean except for this ZDoc smoke report.

This smoke did not modify code, tests, frontend files, existing docs, configuration files, deployment scripts, databases, model files, cache files, or runtime output directories.

## 2. Repository Preflight

ZDoc preflight:

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `0c25ca2e3a1e8c52990a98512b44b4f82c9c4015`
- `git status --short` before smoke: empty

ZBid preflight:

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- Start HEAD: `378355755372e03ac4f4064af59b287054984c25`
- `git status --short` before smoke: empty

Both repositories matched the authorized branch, HEAD, and clean-worktree requirements before service startup.

## 3. Output Isolation Snapshot

ZDoc output snapshot command:

```bash
find output job export -maxdepth 2 -type f 2>/dev/null | sort
```

ZDoc result:

- Before smoke: empty
- After outbound adapter call: empty

ZBid output snapshot command:

```bash
find output job export -maxdepth 2 -type f 2>/dev/null | sort
```

ZBid result:

- Before smoke: empty
- After receiver API call: empty

No file was written under `output/job/export` in either repository.

## 4. ZBid Service Startup

ZBid receiver service startup command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18763
```

Startup result:

- Service address: `127.0.0.1:18763`
- Service PID: `57633`
- Startup result: successful
- Uvicorn reported the service running on `http://127.0.0.1:18763`

No ZDoc service was started.

## 5. ZDoc Outbound Adapter Invocation

ZDoc outbound adapter was invoked from the ZDoc repository using temporary process-scoped environment variables:

```bash
PYTHONDONTWRITEBYTECODE=1
ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true
ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true
ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18763/local-llm/zdoc-preview-only/receive
```

The invocation imported ZDoc preview packet, validator, and outbound adapter helper functions directly. It did not call any ZDoc HTTP endpoint.

The outbound adapter result:

- `ok=true`
- `outbound_status=sent_preview_only`
- `network_send_attempted=true`
- `network_send_succeeded=true`
- Endpoint: `http://127.0.0.1:18763/local-llm/zdoc-preview-only/receive`

## 6. Endpoint Call List

The only endpoint called during the cross-system smoke was:

```text
POST http://127.0.0.1:18763/local-llm/zdoc-preview-only/receive
```

The smoke did not call:

- `/local-trial/preview-only`
- `/generate`
- `/export_docx`
- `/review/apply`
- any other ZDoc endpoint
- any other ZBid endpoint
- any external API

## 7. Receiver Runtime Result

ZBid receiver endpoint result:

- HTTP status: `200`
- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `status=accepted_preview_only`
- `receiver_accepted=true`

Readable fields:

- `preview_packet`: readable
- `validator_result`: readable
- `blocked_reasons`: readable

The returned `blocked_reasons` were:

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

## 8. Five False Flags Verification

The receiver response returned all five no-write / no-formal-chain flags as false:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

The adapter result also preserved the corresponding no-write state.

## 9. No Evidence / No Writeback Verification

The receiver response reported:

- `produces_evidence=false`
- `produces_writeback=false`
- `writes_storage=false`
- `writes_scoring_basis=false`

The adapter result reported:

- `produces_evidence=false`
- `produces_writeback=false`
- `writes_storage=false`
- `writes_scoring_basis=false`
- `writes_output_job_export=false`
- `zbid_writeback_attempted=false`

No advisory, preview, shadow, patch, diff, rollback, or dry-run output was treated as evidence.

## 10. Service Shutdown

The ZBid service process started for this smoke was stopped:

- Stopped PID: `57633`
- Stop result: stopped
- Post-shutdown listener check: `127.0.0.1:18763` had no listening process

No destructive batch kill was used.

## 11. Strict Non-Occurrence Confirmation

During Step 222:

- ZDoc code was not modified.
- ZBid code was not modified.
- Tests were not modified.
- Frontend files were not modified.
- Existing docs were not modified.
- Ollama was not run.
- `/local-trial/preview-only` was not called.
- `/generate` was not triggered.
- `/export_docx` was not triggered.
- `/review/apply` was not triggered.
- ZBid writeback was not triggered.
- No DOCX was generated.
- ZDoc `output/job/export` was not written.
- ZBid `output/job/export` was not written.
- Formal generation chain was not entered.
- Formal evidence chain was not entered.
- Formal scoring chain was not entered.
- Formal export chain was not entered.
- Formal writeback chain was not entered.
- 50-person formal deployment design was not entered.
- No failed smoke finding was repaired by code changes.

## 12. End State

ZDoc end state before committing this report:

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- End HEAD before report commit: `0c25ca2e3a1e8c52990a98512b44b4f82c9c4015`
- `git status --short`: clean before report creation

ZBid end state:

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- End HEAD: `378355755372e03ac4f4064af59b287054984c25`
- `git status --short`: empty
- No commit, tag, or push was performed in the ZBid repository.

## 13. Risk Conclusion

No high-risk condition was observed in this controlled smoke.

The cross-system preview-only path was verified for one minimal payload:

- ZDoc outbound adapter sent a preview-only payload.
- ZBid receiver accepted it.
- ZBid returned HTTP 200.
- ZBid returned preview-only / no-write / no-evidence status.
- Required fields were readable.
- Five no-write / no-formal-chain flags remained false.
- No output write or DOCX generation occurred.

Remaining limitations:

- This was a controlled local smoke only.
- It does not open formal generation, evidence, scoring, DOCX export, review/apply, storage, or writeback paths.
- It does not prove production deployment readiness.
- It does not authorize any persistent configuration changes.
- It does not authorize 50-person formal deployment design.

## 14. Next Step Recommendation

Recommended next step:

Step 223: ZDoc-ZBid preview-only cross-system controlled smoke stage review.

Step 223 should be docs-only / stage-review-only. It should not start services, access ports, call endpoints, modify code, run pytest, trigger writeback, generate DOCX, write `output/job/export`, or enter formal ZDoc/ZBid integration.
