# ZDoc Local LLM Preview API Task Bridge Guard and Test Design

## 1. Purpose

This document is the docs-only ZDoc Step 6 design for local-LLM preview API / task bridge guards and deterministic tests.

The current stage only designs the API / task bridge guard and future deterministic tests. It does not implement code, does not add or modify tests, does not run pytest, does not start services, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal document artifacts, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

This document must not be interpreted as permission to immediately implement an API endpoint, task bridge, UI trigger, real Ollama transport, generation-chain integration, export-chain integration, or ZBid writeback integration.

## 2. Baseline inherited from ZDoc Step 5

ZDoc Step 5 completed the API / task bridge pre-design in:

```text
docs/zdoc-local-llm-preview-api-task-bridge-design.md
```

The Step 5 baseline states:

- The current fake-only helper exists in `backend/zhifei_autoplan/ollama_preview.py`.
- The current feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- The current helper is default-off.
- The current helper is preview-only.
- The current helper is no-write.
- The current helper does not affect the generation chain.
- The current helper does not affect the export chain.
- The current helper does not connect ZBid formal writeback.
- A future API / task bridge may only call the fake-only helper.
- A future API / task bridge must remain default disabled.
- A future API / task bridge must only return preview suggestions.
- A future API / task bridge must not automatically trigger.
- A future API / task bridge must only be manually triggered or internally triggered for diagnostics.
- A future API / task bridge must not write正文, `output/`, `job/`, or `export/`.
- A future API / task bridge must not trigger DOCX / JSON / Markdown formal export.
- A future API / task bridge must not call real Ollama or external model/API transports.

This Step 6 document converts that bridge boundary into future guard and deterministic test requirements. It does not widen the implementation scope.

## 3. Guard objective

The future API / task bridge guard must prove that the bridge is an advisory sidecar, not a generation or export feature.

Guard objectives:

- API / task bridge must be default-off.
- API / task bridge must be preview-only.
- API / task bridge must be no-write.
- API / task bridge must not modify正文章节.
- API / task bridge must not write `output/`.
- API / task bridge must not write `job/`.
- API / task bridge must not write `export/`.
- API / task bridge must not trigger DOCX / JSON / Markdown formal export.
- API / task bridge must not connect ZBid formal writeback.
- API / task bridge must not real-call Ollama.
- API / task bridge must not call external model/API transports.
- API / task bridge must not automatically trigger.
- API / task bridge must only be manually triggered or internally triggered for diagnostics.
- API / task bridge must only call the fake-only helper.
- API / task bridge tests must be fake-only.
- API / task bridge tests must not start services.
- API / task bridge tests must not real-call Ollama.
- API / task bridge tests must not write `output/`, `job/`, or `export/`.

The guard should fail closed. If an implementation request does not name exact allowed files, exact forbidden files, feature flag inheritance, disabled behavior, enabled fake-only behavior, and deterministic tests, implementation should not start.

## 4. Allowed future file scope

This document does not authorize code changes. A later implementation request must explicitly name allowed files before any code is modified.

Future implementation may only proceed if the request states whether each of the following is allowed:

- A specific API route file, if an endpoint is authorized.
- A specific task bridge file, if a task bridge is authorized.
- `backend/zhifei_autoplan/ollama_preview.py`, if helper changes are authorized.
- New or modified tests under `backend/tests/`, if deterministic tests are authorized.
- A specific task spec under `tasks/`, if a guard task spec is authorized.
- A specific docs review file under `docs/`, if a post-implementation review document is authorized.

Exact path naming is required. Broad instructions such as "connect local LLM to ZDoc" are not sufficient to modify API, task, helper, test, generation, export, job, output, or ZBid writeback paths.

## 5. Forbidden future file scope

Before explicit future authorization, the guard must reject changes to:

- Formal generation-chain files.
- Formal export-chain files.
- ZBid formal writeback files.
- Job creation, job update, or job store files.
- Output artifact writer files.
- Result-bundle writer files.
- UI auto-trigger files.
- `output/**`.
- `job/**`.
- `export/**`.
- `build/**`.
- Generated DOCX artifacts.
- Generated JSON artifacts.
- Generated Markdown artifacts.
- Model download or model pull scripts.
- Unrelated cleanup or repo hygiene files.

