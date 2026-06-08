# MODEL-FLEET-GOVERNANCE-039: Controlled Preview-Only Endpoint Validation Preflight and Service Start Gate

## 1. Baseline

- Task node: `MODEL-FLEET-GOVERNANCE-039-CONTROLLED-PREVIEW-ONLY-ENDPOINT-VALIDATION-PREFLIGHT-AND-SERVICE-START-GATE`
- Node type: controlled preview-only endpoint validation preflight and ZDoc service start authorization gate
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `b3f8100c8420997dbd54f9547939e004f5e9430e`
- Start tag at HEAD: `v0.1.599-zdoc-controlled-preview-only-endpoint-authorization-gate`
- Start commit: `b3f8100 docs: add controlled preview-only endpoint authorization gate`
- Previous node: `MODEL-FLEET-GOVERNANCE-038-CONTROLLED-PREVIEW-ONLY-ENDPOINT-AUTHORIZATION-GATE`
- Previous decision: `CONTROLLED PREVIEW-ONLY ENDPOINT AUTHORIZATION GATE COMPLETED / ENDPOINT VALIDATION NOT EXECUTED / NO TRIAL AUTHORIZED`

This node is not endpoint validation execution.

This node does not run ZDoc service, access endpoints, run tests, run Ollama, read real KG, parse real KG JSON, read unknown `.json` bodies, trigger formal generation / export / write-back, write `output`, `job`, or `export`, generate images, or enter trial.

## 2. Inputs Reviewed

Required docs files read:

1. `docs/zdoc-controlled-preview-only-endpoint-authorization-gate-model-fleet-governance-038.md`
2. `docs/zdoc-preview-only-integration-result-review-and-controlled-endpoint-gate-model-fleet-governance-037.md`
3. `docs/zdoc-preview-only-zdoc-integration-validation-execution-record-model-fleet-governance-036.md`

Required test file read:

1. `backend/tests/test_local_trial_preview_only_route.py`

The test file explicitly imports the preview-only route source as:

```python
from backend.app.routers import local_trial_preview_only
```

Allowed single route source file read:

1. `backend/app/routers/local_trial_preview_only.py`

No full-repository `rg` was executed.

No broad search was executed.

No real KG was read.

No unknown `.json` body was read.

No `知识图谱/**` or `AI知识图谱大全/**` path was read.

No `output/**`, `job/**`, or `export/**` path was read.

## 3. Review of 038 Controlled Endpoint Authorization Gate

`MODEL-FLEET-GOVERNANCE-038` completed the controlled preview-only endpoint authorization gate.

The 038 gate authorized only the boundary for a future controlled preview-only endpoint validation node.

The 038 gate does not authorize endpoint validation execution in this node.

The 038 gate does not authorize ZDoc service execution in this node.

The 038 gate does not authorize endpoint access in this node.

The 038 gate does not authorize real KG access, formal generation, export, write-back, `output` writes, `job` writes, `export` writes, real use, or trial.

## 4. Review of 037 and 036 Preview-Only / No-Write Conclusions

`MODEL-FLEET-GOVERNANCE-037` completed docs-only result review and formed a controlled endpoint gate requirement.

`MODEL-FLEET-GOVERNANCE-036` preview-only integration validation passed.

The 036 test command was:

```bash
python3 -m pytest backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_cleans_synthetic_json backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_extracts_markdown_and_text backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_blocks_failure_and_can_disable
```

The 036 test result was:

```text
3 passed in 0.09s
```

The 036 / 037 conclusions prove only that preview-only / no-write integration validation passed with authorized synthetic tests.

Preview-only / no-write validation passed does not equal:

1. Ollama run authorization;
2. ZDoc service run authorization;
3. endpoint access authorization;
4. real KG read authorization;
5. formal generation authorization;
6. export authorization;
7. write-back authorization;
8. `output`, `job`, or `export` write authorization;
9. trial authorization.

