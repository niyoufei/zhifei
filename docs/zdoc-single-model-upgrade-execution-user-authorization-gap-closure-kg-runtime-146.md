# ZDoc Single-Model Upgrade Execution User-Authorization Gap Closure - KG-RUNTIME-146

## 1. Runtime Scope

- Stage: KG-RUNTIME-146
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only user-authorization gap closure
- New artifact: `docs/zdoc-single-model-upgrade-execution-user-authorization-gap-closure-kg-runtime-146.md`
- Stop line: do not enter KG-RUNTIME-147

KG-RUNTIME-146 only closes the user-authorization gap as text. It does not execute an upgrade, does not run Ollama, does not execute any model command, does not execute `ollama pull qwen3.6:35b`, does not perform additional internet lookup, does not enter real use or trial use, and does not enter KG-RUNTIME-147.

This stage records that the authorization state after KG-RUNTIME-145 remains incomplete. A future approval template, future command candidate, or docs-only gap closure cannot be treated as actual user authorization.

## 2. Baseline

KG-RUNTIME-145 ended with the following recorded state:

- End HEAD: `6295d851f8c50a6b160b36b51e566d82efac0f8f`
- Remote tag: `v0.1.528-zdoc-single-model-upgrade-command-authorization-intake`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-explicit-command-authorization-intake-kg-runtime-145.md`
- Authorization intake status: `NO-GO / pending explicit user approval`
- GO / NO-GO conclusion: `NO-GO`
- Worktree state after KG-RUNTIME-145: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-145 also recorded that no model command was authorized or executed, and that `ollama pull qwen3.6:35b` remained only a future user-authorization candidate command.

## 3. Source Boundary

KG-RUNTIME-146 is based only on the following authorized project documents:

1. KG-RUNTIME-145 explicit command authorization intake document:
   `docs/zdoc-single-model-upgrade-execution-explicit-command-authorization-intake-kg-runtime-145.md`
2. KG-RUNTIME-144 final user approval checkpoint document:
   `docs/zdoc-single-model-upgrade-execution-final-user-approval-checkpoint-kg-runtime-144.md`
3. KG-RUNTIME-143 readiness confirmation document:
   `docs/zdoc-single-model-upgrade-execution-readiness-confirmation-kg-runtime-143.md`
4. KG-RUNTIME-142 explicit authorization gate document:
   `docs/zdoc-single-model-upgrade-execution-explicit-user-authorization-gate-kg-runtime-142.md`
5. KG-RUNTIME-141 authorization request document:
   `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