Known sensitive concepts include:

- `run_autoplan`.
- `create_job`.
- `update_job`.
- `_save_outputs`.
- `save_output_artifacts`.
- DOCX export handlers.
- JSON export handlers.
- Markdown formal export handlers.
- Section apply / reject / rollback handlers.
- Provider or main-chain LLM routing.
- ZBid formal apply or writeback paths.

The guard must also reject `git clean`, untracked-file cleanup, service starts, model downloads, model pulls, and any command intended to hide or remove side-effect evidence.

## 6. Feature flag inheritance

The future API / task bridge must inherit the existing feature flag:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

Feature flag inheritance requirements:

- Missing flag means disabled.
- Empty flag means disabled.
- `false`, `0`, `no`, and `off` mean disabled.
- `true`, `1`, `yes`, and `on` may enable fake preview only.
- Disabled behavior must be checked before any helper call.
- Disabled behavior must not call the helper.
- Disabled behavior must not call real Ollama.
- Disabled behavior must not call external model/API transports.
- Enabled behavior may call only the fake-only helper.
- Enabled behavior must still be preview-only and no-write.

Any later bridge-specific flag must be stricter than, and subordinate to, `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`. No future flag may bypass the default-off behavior.

## 7. Disabled behavior contract

When disabled, the future API / task bridge must:

- Return a stable disabled response.
- Return `enabled=false`.
- Preserve `preview_only=true`.
- Preserve `no_write=true`.
- Preserve `affects_generation=false`.
- Preserve `affects_export=false`.
- Preserve `affects_zbid_writeback=false`.
- Not call `run_zdoc_local_llm_preview`.
- Not call a fake client.
- Not call a model client.
- Not call real Ollama.
- Not call external model/API transports.
- Not modify正文.
- Not write `output/`, `job/`, or `export/`.
- Not create or update jobs.
- Not trigger DOCX / JSON / Markdown formal export.
- Not connect ZBid formal writeback.

Disabled must be the highest priority branch. Invalid request content must not cause helper calls before the disabled check.

## 8. Enabled fake-only behavior contract

When enabled, the future API / task bridge may only call the existing fake-only helper.

Enabled behavior must:

- Call only the fake-only helper in `backend/zhifei_autoplan/ollama_preview.py`.
- Return deterministic fake advisory / suggestions.
- Preserve `preview_only=true`.
- Preserve `no_write=true`.
- Preserve `affects_generation=false`.
- Preserve `affects_export=false`.
- Preserve `affects_zbid_writeback=false`.
- Avoid formal generated-output field names.
- Avoid export path field names.
- Avoid job creation or job status field names.
- Avoid ZBid writeback confirmation field names.
- Keep original section正文 unchanged.
- Keep input payload unchanged.
- Return stable failure for missing input.
- Return stable failure for empty text.
- Return stable failure for illegal fields.

Enabled behavior must not:

- Modify正文章节.
- Persist suggestions.
- Write preview suggestions into formal artifacts.
- Trigger the formal generation chain.
- Trigger the export chain.
- Connect ZBid formal writeback.
- Call real Ollama.
- Call external model/API transports.
- Start services.
- Download or pull models.
- Execute `ollama pull`.

## 9. Preview request boundary

A future API / task bridge request may only contain data needed for advisory preview.

Acceptable request concepts may include:

- A manually triggered caller label.
- An internal diagnostic caller label.
- A section title.
- A section text snippet.
- A review focus.
- A preview type.
- A read-only source context.
- A read-only ZBid snapshot-derived context.

Forbidden request concepts include:

- Formal apply.
-正文 rewrite.
- Persist preview.
- Export preview.
- Create job.
- Update job.
- Write result bundle.
- Write `output/`.
- Write `job/`.
- Write `export/`.
- Generate DOCX.
- Generate formal Markdown.
- Generate formal JSON.
- Submit to ZBid.
- Call real Ollama.
- Call external model/API.
- Pull or download models.
- Auto-trigger from UI or generation flow.

