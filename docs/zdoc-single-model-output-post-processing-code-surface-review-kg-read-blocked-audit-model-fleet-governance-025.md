# MODEL-FLEET-GOVERNANCE-025: KG Read Blocked Audit for Code Surface Review

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Original `MODEL-FLEET-GOVERNANCE-025-SINGLE-MODEL-OUTPUT-POST-PROCESSING-CODE-SURFACE-REVIEW` starting HEAD:

  `caea463f8a08f1c5d6b570fe09fb375f44c4744b`

- Current blocked-audit starting HEAD:

  `caea463f8a08f1c5d6b570fe09fb375f44c4744b`

- Current blocked-audit starting `git status --short`: clean
- Original `025` status: not completed
- This node is a blocked audit node.
- This node is not a code surface review retry.

This node does not continue code surface review, does not execute broad `rg`, does not read real KG, does not modify code, does not run Ollama, does not run the ZDoc service, does not access endpoints, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not generate images, and does not enter real use or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-output-post-processing-implementation-authorization-gate-model-fleet-governance-024.md`
2. `docs/zdoc-single-model-output-post-processing-smoke-test-execution-record-model-fleet-governance-023.md`
3. `docs/zdoc-single-model-output-post-processing-authorization-gate-model-fleet-governance-022.md`
4. `docs/zdoc-single-model-output-format-control-smoke-test-execution-record-model-fleet-governance-021.md`
5. `docs/zdoc-single-model-output-format-control-authorization-gate-model-fleet-governance-020.md`

No real KG file was read in this blocked-audit node.

No real KG JSON was read or parsed in this blocked-audit node.

The following file was not read in this blocked-audit node:

`知识图谱/ZF-KG-26-Port-Harbor.json`

No `AI知识图谱大全/**` file was read in this blocked-audit node.

No `output/**`, `job/**`, or `export/**` file was read in this blocked-audit node.

## 3. Blocked Event Summary

The original `MODEL-FLEET-GOVERNANCE-025-SINGLE-MODEL-OUTPUT-POST-PROCESSING-CODE-SURFACE-REVIEW` execution was not completed.

During the original `025` execution, a read-only `rg` code-surface search mistakenly matched:

`知识图谱/ZF-KG-26-Port-Harbor.json`

That command output real KG body snippets.

This violated the original boundary:

`禁止读取真实 KG 文件正文`

Codex immediately stopped after identifying this boundary violation.

No further code surface review was performed after the stop.

This blocked-audit node records the event only.

This blocked-audit node does not retry the code surface review.

## 4. Boundary Compliance After Stop

The following statements describe the state after the original `025` was blocked:

- 未新增 docs 文件
- 未修改代码
- 未运行 Ollama
- 未运行 ZDoc 服务
- 未访问 endpoint
- 未触发 generation / export / write-back
- 未写 output / job / export
- 未执行 commit / push / tag

The original `025` did not complete.

The original `025` did not create the intended code surface review docs file.

The original `025` did not modify adapter / route / helper / `main.py`.

The original `025` did not modify frontend, tests, config, JSON, or business files.

The original `025` did not run tests.

The original `025` did not run build commands.

## 5. Root Cause Assessment

The root cause was a broad code-surface `rg` search that did not sufficiently exclude real KG paths.

Excluding only `output/**`, `job/**`, and `export/**` is not enough to avoid KG risk.

Real KG files may exist outside `output/**`, `job/**`, and `export/**`.

Real KG files may exist under:

1. `知识图谱/**`
2. `AI知识图谱大全/**`
3. other non-output / non-job / non-export paths whose names contain `KG`, `kg`, `graph`, or `知识图谱`

The previous broad search was too wide for this repository.

The previous broad search prioritized coverage over the KG read boundary.

Future code surface review must prioritize safety over completeness.

Future review must use allowlist paths instead of broad search.

Future review must not use repository-wide keyword scanning.

## 6. Safe Retry Strategy

Future safe retry strategy:

1. Do not use broad repository-wide `rg`.
2. Do not use wide keyword scanning over the whole repository.
3. Do not scan `知识图谱/**`.
4. Do not scan `AI知识图谱大全/**`.
5. Use allowlist directories or allowlist files only.
6. Prefer allowlist candidates under:
   - `backend/**`
   - `frontend/**`
   - `tests/**`
   - `config/**`
   - explicitly named prior target docs under `docs/**`
7. Even with allowlists, continue excluding:
   - `知识图谱/**`
   - `AI知识图谱大全/**`
   - `output/**`
   - `job/**`
   - `export/**`
   - `node_modules/**`
   - `__pycache__/**`
   - `*.pyc`
8. If keyword search is needed, first create a candidate file list that is itself KG-safe.
9. Inspect candidate files one by one with bounded read commands.
10. Do not execute `cat`, `sed`, `head`, or `rg` against unknown wide paths.
11. If a candidate path contains `KG`, `kg`, `graph`, `知识图谱`, or `json` and cannot be confirmed safe, skip it and record:

    `未读取，避免真实 KG 风险`

12. The primary goal of the next code surface review is safety, not exhaustive discovery.
13. A safe retry node must not directly read real KG.
14. A safe retry node must not parse real KG JSON.

The next safe retry must be explicitly authorized before any new code surface review begins.

## 7. Current Decision

`CODE SURFACE REVIEW BLOCKED BY KG READ BOUNDARY / AUDIT RECORDED / NO CODE CHANGE`

This decision records only the blocked audit.

This decision does not authorize code surface review retry in this node.

This decision does not authorize broad `rg` in this node.

This decision does not authorize KG read or parse.

This decision does not authorize code change.

This decision does not authorize test execution.

This decision does not authorize Ollama execution.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize generation / export / write-back.

This decision does not authorize output / job / export writes.

This decision does not authorize real use or trial.

## 8. NO-GO Statements

`NO-GO FOR CODE SURFACE RETRY IN THIS NODE`

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

## 9. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-025-SAFE-CODE-SURFACE-REVIEW-RETRY`

The next node must use allowlist search.

The next node must not use broad repository-wide `rg`.

The next node must not scan `知识图谱/**`.

The next node must not scan `AI知识图谱大全/**`.

The next node must still not modify code.

The next node must still not run ZDoc.

The next node must still not access endpoints.

The next node must still not run Ollama.

The next node must still not read real KG.

The next node must still not parse real KG JSON.

The next node must still not trigger generation / export / write-back.

The next node must still not write `output`, `job`, or `export`.

The next node must still not enter real use or trial.

MODEL-FLEET-GOVERNANCE-025-KG-READ-BLOCKED-AUDIT stops here and waits for human review.