6. KG-RUNTIME-140 strategy document:
   `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
7. KG-RUNTIME-139 lookup document:
   `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`

This stage does not add internet lookup, does not re-collect the local model inventory, does not execute `ollama list`, does not expand model families, does not adjust candidate priority, and does not introduce any external new basis.

The source boundary remains limited to the previously recorded KG-RUNTIME-139 through KG-RUNTIME-145 documents. KG-RUNTIME-146 does not treat a template authorization format as actual user authorization and does not treat this gap closure as actual user authorization.

## 4. Candidate Confirmation

The only single-model candidate carried into this authorization gap closure is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 recorded the `qwen3` family lookup result; KG-RUNTIME-140 ranked `qwen3.6:35b` as the P0 primary single-model authorization-request candidate; KG-RUNTIME-141 selected `qwen3.6:35b` as the only proposed single-model upgrade candidate; KG-RUNTIME-142 retained `qwen3.6:35b` as the only candidate for a future explicit authorization gate; KG-RUNTIME-143 confirmed `qwen3.6:35b` as the only readiness-confirmation candidate; KG-RUNTIME-144 retained `qwen3.6:35b` as the only final approval checkpoint candidate; KG-RUNTIME-145 retained `qwen3.6:35b` as the only explicit command authorization intake candidate.
- Current state: authorization gap closure candidate only.
- Upgrade executed by KG-RUNTIME-146: no.
- Upgrade allowed in KG-RUNTIME-146: no.
- Upgrade allowed in an automatic later node: no.
- Requirement for any later execution node: the user must explicitly authorize the exact model name, final command whitelist, online pull behavior, latest-tag behavior, old-model retention policy, no-delete boundary, retry rule, download-size boundary, execution time window, and validation boundary.

No other candidate is confirmed by this stage. `qwen3-next:80b`, `deepseek-r1:latest`, and `qwen3-coder-next:latest` remain outside the KG-RUNTIME-146 single-model authorization gap closure.

## 5. Current GO / NO-GO Status

Current status: `NO-GO / pending explicit user approval`

Reasons:

- User item-by-item authorization has not been formed.
- The command whitelist has not been finally approved by the user.
- Online pull / network download has not been finally approved by the user.
- Latest-tag impact has not been confirmed by the user.
- Old-model retention and the prohibition on deleting old models have not been confirmed by the user.
- Download size, failure retry, retry count, and execution time window have not been confirmed by the user.
- Therefore KG-RUNTIME-146 must not enter actual upgrade execution.

This status prevents KG-RUNTIME-146 from executing `ollama pull qwen3.6:35b`, running any Ollama command, entering stability verification, entering real use, or entering any trial stage.

## 6. Authorization Gap Closure Matrix

| Authorization gap item | Current status | Closed | Reason not closed | Explicit user reply required |
|---|---|---:|---|---|
| Confirm the only model is `qwen3.6:35b` | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that the only later execution target may be `qwen3.6:35b` |
| Allow online pull / network download | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply whether online pull is allowed or prohibited |
| Approve final command whitelist | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply whether `ollama pull qwen3.6:35b` is approved as the only future command |
| Allow any `latest` tag impact | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply whether any `latest` tag may be affected |
| Require old-model retention | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply whether all old models must be retained |
| Explicitly prohibit deleting old models | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that deleting old models remains prohibited |
| Allow retry after failure | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply whether failure retry is allowed |
| Set failure retry count | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply with maximum retry count, or `0` if no retry is allowed |
| Set maximum download size | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply with a maximum size, or explicitly confirm no size limit |
| Set execution time window | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply with the permitted execution time window |
| Confirm worktree must be clean | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that future execution requires clean worktree |
| Confirm ZDoc service must not run | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that ZDoc service runtime remains prohibited |
| Confirm endpoint access is prohibited | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that no endpoint may be accessed |
| Confirm real KG reading is prohibited | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that real KG file body content must not be read |
| Confirm generation / export / writeback are prohibited | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that generation, export, and writeback remain prohibited |
| Confirm upgrade success only enters stability verification | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that upgrade success may only enter stability verification |
| Confirm upgrade success still does not enter real use or trial use | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that real use, formal trial use, and controlled trial use remain prohibited |
| Confirm later nodes still require report and review | `NO-GO / pending explicit user approval` | No | Not closed / pending explicit user approval | Reply that every later step requires report, review, and approval |

All missing, implied, template-only, or partial approvals remain `Not closed / pending explicit user approval`.

## 7. User Approval Text Required for Closure

If the user wants a later node to consider actual upgrade execution, the user must provide an explicit reply that completes all required values. The following is only a future authorization template and does not represent authorization granted in KG-RUNTIME-146:

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

This template is only the required future approval format. It is not KG-RUNTIME-146 authorization, does not approve any command, and does not permit any model upgrade.

## 8. Future Command Candidate

KG-RUNTIME-146 does not execute any command candidate in this section.

The following command is only a future user-authorized candidate command. It is not approved by KG-RUNTIME-146, was not run by KG-RUNTIME-146, and must not be executed later unless the user explicitly approves it in a later step.

Future user-authorized candidate command / not executed in KG-RUNTIME-146:

```bash
ollama pull qwen3.6:35b
```

Command candidate constraints:

- The command must be strictly limited to `qwen3.6:35b`.
- No wildcard model pattern is allowed.
- No batch model command is allowed.
- No delete command is allowed.
- No automatic all-model upgrade command is allowed.
- No command may be treated as approved unless the user explicitly confirms it later.
- No future node may broaden this candidate into another model, another command, or a batch operation without separate user authorization.

## 9. GO Preconditions

Before any future stage may move from `NO-GO / pending explicit user approval` to `GO`, all of the following must be satisfied:

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

## 10. Hard NO-GO Conditions

A current or future upgrade preparation or execution node must remain `NO-GO / pending explicit user approval` if any of the following conditions apply:

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

## 11. Post-Upgrade Validation Boundary

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

## 12. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Model upgrade before preview-only validation remains internal technical validation only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 13. KG-RUNTIME-147 Recommendation

Recommended next stage:

`KG-RUNTIME-147: single-model upgrade execution final explicit user authorization review docs-only`

KG-RUNTIME-147 should remain docs-only by default and must not default to upgrade execution.

Only after the user reviews KG-RUNTIME-146 and explicitly approves all of the following may a later node consider actual upgrade execution:

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

If the user does not approve these items one by one, KG-RUNTIME-147 should continue to remain docs-only and must not execute an upgrade.

KG-RUNTIME-146 does not enter KG-RUNTIME-147.

## 14. Final Compliance Statement

- This stage only adds one docs file.
- This stage did not run Ollama.
- This stage did not execute `ollama list`.
- This stage did not execute any Ollama command.
- This stage did not execute `ollama pull qwen3.6:35b`.
- This stage did not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- This stage did not upgrade, pull, delete, or replace any model.
- This stage did not perform additional internet lookup.
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
- This stage did not add `.pyc` or `__pycache__`.
- This stage did not enter real use.
- This stage did not enter formal trial use.
- This stage did not enter controlled trial use.
- Model upgrade has not been executed.
- KG-RUNTIME-147 has not been entered.
