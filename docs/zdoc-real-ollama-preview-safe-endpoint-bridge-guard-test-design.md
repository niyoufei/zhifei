# ZDoc Real Ollama Preview Safe Endpoint Bridge Guard Test Design

## 1. Stage Background

This document records ZDoc Step 22: real-Ollama preview safe endpoint bridge guard + deterministic tests pre-design.

This step is docs-only. It does not implement endpoint bridge code, does not modify tests, does not run pytest, does not start services, does not run Ollama, does not run `ollama serve`, does not call external model/API transports, does not download or pull models, does not generate formal documents, does not write `output/`, `job/`, or `export/`, does not trigger DOCX / JSON / Markdown formal export, and does not connect ZBid formal writeback.

Step 21 has archived the bridge design in:

```text
docs/zdoc-real-ollama-preview-safe-endpoint-bridge-design.md
```

Step 21 designed a future bridge from `POST /local-llm/preview-safe` to the real-Ollama preview adapter, but it was docs-only. It did not implement endpoint calls into `run_zdoc_ollama_preview`, and it did not validate an end-to-end `/api/generate` path through the safe endpoint.

The inherited Step 20 facts remain:

- Step 20 confirmed only that Ollama loopback `/api/tags` was reachable during that smoke.
- Step 20 confirmed the local model list included `qwen3:0.6b`.
- Step 20 did not call Ollama `/api/generate`.
- Step 20 enabled scenario for `POST /local-llm/preview-safe` still returned `calls_ollama=false`.
- The current `/local-llm/preview-safe` endpoint must not be treated as proof that real-Ollama generate is connected.

The purpose of Step 22 is to lock down the guard, deterministic test, failure-response, no-write, and rollback boundaries before any later code implementation.

## 2. Current Fact Link

Read-only inspection shows the current safe endpoint chain is:

```text
POST /local-llm/preview-safe
-> backend/app/routers/local_llm_preview_safe.py
-> local_llm_preview_safe_endpoint
-> run_zdoc_local_llm_preview_safe_service_entry
-> run_zdoc_local_llm_preview_task
-> run_zdoc_local_llm_preview
-> preview-only advisory response
```

The current endpoint imports and calls:

```text
run_zdoc_local_llm_preview_safe_service_entry
```

The current endpoint source remains:

```text
zdoc_local_llm_preview_isolated_safe_endpoint_fake
```

The current safe service entry source remains:

```text
zdoc_local_llm_preview_safe_service_entry_fake
```

The current path must not be misread as:

```text
POST /local-llm/preview-safe
-> real Ollama /api/generate
```

Current response metadata explicitly keeps:

```text
calls_ollama=false
calls_generate_route=false
calls_export_docx_route=false
calls_review_apply_route=false
writes_output=false
writes_job=false
writes_export=false
```

Therefore any later bridge implementation must start from this fake-only safety floor and prove every changed path with deterministic tests before runtime smoke.

## 3. Later Target Link

A later implementation step may target this chain:

```text
POST /local-llm/preview-safe
-> endpoint guard
-> request normalization
-> run_zdoc_ollama_preview
-> model selection
-> /api/tags
-> /api/generate
-> normalize_zdoc_ollama_response
-> bounded preview-only advisory response
```

This document does not implement that target link.

The target endpoint guard must execute before any adapter call. Request normalization must pass only preview input fields to the adapter, not formal generation or export fields.

The adapter may use the existing real-Ollama preview adapter entry:

```text
run_zdoc_ollama_preview
```

The adapter's current deterministic-test structure already supports:

```text
fake tags transport
fake generate transport
select_zdoc_local_ollama_model
normalize_zdoc_ollama_response
```

The later endpoint bridge must preserve that injection boundary so deterministic tests do not require a real Ollama runtime.

## 4. Guard Design Requirements

Future implementation must include these guards:

- If `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true` is not set, return stable disabled.
- If `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true` is not set, return stable disabled or preserve the existing fake-only behavior.
- If the adapter flag is disabled, do not call Ollama.
- Only when both flags are true and the request is valid may the endpoint enter the real-Ollama preview adapter.
- Disabled responses must keep `preview_only=true`.
- Disabled responses must keep `no_write=true`.
- Failure responses must keep `preview_only=true`.
- Failure responses must keep `no_write=true`.
- Exceptions must be caught and converted into controlled failure responses.
- No exception may cross into the formal generation chain.
- The endpoint must not call `/generate`.
- The endpoint must not call `/export_docx`.
- The endpoint must not call `/review/apply`.
- The endpoint must not write `output/`, `job/`, or `export/`.
- The endpoint must not modify formal section content.
- The endpoint must not connect ZBid formal writeback.

The request guard must reject or control:

- missing required preview payload;
- empty `section_text`;
- illegal fields such as `generate`, `export_docx`, `review_apply`, `job_id`, `output_path`, `docx_path`, `json_path`, and `markdown_path`;
- helper or adapter responses that contain formal result fields.