The future bridge must reject or fail stably on persistence flags, export flags, job flags, writeback flags, generation-chain flags, model-transport flags, and unknown dangerous fields.

## 10. Preview response boundary

A future API / task bridge response must be advisory-only and must not look like a formal generation result.

Required response safety semantics:

- `preview_only=true`.
- `no_write=true`.
- `affects_generation=false`.
- `affects_export=false`.
- `affects_zbid_writeback=false`.
- Stable disabled response.
- Stable failure response.
- Stable fake success response.
- Advisory or suggestions only.
- Human review required.

Forbidden response semantics:

- Formal generated正文 replacement.
- DOCX path.
- JSON export path.
- Markdown export path.
- Job ID created by the bridge.
- Result bundle path.
- Output artifact path.
- Export completion status.
- ZBid writeback ID.
- ZBid writeback success.
- Raw hidden thinking or full model trace.

Any thinking-like signal, if ever designed in a later phase, must be a bounded human-facing preview summary and must not expose raw chain-of-thought or become formal output.

## 11. No-write boundary

The future API / task bridge guard and tests must prove no-write behavior.

No-write means:

- No正文 mutation.
- No section draft mutation.
- No preview suggestion persistence.
- No formal artifact write.
- No `output/` write.
- No `job/` write.
- No `export/` write.
- No `build/` write.
- No `backend/data/autoplan/jobs` write.
- No generated DOCX.
- No generated formal Markdown.
- No generated formal JSON.
- No ZBid formal writeback.

No-write verification should include:

- File counts or path existence checks before and after tests.
- Spies or patches on job creation and update functions.
- Spies or patches on output artifact writers.
- Spies or patches on export functions.
- Spies or patches on ZBid writeback functions if such functions are in scope.
- Assertions that input section正文 remains unchanged.
- Assertions that the bridge response contains only preview fields.

## 12. No-generation-chain boundary

The future API / task bridge must not connect to the formal generation chain.

Guard checks must ensure:

- No unauthorized modification to formal generation-chain files.
- No call from bridge to `run_autoplan`.
- No generation job creation.
- No generation worker spawn.
- No generated正文 mutation.
- No preview suggestion adoption into正文.
- No automatic remediation call.
- No automatic generation-before-preview or generation-after-preview behavior.

The bridge may be manually triggered or internally triggered for diagnostics only. It must not become an ordinary generation workflow step.

## 13. No-export-chain boundary

The future API / task bridge must not connect to the export chain.

Guard checks must ensure:

- No unauthorized modification to export-chain files.
- No DOCX export call.
- No formal Markdown export call.
- No formal JSON export call.
- No export job creation.
- No export path response.
- No export metadata write.
- No result bundle export.
- No conversion of advisory preview into exportable formal output.

The response may be displayed as preview output only. It must not be treated as a formal export.

## 14. No-ZBid-writeback boundary

The future API / task bridge must not connect to ZBid formal writeback.

Guard checks must ensure:

- No unauthorized modification to `backend/zhifei_autoplan/zbid_snapshot_mapper.py`.
- No ZBid formal apply.
- No ZBid writeback endpoint call.
- No ZBid review-state mutation.
- No ZBid result adoption.
- No ZBid export or submission path.
- No response fields that claim ZBid writeback success.

ZBid-related inputs may only be read-only snapshot or snapshot-derived preview context. Snapshot context must not be treated as permission to persist or submit changes to ZBid.

## 15. Deterministic tests matrix

A later implementation must add fake-only deterministic tests before commit. This Step 6 document does not add tests.

The minimum future test matrix is:

