# ZDoc Single-Model Upgrade Controlled Preflight Checks - KG-RUNTIME-154

## 1. Runtime Scope

KG-RUNTIME-154 is a command-limited controlled preflight checks stage for the ZDoc single-model upgrade chain.

The user has explicitly authorized actual pre-upgrade preflight checks for KG-RUNTIME-154 only.

This stage explicitly:

- Does not execute an upgrade.
- Does not run Ollama.
- Does not execute any model command.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not enter real use, formal trial use, or controlled trial use.
- Does not enter KG-RUNTIME-155.

The authorization in this stage is limited to preflight checks. It is not model upgrade authorization.

## 2. Baseline

KG-RUNTIME-153 ended with the following recorded state:

- End HEAD: `19edb5da2529081d91236bdc0610307ba2cf4363`
- Remote tag: `v0.1.536-zdoc-single-model-upgrade-preflight-authorization-gate`
- New docs-only file: `docs/zdoc-single-model-upgrade-preflight-authorization-gate-kg-runtime-153.md`
- Preflight gate result: `NOT AUTHORIZED FOR EXECUTION / pending explicit user approval`
- Current added authorization: the user has explicitly authorized KG-RUNTIME-154 actual pre-upgrade preflight checks.
- Worktree before this docs-only change: clean.
- Model upgrade state: not executed.
- Real use state: not entered.
- Trial use state: not entered.

KG-RUNTIME-154 preflight observed:

- Start HEAD: `19edb5da2529081d91236bdc0610307ba2cf4363`
- Local tag pointing at start HEAD: none observed.
- Worktree before this docs-only change: clean.

## 3. User Authorization Record

The user explicitly authorized KG-RUNTIME-154 to perform actual pre-upgrade preflight checks.

Authorization scope:

- Authorization is limited to pre-upgrade preflight checks.
- Preflight object is limited to `qwen3.6:35b`.
- Git state confirmation is authorized.
- Disk-space check is authorized.
- Read-only network connectivity check is authorized.
- Download size recording is authorized.
- Confirmation that the ZDoc service was not run is authorized.
- Confirmation that no endpoint was accessed is authorized.
- Confirmation that no real KG was read is authorized.
- Confirmation that no generation, export, or write-back was triggered is authorized.
- Running Ollama is not authorized.
- Running `ollama list` is not authorized.
- Running `ollama pull qwen3.6:35b` is not authorized.
- Running any Ollama model command is not authorized.
- Upgrading, pulling, deleting, or replacing any model is not authorized.
- Entering real use, formal trial use, or controlled trial use is not authorized.

This authorization does not approve model upgrade, model download, model replacement, model deletion, service runtime, endpoint access, real KG access, generation, export, writeback, or KG-RUNTIME-155.

## 4. Source Boundary

KG-RUNTIME-154 is based only on:

1. KG-RUNTIME-153 preflight authorization gate document:
   `docs/zdoc-single-model-upgrade-preflight-authorization-gate-kg-runtime-153.md`
2. KG-RUNTIME-152 controlled latest-version recheck document:
   `docs/zdoc-single-model-upgrade-controlled-latest-version-recheck-kg-runtime-152.md`
3. KG-RUNTIME-151 latest-version recheck authorization gate document:
   `docs/zdoc-single-model-upgrade-latest-version-recheck-authorization-gate-kg-runtime-151.md`
4. KG-RUNTIME-150 approval response intake document:
   `docs/zdoc-single-model-upgrade-execution-explicit-approval-response-intake-kg-runtime-150.md`
5. This stage's user-authorized read-only preflight results.

This stage:

- Does not expand model families.
- Does not re-collect the local model inventory.
- Does not run local model tools.
- Does not treat the preflight result as upgrade authorization.
- Does not convert the preflight result directly into execution commands.

## 5. Preflight Commands Executed

