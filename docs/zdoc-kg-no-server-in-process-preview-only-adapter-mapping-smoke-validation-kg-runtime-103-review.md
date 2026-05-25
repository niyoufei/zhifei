# KG-RUNTIME-103 ZDoc KG no-server in-process preview-only adapter mapping smoke validation

## Scope

- Stage: KG-RUNTIME-103.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.
- Start HEAD: `21a5ed57524c99bf023da824759824b350fb27da`.
- Start baseline tag: `v0.1.485-zdoc-kg-preview-only-mapping-smoke-gate`.
- Baseline note: the local HEAD matched the requested baseline. Local lookup did not show the baseline tag; remote tag lookup was not retried with broader permissions after the sandbox rejected SSH access to `github.com`. The user-provided baseline states that the remote tag already points to the requested HEAD.
- Allowed output of this stage: this docs-only review file only.
- KG-RUNTIME-103 does not enter KG-RUNTIME-104.

## Smoke Method

Executed exactly one no-server in-process Python mapping smoke with `PYTHONDONTWRITEBYTECODE=1`.

Direct helper / adapter mapping calls used:

- `classify_content_safe_fields`
- `filter_preview_only_fields`
- `filter_audit_only_fields`
- `build_preview_only_payload`
- `build_preview_only_adapter_mapping`

The smoke used a synthetic already-content-safe response shape. It did not use a real KG file, did not parse a real KG JSON file, did not start `uvicorn`, did not bind a TCP port, and did not access `127.0.0.1`.

During the actual mapping calls, the smoke installed guards that fail on file body reads, `Path.read_text`, `Path.read_bytes`, `json.load`, `json.loads`, or socket creation. The guarded mapping call completed successfully.

## Smoke Result

Mapping smoke conclusion: PASS.

Observed smoke output:

- `KG_RUNTIME_103_MAPPING_SMOKE=PASS`
- `input_shape=synthetic_content_safe_response`
- `preview_only_keys=structural_profile_contract,structural_profile_only,structural_profile_summary,structure_contract,structure_read_only,structure_summary`
- `audit_only_keys=adapter_contract_code,allowlist_status,authorized_target_hit_status,feature_flag_status,manual_trigger_status,overlap_check_result,real_kg_read_only_status,route_contract_code,validation_result`
- `prohibited_values_output=false`
- `forbidden_sentinel_leaked=false`
- `file_io_json_parse_socket_guard=pass`

## Preview-Only Classification

PASS: `preview_only` only contained the allowed top-level mapping classes:

- `structure_read_only`
- `structure_summary`
- `structural_profile_only`
- `structural_profile_summary`

PASS: `preview_only` contract mapping only retained safe enum / numeric code fields from `structure_contract` and `structural_profile_contract`.

PASS: `preview_only` did not contain prohibited synthetic sentinel values.

PASS: `preview_only` did not contain KG scalar value, list item content, dict value content, business body, entity body, knowledge entry body, prompt content, system instruction content, evidence content, scoring content, raw KG text fragment, or reverse-inference text.

## Audit-Only Classification

PASS: `audit_only` only contained the allowed audit / status / code classes:

- `feature_flag_status`
- `manual_trigger_status`
- `real_kg_read_only_status`
- `authorized_target_hit_status`
- `allowlist_status`
- `route_contract_code`
- `adapter_contract_code`
- `validation_result`
- `overlap_check_result`

PASS: `audit_only` did not contain KG body output, generation material, export material, writeback material, evidence material, or scoring material.

## Prohibited Classification

PASS: `prohibited` only preserved the forbidden-category list and `values_output=false`.

The preserved prohibited categories are:

- KG scalar value.
- list item 内容.
- dict value 内容.
- 业务正文.
- 实体正文.
- 知识条目正文.
- prompt.
- system instruction.
- evidence.
- scoring.
- 原始 KG 文本片段.
- 可反推 KG 正文的字符串.

PASS: `prohibited` did not enter `preview_only`.

PASS: `prohibited` did not output actual KG values, KG text, prompt content, evidence content, or scoring content.

## Non-Execution Record

Not performed in KG-RUNTIME-103:

- No code modification.
- No adapter modification.
- No route modification.
- No helper modification.
- No `main.py` modification.
- No frontend modification.
- No tests modification.
- No config modification.
- No JSON modification.
- No directory scan rerun.
- No real KG file body read.
- No real KG JSON parse.
- No service start.
- No TCP port bind.
- No `127.0.0.1` access.
- No endpoint call.
- No `/health` call.
- No `/kg/read-only-preview` call.
- No `/generate` call.
- No `/export_docx` call.
- No `/review/apply` call.
- No ZBid writeback.
- No `output` write.
- No `job` write.
- No `export` write.
- No Ollama run.
- No RAG integration.
- No prompt registry integration.
- No system instruction registry integration.
- No CI integration.
- No evidence use.
- No scoring use.
- No ZDoc integration.
- No real-use stage.
- No trial-use stage.

## Pycache Record

`PYTHONDONTWRITEBYTECODE=1` was used for the smoke.

Targeted pre/post checks showed the already-existing directories below kept unchanged mtimes:

- `backend/__pycache__`: `1779633631`
- `backend/app/routers/__pycache__`: `1779633630`

No new `.pyc` / `__pycache__` item was attributed to KG-RUNTIME-103.

## Final KG-RUNTIME-103 Conclusion

PASS: KG-RUNTIME-103 completed the no-server in-process preview-only adapter mapping smoke validation.

PASS: The smoke used direct helper / adapter mapping calls and a synthetic already-content-safe response shape.

PASS: `preview_only`, `audit_only`, and `prohibited` classifications matched the content-safe output contract for this stage.

PASS: KG-RUNTIME-103 did not enter ZDoc KG integration, real use, trial use, or KG-RUNTIME-104.
