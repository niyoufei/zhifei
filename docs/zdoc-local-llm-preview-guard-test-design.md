# ZDoc Local LLM Preview Guard and Test Design

## 1. Purpose

This document is the docs-only ZDoc Step 2 design for local-LLM preview guards and fake-only tests.

The current stage only designs guard boundaries and future deterministic test requirements. It does not implement code, does not add tests, does not run pytest, does not start services, does not run Ollama, does not run `ollama serve`, does not generate formal document artifacts, does not write `output/`, `job/`, or `export/`, does not touch the formal generation chain, does not touch the export chain, and does not connect ZBid formal write-back.

This document must not be interpreted as permission to implement local-LLM preview code immediately.

## 2. Baseline Inherited From ZDoc Step 1

This Step 2 inherits the ZDoc Step 1 local-LLM gap-analysis baseline:

- Current ZDoc branch: `main`
- Current Step 1 stable baseline: `v0.1.48-zdoc-local-llm-gap-analysis`
- Step 1 document: `docs/zdoc-local-llm-gap-analysis-and-qingtian-boundary-reuse.md`
- Existing preview helper: `backend/zhifei_autoplan/ollama_preview.py`
- Existing ZBid snapshot mapper: `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- Existing test root: `backend/tests/`
- Existing task spec root: `tasks/`

Read-only facts inherited from Step 1:

- ZDoc already has an Ollama preview helper file.
- ZDoc already has a ZBid snapshot mapper.
- ZDoc already has local-LLM / Ollama / ZBid related tests and docs.
- ZDoc has production-sensitive job, output, build, export, DOCX, JSON, Markdown, generation, and write-back surfaces.
- Qingtian boundary reuse for ZDoc means `default-off`, `preview-only`, `no-write`, fake-only tests first, and separately authorized runtime smoke.

Current Step 2 boundaries:

- Do not modify the formal generation chain.
- Do not write `output/`.
- Do not write `job/`.
- Do not write `export/`.
- Do not trigger DOCX, JSON, or Markdown formal export.
- Do not connect ZBid formal write-back.
- Do not run real Ollama.
- Do not start services.

## 3. Guard Objective

The future ZDoc local-LLM preview guard must prove that any preview feature remains a sidecar advisory capability.

Guard objectives:

- Preview must be `default-off`.
- Preview must be manually triggered.
- Preview must be `preview-only`.
- Preview must be `no-write`.
- Preview must not automatically modify generated正文 or source section content.
- Preview must not write `output/`, `job/`, `export/`, `build/`, result bundles, or job records.
- Preview must not trigger formal DOCX, JSON, or Markdown exports.
- Preview must not connect ZBid formal write-back.
- Preview must not call external model APIs.
- Preview must not download or pull models.
- Preview must not run real Ollama during code implementation or fake-only tests.
- Runtime smoke must be separately authorized.
- Real Ollama runtime smoke, if later authorized, must use the 2号窗口 / dedicated `ollama serve` rule.

The guard should fail closed. If any forbidden path is present in the changed files, command plan, response schema, or tests, the implementation should stop before commit.

## 4. Allowed Future File Scope

This Step 2 does not authorize code changes. It only defines the future file scope that a later implementation request must state explicitly.

A future implementation may be allowed to modify only after separate authorization:

- `backend/zhifei_autoplan/ollama_preview.py`, if the user explicitly permits helper-layer changes.
- A new or existing API bridge file, if the user explicitly permits a preview endpoint.
- New fake-only tests under `backend/tests/`, if the user explicitly permits tests.
- A new task spec under `tasks/`, if the user explicitly permits a guard task.
- A new docs review file under `docs/`, if the user explicitly permits post-implementation review docs.

Future authorization must name exact paths. Broad phrases such as "wire local LLM into ZDoc" are not sufficient to modify production chains.

## 5. Forbidden Future File Scope

Before explicit future authorization, the guard must reject changes to:

- formal generation-chain files;
- formal export-chain files;
- ZBid formal write-back files;
- job creation/update/store files;
- output artifact writer files;
- result-bundle writer files;
- `output/**`;
- `job/**`;
- `export/**`;
- `build/**`;
- generated DOCX, JSON, Markdown, XLSX, PPTX, or other formal artifact files;
- unrelated frontend auto-trigger behavior;
- unrelated cleanup or repo hygiene files.

Known sensitive paths and concepts include:

- `run_autoplan`;
- `create_job`;
- `update_job`;
- `_save_outputs`;
- `save_output_artifacts`;
- export functions;
- DOCX export handlers;
- section apply/reject/rollback handlers;
- provider/main-chain LLM routing;
- ZBid formal apply/write-back paths.

The guard must also reject `git clean`, untracked-file cleanup, model downloads, model pulls, service starts, and any command that attempts to hide or remove evidence.

## 6. Feature Flag Contract

The future preview feature must have an explicit feature flag. The recommended flag is:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

Feature flag contract:

- Missing flag means disabled.
- Empty flag means disabled.
- `0`, `false`, `no`, `off`, and `n` mean disabled.
- `1`, `true`, `yes`, `on`, and `y` may mean enabled.
- Disabled mode must not call transport, Ollama, external APIs, provider chains, or formal generation.
- Disabled mode must return a stable disabled response.
- Enabled mode in fake-only tests must use fake transport only.
- Enabled mode must still remain preview-only and no-write.

If future implementation reuses `ZDOC_OLLAMA_PREVIEW_ENABLED`, the implementation request must explicitly justify reusing the existing flag instead of creating `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`.

## 7. Preview-Only Response Contract

The future preview response should be stable, structured, and explicitly non-authoritative.

Recommended success schema:

```json
{
  "ok": true,
  "enabled": true,
  "status": "ok",
  "mode": "preview_only",
  "provider": "local_llm",
  "model": "fake-local-llm",
  "preview_type": "section_review",
  "content": "advisory preview text",
  "warning": null,
  "error": null,
  "fallback": null,
  "safety": {
    "default_off": true,
    "manual_trigger": true,
    "preview_only": true,
    "no_write": true,
    "affects_generated_body": false,
    "affects_export": false,
    "affects_job": false,
    "affects_zbid_writeback": false,
    "requires_human_review": true
  }
}
```

Recommended disabled/failure schema:

```json
{
  "ok": false,
  "enabled": false,
  "status": "disabled",
  "mode": "preview_only",
  "provider": "local_llm",
  "model": "fake-local-llm",
  "preview_type": "section_review",
  "content": "",
  "warning": "local_llm_preview_disabled",
  "error": null,
  "fallback": {
    "available": true,
    "message": "Local LLM preview is unavailable; formal generation was not affected."
  },
  "safety": {
    "default_off": true,
    "manual_trigger": true,
    "preview_only": true,
    "no_write": true,
    "affects_generated_body": false,
    "affects_export": false,
    "affects_job": false,
    "affects_zbid_writeback": false,
    "requires_human_review": true
  }
}
```

Response requirements:

- The response must not contain formal generated正文 replacements.
- The response must not contain export paths.
- The response must not contain job IDs for new or updated jobs.
- The response must not contain ZBid formal write-back IDs.
- The response must not include raw hidden thinking or full raw model traces.
- Any thinking-like signal may only appear as a bounded human-facing preview summary if separately designed and tested.

## 8. No-Write Boundary

The future guard and tests must prove no-write behavior across all results.

No-write means:

- No write to `output/`.
- No write to `job/`.
- No write to `export/`.
- No write to `build/`.
- No write to `backend/data/autoplan/jobs`.
- No result-bundle write.
- No output artifact write.
- No generated正文 mutation.
- No formal Markdown write.
- No formal JSON write.
- No DOCX write.
- No ZBid formal write-back.

Required no-write verification for future implementation:

- Count files under `backend/data/autoplan/jobs`, `build`, and `output` before and after fake-only tests.
- Patch or spy on `create_job`, `update_job`, `_save_outputs`, and `save_output_artifacts`.
- Patch or spy on export functions.
- Patch or spy on formal apply/write-back functions.
- Assert generated section inputs are unchanged after preview.
- Assert preview content is returned only in preview response fields.

## 9. No-Generation-Chain Boundary

The future preview feature must not call the formal generation chain.

Guard checks:

- No unauthorized change to formal generation-chain files.
- No call to `run_autoplan` from local-LLM preview.
- No queue or async generation path.
- No generation job creation.
- No orchestration or provider main-chain call unless a future runtime-smoke step explicitly authorizes a no-write smoke path.
- No automatic remediation or正文 replacement.

Fake-only tests should patch generation-chain entry points with failing mocks and assert they are not called.

## 10. No-Export-Chain Boundary

The future preview feature must not call export code.

Guard checks:

- No unauthorized change to export-chain files.
- No call to DOCX export.
- No call to JSON formal export.
- No call to Markdown formal export.
- No call to XLSX/PPTX export helpers.
- No returned formal export path.
- No export job creation.

Fake-only tests should patch all reachable export helpers with failing mocks and assert they are not called.

## 11. No-ZBid-Writeback Boundary

The future preview feature must not connect to ZBid formal write-back.

Guard checks:

- `backend/zhifei_autoplan/zbid_snapshot_mapper.py` must remain pure unless separately authorized.
- Existing ZBid mock API bridge must remain mock-only and draft-only.
- ZBid snapshot preview must not call Ollama automatically.
- Local-LLM preview output must not be posted to a ZBid formal write-back endpoint.
- ZBid formal apply, formal write-back, and review-state mutation paths must be patched or guarded in tests.

The preview result may reference `source_system=zbid` only as metadata for a preview context. It must not imply formal adoption by ZBid.

## 12. Fake-Only Deterministic Tests Matrix

This section designs future tests only. This Step 2 does not add test files and does not run pytest.

Required future fake-only matrix:

| Case | Input / Setup | Expected Result | Forbidden Side Effects |
| --- | --- | --- | --- |
| 1 | Feature flag absent | preview disabled | no Ollama call; no output/job/export write |
| 2 | Feature flag empty | preview disabled | no transport call; no service start |
| 3 | Feature flag `0` | preview disabled | no Ollama call; no generation chain |
| 4 | Feature flag `false` | preview disabled | no output/job/export write |
| 5 | Feature flag `no` | preview disabled | no model/API call |
| 6 | Feature flag `off` | preview disabled | no export chain |
| 7 | Disabled with fail transport | stable disabled response | fail transport not called |
| 8 | Enabled with fake preview success | stable preview-only response | no正文 mutation |
| 9 | Enabled fake section review | `preview_type=section_review` | no generation chain |
| 10 | Enabled fake pre-generation review | advisory warning response | no job creation |
| 11 | Enabled fake ZBid snapshot preview context | preview metadata only | no ZBid formal write-back |
| 12 | Fake client timeout | stable failure/fallback | no output/job/export write |
| 13 | Fake client invalid response | stable failure/fallback | no formal export |
| 14 | Fake client empty content | stable failure/fallback | no transport retry to real Ollama |
| 15 | Fake client success | stable preview result | no formal Markdown/JSON/DOCX |
| 16 | Preview content contains suggested rewrite | returned as advisory only | not written into正文 |
| 17 | Preview content contains export-like path | sanitized or treated as text only | no export file created |
| 18 | Preview content contains job-like token | treated as text only | no job file created |
| 19 | Any success/failure result | artifact counts unchanged | no `backend/data/autoplan/jobs`, `build`, `output` changes |
| 20 | Any test case | fake transport only | no real Ollama, no service, no model download/pull |

Additional fake-only requirements:

- Tests must not call external networks.
- Tests must not call real Ollama.
- Tests must not start backend or frontend services.
- Tests must not run `ollama serve`.
- Tests must not download or pull models.
- Tests must not execute `git clean`.
- Tests must not clean untracked files.
- Tests must not depend on existing local model inventory.
- Tests must not write DOCX, JSON, Markdown, XLSX, PPTX, job files, output files, or export files.

## 13. Runtime Smoke Acceptance Criteria

Runtime smoke is not authorized by this Step 2 document. It must be a separate future step.

If runtime smoke is later authorized, minimum acceptance criteria are:

- User explicitly authorizes real Ollama.
- User explicitly authorizes whether a service may start.
- User explicitly names the model.
- User explicitly names the local base URL.
- The 2号窗口 / `ollama serve` rule is active and documented.
- Runtime smoke uses loopback/local transport only.
- Runtime smoke does not call external model APIs.
- Runtime smoke does not download or pull models.
- Runtime smoke does not trigger formal generation.
- Runtime smoke does not trigger export.
- Runtime smoke does not create or update jobs.
- Runtime smoke does not write `output/`, `job/`, `export/`, or `build/`.
- Runtime smoke reports structure-only results.
- Runtime smoke does not retain full raw model output or hidden thinking.
- Runtime smoke stops after reporting and waits for ChatGPT review.

Runtime smoke must not be combined with code implementation, fake-only tests, formal document generation, or export-chain verification.

## 14. Future Implementation Acceptance Criteria

A later code implementation may start only if all of the following are true:

- ZDoc Step 2 design has been completed and archived.
- The user explicitly authorizes implementation after Step 2 review.
- The implementation request names the exact allowed files.
- The implementation request states whether `backend/zhifei_autoplan/ollama_preview.py` may be modified.
- The implementation request states whether new tests may be added.
- The implementation request states whether any API route may be added or changed.
- The implementation request states whether a task spec may be added.
- The feature flag name is explicit.
- Default-off behavior is explicit.
- Manual-trigger behavior is explicit.
- Preview-only response schema is explicit.
- No-write validation is explicit.
- The implementation does not write `output/`, `job/`, or `export/`.
- The implementation does not trigger export chains.
- The implementation does not connect ZBid formal write-back.
- Fake-only tests are implemented before runtime smoke.
- The code implementation stage does not run real Ollama.
- The code implementation stage does not run `ollama serve`.
- The code implementation stage does not start services unless separately authorized.
- Runtime smoke, if needed, is separated into a later authorized phase.
- The runtime-smoke phase is the first phase that may use the 2号窗口.
- Completion must stop and wait for ChatGPT review.

Minimum future implementation report:

- changed files;
- exact feature flag;
- exact preview response schema;
- fake-only test command;
- fake-only test result;
- artifact counts before/after;
- confirmation that output/job/export/build did not change;
- confirmation that DOCX/JSON/Markdown formal export did not run;
- confirmation that ZBid formal write-back did not run;
- confirmation that Ollama was not run in implementation/fake-only phase.

## 15. ZDoc Step 2 Closure Statement

This document is a guard and fake-only test design artifact only. It does not authorize immediate code implementation, test creation, pytest execution, service startup, real Ollama calls, `ollama serve`, model download or pull, formal document generation, output/job/export writes, DOCX/JSON/Markdown formal export, or ZBid formal write-back.

The recommended next step is ChatGPT review of this Step 2 design. Do not continue automatically into ZDoc code implementation, generation-chain work, export-chain work, runtime smoke, or real model calls.
