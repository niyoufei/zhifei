# ZDoc Local LLM Preview Endpoint UI Entry Guard and Test Design

## 1. Purpose

This document records the ZDoc Step 10 guard and deterministic test design for a future local-LLM preview endpoint / UI entry.

The current stage only designs endpoint / UI entry guards and future deterministic tests. It does not implement code, does not add or modify tests, does not run pytest, does not start services, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal document artifacts, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately implement an endpoint or UI.

## 2. Baseline inherited from ZDoc Step 9

ZDoc Step 9 completed the endpoint / UI entry design in:

```text
docs/zdoc-local-llm-preview-endpoint-ui-entry-design.md
```

The inherited baseline is:

- The current fake-only helper already exists.
- The current fake-only API / task bridge helper already exists.
- The current feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- Any future endpoint / UI entry must be default-off.
- Any future endpoint / UI entry must be manually triggered.
- Any future endpoint / UI entry must not automatically trigger the local model.
- Any future endpoint / UI entry may only call the fake-only preview bridge unless a later real-model phase is separately authorized.
- Any future endpoint / UI entry must be preview-only.
- Any future endpoint / UI entry must be no-write.
- Any future endpoint / UI entry must not modify body text.
- Any future endpoint / UI entry must not write `output/`, `job/`, or `export/`.
- Any future endpoint / UI entry must not trigger the formal generation chain.
- Any future endpoint / UI entry must not trigger the formal export chain.
- Any future endpoint / UI entry must not generate DOCX.
- Any future endpoint / UI entry must not generate formal Markdown.
- Any future endpoint / UI entry must not generate formal JSON.
- Any future endpoint / UI entry must not connect ZBid formal writeback.
- Any future endpoint / UI entry must not call real Ollama.
- Any future endpoint / UI entry must not call external model/API services.
- Any future endpoint / UI entry must not download or pull models.
- Any future endpoint / UI entry must not execute `ollama pull`.
- A future UI, if present, may only display preview advisory / suggestions.
- A future UI must not provide one-click body writeback.
- A future UI must not provide one-click formal document generation.
- A future UI must not provide one-click DOCX / JSON / Markdown export.

This Step 10 document narrows that design into guard and deterministic test requirements. It does not widen implementation scope.

## 3. Guard objective

The future guard must prove that the endpoint / UI entry is an advisory preview sidecar, not a generation, export, writeback, or model-runtime feature.

Guard objectives:

- Endpoint / UI entry must be default-off.
- Endpoint / UI entry must be manually triggered.
- Endpoint / UI entry must be preview-only.
- Endpoint / UI entry must be no-write.
- Endpoint / UI entry must only call the fake-only preview bridge unless a later real-model phase is separately authorized.
- Endpoint / UI entry must not automatically call Ollama.
- Endpoint / UI entry must not call external model/API transports.
- Endpoint / UI entry must not start services.
- Endpoint / UI entry must not modify正文.
- Endpoint / UI entry must not write `output/`, `job/`, or `export/`.
- Endpoint / UI entry must not generate DOCX.
- Endpoint / UI entry must not generate formal Markdown.
- Endpoint / UI entry must not generate formal JSON.
- Endpoint / UI entry must not trigger the generation chain.
- Endpoint / UI entry must not trigger the export chain.
- Endpoint / UI entry must not connect ZBid formal writeback.
- Endpoint / UI entry must not download or pull models.
- Endpoint / UI entry must not execute `ollama pull`.

The guard should fail closed. If a future implementation request does not name exact allowed files, exact forbidden files, feature flag inheritance, disabled behavior, enabled fake-only behavior, no-write assertions, and deterministic tests, implementation should not start.

## 4. Allowed future file scope

This document does not authorize code changes. A later implementation request must explicitly name all allowed files before any endpoint or UI code is modified.

Future implementation may only proceed if the request states whether each category is allowed:

- Specific endpoint route file or files.
- Specific endpoint schema/helper file or files.
- Specific UI file or files.
- `backend/zhifei_autoplan/ollama_preview.py`, if bridge/helper changes are authorized.
- Specific endpoint test file or files.
- Specific UI test file or files.
- Specific docs review file under `docs/`, if a post-implementation review is authorized.

