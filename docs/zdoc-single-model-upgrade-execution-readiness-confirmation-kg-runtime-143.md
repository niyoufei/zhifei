# ZDoc Single-Model Upgrade Execution Readiness Confirmation - KG-RUNTIME-143

## 1. Runtime Scope

- Stage: KG-RUNTIME-143
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only single-model upgrade execution readiness confirmation
- New artifact: `docs/zdoc-single-model-upgrade-execution-readiness-confirmation-kg-runtime-143.md`
- Stop line: do not enter KG-RUNTIME-144

KG-RUNTIME-143 is only a docs-only readiness confirmation for a future single-model upgrade execution path.

This stage does not execute an upgrade, does not run Ollama, does not execute any model command, does not execute `ollama pull qwen3.6:35b`, does not perform additional internet lookup, does not enter real use or trial use, and does not enter KG-RUNTIME-144.

This document confirms whether the execution conditions are ready for later user review. It is not actual runtime authorization and does not allow any later node to execute upgrade commands automatically.

## 2. Baseline

KG-RUNTIME-142 ended with the following recorded state:

- End HEAD: `df42efccdab56fb065c219abd0a0be9b16b87a11`
- Remote tag: `v0.1.525-zdoc-single-model-upgrade-explicit-authorization-gate`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-explicit-user-authorization-gate-kg-runtime-142.md`
- Worktree state after KG-RUNTIME-142: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-143 preflight observed:

- Start HEAD: `df42efccdab56fb065c219abd0a0be9b16b87a11`
- Local tag at start HEAD: none observed by `git tag --points-at HEAD`
- Worktree before this docs-only change: clean

The KG-RUNTIME-142 non-execution boundaries remain active:

- Ollama was not run.
- `ollama list` was not executed.
- No Ollama command was executed.
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

KG-RUNTIME-143 is based only on the following authorized source documents:

1. KG-RUNTIME-142 explicit authorization gate document:
   `docs/zdoc-single-model-upgrade-execution-explicit-user-authorization-gate-kg-runtime-142.md`
2. KG-RUNTIME-141 authorization request document:
   `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
