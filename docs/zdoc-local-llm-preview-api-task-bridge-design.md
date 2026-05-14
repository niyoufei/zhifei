# ZDoc Local LLM Preview API and Task Bridge Design

## 1. Purpose

This document is a docs-only pre-design for a future ZDoc local-LLM preview API / task bridge. It does not implement code, add tests, start services, run Ollama, call external model APIs, generate documents, write `output/`, write `job/`, write `export/`, or connect any formal ZBid writeback path.

The purpose is to define the hard boundary for a possible bridge from the existing fake-only local-LLM preview helper into an API or task layer. This document must not be interpreted as approval to immediately implement an API endpoint, a task, a UI trigger, a real model transport, a generation-chain step, an export-chain step, or a ZBid writeback path.

## 2. Baseline inherited from ZDoc Step 4

ZDoc Step 4 recorded the current state after ZDoc Step 3:

- The current capability is still a fake-only helper layer.
- The fake-only helper exists in `backend/zhifei_autoplan/ollama_preview.py`.
- The deterministic tests exist in `backend/tests/test_ollama_preview.py`.
- The feature flag is `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.
- The helper is default-off.
- The helper is preview-only.
- The helper is no-write.
- The helper does not affect the formal generation chain.
- The helper does not affect the formal export chain.
- The helper does not connect to ZBid formal writeback.
- The helper does not call real Ollama.
- The helper does not call external model APIs.
- The helper does not download or pull models.
- The helper does not write `output/`, `job/`, or `export/`.
- The helper does not trigger DOCX, JSON, or Markdown formal export.

This Step 5 document only designs the future API / task bridge boundary. It does not widen the implementation scope.

## 3. Existing fake-only helper capability

The existing helper in `backend/zhifei_autoplan/ollama_preview.py` is the only local-LLM preview capability that a future bridge may call unless a later approved design explicitly changes that scope.

The helper behavior inherited by any future bridge is:

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` absent, empty, `false`, `0`, `no`, or `off` means disabled.
- Disabled behavior must take precedence over every other condition.
- Disabled behavior must not call a fake client, a model client, real Ollama, an external model API, or any network transport.
- Enabled behavior may only return deterministic fake advisory / suggestions.
- Enabled behavior must preserve `preview_only=true`.
- Enabled behavior must preserve `no_write=true`.
- Enabled behavior must preserve `affects_generation=false`.
- Enabled behavior must preserve `affects_export=false`.
- Enabled behavior must preserve the no-ZBid-writeback boundary.

The helper must remain a preview helper. It must not become a formal generation primitive, a document rewrite primitive, an export primitive, or a ZBid writeback primitive.

## 4. Proposed API / task bridge objective

A future API / task bridge, if separately authorized, should provide a manually triggered or internal-diagnostic preview bridge for the existing fake-only helper.

The bridge objective is limited to:

- Read an input summary, selected section snippet, or ZBid snapshot-style preview payload.
- Validate that the request is explicitly preview-only.
- Inherit the `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` default-off behavior.
- When disabled, return a stable disabled preview response without calling the helper.
- When enabled, call only the fake-only helper.
- Return only fake preview advisory / suggestions.
- Preserve deterministic behavior for the same input.
- Avoid fields that can be confused with formal generated document output.

The bridge must not:

- Modify正文 or section content.
- Generate a formal document.
- Write `output/`, `job/`, or `export/`.
- Trigger the formal export chain.
- Connect to ZBid formal writeback.
- Real-call Ollama.
- Call an external model/API.
- Change the existing generation flow.
- Become an automatically triggered generation step.

## 5. Non-goals

The Step 5 bridge design explicitly excludes:

- Implementing a new endpoint.
- Implementing a new task.
- Modifying `backend/zhifei_autoplan/ollama_preview.py`.
- Modifying `backend/zhifei_autoplan/zbid_snapshot_mapper.py`.
- Modifying tests.
- Adding new tests.
- Starting a backend service.
- Running pytest.
- Running Ollama or `ollama serve`.
- Calling external model/API transports.
- Downloading or pulling models.
- Generating DOCX.
- Generating formal Markdown.
- Generating formal JSON.
- Writing `output/`, `job/`, or `export/`.
- Connecting UI auto-trigger behavior.
- Connecting ZBid formal writeback.

## 6. Feature flag inheritance