| Command | Purpose | In authorization scope | Output summary | Risk found |
|---|---|---|---|---|
| `git status --short` | Confirm worktree state before the docs-only change | Yes | Empty output before edit | No |
| `git rev-parse HEAD` | Record start HEAD | Yes | `19edb5da2529081d91236bdc0610307ba2cf4363` | No |
| `git tag --points-at HEAD` | Record local tag state at start HEAD | Yes | Empty output | No |
| `sed -n '1,260p' docs/zdoc-single-model-upgrade-preflight-authorization-gate-kg-runtime-153.md` | Read KG-RUNTIME-153 target docs file | Yes | Required baseline and gate content read | No |
| `sed -n '261,520p' docs/zdoc-single-model-upgrade-preflight-authorization-gate-kg-runtime-153.md` | Read remaining KG-RUNTIME-153 target docs file | Yes | Final compliance and stop boundary read | No |
| `sed -n '1,260p' docs/zdoc-single-model-upgrade-controlled-latest-version-recheck-kg-runtime-152.md` | Read KG-RUNTIME-152 target docs file | Yes | Official source and 24GB size record read | No |
| `sed -n '261,520p' docs/zdoc-single-model-upgrade-controlled-latest-version-recheck-kg-runtime-152.md` | Read remaining KG-RUNTIME-152 target docs file | Yes | Final compliance and stop boundary read | No |
| `sed -n '1,220p' docs/zdoc-single-model-upgrade-latest-version-recheck-authorization-gate-kg-runtime-151.md` | Read KG-RUNTIME-151 target docs file | Yes | Gate and source-boundary content read | No |
| `sed -n '221,520p' docs/zdoc-single-model-upgrade-latest-version-recheck-authorization-gate-kg-runtime-151.md` | Read remaining KG-RUNTIME-151 target docs file | Yes | Final compliance and stop boundary read | No |
| `sed -n '1,220p' docs/zdoc-single-model-upgrade-execution-explicit-approval-response-intake-kg-runtime-150.md` | Read KG-RUNTIME-150 target docs file | Yes | Approval intake and NO-GO content read | No |
| `sed -n '221,520p' docs/zdoc-single-model-upgrade-execution-explicit-approval-response-intake-kg-runtime-150.md` | Read remaining KG-RUNTIME-150 target docs file | Yes | Final compliance and stop boundary read | No |
| `df -h .` | Check disk space for the current repository location | Yes | `/dev/disk3s5`, size `3.6Ti`, used `651Gi`, available `3.0Ti`, capacity `18%` | No blocking disk risk observed |
| `df -h "$HOME"` | Check disk space for user home location | Yes | `/dev/disk3s5`, size `3.6Ti`, used `651Gi`, available `3.0Ti`, capacity `18%` | No blocking disk risk observed |
| `df -h "$HOME/.ollama"` | Check disk space for the `.ollama` path when present | Yes | `/dev/disk3s5`, size `3.6Ti`, used `651Gi`, available `3.0Ti`, capacity `18%` | No blocking disk risk observed |
| `pgrep -fl "uvicorn\|fastapi\|zdoc\|文档生成系统\|vite\|next\|node"` | Confirm whether relevant service-like processes are visible | Yes | Failed: `sysmon request failed with error: sysmond service not found`; `pgrep: Cannot get process list` | Service state inconclusive |
| `curl -I -L --max-time 15 https://ollama.com/library/qwen3.6:35b` | Read-only HEAD connectivity check for Ollama official model page | Yes | Failed to connect to local proxy `127.0.0.1:7897` | Network check incomplete |
| `curl -I -L --max-time 15 https://github.com/QwenLM/Qwen3.6` | Read-only HEAD connectivity check for Qwen official release channel | Yes | Failed to connect to local proxy `127.0.0.1:7897` | Network check incomplete |
| `curl -I -L --max-time 15 https://qwen.ai/blog?id=qwen3.6-35b-a3b` | Initial Qwen official blog HEAD attempt | Yes | Shell glob error before network access because the URL query string was not quoted | Command syntax risk corrected by rerun |
| `curl -I -L --max-time 15 'https://qwen.ai/blog?id=qwen3.6-35b-a3b'` | Quoted read-only HEAD connectivity check for Qwen official blog | Yes | Failed to connect to local proxy `127.0.0.1:7897` | Network check incomplete |
| `curl -I -L --max-time 15 https://huggingface.co/Qwen/Qwen3.6-35B-A3B` | Read-only HEAD connectivity check for Hugging Face Qwen official model page | Yes | Failed to connect to local proxy `127.0.0.1:7897` | Network check incomplete |

