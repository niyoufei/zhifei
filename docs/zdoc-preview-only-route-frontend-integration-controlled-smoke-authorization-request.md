# ZDoc Preview-Only Route Frontend Integration Controlled Smoke Authorization Request

## 1. Purpose

This document drafts the authorization request for a future controlled smoke of the frontend integration with:

- `/local-trial/preview-only`

The future smoke would verify whether the frontend page can request the preview-only route and render the route result without entering any formal chain.

Step 192 is docs-only / authorization-request-only. It does not authorize or execute the smoke. It does not modify code, tests, frontend files, existing docs, backend routes, configuration, deployment scripts, or runtime files. It does not run pytest, start services, access ports, run Ollama, call `/local-trial/preview-only`, trigger `/generate`, trigger `/export_docx`, trigger `/review/apply`, trigger ZBid writeback, generate DOCX, write `output/job/export`, enter real ZDoc/ZBid integration, or enter the 50-person deployment design.

This authorization request must not be treated as user authorization. A later explicit user authorization is required before Step 193 can run.

## 2. Current Baseline

The current baseline is:

- `/local-trial/preview-only` has been implemented.
- Backend runtime smoke for `/local-trial/preview-only` has passed.
- The frontend has been minimally integrated with `/local-trial/preview-only`.
- The frontend implementation uses `fetch("/local-trial/preview-only")`.
- The frontend implementation is intended to display:
  - `preview_packet`
  - `validator_result`
  - `blocked_reasons`
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- Step 191 archived that implementation.

Remaining gap:

- No controlled frontend integration smoke has been executed.
- The frontend-to-backend same-origin route or proxy behavior has not been confirmed.
- The live UI has not yet been verified against a running `/local-trial/preview-only` route.

## 3. Smoke Purpose

The future controlled smoke should verify:

- The frontend page can request `/local-trial/preview-only` in preview-only mode.
- The page can display `preview_packet`.
- The page can display `validator_result`.
- The page can display `blocked_reasons`.
- The page can display the five formal-chain false flags:
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- The same-origin route or proxy mechanism for `/local-trial/preview-only` works as expected.
- Route failures show errors and do not fallback to formal interfaces.

The smoke remains preview-only / no-write validation only.

## 4. Requested Future Authorization Scope

The future Step 193 authorization should explicitly allow only the minimum actions needed to run a controlled frontend integration smoke.

Requested future authorization items:

- Start the backend service if required for `/local-trial/preview-only`.
- Start the frontend service if required for the frontend page.
- Access the local frontend page.
- Trigger only the frontend preview-only control that calls `/local-trial/preview-only`.
- Call `/local-trial/preview-only` only through the preview-only frontend path or the minimum approved smoke request path.
- Inspect whether the page renders `preview_packet`.
- Inspect whether the page renders `validator_result`.
- Inspect whether the page renders `blocked_reasons`.
- Inspect whether the page renders the five false flags.
- Check `output/job/export` before and after smoke.
- Stop any services started for the smoke.

The future authorization must list exact service commands, local ports, endpoint paths, stop conditions, and report fields before execution.

## 5. Explicitly Not Authorized

The future controlled smoke must not authorize:

- Trigger `/generate`
- Trigger `/export_docx`
- Trigger `/review/apply`
- Trigger ZBid writeback
- Call ZBid API / DB / writeback
- Generate DOCX
- Write `output/job/export`
- Enter formal generation chain
- Enter DOCX export chain
- Enter review/apply chain
- Enter ZBid writeback chain
- Enter real ZDoc/ZBid integration
- Enter the 50-person deployment design
- Download or pull models
- Run Ollama unless separately authorized

Step 192 itself authorizes none of these actions.

## 6. Preview-Only And No-Write Boundaries

The future smoke must preserve these boundaries:

- It remains preview-only.
- It remains no-write.
- It must not create formal documents.
- It must not write `output/job/export`.
- It must not treat advisory as evidence.
- It must not treat preview as formal正文.
- It must not treat `accepted_preview_only` as writeback permission.
- It must not call any formal endpoint as a fallback when `/local-trial/preview-only` fails.

