# MODEL-FLEET-GOVERNANCE-033: ZDoc Preview-Only Integration Code Implementation Authorization Gate

## 1. Baseline

- Task node: `MODEL-FLEET-GOVERNANCE-033-ZDOC-PREVIEW-ONLY-INTEGRATION-CODE-IMPLEMENTATION-AUTHORIZATION-GATE`
- Node type: docs-only implementation authorization gate
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Start HEAD: `da501839b0113d91da449b3e7869d70f8d209bc9`
- Previous node: `MODEL-FLEET-GOVERNANCE-032`
- Previous decision: `ZDOC PREVIEW-ONLY INTEGRATION SURFACE REVIEW COMPLETED / IMPLEMENTATION SURFACE IDENTIFIED / NO CODE CHANGE / NO TRIAL AUTHORIZED`

This node creates only a docs-only authorization gate. It does not modify code, tests, frontend, backend runtime behavior, config, JSON data, KG data, output artifacts, job artifacts, export artifacts, model state, ZDoc service state, or endpoint state.

## 2. Inputs Reviewed

Prescribed prior docs files read in this node:

1. `docs/zdoc-preview-only-zdoc-integration-code-surface-review-model-fleet-governance-032.md`
2. `docs/zdoc-preview-only-output-post-processing-zdoc-integration-implementation-authorization-gate-model-fleet-governance-031.md`
3. `docs/zdoc-preview-only-validation-result-review-and-zdoc-integration-gate-model-fleet-governance-030.md`
4. `docs/zdoc-preview-only-output-post-processing-validation-execution-record-model-fleet-governance-029.md`
5. `docs/zdoc-output-post-processing-code-review-and-preview-only-validation-gate-model-fleet-governance-028.md`
6. `docs/zdoc-single-model-output-post-processing-code-implementation-record-model-fleet-governance-027.md`
7. `docs/zdoc-single-model-output-post-processing-code-implementation-authorization-gate-model-fleet-governance-026.md`

`032` safe candidate source/test/config-related files read in this node:

1. `backend/app/routers/local_trial_preview_only.py`
2. `backend/zhifei_autoplan/zdoc_zbid_preview_packet.py`
3. `backend/zhifei_autoplan/zbid_preview_input_validator.py`
4. `backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py`
5. `backend/app/routers/local_llm_preview_safe.py`
6. `backend/tests/test_local_trial_preview_only_route.py`
7. `backend/tests/test_zdoc_zbid_preview_packet.py`
8. `backend/tests/test_zdoc_zbid_preview_outbound.py`
9. `backend/tests/test_zdoc_zbid_preview_only_integration_contract_schema.py`
10. `backend/tests/test_zbid_preview_input_validator.py`
11. `backend/tests/test_local_llm_preview_safe_endpoint.py`
12. `backend/tests/test_preview_only_route_frontend_integration_plan_schema.py`

No real KG was read. No real KG JSON was parsed. No unknown `.json` body was read. No `知识图谱/**` or `AI知识图谱大全/**` path was read. No `output/**`, `job/**`, or `export/**` path was read.

## 3. Surface Review Result

`MODEL-FLEET-GOVERNANCE-032` established the following review result:

1. Backend integration surface: identified.
2. Frontend integration surface: `未在本节点安全 allowlist 复核中查明`.
3. Test / fixture surface: identified.
4. Config / feature flag surface: identified.
5. Formal-chain risk: written.
6. Recommended implementation path: written.

The first-choice future backend implementation surface remains `backend/app/routers/local_trial_preview_only.py`. The helper/reference surfaces remain `backend/zhifei_autoplan/zdoc_zbid_preview_packet.py` and `backend/zhifei_autoplan/zbid_preview_input_validator.py`. The outbound adapter surface `backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py` remains high-caution because it contains endpoint/network-send capability and must not be the first implementation surface unless a later node explicitly authorizes it.

The secondary local preview-safe surface `backend/app/routers/local_llm_preview_safe.py` remains secondary because it is Ollama-adjacent and contains real-adapter bridge paths. It is not the first-choice ZDoc preview-only integration implementation target.

No frontend implementation surface was proven by the safe allowlist review. Future implementation must not infer an unknown frontend surface.

## 4. Implementation Authorization Boundary

Future implementation, if and only if explicitly authorized in `034`, can only start with ZDoc preview-only / no-write integration.

