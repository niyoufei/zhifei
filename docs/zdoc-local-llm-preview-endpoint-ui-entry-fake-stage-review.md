# ZDoc Local LLM Preview Endpoint UI Entry Fake Stage Review

## 1. Purpose

This document archives the ZDoc Step 11 implementation review for the local-LLM preview endpoint / UI entry fake-only helper stage.

ZDoc Step 11 completed a controlled pure-function endpoint / UI entry fake helper and deterministic tests. This review records the implementation scope, feature flag behavior, disabled/enabled behavior, deterministic test coverage, explicit non-integrations, no-write boundary, remaining risks, and next-stage entry criteria.

This document is docs-only. It does not modify code, tests, tasks, endpoint routes, UI pages, formal generation chains, formal export chains, `output/`, `job/`, `export/`, real Ollama transport, external model/API transports, or ZBid formal writeback.

## 2. Baseline before ZDoc Step 11

ZDoc Step 11 started from the Step 9 and Step 10 design baseline:

- Step 9 design document: `docs/zdoc-local-llm-preview-endpoint-ui-entry-design.md`
- Step 10 guard/test design document: `docs/zdoc-local-llm-preview-endpoint-ui-entry-guard-test-design.md`
- Step 11 stable tag after implementation: `v0.1.58-zdoc-local-llm-preview-endpoint-ui-entry-fake`
- Step 11 commit: `a279d73cb5f55d817f80a5b0a90fcde06ed8a900`

The inherited baseline required the endpoint / UI entry fake path to remain:

- default-off;
- fake-only;
- preview-only;
- no-write;
- deterministic;
- manually triggered or internally diagnostic only;
- disconnected from real endpoint registration;
- disconnected from real UI page changes;
- disconnected from real Ollama;
- disconnected from external model/API transports;
- disconnected from the formal generation chain;
- disconnected from the formal export chain;
- disconnected from ZBid formal writeback.

## 3. Files changed in ZDoc Step 11

Actual Step 11 implementation file:

```text
backend/zhifei_autoplan/ollama_preview.py
```

Actual Step 11 test file:

```text
backend/tests/test_ollama_preview.py
```

No other files were modified in Step 11.

Not modified:

- `backend/zhifei_autoplan/zbid_snapshot_mapper.py`
- `tasks/`
- `output/`
- `job/`
- `export/`
- `build/`
- any formal generation-chain file
- any formal export-chain file
- any ZBid formal writeback file
- any UI page file
- any app main entry or service startup file
- any real Ollama transport integration file

## 4. Feature flag behavior

Step 11 continues to use the existing feature flag:

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

Disabled behavior remains highest priority. When disabled, the endpoint / UI fake helper returns a stable disabled response and does not call the endpoint / UI fake bridge, fake preview builder, model client, Ollama, external model/API transport, generation chain, export chain, output writer, job writer, or ZBid writeback path.

## 5. Disabled endpoint / UI fake behavior review

ZDoc Step 11 added pure-function endpoint / UI entry fake helper behavior around the existing fake-only bridge.

Disabled endpoint / UI fake behavior:

- returns `status=disabled`;
- returns `enabled=false`;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- returns `entry_type=endpoint_ui_entry`;
- returns `entry_source=zdoc_local_llm_preview_endpoint_ui_entry_fake`;
- returns `endpoint_entry_ready=true`;
- returns `ui_entry_ready=true`;
- returns `endpoint_registered=false`;
- returns `ui_registered=false`;
- returns `service_started=false`;
- returns `fake_only=true`;
- returns `warning=local_llm_preview_endpoint_ui_entry_disabled`;
- returns `reason=feature_flag_disabled`;
- does not call the endpoint / UI fake bridge;
- does not call the fake preview builder;
- does not call any model client;
- does not write `output/job/export`;
- does not modify正文.

This proves the default-off endpoint / UI entry boundary at pure-function level.

## 6. Enabled endpoint / UI fake behavior review

Enabled endpoint / UI fake behavior:

