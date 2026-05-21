# ZDoc Preview-Only Route Frontend Integration Code Implementation Authorization Request

## 1. Purpose

This document drafts the authorization request for a future frontend code implementation step.

The requested future work is to connect the frontend to:

- `/local-trial/preview-only`

The future implementation would let the frontend display:

- `preview_packet`
- `validator_result`
- `blocked_reasons`
- The five formal chain flags, all false
- `preview-only` status
- `no-write` status
- Evidence boundary notices

Step 189 is docs-only / authorization-request-only. It does not grant authorization, modify code, modify tests, modify frontend files, modify existing docs, run pytest, start backend or frontend services, run Ollama, access ports, trigger formal routes, call ZBid, write `output/job/export`, enter real ZDoc/ZBid integration, or enter the 50-person deployment design.

This document is not authorization itself. A later user message must explicitly authorize Step 190 before any frontend code change can be made.

## 2. Current Baseline

The current baseline is:

- `/local-trial/preview-only` has been implemented.
- Runtime smoke for `/local-trial/preview-only` has passed.
- `preview_packet` is readable from the route result.
- `validator_result` is readable from the route result.
- `blocked_reasons` is readable from the route result.
- The five formal chain flags remain false:
  - `formal_writeback_allowed=false`
  - `review_apply_allowed=false`
  - `docx_export_allowed=false`
  - `zbid_writeback_allowed=false`
  - `output_write_allowed=false`
- Frontend no-write UI has been repaired.
- Frontend no-write UI has passed screenshot-level visual smoke.
- Frontend integration plan fake schema tests have passed.

Remaining gap:

- The frontend does not yet call `/local-trial/preview-only`.
- Frontend-to-route integration smoke has not been executed.
- Real ZDoc/ZBid integration has not been entered.

## 3. Authorization Request Summary

The future Step 190 authorization request would ask permission to modify frontend code only for the minimum integration needed to call `/local-trial/preview-only` and display its metadata-only result.

The requested scope is limited to:

- Calling `/local-trial/preview-only` from the frontend.
- Rendering `preview_packet`.
- Rendering `validator_result`.
- Rendering `blocked_reasons`.
- Rendering the five formal chain flags as false.
- Keeping the UI visibly preview-only and no-write.
- Keeping advisory/evidence boundaries visible.
- Keeping preview/formal正文 boundaries visible.

The requested scope does not include formal generation, DOCX export, review/apply, ZBid writeback, formal writeback, real ZDoc/ZBid integration, output writes, deployment work, or 50-person deployment design.

## 4. Requested Future Authorization Scope

The future Step 190 authorization should explicitly allow:

- Modify frontend page or frontend static resource files.
- Add the minimum frontend logic needed to call `/local-trial/preview-only`.
- Display metadata-only route result.
- Add or update a `blocked_reasons` display area.
- Add or update a `validator_result` display area.
- Add or update a `preview_packet` display area.
- Add or update a formal chain flags display area.
- Preserve the existing no-write UI notices.
- Preserve the existing formal-export-not-open UI state.
- Add frontend-only tests if they are directly necessary for the integration and do not start services.

The implementation should be minimal and should follow the existing frontend structure.

## 5. Explicitly Not Authorized

The future Step 190 authorization must not include:

- Trigger `/generate`
- Trigger `/export_docx`
- Generate DOCX
- Trigger `/review/apply`
- Trigger ZBid writeback
- Call ZBid API / DB / writeback
- Trigger formal writeback
- Write `output/job/export`
- Create formal documents
- Modify backend formal generation chain
- Modify DOCX export chain
- Modify review/apply chain
- Modify ZBid writeback chain
- Modify formal writeback chain
- Enter real ZDoc/ZBid integration
- Enter 50-person deployment design
- Modify deployment scripts
- Modify runtime configuration unless a later step explicitly authorizes it

## 6. Future Code Implementation Boundary

The future frontend code implementation must obey these boundaries:

