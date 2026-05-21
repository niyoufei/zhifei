# ZDoc-ZBid Preview-Only Cross-System Controlled Smoke Authorization Request

## 1. Purpose

This document drafts the authorization request for a future ZDoc-ZBid preview-only cross-system controlled smoke.

This document is authorization-request-only. It does not grant authorization, does not modify code, does not modify tests, does not start services, does not access ports, does not call ZDoc or ZBid endpoints, does not perform smoke testing, and does not authorize writeback.

## 2. Authorization Request Source

This request is based on the current ZDoc and ZBid preview-only baseline:

- ZDoc has implemented the `/local-trial/preview-only` backend route.
- ZDoc has implemented the frontend same-origin proxy and dynamic preview display.
- ZDoc has implemented a default-off preview-only outbound adapter.
- ZDoc outbound adapter has implemented explicitly enabled preview-only network-send.
- ZBid has implemented the preview-only receiver/helper.
- ZBid has exposed `POST /local-llm/zdoc-preview-only/receive`.
- ZBid receiver API runtime smoke has passed.
- The current remaining gap is that ZDoc -> ZBid cross-system preview-only smoke has not been executed.

The future smoke should validate only the preview-only / no-write / no-evidence path between ZDoc outbound adapter and ZBid receiver API.

## 3. Current Baseline

ZDoc baseline:

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Current HEAD: `8f3a356f6246bae6d3dfe42bdabb5ab0e5de6315`
- Current tag at HEAD: `v0.1.273-zdoc-outbound-adapter-preview-only-network-send-code-implementation-stage-review`

ZBid baseline:

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- Current stage review HEAD: `378355755372e03ac4f4064af59b287054984c25`

Known completed checks:

- ZBid receiver API controlled smoke returned HTTP 200.
- ZBid receiver response included `preview_only=true`, `no_write=true`, and `no_evidence=true`.
- ZDoc outbound adapter fake-sender unit tests passed.
- ZDoc outbound adapter remains default-off unless explicitly enabled.

## 4. Current Blocker

Before Step 219, the ZDoc outbound adapter could not actively send a payload to ZBid. Step 219 implemented the code path, but only fake-sender unit tests have been executed.

Current blocker:

- The ZDoc outbound adapter has not yet sent a real preview-only payload to a running ZBid receiver service.
- The ZBid receiver has not yet received a real request from the ZDoc outbound adapter.
- Therefore the cross-system preview-only path is not yet runtime-verified.

This authorization request is for a future controlled smoke to close that specific runtime gap.

## 5. Proposed Step 222 Smoke Scope

If the user explicitly authorizes Step 222, the future smoke may:

- Verify ZDoc repository preflight.
- Verify ZBid repository preflight.
- Start the necessary local ZBid receiver service.
- Access the local ZBid receiver port.
- Temporarily enable ZDoc preview-only outbound network-send for this smoke only.
- Configure the ZBid receiver endpoint for this smoke only.
- Send a preview-only payload from the ZDoc outbound adapter to the ZBid receiver endpoint.
- Call only the ZBid receiver endpoint:
  `POST /local-llm/zdoc-preview-only/receive`.
- Verify the ZBid response remains preview-only / no-write / no-evidence.
- Verify `preview_packet`, `validator_result`, and `blocked_reasons` are readable.
- Verify all five no-write / no-formal-chain flags remain false.
- Check output isolation on both ZDoc and ZBid sides.
- Stop all services started for the smoke.

Step 222 must not modify code, tests, docs, frontend files, configuration files, deployment scripts, databases, model files, cache files, or runtime output directories.

## 6. Temporary Enablement Conditions

The future Step 222 smoke may use temporary process-scoped environment variables such as:

```bash
ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true
ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true
ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:<ZBID_PORT>/local-llm/zdoc-preview-only/receive
```

These conditions must be temporary and scoped to the smoke process only.

The smoke must not:

- Write these values into persistent configuration.
- Modify `.env` files.
- Modify local config files.
- Modify deployment scripts.
- Enable network-send by default after the smoke.

## 7. Required Payload Boundary

The outbound payload sent from ZDoc to ZBid must be limited to:

- `preview_packet`
- `validator_result`
- `blocked_reasons`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

The payload must not include:

- formal evidence
- DOCX
- formal scoring result
- writeback data
- storage write data
- source-section mutation data
- formal business data
- shadow candidate write data
- patch, diff, rollback, or dry-run data as evidence

## 8. Required Five False Flags

The future smoke must verify these five flags:

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

If any flag is not false, the smoke must stop and report high risk.

## 9. Explicitly Forbidden Actions

The future Step 222 smoke must not:

- Trigger `/generate`.
- Trigger `/export_docx`.
- Trigger `/review/apply`.
- Trigger ZBid writeback.
- Generate DOCX.
- Write `output/job/export`.
- Run Ollama.
- Treat advisory, preview, shadow, patch, diff, rollback, or dry-run output as evidence.
- Enter formal integration.
- Enter formal generation, formal export, formal review/apply, scoring, storage, evidence, or writeback chains.
- Enter 50-person formal deployment design.
- Modify code, tests, docs, frontend files, configuration, deployment scripts, database files, model files, cache files, or runtime artifacts.
- Fix failed smoke findings during the smoke.

