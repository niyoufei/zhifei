# ZDoc Single-Model Upgrade Execution Explicit Approval Response Intake - KG-RUNTIME-150

## 1. Runtime Scope

KG-RUNTIME-150 is a docs-only explicit approval response intake stage for the ZDoc single-model upgrade execution chain.

This stage only receives and checks whether a complete item-by-item explicit user approval response already exists after KG-RUNTIME-149.

This stage explicitly:

- Does not execute an upgrade.
- Does not run Ollama.
- Does not execute any model command.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not perform additional internet lookup.
- Does not enter real use, formal trial use, or controlled trial use.
- Does not enter KG-RUNTIME-151.

KG-RUNTIME-150 is not actual upgrade authorization and is not an execution node.

## 2. Baseline

KG-RUNTIME-149 ended with the following recorded state:

- End HEAD: `4290194623ddeffd59e26b0d22eddfaa062bc51f`
- Remote tag: `v0.1.532-zdoc-single-model-upgrade-explicit-approval-wait-state`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-explicit-approval-wait-state-kg-runtime-149.md`
- Explicit approval wait-state result: `NO-GO / pending explicit user approval`
- Current GO / NO-GO status: `NO-GO / pending explicit user approval`
- Worktree state after KG-RUNTIME-149: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-150 preflight observed:

- Start HEAD: `4290194623ddeffd59e26b0d22eddfaa062bc51f`
- Baseline remote tag carried from KG-RUNTIME-149: `v0.1.532-zdoc-single-model-upgrade-explicit-approval-wait-state`
- Worktree before this docs-only change: clean

## 3. Source Boundary

KG-RUNTIME-150 is based only on the following authorized project documents:

1. KG-RUNTIME-149 explicit approval wait-state document:
   `docs/zdoc-single-model-upgrade-execution-explicit-approval-wait-state-kg-runtime-149.md`
2. KG-RUNTIME-148 authorization decision checkpoint document:
   `docs/zdoc-single-model-upgrade-execution-authorization-decision-checkpoint-kg-runtime-148.md`
3. KG-RUNTIME-147 final explicit authorization review document:
   `docs/zdoc-single-model-upgrade-execution-final-explicit-user-authorization-review-kg-runtime-147.md`

This stage:

- Does not add internet lookup.
- Does not re-collect the local model inventory.
- Does not expand model families.
- Does not adjust candidate priority.
- Does not introduce any external new basis.
- Does not treat a wait-state template as actual user authorization.
- Does not treat general acceptance of the control route as actual command authorization.
- Does not treat this response intake stage as actual upgrade execution authorization.

## 4. Candidate Confirmation

The only single-model candidate for this response intake stage is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 through KG-RUNTIME-149, as carried forward by the authorized prior docs chain
- Current state: explicit approval response intake candidate only
- Upgrade executed by KG-RUNTIME-150: no
- Upgrade allowed in KG-RUNTIME-150: no
- Upgrade allowed in an automatic later node: no
- Requirement for any later execution path: complete explicit approval and a separate latest-version recheck / preflight docs-only gate must occur first

No other model candidate is confirmed by KG-RUNTIME-150. No model family is expanded by this stage.

## 5. Approval Response Intake Result

Authorization response status:

`incomplete / pending explicit user approval`

Current GO / NO-GO status:

`NO-GO / pending explicit user approval`

Reasoning:

- No user item-by-item approval response has been observed for actual upgrade of `qwen3.6:35b`.
- No user approval has been observed for the final command whitelist.
- No user approval has been observed for online pull / network download.
- No user approval has been observed for latest-tag impact strategy.
- No user approval has been observed for old-model retention and explicit prohibition on deleting old models.
- No user approval has been observed for failure retry, retry count, download size, or execution time window.
- General wording such as "按总控意见推进" represents route acceptance only and does not represent actual command authorization.
- Therefore KG-RUNTIME-150 must not enter actual upgrade execution.

This result blocks all Ollama commands, model upgrade, post-upgrade stability verification as an already-started phase, real use, formal trial use, controlled trial use, and KG-RUNTIME-151 execution.

## 6. Approval Response Intake Matrix

| 授权项 | 当前是否收到明确回复 | 当前状态 | 是否满足进入预检条件 | 缺口说明 |
|---|---|---|---|---|
| 唯一模型是否明确批准为 `qwen3.6:35b` | No | Missing / pending explicit user approval | No | 仅有候选记录，未见实际升级批准 |
| 是否允许联网拉取 | No | Missing / pending explicit user approval | No | 未见用户明确允许或不允许联网拉取 |
| 是否批准最终命令白名单 | No | Missing / pending explicit user approval | No | 未见最终命令白名单批准 |
| 命令白名单是否严格限定为 `ollama pull qwen3.6:35b` | No | Missing / pending explicit user approval | No | 未见用户确认唯一命令白名单 |
| 是否允许影响 `latest` 标签 | No | Missing / pending explicit user approval | No | 未见 latest 标签影响策略确认 |
| 是否要求保留旧模型 | No | Missing / pending explicit user approval | No | 未见旧模型保留策略确认 |
| 是否明确禁止删除旧模型 | No | Missing / pending explicit user approval | No | 未见用户明确禁止删除任何旧模型 |
| 是否允许失败后重试 | No | Missing / pending explicit user approval | No | 未见失败后是否可重试确认 |
| 失败后允许重试次数 | No | Missing / pending explicit user approval | No | 未见最大重试次数 |
| 是否设置最大下载体积 | No | Missing / pending explicit user approval | No | 未见下载体积限制或不限制确认 |
| 是否设置执行时间窗口 | No | Missing / pending explicit user approval | No | 未见执行时间窗口 |
| 是否确认工作区必须 clean | No | Missing / pending explicit user approval | No | 当前工作区为 clean，但未来执行要求仍需用户明确确认 |
| 是否确认不得运行 ZDoc 服务 | No | Missing / pending explicit user approval | No | 本阶段未运行服务，但未来执行边界仍需用户明确确认 |
| 是否确认不得访问 endpoint | No | Missing / pending explicit user approval | No | 本阶段未访问 endpoint，但未来执行边界仍需用户明确确认 |
| 是否确认不得读取真实 KG | No | Missing / pending explicit user approval | No | 本阶段未读取真实 KG，但未来执行边界仍需用户明确确认 |
| 是否确认不得触发生成 / 导出 / 写回 | No | Missing / pending explicit user approval | No | 本阶段未触发，但未来执行边界仍需用户明确确认 |
| 是否确认升级后仅进入稳定性验证 | No | Missing / pending explicit user approval | No | 未见升级后验证边界确认 |
| 是否确认升级后仍不得进入真实使用 / 试用 | No | Missing / pending explicit user approval | No | 未见升级后仍禁止真实使用 / 试用的确认 |
| 是否确认后续节点仍需回报和审核 | No | Missing / pending explicit user approval | No | 未见后续每一步仍需回报和审核的确认 |

Because every required execution authorization item remains missing or incomplete, KG-RUNTIME-150 remains `NO-GO / pending explicit user approval`.

## 7. Required User Approval Text for Next Step

If the user later wants to enter an upgrade-preflight path, the user must provide an explicit reply that completes all required values. The following is only a future authorization template and does not represent authorization granted in KG-RUNTIME-150:

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

This template is only the required future approval format. It is not KG-RUNTIME-150 authorization, does not approve any command, and does not permit any model upgrade.

## 8. Future Command Candidate

KG-RUNTIME-150 does not execute any command candidate in this section.

The following command is only a future user-approved candidate command. It is not approved by KG-RUNTIME-150, was not run by KG-RUNTIME-150, and must not be executed later unless the user explicitly approves it in a later reviewed step.

Future user-approved candidate command / not executed in KG-RUNTIME-150:

```bash
ollama pull qwen3.6:35b
```

Command candidate constraints:

- KG-RUNTIME-150 does not execute any command candidate.
- The command candidate is only for later final user approval.
- No command may be executed without complete explicit user authorization.
- The command must be strictly limited to `qwen3.6:35b`.
- No wildcard model pattern is allowed.
- No batch model command is allowed.
- No delete command is allowed.
- No automatic all-model upgrade command is allowed.

## 9. Decision for Next Runtime

Because authorization remains incomplete, the recommended next stage is:

`KG-RUNTIME-151: single-model upgrade latest-version recheck authorization gate docs-only`

KG-RUNTIME-151 must still not execute an upgrade. It should only confirm whether a latest-version read-only recheck is allowed, and define the recheck scope, sources, and prohibited boundaries.

Even if a future user approval response becomes complete, KG-RUNTIME-150 still must not directly enter actual upgrade execution. A separate single-model upgrade latest-version recheck / preflight docs-only gate must happen first.

## 10. Conditions to Move Beyond NO-GO

Before any future stage may move beyond `NO-GO / pending explicit user approval` into an upgrade-preflight path, all of the following must be satisfied:

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
17. Completion of the current response intake can lead only to latest-version recheck or upgrade preflight, not direct upgrade execution.

If any condition is missing, unclear, implied, or only present as a template, the future runtime stage must remain `NO-GO / pending explicit user approval`.

## 11. Hard NO-GO Conditions

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
- Codex cannot clearly report execution result, changed files, tag state, and push state.

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

## 14. KG-RUNTIME-151 Recommendation

Recommended next stage:

`KG-RUNTIME-151: single-model upgrade latest-version recheck authorization gate docs-only`

KG-RUNTIME-151 must not be entered by KG-RUNTIME-150.

KG-RUNTIME-151 should still not default to internet lookup or upgrade execution. It should only confirm whether latest-version read-only recheck is allowed, and define the recheck scope, sources, and prohibited boundaries.

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
- KG-RUNTIME-151 has not been entered.