The model guard must reject missing or unavailable models without download, pull, or update.

The transport guard must limit target semantics to the preview adapter path. The formal route `/generate` is forbidden even though the Ollama adapter may later call Ollama's local `/api/generate` transport under the guarded preview-only path.

## 5. Response Structure Guard

The future safe endpoint response must retain at least:

```text
status
ok
enabled
preview_only
no_write
affects_generation
affects_export
calls_ollama
model
source
advisory
suggestions
warnings or risk_notes
error_type or failure_reason
```

Response-state definitions:

- `disabled`: `calls_ollama=false`.
- `fake-only`: `calls_ollama=false`.
- `real-Ollama success`: `calls_ollama=true`.
- `real-Ollama controlled failure`: `calls_ollama` must explicitly reflect whether the adapter reached the fake or real Ollama transport boundary, but the response must keep `no_write=true`.
- `exception`: controlled failure, no unhandled stack trace in the user-facing response.

All response states must preserve:

```text
preview_only=true
no_write=true
affects_generation=false
affects_export=false
```

The endpoint should continue to expose explicit no-route/no-write metadata:

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

The `source` value must distinguish disabled, fake-only, and real-adapter preview paths clearly enough that smoke reports cannot confuse fake-only success with real-Ollama success.

## 6. Deterministic Tests Pre-Design

The later implementation must add deterministic tests before runtime smoke. This Step 22 document does not run pytest.

### 6.1 Top-Level Flag Disabled

Test target:

```text
POST /local-llm/preview-safe
```

Input:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED unset or false-like
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
valid preview payload
```

Expected output:

```text
status=disabled
ok=false
enabled=false
preview_only=true
no_write=true
calls_ollama=false
```

Must not happen:

- fake transport is not called;
- real adapter is not called;
- Ollama is not called;
- `output/job/export` is not written.

### 6.2 Adapter Flag Disabled

Input:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED unset or false-like
valid preview payload
```

Expected output:

```text
status=disabled or fake-only ok
calls_ollama=false
preview_only=true
no_write=true
```

Must not happen:

- `/api/tags` transport is not called;
- `/api/generate` transport is not called;
- formal generation, export, and apply routes are not called.

### 6.3 Double Flags Enabled With Model Present

Input:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
fake /api/tags response includes qwen3:0.6b
```

Expected output:

```text
model=qwen3:0.6b
fake generate path is allowed
preview_only=true
no_write=true
```

Must not happen:

- model download;
- model pull;
- external API call.

### 6.4 Double Flags Enabled With Model Missing

Input:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
fake /api/tags response does not include qwen3:0.6b
```

Expected output:

```text
status=failure or controlled disabled
error_type=model_unavailable
no_write=true
```

Must not happen:

- fake generate transport is not called;
- model is not downloaded;
- model is not pulled;
- `ollama pull` is not executed.

### 6.5 Fake Generate Normal Response

Input:

```text
double flags enabled
fake /api/tags includes selected model
fake /api/generate returns a normal response field
```

Expected output:

```text
status=ok
calls_ollama=true
model=<selected model>
advisory=<bounded advisory>
suggestions=<bounded suggestions>
preview_only=true
no_write=true
```

Must not happen:

- formal content fields are returned;
- `job_id`, `output_path`, `export_path`, `docx_path`, `json_path`, or `markdown_path` appear;
- any file write occurs.

### 6.6 Fake Generate Empty Response

Input:

```text
fake /api/generate returns no usable response, message content, or advisory
```

Expected output:

```text
status=failure or bounded advisory
error_type=invalid_response or equivalent
reason=missing_preview_advisory or equivalent
no_write=true
```

Must not happen:

- raw empty model output is treated as formal正文;
- generation chain is triggered as fallback.

### 6.7 Fake Generate Thinking-Only Response

Input:

```text
fake /api/generate returns thinking-only or reasoning-only text
```

Expected output:

```text
status=ok with bounded preview advisory or controlled failure
risk_notes or warning marks the output as preview-only
preview_only=true
no_write=true
```

The implementation should follow the existing normalization pattern: extract bounded text only from accepted response shapes, convert it into advisory / suggestions, and never treat it as formal正文.

Must not happen:

- thinking-only text is written into the formal方案;
- thinking-only text is returned as a正文 replacement field;
- hidden or long raw reasoning is persisted.

### 6.8 Fake Transport Exception

Input:

```text
fake tags transport or fake generate transport raises TimeoutError, OSError, ValueError, or RuntimeError
```

Expected output:

```text
status=failure
error_type=timeout, ollama_unreachable, invalid_response, or transport_failure
no_write=true
preview_only=true
```

Must not happen:

- unhandled stack trace is returned to the user;
- exception reaches generation, export, or writeback code.

