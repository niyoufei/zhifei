# ZDoc Real Ollama Preview Runtime Smoke Report

## 1. Purpose

This report records ZDoc Step 20: real-Ollama preview runtime smoke + smoke report.

The smoke was limited to local loopback checks and the isolated safe endpoint:

```text
POST /local-llm/preview-safe
```

This step did not modify code, did not add or modify tests, did not run pytest, did not call external model/API transports, did not access the internet, did not download or pull models, did not execute `ollama pull`, did not request `/generate`, did not request `/export_docx`, did not request `/review/apply`, did not write `output/`, `job/`, or `export/`, did not trigger DOCX / JSON / Markdown formal export, and did not connect ZBid formal writeback.

## 2. Baseline

Working directory:

```text
/Users/youfeini/Desktop/文档生成系统
```

Branch:

```text
main
```

Start HEAD:

```text
babd4cd4ccab0cdfcb5d334d29c52a0f95a19393
```

The inherited plan was:

```text
docs/zdoc-real-ollama-preview-runtime-smoke-plan.md
```

The baseline tag was:

```text
v0.1.78-zdoc-real-ollama-preview-runtime-smoke-plan
```

## 3. 2号窗口 and Ollama serve

Initial listener check found no existing listener on:

```text
127.0.0.1:11434
```

2号窗口 was used only to run:

```text
ollama serve
```

Observed Ollama listener:

```text
PID 48013
TCP 127.0.0.1:11434 (LISTEN)
```

No other command was run in 2号窗口.

Because this Ollama listener was started by this step, it was stopped after the smoke. Final listener check showed no process listening on `127.0.0.1:11434`.

## 4. Ollama reachability check

Codex performed only this loopback reachability request:

```text
GET http://127.0.0.1:11434/api/tags
```

Result:

- HTTP status: `200`
- valid JSON: yes
- models field present: yes
- external network access: no
- model download: no
- model pull: no
- `ollama pull`: not executed

Local model summary:

```text
model_count=7
models=qwen3-next:80b-a3b-instruct-q8_0, qwen3-coder:30b, deepseek-r1:32b, qwen3:30b, qwen3:14b, qwen3:8b, qwen3:0.6b
```

Preferred lightweight local model was present:

```text
qwen3:0.6b
```

The full model JSON output is not repeated in this report.

## 5. Service startup boundary

FastAPI service smoke used only loopback:

```text
127.0.0.1:18750
```

No service listened on `0.0.0.0`.

Disabled scenario service command:

```text
env -u ZDOC_LOCAL_LLM_PREVIEW_ENABLED -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18750
```

Disabled scenario service PID:

```text
48067
```

Enabled scenario service command:

```text
env ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18750
```

Enabled scenario service PID:

```text
48135
```

Both FastAPI service processes were stopped with Ctrl-C. Final listener check showed no process listening on `127.0.0.1:18750`.

## 6. Disabled scenario

Feature flag state:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED unset
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED unset
```

Request endpoint:

```text
POST /local-llm/preview-safe
```

Synthetic request summary:

```json
{
  "section_title": "Smoke preview",
  "section_text": "Synthetic local preview smoke only.",
  "context_summary": "disabled smoke",
  "request_id": "zdoc-step20-disabled"
}
```

HTTP status:

```text
200
```

Response summary:

```text
ok=false
enabled=false
status=disabled
preview_only=true
no_write=true
affects_generation=false
affects_export=false
affects_zbid_writeback=false
source=zdoc_local_llm_preview_isolated_safe_endpoint_fake
endpoint_path=/local-llm/preview-safe
reason=feature_flag_disabled
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

Disabled scenario conclusion:

```text
passed: top-level preview flag disabled returned disabled and did not call real Ollama generate.
```

## 7. Enabled runtime smoke scenario

