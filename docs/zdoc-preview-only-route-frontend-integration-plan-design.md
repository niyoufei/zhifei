# ZDoc Preview-Only Route Frontend Integration Plan Design

## 1. Scope

This document designs the future frontend integration plan for `/local-trial/preview-only`.

Step 186 is docs-only. It does not modify code, tests, frontend files, existing docs, configuration, deployment scripts, backend routes, or generation chains. It does not run pytest, start backend or frontend services, run Ollama, access ports, trigger `/generate`, trigger `/export_docx`, trigger `/review/apply`, call ZBid, generate DOCX, write `output/job/export`, perform real ZDoc/ZBid integration, or enter the 50-person deployment design.

The plan below is a future implementation contract only. It is not frontend implementation authorization.

## 2. Current Baseline

The current baseline is:

- `/local-trial/preview-only` has been implemented as a backend route.
- The route runtime smoke has passed.
- `preview_packet` is readable from the route response.
- `validator_result` is readable from the route response.
- `blocked_reasons` is readable from the route response.
- The five formal chain flags remain false:
  - `formal_writeback_allowed=false`
  - `review_apply_allowed=false`
  - `docx_export_allowed=false`
  - `zbid_writeback_allowed=false`
  - `output_write_allowed=false`
- The frontend no-write UI has been repaired.
- The frontend no-write UI has passed screenshot-level visual smoke.

Remaining baseline limitation:

- The frontend has not yet been wired to call `/local-trial/preview-only`.
- No frontend-to-route integration smoke has been executed.
- No real ZDoc/ZBid integration has been executed.

## 3. Frontend Integration Goals

The future frontend integration should only call:

- `/local-trial/preview-only`

The frontend should use that response only for preview-only display.

Required display goals:

- Display preview-only metadata.
- Display `preview_packet`.
- Display `validator_result`.
- Display `blocked_reasons`.
- Display `preview-only` status.
- Display `no-write` status.
- Display that advisory content is not evidence.
- Display that preview content is not formal正文.
- Display all formal chain flags as false.

The integration must not trigger:

- Formal generation
- DOCX export
- Review/apply
- ZBid writeback
- Formal writeback
- `output/job/export` writes

## 4. Frontend State Display Design

The future frontend state area should expose the preview-only route result as a read-only status panel.

### 4.1 Preview-Only State

The page must show that the current result is `preview-only`.

Suggested display contract:

- Show a visible `preview-only` label.
- Keep the result visually separate from formal正文.
- Avoid language that implies the preview is ready for formal generation, DOCX export, review/apply, or ZBid writeback.

### 4.2 No-Write State

The page must show that the current operation is `no-write`.

Suggested display contract:

- Show a visible `no-write` label.
- State that no formal document, job artifact, export artifact, or writeback is created by this preview.
- Preserve the existing frontend no-write notice from the Step 171 UI patch.

### 4.3 Validator State

The page should display validator status as read-only.

Supported future display states:

- `accepted_preview_only`
- `blocked`
- `requires_human_review`

The UI must not convert `accepted_preview_only` into writeback permission. It only means the metadata is acceptable for preview-only display.

### 4.4 Blocked Reasons List

The page must show `blocked_reasons` as a readable list.

The list must be visible even when the route returns an accepted preview-only result, because the blocked reasons explain why preview output cannot become evidence, formal正文, DOCX export, review/apply, ZBid writeback, or formal writeback.

Expected reasons include, but are not limited to:

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

### 4.5 Evidence Boundary Notice

The page must show evidence boundary text.

Required meanings:

- AI advisory is not evidence.
- Preview advisory is not evidence.
- ZBid scoring preview is not evidence.
- Evidence must come from verifiable tender source anchors.
- Missing or unverifiable evidence must remain blocked or require human review.

### 4.6 Scoring And Tender References

The page may display tender and scoring references as read-only metadata.

Suggested display contract:

