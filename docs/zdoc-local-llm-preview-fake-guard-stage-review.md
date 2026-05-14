# ZDoc Local LLM Preview Fake Guard Stage Review

## 1. Purpose

This document archives the ZDoc Step 3 implementation review for the local-LLM preview fake guard.

ZDoc Step 3 completed a controlled fake-only helper-layer implementation for local-LLM preview and deterministic tests. This review records the implementation scope, feature flag behavior, disabled/enabled behavior, no-write boundary, explicit non-integrations, remaining risks, and next-stage entry criteria.

This document is docs-only. It does not modify code, tests, tasks, generation chains, export chains, output/job/export paths, real Ollama transport, API routes, UI, or ZBid formal write-back.

## 2. Baseline Before ZDoc Step 3

ZDoc Step 3 started from the Step 2 guard/test design baseline:

- Previous stable tag: `v0.1.49-zdoc-local-llm-preview-guard-test-design`
- Step 2 design document: `docs/zdoc-local-llm-preview-guard-test-design.md`
- Step 1 gap analysis document: `docs/zdoc-local-llm-gap-analysis-and-qingtian-boundary-reuse.md`
- Step 3 stable tag after implementation: `v0.1.50-zdoc-local-llm-preview-fake-guard`
- Step 3 commit: `531bc38477a884233588c1bdcca87cb2230fbaeb`

The Step 2 baseline required local-LLM preview work to remain default-off, preview-only, no-write, fake-only first, and separate from runtime smoke.

## 3. Files Changed in ZDoc Step 3

Actual Step 3 implementation file:

```text
backend/zhifei_autoplan/ollama_preview.py
```

Actual Step 3 test file:

```text
backend/tests/test_ollama_preview.py
```

No other files were modified in Step 3.

Not modified:

- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- `tasks/`
- `output/`
- `job/`
- `export/`
- `build/`
- formal generation-chain files
- formal export-chain files
- ZBid formal write-back files

## 4. Feature Flag Behavior