- only goes through the deterministic fake preview bridge;
- returns advisory / suggestions;
- returns `preview_only=true`;
- returns `no_write=true`;
- returns `affects_generation=false`;
- returns `affects_export=false`;
- returns `affects_zbid_writeback=false`;
- returns `entry_type=endpoint_ui_entry`;
- returns `entry_source=zdoc_local_llm_preview_endpoint_ui_entry_fake`;
- returns `endpoint_entry_ready=true`;
- returns `ui_entry_ready=true`;
- returns `endpoint_registered=false`;
- returns `ui_registered=false`;
- returns `service_started=false`;
- returns `fake_only=true`;
- preserves manual trigger metadata;
- rejects automatic trigger with stable failure;
- does not modify正文章节;
- does not mutate input payload data;
- does not expose formal generated-output fields;
- does not expose DOCX / Markdown / JSON formal export fields;
- does not expose job IDs or export paths;
- does not connect ZBid formal writeback.

Stable failure behavior:

- missing payload returns `error_type=missing_input`;
- missing `section_text` returns `error_type=missing_field`;
- empty `section_text` returns `error_type=empty_text`;
- illegal fields such as `export` or `job` return `error_type=illegal_field`;
- automatic trigger returns `error_type=invalid_trigger`.

Enabled behavior remains fake-only. It does not call real Ollama and does not call external model/API transports.

## 7. Deterministic test coverage

Step 11 modified:

```text
backend/tests/test_ollama_preview.py
```

Test command:

```bash
python3 -m pytest backend/tests/test_ollama_preview.py -q
```

Test result:

```text
58 passed in 0.63s
```

The Step 11 tests cover:

- feature flag absent returns disabled;
- feature flag empty / false / 0 / no / off returns disabled;
- disabled endpoint / UI fake behavior does not call the bridge;
- disabled endpoint / UI fake behavior does not write `output/job/export`;
- enabled endpoint / UI fake behavior calls the fake-only bridge;
- enabled endpoint / UI fake behavior returns advisory / suggestions;
- enabled endpoint / UI fake behavior returns `preview_only=true`;
- enabled endpoint / UI fake behavior returns `no_write=true`;
- enabled endpoint / UI fake behavior returns `affects_generation=false`;
- enabled endpoint / UI fake behavior returns `affects_export=false`;
- enabled endpoint / UI fake behavior returns `affects_zbid_writeback=false`;
- enabled endpoint / UI fake behavior does not modify正文章节;
- enabled endpoint / UI fake behavior does not expose DOCX / Markdown / JSON formal export fields;
- enabled endpoint / UI fake behavior does not expose job or export path fields;
- enabled endpoint / UI fake behavior does not call Ollama;
- enabled endpoint / UI fake behavior does not call external model/API transports;
- enabled endpoint / UI fake behavior does not write `output/job/export`;
- same input returns deterministic output;
- missing input returns stable failure;
- empty text returns stable failure;
- illegal fields return stable failure;
- automatic trigger returns stable failure;
- UI view helper returns preview diagnostics display data only;
- UI view helper disables writeback, generation, export, and ZBid writeback actions;
- existing fake-only helper and API/task bridge tests continue to pass.

The tests are fake-only. They do not start a service, do not run Ollama, do not run `ollama serve`, do not call external model/API transports, do not download or pull models, and do not create formal artifacts.

## 8. Explicit non-integrations

Step 11 did not integrate the endpoint / UI fake helper into:

- real endpoint registration;
- route mounting;
- real UI page files;
- Streamlit UI controls;
- app main entry;
- service startup;
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

The current capability remains a pure-function endpoint / UI entry fake helper only.

## 9. No-write boundary

Step 11 preserved the no-write boundary.

The endpoint / UI fake helper:

- does not modify正文;
- does not write `output/`;
- does not write `job/`;
- does not write `export/`;
- does not create DOCX files;
- does not create formal Markdown files;
- does not create formal JSON files;
- does not persist preview suggestions;
- does not update job records;
- does not update export records;
- does not update ZBid records.

