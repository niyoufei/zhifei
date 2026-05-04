# ZDoc Formal Section Draft Write-back Governance Design

This document defines the governance boundary for any future formal write-back of section drafts. It builds on the current draft-only section draft preview and decision UI baseline at `v0.1.29-zdoc-section-draft-decision-ui-validation`.

## Current State

- ZDoc currently supports draft-only preview for section draft write-back.
- `/actions/ollama/section_draft/build` returns draft, diff, and audit data only.
- `/actions/ollama/section_draft/apply_preview` returns an applied preview only.
- `/actions/ollama/section_draft/reject` returns rejected draft state only.
- `/actions/ollama/section_draft/rollback` returns rolled-back draft state only.
- None of the current build, apply preview, reject, or rollback paths writes formal section content.
- The frontend only displays draft, diff, audit, status, and decision data.
- The current flow does not write job records, result bundles, build artifacts, output artifacts, or export artifacts.
- The current flow does not trigger DOCX, XLSX, or export paths.

## Formal Write-back Trigger Conditions

Formal write-back must remain unavailable unless all of the following conditions are true:

- A human reviewer explicitly confirms the write-back.
- The formal apply feature flag is enabled.
- An original-to-draft diff exists and is visible to the reviewer.
- At least one audit record exists for the draft.
- A second confirmation step is completed after the reviewer sees the final diff and metadata.
- The request includes the draft payload that was previously reviewed.
- The request does not rely on implicit state from the frontend session alone.

## Permission Boundary

The formal write-back path needs an explicit permission model before implementation.

- A write-back confirmer should be a named user, reviewer, or operator, not an anonymous session.
- The backend should require a `confirmed_by` value.
- The backend should set or validate a `confirmed_at` timestamp.
- The API should include a role field if the application has distinct operator, reviewer, and admin roles.
- The API should require a second-confirmation `reason` before the draft can become a persisted write-back candidate.
- The UI should display the confirmer identity, role, timestamp, and reason before any irreversible step.
- The backend should reject formal apply requests with missing identity, missing reason, missing audit trail, or disabled flags.

## Pre-write Checks

Before any formal write-back is accepted, the backend should verify and record:

- `section_title`.
- `original_hash`.
- `draft_hash`.
- `diff_preview`.
- `provider`.
- `model`.
- `base_url`.
- `prompt_hash`.
- full audit trail.
- whether the current section still matches the original hash.
- whether another draft or write-back has already modified the same section.
- whether the request conflicts with a newer version.

If the current section hash no longer matches the draft's `original_hash`, the formal write-back must stop and return a conflict status.

## Write Target Boundary

The first persisted write-back step should not update the formal result bundle.

Recommended default:

- Write only to a dedicated draft store.
- Do not directly update the formal section body.
- Do not directly update `run_result`.
- Do not directly update job status or job result.
- Do not write a formal result bundle.
- Do not write build or output artifacts.

Future options must stay separately gated:

- Persisting draft decisions to a draft store can be one phase.
- Promoting a persisted draft to a formal section can be a later phase.
- Updating job/result bundle state must be a separate design and PR.
- Writing build/output artifacts must require separate validation.

## Audit Record Requirements

Formal write-back audit records should be append-only and should include:

- `action_type`.
- `provider`.
- `model`.
- `base_url`.
- `section_title`.
- `original_hash`.
- `draft_hash`.
- `prompt_hash`.
- `confirmed_by`.
- `confirmed_at`.
- `reason`.
- `previous_version`.
- `new_version`.
- request identifier.
- feature flags active at the time of the action.
- conflict check result.

The backend must not accept formal write-back without an audit record. The UI must show the audit record before and after the write-back request.

## Rollback Mechanism

Rollback must be designed before any formal write-back touches durable state.

