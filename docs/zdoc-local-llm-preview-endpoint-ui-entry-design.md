# ZDoc Local LLM Preview Endpoint and UI Entry Design

## 1. Purpose

This document records the ZDoc Step 9 endpoint / UI entry design boundary for local LLM preview.

The current stage only designs a possible endpoint and UI entry. It does not implement endpoint code, UI code, service registration, generation-chain integration, export-chain integration, real Ollama calls, external model calls, or ZBid writeback.

This document must not be interpreted as permission to immediately implement an endpoint or UI entry.

## 2. Baseline inherited from ZDoc Step 8

ZDoc Step 8 closed the fake-only API / task bridge stage review.

The inherited baseline is:

- The fake-only helper already exists in `backend/zhifei_autoplan/ollama_preview.py`.
- The fake-only API / task bridge helper already exists.
- The active feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- The current helper and bridge remain default-off.
- The current helper and bridge remain preview-only.
- The current helper and bridge remain no-write.
- The current helper and bridge do not affect the formal generation chain.
- The current helper and bridge do not affect the formal export chain.
- The current helper and bridge do not connect to ZBid formal writeback.
- The current capability is still helper-level and bridge-level only.
- No real endpoint is registered.
- No UI entry is connected.
- No real Ollama call is connected.
- No external model/API call is connected.

## 3. Existing fake-only helper and task bridge

The existing helper and bridge provide a controlled fake-only preview path.

The expected current behavior is:

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` absent, empty, `false`, `0`, `no`, or `off` means disabled.
- Disabled behavior returns a disabled response and must not call the helper or any model client.
- Enabled behavior may call the fake-only preview helper.
- Enabled behavior returns deterministic advisory / suggestions only.
- Enabled behavior keeps `preview_only=true`.
- Enabled behavior keeps `no_write=true`.
- Enabled behavior keeps `affects_generation=false`.
- Enabled behavior keeps `affects_export=false`.
- Enabled behavior must not modify body sections.
- Enabled behavior must not write `output/`, `job/`, or `export/`.
- Enabled behavior must not trigger DOCX, formal Markdown, or formal JSON export.
- Enabled behavior must not connect to ZBid formal writeback.
- Enabled behavior must not call real Ollama.
- Enabled behavior must not call external model/API services.

## 4. Endpoint / UI entry objective

The future endpoint / UI entry objective is limited to a manual preview / diagnostics surface.

The endpoint / UI entry may only:

- Read a bounded preview request.
- Call the fake-only preview bridge when enabled.
- Return preview advisory / suggestions.
- Clearly mark all responses as preview-only and no-write.
- Support human review before any later stage decision.

The endpoint / UI entry must not change the existing generation flow.

## 5. Non-goals

The following are explicit non-goals for this stage and for any immediate follow-up implementation without separate authorization:

- No endpoint implementation in this document stage.
- No UI implementation in this document stage.
- No service startup.
- No automatic local model trigger.
- No real Ollama call.
- No external model/API call.
- No model download or pull.
- No `ollama pull`.
- No formal document generation.
- No write to `output/`.
- No write to `job/`.
- No write to `export/`.
- No DOCX generation.
- No formal Markdown generation.
- No formal JSON generation.
- No body-section modification.
- No formal generation-chain integration.
- No formal export-chain integration.
- No ZBid formal writeback.

## 6. Feature flag inheritance

Any future endpoint / UI entry must inherit the existing feature flag:

`ZDOC_LOCAL_LLM_PREVIEW_ENABLED`

The required inheritance rules are:

- Absent, empty, `false`, `0`, `no`, and `off` mean disabled.
- Disabled must be the default behavior.
- Disabled must have the highest priority.
- Disabled endpoint behavior must not call the preview bridge.
- Disabled UI behavior must not trigger preview execution.
- Enabled may only route to the fake-only preview bridge unless a later real-model phase is separately authorized.
- Enabled must still remain preview-only and no-write.

## 7. Endpoint design boundary

A future endpoint may only be a preview / diagnostics entry.

The endpoint boundary is:

- The endpoint must be default-off.
- The endpoint must return disabled when the feature flag is absent or disabled.
- The endpoint disabled path must not call the bridge.
- The endpoint enabled path may only call the fake-only bridge.
- The endpoint must not enter the formal generation chain.
- The endpoint must not write `output/`, `job/`, or `export/`.
- The endpoint must not trigger the export chain.
- The endpoint must not connect to ZBid formal writeback.
- The endpoint must not call real Ollama.
- The endpoint must not call external model/API services.
- The endpoint must not download or pull models.
- The endpoint must not execute `ollama pull`.
- The endpoint response must clearly mark `preview_only=true`.
- The endpoint response must clearly mark `no_write=true`.
- The endpoint response must clearly mark `affects_generation=false`.
- The endpoint response must clearly mark `affects_export=false`.
- The endpoint must not return field names that can be mistaken for a formal generation result.

Field names such as `final_document`, `generated_docx`, `export_path`, `job_result`, `official_markdown`, `official_json`, or `zbid_writeback_result` should be forbidden in preview responses unless a later guard document explicitly allows a safe equivalent.

## 8. UI entry design boundary

A future UI entry may only expose a human-triggered preview / diagnostics action.

The UI boundary is:

- The UI entry must be manually triggered.
- The UI entry must be hidden or disabled unless `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is enabled.
- The UI entry must not automatically trigger the local model.
- The UI entry must only call the fake-only preview bridge unless a later real-model phase is separately authorized.
- The UI may only display preview advisory / suggestions.
- The UI must clearly label the result as preview / diagnostics.
- The UI must not present preview output as a formal score.
- The UI must not present preview output as a formal generation conclusion.
- The UI must not automatically write preview suggestions back into body text.
- The UI must not provide a one-click writeback-to-body action.
- The UI must not provide a one-click formal-document generation action.
- The UI must not provide a one-click DOCX / JSON / Markdown export action.
- The UI must not start a formal generation task.
- The UI must not trigger formal export.
- The UI must not trigger ZBid writeback.
- The UI must not save preview content to `output/`, `job/`, or `export/`.

