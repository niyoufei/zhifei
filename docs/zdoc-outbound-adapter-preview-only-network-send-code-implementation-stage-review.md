# ZDoc Outbound Adapter Preview-Only Network-Send Code Implementation Stage Review

## 1. Scope

This document archives Step 219: ZDoc outbound adapter preview-only network-send code implementation.

Step 219 was authorized only for ZDoc-side preview-only outbound adapter implementation and direct tests.

Authorized repository and baseline:

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `6af7cf01f193152dfc481bc6e0275cc713911e77`

Authorized file scope:

- `backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py`
- `backend/tests/test_zdoc_zbid_preview_outbound.py`

Step 219 did not authorize service startup, port access, real ZBid endpoint calls, runtime smoke, ZBid repository changes, formal generation, DOCX export, review/apply, writeback, or `output/job/export` writes.

## 2. Actual Modified Files

Step 219 modified exactly:

- `backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py`
- `backend/tests/test_zdoc_zbid_preview_outbound.py`

No frontend files, docs, deployment scripts, configuration files, formal generation files, export files, review/apply files, or output/write chains were modified.

## 3. Implementation Result

Step 219 implemented preview-only network-send support in the ZDoc outbound adapter.

Implemented behavior:

- Network-send remains default-off.
- Network-send requires explicit enablement.
- Endpoint must be configured.
- Target endpoint is limited to `POST /local-llm/zdoc-preview-only/receive`.
- Payload is restricted to:
  - `preview_packet`
  - `validator_result`
  - `blocked_reasons`
  - five no-write / no-formal-chain false flags
- Any formal-chain flag that is not false causes the adapter to refuse sending.
- Missing endpoint returns a preview-only / no-write safe state.
- Disallowed endpoint returns a blocked state before sender invocation.
- Fake sender success path returns preview-only / no-write result.
- Fake sender failure path returns preview-only / no-write error.
- Send failure does not fall back to any formal endpoint.

Explicit enablement requires:

- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- a configured receiver endpoint
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`

## 4. Endpoint Boundary

The allowed receiver path is:

```text
POST /local-llm/zdoc-preview-only/receive
```

The adapter only allows endpoints whose path resolves to that receiver path.

It does not allow sending to:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback routes
- arbitrary proxy routes
- arbitrary business endpoints

## 5. Payload Boundary

The network-send payload is limited to:

- `preview_packet`
- `validator_result`
- `blocked_reasons`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

The payload does not include:

- evidence
- DOCX
- formal scoring result
- writeback data
- storage write data
- formal business data
- source-section mutation data

## 6. Five Flags

The five no-write / no-formal-chain flags remain false:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

The adapter refuses to send if any incoming or derived formal-chain flag is not false.

## 7. Boundary Confirmation

Step 219 confirmed:

- ZBid repository was not modified.
- ZDoc formal generation chain was not modified.
- ZDoc export chain was not modified.
- ZDoc review/apply chain was not modified.
- ZDoc `output/job/export` chain was not modified.
- No evidence was sent.
- No DOCX was sent.
- No formal scoring result was sent.
- No writeback data was sent.
- No storage write was produced.
- No `output/job/export` write was produced.
- No real endpoint was called.

## 8. Verification Result

Step 219 ran the focused outbound adapter test:

```bash
python -m pytest backend/tests/test_zdoc_zbid_preview_outbound.py -vv
```

Final result:

- `15 passed in 0.04s`

Additional checks:

- `git diff --check`: passed
- `git diff --cached --check`: passed

The first test run exposed a local helper signature issue in `_non_false_formal_chain_flags`. The issue was fixed within the authorized file scope and the focused test was rerun successfully.

## 9. Strict Non-Occurrence Confirmation

During Step 219:

- No service was started.
- No port was accessed.
- Ollama was not run.
- `/local-trial/preview-only` was not called.
- No ZDoc endpoint was called.
- No ZBid endpoint was called.
- `/generate` was not triggered.
- `/export_docx` was not triggered.
- `/review/apply` was not triggered.
- ZBid writeback was not triggered.
- No DOCX was generated.
- `output/job/export` was not written.
- Real ZDoc/ZBid integration was not entered.
- 50-person formal deployment design was not entered.
- Runtime smoke was not executed.

## 10. Commit And Tag

Step 219 was committed as:

- Commit: `e54c70bad904ae986cfd9854414b1675c973d8da`
- Tag: `v0.1.272-zdoc-outbound-adapter-preview-only-network-send-code-implementation`

## 11. Risk Conclusion

Current risk conclusion:

- Step 219 only completed ZDoc outbound adapter code implementation and fake sender unit tests.
- ZDoc service has not been started.
- ZBid service has not been started.
- The real ZBid receiver endpoint has not been called.
- ZDoc -> ZBid cross-system smoke has not been executed.
- Real integration is not complete.
- No writeback chain is open.
- No evidence chain is open.
- No scoring chain is open.
- DOCX export remains closed.

## 12. Next Step Recommendation

Recommended next step:

- Step 221: ZDoc-ZBid preview-only cross-system controlled smoke authorization request.

Alternative:

- First draft a cross-system smoke design / checklist.

Any future service startup, port access, real endpoint call, cross-system integration, or writeback-related action requires separate explicit user authorization.

## 13. Safety Conclusion

Step 220 is docs-only / stage-review-only. It only archives the Step 219 implementation result.

This document does not authorize Step 221, does not modify code, does not run pytest, does not start services, does not access ports, does not call endpoints, does not run Ollama, does not write `output/job/export`, does not generate DOCX, does not trigger `/generate`, `/export_docx`, `/review/apply`, or ZBid writeback, and does not enter real ZDoc/ZBid integration or 50-person formal deployment design.
