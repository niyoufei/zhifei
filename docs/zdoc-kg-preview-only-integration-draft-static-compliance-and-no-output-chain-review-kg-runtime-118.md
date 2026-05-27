# ZDoc KG preview-only integration draft static compliance and no-output-chain review - KG-RUNTIME-118

## 1. Review conclusion

- KG-RUNTIME-118 result: static compliance review completed.
- Reviewed target: KG-RUNTIME-117 ZDoc KG preview-only integration controlled implementation draft.
- Review type: docs-only, static review, no-runtime review, no-output-chain review.
- Conclusion: the KG-RUNTIME-117 draft remains a preview-only, content-safe, default-off, manual-trigger, no-runtime, no-output-chain, no-generation, no-export, no-writeback, no-evidence, no-scoring, no-RAG, no-registry draft.
- This review does not mean ZDoc has been integrated.
- This review does not mean the feature has entered real use.
- This review does not mean the feature has entered trial use.
- KG-RUNTIME-119 is still required as the preview-only integration frozen audit and no-server smoke authorization gate.

## 2. Static evidence reviewed

Reviewed only repository metadata and the authorized KG-RUNTIME-117 files:

- `backend/kg_content_safe_output_contract.py`
- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`
- `docs/zdoc-kg-preview-only-integration-controlled-implementation-draft-kg-runtime-117-review.md`

KG-RUNTIME-117 file-scope evidence:

- `git show --name-only --format=fuller HEAD` shows only the helper, adapter, route, and KG-RUNTIME-117 review document were changed.
- `git diff --name-only HEAD^ HEAD` shows only:
  - `backend/app/routers/kg_read_only_preview.py`
  - `backend/kg_content_safe_output_contract.py`
  - `backend/kg_read_only_preview_adapter.py`
  - `docs/zdoc-kg-preview-only-integration-controlled-implementation-draft-kg-runtime-117-review.md`

## 3. Authorized scope review

Confirmed:

- KG-RUNTIME-117 only modified the authorized helper / adapter / route files and one review document.
- `backend/app/main.py` was not modified.
- No frontend file was modified.
- No tests file was modified.
- No config file was modified.
- No JSON file was modified.
- KG-RUNTIME-118 only adds this docs-only review file.

## 4. Added or adjusted KG-RUNTIME-117 integration draft surface

Confirmed KG-RUNTIME-117 added or adjusted:

- `build_zdoc_preview_only_payload`
- `build_zdoc_preview_only_adapter_payload`
- `zdoc_preview_only_integration`

Confirmed these are draft preview-only integration surfaces only:

- `build_zdoc_preview_only_payload` builds a ZDoc preview-only draft payload from an already content-safe response.
- `build_zdoc_preview_only_adapter_payload` enriches an already content-safe preview response with audit-only status fields and delegates to the ZDoc helper.
- `zdoc_preview_only_integration` is present only as an adapter output field and route metadata passthrough field.

## 5. Reused helper review

Confirmed the KG-RUNTIME-117 draft reuses existing helper paths:

- `build_preview_only_payload`
- `build_preview_only_adapter_mapping`
- `classify_content_safe_fields`
- `filter_preview_only_fields`
- `filter_audit_only_fields`

The ZDoc draft helper delegates to the existing preview-only payload builder. It does not introduce a new KG value extraction path, a new body text path, a new evidence path, or a new scoring path.

## 6. Adapter and route passthrough review

Confirmed:

- `zdoc_preview_only_integration` is added to the adapter output whitelist.
- The adapter builds `zdoc_preview_only_integration` beside the existing `preview_only_response` field.
- The route adds `zdoc_preview_only_integration` to `KG_READ_ONLY_PREVIEW_REAL_KG_METADATA_FIELDS`.
- The route loop only copies the field from `adapter_result` into route metadata when the adapter already returned it.
- The route change does not start a service, call another endpoint, call `/generate`, call `/export_docx`, call `/review/apply`, trigger an output chain, trigger an export chain, or write back to ZBid.

## 7. Preview-only and content-safe output review

Confirmed:

- Preview-only output is derived from the established content-safe / preview-only response structure.
- `filter_preview_only_fields` only keeps allowlisted preview-only top-level fields and safe contract fields.
- `filter_audit_only_fields` only keeps audit-only response fields.
- `build_preview_only_payload` separates preview-only, audit-only, prohibited, and downstream prohibition categories.
- `build_zdoc_preview_only_payload` reuses the preview-only mapping produced by `build_preview_only_payload`.
- `prohibited` fields are not copied into `preview_only_mapping`.
- Preview-only output does not include KG scalar values.
- Preview-only output does not include KG body text, business body text, entity body text, knowledge-entry body text, original KG text snippets, or strings that can reverse-infer KG body content.
- Preview-only output does not include evidence content.
- Preview-only output does not include scoring content.

## 8. No-output-chain review

Confirmed no KG-RUNTIME-117 change connects the draft to:

- frontend
- `/generate`
- `/export_docx`
- `/review/apply`
- output write
- job write
- export write
- ZBid writeback
- evidence
- scoring
- RAG
- prompt registry
- system instruction registry
- CI

The existing route response metadata continues to declare output-chain flags as false, including generation, export, review apply, writeback, evidence, scoring, RAG, prompt registry, and system instruction registry allowances.

## 9. Runtime and data-access review performed in KG-RUNTIME-118

Confirmed for this review:

- No service was run.
- No port was accessed.
- No endpoint was called.
- `/health` was not called.
- `/kg/read-only-preview` was not called.
- `/generate` was not triggered.
- `/export_docx` was not triggered.
- `/review/apply` was not triggered.
- ZBid writeback was not triggered.
- No `output/`, `job/`, or `export/` content was written.
- Ollama was not run.
- No real KG file body content was read.
- No real KG JSON was parsed.
- No directory scan command was run, including `find ..`, `find /`, or `find AI知识图谱大全`.
- `pytest` was not run.
- `py_compile` was not run.

## 10. Remaining boundary

- KG-RUNTIME-118 is only a static compliance and no-output-chain review.
- KG-RUNTIME-118 does not authorize ZDoc integration completion.
- KG-RUNTIME-118 does not authorize real use.
- KG-RUNTIME-118 does not authorize trial use.
- KG-RUNTIME-118 does not authorize frontend integration.
- KG-RUNTIME-118 does not authorize generation-chain integration.
- KG-RUNTIME-118 does not authorize export-chain integration.
- KG-RUNTIME-118 does not authorize writeback-chain integration.
- KG-RUNTIME-118 does not authorize evidence or scoring use.
- KG-RUNTIME-118 does not enter KG-RUNTIME-119.
- KG-RUNTIME-119 remains required before any no-server smoke authorization gate decision.
