# ZDoc Single-Model Upgrade Execution Explicit User Authorization Gate - KG-RUNTIME-142

## 1. Runtime Scope

- Stage: KG-RUNTIME-142
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only explicit user authorization gate
- New artifact: `docs/zdoc-single-model-upgrade-execution-explicit-user-authorization-gate-kg-runtime-142.md`
- Stop line: do not enter KG-RUNTIME-143

KG-RUNTIME-142 is only a docs-only explicit authorization gate for a future single-model upgrade execution path. It records what the user must explicitly approve before any later command can be executed.

KG-RUNTIME-142 does not execute an upgrade, does not run Ollama, does not execute any model command, does not perform additional internet lookup, does not enter real use or trial use, and does not enter KG-RUNTIME-143.

This document is not runtime authorization. It is a pre-execution checklist and boundary record for later human review.

## 2. Baseline

KG-RUNTIME-141 ended with the following recorded state:

- End HEAD: `7889bb5efc600baaa26cda3f40be34b71d4042bd`
- Remote tag: `v0.1.524-zdoc-single-model-upgrade-authorization-request`
- New docs-only file: `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
- Worktree state after KG-RUNTIME-141: clean
- Model upgrade state: not executed
- Real use state: not entered
- Trial use state: not entered

KG-RUNTIME-141 also recorded that:

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
- KG-RUNTIME-142 had not been entered.

## 3. Source Boundary

KG-RUNTIME-142 is based only on the following authorized source documents:

1. KG-RUNTIME-141 authorization request document:
   `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
