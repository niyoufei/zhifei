# MODEL-FLEET-GOVERNANCE-025: Safe Code Surface Review Retry

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `199abe0fff541a200cc416e4dc292503ea9efd63`
- Starting tag at HEAD: not queried because this node's allowed command list did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-025-KG-READ-BLOCKED-AUDIT`
- Previous decision:

  `CODE SURFACE REVIEW BLOCKED BY KG READ BOUNDARY / AUDIT RECORDED / NO CODE CHANGE`

This node is a safe read-only code surface review retry and docs-only record.

This node does not modify code, does not add code files, does not modify tests, does not run tests, does not run Ollama, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not read unknown `.json` file bodies, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not generate images, and does not enter real use or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-output-post-processing-code-surface-review-kg-read-blocked-audit-model-fleet-governance-025.md`
2. `docs/zdoc-single-model-output-post-processing-implementation-authorization-gate-model-fleet-governance-024.md`
3. `docs/zdoc-single-model-output-post-processing-smoke-test-execution-record-model-fleet-governance-023.md`
4. `docs/zdoc-single-model-output-post-processing-authorization-gate-model-fleet-governance-022.md`
5. `docs/zdoc-single-model-output-format-control-smoke-test-execution-record-model-fleet-governance-021.md`
6. `docs/zdoc-single-model-output-format-control-authorization-gate-model-fleet-governance-020.md`

No real KG file was read.

No real KG JSON was read or parsed.

No `知识图谱/**` file was read.

No `AI知识图谱大全/**` file was read.

No unknown `.json` file body was read.

No `output/**`, `job/**`, or `export/**` file was read.

## 3. Safe Review Method

This node did not use broad repository-wide `rg`.

This node did not execute `rg` against `.`.

This node used an allowlist file discovery method limited to:

1. `backend`
2. `frontend`
3. `tests`
4. `config`

The allowlist only considered source-like file extensions:

1. `.py`
2. `.ts`
3. `.tsx`
4. `.js`
5. `.jsx`
6. `.md`

The allowlist excluded paths containing:

1. `知识图谱`
2. `AI知识图谱大全`
3. `KG`
4. `kg`
5. `graph`
6. `output`
7. `job`
8. `export`
9. `node_modules`
10. `__pycache__`
11. `.pyc`

The actual keyword search was executed only against the filtered allowlist file list.

The actual keyword search also excluded `backend/data/uploads/**` from inspection because that path is data-like rather than source-like.

This node only read a small number of clearly safe source and test files with bounded `sed -n '1,220p'`.

This node did not read unknown `.json` file bodies.

This node did not read any suspicious KG / real-data path.

## 4. Candidate Backend Surfaces

### `backend/app/routers/local_trial_preview_only.py`

- Related keywords: `local-trial`, `preview_only`, `no_write`, `preview_packet`, `validator_result`, `blocked_reasons`, `output_write_allowed`, `writes_output`, `writes_job`, `writes_export`
- Related route: `/local-trial/preview-only`
- Relationship to post-processing: this is the clearest preview-only / no-write response assembly point. A future implementation could attach post-processing metadata such as `cleaning_applied`, `warnings`, `cleaned_text`, and `blocked_reasons` to preview-only metadata only.
- Formal chain proximity: low. The reviewed code returns explicit false flags for generation, export, review/apply, write-back, output/job/export writes, Ollama calls, and external model calls.
- Future touch recommendation: recommended as a first-choice preview-only adapter surface, but only under a later implementation authorization node.

### `backend/app/routers/local_llm_preview_safe.py`

- Related keywords: `preview-safe`, `preview_only`, `no_write`, `_clean_endpoint_text`, `SAFE_ENDPOINT_FORMAL_OUTPUT_FIELDS`, `calls_export_docx_route`, `triggers_generation_chain`, `writes_output`, `writes_job`, `writes_export`, `feature_flag_disabled`
- Related route: `/local-llm/preview-safe`
- Relationship to post-processing: this file already normalizes endpoint text and wraps preview-safe responses. A future implementation could apply post-processing to safe preview helper / adapter output before the response is returned, while keeping formal output fields blocked.
- Formal chain proximity: medium. The safe endpoint is isolated and default-off, but it can bridge to a real adapter when separately enabled.
- Future touch recommendation: possible secondary surface. Limit any future changes to default-off preview-only behavior and never enable real runtime paths in the same node.

### `backend/zhifei_autoplan/ollama_preview.py`

- Related keywords: `LOCAL_LLM_PREVIEW_FLAG`, `LOCAL_LLM_OLLAMA_PREVIEW_FLAG`, `_clean_text`, response mode constants, `thinking_only_fallback`, `preview_only`, `no_write`, `writes_output`, `writes_job`, `writes_export`
- Relationship to post-processing: this file contains local LLM / Ollama preview response normalization and default-off feature flags. It is relevant to future post-processing of local model preview responses.
- Formal chain proximity: medium to high. It is close to local model adapter behavior and real transport gating, even though safety flags indicate preview-only / no-write behavior.
- Future touch recommendation: avoid as first implementation target unless the next implementation node explicitly authorizes it. Prefer a small standalone helper plus preview-only route integration first.

### `backend/zhifei_autoplan/preview_advisory_quality_gate.py`

- Related keywords: `preview_only`, `no_write`, `FORMAL_GENERATION_ALLOWED = False`, `WRITEBACK_ALLOWED = False`, `EXPORT_ALLOWED = False`, `thinking_only_fallback`, `blockers`, `warnings`
- Relationship to post-processing: this file is a candidate for validating post-processed preview advisory results and blocking unsafe response modes or failed cleaning outcomes.
- Formal chain proximity: medium. It contains formal-chain guard fields and formal result field detection.
- Future touch recommendation: suitable for failure blocking / warning propagation only after a minimal cleaning helper exists.

### `backend/zhifei_autoplan/zbid_isolation_guard.py`

- Related keywords: `blocked_reasons`, `response_mode`, `thinking_only_fallback`, `formal_generation_requested`, `export_docx_request_triggered`, `output_write_allowed`
- Relationship to post-processing: this file is relevant to final downstream isolation and blocked reason semantics if post-processing output ever approaches ZBid preview/write-back guard boundaries.
- Formal chain proximity: high because it is close to ZBid write-back isolation semantics.
- Future touch recommendation: avoid in the first implementation. Use it only as a reference or later integration point after preview-only post-processing is proven.

### `backend/app/main.py`

- Related keywords: router registration for `local_llm_preview_safe_router` and `local_trial_preview_only_router`
- Relationship to post-processing: confirms preview-safe and local-trial preview-only routes are registered.
- Formal chain proximity: high as an application entrypoint that also references broad system capabilities.
- Future touch recommendation: avoid for the first implementation unless route registration is explicitly required.

Unverified backend areas:

Formal generation / export / write-back code surfaces were only identified as risk-adjacent from safe allowlist keyword hits and were not opened as implementation targets in this node. Direct implementation in those paths is not recommended.

## 5. Candidate Frontend Surfaces

No candidate frontend file under the allowed `frontend/**` allowlist was found or read in this node.

Candidate frontend preview-only display surfaces were not identified in this safe read-only review.

It was not established in this node whether a frontend component exists for displaying `cleaning_applied`, `warnings`, or `cleaned_text`.

`未在本节点安全只读复核中查明`

Future frontend review must use an explicit frontend allowlist and must not broaden into repository-wide search.

## 6. Candidate Test / Fixture Surfaces

### `backend/tests/test_local_trial_preview_only_route.py`

- Related keywords: `preview-only`, `no_write`, `blocked_reasons`, formal flags, output/job/export count checks
- Relationship to post-processing: suitable for synthetic fixture tests around preview-only route metadata, `blocked_reasons`, `cleaning_applied`, and no-write guarantees.
- Synthetic fixture suitability: high.
- Formal chain proximity: low to medium; the tests explicitly assert no formal route or write-back module usage.

### `backend/tests/test_local_llm_preview_safe_endpoint.py`

- Related keywords: `preview-safe`, `feature_flag_disabled`, `preview_only`, `no_write`, `calls_ollama`, `writes_output`, `writes_job`, `writes_export`, `FORMAL_RESULT_FIELDS`
- Relationship to post-processing: suitable for synthetic fixture tests of a disabled-by-default post-processing flag and safe endpoint response metadata.
- Synthetic fixture suitability: high.
- Formal chain proximity: medium because the endpoint can represent fake and real adapter bridge states, but the tests assert default-off and no-write behavior.

### `backend/tests/test_preview_advisory_quality_gate.py`

- Related keywords: `thinking_only_fallback`, `warnings`, `blockers`, `preview_only`, `no_write`, `affects_generation`, `affects_export`
- Relationship to post-processing: suitable for testing failure blocking, warning propagation, and response-mode handling after cleaning.
- Synthetic fixture suitability: high.
- Formal chain proximity: medium because the quality gate enforces formal-chain ineligibility.

Additional test candidates may exist, but were not opened in this node to keep the safe review bounded.

## 7. Candidate Config / Feature Flag Surfaces

No unknown `.json` config body was read.

Path-level and source-level feature flag candidates were identified:

1. `backend/zhifei_autoplan/ollama_preview.py`
   - `LOCAL_LLM_PREVIEW_FLAG = "ZDOC_LOCAL_LLM_PREVIEW_ENABLED"`
   - `LOCAL_LLM_OLLAMA_PREVIEW_FLAG = "ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED"`
   - Relationship: a future post-processing enable / disable flag could follow the existing environment-variable, default-off pattern.

2. `backend/app/routers/local_llm_preview_safe.py`
   - `_safe_endpoint_flag_enabled()`
   - `_safe_endpoint_ollama_flag_enabled()`
   - Relationship: demonstrates endpoint-level disable switch behavior and default-off safety response handling.

3. `backend/app/main.py`
   - `/config` source code references non-sensitive runtime configuration and environment defaults.
   - Relationship: potential path for future visibility of a flag, but not recommended as a first implementation target.

No `config/**` source-like file was identified in the safe allowlist review.

Unknown `.json` config files were intentionally not read.

## 8. Risk Review

Formal generation / export / write-back risks:

1. `backend/app/routers/actions_bridge.py` appeared in safe keyword results around generation mode, `/review/apply`, and `/export_docx`; this is a formal-chain-adjacent router and should be avoided in the first implementation.
2. `backend/app/routers/zhifei_autoplan.py` appeared in safe keyword results around jobs and export routes; this is formal-chain-adjacent and should be avoided in the first implementation.
3. `backend/app/main.py` is a broad app entrypoint; modifying it risks affecting multiple routes at once.

Output / job / export write risks:

1. Tests already count `output`, `job`, and `export` write surfaces for preview-only routes.
2. Future post-processing must not introduce any file writes to `output`, `job`, or `export`.
3. Future post-processing should return in-memory metadata only.

Real KG read risks:

1. Any path containing `KG`, `kg`, `graph`, `知识图谱`, or unknown `.json` must remain excluded unless separately authorized.
2. `backend/app/main.py` references KG-related capabilities; this file should not be used as a first implementation point.
3. A future safe review must continue to avoid `知识图谱/**`, `AI知识图谱大全/**`, and unknown `.json` bodies.

Endpoint trigger risks:

1. Route files are endpoint surfaces; code changes there can expose behavior immediately if services are run later.
2. Any implementation must remain default-off and preview-only.
3. No future implementation node should run the service or call endpoints unless separately authorized.

Formal-chain misconnection risks:

1. Do not connect cleaned model output to formal generation.
2. Do not connect cleaned model output to export.
3. Do not connect cleaned model output to write-back.
4. Do not fall back to polluted raw output if cleaning fails.
5. Do not treat a cleaned preview as evidence or final business content.

Paths to avoid in the first implementation:

1. `backend/app/routers/actions_bridge.py`
2. `backend/app/routers/zhifei_autoplan.py`
3. `backend/app/main.py`
4. any path containing `KG`, `kg`, `graph`, `知识图谱`, or unknown `.json`
5. any path writing `output`, `job`, or `export`

Recommended preview-only / no-write first surfaces:

1. `backend/app/routers/local_trial_preview_only.py`
2. `backend/app/routers/local_llm_preview_safe.py`
3. a new minimal helper only if the next node explicitly authorizes code changes
4. `backend/tests/test_local_trial_preview_only_route.py`
5. `backend/tests/test_local_llm_preview_safe_endpoint.py`

## 9. Recommended Implementation Path

Recommended next implementation path:

1. Add a minimal post-processing helper function.
2. Keep the helper independent from formal generation / export / write-back.
3. Connect the helper only to preview-only / no-write response assembly.
4. Return bounded metadata such as `cleaning_applied`, `warnings`, `cleaned_text`, `extracted_payload`, and `blocked_reasons`.
5. Add synthetic fixture tests only.
6. Add or reuse a default-off disable flag.
7. Block preview continuation when cleaning fails.
8. Never fall back to polluted raw output.

The implementation must not directly connect to formal generation / export / write-back.

The implementation must not run the ZDoc service.

The implementation must not access endpoints.

The implementation must not read real KG.

The implementation must not parse real KG JSON.

The implementation must not write `output`, `job`, or `export`.

## 10. Current Decision

`SAFE CODE SURFACE REVIEW COMPLETED / IMPLEMENTATION SURFACE IDENTIFIED / NO CODE CHANGE / NO TRIAL AUTHORIZED`

This decision is based on safe allowlist review identifying backend, test, and feature-flag surfaces sufficient for a later implementation authorization gate.

This decision does not authorize code changes in this node.

This decision does not authorize test execution in this node.

This decision does not authorize Ollama execution.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize KG read or parse.

This decision does not authorize generation / export / write-back.

This decision does not authorize output / job / export writes.

This decision does not authorize real use or trial.

## 11. NO-GO Statements

`NO-GO FOR BROAD RG IN THIS NODE`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR CODE CHANGE IN THIS NODE`

`NO-GO FOR TEST EXECUTION IN THIS NODE`

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR ENDPOINT ACCESS`

`NO-GO FOR GENERATION / EXPORT / WRITE-BACK`

`NO-GO FOR OUTPUT / JOB / EXPORT WRITE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR CONCURRENT TEST`

`NO-GO FOR PERFORMANCE TEST`

## 12. Next Recommended Node

Because the safe code surface review identified sufficient implementation surfaces, the recommended next node is:

`MODEL-FLEET-GOVERNANCE-026-SINGLE-MODEL-OUTPUT-POST-PROCESSING-CODE-IMPLEMENTATION-AUTHORIZATION-GATE`

The next node must not automatically modify code unless ChatGPT controller explicitly gives implementation instructions.

The next node must not automatically run ZDoc.

The next node must not access endpoints.

The next node must not read real KG.

The next node must not parse real KG JSON.

The next node must not trigger generation / export / write-back.

The next node must not write `output`, `job`, or `export`.

The next node must not enter real use or trial.

MODEL-FLEET-GOVERNANCE-025-SAFE-CODE-SURFACE-REVIEW-RETRY stops here and waits for human review.
