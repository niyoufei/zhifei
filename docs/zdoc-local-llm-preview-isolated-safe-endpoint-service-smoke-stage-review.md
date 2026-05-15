# ZDoc Local LLM Preview Isolated Safe Endpoint Service Smoke Stage Review

## 1. Purpose

This document archives the ZDoc Step 14K service smoke stage review for the local-LLM preview isolated safe endpoint.

ZDoc Step 14K completed a fake-only isolated safe endpoint service smoke. The smoke verified disabled and enabled fake-only behavior through a local loopback FastAPI service while preserving the default-off, preview-only, no-write, no-generation-chain, no-export-chain, and no-ZBid-writeback boundaries.

This review is docs-only. It does not modify code, does not add or modify tests, does not run pytest, does not start a service, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

## 2. Baseline before ZDoc Step 14K

The service smoke inherited the ZDoc Step 14J smoke plan baseline:

- smoke plan: `docs/zdoc-local-llm-preview-isolated-safe-endpoint-service-smoke-plan.md`
- isolated safe endpoint implementation review: `docs/zdoc-local-llm-preview-isolated-safe-endpoint-fake-stage-review.md`
- endpoint implementation: `backend/app/routers/local_llm_preview_safe.py`
- application router include: `backend/app/main.py`
- feature flag: `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`
- allowed endpoint: `POST /local-llm/preview-safe`
- forbidden endpoints: `/generate`, `/export_docx`, `/review/apply`
- Step 14K smoke report: `docs/zdoc-local-llm-preview-isolated-safe-endpoint-service-smoke-report.md`
- Step 14K commit: `632f5b41e966ff76cecfa39d43fa289979df0c17`
- Step 14K tag: `v0.1.71-zdoc-local-llm-isolated-safe-endpoint-service-smoke-report`

## 3. Service smoke execution summary

ZDoc Step 14K verified only the isolated safe endpoint fake-only smoke path.

The service boundary was:

- listen address: `127.0.0.1`
- port: `18749`
- forbidden listen address: `0.0.0.0`
- allowed request: `POST /local-llm/preview-safe`

The smoke only requested:

```text
POST /local-llm/preview-safe
```

The smoke did not request:

```text
/generate
/export_docx
/review/apply
```

The smoke did not run pytest. It did not run Ollama. It did not run `ollama serve`. It did not call external model/API transports. It did not download or pull models.

## 4. Disabled scenario review

The disabled scenario was verified with `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` unset.

Startup boundary:

- host: `127.0.0.1`
- port: `18749`
- observed PID: `26956`
- endpoint requested: `POST /local-llm/preview-safe`

Disabled response summary:

- `status=disabled`
- `ok=false`
- `enabled=false`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `affects_zbid_writeback=false`
- `reason=feature_flag_disabled`
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `triggers_generation_chain=false`
- `triggers_export_chain=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`
- `calls_ollama=false`
- `calls_external_model_api=false`

The disabled scenario did not call the fake bridge for preview generation and did not write `output/job/export`.

## 5. Enabled fake-only scenario review

The enabled fake-only scenario was verified with:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
```

Startup boundary:

- host: `127.0.0.1`
- port: `18749`
- observed PID: `27008`
- endpoint requested: `POST /local-llm/preview-safe`

Enabled response summary:

- `status=ok`
- `ok=true`
- `enabled=true`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `affects_zbid_writeback=false`
- `source=zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- `entry_type=isolated_safe_endpoint`
- `fake_only=true`
- deterministic fake advisory returned
- deterministic fake suggestions returned
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `triggers_generation_chain=false`
- `triggers_export_chain=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`
- `calls_ollama=false`
- `calls_external_model_api=false`

The enabled scenario remained fake-only and advisory-only. It did not modify source section text and did not create formal output.

## 6. Forbidden route isolation review

The service smoke was limited to the isolated safe endpoint.

Confirmed not requested:

- `/generate`
- `/export_docx`
- `/review/apply`

