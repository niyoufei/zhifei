# ZDoc Single-Model Upgrade Execution Final User Approval Checkpoint - KG-RUNTIME-144

## 1. Runtime Scope

- Stage: KG-RUNTIME-144
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only single-model upgrade execution final user approval checkpoint
- New artifact: `docs/zdoc-single-model-upgrade-execution-final-user-approval-checkpoint-kg-runtime-144.md`
- Stop line: do not enter KG-RUNTIME-145

KG-RUNTIME-144 is only a docs-only final user approval checkpoint for a possible future single-model upgrade execution path.

This stage does not execute an upgrade, does not run Ollama, does not execute any model command, does not execute `ollama pull qwen3.6:35b`, does not perform additional internet lookup, does not enter real use or trial use, and does not enter KG-RUNTIME-145.

This checkpoint is not actual execution authorization. It records what the user must explicitly approve before any later node may consider actual upgrade execution.

## 2. Baseline

KG-RUNTIME-143 ended with the following recorded state:

- End HEAD: `3afb962721fe296a1febf4a973700b27d2704a4f`
- Remote tag: `v0.1.526-zdoc-single-model-upgrade-readiness-confirmation`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-readiness-confirmation-kg-runtime-143.md`
- Worktree state after KG-RUNTIME-143: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-144 preflight observed:

- Current branch: `main`
- Start HEAD: `3afb962721fe296a1febf4a973700b27d2704a4f`
- Local tag at start HEAD: none observed by `git tag --points-at HEAD`
- Worktree before this docs-only change: clean

The KG-RUNTIME-143 non-execution boundaries remain active:

- Ollama was not run.
- `ollama list` was not executed.
- No Ollama command was executed.
- `ollama pull qwen3.6:35b` was not executed.
- No model was upgraded, pulled, deleted, or replaced.
- No ZDoc service was run.
- No endpoint was accessed.
- No real KG file body content was read.
- No real KG JSON was parsed.
- No generation, export, or writeback was triggered.
- No `output`, `job`, or `export` write occurred.
- Real use and trial use were not entered.
- Model upgrade has not been executed.

## 3. Source Boundary

KG-RUNTIME-144 is based only on the following authorized source documents:

1. KG-RUNTIME-143 readiness confirmation document:
   `docs/zdoc-single-model-upgrade-execution-readiness-confirmation-kg-runtime-143.md`
2. KG-RUNTIME-142 explicit authorization gate document:
   `docs/zdoc-single-model-upgrade-execution-explicit-user-authorization-gate-kg-runtime-142.md`
3. KG-RUNTIME-141 authorization request document:
   `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
