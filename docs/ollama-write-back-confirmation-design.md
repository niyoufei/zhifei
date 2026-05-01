# Ollama Write-Back Confirmation Design

## Current State

ZDoc has completed the controlled Ollama path up to no-write main-chain smoke validation:

- Manual sidecar preview and section review endpoints are available.
- Frontend manual preview and section-review controls are available.
- `OllamaProvider` exists as an adapter and is available through `LLMClient(provider="ollama")` behind `ZDOC_OLLAMA_PROVIDER_ENABLED=1`.
- `run_autoplan()` supports `no_write` / `preview_only` for protected main-chain smoke validation.
- A default-off manual no-write main-chain smoke endpoint exists for API-level validation.

The current system still does not allow Ollama to:

- Write generated section text into formal sections.
- Create or update jobs.
- Write result bundles.
- Write `build` or `output` artifacts.
- Trigger DOCX/XLSX export.

## Write-Back Target

The first write-back target must be a draft area only.

- No-write Ollama results may enter a draft section.
- Draft content must not directly overwrite the formal section.
- Draft content must not automatically update the formal result bundle.
- Draft content must not directly trigger DOCX/XLSX export.
- Formal content remains unchanged until a human explicitly applies the draft.

## Manual Confirmation Boundary

Write-back must require explicit human confirmation.

- The confirmer should be the current authenticated operator or the local user who triggered the action.
- Suggested action name: `Confirm Ollama draft write-back`.
- Suggested button label: `确认写入草稿区`.
- Before confirmation, the UI or API response must show the original content, draft content, and diff preview.
- After confirmation, the draft is written to a draft-only storage area, not to the formal section body.
- Applying a draft to formal content should require a second confirmation.
- Every confirmation should record operator, timestamp, provider, model, prompt hash, and source section.

## Draft Area Design

The draft area should model each candidate change as a separate draft record.

- `draft_section`: proposed Ollama-generated content.
- `original_section`: immutable source content captured at draft creation time.
- `diff_preview`: computed comparison between original and draft.
- `apply`: promote the draft into formal content after explicit confirmation.
- `reject`: mark the draft as rejected without changing formal content.
- `rollback`: restore the previous applied version.

Drafts must not affect formal sections until a human applies them.

## Job And Result Bundle Boundary

The default behavior must avoid formal job and result writes.

- Do not update job status by default.
- Do not write result bundles by default.
- Do not rewrite generated artifacts by default.
- If future write-back is allowed, it must be controlled by a separate feature flag.
- Any allowed write must produce an audit record.

## Export Boundary

Draft content must remain isolated from export.

- Draft creation must not trigger export.
- Applying a draft must not automatically trigger export.
- DOCX/XLSX export must remain a separate user action.
- Before export, the user must confirm whether the export uses formal content or draft content.
- Export code must not silently prefer drafts.

## Rollback Mechanism

Rollback must be available before any broader write-back rollout.

- Keep original content.
- Keep draft content.
- Keep the applied version.
- Support undo to the previous version.
- Support a pre-export consistency check.
- Preserve enough metadata to explain which version is currently active.

## Audit Record

Every confirm/apply/reject/rollback action should emit an audit record with:

- `model`
- `provider`
- `base_url`
- `prompt_hash`
- `section_title`
- `original_hash`
- `draft_hash`
- `confirmed_by`
- `confirmed_at`
- `action_type`

Optional fields can include project identifier, request identifier, diff hash, and validation summary.

## Feature Flags

Suggested feature flags:

- `ZDOC_OLLAMA_WRITE_BACK_ENABLED=1`
- `ZDOC_OLLAMA_WRITE_BACK_MODE=draft_only|apply_with_confirm`

Defaults:

- Write-back is disabled.
- Draft-only mode is the first allowed mode.
- Apply-with-confirm mode must be a later explicit rollout.

## Forbidden Scope

The write-back phase must not:

- Directly connect Ollama to `/actions/generate_async`.
- Automatically overwrite sections.
- Automatically export DOCX/XLSX.
- Write without audit records.
- Let failures affect the existing generation chain.
- Change default provider behavior.
- Change `provider_chain` behavior by default.

## Phased Roadmap

### Phase 1: Design

- Define manual confirmation boundaries.
- Define draft-only behavior.
- Define audit and rollback requirements.

### Phase 2: Draft Data Structure Mock Tests

- Add pure helper/data-structure tests.
- Do not connect to frontend.
- Do not write formal result bundles.
- Do not trigger export.

### Phase 3: Default-Off Draft-Only API

- Add a backend draft-only API behind `ZDOC_OLLAMA_WRITE_BACK_ENABLED=1`.
- Keep the API disabled by default.
- Store only draft records.
- Avoid job/result/export writes unless explicitly designed and tested.

### Phase 4: Frontend Diff Preview

- Show original content, draft content, and diff preview.
- Allow manual reject.
- Keep apply disabled until Phase 5.

### Phase 5: Manual Apply

- Allow formal apply only after explicit confirmation.
- Require audit record creation.
- Preserve rollback state.

### Phase 6: Export-Time Content Selection

- Require the user to choose formal or draft/applied content before export.
- Keep export as an explicit separate action.
- Run pre-export checks before generating DOCX/XLSX.

## Recommended Next Step

The next safe PR should add draft-only data structures and mock tests.

That PR should:

- Avoid frontend changes.
- Avoid formal result bundle writes.
- Avoid job updates.
- Avoid export triggers.
- Avoid real Ollama calls.
- Focus only on draft/original/diff/apply/reject/rollback state transitions in memory or isolated helpers.
