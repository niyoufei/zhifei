# ZDoc Local LLM Preview API Task Bridge Fake Stage Review

## 1. Purpose

This document archives the ZDoc Step 7 implementation review for the local-LLM preview API / task bridge fake-only path.

ZDoc Step 7 completed a controlled pure-function fake-only API / task bridge helper and deterministic tests. This review records the implementation scope, feature flag behavior, disabled/enabled bridge behavior, deterministic test coverage, explicit non-integrations, no-write boundary, remaining risks, and next-stage entry criteria.

This document is docs-only. It does not modify code, tests, tasks, endpoint routes, UI, formal generation chains, formal export chains, `output/`, `job/`, `export/`, real Ollama transport, external model/API transports, or ZBid formal writeback.

## 2. Baseline before ZDoc Step 7

ZDoc Step 7 started from the Step 5 and Step 6 design baseline:

- Step 5 design document: `docs/zdoc-local-llm-preview-api-task-bridge-design.md`
- Step 6 guard/test design document: `docs/zdoc-local-llm-preview-api-task-bridge-guard-test-design.md`
- Step 7 stable tag after implementation: `v0.1.54-zdoc-local-llm-preview-api-task-bridge-fake`
- Step 7 commit: `c7c944b89d38d60556abf1c4f78bed876c5a7d76`

The inherited baseline required the API / task bridge path to remain:

- default-off;
- preview-only;
- no-write;
- fake-only;
- deterministic;
- manually or internally triggered only;
- disconnected from real Ollama;
- disconnected from external model/API transports;
- disconnected from the formal generation chain;
- disconnected from the formal export chain;
- disconnected from ZBid formal writeback.

## 3. Files changed in ZDoc Step 7

Actual Step 7 implementation file:

```text
backend/zhifei_autoplan/ollama_preview.py
```

Actual Step 7 test file:

```text
backend/tests/test_ollama_preview.py
```

No other files were modified in Step 7.

Not modified:

- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- `tasks/`
- `output/`
- `job/`
- `export/`
- `build/`
- requirements / pyproject / lock files
- formal generation-chain files
- formal export-chain files
- ZBid formal writeback files

## 4. Feature flag behavior

Step 7 continues to use the existing feature flag:

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

Disabled behavior remains highest priority. When disabled, the API / task bridge returns a stable disabled response and does not call the helper, fake client, model client, Ollama, external model/API transport, generation chain, export chain, output writer, job writer, or ZBid writeback path.

## 5. Disabled bridge behavior review

Step 7 added the pure-function bridge helper:

```text
run_zdoc_local_llm_preview_task
```

Disabled bridge behavior:

- returns `status=disabled`;
- returns `enabled=false`;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- returns `source=zdoc_local_llm_preview_fake`;
- returns `bridge_type=api_task_bridge`;
- returns `bridge_source=zdoc_local_llm_preview_api_task_bridge_fake`;
- returns `warning=local_llm_preview_api_task_bridge_disabled`;
- returns `reason=feature_flag_disabled`;
- does not call `run_zdoc_local_llm_preview`;
- does not call any injected preview helper;
- does not write `output/job/export`;
- does not modify正文.

This proves the default-off bridge boundary at pure-function level.

## 6. Enabled fake-only bridge behavior review

Enabled bridge behavior:

- calls only the fake-only helper path;
- calls `run_zdoc_local_llm_preview` by default;
- accepts an injected `preview_helper` only for fake-only deterministic tests;
- builds a sanitized helper payload through `build_zdoc_local_llm_preview_api_payload`;
- only returns deterministic advisory / suggestions;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- returns `bridge_type=api_task_bridge`;
- returns `bridge_source=zdoc_local_llm_preview_api_task_bridge_fake`;
- preserves manual/internal trigger metadata through `trigger`;
- preserves caller metadata through `caller`;
- does not modify正文章节;
- does not mutate input payload data;
- does not expose formal generated-output fields;
- does not expose DOCX / Markdown / JSON formal export fields;
- does not expose job IDs or export paths.