### 6.9 Endpoint Payload Missing Optional Fields

Input:

```text
valid section_text
missing optional section_title, context_summary, or request_id
```

Expected output:

```text
controlled defaults are applied
no_write=true
```

Must not happen:

- no disk write;
- no formal job creation;
- no export artifact.

### 6.10 Endpoint Payload Illegal

Input examples:

```text
generate=true
export_docx=true
review_apply=true
job_id=...
output_path=...
docx_path=...
```

Expected output:

```text
422 or controlled failure
preview_only=true
no_write=true
```

Must not happen:

- adapter transport is called after illegal payload detection;
- formal route is called;
- file output is written.

### 6.11 Universal Guard Assertions

Every endpoint response in the deterministic suite must assert:

```text
preview_only=true
no_write=true
affects_generation=false
affects_export=false
```

The suite must also prove:

- `/generate` is not triggered;
- `/export_docx` is not triggered;
- `/review/apply` is not triggered;
- `output/` is not written;
- `job/` is not written;
- `export/` is not written.

The current tests already use write-surface count checks for `output`, `job`, `export`, `backend/data/autoplan/jobs`, and `build`. The later implementation should preserve that style for this bridge.

## 7. Fake Transport and Dependency Injection Requirements

Future deterministic tests must prioritize:

- fake tags transport;
- fake generate transport;
- monkeypatch;
- dependency injection;
- stable fixture payload;
- explicit write-surface count snapshots;
- route patching for forbidden generation/export/apply calls.

Future deterministic tests must not:

- depend on a real Ollama process;
- run `ollama serve`;
- call external network providers;
- call OpenAI, Spark, Gemini, or any other external model/API;
- download models;
- pull models;
- execute `ollama pull`;
- write formal `output/`, `job/`, or `export/`;
- create DOCX, JSON, or Markdown formal export artifacts.

Fake transport tests may use the target URL strings:

```text
http://127.0.0.1:11434/api/tags
http://127.0.0.1:11434/api/generate
```

Those URL strings in fake tests are contract assertions, not permission to call a real local Ollama runtime during deterministic tests.

## 8. Allowed Future Modification Boundary

If a later step enters implementation or tests, the default allowed file set should remain:

```text
backend/app/routers/local_llm_preview_safe.py
backend/zhifei_autoplan/ollama_preview.py
backend/tests/test_local_llm_preview_safe_endpoint.py
backend/tests/test_ollama_preview.py
```

The later implementation should not add a new test file unless that addition is separately designed and reviewed by ChatGPT.

The preferred implementation sequence is:

1. Add or adjust deterministic tests with fake transport / monkeypatch first.
2. Add the minimal endpoint bridge guard.
3. Wire only the preview-safe path to the adapter under the double flag.
4. Re-run only the narrowly relevant deterministic tests when explicitly authorized.

## 9. Forbidden Future Touch Boundary

The later implementation must not modify formal generation-chain files, formal export-chain files, ZBid writeback files, runtime artifact directories, formal templates, formal generated result files, or unrelated UI main flows.

Concrete paths already visible from the inspected files and prior stage documents include:

```text
backend/app/routers/actions_bridge.py
backend/app/routers/zhifei_autoplan.py
backend/zhifei_autoplan/zbid_snapshot_mapper.py
backend/data/autoplan/jobs/
output/
job/
export/
build/
app.py
frontend_web/app.py
```

These paths must remain untouched unless a later, separately reviewed step explicitly expands scope.

Formal template files, formal generation result files, and preview-unrelated UI main-flow files require another read-only inventory before implementation if a later task proposes touching them.

## 10. Risks and Rollback

Risk 1:

```text
The safe endpoint may enter the real adapter path and accidentally trigger the formal generation chain or write to disk.
```

Risk 2:

```text
Real model output may be unstable, empty, too long, or not suitable for predictable advisory normalization.
```

Risk 3:

```text
Thinking-only output may be mistaken for formal正文.
```

Risk 4:

```text
Users may believe preview advisory text has already been written back into the official方案.
```

Risk 5:

```text
Missing local models may accidentally trigger automatic download or pull behavior.
```

Rollback measure:

```text
Disable ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED.
```

Fallback measure:

- Keep the existing disabled path.
- Keep the existing fake-only path.
- Preserve current fake-only safe endpoint behavior.
- Preserve existing fake-only tests.
- Do not delete fake-only helpers.
- Do not delete fake transport support.

Rollback must not require changes to formal generation, export, or ZBid writeback code.

## 11. Next Stage Recommendation

The next recommended step is:

```text
ZDoc Step 23: real-Ollama preview safe endpoint bridge fake-only implementation + deterministic tests
```

The next step must not directly enter runtime smoke, real Ollama `/api/generate`, formal generation-chain integration, export-chain integration, or ZBid formal writeback.