Any future API / task bridge must inherit the existing feature flag:

`ZDOC_LOCAL_LLM_PREVIEW_ENABLED`

The bridge flag contract must be:

- Absent means disabled.
- Empty means disabled.
- `false`, `0`, `no`, and `off` mean disabled.
- `true`, `1`, `yes`, and `on` may enable fake preview only.
- Disabled must be checked before any helper call.
- Disabled must return a stable disabled response.
- Enabled must still be fake-only.
- Enabled must not call real Ollama.
- Enabled must not call external model/API transports.

The bridge must not introduce a second flag that silently bypasses this contract. If a later implementation needs an API-specific or task-specific flag, that flag must be documented as stricter than, and subordinate to, `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.

## 7. Preview request boundary

A future preview request may contain only data needed to produce advisory preview output. Acceptable future request inputs may include:

- A document or section identifier used only for traceability.
- A section title or section path.
- A short input summary.
- A selected section snippet.
- A ZBid snapshot-style preview payload that is read-only.
- A caller label such as `manual` or `internal_diagnostic`.

The request must not contain instructions to:

- Rewrite正文.
- Persist suggestions.
- Save formal generated output.
- Export DOCX, JSON, or Markdown.
- Create or update jobs.
- Write `output/`, `job/`, or `export/`.
- Submit data to ZBid formal writeback.
- Call real Ollama.
- Call an external model/API.
- Download or pull a model.

The bridge should reject or return stable failure for missing input, empty text, illegal fields, persistence flags, export flags, writeback flags, or generation-chain flags.

## 8. Preview response boundary

A future bridge response must be preview-only and no-write. It should be structured so that callers cannot confuse it with a formal generated document.

The response should preserve or expose:

- `status`
- `enabled`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `affects_zbid_writeback=false`
- `source="zdoc_local_llm_preview_fake"`
- advisory or suggestions
- reason or error type for disabled and failure cases

The response must not include fields that imply formal document completion, formal export success, persisted output paths, DOCX paths, Markdown paths, JSON paths, job IDs created by the bridge, or ZBid writeback confirmation.

## 9. No-write boundary

The future API / task bridge must remain no-write. That means:

- It must not modify正文.
- It must not rewrite section drafts.
- It must not persist preview suggestions into the document body.
- It must not write preview suggestions into formal generated artifacts.
- It must not write `output/`.
- It must not write `job/`.
- It must not write `export/`.
- It must not write `build/`.
- It must not create hidden side-effect files.
- It must not clean or delete untracked files.
- It must not execute `git clean`.

No-write verification must be part of any later implementation plan and deterministic test plan.

## 10. No-generation-chain boundary

The bridge must not become part of the formal generation chain.

Forbidden future behavior includes:

- Calling formal document generation from the preview endpoint or task.
- Running generation before preview.
- Running generation after preview.
- Treating preview suggestions as a required generation step.
- Persisting preview suggestions into generated正文.
- Creating or updating formal generation jobs.
- Writing formal generated Markdown.
- Writing formal generated JSON.
- Writing formal generated DOCX.

The bridge may only be manually triggered or internally triggered for diagnostics. It must not be automatically invoked by ordinary generation flows.

## 11. No-export-chain boundary

The bridge must not connect to the formal export chain.

Forbidden future behavior includes:

- Triggering DOCX export.
- Triggering JSON export.
- Triggering formal Markdown export.
- Producing export paths.
- Writing export metadata.
- Returning a response that claims export completion.
- Calling existing export helpers from the bridge.
- Treating preview advisory as exportable formal output.

The bridge response may be viewed by a caller, but it must not become a formal document export.

## 12. No-ZBid-writeback boundary

The bridge must not connect to ZBid formal writeback.

Forbidden future behavior includes:

- Submitting preview suggestions to ZBid.
- Updating ZBid records.
- Calling a ZBid writeback API.
- Returning writeback success.
- Treating a ZBid snapshot preview payload as permission to persist to ZBid.
- Modifying `backend/zhifei_autoplan/zbid_snapshot_mapper.py` without a later approved scope.

Any ZBid-related input must remain snapshot-style and read-only. The bridge may return advisory preview output derived from read-only input only.

## 13. Forbidden integration paths

The following paths are forbidden before a separate approved implementation design, guard design, deterministic test design, and ChatGPT review:

- Do not connect the formal generation chain.
- Do not connect the formal export chain.
- Do not connect any `output/`, `job/`, or `export/` write chain.
- Do not connect ZBid formal writeback.
- Do not automatically generate DOCX.
- Do not automatically generate formal Markdown.
- Do not automatically generate formal JSON.
- Do not automatically modify正文.
- Do not automatically call Ollama.
- Do not call external model/API transports.
- Do not start a backend service.
- Do not download or pull a model.
- Do not execute `ollama pull`.
- Do not connect UI auto-trigger behavior.
- Do not treat preview as a formal generation step.
- Do not treat preview as a formal export result.

## 14. Future guard requirements

Before any future API / task bridge implementation, a separate guard design must specify:

- Which API files may be modified.
- Which task files may be modified.
- Whether a new endpoint is allowed.
- Whether a new task is allowed.
- Whether `backend/zhifei_autoplan/ollama_preview.py` may be modified.
- Whether tests may be added.
- How `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is inherited.
- The disabled behavior.
- The enabled fake-only behavior.
- The no-write verification approach.
- The verification that `output/`, `job/`, and `export/` are not written.
- The verification that the generation chain is not triggered.
- The verification that the export chain is not triggered.
- The verification that ZBid formal writeback is not connected.
- The fake-only deterministic test matrix.
- Whether runtime smoke is needed at all.
- The 2号窗口 usage rule if a later separately authorized runtime smoke ever involves real Ollama.