## 9. Manual trigger boundary

The endpoint / UI entry must be human-triggered or internal-diagnostics-triggered only.

The boundary is:

- No automatic execution during project load.
- No automatic execution during section editing.
- No automatic execution during formal generation.
- No automatic execution during export.
- No automatic execution during ZBid snapshot mapping.
- No background retry loop.
- No scheduled task.
- No hidden service call.
- No implicit model startup.

Any future runtime smoke must be separately authorized and must not be treated as part of this design stage.

## 10. Preview request boundary

A future preview request must be bounded and non-authoritative.

The request boundary is:

- It may include a section snippet, summary, or diagnostic input.
- It may include metadata needed to identify the preview context.
- It must not include instructions to modify body text.
- It must not include instructions to write formal output files.
- It must not include export targets.
- It must not include ZBid writeback targets.
- It must not include real model transport configuration unless a later real-model phase is separately authorized.
- Missing input must return a stable failure.
- Empty text must return a stable failure.
- Invalid fields must return a stable failure.

## 11. Preview response boundary

A future preview response must remain advisory and deterministic.

The response boundary is:

- It must include `preview_only=true`.
- It must include `no_write=true`.
- It must include `affects_generation=false`.
- It must include `affects_export=false`.
- It should include a source value that identifies fake-only preview behavior.
- It may include advisory text or suggestions.
- It may include stable failure metadata.
- It must not include formal document content fields.
- It must not include export file paths.
- It must not include job output paths.
- It must not include ZBid writeback results.
- It must not imply that a formal generation result has been produced.

## 12. No-write boundary

The endpoint / UI entry must preserve a strict no-write boundary.

The endpoint / UI entry must not:

- Modify body sections.
- Write `output/`.
- Write `job/`.
- Write `export/`.
- Create DOCX files.
- Create formal Markdown files.
- Create formal JSON files.
- Persist preview content as a formal artifact.
- Save preview content into a generation job.
- Save preview content into an export record.
- Save preview content into a ZBid writeback record.

## 13. No-generation-chain boundary

The endpoint / UI entry must not be part of the formal generation chain.

It must not:

- Start a generation task.
- Call formal document-generation code.
- Queue a formal generation job.
- Convert advisory suggestions into body text.
- Treat preview suggestions as accepted content.
- Update any generated document bundle.
- Change existing generation behavior.

## 14. No-export-chain boundary

The endpoint / UI entry must not be part of the formal export chain.

It must not:

- Trigger DOCX export.
- Trigger formal Markdown export.
- Trigger formal JSON export.
- Create an export record.
- Return an export path.
- Update an export manifest.
- Call export helpers indirectly through generation-chain code.