- Store the original content.
- Store the draft content.
- Store the applied version.
- Store the previous persisted version.
- Store the new persisted version.
- Allow rollback to the previous version.
- Treat rollback as a separate audited action.
- Require `confirmed_by`, `confirmed_at`, and `reason` for rollback.
- Do not automatically trigger export after rollback.
- Do not silently modify job/result bundle state during rollback.

Rollback should return a clear status and audit trail before any export or deliverable path can see the restored version.

## Job and Result Bundle Boundary

The default boundary is no job mutation.

- Formal write-back should not update job state by default.
- Formal write-back should not update job result by default.
- Formal write-back should not write a result bundle by default.
- If future work allows job updates, it must use a dedicated feature flag.
- Result bundle writes must be designed and implemented in a separate PR.
- Build and output writes must be validated separately.
- Any job/result mutation must include migration, rollback, and audit behavior.

Recommended future flag:

- `ZDOC_SECTION_DRAFT_JOB_UPDATE_ENABLED=1` for any job mutation, if it is ever introduced.

## Export Boundary

Formal write-back must not automatically trigger DOCX, XLSX, or export paths.

- Export must be started by a separate user action.
- Export must require the user to choose formal content or draft content.
- Export must show the selected version state before starting.
- Export must show whether content is draft-only, persisted draft, formally applied, or rolled back.
- Export must not infer version choice from the last clicked preview button.
- Export integration requires its own feature flag, PR, and validation.

## Feature Flag Recommendations

All formal write-back and persistence flags should default to disabled:

- `ZDOC_SECTION_DRAFT_APPLY_ENABLED=1` enables formal apply request handling.
- `ZDOC_SECTION_DRAFT_PERSIST_ENABLED=1` enables draft store persistence.
- `ZDOC_SECTION_DRAFT_EXPORT_ENABLED=1` enables export integration for selected draft/formal versions.

Additional future flags may be useful:

- `ZDOC_SECTION_DRAFT_JOB_UPDATE_ENABLED=1` for job mutation.
- `ZDOC_SECTION_DRAFT_RESULT_BUNDLE_ENABLED=1` for result bundle writes.

No flag should enable multiple high-risk surfaces at once.

## Phased Rollout

Phase 1: docs-only governance design.

- Define permissions, audit, rollback, persistence, job/result, and export boundaries.
- Do not modify code.

Phase 2: draft store helper, mock-only.

- Add pure helper functions for draft store data structures.
- Use deterministic tests and no filesystem writes unless explicitly mocked.
- Do not connect frontend.

Phase 3: draft persist API, default disabled.

- Add an API that persists to a draft store only when explicitly enabled.
- Keep result bundle, job, build, output, and export untouched.

Phase 4: formal apply preview with audit.

- Return the would-apply structure and audit record.
- Do not persist formal content.
- Do not update job or export.

Phase 5: formal apply with persisted draft only.

- Persist an applied draft state in the draft store.
- Do not update formal result bundle.
- Do not trigger export.

Phase 6: result bundle write design.

- Design how formal applied drafts would update result bundle state.
- Define migration, validation, rollback, and audit requirements.
- Do not implement export in the same PR.

Phase 7: export-time version selection.

- Let users choose formal content or persisted draft content before export.
- Show version and audit status before generating DOCX/XLSX.
- Keep export user-initiated.

## Forbidden Scope

Future formal write-back work must not:

- directly call `/actions/generate_async`.
- automatically overwrite section body content.
- automatically update job state.
- automatically write result bundles.
- automatically write build or output artifacts.
- automatically trigger export.
- write without an audit record.
- write without human confirmation.
- combine persistence, job update, result bundle update, and export in one PR.

## Recommended Next Step

The next smallest safe task is either:

- a draft store helper design document, or
- a mock-only draft store helper implementation with deterministic tests.

The recommended next implementation boundary is:

- no frontend connection.
- no formal result bundle writes.
- no job updates.
- no export trigger.
- default disabled.
- proof that job/build/output counts do not change.

Formal section write-back should remain deferred until draft store persistence, audit, conflict detection, and rollback behavior have been designed and validated independently.
