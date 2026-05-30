# ZDoc Single-Model Upgrade Execution Final Explicit User Authorization Review - KG-RUNTIME-147

## 1. Runtime Scope

- Stage: KG-RUNTIME-147
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only final explicit user authorization review
- New artifact: `docs/zdoc-single-model-upgrade-execution-final-explicit-user-authorization-review-kg-runtime-147.md`
- Stop line: do not enter KG-RUNTIME-148

KG-RUNTIME-147 is only a docs-only final explicit user authorization review. It reviews whether the authorization gap recorded by KG-RUNTIME-146 has been closed by an itemized user approval after KG-RUNTIME-146.

This stage:

- Does not execute an upgrade.
- Does not run Ollama.
- Does not execute any model command.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not perform additional internet lookup.
- Does not enter real use, formal trial use, or controlled trial use.
- Does not enter KG-RUNTIME-148.

KG-RUNTIME-147 is not actual upgrade authorization. It is a final review record that keeps the execution gate closed unless explicit user approval is present and complete.

## 2. Baseline

KG-RUNTIME-146 ended with the following recorded state:

- End HEAD: `8ecbc50a51e68818099a4493da0a8653e0ec70bb`
- Remote tag: `v0.1.529-zdoc-single-model-upgrade-user-authorization-gap-closure`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-user-authorization-gap-closure-kg-runtime-146.md`
- Current GO / NO-GO status: `NO-GO / pending explicit user approval`
- Worktree state after KG-RUNTIME-146: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-147 preflight observed:

- Start HEAD: `8ecbc50a51e68818099a4493da0a8653e0ec70bb`
- Local tag at start HEAD: none observed by `git tag --points-at HEAD`
- Worktree before this docs-only change: clean

KG-RUNTIME-146 also recorded that:

- The authorization gap was still not closed by actual user approval.
- The future authorization template was not authorization.
- The future command candidate was not authorization.
- The only single-model candidate remained `qwen3.6:35b`.
- Model upgrade had not been executed.
- Real use, formal trial use, and controlled trial use had not been entered.

## 3. Source Boundary

KG-RUNTIME-147 is based only on the following authorized project documents:

1. KG-RUNTIME-146 user-authorization gap closure document:
   `docs/zdoc-single-model-upgrade-execution-user-authorization-gap-closure-kg-runtime-146.md`
2. KG-RUNTIME-145 authorization intake document:
   `docs/zdoc-single-model-upgrade-execution-explicit-command-authorization-intake-kg-runtime-145.md`
3. KG-RUNTIME-144 final approval checkpoint document:
   `docs/zdoc-single-model-upgrade-execution-final-user-approval-checkpoint-kg-runtime-144.md`
4. KG-RUNTIME-143 readiness confirmation document:
   `docs/zdoc-single-model-upgrade-execution-readiness-confirmation-kg-runtime-143.md`
5. KG-RUNTIME-142 explicit authorization gate document:
   `docs/zdoc-single-model-upgrade-execution-explicit-user-authorization-gate-kg-runtime-142.md`
6. KG-RUNTIME-141 authorization request document:
   `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
