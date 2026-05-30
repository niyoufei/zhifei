# ZDoc Single-Model Upgrade Execution Explicit Approval Wait-State - KG-RUNTIME-149

## 1. Runtime Scope

- Stage: KG-RUNTIME-149
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only explicit approval wait-state
- New artifact: `docs/zdoc-single-model-upgrade-execution-explicit-approval-wait-state-kg-runtime-149.md`
- Stop line: do not enter KG-RUNTIME-150

KG-RUNTIME-149 only records the explicit approval wait-state for the single-model upgrade candidate carried forward from KG-RUNTIME-148.

This stage:

- Does not execute an upgrade.
- Does not run Ollama.
- Does not execute any model command.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not perform additional internet lookup.
- Does not enter real use, formal trial use, or controlled trial use.
- Does not enter KG-RUNTIME-150.

KG-RUNTIME-149 is not actual upgrade authorization. It keeps the execution gate closed until the user provides complete, item-by-item, explicit approval in a later reviewed node.

## 2. Baseline

KG-RUNTIME-148 ended with the following recorded state:

- End HEAD: `0b12e8947b88723301fdbeb112b0b8708ad66281`
- Remote tag: `v0.1.531-zdoc-single-model-upgrade-authorization-decision-checkpoint`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-authorization-decision-checkpoint-kg-runtime-148.md`
- Authorization decision result: `NO-GO / pending explicit user approval`
- Current GO / NO-GO status: `NO-GO / pending explicit user approval`
- Worktree state after KG-RUNTIME-148: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-149 preflight observed:

- Start HEAD: `0b12e8947b88723301fdbeb112b0b8708ad66281`
- Baseline remote tag carried from KG-RUNTIME-148: `v0.1.531-zdoc-single-model-upgrade-authorization-decision-checkpoint`
- Worktree before this docs-only change: clean

KG-RUNTIME-148 also recorded that:

- The authorization decision result was still `NO-GO / pending explicit user approval`.
- The future user authorization template was not actual user authorization.
- The future command candidate was not authorization.
- The only single-model candidate remained `qwen3.6:35b`.
- Model upgrade had not been executed.
- Real use, formal trial use, and controlled trial use had not been entered.

## 3. Source Boundary

KG-RUNTIME-149 is based only on the following authorized project documents:

1. KG-RUNTIME-148 authorization decision checkpoint document:
   `docs/zdoc-single-model-upgrade-execution-authorization-decision-checkpoint-kg-runtime-148.md`
2. KG-RUNTIME-147 final explicit user authorization review document, if needed:
   `docs/zdoc-single-model-upgrade-execution-final-explicit-user-authorization-review-kg-runtime-147.md`
3. KG-RUNTIME-146 user-authorization gap closure document, if needed:
   `docs/zdoc-single-model-upgrade-execution-user-authorization-gap-closure-kg-runtime-146.md`
4. KG-RUNTIME-145 authorization intake document, if needed:
   `docs/zdoc-single-model-upgrade-execution-explicit-command-authorization-intake-kg-runtime-145.md`
5. KG-RUNTIME-144 final approval checkpoint document, if needed:
   `docs/zdoc-single-model-upgrade-execution-final-user-approval-checkpoint-kg-runtime-144.md`
6. KG-RUNTIME-143 readiness confirmation document, if needed:
   `docs/zdoc-single-model-upgrade-execution-readiness-confirmation-kg-runtime-143.md`
7. KG-RUNTIME-142 explicit authorization gate document, if needed:
   `docs/zdoc-single-model-upgrade-execution-explicit-user-authorization-gate-kg-runtime-142.md`
8. KG-RUNTIME-141 authorization request document, if needed:
   `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