No Ollama command was executed. No upgrade, pull, delete, replacement, service runtime, endpoint call, real KG read, generation, export, writeback, output/job/export write, RAG, registry, or CI action was executed.

## 6. Git State Check

- `git status --short` before edit: empty output.
- `git rev-parse HEAD` before edit: `19edb5da2529081d91236bdc0610307ba2cf4363`.
- `git tag --points-at HEAD` before edit: empty output.
- Worktree before edit: clean.
- Non-target file changes before edit: none observed.

## 7. Disk Space Check

Disk-space checks executed:

- Current repository disk: `/dev/disk3s5`, size `3.6Ti`, used `651Gi`, available `3.0Ti`, capacity `18%`.
- User home disk: `/dev/disk3s5`, size `3.6Ti`, used `651Gi`, available `3.0Ti`, capacity `18%`.
- `$HOME/.ollama` path disk: `/dev/disk3s5`, size `3.6Ti`, used `651Gi`, available `3.0Ti`, capacity `18%`.

Disk preflight result:

`PASS FOR AUTHORIZATION REVIEW / actual upgrade still not authorized`

The observed available space is sufficient for later download-readiness review against the 24GB size record carried from KG-RUNTIME-152, but disk space must still be reconfirmed immediately before any separately authorized actual upgrade command.

`model storage location not confirmed because Ollama commands are prohibited`

No model directory scan, model blob read, or model content inspection was performed.

## 8. Network Connectivity Check

Read-only network checks were attempted only against authorized official sources:

- Ollama official model library: `https://ollama.com/library/qwen3.6:35b`
- Qwen official release channel: `https://github.com/QwenLM/Qwen3.6`
- Qwen official blog: `https://qwen.ai/blog?id=qwen3.6-35b-a3b`
- Hugging Face Qwen official model page: `https://huggingface.co/Qwen/Qwen3.6-35B-A3B`

Observed result:

- Ollama official model library check failed because `curl` attempted to use unavailable local proxy `127.0.0.1:7897`.
- Qwen official release channel check failed because `curl` attempted to use unavailable local proxy `127.0.0.1:7897`.
- Qwen official blog check initially failed locally due an unquoted URL query string; the quoted rerun then failed because `curl` attempted to use unavailable local proxy `127.0.0.1:7897`.
- Hugging Face Qwen official model page check failed because `curl` attempted to use unavailable local proxy `127.0.0.1:7897`.

Network preflight result:

`INCOMPLETE / manual confirmation required`

No search engine was used. No unrelated model family page was accessed. No model download was attempted.

## 9. Download Size Record

KG-RUNTIME-152 recorded the Ollama official package size for `qwen3.6:35b` as `24GB`.

Current-stage status:

- Download size record carried from KG-RUNTIME-152: `24GB`.
- Live current-stage reconfirmation: not completed because authorized HEAD checks failed through unavailable local proxy `127.0.0.1:7897`.
- No actual pull was used to measure size.
- No Ollama command was run.
- No unauthorized third-party source was used.
- Before any actual upgrade authorization, the download size still requires confirmation or explicit user acceptance of the carried 24GB record.

## 10. ZDoc Service / Endpoint Safety Check

This task did not start, stop, or run the ZDoc service.

This task did not access any ZDoc endpoint.

The authorized process-level check:

`pgrep -fl "uvicorn|fastapi|zdoc|文档生成系统|vite|next|node"`

returned:

`sysmon request failed with error: sysmond service not found`

and:

`pgrep: Cannot get process list`

Service status:

`inconclusive / manual confirmation required`

No service log was read. No interface was accessed. No endpoint call was made.

## 11. KG / Generation / Export / Write-back Safety Check

This task:

- Did not read real KG file body content.
- Did not parse real KG JSON.
- Did not trigger generation.
- Did not trigger export.
- Did not trigger writeback.
- Did not write `output`, `job`, or `export`.
- Did not connect RAG, registry, or CI.

## 12. Preflight Result

Overall preflight result:

`PREFLIGHT INCOMPLETE / manual confirmation required`

Reason:

- Git state check passed for authorization review.
- Disk-space check passed for authorization review.
- Download size was recorded from KG-RUNTIME-152 as 24GB, but current-stage live confirmation was not completed.
- Read-only network connectivity checks failed through unavailable local proxy `127.0.0.1:7897`.
- ZDoc service process state is inconclusive because the authorized `pgrep` command could not obtain the process list.

Regardless of this result:

- KG-RUNTIME-154 does not execute an upgrade.
- KG-RUNTIME-154 does not execute any model command.
- A later actual upgrade command still requires separate explicit user authorization.
- This result cannot directly enter model upgrade execution.

## 13. Remaining Authorization Items Before Upgrade

Before actual upgrade execution may be considered, the user must still confirm:

1. Whether to approve executing `ollama pull qwen3.6:35b`.
2. Whether the download size is confirmed or accepted.
3. Whether disk space is sufficient immediately before execution.
4. Whether the execution time window is confirmed.
5. Whether the failure retry count is confirmed.
6. Whether old model retention is confirmed.
7. Whether deleting old models remains prohibited.
8. Whether `latest` tag impact strategy is confirmed.
9. Whether the post-upgrade phase is limited to stability verification.
10. Whether real use, formal trial use, and controlled trial use remain prohibited.
11. Whether later execution must still report back and wait for review.

## 14. Future Upgrade Command Candidate Boundary

Future upgrade candidate command only:

`ollama pull qwen3.6:35b`

Status:

`future upgrade candidate command / not executed in KG-RUNTIME-154`

Boundary:

- KG-RUNTIME-154 does not execute this command.
- This command may only be considered after later explicit user authorization for actual upgrade execution.
- Wildcards are prohibited.
- Batch model operations are prohibited.
- Model deletion is prohibited.

## 15. Decision for Next Runtime

Recommended next stage:

`KG-RUNTIME-155: single-model upgrade preflight insufficiency closure docs-only`

Reason:

Network connectivity and service process state remain incomplete and require closure before any actual upgrade execution authorization request can be cleanly reviewed.

KG-RUNTIME-154 does not enter KG-RUNTIME-155.

## 16. Hard NO-GO Conditions

The path must remain NO-GO if any of the following applies:

- User has not explicitly authorized actual upgrade.
- User authorization content is incomplete.
- Disk space is insufficient or cannot be confirmed.
- Network connectivity fails or remains unconfirmed.
- Download size cannot be confirmed and the user has not accepted the risk.
- ZDoc service status is unclear.
- Endpoint risk is unclear.
- Real KG read risk is unclear.
- Generation, export, or writeback risk is unclear.
- The task requires running Ollama.
- The task requires executing `ollama list`.
- The task requires executing `ollama pull qwen3.6:35b`.
- The task requires executing any model command.
- The task requires upgrading, pulling, deleting, or replacing any model.

## 17. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Preview-only validation before model upgrade remains internal technical validation only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 18. Final Compliance Statement

- This stage only adds one docs file.
- This stage performed user-authorized actual pre-upgrade preflight checks.
- The preflight object was limited to `qwen3.6:35b`.
- Git state confirmation was executed.
- Disk-space check was executed.
- Read-only network connectivity checks were attempted only against authorized official sources.
- Download size was recorded from KG-RUNTIME-152 as 24GB, with current-stage live confirmation incomplete.
- This task did not run the ZDoc service.
- This task did not access any endpoint.
- This task did not run Ollama.
- This task did not execute `ollama list`.
- This task did not execute any Ollama command.
- This task did not execute `ollama pull qwen3.6:35b`.
- This task did not upgrade, pull, delete, or replace any model.
- This task did not read real KG.
- This task did not parse real KG JSON.
- This task did not execute another directory scan.
- This task did not trigger generation, export, or writeback.
- This task did not write `output`, `job`, or `export`.
- This task did not modify code.
- This task did not modify frontend, tests, config, or JSON.
- This task did not connect RAG, registry, or CI.
- This task did not add `.pyc` or `__pycache__`.
- This task did not enter real use, formal trial use, or controlled trial use.
- Model upgrade has not been executed.
- KG-RUNTIME-155 has not been entered.