Stable failure behavior:

- missing payload returns `error_type=missing_input`;
- missing `section_text` returns `error_type=missing_field`;
- empty `section_text` returns `error_type=empty_text`;
- illegal fields such as `export` or `job` return `error_type=illegal_field`;
- helper timeout returns `error_type=bridge_helper_timeout`;
- helper exception returns `error_type=bridge_helper_error:<ExceptionName>`;
- invalid helper response returns `error_type=invalid_bridge_response`.

Enabled behavior remains fake-only. It does not call real Ollama and does not call external model/API transports.

## 7. Deterministic test coverage

Step 7 modified:

```text
backend/tests/test_ollama_preview.py
```

Test command:

```bash
python3 -m pytest backend/tests/test_ollama_preview.py -q
```

Test result:

```text
42 passed in 0.34s
```

The Step 7 tests cover:

- bridge default disabled;
- feature flag absent returns disabled;
- feature flag empty / false / 0 / no / off returns disabled;
- disabled bridge does not call helper;
- disabled bridge does not write `output/job/export`;
- enabled bridge calls the fake-only helper;
- enabled bridge returns `preview_only=true`;
- enabled bridge returns `no_write=true`;
- enabled bridge returns `affects_generation=false`;
- enabled bridge returns `affects_export=false`;
- enabled bridge returns `affects_zbid_writeback=false`;
- enabled bridge does not modify正文章节;
- enabled bridge does not expose DOCX / Markdown / JSON formal export fields;
- enabled bridge does not expose job or export path fields;
- enabled bridge does not call Ollama;
- enabled bridge does not call external model/API transports;
- enabled bridge does not write `output/job/export`;
- same input returns deterministic output;
- missing input returns stable failure;
- empty text returns stable failure;
- illegal fields return stable failure;
- existing fake-only helper tests continue to pass.

The tests are fake-only. They do not start a service, do not run Ollama, do not run `ollama serve`, do not call external model/API transports, do not download or pull models, and do not create formal artifacts.

## 8. Explicit non-integrations

Step 7 did not integrate the bridge into:

- real endpoint registration;
- route mounting;
- UI entry;
- task file execution;
- formal generation chain;
- formal export chain;
- job creation/update path;
- result bundle path;
- output artifact writer;
- DOCX export;
- JSON export;
- Markdown formal export;
- real Ollama;
- external model/API transport;
- model download or pull;
- ZBid formal writeback.

The current capability is still only a pure-function fake-only API/task bridge helper.

## 9. No-write boundary

Step 7 preserves the no-write boundary:

- does not write正文;
- does not modify正文章节;
- does not persist preview suggestions;
- does not write `output/`;
- does not write `job/`;
- does not write `export/`;
- does not write `build/`;
- does not write `backend/data/autoplan/jobs`;
- does not write result bundles;
- does not write output artifacts;
- does not generate DOCX;
- does not generate formal Markdown;
- does not generate formal JSON;
- does not write to ZBid.

The fake preview result remains advisory-only and requires human review before any future manual adoption.

## 10. No-generation-chain boundary

Step 7 did not connect local-LLM preview API / task bridge behavior to the formal generation chain.

Not connected:

- `run_autoplan`;
- generation queue;
- job worker;
- orchestrator;
- provider/main-chain LLM routing;
- automatic remediation;
- formal section rewrite;
- formal review/apply;
- automatic generation-before-preview;
- automatic generation-after-preview.

The bridge returns advisory fields and does not produce or apply formal generated document sections.

## 11. No-export-chain boundary

Step 7 did not connect local-LLM preview API / task bridge behavior to export paths.

Not triggered:

- DOCX export;
- JSON formal export;
- Markdown formal export;
- XLSX/PPTX export;
- export job creation;
- export metadata write;
- export path response;
- result bundle export.