3. KG-RUNTIME-140 strategy document:
   `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
4. KG-RUNTIME-139 lookup document:
   `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`

This stage does not add internet lookup, does not re-collect the local model inventory, does not execute `ollama list`, does not expand model families, does not adjust candidate priority, and does not introduce any external new basis.

The source boundary remains limited to the already recorded KG-RUNTIME-139 through KG-RUNTIME-142 documents. KG-RUNTIME-143 does not treat any command, model registry, local model list, directory scan, endpoint, or newly queried source as additional evidence.

## 4. Confirmed Single-Model Candidate

The only single-model candidate confirmed for future execution readiness review is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 recorded the `qwen3` family lookup result; KG-RUNTIME-140 ranked `qwen3.6:35b` as the P0 primary single-model authorization-request candidate; KG-RUNTIME-141 selected `qwen3.6:35b` as the only proposed single-model upgrade candidate; KG-RUNTIME-142 retained `qwen3.6:35b` as the only candidate for a future explicit authorization gate.
- Current state: upgrade execution readiness candidate only.
- Upgrade executed by KG-RUNTIME-143: no.
- Upgrade allowed in KG-RUNTIME-143: no.
- Upgrade allowed in an automatic later node: no.
- Requirement for any later execution node: the user must explicitly authorize the exact model name, final command whitelist, network behavior, latest-tag behavior, old-model retention policy, no-delete boundary, retry rule, size boundary, execution time window, and validation boundary.

No other candidate is confirmed by this stage. `qwen3-next:80b`, `deepseek-r1:latest`, and `qwen3-coder-next:latest` remain outside the KG-RUNTIME-143 single-model readiness confirmation.

## 5. Readiness Confirmation Matrix

| Confirmation item | Current status | Satisfied | Gap | User confirmation required next |
|---|---|---|---|---|
| Single model name is explicit | `qwen3.6:35b` is the only named candidate | Yes | None for naming | Confirm exact target remains `qwen3.6:35b` |
| Model family is explicit | `qwen3` family | Yes | None for family | Confirm no family expansion |
| Candidate is limited to `qwen3.6:35b` | Limited by KG-RUNTIME-141 and KG-RUNTIME-142 | Yes | None for candidate scope | Confirm no alternate model |
| Batch models are prohibited | Batch upgrade remains prohibited | Yes | None for prohibition | Confirm no batch operation |
| Old-model deletion is prohibited | Deletion remains prohibited by default | Yes | Need final no-delete confirmation for execution | Confirm old models must not be deleted |
| Old-model retention policy is confirmed | Retention is required for review but not fully authorized for execution | No | Pending explicit user authorization | Confirm exact retention policy |
| Online pull permission is confirmed | Not authorized in KG-RUNTIME-143 | No | Pending explicit user authorization | Confirm whether network pull is allowed |
| `latest` tag impact is confirmed | No permission to affect or replace `latest` | No | Pending explicit user authorization | Confirm whether any `latest` tag impact is allowed |
| Failure retry count is confirmed | Not confirmed | No | Pending explicit user authorization | Confirm retry allowed and maximum retry count |
| Maximum download size is confirmed | Not confirmed | No | Pending explicit user authorization | Confirm size limit or explicit no-limit |
| Execution time window is confirmed | Not confirmed | No | Pending explicit user authorization | Confirm allowed execution window |
| Worktree clean is confirmed | Preflight `git status --short` was clean | Yes | Must remain clean before future execution | Confirm clean state again immediately before execution |
| ZDoc service runtime is prohibited | Service runtime remains prohibited | Yes | None for this stage | Confirm no service runtime in execution node unless separately authorized |
| Endpoint calls are prohibited | Endpoint access remains prohibited | Yes | None for this stage | Confirm no endpoint access |
| Real KG reading is prohibited | Real KG file body reads remain prohibited | Yes | None for this stage | Confirm no real KG read |
| Generation / export / writeback are prohibited | These chains remain prohibited | Yes | None for this stage | Confirm no generation, export, or writeback |
| Upgrade success only allows stability verification | Stable verification is the only allowed post-upgrade phase | Yes | Need restatement in execution approval | Confirm upgrade success does not permit real use |
| Real use / trial use remains prohibited | Real use, formal trial use, and controlled trial use remain prohibited | Yes | None for this stage | Confirm trial boundary remains closed |

Readiness result:

- Current readiness state: `NO-GO / pending explicit user authorization`
- Reason: execution-specific authorization remains incomplete for network pull, final command whitelist, latest-tag behavior, old-model retention policy, retry rules, download-size boundary, execution time window, and final post-upgrade validation boundary.
- Consequence: no upgrade command may be executed by KG-RUNTIME-143 or by any later node unless the user explicitly authorizes it again.

## 6. Future Command Candidate Status

KG-RUNTIME-143 does not execute any command candidate in this section.

The following command is only a future authorization candidate command. It is not approved by KG-RUNTIME-143, was not run by KG-RUNTIME-143, and must not be executed later unless the user explicitly approves it in a later step.

Future authorization candidate command / not executed in KG-RUNTIME-143:

```bash
ollama pull qwen3.6:35b
```

Command candidate constraints:

- The command is limited to `qwen3.6:35b`.
- No wildcard model pattern is allowed.
- No batch model command is allowed.
- No delete command is allowed.
- No automatic all-model upgrade command is allowed.
- No long-running service command is allowed.
- No command may be treated as approved unless the user explicitly confirms it later.
- No future node may broaden this candidate into another model, another command, or a batch operation without separate user authorization.

## 7. Explicit NO-GO Conditions

A future upgrade preparation or execution node must be marked `NO-GO / pending explicit user authorization` if any of the following conditions apply:

- The user has not explicitly authorized the exact execution step.
- The model name is not exactly `qwen3.6:35b`.
- The command is outside the final user-approved whitelist.
- There is batch upgrade risk.
- There is old-model deletion risk.
- There is automatic replacement of multiple `latest` tags risk.
- The worktree is not clean.
- A service is running and service runtime was not authorized.
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

## 8. Execution Preconditions for Future Runtime

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

## 9. Post-Upgrade Validation Boundary

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

## 10. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Model-upgrade-before-preview-only validation remains internal technical validation only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 11. KG-RUNTIME-144 Recommendation

Recommended next stage:

`KG-RUNTIME-144: single-model upgrade execution final user approval checkpoint`

KG-RUNTIME-144 should remain a final user approval checkpoint by default. It must not default to upgrade execution.

Only after the user reviews KG-RUNTIME-143 and explicitly approves all of the following may a later node consider actual upgrade execution:

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

If the user does not approve these items one by one, KG-RUNTIME-144 should remain docs-only and must not execute an upgrade.

KG-RUNTIME-143 does not enter KG-RUNTIME-144.

## 12. Final Compliance Statement

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
- KG-RUNTIME-144 has not been entered.
