# ZDoc Real Ollama Preview Safe Endpoint Bridge Design

## 1. Stage Background

This document records ZDoc Step 21: real-Ollama preview safe endpoint bridge design.

This step is docs-only. It does not implement endpoint wiring, does not modify code, does not modify tests, does not run pytest, does not start services, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

Step 20 has archived the runtime smoke report in:

```text
docs/zdoc-real-ollama-preview-runtime-smoke-report.md
```

The Step 20 runtime smoke confirmed:

- Ollama loopback `/api/tags` was reachable during the smoke.
- The local model list contained `qwen3:0.6b`.
- `POST /local-llm/preview-safe` kept `preview_only=true`.
- `POST /local-llm/preview-safe` kept `no_write=true`.
- `POST /local-llm/preview-safe` kept `affects_generation=false`.
- `POST /local-llm/preview-safe` kept `affects_export=false`.
- The enabled safe endpoint scenario still returned `calls_ollama=false`.
- The current safe endpoint still has not exercised the real-Ollama generate path.

The important limitation from Step 20 is that endpoint safety was proven only for the existing isolated safe endpoint path. It was not proof of end-to-end real model preview through `POST /local-llm/preview-safe`.

## 2. Current Link Facts

Read-only code inspection shows that the current safe endpoint chain is:

```text
POST /local-llm/preview-safe
-> backend/app/routers/local_llm_preview_safe.py
-> local_llm_preview_safe_endpoint
-> run_zdoc_local_llm_preview_safe_service_entry
-> run_zdoc_local_llm_preview_task
-> run_zdoc_local_llm_preview
-> preview advisory response
```

The endpoint module currently defines:

```text
SAFE_ENDPOINT_PATH=/local-llm/preview-safe
SAFE_ENDPOINT_SOURCE=zdoc_local_llm_preview_isolated_safe_endpoint_fake
```

The safe service helper currently identifies itself as:

```text
zdoc_local_llm_preview_safe_service_entry_fake
```

The current endpoint metadata forces the safety fields back to no-write fake-only values, including:

```text
preview_only=true
no_write=true
affects_generation=false
affects_export=false
calls_generate_route=false
calls_export_docx_route=false
calls_review_apply_route=false
triggers_generation_chain=false
triggers_export_chain=false
writes_output=false
writes_job=false
writes_export=false
calls_ollama=false
calls_external_model_api=false
```

Therefore the current chain must not be interpreted as real-Ollama end-to-end connectivity. Even when both preview-related environment flags are enabled during a service smoke, the safe endpoint still returns through the fake-only safe helper path and does not call `/api/generate`.

## 3. Target Link Design

A later implementation step may bridge the isolated safe endpoint to the real-Ollama preview adapter. This document does not implement that bridge.

The target chain should be:

```text
POST /local-llm/preview-safe
-> endpoint guard
-> safe request normalization
-> run_zdoc_ollama_preview
-> model selection
-> /api/tags
-> /api/generate
-> normalize_zdoc_ollama_response
-> bounded preview-only advisory response
```

The endpoint guard must remain the first safety boundary. It must reject non-preview request shapes, formal output fields, generation/export/apply indicators, and malformed payloads before any adapter call.

Safe request normalization must translate the endpoint payload into the minimal adapter payload only:

```text
section_title
section_text
review_focus
preview_type
source_context
request_id
```

The bridge must not pass formal job identifiers, output paths, export paths, DOCX paths, JSON paths, Markdown paths, generated section fields, ZBid writeback fields, or正文 replacement fields into the adapter.

The adapter may call only the local Ollama loopback target:

```text
http://127.0.0.1:11434/api/tags
http://127.0.0.1:11434/api/generate
```

The normalized response must remain bounded advisory data. It must not become formal generated正文.

## 4. Double-Flag Admission

