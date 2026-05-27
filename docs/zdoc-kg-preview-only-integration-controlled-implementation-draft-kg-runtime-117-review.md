# ZDoc KG preview-only integration controlled implementation draft review - KG-RUNTIME-117

## 1. Stage conclusion

- KG-RUNTIME-117 result: completed as a controlled implementation draft only.
- This stage only prepares an already content-safe / preview-only KG response shape for internal ZDoc preview-only consumption.
- This stage does not mean ZDoc has been integrated.
- This stage does not mean the feature has entered real use.
- This stage does not mean the feature has entered trial use.
- KG-RUNTIME-118 is still required for static compliance and no-output-chain review.

## 2. Actual file changes

Modified code files:

- `backend/kg_content_safe_output_contract.py`
- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`

Added review document:

- `docs/zdoc-kg-preview-only-integration-controlled-implementation-draft-kg-runtime-117-review.md`

Scope confirmation:

- Only authorized helper / adapter / route files were modified.
- `backend/app/main.py` was not modified.
- No frontend file was modified.
- No tests file was modified.
- No config file was modified.
- No JSON file was modified.

## 3. Runtime and data-access boundary

- No real KG body content was read.
- No real KG JSON was parsed.
- No service was run.
- No endpoint was called.
- `/health` was not called.
- `/kg/read-only-preview` was not called.
- `pytest` was not run.
- `py_compile` was not run.
- No directory scan was run, including `find ..`, `find /`, or `find AI知识图谱大全`.
- Ollama was not run.
- `/generate` was not triggered.
- `/export_docx` was not triggered.
- `/review/apply` was not triggered.
- ZBid writeback was not triggered.
- No `output/`, `job/`, or `export/` content was written.
- RAG was not integrated.
- Prompt registry was not integrated.
- System instruction registry was not integrated.
- CI was not integrated.

## 4. Added or adjusted draft fields and functions

New helper constants:

- `ZDOC_PREVIEW_ONLY_INTEGRATION_SOURCE_CODE`
- `ZDOC_PREVIEW_ONLY_INTEGRATION_POLICY`
- `ZDOC_PREVIEW_ONLY_DEFAULT_OFF_POLICY`
- `ZDOC_PREVIEW_ONLY_MANUAL_TRIGGER_POLICY`
- `ZDOC_PREVIEW_ONLY_OUTPUT_CHAIN_POLICY`

New helper / adapter functions:

- `build_zdoc_preview_only_payload`
- `build_zdoc_preview_only_adapter_payload`

New adapter / route passthrough field:

- `zdoc_preview_only_integration`

The route change is a metadata passthrough only. It does not call an endpoint, start a service, trigger a generation chain, trigger an export chain, or write back to ZBid.

## 5. Reused verified content-safe / preview-only structures

This draft reuses the established content-safe / preview-only structure family from KG-RUNTIME-100 / 105 / 108 / 114:

- `preview_only_response`
- `preview_contract`
- `preview_only_mapping`
- `audit_only_mapping`
- `prohibited_mapping`

This draft also reuses the established helper path:

- `classify_content_safe_fields`
- `filter_preview_only_fields`
- `filter_audit_only_fields`
- `build_preview_only_payload`
- `build_preview_only_adapter_mapping`

The new ZDoc draft helper delegates to the existing preview-only payload builder and does not introduce a KG value extraction path.

## 6. Preview-only field list

Allowed preview-only output remains limited to:

- `structure_read_only`
- `structure_summary`
- `structural_profile_only`
- `structural_profile_summary`
- `structure_contract` safe enum / numeric-code fields
- `structural_profile_contract` safe enum / numeric-code fields
- `preview_contract` safe fields
- `preview_only_mapping`

Confirmed: prohibited fields do not enter `preview_only_mapping`.

Confirmed: preview-only output does not include KG scalar values, list item content, dict value content, business body text, entity body text, knowledge-entry body text, prompt text, system instruction text, evidence, scoring, original KG text snippets, or strings that can reverse-infer KG body content.

## 7. Audit-only field list

Allowed audit-only output remains limited to:

- feature flag status
- manual trigger status
- real KG read-only status
- authorized target hit status
- `allowlist_status`
- route / adapter contract code
- validation result
- overlap check result

## 8. Prohibited field list

The prohibited category remains a prohibition list only and must not contain KG values:

- KG scalar value
- list item 内容
- dict value 内容
- 业务正文
- 实体正文
- 知识条目正文
- prompt
- system instruction
- evidence
- scoring
- 原始 KG 文本片段
- 可反推 KG 正文的字符串

Confirmed: `prohibited_mapping` is returned only as the prohibited category list and is not copied into preview-only output.

## 9. Downstream boundary

- No `/generate` integration was added.
- No `/export_docx` integration was added.
- No `/review/apply` integration was added.
- No output chain integration was added.
- No export chain integration was added.
- No writeback integration was added.
- No evidence integration was added.
- No scoring integration was added.

## 10. Remaining required review

KG-RUNTIME-118 is still required to perform static compliance and no-output-chain review.

This KG-RUNTIME-117 artifact is only a ZDoc preview-only integration draft. It cannot be used to claim ZDoc integration completion, real use, or trial use.
