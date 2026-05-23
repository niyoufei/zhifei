# ZDoc-ZBid 20-user local deployment and pilot-run controlled execution report

## 1. Scope

This report records Step 245: ZDoc-ZBid 20-user local deployment and pilot-run controlled execution.

This run was limited to a local, representative pilot-run for an approximately 20-person team. It remained preview-only / no-write / no-evidence. It did not open formal generation, formal evidence, scoring-basis write, DOCX export, review/apply, ZBid writeback, real business write paths, 50-user formal deployment design, or top local model upgrade implementation.

The run used representative role payloads instead of real 20-user concurrent load testing. The goal was to verify local usability, process closure, preview-only payload flow, readable blocked reasons, logging traceability, rollback record, and human review flow.

## 2. Repository Baseline

### ZDoc

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Authorized branch: `main`
- Start HEAD: `7060507540b371a8ebc0ad425fc42d4026dd54e1`
- Execution-end HEAD before this report commit: `7060507540b371a8ebc0ad425fc42d4026dd54e1`
- Final HEAD after committing this report: recorded in the completion response.
- Pre-run `git status --short`: empty
- Post-run `git status --short` before this report file was added: empty

### ZBid

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Authorized branch: `local-llm-integration-clean`
- Start HEAD: `378355755372e03ac4f4064af59b287054984c25`
- End HEAD: `378355755372e03ac4f4064af59b287054984c25`
- Pre-run `git status --short`: empty
- Post-run `git status --short`: empty
- ZBid commit/tag/push: not performed

## 3. Pilot-run Boundary

- Pilot-run scope: approximately 20-person local deployment and pilot-run.
- Actual validation method: representative role and process validation, not formal concurrent load testing.
- Data scope: desensitized samples, test documents, and non-formal bidding artifacts.
- Allowed endpoints:
  - ZDoc preview-only route: `POST /local-trial/preview-only`
  - ZBid receiver endpoint: `POST /local-llm/zdoc-preview-only/receive`
- Forbidden endpoints and chains remained forbidden:
  - `/generate`
  - `/export_docx`
  - `/review/apply`
  - ZBid writeback
  - DOCX generation
  - `output/job/export` write
  - preview-only result as evidence
  - preview-only result as scoring basis

## 4. Services

### ZDoc service

- Start command:

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- PID: `39062`
- Port: `127.0.0.1:18766`
- Purpose: local preview-only entry support for pilot-run validation.

### ZBid service

- Start command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- PID: `39345`
- Port: `127.0.0.1:18767`
- Purpose: local preview-only receiver API support for pilot-run validation.

### Shutdown result

- ZDoc service PID `39062` was stopped after the pilot-run.
- ZBid service PID `39345` was stopped after the pilot-run.
- `127.0.0.1:18766` had no listener after shutdown.
- `127.0.0.1:18767` had no listener after shutdown.

## 5. Temporary Environment

The following environment variables were used only for this pilot-run process scope and were not written to `.env`, config files, or persistent files:

- `PYTHONDONTWRITEBYTECODE=1`
- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1`
- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`

## 6. Representative Roles

The run covered five representative role payloads under the approximately 20-person team pilot-run口径:

1. Technical writer: 技术标编制
2. Reviewer: 复核
3. Project owner: 项目负责人
4. Quality auditor: 质控审核
5. Backup integrated role: 备用综合角色

These role payloads were desensitized, local, and non-formal. They did not include real sensitive business data, DOCX artifacts, formal evidence, formal scoring results, or writeback data.

## 7. Endpoint Calls

The executed endpoint calls were limited to preview-only endpoints:

- `POST http://127.0.0.1:18766/local-trial/preview-only`
- `POST http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`

No other ZDoc or ZBid business endpoint was called.

The following endpoints were not called:

- `/generate`
- `/export_docx`
- `/review/apply`
- Any ZBid writeback endpoint
- Any unknown business endpoint

## 8. Pilot-run Result Summary

Final representative run result:

| Item | Result |
| --- | --- |
| ZDoc local preview-only route reachable | Passed |
| ZBid receiver API reachable | Passed |
| ZDoc outbound adapter sent preview-only payload to ZBid | Passed |
| Five representative role payloads returned ZDoc HTTP 200 | Passed |
| Five representative role payloads returned ZBid HTTP 200 | Passed |
| `preview_only=true` | Passed |
| `no_write=true` | Passed |
| `no_evidence=true` | Passed |
| `preview_packet` readable | Passed |
| `validator_result` readable | Passed |
| `blocked_reasons` readable | Passed |
| Five no-write / no-formal-chain flags remained false | Passed |
| DOCX generation | Not triggered |
| Formal chain | Not triggered |
| ZBid writeback | Not triggered |
| `output/job/export` write | Not observed |

Each of the five representative role payloads returned HTTP 200 through the ZDoc preview-only route and through the ZBid receiver endpoint.

## 9. Preview-only Status Verification

The returned results confirmed:

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

The readable preview-only fields were confirmed:

- `preview_packet`: readable
- `validator_result`: readable
- `blocked_reasons`: readable

## 10. No-write / No-formal-chain Flags

The five required flags remained false:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

