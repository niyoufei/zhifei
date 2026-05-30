# ZDoc Single-Model Upgrade Execution Explicit Command Authorization Intake - KG-RUNTIME-145

## 1. Runtime Scope

- Stage: KG-RUNTIME-145
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only explicit command authorization intake
- New artifact: `docs/zdoc-single-model-upgrade-execution-explicit-command-authorization-intake-kg-runtime-145.md`
- Stop line: do not enter KG-RUNTIME-146

KG-RUNTIME-145 is only a docs-only explicit command authorization intake stage.

This stage does not execute an upgrade, does not run Ollama, does not execute any model command, does not execute `ollama pull qwen3.6:35b`, does not perform additional internet lookup, does not enter real use or trial use, and does not enter KG-RUNTIME-146.

This stage records whether actual execution authorization is already present after KG-RUNTIME-144. It is not actual upgrade authorization, and it cannot convert any template, candidate command, or prior gate text into permission to run a model command.

## 2. Baseline

KG-RUNTIME-144 ended with the following recorded state:

- End HEAD: `d9bbb360b2bb3845fa3b062c28550409437b41bb`
- Remote tag: `v0.1.527-zdoc-single-model-upgrade-final-approval-checkpoint`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-final-user-approval-checkpoint-kg-runtime-144.md`
- Worktree state after KG-RUNTIME-144: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-144 recorded that:

- It did not run Ollama.
- It did not execute `ollama list`.
- It did not execute any Ollama command.
- It did not execute `ollama pull qwen3.6:35b`.
- It did not upgrade, pull, delete, or replace any model.
- It did not run the ZDoc service.
- It did not access any endpoint.
- It did not read real KG file body content.
- It did not parse real KG JSON.
- It did not trigger generation, export, or writeback.
- It did not write `output`, `job`, or `export`.
- It did not enter real use or trial use.
- It did not enter KG-RUNTIME-145.

## 3. Source Boundary

KG-RUNTIME-145 is based only on the following authorized project documents:

1. KG-RUNTIME-144 final user approval checkpoint document:
   `docs/zdoc-single-model-upgrade-execution-final-user-approval-checkpoint-kg-runtime-144.md`
2. KG-RUNTIME-143 readiness confirmation document:
   `docs/zdoc-single-model-upgrade-execution-readiness-confirmation-kg-runtime-143.md`
3. KG-RUNTIME-142 explicit authorization gate document:
   `docs/zdoc-single-model-upgrade-execution-explicit-user-authorization-gate-kg-runtime-142.md`
4. KG-RUNTIME-141 authorization request document:
   `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
