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

## LLMClient optional Ollama provider real validation

- Validation target: `LLMClient(provider="ollama")`.
- Current capability: `OllamaProvider` is wired into `LLMClient` as an explicit optional provider.
- Default state: disabled by default and controlled by `ZDOC_OLLAMA_PROVIDER_ENABLED=1`.
- Validation prerequisite: Ollama `/api/tags` returned HTTP `200`.
- Validation prerequisite: the model list included `qwen3:0.6b`.
- Success scenario: `ZDOC_OLLAMA_PROVIDER_ENABLED=1`.
- Success scenario: `provider=ollama`.
- Success scenario: `model=qwen3:0.6b`.
- Success scenario: `ok=true`.
- Success scenario: returned `text` was non-empty.
- Success text summary: `本地模型章节复核用于确保模型在特定章节的逻辑、数据和计算过程准确无误，从而提升整体模型的可靠性与准确性。`
- Missing-model fallback scenario: `model=not-exist-model-for-validation`.
- Missing-model fallback scenario: `ok=false`.
- Missing-model fallback scenario: `text=""`.
- Missing-model fallback scenario: `error=ollama_error:HTTPError`.
- Missing-model fallback scenario: no crash occurred.
- Main-chain isolation: `run_autoplan` was not triggered.
- Main-chain isolation: `create_job` was not triggered.
- Main-chain isolation: `update_job` was not triggered.
- Main-chain isolation: `_save_outputs` was not triggered.
- Main-chain isolation: `save_output_artifacts` was not triggered.
- Main-chain isolation: export/docx paths were not triggered.
- Main-chain isolation: related modules were not imported.
- Write isolation: `backend/data/autoplan/jobs` file count remained `87 -> 87`.
- Write isolation: `build` file count remained `1389 -> 1389`.
- Write isolation: `output` file count remained `0 -> 0`.
- Workspace result: `git status --short` was empty.
- Workspace result: no files were modified by validation.
- Workspace result: no `git clean` was executed.
- Workspace result: no dependencies were installed.
- Conclusion: `LLMClient(provider="ollama")` real invocation works.
- Conclusion: a missing Ollama model falls back safely.
- Conclusion: the integration is still not connected to `orchestrator`.
- Conclusion: the integration still does not change `provider_chain`.
- Conclusion: the integration still does not enter the main generation chain.

## No-write Ollama main-chain smoke validation

- Validation target: `run_autoplan(no_write=True)` main-chain smoke validation.
- Validation method: did not call `/actions/generate`.
- Validation method: did not call `/actions/generate_async`.
- Validation method: did not start ZDoc frontend or backend services.
- Validation method: called `run_autoplan()` directly.
- Ollama service: `/api/tags` returned HTTP status `200`.
- Ollama service: `qwen3:0.6b` was confirmed in the model list.
- Call configuration: `provider=ollama`.
- Call configuration: `model=qwen3:0.6b`.
- Call configuration: `base_url=http://127.0.0.1:11434`.
- Call configuration: `no_write=True`.
- Call configuration: `generate_images=False`.
- Call configuration: `auto_remediate=False`.
- Call configuration: `quality_strict=False`.
- Call configuration: `agent_parallelism=1`.
- Call configuration: `variant_parallelism=1`.
- Validation result: `run_autoplan(no_write=True)` completed.
- Validation result: no uncaught exception occurred.
- Validation result: `section_count=1`.
- Validation result: the section title was `Ollama主链烟测`.
- Validation result: `provider=ollama`.
- Validation result: `model=qwen3:0.6b`.
- Validation result: `error=null`.
- Validation result: the section content was non-empty.
- Real Ollama call confirmation: `OllamaProvider.complete` was called once.
- Real Ollama call confirmation: `base_url=http://127.0.0.1:11434`.
- Real Ollama call confirmation: `model=qwen3:0.6b`.
- Write isolation: `create_job` was not triggered.
- Write isolation: `update_job` was not triggered.
- Write isolation: `_save_outputs` was not triggered.
- Write isolation: `save_output_artifacts` was not triggered.
- Write isolation: export/docx/xlsx paths were not triggered.
- Write isolation: `save_latest_receipt` call count was `0`.
- Write isolation: `param_receipt_latest.json` size and mtime did not change.
- File count validation: `backend/data/autoplan/jobs` file count remained `87 -> 87`.
- File count validation: `build` file count remained `1389 -> 1389`.
- File count validation: `output` file count remained `0 -> 0`.
- Workspace result: `git status --short` was empty.
- Workspace result: there were no tracked modifications.
- Workspace result: no commit was created during validation.
- Workspace result: no PR was created during validation.
- Workspace result: no `git clean` was executed.
- Conclusion: Ollama can enter the main-chain smoke path under `no_write=True` protection.
- Conclusion: `/actions/generate_async` should still not be opened directly for Ollama main-chain validation.
- Conclusion: the next step should first design an API-level no-write smoke endpoint or manually confirm write-back boundaries.