1. API / task bridge default disabled.
2. Disabled bridge does not call the helper.
3. Disabled bridge does not write `output/`, `job/`, or `export/`.
4. Disabled bridge does not modify正文.
5. Enabled bridge calls the fake-only helper.
6. Enabled bridge returns `preview_only=true`.
7. Enabled bridge returns `no_write=true`.
8. Enabled bridge returns `affects_generation=false`.
9. Enabled bridge returns `affects_export=false`.
10. Enabled bridge does not modify正文章节.
11. Enabled bridge does not trigger the formal generation chain.
12. Enabled bridge does not trigger the export chain.
13. Enabled bridge does not connect ZBid formal writeback.
14. Enabled bridge does not call Ollama.
15. Enabled bridge does not call external model/API transports.
16. Enabled bridge does not write `output/`, `job/`, or `export/`.
17. Same input returns deterministic output.
18. Missing input returns stable failure.
19. Empty text returns stable failure.
20. Illegal fields return stable failure.
21. Tests do not real-call Ollama.
22. Tests do not start services.
23. Tests do not write `output/`, `job/`, or `export/`.
24. Tests do not generate DOCX / JSON / Markdown formal artifacts.
25. Existing `backend/tests/test_ollama_preview.py` must continue to pass.

The tests must remain fake-only. Passing fake-only tests must not be presented as proof that real Ollama transport, model availability, model response shape, model latency, or runtime stability has been validated.

## 16. Runtime smoke boundary

No runtime smoke is authorized by this document.

Implementation-stage work must not:

- Start a backend service.
- Run real Ollama.
- Run `ollama serve`.
- Execute `ollama pull`.
- Call external model/API transports.
- Download or pull models.
- Generate DOCX / JSON / Markdown formal artifacts.
- Write `output/`, `job/`, or `export/`.
- Connect ZBid formal writeback.

If a later phase proposes runtime smoke, it must be separately authorized and must define:

- Whether a backend service may be started.
- Which exact service command may be used.
- Whether real Ollama may be contacted.
- Whether 2号窗口 must be used.
- Which model name may be used.
- Whether `ollama serve` is already running and owned by 2号窗口.
- That `ollama pull` is forbidden unless separately authorized.
- That no formal generation or export is triggered.
- That no `output/`, `job/`, or `export/` write occurs unless separately authorized.
- That ZBid formal writeback remains disconnected.

Runtime smoke must never be inferred from API / task bridge implementation permission.

## 17. Future implementation acceptance criteria

Future code implementation may begin only if all of the following are true:

- ZDoc Step 6 design has been archived.
- The implementation request names exact allowed files.
- The implementation request states whether a new API endpoint is allowed.
- The implementation request states whether a new task bridge is allowed.
- The implementation request states whether `backend/zhifei_autoplan/ollama_preview.py` may be modified.
- The implementation request states whether tests may be added or modified.
- The implementation request states how `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is inherited.
- The implementation request states disabled behavior.
- The implementation request states enabled fake-only behavior.
- The implementation request states no-write verification.
- The implementation request states that `output/`, `job/`, and `export/` are not written.
- The implementation request states that the generation chain is not triggered.
- The implementation request states that the export chain is not triggered.
- The implementation request states that ZBid formal writeback is not connected.
- Fake-only deterministic tests are required.
- Existing `backend/tests/test_ollama_preview.py` remains in the relevant regression scope.
- Code implementation stage does not run Ollama.
- Code implementation stage does not start services unless separately authorized.
- Runtime smoke stage is separate from code implementation.
- 2号窗口 may be enabled only in a separately authorized runtime smoke phase.
- Completion must stop and wait for ChatGPT review.

If any acceptance criterion is missing, implementation should not proceed.

## 18. Recommended next ZDoc step

The recommended next step is:

```text
ZDoc Step 7：ZDoc local-LLM preview API / task bridge fake-only 实现 + deterministic tests
```

Step 7 must not directly enter real Ollama, generation-chain integration, export-chain integration, or ZBid writeback. It must remain fake-only unless a later explicit instruction changes the scope.

## 19. Closure statement

This document only records the ZDoc local-LLM preview API / task bridge guard and deterministic tests pre-design. It confirms that a future bridge must be default-off, preview-only, no-write, manually or diagnostically triggered, fake-only, non-generating, non-exporting, non-ZBid-writeback, disconnected from real Ollama, disconnected from external model/API transports, and covered by deterministic fake-only tests before archival.

This document does not authorize immediate API implementation, task implementation, UI work, real model calling, runtime smoke, generation-chain integration, export-chain integration, output/job/export writes, or ZBid formal writeback.