9. KG-RUNTIME-140 strategy document, if needed:
   `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
10. KG-RUNTIME-139 query document, if needed:
    `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`

This stage does not add internet lookup, does not re-collect the local model inventory, does not execute `ollama list`, does not expand model families, does not adjust candidate priority, and does not introduce any external new basis.

This stage also does not treat any authorization template as actual user authorization. It does not treat this explicit approval wait-state as actual upgrade authorization.

## 4. Candidate Confirmation

The only single-model candidate for this explicit approval wait-state is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 through KG-RUNTIME-148
- Current state: explicit approval wait-state candidate only
- Upgrade executed by KG-RUNTIME-149: no
- Upgrade allowed in KG-RUNTIME-149: no
- Upgrade allowed in an automatic later node: no
- Requirement for any later execution node: the user must explicitly authorize the exact model name, final command whitelist, online pull behavior, latest-tag behavior, old-model retention policy, no-delete boundary, retry rule, download-size boundary, execution time window, and validation boundary.

No other model candidate is confirmed by KG-RUNTIME-149. No model family is expanded by this stage.

## 5. Explicit Approval Wait-State Result

Explicit approval wait-state result:

`NO-GO / pending explicit user approval`

Reasons:

- No user approval has been observed for actual upgrade of `qwen3.6:35b`.
- No user approval has been observed for the final command whitelist.
- No user approval has been observed for online pull / network download.
- No user approval has been observed for latest-tag impact strategy.
- No user approval has been observed for old-model retention and explicit prohibition on deleting old models.
- No user approval has been observed for failure retry, retry count, download size, or execution time window.
- Therefore KG-RUNTIME-149 can only wait for explicit user approval.
- During the wait-state, no model upgrade command may be executed.

This result blocks `ollama pull qwen3.6:35b`, all Ollama commands, model upgrade, post-upgrade stability verification as an already-started phase, real use, formal trial use, controlled trial use, and KG-RUNTIME-150 execution.

## 6. Wait-State Evidence Review

Wait-state evidence review:

- KG-RUNTIME-148 authorization decision result was checked.
- KG-RUNTIME-148 still records `NO-GO / pending explicit user approval`.
- The future user authorization template remains a template only and is not actual authorization.
- No user item-by-item authorization record has been observed.
- KG-RUNTIME-149 cannot execute `ollama pull qwen3.6:35b`.
- KG-RUNTIME-149 cannot enter actual upgrade execution.
- KG-RUNTIME-149 can only remain in explicit approval wait-state.

Missing, implied, partial, or template-only approvals remain insufficient for GO.

## 7. Wait-State Matrix

| 等待项 | 当前状态 | 是否可退出 wait-state | 退出条件 | 当前结论 |
|---|---|---|---|---|
| 唯一模型是否确认为 `qwen3.6:35b` | Docs candidate is `qwen3.6:35b`; execution approval is still missing | No | 用户明确批准后续节点仅针对 `qwen3.6:35b` | Remain in wait-state / pending explicit user approval |
| 是否允许联网拉取 | 未见用户明确批准 | No | 用户明确回复允许或不允许联网拉取 | Remain in wait-state / pending explicit user approval |
| 是否批准最终命令白名单 | 未见用户明确批准 | No | 用户明确批准唯一命令白名单 `ollama pull qwen3.6:35b` | Remain in wait-state / pending explicit user approval |
| 是否允许影响 `latest` 标签 | 未见用户明确批准 | No | 用户明确回复是否允许任何 `latest` 标签影响 | Remain in wait-state / pending explicit user approval |
| 是否要求保留旧模型 | 未见用户明确批准 | No | 用户明确要求保留全部旧模型 | Remain in wait-state / pending explicit user approval |
| 是否明确禁止删除旧模型 | 未见用户明确批准 | No | 用户明确禁止删除任何旧模型 | Remain in wait-state / pending explicit user approval |
| 是否允许失败后重试 | 未见用户明确批准 | No | 用户明确回复是否允许失败后重试 | Remain in wait-state / pending explicit user approval |
| 失败后允许重试次数 | 未见用户明确批准 | No | 用户明确给出最大重试次数，或回复 `0` | Remain in wait-state / pending explicit user approval |
| 是否设置最大下载体积 | 未见用户明确批准 | No | 用户明确给出最大下载体积，或确认不限制 | Remain in wait-state / pending explicit user approval |
| 是否设置执行时间窗口 | 未见用户明确批准 | No | 用户明确给出允许执行时间窗口 | Remain in wait-state / pending explicit user approval |
| 是否确认工作区必须 clean | 本阶段开始前 clean；未来执行仍需用户确认 | No | 用户明确确认未来执行前必须保持工作区 clean | Remain in wait-state / pending explicit user approval |
| 是否确认不得运行 ZDoc 服务 | 本阶段未运行服务；未来执行仍需用户确认 | No | 用户明确确认不得运行 ZDoc 服务 | Remain in wait-state / pending explicit user approval |
| 是否确认不得访问 endpoint | 本阶段未访问 endpoint；未来执行仍需用户确认 | No | 用户明确确认不得访问 endpoint | Remain in wait-state / pending explicit user approval |
| 是否确认不得读取真实 KG | 本阶段未读取真实 KG；未来执行仍需用户确认 | No | 用户明确确认不得读取真实 KG 文件正文内容 | Remain in wait-state / pending explicit user approval |
| 是否确认不得触发生成 / 导出 / 写回 | 本阶段未触发；未来执行仍需用户确认 | No | 用户明确确认不得触发生成 / 导出 / 写回 | Remain in wait-state / pending explicit user approval |
| 是否确认升级后仅进入稳定性验证 | 未见用户明确批准 | No | 用户明确确认升级后只能进入稳定性验证 | Remain in wait-state / pending explicit user approval |
| 是否确认升级后仍不得进入真实使用 / 试用 | 未见用户明确批准 | No | 用户明确确认升级后仍不得进入真实使用 / 试用 | Remain in wait-state / pending explicit user approval |
| 是否确认后续节点仍需回报和审核 | 未见用户明确批准 | No | 用户明确确认后续每一步仍需回报和审核 | Remain in wait-state / pending explicit user approval |

All missing, implied, partial, or template-only approvals remain `Remain in wait-state / pending explicit user approval`.

## 8. User Approval Text Required to Exit Wait-State

If the user wants a later node to consider exiting wait-state and entering actual upgrade execution, the user must provide an explicit reply that completes all required values. The following is only a future authorization template and does not represent authorization granted in KG-RUNTIME-149:

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

This template is only the required future approval format. It is not KG-RUNTIME-149 authorization, does not approve any command, and does not permit any model upgrade.

## 9. Future Command Candidate

KG-RUNTIME-149 does not execute any command candidate in this section.

The following command is only a future user-approved candidate command. It is not approved by KG-RUNTIME-149, was not run by KG-RUNTIME-149, and must not be executed later unless the user explicitly approves it in a later step.

Future user-approved candidate command / not executed in KG-RUNTIME-149:

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

## 10. Conditions to Exit Wait-State

Before any future stage may exit wait-state, all of the following must be satisfied:

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

If any precondition is missing, unclear, implied, or only present as a template, the future runtime stage must stop before executing model commands.

## 11. Hard Wait-State Persistence Conditions

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

## 12. Post-Upgrade Validation Boundary

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

## 13. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Model upgrade before preview-only validation remains internal technical validation only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 14. KG-RUNTIME-150 Recommendation

Recommended next stage:

`KG-RUNTIME-150: single-model upgrade execution explicit approval response intake docs-only`

KG-RUNTIME-150 must still not default to upgrade execution. Only after the user reviews KG-RUNTIME-149 and explicitly approves all of the following item by item may a later node consider actual execution:

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

If the user does not approve these items one by one, KG-RUNTIME-150 should continue to remain docs-only and must not execute an upgrade.

KG-RUNTIME-149 does not enter KG-RUNTIME-150.

## 15. Final Compliance Statement

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
- KG-RUNTIME-150 has not been entered.