2. KG-RUNTIME-140 strategy document, used only to verify the candidate strategy:
   `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
3. KG-RUNTIME-139 lookup document, used only to verify the candidate source:
   `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`

This stage does not add any internet lookup, does not re-collect the local model inventory, does not execute `ollama list`, does not expand model families, does not change candidate priority, and does not use any external material as a new source.

The source boundary remains limited to the previously recorded KG-RUNTIME-139, KG-RUNTIME-140, and KG-RUNTIME-141 documents. KG-RUNTIME-142 does not treat any command, model registry, local model list, or newly queried source as additional evidence.

## 4. Confirmed Single-Model Candidate for Authorization Gate

The only single-model candidate allowed to enter a future authorization discussion from this stage is:

`qwen3.6:35b`

Candidate record:

- Model name: `qwen3.6:35b`
- Model family: `qwen3`
- Source basis: KG-RUNTIME-139 recorded the `qwen3` family lookup result; KG-RUNTIME-140 ranked `qwen3.6:35b` as the P0 primary single-model authorization-request candidate; KG-RUNTIME-141 selected `qwen3.6:35b` as the only proposed single-model upgrade candidate.
- Current state: authorization-gate candidate only.
- Upgrade executed by KG-RUNTIME-142: no.
- Upgrade authorized by KG-RUNTIME-142: no.
- Upgrade allowed in an automatic later node: no.
- Requirement for any later execution node: the user must explicitly authorize the exact model name, command whitelist, network behavior, retention policy, retry rule, size boundary, time window, and validation boundary.

No other candidate is authorized by this stage. `qwen3-next:80b`, `deepseek-r1:latest`, and `qwen3-coder-next:latest` remain outside the KG-RUNTIME-142 single-model authorization gate.

## 5. User Authorization Checklist

Before any later upgrade execution node can run, the user must explicitly answer all of the following:

1. Confirm whether the later upgrade execution preparation may target only `qwen3.6:35b`.
2. Confirm whether online pull / network download for `qwen3.6:35b` is allowed.
3. Confirm whether the exact single-model pull command is allowed.
4. Confirm whether any command may affect or replace a `latest` tag.
5. Confirm whether old local models must be retained.
6. Confirm whether deletion of old models remains strictly prohibited.
7. Confirm whether retry after a failed pull, failed load, or failed validation is allowed.
8. Confirm the maximum number of retries, if retry is allowed.
9. Confirm whether a maximum download size is set, or explicitly confirm that no size limit is imposed.
10. Confirm whether an execution time window is required.
11. Confirm whether a successful upgrade may proceed only to stability verification.
12. Confirm that even after upgrade success, real use, formal trial use, and controlled trial use remain prohibited.
13. Confirm that every later step still requires separate report, review, and authorization.
14. Confirm that any command not listed in the final user-approved whitelist remains prohibited.
15. Confirm that no other model may be upgraded at the same time.

If any item is missing, unclear, or only implied, the later execution node must not run upgrade commands.

## 6. Future Command Allowlist Candidate

KG-RUNTIME-142 does not execute the command in this section.

The following is only a future authorization candidate command. It is not approved by KG-RUNTIME-142, was not run by KG-RUNTIME-142, and must not be executed later unless the user explicitly approves it in a later step.

Future authorization candidate command / not executed in KG-RUNTIME-142:

```bash
ollama pull qwen3.6:35b
```

Allowlist candidate constraints:

- The command is limited to `qwen3.6:35b`.
- No wildcard model pattern is allowed.
- No batch model command is allowed.
- No delete command is allowed.
- No automatic all-model upgrade command is allowed.
- No long-running service command is allowed.
- No command may be treated as approved unless the user explicitly confirms it later.
- No future node may broaden this candidate into another model, another command, or a batch operation without separate user authorization.

## 7. Explicitly Prohibited Commands and Actions

The following commands and actions remain prohibited by default:

- `ollama list`
- `ollama run`
- `ollama rm`
- `ollama serve`
- `ollama show`
- `ollama ps`
- Any other Ollama command not separately and explicitly approved in a later stage.
- Delete old models.
- Batch-delete models.
- Upgrade multiple models at the same time.
- Use wildcard model commands.
- Automatically replace all `latest` tags.
- Start a long-running Ollama service.
- Run the ZDoc service.
- Access any endpoint.
- Read real KG file body content.
- Parse real KG JSON.
- Trigger generation, export, or writeback.
- Write `output`, `job`, or `export`.
- Connect RAG, registry, or CI.
- Enter real use, formal trial use, or controlled trial use.

KG-RUNTIME-142 does not convert any future allowlist candidate into an executable authorization.

## 8. Execution Preconditions for Future Runtime

Before any later actual upgrade execution node, all of the following must be satisfied:

1. The user explicitly approves `qwen3.6:35b`.
2. The user explicitly approves the final command whitelist.
3. The user explicitly approves whether online pull / network download is allowed.
4. The user explicitly approves whether any command may affect a `latest` tag.
5. The user explicitly approves old-model retention policy.
6. The user explicitly approves failure retry rules.
7. The user explicitly approves a download size limit, or explicitly confirms that no size limit is imposed.
8. The user explicitly approves an execution time window.
9. The worktree is clean.
10. The current HEAD and tag state are recorded.
11. The ZDoc service has not been run.
12. No endpoint has been accessed.
13. No real KG file body content has been read.
14. No real KG JSON has been parsed.
15. No generation, export, or writeback has been triggered.
16. Completion of any later upgrade can lead only to stability verification.

If any precondition is not met, the future runtime stage must stop before executing model commands.

## 9. Abort Conditions

A future upgrade preparation or execution node must abort if any of the following occurs:

- User authorization is incomplete.
- The model name differs from `qwen3.6:35b`.
- The command is outside the user-approved whitelist.
- The worktree is not clean.
- A service appears to be running and service runtime was not authorized.
- There is endpoint access risk.
- There is real KG file body read risk.
- There is real KG JSON parse risk.
- There is generation, export, or writeback risk.
- Disk space, network, or download-size risk has not been confirmed.
- Codex cannot clearly report what was executed and what changed.
- There is any risk of batch upgrade, old-model deletion, or automatic replacement behavior.

Abort means stop the stage, report the reason, and wait for user review. It does not mean retry, broaden the command set, remove models, or continue into trial use.

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

No stability verification may silently broaden into ZDoc service runtime, endpoint access, real KG reading, real KG JSON parsing, generation, export, writeback, real use, or trial use.

## 11. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Preview-only verification before model upgrade is internal technical verification only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 12. KG-RUNTIME-143 Recommendation

Recommended next stage:

`KG-RUNTIME-143: single-model upgrade execution readiness confirmation docs-only`

KG-RUNTIME-143 should remain docs-only readiness confirmation by default. It must not default to upgrade execution.

Only after the user reviews KG-RUNTIME-142 and explicitly approves all of the following may a later node discuss actual upgrade execution:

- Model name: `qwen3.6:35b`
- Whether online pull / network download is allowed.
- Future command whitelist.
- Whether old models must be retained.
- Whether deleting old models remains prohibited.
- Failure retry rules.
- Download size limit or explicit no-limit confirmation.
- Execution time window.
- Upgrade success leading only to stability verification.

KG-RUNTIME-142 does not enter KG-RUNTIME-143.

## 13. Final Compliance Statement

- This stage only adds one docs file.
- This stage does not run Ollama.
- This stage does not execute `ollama list`.
- This stage does not execute any Ollama command.
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
- KG-RUNTIME-143 has not been entered.