## 10. Success Criteria

The future Step 222 smoke succeeds only if all of the following are true:

- ZDoc preflight passes.
- ZBid preflight passes.
- ZBid receiver API is reachable.
- ZDoc outbound adapter sends a preview-only payload to the ZBid receiver endpoint.
- The only target endpoint is `POST /local-llm/zdoc-preview-only/receive`.
- ZBid returns HTTP 200.
- ZBid returns `preview_only=true`.
- ZBid returns `no_write=true`.
- ZBid returns `no_evidence=true`.
- `preview_packet` is readable.
- `validator_result` is readable.
- `blocked_reasons` is readable.
- The five no-write / no-formal-chain flags are all false.
- ZDoc `output/job/export` has no new files.
- ZBid `output/job/export` has no new files.
- No DOCX is generated.
- No formal chain is triggered.
- All services started for the smoke are stopped.
- Smoke ports have no listeners after shutdown.

## 11. Hard Stop Conditions

The future Step 222 smoke must stop immediately if any of the following occurs:

- ZDoc repository path is wrong.
- ZDoc branch is wrong.
- ZDoc start HEAD is wrong.
- ZDoc worktree is not clean.
- ZBid repository path is wrong.
- ZBid branch is wrong.
- ZBid start HEAD is wrong.
- ZBid worktree is not clean.
- ZBid receiver service cannot start with a readable error.
- ZDoc outbound adapter attempts to send to any endpoint other than `/local-llm/zdoc-preview-only/receive`.
- ZBid receiver returns non-200.
- Any no-write / no-formal-chain flag is not false.
- `/generate` is triggered.
- `/export_docx` is triggered.
- `/review/apply` is triggered.
- ZBid writeback is triggered.
- DOCX is generated.
- ZDoc or ZBid writes `output/job/export`.
- Ollama is run.
- A service started for the smoke cannot be stopped.

## 12. Proposed Step 222 Runtime Report

The future Step 222 report should record:

- User authorization text.
- ZDoc path, branch, start HEAD, end HEAD, and `git status --short`.
- ZBid path, branch, start HEAD, end HEAD, and `git status --short`.
- ZBid service startup command, PID, port, and shutdown result.
- Temporary ZDoc outbound enablement variables used.
- Exact ZBid receiver endpoint URL.
- Payload field list.
- Receiver HTTP status.
- Receiver response summary.
- `preview_packet` readability.
- `validator_result` readability.
- `blocked_reasons` readability.
- Five false flags result.
- Whether any ZDoc endpoint was called.
- Whether any forbidden endpoint or chain was triggered.
- ZDoc output snapshot before and after.
- ZBid output snapshot before and after.
- Whether DOCX was generated.
- Whether services stopped and ports were free.
- Risks and next-step recommendation.

## 13. Step 222 User Authorization Wording

Before Step 222 may be executed, the user should explicitly reply with wording equivalent to:

> 我授权执行 Step 222 ZDoc-ZBid preview-only cross-system controlled smoke。ZDoc 仓库限定为 `/Users/youfeini/Desktop/文档生成系统`，分支限定为 `main`，开始前 HEAD 必须为 `8f3a356f6246bae6d3dfe42bdabb5ab0e5de6315`；ZBid 仓库限定为 `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`，分支限定为 `local-llm-integration-clean`，开始前 HEAD 必须为 `378355755372e03ac4f4064af59b287054984c25`。允许启动必要本地服务、访问本地端口，并允许 ZDoc outbound adapter 仅向 ZBid receiver endpoint `POST /local-llm/zdoc-preview-only/receive` 发送 preview-only payload；仅限 preview-only / no-write / no-evidence 验证；不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回，不得生成 DOCX，不得写 `output/job/export`，不得运行 Ollama，不得把 advisory / preview / shadow / patch / diff / rollback / dry-run 作为 evidence，不得进入正式联调，不得进入 50 人正式部署设计。

Without the above or equivalent explicit authorization, Step 222 must not be executed.

## 14. Next Step Recommendation

Recommended next step:

Step 222: ZDoc-ZBid preview-only cross-system controlled smoke.

Step 222 must be separately authorized by the user. It must not modify code, tests, docs, configuration, or runtime files. It must not repair failed smoke findings. It must not enter formal generation, DOCX export, review/apply, scoring, evidence, storage, writeback, or deployment design.

## 15. Safety Conclusion

Step 221 only drafts the future cross-system controlled smoke authorization request.

This document does not authorize Step 222, does not start services, does not access ports, does not call ZDoc or ZBid endpoints, does not run pytest, does not run Ollama, does not generate DOCX, does not write `output/job/export`, does not trigger `/generate`, `/export_docx`, `/review/apply`, or ZBid writeback, and does not enter real ZDoc/ZBid integration or 50-person formal deployment design.