The UI view helper only returns display data for preview diagnostics and disables writeback, generation, export, and ZBid writeback actions.

## 10. No-generation-chain boundary

Step 11 did not modify the formal generation chain.

The endpoint / UI fake helper:

- does not start generation;
- does not queue generation jobs;
- does not create generation job IDs;
- does not call formal generation functions;
- does not turn preview advisory into正文;
- does not treat suggestions as accepted content;
- does not update generated document bundles;
- keeps `affects_generation=false`.

## 11. No-export-chain boundary

Step 11 did not modify the formal export chain.

The endpoint / UI fake helper:

- does not trigger DOCX export;
- does not trigger formal Markdown export;
- does not trigger formal JSON export;
- does not create export jobs;
- does not update export manifests;
- does not return export paths;
- does not call export helpers;
- keeps `affects_export=false`.

## 12. No-ZBid-writeback boundary

Step 11 did not connect ZBid formal writeback.

The endpoint / UI fake helper:

- does not build ZBid apply payloads;
- does not call ZBid writeback APIs;
- does not return ZBid writeback results;
- does not mutate ZBid snapshot mapper behavior;
- does not modify `backend/zhifei_autoplan/zbid_snapshot_mapper.py`;
- keeps `affects_zbid_writeback=false`.

## 13. Remaining risks

Remaining risks and constraints:

- Current capability only implements a pure-function endpoint / UI entry fake helper.
- Current capability has no real endpoint.
- Current capability has no real UI page.
- Current capability has no real Ollama call.
- Current capability has no service startup validation.
- Current capability has no generation-chain integration.
- Current capability has no export-chain integration.
- Current capability has no ZBid formal writeback.
- Fake-only tests do not prove real model availability.
- Fake-only tests do not prove service routing behavior.
- Fake-only tests do not prove browser or UI behavior.
- Future real endpoint integration must continue default-off.
- Future real UI entry must be manually triggered.
- Future real Ollama calls must be separately authorized and must use 2号窗口.
- Future work must not write `output/job/export`.
- Future work must not automatically modify正文.
- Future work must not trigger formal export.
- Future work must not connect ZBid formal writeback.

## 14. Required next-stage guard

Before any real endpoint, real UI, or runtime smoke work, a separate design must define:

- exact endpoint file scope;
- exact UI file scope;
- whether `backend/zhifei_autoplan/ollama_preview.py` may be modified;
- whether endpoint tests may be added or modified;
- whether UI tests may be added or modified;
- feature flag inheritance;
- disabled behavior;
- enabled fake-only behavior;
- manual trigger behavior;
- no-write verification;
- `output/job/export` count checks;
- no-generation-chain verification;
- no-export-chain verification;
- no-ZBid-writeback verification;
- no-real-Ollama verification for fake-only stages;
- whether runtime smoke may start a service;
- whether browser automation may be used;
- 2号窗口 usage rules for any later real Ollama stage;
- completion and ChatGPT review gate.

## 15. Recommended next ZDoc step

The recommended next step is docs-only:

ZDoc Step 13：ZDoc local-LLM preview endpoint / UI entry service smoke 前置设计文档

The next step must not directly enter real endpoint / UI code implementation or real Ollama.

## 16. Closure statement

ZDoc Step 11 completed a fake-only, preview-only, no-write, deterministic, pure-function endpoint / UI entry helper stage.

The implementation stayed inside:

- `backend/zhifei_autoplan/ollama_preview.py`
- `backend/tests/test_ollama_preview.py`

It did not register a real endpoint, did not modify a real UI page, did not start a service, did not call Ollama, did not call external model/API transports, did not write `output/job/export`, did not trigger DOCX / JSON / Markdown formal export, did not touch the formal generation chain, did not touch the formal export chain, and did not connect ZBid formal writeback.

This document does not authorize real endpoint implementation, real UI implementation, runtime smoke, real model transport, formal generation, formal export, or ZBid writeback.