The tests check that the fake bridge response does not contain formal export-looking fields such as `docx`, `markdown`, `json`, `job_id`, or `export_path`.

## 12. No-ZBid-writeback boundary

Step 7 did not modify:

```text
backend/zhifei_autoplan/zbid_snapshot_mapper.py
```

Step 7 did not connect local-LLM preview API / task bridge behavior to ZBid formal writeback.

Not connected:

- ZBid formal apply;
- ZBid writeback endpoint;
- ZBid review-state mutation;
- ZBid result adoption;
- ZBid export or submission path.

Any future ZBid-related input for local-LLM preview must remain read-only, snapshot-style, preview-only, and no-write until a separate approved phase says otherwise.

## 13. Remaining risks

Remaining risks and constraints:

- Current capability only implements a fake-only API/task bridge helper.
- Current capability is pure-function level only.
- Current capability has no real endpoint.
- Current capability has no UI entry.
- Current capability has no real Ollama call.
- Current capability has no external model/API call.
- Current capability has no generation-chain integration.
- Current capability has no export-chain integration.
- Current capability has no ZBid formal writeback integration.
- Fake-only tests do not prove that a real model is available.
- Fake-only tests do not prove real model response shape compatibility.
- Fake-only tests do not validate model latency, token behavior, timeout behavior, local runtime ownership, or runtime stability.
- Future endpoint integration must continue default-off.
- Future endpoint integration must keep preview-only and no-write response semantics.
- Future UI integration must not auto-trigger preview.
- Future UI integration must not auto-write正文.
- Future real Ollama calls must be separately authorized.
- Future real Ollama calls must use the 2号窗口 / dedicated `ollama serve` rule.
- Future work must not write `output/job/export`.
- Future work must not automatically modify正文.
- Future work must not trigger formal DOCX / JSON / Markdown export.
- Future work must not connect ZBid formal writeback without separate design, tests, smoke criteria, and ChatGPT review.

## 14. Required next-stage guard

Before any endpoint, UI, runtime smoke, real model, generation-chain, export-chain, or ZBid work, the next stage must define:

- exact allowed files;
- exact forbidden files;
- whether an endpoint may be added;
- whether UI changes are in scope;
- whether task files are in scope;
- whether `backend/zhifei_autoplan/ollama_preview.py` may be modified again;
- whether `backend/tests/test_ollama_preview.py` remains the relevant regression test;
- whether additional endpoint/UI tests are allowed;
- feature flag behavior at endpoint boundary;
- disabled endpoint/UI behavior;
- enabled fake-only endpoint/UI behavior;
- no-write proof;
- no generation-chain proof;
- no export-chain proof;
- no ZBid writeback proof;
- fake-only test command and expected scope;
- runtime smoke exclusion from implementation tests;
- separate authorization requirement for real Ollama;
- 2号窗口 / `ollama serve` ownership rule for any later real runtime smoke;
- final ChatGPT review stop point.

The next stage must not combine endpoint/UI design with immediate real model calls, formal generation, formal export, or ZBid writeback.

## 15. Recommended next ZDoc step

Recommended next step is docs-only:

```text
ZDoc Step 9：ZDoc local-LLM preview endpoint / UI entry 前置设计文档
```

Step 9 must design endpoint / UI entry boundaries before implementation. It must not directly enter endpoint code implementation or UI code implementation.

## 16. Closure statement

ZDoc Step 7 successfully added a default-off, preview-only, no-write, fake-only API / task bridge helper and deterministic tests. The implementation remains strictly pure-function helper level.

This stage does not authorize automatic continuation into endpoint registration, UI entry, real Ollama, runtime smoke, formal generation, formal export, `output/job/export` writes, or ZBid formal writeback. Any later endpoint, UI, or real-model phase must be separately designed, tested, reviewed, and approved by ChatGPT before implementation.
