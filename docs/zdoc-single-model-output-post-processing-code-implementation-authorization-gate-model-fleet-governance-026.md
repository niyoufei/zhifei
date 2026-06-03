# MODEL-FLEET-GOVERNANCE-026: Single-Model Output Post-Processing Code Implementation Authorization Gate

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `c77f1f64a66abd4a3901c1a31bfa890fde14123d`
- Starting tag at HEAD: not queried because this node's allowed command list did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-025-SAFE-CODE-SURFACE-REVIEW-RETRY`
- Previous decision:

  `SAFE CODE SURFACE REVIEW COMPLETED / IMPLEMENTATION SURFACE IDENTIFIED / NO CODE CHANGE / NO TRIAL AUTHORIZED`

This node is a docs-only code implementation authorization gate.

This node does not modify code, does not add code files, does not modify tests, does not modify frontend, backend, adapter, route, helper, `main.py`, config, JSON, or business files, does not run tests or builds, does not run Ollama, does not execute any Ollama command, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not use real project materials, real tender documents, real construction organization design text, real business data, or real model output full text, does not generate images, does not call image generation tools or image models, and does not enter real use, trial, preview, or production paths.

## 2. Inputs Reviewed

The following prescribed docs files were read:

1. `docs/zdoc-single-model-output-post-processing-safe-code-surface-review-retry-model-fleet-governance-025.md`
2. `docs/zdoc-single-model-output-post-processing-code-surface-review-kg-read-blocked-audit-model-fleet-governance-025.md`
3. `docs/zdoc-single-model-output-post-processing-implementation-authorization-gate-model-fleet-governance-024.md`
4. `docs/zdoc-single-model-output-post-processing-smoke-test-execution-record-model-fleet-governance-023.md`
5. `docs/zdoc-single-model-output-post-processing-authorization-gate-model-fleet-governance-022.md`
6. `docs/zdoc-single-model-output-format-control-smoke-test-execution-record-model-fleet-governance-021.md`

No real KG file body content was read.

No real KG JSON was parsed.

No `知识图谱/**` file was read.

No `AI知识图谱大全/**` file was read.

No `output/**`, `job/**`, or `export/**` file was read.

## 3. Safe Surface Review Result

`MODEL-FLEET-GOVERNANCE-025-SAFE-CODE-SURFACE-REVIEW-RETRY` used a constrained safe file allowlist.

It did not use full-repository `rg`.

It did not perform broad text search.

It did not read real KG.

It did not parse real KG JSON.

It did not read `知识图谱/**`.

It did not read `AI知识图谱大全/**`.

It did not read `output/**`, `job/**`, or `export/**`.

The safe review identified the following backend candidate surfaces:

1. `backend/app/routers/local_trial_preview_only.py`
   - Clearest preview-only / no-write response assembly surface.
   - Candidate location for bounded post-processing metadata such as `cleaning_applied`, `warnings`, `cleaned_text`, and `blocked_reasons`.
2. `backend/app/routers/local_llm_preview_safe.py`
   - Secondary safe endpoint surface.
   - Contains safe endpoint flag handling and local text cleaning helpers.
   - Higher care is required because it is closer to a local LLM preview bridge.
3. `backend/zhifei_autoplan/ollama_preview.py`
   - Local LLM / Ollama preview response normalization and feature-flag surface.
   - Higher risk for first implementation unless a later node explicitly authorizes this surface.
4. `backend/zhifei_autoplan/preview_advisory_quality_gate.py`
   - Candidate surface for failure blocking, warnings, and response-mode validation.
5. `backend/zhifei_autoplan/zbid_isolation_guard.py`
   - Downstream isolation and blocked-reason surface.
   - High proximity to isolation enforcement, so it should not be the first implementation surface without explicit authorization.
6. `backend/app/main.py`
   - Route registration surface.
   - It should be avoided for the first implementation unless explicitly required by a later code node.

Frontend surface result:

- No frontend implementation surface was identified within the safe allowlist in `MODEL-FLEET-GOVERNANCE-025-SAFE-CODE-SURFACE-REVIEW-RETRY`.
- This node does not infer or authorize an unknown frontend surface.

Tests and synthetic fixtures identified:

1. `backend/tests/test_local_trial_preview_only_route.py`
2. `backend/tests/test_local_llm_preview_safe_endpoint.py`
3. `backend/tests/test_preview_advisory_quality_gate.py`

Config and feature-flag surfaces identified:

1. `backend/zhifei_autoplan/ollama_preview.py`
   - `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`
   - `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`
2. `backend/app/routers/local_llm_preview_safe.py`
   - `_safe_endpoint_flag_enabled`
   - `_safe_endpoint_ollama_flag_enabled`

Formal misconnection risk:

- Raw `qwen3:30b` output is not authorized for direct formal-chain use.
- Post-processing must not be connected to formal generation, export, write-back, production, trial, endpoint, real KG, or real project-material paths.
- The lower-risk implementation direction is preview-only / no-write, synthetic-only, feature-flagged, failure-blocking, and separately reviewable.

## 4. Implementation Authorization Boundary

Future implementation, if separately authorized by an explicit ChatGPT implementation instruction, must remain preview-only / no-write.

Future implementation must not connect to formal generation.

Future implementation must not connect to formal export.

Future implementation must not connect to formal write-back.