The guard must also state that implementation-stage tests do not run real Ollama, do not start services, do not call external model/API transports, and do not download or pull models.

## 15. Future deterministic tests requirements

A later API / task bridge implementation must be preceded by deterministic fake-only tests. The minimum test matrix must cover:

1. API/task bridge default disabled.
2. Disabled bridge does not call the helper.
3. Disabled bridge does not write `output/`, `job/`, or `export/`.
4. Enabled bridge calls the fake-only helper.
5. Enabled bridge returns `preview_only=true`.
6. Enabled bridge returns `no_write=true`.
7. Enabled bridge returns `affects_generation=false`.
8. Enabled bridge returns `affects_export=false`.
9. Enabled bridge does not modify正文.
10. Enabled bridge does not trigger the generation chain.
11. Enabled bridge does not trigger the export chain.
12. Enabled bridge does not connect ZBid formal writeback.
13. Enabled bridge does not call Ollama.
14. Enabled bridge does not call external model/API transports.
15. Same input returns deterministic output.
16. Missing input returns stable failure.
17. Empty text returns stable failure.
18. Illegal fields return stable failure.
19. Tests do not real-call Ollama.
20. Tests do not start services.
21. Tests do not write `output/`, `job/`, or `export/`.

These tests must remain fake-only. They must not be used as evidence that a real model transport is available or safe.

## 16. Future service / runtime smoke requirements

No service or runtime smoke is authorized by this document.

If a future phase proposes runtime smoke, it must be separately authorized and must state:

- Whether a backend service may be started.
- Which command may be used.
- Whether real Ollama may be contacted.
- Whether 2号窗口 must be enabled.
- Which model name may be used, if any.
- That `ollama serve` is not started unless explicitly authorized.
- That `ollama pull` is not executed unless explicitly authorized.
- That no DOCX, JSON, or Markdown formal export is triggered.
- That `output/`, `job/`, and `export/` remain untouched unless a separate approved scope says otherwise.
- That ZBid formal writeback remains disconnected.

Runtime smoke must never be inferred from this Step 5 document.

## 17. Recommended next ZDoc step

The recommended next step is docs-only:

ZDoc Step 6：ZDoc local-LLM preview API / task bridge guard + deterministic tests 前置设计文档

The next step must not directly enter API implementation, task implementation, UI implementation, real model calling, generation-chain integration, export-chain integration, or ZBid writeback integration.

## 18. Closure statement

This document only records the ZDoc local-LLM preview API / task bridge pre-design boundary. It confirms that the current fake-only helper remains default-off, preview-only, and no-write. It also confirms that any future API / task bridge must remain disabled by default, manually or diagnostically triggered, fake-only, no-write, non-generating, non-exporting, non-ZBid-writeback, and disconnected from real Ollama or external model/API transports until a later explicitly authorized phase designs, tests, and reviews those boundaries.