5. KG-RUNTIME-140 strategy document:
   `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
6. KG-RUNTIME-139 lookup document:
   `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`

This stage does not add internet lookup, does not re-collect the local model inventory, does not execute `ollama list`, does not expand model families, does not adjust candidate priority, and does not introduce any external new basis.

The source boundary remains limited to the previously recorded KG-RUNTIME-139 through KG-RUNTIME-144 documents. KG-RUNTIME-145 does not treat a template authorization format as actual user authorization and does not treat any current docs-only task instruction as permission to run an upgrade command.

## 4. Final Candidate Confirmation

The only single-model candidate carried into this authorization intake is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 recorded the `qwen3` family lookup result; KG-RUNTIME-140 ranked `qwen3.6:35b` as the P0 primary single-model authorization-request candidate; KG-RUNTIME-141 selected `qwen3.6:35b` as the only proposed single-model upgrade candidate; KG-RUNTIME-142 retained `qwen3.6:35b` as the only candidate for a future explicit authorization gate; KG-RUNTIME-143 confirmed `qwen3.6:35b` as the only readiness-confirmation candidate; KG-RUNTIME-144 retained `qwen3.6:35b` as the only final approval checkpoint candidate.
- Current state: authorization intake candidate only.
- Upgrade executed by KG-RUNTIME-145: no.
- Upgrade allowed in KG-RUNTIME-145: no.
- Upgrade allowed in an automatic later node: no.
- Requirement for any later execution node: the user must explicitly authorize the exact model name, final command whitelist, online pull behavior, latest-tag behavior, old-model retention policy, no-delete boundary, retry rule, download-size boundary, execution time window, and validation boundary.

No other candidate is confirmed by this stage. `qwen3-next:80b`, `deepseek-r1:latest`, and `qwen3-coder-next:latest` remain outside the KG-RUNTIME-145 single-model authorization intake.

## 5. Authorization Intake Status

KG-RUNTIME-145 checks whether a user approval after KG-RUNTIME-144 has been recorded in the authorized project docs as a complete, itemized, explicit command authorization.

No such actual execution authorization is recorded in the authorized docs reviewed for this stage.

Authorization intake status: `NO-GO / pending explicit user approval`

Reasons:

- KG-RUNTIME-144's authorization wording is a future approval template only.
- A template does not equal authorization.
- A future command candidate does not equal authorization.
- A docs-only KG-RUNTIME-145 instruction does not authorize execution of `ollama pull qwen3.6:35b`.
- Current state cannot execute `ollama pull qwen3.6:35b`.
- Current state cannot run any Ollama command.
- Current state cannot enter an actual upgrade execution node.

## 6. Required Explicit User Authorization Items

Before any later node may consider actual upgrade execution, the user must explicitly approve each of the following:

1. Whether the only model is confirmed as `qwen3.6:35b`.
2. Whether online pull / network download is allowed.
3. Whether the final command whitelist is approved.
4. Whether any command may affect a `latest` tag.
5. Whether old models must be retained.
6. Whether deleting old models remains explicitly prohibited.
7. Whether retry after failure is allowed.
8. The maximum retry count after failure.
9. Whether a maximum download size is set.
10. Whether an execution time window is set.
11. Whether the worktree must be clean.
12. Whether the ZDoc service must not run.
13. Whether endpoint access remains prohibited.
14. Whether real KG reading remains prohibited.
15. Whether generation, export, and writeback remain prohibited.
16. Whether a successful upgrade may enter only stability verification.
17. Whether real use and trial use remain prohibited after upgrade.
18. Whether every later node still requires report and review.

If any item is missing, unclear, implied, or only present as a template, the later node must remain `NO-GO` and must not execute model commands.

## 7. Future Command Candidate

KG-RUNTIME-145 does not execute any command candidate in this section.

The following command is only a future explicit-command authorization candidate. It is not approved by KG-RUNTIME-145, was not run by KG-RUNTIME-145, and must not be executed later unless the user explicitly approves it in a later step.

Future explicit-command authorization candidate / not executed in KG-RUNTIME-145:

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

## 8. GO / NO-GO Decision

GO / NO-GO conclusion: `NO-GO`

Reasons:

- Actual user execution authorization has not been recorded in the authorized docs after KG-RUNTIME-144.
- The command whitelist has not been finally confirmed by the user.
- Online pull / network download has not been finally confirmed by the user.
- Latest-tag behavior has not been finally confirmed by the user.
- Old-model retention and no-delete policy have not been finally confirmed by the user.
- Download size, failure retry, retry count, and execution time window have not been finally confirmed by the user.
- Therefore KG-RUNTIME-145 must not enter actual upgrade execution.

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

## 12. KG-RUNTIME-146 Recommendation

Recommended next stage:

`KG-RUNTIME-146: single-model upgrade execution user-authorization gap closure docs-only`

KG-RUNTIME-146 should remain docs-only by default and must not default to upgrade execution.

Only after the user reviews KG-RUNTIME-145 and explicitly approves all of the following may a later node consider actual upgrade execution:

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

If the user does not approve these items one by one, KG-RUNTIME-146 should continue to remain docs-only and must not execute an upgrade.

KG-RUNTIME-145 does not enter KG-RUNTIME-146.

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
- KG-RUNTIME-146 has not been entered.