## 5. Candidate Preview-Only Endpoint Boundary Confirmed from Authorized Files

The candidate preview-only route source confirmed from the authorized test file is:

`backend/app/routers/local_trial_preview_only.py`

The candidate route constant confirmed from the route source is:

```text
LOCAL_TRIAL_PREVIEW_ONLY_PATH = "/local-trial/preview-only"
```

The route decorator confirmed from the route source is:

```text
@router.post(LOCAL_TRIAL_PREVIEW_ONLY_PATH)
```

The route name confirmed from the route source is:

```text
local_trial_preview_only
```

The candidate endpoint path confirmed from the authorized files is:

```text
/local-trial/preview-only
```

This node does not access that endpoint.

This node does not send any request to that endpoint.

This node does not start any service for that endpoint.

## 6. Future Endpoint Input Boundary

Future endpoint access must be a separate later node.

If separately authorized, future endpoint validation may use only synthetic / dummy / fake input.

Future input must not contain:

1. real KG;
2. real project materials;
3. real tender documents;
4. real construction organization design text;
5. real business data;
6. user privacy data;
7. production identifiers;
8. real evidence bodies;
9. unknown `.json` bodies;
10. any content from `知识图谱/**` or `AI知识图谱大全/**`;
11. any content from `output/**`, `job/**`, or `export/**`.

The authorized test file uses synthetic values in `_safe_payload`, including fake local trial identifiers and preview-only advisory text.

Any later endpoint validation node must re-confirm that all input remains synthetic / dummy / fake before endpoint access.

## 7. Future Endpoint Output and Blocking Fields

From the authorized test file and route source, future endpoint validation may at most verify the following preview-only / no-write response surfaces:

1. `preview_packet`;
2. `validator_result`;
3. `blocked_reasons`;
4. `warnings`;
5. `output_post_processing`;
6. `cleaning_applied`;
7. `preview_only`;
8. `no_write`;
9. `no_evidence`;
10. `metadata_only`;
11. formal generation / export / write-back flags;
12. `writes_output`;
13. `writes_job`;
14. `writes_export`;
15. `calls_generate_route`;
16. `calls_export_docx_route`;
17. `calls_review_apply_route`;
18. `triggers_generation_chain`;
19. `triggers_export_chain`;
20. `affects_generation`;
21. `affects_export`;
22. `affects_zbid_writeback`;
23. `calls_ollama`;
24. `calls_external_model_api`;
25. `downloads_models`;
26. `pulls_models`.

The blocking fields confirmed from the authorized files include:

1. `blocked_reasons`;
2. `warnings`;
3. `post_processing_blocked`;
4. `formal_writeback_allowed`;
5. `review_apply_allowed`;
6. `docx_export_allowed`;
7. `zbid_writeback_allowed`;
8. `output_write_allowed`;
9. `writes_output`;
10. `writes_job`;
11. `writes_export`.

The authorized tests assert example blocked reasons such as:

1. `preview_only_is_not_writeback_permission`;
2. `preview_only_is_not_evidence`;
3. `missing_scoring_clause_refs`;
4. `generated_advisory_cannot_be_evidence`;
5. `zbid_writeback_request_blocked`;
6. `docx_export_request_blocked`;
7. `review_apply_request_blocked`;
8. `formal_writeback_request_blocked`;
9. `output_write_request_blocked`;
10. `target_structure_not_found`.

## 8. Future ZDoc Service Start Gate Boundary

The next service start gate, if separately authorized, may at most authorize:

1. checking current HEAD, current tag, and whether `git status --short` is clean;
2. confirming the service startup command;
3. confirming service startup remains only for later preview-only / no-write endpoint validation preparation;
4. starting ZDoc service only to prepare for later preview-only endpoint validation;
5. prohibiting automatic endpoint access after service start;
6. prohibiting real KG reads after service start;
7. prohibiting formal generation, export, and write-back after service start;
8. requiring service state report after service start;
9. stopping immediately after service state report;
10. requiring any endpoint access to enter a separate later authorization node.