4. KG-RUNTIME-140 strategy document:
   `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
5. KG-RUNTIME-139 lookup document:
   `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`

This stage does not add internet lookup, does not re-collect the local model inventory, does not execute `ollama list`, does not expand model families, does not adjust candidate priority, and does not introduce any external new basis.

The source boundary remains limited to the previously recorded KG-RUNTIME-139 through KG-RUNTIME-143 documents. KG-RUNTIME-144 does not treat any command, model registry, local model list, directory scan, endpoint, or newly queried source as additional evidence.

## 4. Final Candidate Confirmation

The only single-model candidate allowed to remain in the final approval checkpoint is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 recorded the `qwen3` family lookup result; KG-RUNTIME-140 ranked `qwen3.6:35b` as the P0 primary single-model authorization-request candidate; KG-RUNTIME-141 selected `qwen3.6:35b` as the only proposed single-model upgrade candidate; KG-RUNTIME-142 retained `qwen3.6:35b` as the only candidate for a future explicit authorization gate; KG-RUNTIME-143 confirmed `qwen3.6:35b` as the only readiness-confirmation candidate.
- Current state: final approval checkpoint candidate only.
- Upgrade executed by KG-RUNTIME-144: no.
- Upgrade allowed in KG-RUNTIME-144: no.
- Upgrade allowed in an automatic later node: no.
- Requirement for any later execution node: the user must explicitly authorize the exact model name, final command whitelist, online pull behavior, latest-tag behavior, old-model retention policy, no-delete boundary, retry rule, download-size boundary, execution time window, and validation boundary.

No other candidate is confirmed by this stage. `qwen3-next:80b`, `deepseek-r1:latest`, and `qwen3-coder-next:latest` remain outside the KG-RUNTIME-144 single-model final approval checkpoint.

## 5. Final Approval Checklist

| Approval item | Current status | Satisfied | Gap | Explicit user reply required |
|---|---|---:|---|---|
| Confirm the only model is `qwen3.6:35b` | Pending explicit user approval | No | The user has not yet approved the final execution target in KG-RUNTIME-144 | Reply that the only later execution target may be `qwen3.6:35b` |
| Allow online pull / network download | Pending explicit user approval | No | Network pull permission is not granted | Reply whether online pull is allowed or prohibited |
| Approve future command candidate | Pending explicit user approval | No | No command whitelist is approved for execution | Reply whether `ollama pull qwen3.6:35b` is approved as the only future command |
| Allow any `latest` tag impact | Pending explicit user approval | No | Latest-tag impact policy is not decided | Reply whether any `latest` tag may be affected |
| Require old-model retention | Pending explicit user approval | No | Retention policy is not final | Reply whether all old models must be retained |
| Explicitly prohibit deleting old models | Pending explicit user approval | No | No-delete rule must be restated for execution | Reply that deleting old models remains prohibited |
| Allow retry after failure | Pending explicit user approval | No | Retry permission is not granted | Reply whether failure retry is allowed |
| Set maximum retry count after failure | Pending explicit user approval | No | Retry count is not defined | Reply with maximum retry count, or `0` if no retry is allowed |
| Set maximum download size | Pending explicit user approval | No | Download-size boundary is not confirmed | Reply with a maximum size, or explicitly confirm no size limit |
| Set execution time window | Pending explicit user approval | No | Execution window is not confirmed | Reply with the permitted execution time window |
| Confirm worktree must be clean | Pending explicit user approval | No | Future execution must re-check clean state | Reply that future execution requires clean worktree |
| Confirm ZDoc service must not run | Pending explicit user approval | No | Runtime boundary must be restated for execution | Reply that ZDoc service runtime remains prohibited |
| Confirm endpoint access is prohibited | Pending explicit user approval | No | Endpoint boundary must be restated for execution | Reply that no endpoint may be accessed |
| Confirm real KG reading is prohibited | Pending explicit user approval | No | Real KG boundary must be restated for execution | Reply that real KG file body content must not be read |
| Confirm generation / export / writeback are prohibited | Pending explicit user approval | No | Output-chain boundary must be restated for execution | Reply that generation, export, and writeback remain prohibited |
| Confirm upgrade success only enters stability verification | Pending explicit user approval | No | Post-upgrade phase is not finally approved | Reply that upgrade success may only enter stability verification |
| Confirm upgrade success still does not enter real use or trial use | Pending explicit user approval | No | Trial boundary must be restated for execution | Reply that real use, formal trial use, and controlled trial use remain prohibited |
| Confirm later nodes still require report and review | Pending explicit user approval | No | Later-stage governance is not finally approved | Reply that every later step requires report, review, and approval |

Final approval state:

- Current state: `NO-GO / pending explicit user approval`
- Reason: KG-RUNTIME-144 is a checkpoint only. Execution-specific authorization remains incomplete.
- Consequence: no upgrade command may be executed by KG-RUNTIME-144 or by any later node unless the user explicitly authorizes all required items again.

## 6. Future Command Candidate

KG-RUNTIME-144 does not execute any command candidate in this section.

The following command is only a future final-approval candidate command. It is not approved by KG-RUNTIME-144, was not run by KG-RUNTIME-144, and must not be executed later unless the user explicitly approves it in a later step.

Future final-approval candidate command / not executed in KG-RUNTIME-144:

```bash
ollama pull qwen3.6:35b
```

Command candidate constraints:

- The command must be strictly limited to `qwen3.6:35b`.
- No wildcard model pattern is allowed.
- No batch model command is allowed.
- No delete command is allowed.
- No automatic all-model upgrade command is allowed.
- No long-running service command is allowed.
- No command may be treated as approved unless the user explicitly confirms it later.
- No future node may broaden this candidate into another model, another command, or a batch operation without separate user authorization.

## 7. Required User Approval Wording

If the user wants to approve actual upgrade execution in a future stage, the user must provide an explicit authorization reply that includes at least the following wording and completed values.

Required future authorization format:

- 我明确授权后续节点仅针对 `qwen3.6:35b`。
- 我允许 / 不允许联网拉取。
- 我批准的命令白名单为：`ollama pull qwen3.6:35b`。
- 我要求保留旧模型。
- 我禁止删除任何旧模型。
- 我允许失败后最多重试 X 次。
- 我确认最大下载体积限制为 X，或确认不限制。
- 我确认执行时间窗口为 X。
- 我确认升级后仅进入稳定性验证。
- 我确认不得进入真实使用 / 试用。
- 我确认后续每一步仍需回报和审核。

This required wording is only a future approval template. KG-RUNTIME-144 does not treat this template, this document, or any prior stage as actual user authorization.

## 8. Explicit NO-GO Conditions

A current or future upgrade preparation or execution node must be marked `NO-GO / pending explicit user approval` if any of the following conditions apply:

- The user has not explicitly authorized the exact execution step.
- The user authorization content is incomplete.
- The model name is not exactly `qwen3.6:35b`.
- The command is not the single-model command explicitly approved by the user.
- There is batch upgrade risk.
- There is old-model deletion risk.
- There is automatic replacement of multiple `latest` tags risk.
- The worktree is not clean.
- A service is found running and service runtime was not authorized.
- There is endpoint access risk.
- There is real KG file body read risk.
- There is real KG JSON parse risk.
- There is generation, export, or writeback risk.
- Download size has not been confirmed.
- Network conditions and online pull permission have not been confirmed.
- Disk-space risk has not been confirmed.
- Execution time window has not been confirmed.
- Codex cannot clearly report the executed command, result, changed files, tag state, and push state.

NO-GO means stop the stage, report the reason, and wait for user review. It does not mean retry, broaden the command set, delete models, run services, access endpoints, or continue into real use or trial use.

## 9. Execution Preconditions for Future Runtime

If a later stage enters actual upgrade execution, all of the following must be satisfied before any model command is allowed:

1. The user explicitly approves model name: `qwen3.6:35b`.
2. The user explicitly approves the final command whitelist.
3. The user explicitly approves whether online pull / network download is allowed.
4. The user explicitly approves whether any command may affect a `latest` tag.
5. The user explicitly approves old-model retention policy.
6. The user explicitly approves that deleting old models remains prohibited.
7. The user explicitly approves failure retry rules.
8. The user explicitly approves a download-size limit, or explicitly confirms that no size limit is imposed.
9. The user explicitly approves the execution time window.
10. The worktree is clean.
11. The current HEAD and tag state are recorded.
12. The ZDoc service has not been run.
13. No endpoint has been accessed.
14. No real KG file body content has been read.
15. No real KG JSON has been parsed.
16. No generation, export, or writeback has been triggered.
17. Completion of any later upgrade can lead only to stability verification.

If any precondition is missing, unclear, or only implied, the future runtime stage must stop before executing model commands.

## 10. Post-Upgrade Validation Boundary

Even if a later explicitly authorized stage completes the model upgrade, the only next allowed phase is stability verification. It is not real use, not formal trial use, and not controlled trial use.

Stability verification must include at least:

- Confirm the model can load.
- Confirm basic question-answer stability.
- Confirm long-text response stability.
- Confirm technical-bid-style text output stability.
- Confirm preview-only chain compatibility.
- Confirm generation, export, and writeback paths are not triggered.
- Confirm real KG file body content is not read.
- Confirm real KG JSON is not parsed.
- Inspect output quality.
- Record failures and review notes.
- Record resource usage.
- Record response time.
- Record rollback or abort notes.

No stability verification may silently broaden into ZDoc service runtime, endpoint access, real KG reading, real KG JSON parsing, generation, export, writeback, real use, formal trial use, or controlled trial use.

## 11. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Model-upgrade-before-preview-only validation remains internal technical validation only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 12. KG-RUNTIME-145 Recommendation

Recommended next stage:

`KG-RUNTIME-145: single-model upgrade execution explicit command authorization intake`

KG-RUNTIME-145 should remain an explicit command authorization intake by default. It must not default to upgrade execution.

Only after the user reviews KG-RUNTIME-144 and explicitly approves all of the following may a later node consider actual upgrade execution:

- Model name: `qwen3.6:35b`
- Whether online pull / network download is allowed.
- Final command whitelist.
- Whether any command may affect a `latest` tag.
- Whether old models must be retained.
- Whether deleting old models remains prohibited.
- Failure retry rules.
- Download-size limit or explicit no-limit confirmation.
- Execution time window.
- Upgrade success leading only to stability verification.
- Real use, formal trial use, and controlled trial use remaining prohibited.

If the user does not approve these items one by one, KG-RUNTIME-145 should continue to remain docs-only and must not execute an upgrade.

KG-RUNTIME-144 does not enter KG-RUNTIME-145.

## 13. Final Compliance Statement

- This stage only adds one docs file.
- This stage does not run Ollama.
- This stage does not execute `ollama list`.
- This stage does not execute any Ollama command.
- This stage does not execute `ollama pull qwen3.6:35b`.
- This stage does not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- This stage does not upgrade, pull, delete, or replace any model.
- This stage does not perform additional internet lookup.
- This stage does not run the ZDoc service.
- This stage does not access any endpoint.
- This stage does not read real KG.
- This stage does not parse real KG JSON.
- This stage does not execute another directory scan.
- This stage does not trigger generation, export, or writeback.
- This stage does not write `output`, `job`, or `export`.
- This stage does not modify code.
- This stage does not modify frontend, tests, config, or JSON.
- This stage does not connect RAG, registry, or CI.
- This stage does not add `.pyc` or `__pycache__`.
- This stage does not enter real use.
- This stage does not enter formal trial use.
- This stage does not enter controlled trial use.
- Model upgrade has not been executed.
- KG-RUNTIME-145 has not been entered.
