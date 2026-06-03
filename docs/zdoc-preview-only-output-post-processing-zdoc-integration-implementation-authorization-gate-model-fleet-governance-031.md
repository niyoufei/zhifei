# MODEL-FLEET-GOVERNANCE-031: Preview-Only Output Post-Processing ZDoc Integration Implementation Authorization Gate

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `58c1568f12ba20c98d8e169ff86aa43b9ea50274`
- Starting tag at HEAD: not queried because this node's allowed command list did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-030`
- Previous decision:

  `VALIDATION RESULT REVIEW COMPLETED / ZDOC INTEGRATION AUTHORIZATION GATE FORMED / NO TRIAL AUTHORIZED`

This node is a docs-only ZDoc preview-only / no-write output post-processing integration implementation authorization gate.

This node does not modify code, does not modify tests, does not add code files, does not add test files, does not run tests, does not run Python tests, does not run frontend tests, does not run builds, does not run Ollama, does not execute any Ollama command, does not run the ZDoc service, does not access a real endpoint, does not read or parse real KG, does not trigger formal generation / export / write-back, does not write `output`, `job`, or `export`, does not use real project materials, real tender documents, real construction organization design text, or real business data, does not generate images, does not call image generation tools or image models, and does not enter real use or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-preview-only-validation-result-review-and-zdoc-integration-gate-model-fleet-governance-030.md`
2. `docs/zdoc-preview-only-output-post-processing-validation-execution-record-model-fleet-governance-029.md`
3. `docs/zdoc-output-post-processing-code-review-and-preview-only-validation-gate-model-fleet-governance-028.md`
4. `docs/zdoc-single-model-output-post-processing-code-implementation-record-model-fleet-governance-027.md`
5. `docs/zdoc-single-model-output-post-processing-code-implementation-authorization-gate-model-fleet-governance-026.md`
6. `docs/zdoc-single-model-output-post-processing-safe-code-surface-review-retry-model-fleet-governance-025.md`

The following specified safe code files were read:

1. `backend/app/routers/local_trial_preview_only.py`
2. `backend/tests/test_local_trial_preview_only_route.py`

Additional allowed read-only review commands executed:

```bash
git show --stat --oneline a9c4789aba7c252b88674ca502a1da6e532ac17f
git show --stat --oneline 58c1568f12ba20c98d8e169ff86aa43b9ea50274
```

Reviewed `029` commit stat:

```text
a9c4789 docs: add preview-only output post-processing validation record
1 file changed, 232 insertions(+)
```

Reviewed `030` commit stat:

```text
58c1568 docs: add preview-only validation review and zdoc integration gate
1 file changed, 281 insertions(+)
```

No full-repository `rg` was executed.

No broad search was executed.

No real KG file was read.

No unknown `.json` file body was read.

No `知识图谱/**` or `AI知识图谱大全/**` file was read.

No `output/**`, `job/**`, or `export/**` file was read.

## 3. Validation Result Baseline

`MODEL-FLEET-GOVERNANCE-029` preview-only output post-processing validation passed.

The `029` validation command was:

```bash
python3 -m pytest backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_cleans_synthetic_json backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_extracts_markdown_and_text backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_blocks_failure_and_can_disable
```

The `029` validation result was:

```text
3 passed in 0.11s
```

The validation confirmed:

1. Thinking / self-check traces cleaning.
2. ANSI / terminal control sequence cleaning.
3. JSON target structure extraction.
4. Markdown target structure extraction.
5. Plain text target structure extraction.
6. `cleaning_applied`.
7. `warnings`.
8. `blocked_reasons`.
9. Failure blocking.
10. Disable switch.
11. Preview-only / no-write boundary.

The preview-only / no-write boundary remains preserved.

Formal generation was not triggered.

Formal export was not triggered.

Formal write-back was not triggered.

`output`, `job`, and `export` were not written.

Validation passed does not mean formal ZDoc integration is complete.

Validation passed does not authorize real use.

Validation passed does not authorize trial.

Validation passed does not authorize 1-2 person controlled trial.

Validation passed does not authorize 2-5 person small-concurrency trial.

Validation passed does not authorize ZDoc service execution.

Validation passed does not authorize endpoint access.

Validation passed does not authorize real KG access.

## 4. ZDoc Integration Implementation Boundary

Future integration can only start with ZDoc preview-only / no-write integration.

Future integration must use only synthetic / dummy / fake preview input until a later explicit gate changes the boundary.

Future integration must preserve a disable switch, such as `preview_output_post_processing_enabled` or an equivalent gate.

Future integration must preserve `blocked_reasons`.

Future integration must preserve failure blocking.

Future integration must preserve cleaned output, `warnings`, and `cleaning_applied` records as bounded preview metadata.

Future integration must not write `output`, `job`, or `export`.

Future integration must not trigger formal generation.

Future integration must not trigger formal export.

Future integration must not trigger formal write-back.

Future integration must not trigger ZBid write-back.

Future integration must not directly connect cleaned output to formal generation / export / write-back.

Future integration must not read real KG.

Future integration must not parse real KG JSON.

Future integration must not run the ZDoc service.

Future integration must not access a real endpoint.

Future integration must not use real project materials.

Future integration must not use real tender documents.

Future integration must not use real construction organization design text.

Future integration must not use real business data.

Future integration must not enter real use.

Future integration must not enter trial.

Future integration must not fall back to polluted raw output when post-processing fails.

Future integration must keep preview-only output as non-evidence.

Future integration must keep formal flags false unless a later explicit authorization gate changes the boundary.

## 5. Recommended Next Surface Review

Recommended next node:

`MODEL-FLEET-GOVERNANCE-032-ZDOC-PREVIEW-ONLY-INTEGRATION-CODE-SURFACE-REVIEW`

This node recommends a surface review before any integration implementation.

Reasons:

1. `025-safe` did not identify a frontend implementation surface within the safe allowlist.
2. ZDoc integration may involve ZDoc preview route, frontend, backend, tests, and config boundaries.
3. A safe surface review is needed before choosing integration implementation files.
4. A safe surface review reduces the risk of accidental formal generation / export / write-back connection.
5. A safe surface review keeps real KG, `output`, `job`, `export`, and unknown `.json` read risk controlled.
6. Existing reviewed implementation surfaces prove preview-only post-processing behavior, but they do not prove the full ZDoc integration surface is safely identified.

Future `032` must use an allowlist.

Future `032` must not use full-repository `rg`.

Future `032` must not use broad search.

Future `032` must not modify code.

Future `032` must not modify tests.

Future `032` must not run tests.

Future `032` must not run the ZDoc service.

Future `032` must not access endpoints.

Future `032` must not read real KG.

Future `032` must not read unknown `.json` file bodies.

Future `032` must not read `知识图谱/**` or `AI知识图谱大全/**`.

Future `032` must not read `output/**`, `job/**`, or `export/**`.

Future `032` must not trigger formal generation / export / write-back.

Future `032` must generate a docs-only surface review file and stop for human review.

## 6. Current Decision

`ZDOC INTEGRATION IMPLEMENTATION AUTHORIZATION GATE FORMED / SURFACE REVIEW REQUIRED / NO TRIAL AUTHORIZED`

This decision records only the docs-only ZDoc preview-only / no-write output post-processing integration implementation authorization gate.

This decision does not authorize code changes in this node.

This decision does not authorize test execution in this node.

This decision does not authorize implementation in this node.

This decision does not authorize Ollama execution.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG access.

This decision does not authorize formal generation / export / write-back.

This decision does not authorize real use or trial.

## 7. NO-GO Statements

`NO-GO FOR CODE CHANGE IN THIS NODE`

`NO-GO FOR TEST EXECUTION IN THIS NODE`

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR ENDPOINT ACCESS`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR FORMAL GENERATION / EXPORT / WRITE-BACK`

`NO-GO FOR OUTPUT / JOB / EXPORT WRITE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR CONCURRENT TEST`

`NO-GO FOR PERFORMANCE TEST`

## 8. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-032-ZDOC-PREVIEW-ONLY-INTEGRATION-CODE-SURFACE-REVIEW`

That node must not execute automatically.

That node must not automatically modify code.

That node must not run tests.

That node must not run ZDoc.

That node must not access endpoints.

That node must not read or parse real KG.

That node must not trigger formal generation / export / write-back.

That node must not write `output`, `job`, or `export`.

That node must not enter real use or trial.

MODEL-FLEET-GOVERNANCE-031 stops here and waits for human review.
