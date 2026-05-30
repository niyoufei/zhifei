# ZDoc Single-Model Upgrade Preflight Authorization Gate - KG-RUNTIME-153

## 1. Runtime Scope

KG-RUNTIME-153 is a docs-only preflight authorization gate for the ZDoc single-model upgrade chain.

This stage only records the boundary for a possible later upgrade preflight. It does not grant or execute the preflight itself.

This stage explicitly:

- Does not execute an upgrade.
- Does not run Ollama.
- Does not execute any model command.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute actual local preflight commands.
- Does not perform expanded internet lookup.
- Does not enter real use, formal trial use, or controlled trial use.
- Does not enter KG-RUNTIME-154.

The gate result in this document is only a future authorization boundary. It must not be treated as actual preflight authorization or actual upgrade authorization.

## 2. Baseline

KG-RUNTIME-152 ended with the following recorded state:

- End HEAD: `2fb5d9e45d3edbbed779d6856903383ec2b4a2e6`
- Remote tag: `v0.1.535-zdoc-single-model-upgrade-controlled-latest-version-recheck`
- New docs-only file: `docs/zdoc-single-model-upgrade-controlled-latest-version-recheck-kg-runtime-152.md`
- Candidate decision after recheck: `KEEP qwen3.6:35b as single-model upgrade candidate`
- No blocked or insufficient-source item affects candidate availability.
- Local installation, disk, network, and execution feasibility remain for a later preflight.
- Worktree state after KG-RUNTIME-152: clean.
- Model upgrade state: not executed.
- Real use state: not entered.
- Trial use state: not entered.

KG-RUNTIME-153 starts from that KG-RUNTIME-152 record and adds only this docs-only preflight authorization gate.

## 3. Source Boundary

KG-RUNTIME-153 is based only on:

1. KG-RUNTIME-152 controlled latest-version recheck document:
   `docs/zdoc-single-model-upgrade-controlled-latest-version-recheck-kg-runtime-152.md`
2. KG-RUNTIME-151 latest-version recheck authorization gate document:
   `docs/zdoc-single-model-upgrade-latest-version-recheck-authorization-gate-kg-runtime-151.md`
3. KG-RUNTIME-150 approval response intake document:
   `docs/zdoc-single-model-upgrade-execution-explicit-approval-response-intake-kg-runtime-150.md`

This stage:

- Does not add internet lookup.
- Does not re-collect the local model inventory.
- Does not run local model tools.
- Does not execute actual preflight commands.
- Does not treat this preflight authorization gate as actual preflight authorization.
- Does not treat this preflight authorization gate as actual upgrade authorization.

## 4. Candidate Confirmation

The only single-model candidate for this preflight authorization gate is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 through KG-RUNTIME-152
- Current state: retained as the single-model upgrade candidate after latest-version recheck
- Upgrade executed by KG-RUNTIME-153: no
- Upgrade allowed in KG-RUNTIME-153: no
- Actual preflight allowed in KG-RUNTIME-153: no
- Automatic later upgrade allowed: no
- Requirement for any later upgrade path: explicit preflight authorization, completed preflight result review, and separate actual upgrade authorization

No other model candidate is confirmed by KG-RUNTIME-153. No model family is expanded by this stage.

## 5. Preflight Authorization Need

A later upgrade preflight is still needed because KG-RUNTIME-152 only confirmed that `qwen3.6:35b` may remain the single-model candidate.

The following items are still unconfirmed:

- Local installation state.
- Disk space for download and old-model retention.
- Network stability.
- Download size record.
- Old model retention strategy.
- `latest` tag impact.
- Failure retry strategy.
- Execution time window.
- ZDoc service boundary before execution.
- Endpoint boundary before execution.
- Real KG body-read boundary before execution.
- Generation, export, and writeback boundary before execution.

Therefore the project cannot directly enter actual upgrade execution.

## 6. Proposed Preflight Scope

The following items may be requested for a later user-authorized preflight, but KG-RUNTIME-153 does not execute them:

1. Whether the worktree is clean.
2. Current HEAD and tag record.
3. Whether the target model name remains exactly `qwen3.6:35b`.
4. Whether a ZDoc service is running.
5. Whether endpoint-call risk exists.
6. Whether real KG read risk exists.
7. Whether generation, export, or writeback mis-trigger risk exists.
8. Whether disk space is sufficient for download and old-model retention.
9. Whether network conditions are suitable for download.
10. Whether download size has been recorded.
11. Whether the old model will be retained.
12. Whether old model deletion remains prohibited.
13. Whether retry is allowed after failure, and the retry count.
14. Whether the execution time window is explicit.
15. Whether post-upgrade activity is limited to stability verification.

This stage only lists the possible preflight scope. It does not perform any preflight.

## 7. Proposed Future Preflight Command Boundary

KG-RUNTIME-153 executes no preflight commands.

If a later stage receives explicit user authorization, the future preflight may request only command categories such as:

- Git state confirmation.
- Disk-space check.
- Read-only network-connectivity check.
- Download-size record.
- Service-not-running confirmation.
- Output directory no-write confirmation.

Even in a later preflight stage:

- Each command must be explicitly authorized by the user.
- Preflight commands must not run Ollama.
- Preflight commands must not execute `ollama list`.
- Preflight commands must not execute `ollama pull qwen3.6:35b`.
- Preflight commands must not upgrade, pull, delete, or replace any model.
- Preflight commands must not access any ZDoc endpoint.
- Preflight commands must not read real KG.
- Preflight commands must not trigger generation, export, or writeback.

## 8. Preflight Authorization Items Required from User