Future real Ollama preview through the safe endpoint must require both flags:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
```

Required behavior:

- If `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` is absent or false-like, the endpoint must return stable disabled and must not call the adapter or Ollama.
- If `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true` but `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` is absent or false-like, the endpoint must return stable disabled or retain the fake-only path and must not call Ollama.
- No endpoint-specific switch may bypass the double-flag requirement.
- Enabling the top-level preview flag alone must not imply real model execution.
- Any disabled path must keep `calls_ollama=false`.

False-like values must include absent, empty, `false`, `0`, `no`, and `off`.

## 5. Model Selection Boundary

Future real Ollama preview may allow model selection through:

```text
ZDOC_OLLAMA_PREVIEW_MODEL
```

Model selection rules:

- If `ZDOC_OLLAMA_PREVIEW_MODEL` is set, the adapter may use it only if the model appears in the local `/api/tags` response.
- If `ZDOC_OLLAMA_PREVIEW_MODEL` is not set, selection must use controlled local model selection from `/api/tags`.
- Model lookup is read-only.
- Model lookup must not download models.
- Model lookup must not pull models.
- Model lookup must not execute `ollama pull`.
- Model lookup must not use external model providers.
- If the requested model is missing, the result must be a controlled failure or controlled disabled state.
- If no usable local model exists, the result must be a controlled failure or controlled disabled state.
- A missing model must never trigger implicit download, implicit pull, or automatic update.

The model name may be returned as response metadata, but it must not be persisted to formal document state or output artifacts.

## 6. No-Write, No-Generation, No-Export Boundary

Even after real-Ollama generate is connected to preview, the safe endpoint must preserve:

```text
preview_only=true
no_write=true
affects_generation=false
affects_export=false
```

The bridge must not:

- write `output/`, `job/`, or `export/`;
- trigger `/generate`;
- trigger `/export_docx`;
- trigger `/review/apply`;
- connect ZBid formal writeback;
- modify formal section content;
- alter generated_sections;
- create formal DOCX output;
- create formal JSON output;
- create formal Markdown output;
- affect formal document generation results.

Allowed output is limited to a bounded advisory response for human review.

## 7. Response Structure Requirements

The safe endpoint response should continue to include at least:

```text
status
preview_only
no_write
affects_generation
affects_export
calls_ollama
model
advisory
suggestions
warnings or risk_notes
source
```

Response-state rules:

- Disabled scenarios must return `calls_ollama=false`.
- Fake-only scenarios must return `calls_ollama=false`.
- A real-Ollama successful preview is the only scenario allowed to return `calls_ollama=true`.
- A model-unavailable scenario must remain no-write and controlled.
- A timeout scenario must remain no-write and controlled.
- An invalid response scenario must remain no-write and controlled.
- A transport exception scenario must remain no-write and controlled.
- Failure scenarios must not raise unhandled exceptions into the formal generation chain.
- Failure scenarios must not expose partial formal output fields.
- All scenarios must preserve `preview_only=true`, `no_write=true`, `affects_generation=false`, and `affects_export=false`.

The response may include additional safety metadata such as:

```text
calls_generate_route=false
calls_export_docx_route=false
calls_review_apply_route=false
triggers_generation_chain=false
triggers_export_chain=false
writes_output=false
writes_job=false
writes_export=false
downloads_models=false
pulls_models=false
```

The `source` value should make the active path visible. Fake-only and real-adapter paths must not share an ambiguous source string.

## 8. Later Implementation Boundary

If a later step enters implementation, the allowed files should remain limited to:

```text
backend/app/routers/local_llm_preview_safe.py
backend/zhifei_autoplan/ollama_preview.py
backend/tests/test_local_llm_preview_safe_endpoint.py
backend/tests/test_ollama_preview.py
```

The implementation must start with deterministic fake transport, monkeypatch, or dependency injection coverage. It must not depend on a real local Ollama process for deterministic tests.

Recommended implementation shape:

- Keep endpoint request validation in `local_llm_preview_safe.py`.
- Add an explicit bridge decision after endpoint guard and request normalization.
- Call `run_zdoc_ollama_preview` only when both flags are true.
- Inject fake tags and fake generate transports in tests.
- Preserve the current fake-only behavior when the real adapter flag is disabled.
- Preserve existing no-write metadata and formal-field stripping.
- Preserve stable disabled and failure responses.

The later implementation must not modify unrelated routers, formal generation files, export files, ZBid writeback files, UI files, or runtime artifact directories unless a separate reviewed step explicitly authorizes that scope.

## 9. Required Deterministic Test Scenarios

Step 22 or Step 23 must cover deterministic tests before any runtime smoke:

- Top-level flag disabled: returns disabled, does not call adapter, does not call Ollama.
- Adapter flag disabled: returns disabled or fake-only response, does not call Ollama.
- Double flags enabled plus fake transport tags missing the model: returns failure or controlled disabled.
- Double flags enabled plus fake transport generate success: returns `status=ok` and `calls_ollama=true`.
- Double flags enabled plus fake transport generate response empty: returns controlled failure or bounded advisory.
- Fake transport raises exception: returns failure and remains no-write.
- Endpoint request payload missing fields: returns controlled defaults or 422, and writes nothing.
- Endpoint must not trigger `/generate`.
- Endpoint must not trigger `/export_docx`.
- Endpoint must not trigger `/review/apply`.
- All responses keep `preview_only=true`.
- All responses keep `no_write=true`.
- All responses keep `affects_generation=false`.
- All responses keep `affects_export=false`.
- No deterministic test may require a real Ollama process.
- No deterministic test may download, pull, or update a model.
- No deterministic test may write `output/`, `job/`, or `export/`.

The deterministic test suite should also assert that the safe endpoint strips or rejects formal result fields from helper or adapter responses.

## 10. Risks and Rollback

Primary risk:

```text
The safe endpoint could accidentally move from a fake-only path to a real adapter path that triggers generation-chain behavior or writes to disk.
```

Second risk:

```text
Real model output may be unstable, too long, empty, or hard to normalize into predictable advisory text.
```

Third risk:

```text
Users may misunderstand preview advisory output as having been written into the formal方案 or official section content.
```

Rollback method:

- Disable `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`.
- Keep the top-level preview disabled or fake-only path available.
- Preserve `POST /local-llm/preview-safe` as preview-only and no-write.
- Preserve current fake-only safe endpoint behavior.
- Do not delete existing fake-only tests.
- Do not delete existing fake-only helper paths.

Rollback must be possible without touching formal generation, export, or ZBid writeback surfaces.

## 11. Next Stage Recommendation

The next recommended step is:

```text
ZDoc Step 22: real-Ollama preview safe endpoint bridge guard + deterministic tests pre-design
```

An acceptable alternative is:

```text
ZDoc Step 22: fake-only test implementation plan for the safe endpoint bridge
```

The next step must not directly enter runtime smoke, real Ollama generate, formal generation-chain integration, export-chain integration, or ZBid formal writeback.