The page should visibly preserve:

- `preview-only`
- `no-write`
- `blocked_reasons`
- Advisory is not evidence
- Preview is not formal正文

## 7. Controlled Smoke Check Items

If later authorized, Step 193 should check:

- Git preflight is clean and on the expected HEAD.
- Backend service starts only if explicitly authorized.
- Frontend service starts only if explicitly authorized.
- Frontend page is reachable only on explicitly authorized local port.
- The preview-only UI control is visible.
- The preview-only UI control calls `/local-trial/preview-only`.
- The page displays `preview_packet`.
- The page displays `validator_result`.
- The page displays `blocked_reasons`.
- The page displays:
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- The same-origin or proxy path for `/local-trial/preview-only` is confirmed.
- The frontend does not call forbidden endpoints.
- `output/job/export` pre/post snapshots have no difference.
- Any started services are stopped.

## 8. Hard Stop Conditions

Future Step 193 must stop immediately if any of the following occurs:

- Git status is not clean.
- Current directory is not `/Users/youfeini/Desktop/文档生成系统`.
- Current branch is not `main`.
- HEAD does not match the Step 193 authorization requirement.
- A service starts on an unauthorized port.
- The frontend calls `/generate`.
- The frontend calls `/export_docx`.
- The frontend calls `/review/apply`.
- The frontend triggers ZBid writeback.
- ZBid API / DB / writeback is called.
- A DOCX file is generated.
- `output/job/export` is written.
- The smoke enters formal generation chain.
- The smoke enters real ZDoc/ZBid integration.
- A service cannot be stopped.
- The page fallback calls a formal interface after `/local-trial/preview-only` failure.
- Any of the five formal-chain proof flags appears true:
  - `generate_called=true`
  - `export_docx_called=true`
  - `review_apply_called=true`
  - `zbid_writeback_called=true`
  - `output_job_export_written=true`

## 9. Required Future Report Template

If Step 193 is later authorized and executed, the report should include:

- User authorization text
- Current directory
- Current branch
- Start HEAD
- End HEAD
- `git status --short` before and after
- Backend start command and PID, if started
- Frontend start command and PID, if started
- Local ports accessed
- Whether `/local-trial/preview-only` was called
- Whether the call came from the preview-only frontend path
- `preview_packet` display result
- `validator_result` display result
- `blocked_reasons` display result
- Five false flags display result
- Whether `/generate` was triggered
- Whether `/export_docx` was triggered
- Whether `/review/apply` was triggered
- Whether ZBid writeback was triggered
- Whether DOCX was generated
- Whether `output/job/export` changed
- Whether services were stopped
- Same-origin or proxy result
- Risks and limitations
- Recommended next step

## 10. User Authorization Confirmation Wording

Step 193 must not run until the user gives explicit authorization equivalent to:

“我授权执行 Step 193 preview-only route frontend integration controlled smoke，授权范围仅限 Step 192 授权请求文档列明事项；允许启动必要的后端和前端服务、访问授权本地端口，并通过前端 preview-only 路径调用 /local-trial/preview-only；不得触发 /generate、/export_docx、/review/apply、ZBid 写回，不得生成 DOCX，不得写 output/job/export，不得进入真实 ZDoc/ZBid 联调，不得进入 50 人正式部署设计。”

If the user does not provide that or equivalent explicit authorization, Step 193 must not be executed.

## 11. Recommended Next Step

Recommended next step:

ZDoc Step 193: preview-only route frontend integration controlled smoke.

Step 193 may run only after explicit user authorization. If authorization is not provided, execution must stop and no service, port access, route call, or smoke action may occur.

## 12. Safety Conclusion

Step 192 only drafts the controlled smoke authorization request. It does not run smoke, does not start services, does not access ports, does not call `/local-trial/preview-only`, does not trigger formal routes, does not call ZBid, does not generate DOCX, does not write `output/job/export`, does not enter real ZDoc/ZBid integration, and does not enter the 50-person deployment design.