7. KG-RUNTIME-140 strategy document:
   `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
8. KG-RUNTIME-139 query document:
   `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`

This stage does not add internet lookup, does not re-collect the local model inventory, does not execute `ollama list`, does not expand model families, does not adjust candidate priority, and does not introduce any external new basis.

This stage also does not treat the KG-RUNTIME-146 authorization template as actual user authorization. It does not treat this final authorization review as actual upgrade authorization.

## 4. Candidate Confirmation

The only single-model candidate carried into this final authorization review is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 through KG-RUNTIME-146.
- Current state: final authorization review candidate only.
- Upgrade executed by KG-RUNTIME-147: no.
- Upgrade allowed in KG-RUNTIME-147: no.
- Upgrade allowed in an automatic later node: no.
- Requirement for any later execution node: the user must explicitly authorize the exact model name, final command whitelist, online pull behavior, latest-tag behavior, old-model retention policy, no-delete boundary, retry rule, download-size boundary, execution time window, and validation boundary.

No other model candidate is confirmed by KG-RUNTIME-147. No model family is expanded by this stage.

## 5. Final Authorization Review Result

Final authorization review result:

`NO-GO / pending explicit user approval`

Reasons:

- No user item-by-item approval has been observed after KG-RUNTIME-146.
- No user approval has been observed for actual upgrade of `qwen3.6:35b`.
- No user approval has been observed for the final command whitelist.
- No user approval has been observed for online pull / network download.
- No user approval has been observed for latest-tag impact strategy.
- No user approval has been observed for old-model retention and explicit prohibition on deleting old models.
- No user approval has been observed for failure retry, retry count, download size, or execution time window.
- Therefore KG-RUNTIME-147 must not enter actual upgrade execution.

This result blocks `ollama pull qwen3.6:35b`, all Ollama commands, model upgrade, stability verification as a post-upgrade phase, real use, formal trial use, controlled trial use, and KG-RUNTIME-148 execution.

## 6. Final Authorization Review Matrix

| 复核项 | 当前状态 | 是否满足 | 复核结论 | 用户仍需明确回复的内容 |
|---|---|---|---|---|
| 唯一模型是否确认为 `qwen3.6:35b` | Docs candidate is `qwen3.6:35b`; execution approval is still missing | Not satisfied / pending explicit user approval | NO-GO | 明确回复后续节点是否只允许针对 `qwen3.6:35b` |
| 是否允许联网拉取 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复允许或不允许联网拉取 |
| 是否批准最终命令白名单 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复是否批准唯一命令白名单 `ollama pull qwen3.6:35b` |
| 是否允许影响 `latest` 标签 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复是否允许任何 `latest` 标签影响 |
| 是否要求保留旧模型 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复是否要求保留全部旧模型 |
| 是否明确禁止删除旧模型 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复是否禁止删除任何旧模型 |
| 是否允许失败后重试 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复是否允许失败后重试 |
| 失败后允许重试次数 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复最大重试次数，或回复 `0` |
| 是否设置最大下载体积 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复最大下载体积，或确认不限制 |
| 是否设置执行时间窗口 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复允许执行时间窗口 |
| 是否确认工作区必须 clean | 当前工作区 clean，但未来执行仍需用户确认 | Not satisfied / pending explicit user approval | NO-GO | 明确回复未来执行前必须保持工作区 clean |
| 是否确认不得运行 ZDoc 服务 | 本阶段未运行服务；未来执行仍需用户确认 | Not satisfied / pending explicit user approval | NO-GO | 明确回复不得运行 ZDoc 服务 |
| 是否确认不得访问 endpoint | 本阶段未访问 endpoint；未来执行仍需用户确认 | Not satisfied / pending explicit user approval | NO-GO | 明确回复不得访问 endpoint |
| 是否确认不得读取真实 KG | 本阶段未读取真实 KG；未来执行仍需用户确认 | Not satisfied / pending explicit user approval | NO-GO | 明确回复不得读取真实 KG 文件正文内容 |
| 是否确认不得触发生成 / 导出 / 写回 | 本阶段未触发；未来执行仍需用户确认 | Not satisfied / pending explicit user approval | NO-GO | 明确回复不得触发生成 / 导出 / 写回 |
| 是否确认升级后仅进入稳定性验证 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复升级后只能进入稳定性验证 |
| 是否确认升级后仍不得进入真实使用 / 试用 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复升级后仍不得进入真实使用 / 试用 |
| 是否确认后续节点仍需回报和审核 | 未见用户明确批准 | Not satisfied / pending explicit user approval | NO-GO | 明确回复后续每一步仍需回报和审核 |

All missing, implied, partial, or template-only approvals remain `Not satisfied / pending explicit user approval`.

## 7. User Approval Text Required Before Any Execution

If the user wants a later node to consider actual upgrade execution, the user must provide an explicit reply that completes all required values. The following is only a future authorization template and does not represent authorization granted in KG-RUNTIME-147:

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

This template is only the required future approval format. It is not KG-RUNTIME-147 authorization, does not approve any command, and does not permit any model upgrade.

## 8. Future Command Candidate

KG-RUNTIME-147 does not execute any command candidate in this section.

The following command is only a future user-approved candidate command. It is not approved by KG-RUNTIME-147, was not run by KG-RUNTIME-147, and must not be executed later unless the user explicitly approves it in a later step.

Future user-approved candidate command / not executed in KG-RUNTIME-147:

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

If any precondition is missing, unclear, implied, or only present as a template, the future runtime stage must stop before executing model commands.

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

## 13. KG-RUNTIME-148 Recommendation

Recommended next stage:

`KG-RUNTIME-148: single-model upgrade execution authorization decision checkpoint docs-only`

KG-RUNTIME-148 should still not default to upgrade execution. Only after the user reviews KG-RUNTIME-147 and explicitly approves all of the following item by item may a later node consider actual execution:

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

If the user does not approve these items one by one, KG-RUNTIME-148 should continue to remain docs-only and must not execute an upgrade.

KG-RUNTIME-147 does not enter KG-RUNTIME-148.

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
- KG-RUNTIME-148 has not been entered.