Exact path naming is required. Broad instructions such as "add the local LLM endpoint" or "add the preview button" are not sufficient to modify endpoint, UI, helper, task, generation, export, job, output, or ZBid writeback paths.

## 5. Forbidden future file scope

Before explicit future authorization, the guard must reject changes to:

- Formal generation-chain files.
- Formal export-chain files.
- ZBid formal writeback files.
- Job creation, job update, or job store files.
- Output artifact writer files.
- Result bundle writer files.
- DOCX export handlers.
- Formal Markdown export handlers.
- Formal JSON export handlers.
- Section apply / reject / rollback handlers.
- Provider or main-chain LLM routing files.
- Model download or model pull scripts.
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`.
- `output/**`.
- `job/**`.
- `export/**`.
- `build/**`.
- Generated DOCX artifacts.
- Generated JSON artifacts.
- Generated Markdown artifacts.
- Unrelated cleanup or repo hygiene files.

The guard must also reject `git clean`, untracked-file cleanup, service starts, model downloads, model pulls, and any command intended to hide or remove side-effect evidence.

## 6. Feature flag inheritance

The future endpoint / UI entry must inherit the existing feature flag:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

Feature flag inheritance requirements:

- Missing flag means disabled.
- Empty flag means disabled.
- `false`, `0`, `no`, and `off` mean disabled.
- `true`, `1`, `yes`, and `on` may enable fake preview only.
- Disabled endpoint behavior must be checked before any bridge call.
- Disabled UI behavior must be checked before any preview trigger.
- Disabled behavior must not call the bridge.
- Disabled behavior must not call real Ollama.
- Disabled behavior must not call external model/API transports.
- Enabled endpoint behavior may call only the fake-only bridge.
- Enabled UI behavior may only show preview advisory / suggestions returned by the fake-only bridge.
- Enabled behavior must still be preview-only and no-write.

Any later endpoint- or UI-specific flag must be stricter than, and subordinate to, `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`. No future flag may bypass default-off behavior.

## 7. Endpoint disabled behavior contract

When disabled, the future endpoint must:

- Return a stable disabled response.
- Return `enabled=false`.
- Preserve `preview_only=true`.
- Preserve `no_write=true`.
- Preserve `affects_generation=false`.
- Preserve `affects_export=false`.
- Preserve `affects_zbid_writeback=false`.
- Not call `run_zdoc_local_llm_preview_task`.
- Not call the fake-only helper.
- Not call a model client.
- Not call real Ollama.
- Not call external model/API transports.
- Not start a service.
- Not modify正文.
- Not write `output/`, `job/`, or `export/`.
- Not create or update jobs.
- Not trigger DOCX / JSON / Markdown formal export.
- Not connect ZBid formal writeback.

Disabled must be the highest priority branch. Invalid request content must not cause bridge calls before the disabled check.

## 8. Endpoint enabled fake-only behavior contract

When enabled, the future endpoint may only call the fake-only preview bridge.

Enabled endpoint behavior must:

- Call only the fake-only bridge helper.
- Return deterministic preview advisory / suggestions.
- Preserve `preview_only=true`.
- Preserve `no_write=true`.
- Preserve `affects_generation=false`.
- Preserve `affects_export=false`.
- Preserve `affects_zbid_writeback=false`.
- Avoid formal generated-output field names.
- Avoid export path field names.
- Avoid job creation or job status field names.
- Avoid ZBid writeback result field names.
- Keep original section正文 unchanged.
- Keep request payload unchanged.
- Return stable failure for missing input.
- Return stable failure for empty text.
- Return stable failure for illegal fields.

Enabled endpoint behavior must not:

- Modify正文章节.
- Persist suggestions.
- Trigger the formal generation chain.
- Trigger the export chain.
- Connect ZBid formal writeback.
- Call real Ollama.
- Call external model/API transports.
- Start services.
- Download or pull models.
- Execute `ollama pull`.

## 9. UI disabled behavior contract

When disabled, the future UI entry must:

- Be hidden or disabled.
- Clearly avoid presenting local LLM preview as available.
- Not trigger preview.
- Not call an endpoint.
- Not call the fake-only bridge.
- Not call any model client.
- Not call real Ollama.
- Not call external model/API transports.
- Not start a service.
- Not modify正文.
- Not write `output/`, `job/`, or `export/`.
- Not trigger generation.
- Not trigger export.
- Not trigger ZBid writeback.

Disabled UI behavior must be observable in deterministic tests without starting a real service unless a later service-smoke phase is separately authorized.

## 10. UI enabled preview-only behavior contract

When enabled, the future UI entry may only expose a human-triggered preview action.

Enabled UI behavior must:

- Require an explicit manual trigger.
- Display preview advisory / suggestions only.
- Clearly label output as preview / diagnostics.
- Preserve preview-only meaning.
- Preserve no-write meaning.
- Avoid showing preview as a formal score.
- Avoid showing preview as a formal generation conclusion.
- Avoid showing preview as accepted body text.
- Avoid saving preview content to `output/`, `job/`, or `export/`.

Enabled UI behavior must not:

- Automatically trigger preview.
- Automatically call Ollama.
- Automatically write suggestions into正文.
- Provide one-click body writeback.
- Provide one-click formal document generation.
- Provide one-click DOCX / JSON / Markdown export.
- Start a formal generation task.
- Trigger formal export.
- Trigger ZBid writeback.

## 11. Manual trigger boundary

The future endpoint / UI entry must remain manual or internal-diagnostics triggered only.

The guard must reject:

- Endpoint automatic trigger.
- UI automatic trigger.
- Automatic trigger during page load.
- Automatic trigger during project load.
- Automatic trigger during section editing.
- Automatic trigger during formal generation.
- Automatic trigger during export.
- Automatic trigger during ZBid snapshot mapping.
- Background retry loops.
- Scheduled tasks.
- Hidden service calls.
- Implicit model startup.

Manual trigger metadata should be visible in preview responses when practical, but it must not imply permission to write or export.

## 12. No-write boundary

The future endpoint / UI entry must preserve strict no-write behavior.

The guard and tests must prove no writes to:

- Body sections.
- `output/`.
- `job/`.
- `export/`.
- Generated DOCX files.
- Formal Markdown files.
- Formal JSON files.
- Job records.
- Export records.
- ZBid writeback records.

Preview advisory / suggestions must remain in response/display space only.

## 13. No-generation-chain boundary

The future endpoint / UI entry must not be part of the formal generation chain.

The guard must reject:

- Calls to formal generation functions.
- Queueing generation jobs.
- Starting generation workers.
- Creating generation job IDs.
- Converting preview advisory into body text.
- Treating preview suggestions as accepted content.
- Updating generated document bundles.
- Changing existing generation behavior.

Endpoint and UI responses must preserve `affects_generation=false`.

## 14. No-export-chain boundary

The future endpoint / UI entry must not be part of the formal export chain.

The guard must reject:

- DOCX export.
- Formal Markdown export.
- Formal JSON export.
- Export job creation.
- Export manifest updates.
- Export path returns.
- Calls to export helpers.
- UI export actions from preview output.

Endpoint and UI responses must preserve `affects_export=false`.

## 15. No-ZBid-writeback boundary

The future endpoint / UI entry must not connect to ZBid formal writeback.

The guard must reject:

- ZBid apply payloads.
- ZBid writeback API calls.
- ZBid writeback result fields.
- ZBid formal apply confirmation.
- Mutation of ZBid snapshot mapper behavior.
- Changes to `backend/zhifei_autoplan/zbid_snapshot_mapper.py`.
- UI actions that imply ZBid writeback.

Endpoint and UI responses must preserve `affects_zbid_writeback=false` or an equivalent explicit no-writeback signal.

## 16. Deterministic tests matrix

This document designs future tests only. It does not add or modify test files.

The future deterministic tests matrix must cover at least:

1. Endpoint feature flag absent returns disabled.
2. Endpoint feature flag `false`, `0`, `no`, or `off` returns disabled.
3. Disabled endpoint behavior does not call the bridge.
4. Disabled endpoint behavior does not write `output/`, `job/`, or `export/`.
5. Enabled endpoint behavior calls the fake-only bridge.
6. Enabled endpoint behavior returns `preview_only=true`.
7. Enabled endpoint behavior returns `no_write=true`.
8. Enabled endpoint behavior returns `affects_generation=false`.
9. Enabled endpoint behavior returns `affects_export=false`.
10. Enabled endpoint behavior does not modify正文.
11. Enabled endpoint behavior does not trigger the generation chain.
12. Enabled endpoint behavior does not trigger the export chain.
13. Enabled endpoint behavior does not connect ZBid formal writeback.
14. Enabled endpoint behavior does not call Ollama.
15. Enabled endpoint behavior does not call external model/API transports.
16. UI disabled state does not trigger preview.
17. UI enabled state only displays preview advisory / suggestions.
18. UI behavior does not write preview output back into正文.
19. UI behavior does not trigger export.
20. UI behavior does not trigger generation.
21. Tests must not call real Ollama.
22. Tests must not start a real service unless a later service smoke is separately authorized.
23. Tests must not write `output/`, `job/`, or `export/`.
24. Existing `backend/tests/test_ollama_preview.py` must continue to pass.

Additional recommended assertions:

- Same input returns deterministic output.
- Missing input returns stable failure.
- Empty text returns stable failure.
- Illegal fields return stable failure.
- Preview response does not expose `content` as formal generated content.
- Preview response does not expose `job_id`.
- Preview response does not expose `export_path`.
- Preview response does not expose DOCX / Markdown / JSON formal artifact fields.

## 17. Runtime smoke boundary

Runtime smoke is not authorized by this document.

If a later step authorizes runtime smoke, that step must separately define:

- Whether a service may be started.
- Which endpoint path may be tested.
- Which UI page or component may be tested.
- Whether browser automation may be used.
- Whether real Ollama remains forbidden.
- Whether 2号窗口 is required.
- The exact write-surface count checks before and after smoke.
- The expected disabled fake-only output.
- The expected enabled fake-only output.
- Cleanup and evidence commands.

Runtime smoke must not be used to introduce real Ollama, external model/API calls, formal generation, formal export, model download, model pull, or ZBid writeback.

## 18. Future implementation acceptance criteria

Before any future endpoint / UI code implementation, all of the following must be true:

- ZDoc Step 10 design is committed, tagged, and pushed.
- The implementation request explicitly names allowed endpoint files.
- The implementation request explicitly names allowed UI files.
- The implementation request explicitly states whether `backend/zhifei_autoplan/ollama_preview.py` may be modified.
- The implementation request explicitly states whether endpoint tests may be added.
- The implementation request explicitly states whether UI tests may be added.
- The feature flag inheritance behavior is explicit.
- Disabled endpoint behavior is explicit.
- Disabled UI behavior is explicit.
- Enabled fake-only endpoint behavior is explicit.
- Enabled preview-only UI behavior is explicit.
- No-write verification is explicit.
- No-write verification covers `output/`, `job/`, and `export/`.
- No-generation-chain verification is explicit.
- No-export-chain verification is explicit.
- No-ZBid-formal-writeback verification is explicit.
- No-real-Ollama verification is explicit.
- Fake-only deterministic tests are defined.
- Code implementation phase does not run Ollama.
- Runtime smoke phase is separate and is the only phase where 2号窗口 may be enabled.
- Completion must wait for ChatGPT review before any next stage.

## 19. Recommended next ZDoc step

The recommended next step is:

ZDoc Step 11：ZDoc local-LLM preview endpoint / UI entry fake-only 实现 + deterministic tests

Step 11 must not directly enter real Ollama, the formal generation chain, the export chain, or ZBid writeback.

## 20. Closure statement

ZDoc Step 10 is a design-only guard and deterministic test document for a future local-LLM preview endpoint / UI entry.

It confirms that future endpoint / UI work must remain default-off, manually triggered, preview-only, no-write, fake-only unless separately authorized, and isolated from formal generation, formal export, real Ollama, external model/API services, model download/pull, and ZBid formal writeback.

This document does not authorize immediate endpoint implementation, UI implementation, test creation, service startup, real model transport, document generation, export, or writeback.