Before any later preflight may execute, the user must explicitly authorize or confirm at least:

1. Whether local disk-space checks are allowed.
2. Whether read-only network-connectivity checks are allowed.
3. Whether download size may be recorded.
4. Whether worktree clean state may be checked.
5. Whether ZDoc service-not-running state may be checked.
6. Whether endpoint-not-accessed state may be checked.
7. Whether `output`, `job`, and `export` no-write state may be checked.
8. Whether no real KG read remains required.
9. Whether no generation, export, or writeback remains required.
10. Whether running Ollama remains prohibited.
11. Whether executing `ollama list` remains prohibited.
12. Whether executing `ollama pull qwen3.6:35b` remains prohibited.
13. Whether preflight completion still does not permit direct upgrade.
14. Whether preflight completion still requires report and review.

Missing, implied, partial, or template-only approval remains insufficient.

## 9. Preflight Gate Result

Preflight gate result:

`Preflight gate result: NOT AUTHORIZED FOR EXECUTION / pending explicit user approval`

Current upgrade execution status:

`Current upgrade execution status: NO-GO / preflight authorization pending`

Result meaning:

- KG-RUNTIME-153 only completes the preflight authorization gate.
- Actual preflight execution is not authorized.
- Model upgrade is not authorized.
- No preflight command may be executed.
- `ollama pull qwen3.6:35b` may not be executed.
- Actual upgrade execution may not be entered.

## 10. Required User Approval Text for KG-RUNTIME-154

If the user later wants KG-RUNTIME-154 to perform actual upgrade preflight, the user must provide explicit approval text equivalent to:

- 我允许 KG-RUNTIME-154 进行实际升级前预检。
- 预检对象仅限 `qwen3.6:35b`。
- 允许执行 git 状态确认。
- 允许执行磁盘空间检查。
- 允许执行只读网络连通性检查。
- 允许记录下载体积。
- 允许确认 ZDoc 服务未运行。
- 允许确认 endpoint 未访问。
- 允许确认不读取真实 KG。
- 允许确认不触发生成 / 导出 / 写回。
- 禁止运行 Ollama。
- 禁止执行 `ollama list`。
- 禁止执行 `ollama pull qwen3.6:35b`。
- 禁止执行任何模型命令。
- 禁止升级、拉取、删除或替换模型。
- 预检完成后必须回报并停止，不得直接升级。

This template is only the required future approval format. It does not mean KG-RUNTIME-153 has received actual preflight execution authorization.

## 11. Future Command Candidate Boundary

The following command string is recorded only as a future upgrade candidate command:

`ollama pull qwen3.6:35b`

Status:

`future upgrade candidate command / not executed in KG-RUNTIME-153`

Boundary:

- KG-RUNTIME-153 does not execute this command.
- A preflight stage also must not execute this command.
- A later node may consider it only after latest-version recheck, preflight, and actual user upgrade authorization have all passed.
- Wildcards are prohibited.
- Batch model operations are prohibited.
- Model deletion is prohibited.

## 12. Decision for Next Runtime

Recommended next stage:

`KG-RUNTIME-154: single-model upgrade controlled preflight checks docs-only / command-limited`

KG-RUNTIME-154 may be considered only if the user explicitly authorizes actual preflight scope and command boundaries.

KG-RUNTIME-154 must still:

- Not run Ollama.
- Not execute `ollama pull qwen3.6:35b`.
- Not upgrade, pull, delete, or replace any model.
- Only perform upgrade preflight checks inside the user-authorized boundary.
- Report the preflight result and stop.
- Not directly upgrade after preflight.

KG-RUNTIME-153 does not enter KG-RUNTIME-154.

## 13. Hard NO-GO Conditions

The current or later upgrade-preparation path must remain NO-GO if any of the following applies:

- The user has not explicitly authorized preflight.
- User authorization content is incomplete.
- Preflight scope is unclear.
- The preflight object is not exactly `qwen3.6:35b`.
- The task requires running Ollama.
- The task requires executing `ollama list`.
- The task requires executing `ollama pull qwen3.6:35b`.
- The task requires executing any model command.
- The task requires upgrading, pulling, deleting, or replacing any model.
- A service is found running and service runtime was not authorized.
- Endpoint access risk exists.
- Real KG read risk exists.
- Generation, export, or writeback mis-trigger risk exists.

NO-GO means stop, report, and wait for user review. It does not mean retry, broaden scope, run services, access endpoints, run Ollama, or continue into real use or trial use.

## 14. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Preview-only validation before model upgrade remains internal technical validation only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 15. Final Compliance Statement

- This stage only adds one docs file.
- This stage did not run Ollama.
- This stage did not execute `ollama list`.
- This stage did not execute any Ollama command.
- This stage did not execute `ollama pull qwen3.6:35b`.
- This stage did not upgrade, pull, delete, or replace any model.
- This stage did not execute actual preflight commands.
- This stage did not perform expanded internet lookup.
- This stage did not run the ZDoc service.
- This stage did not access any endpoint.
- This stage did not read real KG.
- This stage did not parse real KG JSON.
- This stage did not execute another directory scan.
- This stage did not trigger generation, export, or writeback.
- This stage did not write `output`, `job`, or `export`.
- This stage did not modify code.
- This stage did not modify adapter, route, helper, or `main.py`.
- This stage did not modify frontend, tests, config, or JSON.
- This stage did not connect RAG, registry, or CI.
- This stage did not enter real use.
- This stage did not enter formal trial use.
- This stage did not enter controlled trial use.
- Model upgrade has not been executed.
- KG-RUNTIME-154 has not been entered.
