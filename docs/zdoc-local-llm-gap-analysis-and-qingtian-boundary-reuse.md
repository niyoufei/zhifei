# ZDoc Local LLM Gap Analysis and Qingtian Preview Boundary Reuse

## 1. Purpose

This document is a docs-only Step 1 analysis for ZDoc local-LLM integration. It only analyzes the gap between the current ZDoc baseline and the already verified Qingtian preview boundaries. It does not implement code, does not add tests, does not start services, does not call Ollama, does not call the network, and does not authorize immediate local-LLM code integration.

The current stage is limited to ZDoc integration gap analysis. This document must not be interpreted as permission to modify ZDoc generation, export, job, output, or ZBid write-back paths.

## 2. Current ZDoc Baseline

Observed baseline for this Step 1:

- Working directory: `/Users/youfeini/Desktop/文档生成系统`
- Current branch: `main`
- Starting HEAD: `ecd017057da59b2d9782c065810ec641365915dd`
- Current stable baseline tag: `v0.1.47-local-llm-five-systems-integration-roadmap`
- Current task type: docs-only single-step design

The current `main` baseline already records that ZDoc is one of the five local systems planned for local-LLM adoption. The baseline does not authorize immediate production integration.

Current hard boundaries:

- Do not modify the ZDoc generation chain.
- Do not write `output/`, `job/`, `export/`, `build/`, or result bundles.
- Do not run formal document generation.
- Do not trigger DOCX, JSON, or Markdown formal export.
- Do not connect to real Ollama in this step.
- Do not start any service.
- Do not call external networks.
- Do not connect ZBid formal write-back.

## 3. Existing Local LLM / Ollama / ZBid Assets

The read-only scan found local LLM, Ollama, and ZBid foundations in the current ZDoc repository.

Confirmed assets:

- `backend/zhifei_autoplan/ollama_preview.py` exists.
- `backend/zhifei_autoplan/zbid_snapshot_mapper.py` exists.
- `backend/tests/` exists and contains Ollama preview, section review, provider-adapter, ZBid mapper, and ZBid API bridge tests.
- `tasks/` exists and contains `tasks/zbid_snapshot_mock_api_bridge_guard.json`.
- `docs/` contains local-LLM, Ollama preview, ZBid snapshot mapper, and ZBid mock API bridge design/review documents.

Read-only facts from `backend/zhifei_autoplan/ollama_preview.py`:

- The preview helper is default-off through `ZDOC_OLLAMA_PREVIEW_ENABLED`.
- It has a manual preview path using Ollama-compatible `/api/chat`.
- It returns fallback responses instead of affecting the main generation flow when disabled, empty, timed out, or failed.
- `run_ollama_section_review` exists and wraps preview output as `review_type=section_review`.
- The prompt boundary says the model may provide review suggestions but must not rewrite the original section.

Read-only facts from `backend/zhifei_autoplan/zbid_snapshot_mapper.py`:

- The mapper is a pure mock-only mapper from ZBid input snapshots to ZDoc draft-only input.
- Its required safety flags include `draft_only=True`, `allow_formal_apply=False`, `allow_export=False`, `allow_job_write=False`, `allow_result_bundle_write=False`, and `allow_ollama=False`.
- Its output safety boundary includes `no_write=True` and `requires_human_review=True`.
- It rejects forbidden keys including `formal_apply`, `apply`, `export`, `generate_async`, `job`, `result_bundle`, `build_output`, `ollama`, and `llm`.

Read-only facts from tests and task spec:

- Existing tests use fake transports and mocks to prove disabled/default-off behavior and no-write behavior.
- Existing API bridge tests patch `run_autoplan`, job creation/update, result-bundle writes, output artifact writes, section-draft apply/reject/rollback, `LLMClient`, and export functions to prove they are not called.
- Existing tests compare `backend/data/autoplan/jobs`, `build`, and `output` file counts before and after selected preview flows.
- Existing guard task spec marks service start, Ollama commands, generation, export, job/result-bundle writes, build/output writes, formal apply, and `git clean` as risky paths.