No role payload returned a non-false formal-chain flag.

## 11. Error Prompt and Issue List

During calibration, a pilot payload with invalid preview status vocabulary did not send to ZBid. The adapter returned preview-only / no-write blocked reasons and did not fall back to any formal endpoint.

Observed calibration reasons:

- `invalid_zbid_input_status`
- `invalid_zbid_mapping_status`
- `invalid_zbid_scoring_matrix_status`

The final representative run used the existing valid preview-only status values:

- `zbid_input_status=accepted_preview_only`
- `zbid_mapping_status=mapped_preview_only`
- `zbid_scoring_matrix_status=preview_only`

Result: the final five representative role payloads all sent successfully to the ZBid receiver endpoint and returned HTTP 200.

Issue list for follow-up:

- Status vocabulary should remain visible in future pilot-run guidance so operators do not confuse informal labels with accepted preview-only status values.
- This is a guidance and process observation, not a code defect confirmed by this run.

No code was changed and no failed item was fixed in-place.

## 12. blocked_reasons Readability

The final representative payloads included readable preview-only boundary reasons, including:

- `missing_evidence_anchor`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

These reasons were readable for human review and helped confirm that preview-only data was not formal evidence, scoring basis, or writeback permission.

The receiver-side `blocked_reasons` were readable and did not indicate a formal-chain write.

## 13. Log Traceability

The local service logs showed the authorized preview-only endpoint calls:

- ZDoc: repeated `POST /local-trial/preview-only` with HTTP 200.
- ZBid: repeated `POST /local-llm/zdoc-preview-only/receive` with HTTP 200.

The logs were sufficient to verify:

- Called endpoint names
- HTTP status
- Service process shutdown

No sensitive business data was recorded in this report.

## 14. Human Review Flow

The representative pilot-run confirmed the following human review flow can be recorded:

1. Confirm the operation is preview-only / no-write / no-evidence.
2. Confirm `preview_packet`, `validator_result`, and `blocked_reasons` are readable.
3. Confirm the five formal-chain flags are all false.
4. Confirm `blocked_reasons` are treated as review prompts, not evidence or scoring basis.
5. Stop if any formal-chain flag is non-false, if any unknown endpoint is required, or if any output/write path appears.

This flow supports pilot-run review but does not authorize formal evidence, scoring-basis write, DOCX generation, review/apply, or ZBid writeback.

## 15. Rollback Record and Stop-condition Check

Rollback record:

- No code, test, frontend, existing docs, or persistent config was modified.
- Only temporary process environment variables were used.
- Services were stopped after the run.
- Ports were confirmed with no listener after shutdown.

Stop-condition check:

| Stop condition | Result |
| --- | --- |
| Any formal-chain flag non-false | Not observed |
| `output/job/export` write | Not observed |
| DOCX generation | Not observed |
| ZBid writeback | Not observed |
| Evidence write | Not observed |
| Scoring-basis write | Not observed |
| Unknown endpoint required | Not observed |
| Fallback to formal endpoint | Not observed |

## 16. output/job/export Snapshot

### ZDoc

- Before run: no `output`, `job`, or `export` file snapshot entries.
- After run: no `output`, `job`, or `export` file snapshot entries.
- Result: no new `output/job/export` write observed.

### ZBid

- Before run: no `output`, `job`, or `export` file snapshot entries.
- After run: no `output`, `job`, or `export` file snapshot entries.
- Result: no new `output/job/export` write observed.

## 17. Safety Boundary Confirmation

- Ollama was not run.
- `/generate` was not triggered.
- `/export_docx` was not triggered.
- `/review/apply` was not triggered.
- ZBid writeback was not triggered.
- DOCX was not generated.
- `output/job/export` was not written.
- Preview-only results were not treated as evidence.
- Preview-only results were not treated as scoring basis.
- No formal business data was written.
- No 50-user formal deployment design was entered.
- No top local model upgrade implementation was started.

## 18. ChatGPT Control Boundary

For this run, ChatGPT acted as the execution controller and top-level supplement only:

- It coordinated the authorized local preview-only pilot-run steps.
- It kept the run inside the no-write / no-evidence boundary.
- It did not authorize or trigger formal-chain operations.
- It did not perform model upgrade implementation.
- It did not convert preview-only output into formal evidence or scoring basis.

## 19. Risk Conclusion

This run supports the conclusion that the local preview-only ZDoc-ZBid pilot-run path is viable for representative approximately 20-person team workflow validation.

The result does not mean:

- Formal generation is open.
- Formal evidence is open.
- Scoring-basis write is open.
- DOCX export is open.
- Review/apply is open.
- ZBid writeback is open.
- Real business联调 is open.
- 50-user formal deployment design is open.
- Top local model upgrade implementation is open.

The primary observation is procedural: accepted preview-only status vocabulary should remain explicit in future operator guidance.

## 20. Next Recommendation

Recommended next step:

- Draft a Step 246 stage review for this 20-user local deployment and pilot-run controlled execution.

Any broader pilot, formal business联调, formal-chain opening, output write, DOCX generation, ZBid writeback, 50-user deployment design, or model upgrade implementation must be separately authorized.