Feature flag state:

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
```

Request endpoint:

```text
POST /local-llm/preview-safe
```

Synthetic request summary:

```json
{
  "section_title": "Smoke preview",
  "section_text": "Synthetic local preview smoke only.",
  "context_summary": "enabled runtime smoke",
  "request_id": "zdoc-step20-enabled"
}
```

HTTP status:

```text
200
```

Response summary:

```text
ok=true
enabled=true
status=ok
preview_only=true
no_write=true
affects_generation=false
affects_export=false
affects_zbid_writeback=false
source=zdoc_local_llm_preview_isolated_safe_endpoint_fake
model=fake-local-llm
preview_type=safe_endpoint_preview
endpoint_path=/local-llm/preview-safe
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
downloads_models=false
pulls_models=false
```

Enabled scenario conclusion:

```text
passed with limitation: the isolated safe endpoint remained on the existing fake-only safe helper path. It did not call the real-Ollama adapter generate path even with ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true. This is safe and no-write, but it does not prove end-to-end real model preview through the endpoint.
```

## 8. Requested and forbidden endpoints

Requested endpoint:

```text
POST /local-llm/preview-safe
```

Forbidden endpoints were not requested:

```text
/generate
/export_docx
/review/apply
```

Ollama endpoint requested:

```text
GET http://127.0.0.1:11434/api/tags
```

Ollama generate endpoints were not requested:

```text
/api/generate
/api/chat
```

## 9. Artifact and write verification

Pre-smoke artifact state:

```text
output MISSING
job MISSING
export MISSING
```

Post-smoke artifact state:

```text
output MISSING
job MISSING
export MISSING
```

No `output/`, `job/`, or `export/` writes were observed.

No DOCX / JSON / Markdown formal export was observed.

No ZBid formal writeback was observed.

## 10. Process shutdown and port cleanup

FastAPI disabled scenario:

```text
PID 48067 stopped
127.0.0.1:18750 released
```

FastAPI enabled scenario:

```text
PID 48135 stopped
127.0.0.1:18750 released
```

Ollama serve:

```text
PID 48013 stopped because it was started by this step
127.0.0.1:11434 released
```

Final listener checks:

```text
127.0.0.1:18750 no listener
127.0.0.1:11434 no listener
```

## 11. No-generation-chain verification

No request was made to:

```text
/generate
```

The endpoint response reported:

```text
calls_generate_route=false
triggers_generation_chain=false
affects_generation=false
```

No formal generation job or generated section artifact was created.

## 12. No-export-chain verification

No request was made to:

```text
/export_docx
```

The endpoint response reported:

```text
calls_export_docx_route=false
triggers_export_chain=false
affects_export=false
```

No DOCX / JSON / Markdown formal export artifact was created.

## 13. No-ZBid-writeback verification

No request was made to:

```text
/review/apply
```

The endpoint response reported:

```text
calls_review_apply_route=false
affects_zbid_writeback=false
```

No ZBid formal writeback was connected or observed.

## 14. Final git state before commit

Before this report was committed, the only intended changed file was:

```text
docs/zdoc-real-ollama-preview-runtime-smoke-report.md
```

No code files were modified.

No test files were modified.

## 15. Risk statement

This smoke confirms:

- Ollama was reachable on loopback during the smoke;
- local model `qwen3:0.6b` existed;
- the isolated safe endpoint remained preview-only and no-write;
- disabled behavior returned disabled;
- enabled endpoint behavior returned ok;
- no high-risk route was requested;
- no `output/job/export` write occurred;
- all step-started service processes were stopped.

The key limitation is:

```text
The current isolated safe endpoint still routes to the fake-only safe helper and does not call the real-Ollama adapter generate path. This step does not prove end-to-end real model preview through /local-llm/preview-safe.
```

Future work must not treat this as authorization to connect the formal generation chain, export chain, or ZBid writeback. Any endpoint wiring from the safe endpoint to the real adapter requires a separate design, deterministic tests, smoke, and ChatGPT review.