Step 3 introduced the fake-only local-LLM preview feature flag:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
```

Disabled values:

- absent
- empty
- `false`
- `0`
- `no`
- `off`

Enabled values:

- `true`
- `1`
- `yes`
- `on`

Disabled priority remains highest. When the flag is disabled, the helper returns a stable disabled response and does not call the fake client, model client, Ollama, external model API, or any generation/export/write-back path.

## 5. Disabled Behavior Review

Disabled behavior:

- returns `status=disabled`;
- returns `enabled=false`;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- returns `source=zdoc_local_llm_preview_fake`;
- returns `warning=local_llm_preview_disabled`;
- returns `reason=feature_flag_disabled`;
- does not call fake/model client.

This proves the default-off behavior required by Step 2 at the helper layer.

## 6. Enabled Fake Preview Behavior Review

Enabled behavior:

- only returns deterministic fake advisory / suggestions;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- returns `source=zdoc_local_llm_preview_fake`;
- returns `model=fake-local-llm`;
- uses advisory and suggestions fields rather than formal generated output fields;
- avoids response fields that look like formal job IDs or export paths;
- does not write the original section正文;
- does not mutate input payload data;
- produces stable output for identical input.

Failure behavior is also deterministic:

- missing payload returns `error_type=missing_input`;
- missing `section_text` returns `error_type=missing_field`;
- empty `section_text` returns `error_type=empty_text`;
- illegal fields such as `export` or `job` return `error_type=illegal_field`;
- fake client timeout returns `error_type=fake_client_timeout`;
- invalid fake response returns `error_type=invalid_fake_response`.

## 7. Deterministic Test Coverage

Step 3 modified:

```text
backend/tests/test_ollama_preview.py
```

Test command:

```bash
python3 -m pytest backend/tests/test_ollama_preview.py -q
```

Test result:

```text
28 passed in 0.22s
```

The tests cover:

- feature flag absent returns disabled;
- feature flag empty / false / 0 / no / off returns disabled;
- disabled state does not call fake/model client;
- enabled state returns fake preview;
- enabled state returns `preview_only=true`;
- enabled state returns `no_write=true`;
- enabled state returns `affects_generation=false`;
- enabled state returns `affects_export=false`;
- enabled state returns `affects_zbid_writeback=false`;
- enabled state does not write output/job/export/build paths;
- enabled state does not expose DOCX / Markdown / JSON formal export fields;
- enabled state does not expose job or export path fields;
- enabled state does not call Ollama or external API transport;
- same input returns deterministic output;
- input payload is not mutated;
- empty text returns stable failure;
- missing input and missing field return stable failure;
- illegal fields return stable failure;
- fake timeout returns stable failure;
- invalid fake response returns stable failure.

The tests are fake-only. They do not start a service, do not run Ollama, do not run `ollama serve`, do not call external model/API, do not download or pull models, and do not create formal artifacts.

## 8. Explicit Non-Integrations

Step 3 did not integrate the helper into:

- API endpoint;
- UI entry;
- task bridge;
- formal generation chain;
- export chain;
- job/result bundle;
- output artifact writer;
- DOCX export;
- JSON export;
- Markdown formal export;
- real Ollama;
- external model/API;
- model download or pull;
- ZBid formal write-back.

The current capability is still only a fake-only helper-layer function.

## 9. No-Write Boundary

Step 3 preserves the no-write boundary:

- does not write正文;
- does not write `output/`;
- does not write `job/`;
- does not write `export/`;
- does not write `build/`;
- does not write `backend/data/autoplan/jobs`;
- does not write result bundles;
- does not write output artifacts;
- does not generate DOCX;
- does not generate formal Markdown;
- does not generate formal JSON.

The fake preview result is advisory-only and requires human review before any future manual adoption.

## 10. No-Generation-Chain Boundary

Step 3 did not connect local-LLM preview to the formal generation chain.

Not connected:

- `run_autoplan`;
- generation queue;
- job worker;
- orchestrator;
- provider/main-chain LLM routing;
- automatic remediation;
- formal section rewrite;
- formal review/apply.

The helper returns advisory fields and does not produce formal generated document sections.

## 11. No-Export-Chain Boundary

Step 3 did not connect local-LLM preview to export paths.

Not triggered:

- DOCX export;
- JSON formal export;
- Markdown formal export;
- XLSX/PPTX export;
- export job creation;
- export path response;
- result bundle export.

The tests explicitly check that the fake preview response does not contain formal export-looking fields such as `docx`, `markdown`, `json`, `job_id`, or `export_path`.

## 12. No-ZBid-Writeback Boundary

Step 3 did not modify:

```text
backend/zhifei_autoplan/zbid_snapshot_mapper.py
```

Step 3 did not connect local-LLM preview to ZBid formal write-back.

Not connected:

- ZBid formal apply;
- ZBid write-back endpoint;
- ZBid review-state mutation;
- ZBid result adoption;
- ZBid export or submission path.

The existing ZBid mapper remains a separate mock-only / draft-only / no-write mapper.

## 13. Remaining Risks

Remaining risks and constraints:

- Current capability is only fake-only helper-layer logic.
- Current capability has no API endpoint.
- Current capability has no UI entry.
- Current capability has no task bridge.
- Current capability has no real Ollama call.
- Current capability has no external model/API call.
- Current capability has no generation-chain integration.
- Current capability has no export-chain integration.
- Current capability has no ZBid formal write-back integration.
- Fake-only tests do not prove that a real model is available.
- Fake-only tests do not prove real model response shape compatibility.
- Fake-only tests do not validate model latency, timeout behavior, token behavior, or local runtime stability.
- Future API integration must remain default-off.
- Future API integration must keep preview-only and no-write response semantics.
- Future UI integration must not auto-trigger preview.
- Future UI integration must not auto-write正文.
- Future real Ollama calls must be separately authorized.
- Future real Ollama calls must use the 2号窗口 / dedicated `ollama serve` rule.
- Future work must not write `output/`, `job/`, or `export/`.
- Future work must not trigger formal DOCX / JSON / Markdown export.
- Future work must not connect ZBid formal write-back without a separate design and review phase.

## 14. Required Next-Stage Guard

Before any API, UI, runtime smoke, or real model work, the next stage must define:

- exact allowed files;
- exact forbidden files;
- whether an API route may be added;
- whether a task bridge may be added;
- whether UI changes are in scope;
- whether tests may patch API bridge call sites;
- feature flag behavior at API boundary;
- disabled response contract;
- enabled fake response contract;
- no-write proof;
- no generation-chain proof;
- no export-chain proof;
- no ZBid write-back proof;
- fake-only test command and expected scope;
- runtime smoke exclusion from implementation tests;
- separate authorization requirement for real Ollama;
- 2号窗口 / `ollama serve` ownership rule for any later real runtime smoke;
- final ChatGPT review stop point.

The next stage must not combine API/UI design with immediate real model calls.

## 15. Recommended Next ZDoc Step

Recommended next step is docs-only:

```text
ZDoc Step 5: ZDoc local-LLM preview API / task bridge 前置设计文档
```

Step 5 should design the API / task bridge boundary before implementation. It must not directly enter code implementation.

## 16. Closure Statement

ZDoc Step 3 successfully added a default-off, preview-only, no-write, fake-only local-LLM preview helper and deterministic tests. The implementation remains strictly helper-layer only.

This stage does not authorize automatic continuation into API, UI, real Ollama, runtime smoke, formal generation, formal export, output/job/export writes, or ZBid formal write-back. Any later API or real-model phase must be separately designed, tested, reviewed, and approved by ChatGPT before implementation.