Path-level scan also found `backend/zhifei_autoplan/providers/ollama_provider.py`, which suggests a local model provider adapter exists. This Step 1 does not certify that adapter as safe for production use; it only records that ZDoc has local-model-related assets that must be reviewed under a future guard design before any implementation step.

## 4. Qingtian Preview Boundary Summary

Qingtian has already validated boundaries that are reusable as design constraints for ZDoc, not as direct code to copy in this step.

Reusable Qingtian boundaries:

- `default-off`: local-model or preview-related behavior is disabled unless explicitly enabled.
- `preview-only`: model output is sidecar preview content, not production output.
- `no-write`: preview paths must not write result files, jobs, exports, generated artifacts, or business state.
- `affects_score=false` equivalent semantics: preview output must not affect scoring, review decisions, formal generated content, acceptance status, or downstream result bundles.
- Fake-only tests must come before any runtime smoke.
- Runtime smoke must be separately authorized.
- Thinking preview may only be retained as a controlled preview summary, not as full raw model output or hidden chain material.
- Runtime smoke must stay local/loopback-only when authorized.
- If real Ollama is later authorized, the 2号窗口 / dedicated `ollama serve` ownership rule must be explicit and must not be assumed by Codex.

For ZDoc, the direct equivalent of `affects_score=false` is:

- no change to generated sections;
- no change to formal review/apply state;
- no change to job/result bundle;
- no change to export artifacts;
- no change to ZBid formal write-back state;
- preview result is advisory only and requires human review.

## 5. Reusable Boundary Rules for ZDoc

ZDoc local-LLM work should reuse the Qingtian boundary model as ZDoc-specific rules:

1. Default-off first.
2. Manual trigger only.
3. Preview-only result shape.
4. No write to `backend/data/autoplan/jobs`, `build`, `output`, `job`, `export`, or result bundles.
5. No formal generation-chain call.
6. No export-chain call.
7. No ZBid formal write-back.
8. No UI automatic trigger.
9. No external network call.
10. No model download or pull.
11. Fake-only tests before real runtime smoke.
12. Runtime smoke only after separate authorization.
13. Thinking output only as a bounded preview summary.
14. Human review remains required before any adoption of suggestions.

These rules apply even when an existing helper already has partial default-off or no-write behavior. Existing assets are not enough; future implementation must prove the full boundary under an explicit guard.

## 6. ZDoc Gap Analysis

### 6.1 Ollama Preview File

ZDoc already has `backend/zhifei_autoplan/ollama_preview.py`. It provides a manual preview helper and section review helper. This is a strong starting point for a preview-only local-LLM path.

Gap:

- The helper exists, but this Step 1 does not alter it.
- Future work needs a dedicated preview guard design that states allowed files, feature flags, return schema, no-write checks, and fake-only tests.

### 6.2 Local Model Calling Wrapper

ZDoc has local-model-related evidence through `ollama_preview.py`, tests, and a path-level match for `backend/zhifei_autoplan/providers/ollama_provider.py`.

Gap:

- The current safe entry point should not be the provider or main chain.
- The provider/main-chain relationship must remain outside Step 1.
- A future design must decide whether `backend/zhifei_autoplan/ollama_preview.py` is the only allowed implementation file or whether provider-layer code may be touched.

### 6.3 ZBid Snapshot Mapper

ZDoc has `backend/zhifei_autoplan/zbid_snapshot_mapper.py`. It already enforces draft-only, no-write, no-export, no-job, no-result-bundle, no-Ollama safety flags.

Gap:

- The mapper is safe as a mock-only draft-input mapper.
- It should not become a model-call entry point.
- Any future local-LLM flow that consumes ZBid snapshot data should use a separate preview-only layer and preserve mapper purity.

### 6.4 Mock API Bridge

ZDoc has a documented mock API bridge around:

```text
POST /actions/zbid/snapshot_draft_input/preview
ZDOC_ZBID_MOCK_API_ENABLED=1
```

The bridge has existing docs, tests, and a task guard spec.

