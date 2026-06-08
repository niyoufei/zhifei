# MODEL-FLEET-GOVERNANCE-038: Controlled Preview-Only Endpoint Authorization Gate

## 1. Baseline

- Task node: `MODEL-FLEET-GOVERNANCE-038-CONTROLLED-PREVIEW-ONLY-ENDPOINT-AUTHORIZATION-GATE`
- Node type: docs-only controlled preview-only endpoint authorization gate
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `8025ee61b1cd098d444c73f4a2dbfcc41251f5ba`
- Start tag at HEAD: `v0.1.598-zdoc-preview-only-integration-result-endpoint-gate`
- Start commit: `8025ee6 docs: add preview-only integration result review endpoint gate`
- Previous node: `MODEL-FLEET-GOVERNANCE-037`
- Previous decision: `PREVIEW-ONLY INTEGRATION RESULT REVIEW COMPLETED / CONTROLLED ENDPOINT AUTHORIZATION GATE REQUIRED / NO TRIAL AUTHORIZED`

This node is docs-only. It does not execute endpoint validation, run ZDoc, access endpoints, run tests, run Ollama, read real KG, trigger formal generation / export / write-back, write `output`, `job`, or `export`, or enter trial.

## 2. Inputs Reviewed

Required docs files read:

1. `docs/zdoc-preview-only-integration-result-review-and-controlled-endpoint-gate-model-fleet-governance-037.md`
2. `docs/zdoc-preview-only-zdoc-integration-validation-execution-record-model-fleet-governance-036.md`

Allowed test-boundary file read:

1. `backend/tests/test_local_trial_preview_only_route.py`

No full-repository `rg` was executed.

No broad search was executed.

No real KG was read.

No unknown `.json` body was read.

No `知识图谱/**` or `AI知识图谱大全/**` path was read.

No `output/**`, `job/**`, or `export/**` path was read.

## 3. Result Review

`MODEL-FLEET-GOVERNANCE-037` completed docs-only result review and formed a controlled endpoint gate requirement.

`MODEL-FLEET-GOVERNANCE-036` preview-only integration validation passed.

The `036` test command was:

```bash
python3 -m pytest backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_cleans_synthetic_json backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_extracts_markdown_and_text backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_blocks_failure_and_can_disable
```

The `036` test result was:

```text
3 passed in 0.09s
```

The `036 / 037` conclusions prove only that preview-only / no-write integration validation passed with synthetic tests.

That conclusion does not authorize real endpoint access.

That conclusion does not authorize ZDoc service execution.

That conclusion does not authorize Ollama execution.

That conclusion does not authorize real KG reads.

That conclusion does not authorize formal generation.

That conclusion does not authorize export.

That conclusion does not authorize write-back.

That conclusion does not authorize `output`, `job`, or `export` writes.

That conclusion does not authorize trial.

Future controlled endpoint validation must be separately node-authorized.

## 4. Future Allowed Scope

Future controlled preview-only endpoint validation, if later authorized, may at most allow:

1. starting controlled preview-only endpoint validation under a new explicit node;
2. accessing only a preview-only / no-write endpoint;
3. using only synthetic / dummy / fake preview input;
4. confirming synthetic input contains no real project materials;
5. confirming synthetic input contains no real KG;
6. confirming synthetic input contains no real tender documents;
7. confirming synthetic input contains no real business data;
8. confirming synthetic input contains no user privacy data;
9. validating that endpoint output remains preview-only;
10. validating no-write flags;
11. validating formal generation / export / write-back flags remain false;
12. validating safe fields such as `blocked_reasons`, `warnings`, `validator_result`, and `preview_packet`;
13. validating that `output`, `job`, and `export` are not written;
14. stopping immediately after validation and reporting results;
15. not entering trial.

This node does not execute any of the above future validation actions.

## 5. Future Prohibited Scope

Even if future controlled endpoint validation is authorized, it must still prohibit:

1. reading real KG;
2. reading real project materials;
3. reading real tender documents;
4. triggering formal generation;
5. triggering export;
6. triggering write-back;
7. writing `output`, `job`, or `export`;
8. calling any ZBid write-back chain;
9. using real business input;
10. using real user data;
11. concurrent testing;
12. performance testing;
13. real trial;
14. production validation;
15. formal generation endpoint access;
16. export endpoint access;
17. write-back endpoint access.

## 6. Future Startup Checklist

Before any future controlled endpoint validation starts, the future node must check:

1. current HEAD;
2. current tag;
3. whether `git status --short` is clean;
4. whether uncommitted changes exist;
5. whether non-target file changes exist;
6. whether the endpoint is confirmed as preview-only / no-write;
7. whether input is confirmed synthetic / dummy / fake;
8. whether real KG will not be read;
9. whether `output`, `job`, or `export` will not be written;
10. whether formal generation / export / write-back will not be triggered;
11. whether validation will stop immediately after completion.

## 7. Stop Conditions

Future endpoint validation must stop immediately if any of the following occurs:

1. endpoint is not preview-only / no-write;
2. request requires real KG;
3. request requires real project data;
4. formal generation call is observed or required;
5. export call is observed or required;
6. write-back call is observed or required;
7. `output`, `job`, or `export` write is observed or required;
8. trial entry appears;
9. ZBid write-back chain appears;
10. unknown `.json` body read is required;
11. non-synthetic input is required;
12. any unauthorized high-impact action is required or observed.

## 8. NO-GO Statements

`NO-GO FOR CODE CHANGE IN THIS NODE`

`NO-GO FOR TEST EXECUTION IN THIS NODE`

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR ANY OLLAMA COMMAND IN THIS NODE`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR ENDPOINT ACCESS IN THIS NODE`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR UNKNOWN JSON BODY READ`

`NO-GO FOR FORMAL GENERATION / EXPORT / WRITE-BACK`

`NO-GO FOR OUTPUT / JOB / EXPORT WRITE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR IMAGE MODEL CALL`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR CONCURRENT TEST`

`NO-GO FOR PERFORMANCE TEST`

## 9. Current Decision

`CONTROLLED PREVIEW-ONLY ENDPOINT AUTHORIZATION GATE COMPLETED / ENDPOINT VALIDATION NOT EXECUTED / NO TRIAL AUTHORIZED`

This decision forms only an authorization gate for a later controlled preview-only endpoint validation node. It does not authorize endpoint validation in this node.

## 10. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-039-CONTROLLED-PREVIEW-ONLY-ENDPOINT-VALIDATION-EXECUTION`

The next node may proceed only if it explicitly authorizes controlled preview-only endpoint validation and preserves all boundaries in this gate.

The next node must not use real KG, real project materials, real tender documents, real construction organization design text, real business data, real user data, formal generation / export / write-back, `output`, `job`, or `export` writes, trial, concurrent testing, performance testing, or production validation.