- The frontend may call only `/local-trial/preview-only` for this integration.
- The frontend must not call `/generate`.
- The frontend must not call `/export_docx`.
- The frontend must not call `/review/apply`.
- The frontend must not call a ZBid writeback interface.
- The frontend must not submit a formal generation form.
- The frontend must not create a formal document.
- The frontend must not write `output/job/export`.
- The frontend must not treat advisory content as evidence.
- The frontend must not treat preview content as formal正文.
- The frontend must not treat `accepted_preview_only` as writeback permission.

The frontend result display must remain metadata-only, preview-only, and no-write.

## 7. Expected Future UI Result

If a later Step 190 is authorized and implemented, the frontend should show:

- A preview-only status label.
- A no-write status label.
- The route name or endpoint being used: `/local-trial/preview-only`.
- A readable `preview_packet` block or summary.
- A readable `validator_result` block or summary.
- A readable `blocked_reasons` list.
- A formal chain flags section showing:
  - `formal_writeback_allowed=false`
  - `review_apply_allowed=false`
  - `docx_export_allowed=false`
  - `zbid_writeback_allowed=false`
  - `output_write_allowed=false`
- Evidence boundary text:
  - AI advisory is not evidence.
  - Preview advisory is not evidence.
  - ZBid scoring preview is not evidence.
  - Evidence must come from verifiable source anchors.
- Preview boundary text:
  - Preview is not formal正文.
  - Preview is not writeback permission.
  - Accepted preview-only status does not open formal chains.

## 8. Future Validation Boundary

If Step 190 is later authorized, validation should remain narrow.

Allowed future validation may include:

- Static or unit-level frontend checks that do not start services.
- Existing fake schema tests relevant to preview-only frontend integration.
- Source checks confirming the frontend does not call forbidden endpoints.

Runtime frontend integration smoke should remain a separate later authorization step if it requires starting backend/frontend services or accessing local ports.

## 9. Hard Stop Conditions For Future Implementation

Future Step 190 must stop if any of the following occurs:

- The workspace is not clean at the required preflight.
- The current directory or branch is not the authorized one.
- The implementation requires backend formal chain changes.
- The implementation requires DOCX export chain changes.
- The implementation requires review/apply chain changes.
- The implementation requires ZBid writeback chain changes.
- The frontend would call `/generate`.
- The frontend would call `/export_docx`.
- The frontend would call `/review/apply`.
- The frontend would call ZBid API / DB / writeback.
- The frontend would write `output/job/export`.
- The frontend would present preview output as formal正文.
- The frontend would present advisory output as evidence.
- The frontend would hide `blocked_reasons`.
- Any formal chain flag is displayed or treated as true.

## 10. User Authorization Confirmation Wording

Future Step 190 must not run until the user gives an explicit authorization equivalent to:

“我授权执行 Step 190 preview-only route frontend integration code implementation，授权范围仅限 Step 189 授权请求文档列明事项；允许修改前端代码接入 /local-trial/preview-only 并展示 preview_packet、validator_result、blocked_reasons 和五个正式链 false flags；不得触发 /generate、/export_docx、/review/apply、ZBid 写回，不得生成 DOCX，不得写 output/job/export，不得进入 50 人正式部署设计。”

If the user does not provide that or an equivalent explicit authorization, Step 190 must not be executed.

## 11. Recommended Next Step

Recommended next step:

ZDoc Step 190: preview-only route frontend integration code implementation.

Step 190 must require explicit user authorization before any code change. If authorization is not provided, the process must stop and no frontend implementation work may begin.

## 12. Safety Conclusion

Step 189 only drafts the authorization request for a future frontend integration implementation. It does not authorize implementation, does not modify frontend code, does not run tests or services, does not access ports, does not trigger formal routes, does not call ZBid, does not write `output/job/export`, does not enter real ZDoc/ZBid integration, and does not enter the 50-person deployment design.