Gap:

- The bridge is for ZBid snapshot draft-input preview, not local-LLM generation.
- It should not be upgraded into real Ollama, formal generation, export, job, or write-back behavior without a separate guarded implementation step.

### 6.5 Test Foundation

ZDoc has tests for:

- Ollama preview disabled/default-off behavior.
- Fake transport success and fallback behavior.
- Section review preview behavior.
- Main-chain no-write smoke behavior.
- ZBid snapshot mapper pure function behavior.
- ZBid snapshot API bridge disabled/enabled/invalid/forbidden-key scenarios.
- Artifact count stability for jobs/build/output in selected flows.

Gap:

- Step 1 does not add or run tests.
- Future Step 2 should design the exact fake-only tests before any code changes.
- Runtime smoke must remain separate from fake-only tests.

### 6.6 Output / Job / Export Write Chains

Read-only grep shows ZDoc has output, job, export, DOCX, result-bundle, and artifact-write surfaces in the broader backend.

Gap:

- These chains are production-sensitive and must not be touched in this local-LLM preview planning step.
- Future preview work must patch or guard these paths to prove they are not called.

### 6.7 Chains That Cannot Be Touched Now

Current forbidden chains:

- formal document generation;
- `run_autoplan`;
- job create/update;
- result-bundle writes;
- `save_output_artifacts`;
- `output/`, `job/`, `export/`, and `build/`;
- DOCX/JSON/Markdown formal export;
- formal review/apply;
- section-draft apply/reject/rollback;
- provider/main LLM chain;
- ZBid formal write-back.

### 6.8 Gap Versus Qingtian Preview Endpoint

Qingtian's validated preview boundary is explicit about preview-only/no-write behavior and guard-controlled runtime acceptance.

ZDoc has multiple preview-like assets, but the future local-LLM preview boundary still needs one consolidated contract:

- endpoint name and scope;
- feature flag;
- return schema;
- no-write proof;
- fake-only tests;
- runtime-smoke gate;
- no export/generation/write-back proof.

### 6.9 Gap Versus Qingtian Real Transport

Qingtian runtime smoke was treated as a separately authorized step with loopback-only transport and structure-only reporting.

ZDoc has historical manual Ollama validation documents and preview helpers, but this Step 1 did not call real transport. Future ZDoc real transport must be separately authorized and must state:

- model name;
- base URL;
- 2号窗口 / `ollama serve` ownership;
- no external network;
- no output persistence;
- structure-only report shape;
- stop condition on empty or invalid response.

### 6.10 Gap Versus Qingtian Thinking Preview

ZDoc's current preview helper sends `think=False` in the Ollama chat payload. That is safer than accepting hidden or verbose thinking output by default.

Gap:

- If a future model returns a `thinking` field or similar trace, ZDoc must not store full raw thinking output.
- Only a bounded, explicit, human-facing preview summary may be retained.
- Tests should prove that thinking-like fields do not enter generated document text, job state, exports, or ZBid write-back.

### 6.11 Best First ZDoc Entry Point

The best first ZDoc local-LLM entry point is:

1. Chapter review preview.
2. Pre-generation review preview.
3. ZBid snapshot preview.

The first implementation should not directly modify body text. It should only return advisory section-review preview content for human inspection.

## 7. Proposed ZDoc Preview-Only Entry Points

Recommended preview-only entry points, in order:

1. **Chapter review preview**
   - Reuse the existing section-review concept.
   - Return missing items, risks, and suggestions.
   - Do not rewrite正文.
   - Do not write job/output/export.

2. **Pre-generation review preview**
   - Inspect input or planned section requirements before formal generation.
   - Return advisory warnings only.
   - Do not call the formal generator.
   - Do not create jobs.

3. **ZBid snapshot preview**
   - Keep `zbid_snapshot_mapper.py` pure and no-write.
   - Add only a sidecar preview design later if needed.
   - Do not connect ZBid snapshot preview to Ollama or formal write-back in Step 1.