- `tender_file_refs` are references, not automatic evidence.
- `scoring_clause_refs` must point to verifiable scoring clauses.
- `evidence_anchor_refs` must point to verifiable source anchors.
- Do not let the UI imply that a preview advisory creates evidence.

### 4.7 Formal Chain Flags

The page must display the five formal chain flags as false:

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

If any of these flags is ever true, the frontend must treat the result as a hard stop state and must not proceed with display as an accepted local trial preview.

## 5. Prohibited Behavior

Future frontend integration must not:

- Call `/generate`
- Call `/export_docx`
- Call `/review/apply`
- Call ZBid API / DB / writeback
- Trigger formal writeback
- Write `output/job/export`
- Generate DOCX
- Treat advisory as evidence
- Treat preview as formal正文
- Treat `accepted_preview_only` as writeback permission
- Hide `blocked_reasons`
- Hide the no-write boundary
- Hide the preview-only boundary

The integration must remain a metadata-only, preview-only, no-write UI path.

## 6. Future Code Implementation Scope

This section lists possible future code areas. It does not authorize code changes in Step 186.

Potential future frontend change areas:

- Frontend page state area for preview-only result display.
- A preview-only request button or control that calls only `/local-trial/preview-only`.
- A `blocked_reasons` display component.
- A validator result display component.
- A read-only `preview_packet` metadata display component.
- A read-only formal chain flags display section.
- Existing no-write and formal-export-not-open notices from the Step 171 frontend UI patch.

Future implementation must not touch:

- Backend formal generation chain
- DOCX export chain
- Review/apply chain
- ZBid writeback chain
- Formal writeback chain
- `output/job/export`
- Deployment scripts
- Runtime configuration
- 50-person deployment design

## 7. Acceptance Criteria

Future frontend integration can be accepted only if all of the following are true:

- The frontend can display the `/local-trial/preview-only` response.
- `preview_packet` is readable in the UI.
- `validator_result` is readable in the UI.
- `blocked_reasons` is readable in the UI.
- `preview-only` is visible.
- `no-write` is visible.
- Advisory-not-evidence boundary is visible.
- Preview-not-formal正文 boundary is visible.
- `tender_file_refs`, `scoring_clause_refs`, and `evidence_anchor_refs` are shown only as read-only references.
- The five formal chain flags are visible and false:
  - `formal_writeback_allowed=false`
  - `review_apply_allowed=false`
  - `docx_export_allowed=false`
  - `zbid_writeback_allowed=false`
  - `output_write_allowed=false`
- The page does not trigger `/generate`.
- The page does not trigger `/export_docx`.
- The page does not trigger `/review/apply`.
- The page does not trigger ZBid writeback.
- The page does not generate DOCX.
- The page does not write `output/job/export`.
- The page does not present preview output as formal正文.
- The page does not present advisory output as evidence.

## 8. Risk Notes

Key risks to control in later steps:

- A preview-only request button could be mistaken for a formal generation button.
- A readable validator result could be mistaken for writeback approval.
- A preview advisory could be mistaken for evidence.
- Tender and scoring references could be displayed without enough boundary text.
- The UI could accidentally reintroduce a path to `/generate` or `/export_docx`.

The implementation should keep the existing no-write UI contract visible and should fail closed if route response flags do not match the expected false values.

## 9. Recommended Next Step

Recommended next step:

ZDoc Step 187: preview-only route frontend integration plan fake schema tests.

Step 187 should be tests-only. It should not modify frontend code, start services, run Ollama, access ports, call ZBid, trigger formal routes, generate DOCX, write `output/job/export`, perform real ZDoc/ZBid integration, or enter the 50-person deployment design.

## 10. Safety Conclusion

Step 186 only designs the future frontend integration plan for `/local-trial/preview-only`.

The route is available and has passed backend runtime smoke, but the frontend has not yet been integrated with it. The future frontend path must remain preview-only, no-write, metadata-only, and blocked from formal generation, DOCX export, review/apply, ZBid writeback, formal writeback, and `output/job/export` writes.