The endpoint response also reported:

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`

This validates only the isolated safe endpoint smoke boundary. It does not validate or authorize smoke for any high-risk business route.

## 7. No-write verification

ZDoc Step 14K checked filesystem counts before and after the smoke.

Observed counts:

- `output/` file count before: `0`
- `output/` file count after: `0`
- `job/` file count before: `0`
- `job/` file count after: `0`
- `export/` file count before: `0`
- `export/` file count after: `0`
- `backend/data/autoplan/jobs` file count before: `87`
- `backend/data/autoplan/jobs` file count after: `87`

Conclusions:

- no `output/` file was written;
- no `job/` file was written;
- no `export/` file was written;
- no formal artifact was produced;
- no DOCX / JSON / Markdown formal export was triggered.

## 8. No-generation-chain verification

The smoke did not request `/generate` and did not trigger the formal generation chain.

Both disabled and enabled responses preserved:

- `affects_generation=false`
- `calls_generate_route=false`
- `triggers_generation_chain=false`

This milestone does not allow the local-LLM preview path to enter the formal generation chain.

## 9. No-export-chain verification

The smoke did not request `/export_docx` and did not trigger the formal export chain.

Both disabled and enabled responses preserved:

- `affects_export=false`
- `calls_export_docx_route=false`
- `triggers_export_chain=false`
- `writes_export=false`

This milestone does not allow the local-LLM preview path to enter DOCX / JSON / Markdown formal export.

## 10. No-ZBid-writeback verification

The smoke did not request `/review/apply` and did not connect ZBid formal writeback.

Both disabled and enabled responses preserved:

- `affects_zbid_writeback=false`
- `calls_review_apply_route=false`

This milestone does not allow ZBid writeback, review apply, or formal application logic.

## 11. Process shutdown and port cleanup review

All service processes were stopped after the smoke.

Disabled scenario:

- PID: `26956`
- stopped with `SIGTERM`
- port `18749` released

Enabled fake-only scenario:

- PID: `27008`
- stopped with `SIGTERM`
- port `18749` released

Final cleanup result:

- all service processes stopped;
- port `18749` had no listener;
- no background service remained.

## 12. Remaining risks

This stage only verifies the fake-only isolated safe endpoint.

Remaining risks:

- this stage did not verify real Ollama;
- this stage did not verify real model availability;
- this stage did not verify the formal generation chain;
- this stage did not verify the formal export chain;
- this stage did not verify ZBid formal writeback;
- this stage did not run pytest, and only performed service smoke;
- fake-only service smoke does not prove that real model transport is safe;
- fake-only service smoke does not prove that generation-chain integration is safe;
- fake-only service smoke does not prove that export-chain integration is safe;
- fake-only service smoke does not prove that ZBid writeback integration is safe;
- high-risk chains must not be advanced automatically.

Any future real model stage must be separately designed and authorized. Any future formal generation-chain stage must be separately designed and authorized. Any future formal export-chain stage must be separately designed and authorized. Any future ZBid writeback stage must be separately designed and authorized.

## 13. What this milestone enables

This milestone establishes that the isolated safe endpoint can be exercised through local loopback service smoke while staying fake-only and no-write.

It enables future planning for:

- reviewing whether the fake-only preview endpoint should remain a diagnostics-only surface;
- deciding whether a later UI or operator workflow can reference the endpoint as preview-only;
- designing the next-stage local-LLM preview gate from a verified fake-only loopback baseline.

It does not authorize any implementation outside the isolated safe endpoint boundary.

## 14. What this milestone still does not allow

This milestone does not allow:

- real Ollama;
- `ollama serve`;
- external model/API calls;
- model download or pull;
- `/generate` smoke;
- `/export_docx` smoke;
- `/review/apply` smoke;
- formal document generation;
- DOCX / JSON / Markdown formal export;
- writing `output/`;
- writing `job/`;
- writing `export/`;
- modifying正文;
- ZBid formal writeback;
- automatic progression into high-risk chains.

If a future stage enters real Ollama, it must be separately designed and must use 2号窗口 only after explicit authorization. If a future stage enters formal generation, export, or ZBid writeback, it must be separately designed, tested, smoked, and reviewed by ChatGPT.

## 15. Recommended next ZDoc step

Recommended next step is docs-only:

```text
ZDoc Step 14M：ZDoc local-LLM preview 阶段阶段性总结与下一阶段准入清单
```

The next step must not directly enter real Ollama, the formal generation chain, the formal export chain, or ZBid writeback.

## 16. Closure statement

ZDoc Step 14L only reviews and archives the Step 14K fake-only isolated safe endpoint service smoke. It does not continue into real model calls, formal generation, formal export, UI expansion, or ZBid writeback.