These entry points must remain default-off, manual-triggered, preview-only, no-write, and advisory.

## 8. Forbidden Integration Paths

Current Step 1 and the immediate next design step must not:

- connect to the formal document generation chain;
- write `output/`;
- write `job/`;
- write `export/`;
- write `build/`;
- create or update result bundles;
- generate DOCX;
- generate formal Markdown;
- generate formal JSON;
- modify generated正文;
- automatically call Ollama;
- connect to a real model;
- connect to ZBid formal write-back;
- connect to UI automatic trigger behavior;
- call external networks;
- download models;
- pull models;
- run `ollama serve`;
- run `ollama run`;
- start backend or frontend services;
- alter `backend/zhifei_autoplan/ollama_preview.py` in this step;
- alter `backend/zhifei_autoplan/zbid_snapshot_mapper.py` in this step;
- add or modify tests in this step.

## 9. Future Guard Requirements

Before any ZDoc code implementation, a future guard design must define:

- exactly which files may be modified;
- whether `backend/zhifei_autoplan/ollama_preview.py` may be modified;
- whether new tests may be added;
- whether a new API route or task spec may be added;
- the feature flag name;
- default-off behavior;
- manual-trigger requirement;
- preview-only response structure;
- no-write validation;
- validation that `output/`, `job/`, `export/`, `build/`, and result bundles are not written;
- validation that export chains are not triggered;
- validation that formal generation chains are not triggered;
- validation that ZBid formal write-back is not triggered;
- fake-only tests;
- runtime smoke as a separately authorized phase;
- 2号窗口 / `ollama serve` usage rules;
- stop conditions for invalid, empty, timeout, or model-missing responses;
- whether thinking-like model fields are discarded or summarized;
- final report format and artifact-count checks.

The guard should also state that existing production-sensitive chains are forbidden unless a later user request explicitly expands scope.

## 10. Future Fake-Only Test Requirements

Future fake-only tests should be designed before any implementation. They should verify:

- default-off returns a disabled response and does not call transport;
- enabled fake transport returns preview-only data;
- timeout and model-error paths return fallback data;
- empty input does not call transport;
- no call to `run_autoplan`;
- no call to `create_job` or `update_job`;
- no call to `_save_outputs`;
- no call to `save_output_artifacts`;
- no call to DOCX/JSON/Markdown export functions;
- no call to section apply/reject/rollback;
- no call to ZBid formal write-back;
- no file-count change in `backend/data/autoplan/jobs`, `build`, and `output`;
- no formal generated正文 mutation;
- no model thinking field enters generated document text or exports.

These tests must be fake-only first. They must not require Ollama, a service, a browser, a model download, or the external network.

## 11. Future Runtime Smoke Requirements

Runtime smoke is not authorized by this document. If later authorized, it must be a separate step with a separate boundary statement.

Minimum runtime-smoke requirements:

- explicit user authorization for real Ollama;
- explicit model name;
- explicit local base URL;
- explicit 2号窗口 / `ollama serve` ownership rule;
- no external network call;
- no model download or pull;
- no service start unless separately authorized;
- no formal generation;
- no export;
- no job/result-bundle/output write;
- structure-only report;
- no full raw model output retention;
- thinking output summarized only as a bounded preview if present;
- stop after reporting and wait for review.

Runtime smoke must not be mixed with implementation, export, or formal generation work.

## 12. Recommended Next ZDoc Step

The recommended next step is docs-only:

```text
ZDoc Step 2: ZDoc local-LLM preview guard + fake-only tests 前置设计文档
```

Step 2 should design the guard and fake-only tests. It should not directly enter code implementation.

## 13. Closure Statement

This document only records the ZDoc local-LLM gap analysis and Qingtian preview boundary reuse design. It does not permit immediate code integration. It does not permit modifying the ZDoc generation chain, export chain, job/output/export paths, real Ollama transport, UI auto-triggering, or ZBid formal write-back.

Any future ZDoc local-LLM implementation must start from a separately authorized, default-off, preview-only, no-write, fake-only-tested guard design.