## 15. No-ZBid-writeback boundary

The endpoint / UI entry must not connect to ZBid formal writeback.

It must not:

- Apply preview suggestions to ZBid.
- Call a ZBid formal writeback API.
- Create a ZBid writeback payload.
- Return a ZBid writeback result.
- Mutate ZBid snapshot mapper behavior.
- Modify `backend/zhifei_autoplan/zbid_snapshot_mapper.py`.

Any future ZBid-related preview use must remain snapshot preview or diagnostics only unless a later writeback phase is separately authorized.

## 16. Future guard requirements

Before any endpoint / UI implementation, a separate guard + deterministic tests design must define:

- Which endpoint files may be added or modified.
- Which UI files may be added or modified.
- Whether `backend/zhifei_autoplan/ollama_preview.py` may be modified.
- Whether endpoint tests may be added.
- Whether UI tests may be added.
- The inherited feature flag behavior.
- The disabled behavior.
- The enabled fake-only behavior.
- The no-write verification method.
- The verification that `output/`, `job/`, and `export/` are not written.
- The verification that the generation chain is not triggered.
- The verification that the export chain is not triggered.
- The verification that ZBid formal writeback is not connected.
- The verification that real Ollama is not called.
- The verification that external model/API services are not called.
- The fake-only deterministic tests.
- Whether runtime smoke is needed.
- The 2号窗口 usage rule for any later real Ollama stage.

## 17. Future deterministic tests requirements

Future tests must be fake-only unless a later runtime-smoke stage is separately authorized.

The minimum future deterministic tests matrix is:

1. Endpoint feature flag absent returns disabled.
2. Endpoint feature flag `false`, `0`, `no`, or `off` returns disabled.
3. Disabled endpoint behavior does not call the bridge.
4. Disabled endpoint behavior does not write `output/`, `job/`, or `export/`.
5. Enabled endpoint behavior calls the fake-only bridge.
6. Enabled endpoint behavior returns `preview_only=true`.
7. Enabled endpoint behavior returns `no_write=true`.
8. Enabled endpoint behavior returns `affects_generation=false`.
9. Enabled endpoint behavior returns `affects_export=false`.
10. Enabled endpoint behavior does not modify body text.
11. Enabled endpoint behavior does not trigger the generation chain.
12. Enabled endpoint behavior does not trigger the export chain.
13. Enabled endpoint behavior does not connect to ZBid formal writeback.
14. Enabled endpoint behavior does not call Ollama.
15. Enabled endpoint behavior does not call external model/API services.
16. UI disabled state does not trigger preview.
17. UI enabled state only displays preview advisory / suggestions.
18. UI behavior does not write preview output back into body text.
19. UI behavior does not trigger export.
20. Tests must not call real Ollama.
21. Tests must not start a real service unless a later service smoke is separately authorized.
22. Tests must not write `output/`, `job/`, or `export/`.
23. Existing `backend/tests/test_ollama_preview.py` must continue to pass.

The tests must also preserve deterministic behavior for same input, missing input, empty text, and invalid fields.

## 18. Future runtime smoke requirements

Runtime smoke is not authorized by this document.

If a later step authorizes runtime smoke, that step must separately define:

- The exact endpoint or UI path to smoke.
- Whether a service may be started.
- Whether a browser or UI runner may be used.
- Whether real Ollama remains forbidden.
- Whether 2号窗口 is required.
- The maximum allowed write surface.
- The exact cleanup and verification commands.
- The expected disabled and enabled fake-only outputs.

Runtime smoke must not be used to sneak in real Ollama, external model/API calls, formal generation, formal export, or ZBid writeback.

## 19. Recommended next ZDoc step

The recommended next step is docs-only:

ZDoc Step 10：ZDoc local-LLM preview endpoint / UI entry guard + deterministic tests 前置设计文档

The next step must not directly enter endpoint / UI code implementation.

## 20. Closure statement

ZDoc Step 9 is a design-only boundary document for future local LLM preview endpoint / UI entry work.

It confirms that any future endpoint / UI entry must remain default-off, manually triggered, preview-only, no-write, fake-only unless separately authorized, and isolated from formal generation, formal export, real Ollama, external model/API services, model downloads, and ZBid formal writeback.

This document does not authorize immediate endpoint implementation, UI implementation, real model transport, service startup, document generation, export, or writeback.