Future implementation should prioritize only the already identified backend / tests / config surfaces:

1. `backend/app/routers/local_trial_preview_only.py`
2. `backend/zhifei_autoplan/zdoc_zbid_preview_packet.py`
3. `backend/zhifei_autoplan/zbid_preview_input_validator.py`
4. Associated synthetic tests and fixtures listed in this document
5. Existing request-level or environment feature-flag surfaces already identified by `032`

Future implementation should not prioritize frontend changes because frontend integration surface was not identified within the safe allowlist. Future implementation must not modify formal frontend generation, export, or write-back pages. If frontend display becomes necessary, a separate frontend-specific safe surface review is required first.

Future implementation must not connect to formal generation, formal export, formal write-back, ZBid write-back, ZDoc service execution, real endpoint access, real KG read/parse, real use, or trial.

Future implementation must not write `output`, `job`, or `export`.

Future implementation must preserve:

1. disable switch;
2. `blocked_reasons`;
3. failure blocking;
4. `warnings`;
5. `cleaning_applied`;
6. synthetic / dummy / fake preview input;
7. no-write flags;
8. formal-chain false flags.

Failure conditions must block safely and must not fall back into polluted raw output, formal generation, formal export, formal write-back, output writing, job writing, export writing, or endpoint/network send.

## 5. Future Allowed Code Implementation Boundary

Recommended future node:

`MODEL-FLEET-GOVERNANCE-034-ZDOC-PREVIEW-ONLY-INTEGRATION-CODE-IMPLEMENTATION`

Future `034` may allow only the following actions if explicitly authorized:

1. Read prescribed governance docs.
2. Read `032` identified safe surface files.
3. Continue using allowlist discipline.
4. Modify the minimum necessary backend / tests / config files.
5. Avoid frontend changes unless a later frontend-specific safe surface review authorizes a concrete frontend file.
6. Use only synthetic / dummy / fake preview input.
7. Add or modify only specific synthetic tests.
8. Run only specific synthetic tests.
9. Generate a docs-only implementation record.
10. Perform `git diff --check`, staged diff check, commit, push, remote tag, and stop for human review.

Future `034` must continue using the allowlist and must not run full-repository `rg`.

Future `034` must not perform broad search.

Future `034` must not read real KG.

Future `034` must not read unknown `.json` body content.

Future `034` may run only specific synthetic tests scoped to:

1. preview-only / no-write integration behavior;
2. post-processing output entering preview packet metadata only;
3. disable switch;
4. `blocked_reasons`;
5. failure blocking;
6. no formal generation / export / write-back;
7. no `output`, `job`, or `export` write.

## 6. Future Prohibited Boundary

Future implementation remains prohibited from:

1. formal generation / export / write-back;
2. `output`, `job`, or `export` writing;
3. real KG read or parse;
4. real endpoint access;
5. ZDoc service execution;
6. Ollama execution;
7. any Ollama command;
8. real project materials;
9. real tender documents;
10. real construction organization design text;
11. real business data;
12. image generation;
13. image generation tool execution;
14. image model calls;
15. concurrent testing;
16. performance testing;
17. trial;
18. 1-2 person controlled trial;
19. 2-5 person small-concurrency trial;
20. full-repository `rg`;
21. broad search;
22. reading `知识图谱/**`;
23. reading `AI知识图谱大全/**`;
24. reading unknown `.json` bodies;
25. treating preview advisory as evidence;
26. treating preview-only acceptance as writeback permission.

## 7. Current Decision

`ZDOC PREVIEW-ONLY INTEGRATION CODE IMPLEMENTATION AUTHORIZATION GATE FORMED / NO CODE CHANGE IN THIS NODE / NO TRIAL AUTHORIZED`

This decision forms only the implementation authorization gate for a future node. It does not authorize code changes in this node. It does not authorize test execution in this node. It does not authorize trial or real use.

## 8. NO-GO Statements

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

## 9. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-034-ZDOC-PREVIEW-ONLY-INTEGRATION-CODE-IMPLEMENTATION`

Only the next node may allow a minimal code implementation, and only if the next node explicitly authorizes it.

The next node must not run ZDoc, access endpoints, read or parse real KG, trigger formal generation / export / write-back, write `output`, `job`, or `export`, run Ollama, use real project/tender/construction/business data, generate images, enter real use, enter trial, perform concurrent testing, or perform performance testing.
