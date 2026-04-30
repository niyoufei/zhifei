# ZDoc Ollama Provider Integration Design

## Current State

- Ollama is currently implemented only as a manual sidecar capability.
- The backend already exposes `POST /actions/ollama/preview`.
- The backend already exposes `POST /actions/ollama/review_section`.
- The frontend already provides manual buttons for local model preview and section review.
- The frontend already supports copy and in-memory Markdown/TXT download for section review results.
- Ollama is not connected to the main generation chain.

## Forbidden Scope

The current stage must not:

- Modify `LLMClient`.
- Modify `orchestrator`.
- Modify the provider main chain.
- Automatically write or rewrite generated text.
- Write job/result bundle data.
- Trigger the export chain.
- Create or update jobs.

## Future Integration Goals

- Ollama may become an optional provider.
- Ollama provider usage must be disabled by default.
- Ollama provider usage must require explicit feature flags.
- Ollama failures must automatically fall back to the existing provider path.
- Existing `provider_chain` behavior must remain unchanged unless explicitly enabled.
- Existing generation results must remain unchanged when Ollama provider mode is disabled.

## Recommended Feature Flags

- `ZDOC_OLLAMA_PROVIDER_ENABLED=1`
- `ZDOC_OLLAMA_PROVIDER_MODE=manual|fallback|provider`
- `OLLAMA_MODEL=...`
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`

## Phased Roadmap

### Phase 1: Design And Mock Tests

- Add provider integration design.
- Add mock-only tests for provider behavior.
- Do not connect Ollama to the main chain.

### Phase 2: Provider Adapter Helper

- Add an Ollama provider adapter helper.
- Keep the adapter disconnected from `LLMClient`.
- Keep the adapter disconnected from `orchestrator`.
- Use mocks only in automated tests.

### Phase 3: Optional LLMClient Provider

- Connect the adapter to `LLMClient` as an optional provider.
- Keep the provider disabled by default.
- Require `ZDOC_OLLAMA_PROVIDER_ENABLED=1`.
- Preserve existing provider-chain behavior when disabled.

### Phase 4: Small-Sample Real Generation Validation

- Run real Ollama validation only in a separate acceptance phase.
- Use small sample chapters.
- Verify fallback behavior before broader use.

### Phase 5: Partial Chapter Generation Trial

- Enter limited chapter-generation trials only after manual approval.
- Keep output comparison and rollback checks mandatory.
- Do not promote to default behavior without explicit acceptance.

## Fallback Strategy

Fallback must occur when:

- Ollama is unreachable.
- The requested model does not exist.
- The request times out.
- The response content is empty.
- The response JSON or output format is invalid.

Fallback must not interrupt the existing generation chain.

## Acceptance Test Requirements

- Mock unit tests.
- Missing-model fallback tests.
- Tests proving no job/output/export writes.
- Tests proving `provider_chain` remains unchanged when disabled.
- Default-disabled behavior tests.
- Real Ollama tests only in a separate acceptance phase.

## Non-Pollution Principles

The Ollama provider integration must not:

- Write generated text automatically.
- Overwrite chapters.
- Change job status.
- Write result bundles.
- Write `build` or `output` artifacts.
- Trigger DOCX export.
- Change default provider behavior.

## Recommended Next Step

The next safe PR should add a mock-only Ollama provider adapter helper.

That PR should not:

- Connect to `LLMClient`.
- Connect to `orchestrator`.
- Connect to the frontend.
- Call a real Ollama service in automated tests.

It should be a focused PR with its own tests and acceptance notes.