Service startup command status:

```text
未在授权读取范围内查明
```

Because the service startup command was not confirmed within the authorized read scope, this node does not infer or propose a startup command.

## 9. Future Endpoint Access Gate Boundary

Endpoint access must be a separate later node.

Future endpoint access may at most allow:

1. accessing only a preview-only / no-write endpoint;
2. using only synthetic / dummy / fake input;
3. ensuring input contains no real KG;
4. ensuring input contains no real project materials;
5. ensuring input contains no real tender documents;
6. ensuring input contains no real business data;
7. ensuring input contains no user privacy data;
8. verifying only `preview_packet`;
9. verifying only `validator_result`;
10. verifying only `blocked_reasons`;
11. verifying only `warnings`;
12. verifying formal generation / export / write-back flags are all false;
13. verifying `output`, `job`, and `export` are not written;
14. stopping immediately after endpoint access and reporting results;
15. not entering trial.

Future endpoint access must not automatically broaden into service recovery, real data testing, formal generation, export, write-back, concurrent testing, performance testing, real use, or trial.

## 10. Stop Conditions

This node and any directly derived next gate must stop if any of the following appears:

1. ZDoc service must be run;
2. endpoint must be accessed;
3. `curl` or HTTP request must be executed;
4. tests must be run;
5. Ollama must be run;
6. real KG must be read;
7. unknown `.json` must be read;
8. `知识图谱/**` or `AI知识图谱大全/**` must be read;
9. `output/**`, `job/**`, or `export/**` must be read;
10. preview-only / no-write boundary is unclear;
11. endpoint path cannot be confirmed from authorized files;
12. service startup command cannot be confirmed from authorized files;
13. formal generation, export, or write-back may be triggered;
14. non-target file changes are discovered;
15. working tree is not clean outside the target docs file;
16. any unauthorized high-impact action is required.

For this node, the service startup command is `未在授权读取范围内查明`, so any attempt to start service must stop and move to a separate authorization decision.

## 11. NO-GO Statements

`NO-GO FOR CODE CHANGE IN THIS NODE`

`NO-GO FOR TEST EXECUTION IN THIS NODE`

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR ANY OLLAMA COMMAND IN THIS NODE`

`NO-GO FOR ZDOC SERVICE EXECUTION IN THIS NODE`

`NO-GO FOR BACKEND SERVICE START IN THIS NODE`

`NO-GO FOR FRONTEND SERVICE START IN THIS NODE`

`NO-GO FOR API SERVER START IN THIS NODE`

`NO-GO FOR ENDPOINT ACCESS IN THIS NODE`

`NO-GO FOR CURL / HTTP REQUEST IN THIS NODE`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR UNKNOWN JSON BODY READ`

`NO-GO FOR KNOWLEDGE GRAPH DIRECTORY READ`

`NO-GO FOR OUTPUT / JOB / EXPORT READ`

`NO-GO FOR FORMAL GENERATION / EXPORT / WRITE-BACK`

`NO-GO FOR OUTPUT / JOB / EXPORT WRITE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR IMAGE MODEL CALL`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR CONCURRENT TEST`

`NO-GO FOR PERFORMANCE TEST`

## 12. Current Decision

`CONTROLLED PREVIEW-ONLY ENDPOINT VALIDATION PREFLIGHT COMPLETED / ZDOC SERVICE NOT STARTED / ENDPOINT NOT ACCESSED / NO TRIAL AUTHORIZED`

This decision forms only the next controlled ZDoc service start gate.

This decision does not authorize endpoint access.

This decision does not authorize trial.

## 13. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-040-CONTROLLED-ZDOC-SERVICE-START-GATE`

The next node must remain a separate service startup authorization gate.

The next node must first resolve the service startup command because it is `未在授权读取范围内查明` in this node.

The next node must not automatically access an endpoint after service startup.

Any endpoint access must enter a separate later node.