Future implementation must not write `output`, `job`, or `export`.

Future implementation must not read or parse real KG.

Future implementation must not read `知识图谱/**` or `AI知识图谱大全/**`.

Future implementation must not run the ZDoc service.

Future implementation must not access endpoints.

Future implementation must not run Ollama.

Future implementation must not enter ZDoc preview, trial, or production paths.

Future implementation must not use real project materials, real tender documents, real construction organization design text, real business data, or real model output full text.

Future implementation must include a disable switch or remain behind an existing explicit flag boundary.

Future implementation must block on post-processing failure instead of passing polluted or ambiguous output downstream.

Future implementation must keep rollback simple by limiting the first code change to the smallest viable surface.

## 5. Candidate Implementation Scope

The candidate implementation scope for a later node is:

1. A small tool function or helper that removes ANSI / terminal control sequences, strips obvious `Thinking` / self-check traces, extracts the final target body, and reports bounded cleaning metadata.
2. A preview-only / no-write adapter path that calls the helper only inside the authorized preview boundary and never writes formal outputs.
3. A config or existing feature-flag switch that keeps the behavior disabled or explicitly gated until reviewed.
4. Synthetic fixture tests using dummy / non-project / non-KG / non-business samples only.

The expected bounded metadata shape remains:

```text
raw_text
cleaned_text
extracted_payload
cleaning_applied
warnings
blocked_reasons
```

This node does not modify code.

This node does not add a helper.

This node does not modify routes.

This node does not modify adapters.

This node does not modify tests.

This node does not modify config.

## 6. Future Allowed Code Implementation Boundary

Recommended future code node:

`MODEL-FLEET-GOVERNANCE-027-SINGLE-MODEL-OUTPUT-POST-PROCESSING-CODE-IMPLEMENTATION`

That future node may proceed only under an explicit ChatGPT implementation instruction.

That future node may read prescribed docs.

That future node may use the safe surfaces identified in `MODEL-FLEET-GOVERNANCE-025-SAFE-CODE-SURFACE-REVIEW-RETRY`.

That future node may make the minimal necessary code change for preview-only / no-write post-processing.

That future node may add or modify minimal synthetic tests that use only dummy / non-project / non-KG / non-business text.

That future node must not run Ollama.

That future node must not run the ZDoc service.

That future node must not access endpoints.

That future node must not read or parse real KG.

That future node must not trigger generation / export / write-back.

That future node must not write `output`, `job`, or `export`.

That future node must not use real project materials, real tender documents, real construction organization design text, real business data, or real model output full text.

That future node must not enter real use or trial.

That future node must stop for review after completing only the authorized implementation boundary.

The safe file allowlist discipline from `MODEL-FLEET-GOVERNANCE-025-SAFE-CODE-SURFACE-REVIEW-RETRY` must continue.

## 7. Future Prohibited Boundary

Future work remains prohibited from:

1. Formal generation.
2. Formal export.
3. Formal write-back.
4. `output`, `job`, or `export` writes.
5. Real KG reading.
6. Real KG parsing.
7. Endpoint access.
8. ZDoc service execution.
9. Ollama execution.
10. Any Ollama command.
11. Real project materials.
12. Real tender documents.
13. Real construction organization design text.
14. Real business data.
15. Real model output full text.
16. Image generation.
17. Image generation tools.
18. Image models.
19. Concurrency testing.
20. Performance testing.
21. Real use.
22. Trial.
23. ZDoc preview path.
24. ZDoc production path.
25. Multi-model expansion.
26. Model deletion, replacement, or upgrade.
27. `latest` pointer modification.

## 8. Current Decision

`CODE IMPLEMENTATION AUTHORIZATION GATE FORMED / NO CODE CHANGE IN THIS NODE / NO TRIAL AUTHORIZED`

This decision forms only the code implementation authorization gate for a later node.

This decision does not modify code in this node.

This decision does not authorize code execution in this node.

This decision does not authorize tests or builds in this node.

This decision does not authorize Ollama execution.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG access.

This decision does not authorize generation / export / write-back.

This decision does not authorize real use or trial.

## 9. NO-GO Statements

`NO-GO FOR CODE CHANGE IN THIS NODE`

`NO-GO FOR TEST CHANGE IN THIS NODE`

`NO-GO FOR TEST EXECUTION IN THIS NODE`

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR ANY OLLAMA COMMAND`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR ENDPOINT ACCESS`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR GENERATION / EXPORT / WRITE-BACK`

`NO-GO FOR OUTPUT / JOB / EXPORT WRITE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

## 10. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-027-SINGLE-MODEL-OUTPUT-POST-PROCESSING-CODE-IMPLEMENTATION`

That next node must not execute automatically.

That next node must proceed only under an explicit ChatGPT implementation instruction.

That next node must remain preview-only / no-write.

That next node must not connect post-processing to formal generation, export, or write-back.

That next node must not run Ollama.

That next node must not run the ZDoc service.

That next node must not access endpoints.

That next node must not read or parse real KG.

That next node must not write `output`, `job`, or `export`.

That next node must not use real project materials, real tender documents, real construction organization design text, real business data, or real model output full text.

That next node must not generate images or call image generation tools or image models.

That next node must not enter real use, trial, ZDoc preview, or production paths.

MODEL-FLEET-GOVERNANCE-026 stops here and waits for human review.
