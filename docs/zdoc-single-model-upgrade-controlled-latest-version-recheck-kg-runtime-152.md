# ZDoc Single-Model Upgrade Controlled Latest-Version Recheck - KG-RUNTIME-152

## 1. Runtime Scope

KG-RUNTIME-152 is a docs-only controlled latest-version recheck for the ZDoc single-model upgrade chain.

This stage records a user-authorized read-only internet recheck for the single-model candidate carried forward from KG-RUNTIME-151.

This stage explicitly:

- Has user authorization for read-only internet recheck only.
- Does not execute an upgrade.
- Does not run Ollama.
- Does not execute any model command.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not enter upgrade preflight.
- Does not enter real use, formal trial use, or controlled trial use.
- Does not enter KG-RUNTIME-153.

The recheck result is only a future upgrade-preflight basis. It is not model upgrade authorization and must not be converted directly into any command execution.

## 2. Baseline

KG-RUNTIME-151 ended with the following recorded state:

- End HEAD: `7ce1c7ebec7af56304266e550acf8f31ed693768`
- Remote tag: `v0.1.534-zdoc-single-model-upgrade-latest-version-recheck-gate`
- New docs-only file: `docs/zdoc-single-model-upgrade-latest-version-recheck-authorization-gate-kg-runtime-151.md`
- Latest-version recheck gate result: `NOT AUTHORIZED / pending explicit user approval`
- Current added authorization: the user has explicitly authorized KG-RUNTIME-152 read-only internet recheck.
- Worktree state before KG-RUNTIME-152 docs-only change: clean.
- Model upgrade state: not executed.
- Real use state: not entered.
- Trial use state: not entered.

KG-RUNTIME-152 preflight observed:

- Start HEAD: `7ce1c7ebec7af56304266e550acf8f31ed693768`
- Local tag pointing at start HEAD: none observed.
- Worktree before this docs-only change: clean.

## 3. User Authorization Record

The user explicitly authorized KG-RUNTIME-152 to perform read-only internet recheck.

Authorization scope:

- Authorization is limited to read-only internet recheck.
- Authorized object is limited to `qwen3.6:35b` / the `qwen3` model family.
- Authorized sources are limited to the Ollama official model library, Qwen official release channels, and the Qwen official organization pages on Hugging Face.
- Running Ollama is not authorized.
- Running `ollama list` is not authorized.
- Running `ollama pull qwen3.6:35b` is not authorized.
- Running any Ollama model command is not authorized.
- Upgrading, pulling, deleting, or replacing any model is not authorized.
- Entering real use, formal trial use, or controlled trial use is not authorized.

This authorization does not approve model upgrade, model download, model replacement, model deletion, service runtime, endpoint access, real KG access, generation, export, writeback, or KG-RUNTIME-153.

## 4. Source Boundary

KG-RUNTIME-152 is based only on:

1. KG-RUNTIME-151 latest-version recheck authorization gate document:
   `docs/zdoc-single-model-upgrade-latest-version-recheck-authorization-gate-kg-runtime-151.md`
2. KG-RUNTIME-150 approval response intake document:
   `docs/zdoc-single-model-upgrade-execution-explicit-approval-response-intake-kg-runtime-150.md`
3. KG-RUNTIME-149 wait-state document:
   `docs/zdoc-single-model-upgrade-execution-explicit-approval-wait-state-kg-runtime-149.md`
4. KG-RUNTIME-148 authorization decision checkpoint document:
   `docs/zdoc-single-model-upgrade-execution-authorization-decision-checkpoint-kg-runtime-148.md`
5. Official or trusted read-only internet sources inside the user-authorized KG-RUNTIME-152 scope.

This stage:

- Does not expand model families.
- Does not re-collect the local model inventory.
- Does not run local model tools.
- Does not run `ollama list`.
- Does not treat the recheck result as upgrade authorization.
- Does not convert the recheck result directly into execution commands.

## 5. Recheck Sources Used

Read-only internet recheck date: 2026-05-30.

| Source | Source type | Access purpose | In authorization scope | Recheck summary |
|---|---|---|---|---|
| `https://ollama.com/library/qwen3.6` | Ollama official model library | Confirm official Ollama library availability for the `qwen3.6` family and visible `35b` tag | Yes | The page lists `qwen3.6`, identifies 27b and 35b variants, and shows `qwen3.6:35b` as a 24GB, 256K context, Text/Image model. |
| `https://ollama.com/library/qwen3.6/tags` | Ollama official model library tag index | Confirm tag-level state for `qwen3.6:35b` | Yes | The tag index lists `qwen3.6:35b` with digest `07d35212591f`, `latest`, 24GB, 256K context, and Text/Image input. |
| `https://ollama.com/library/qwen3.6:35b` | Ollama official model library tag page | Confirm the exact `qwen3.6:35b` tag remains available | Yes | The tag page identifies `qwen3.6:35b`, model details, Q4_K_M quantization, 24GB size, Apache license, and Qwen3.6 readme summary. Any command examples shown on the page were not executed. |
| `https://github.com/QwenLM/Qwen3.6` | Qwen official release channel | Confirm official Qwen3.6 release status and release dates | Yes | The official QwenLM repository states that Qwen3.6 is the latest addition to the Qwen model family, records `Qwen3.6-35B-A3B` availability on 2026-04-16, and records `Qwen3.6-27B` availability on 2026-04-22. |
| `https://qwen.ai/blog?id=qwen3.6-35b-a3b` | Qwen official release blog | Confirm the official release page for Qwen3.6-35B-A3B | Yes | The page was reached as the official blog URL linked by Qwen sources; direct text extraction was limited, so release details were verified through the official QwenLM repository and Hugging Face model card. |
| `https://huggingface.co/Qwen` | Hugging Face Qwen official organization | Confirm the Hugging Face organization identity and official Qwen linkage | Yes | The organization page identifies Qwen as a company/team and links to `https://qwen.ai/` and `QwenLM`. |
| `https://huggingface.co/Qwen/Qwen3.6-35B-A3B` | Hugging Face Qwen official model page | Confirm official model card availability and model characteristics | Yes | The model card states that the repository contains model weights and configuration files for `Qwen/Qwen3.6-35B-A3B`, records Qwen3.6 highlights, 35B total / 3B activated parameters, native 262,144-token context, and Apache-licensed model artifacts. |
| `https://huggingface.co/collections/Qwen/qwen36` | Hugging Face Qwen official collection | Confirm Qwen3.6 family collection contents | Yes | The Qwen3.6 collection lists `Qwen/Qwen3.6-35B-A3B`, `Qwen/Qwen3.6-35B-A3B-FP8`, `Qwen/Qwen3.6-27B`, and `Qwen/Qwen3.6-27B-FP8`, updated Apr 22. |

No unauthorized third-party source was used as a basis for the decision.

## 6. Latest-Version Recheck Findings

1. `qwen3.6:35b` remains available as the current single-model candidate for a future preflight path.
   - Ollama official pages list `qwen3.6:35b` as an available tag.
   - Ollama tag data indicates 24GB size, 256K context, Text/Image input, and `latest` association for the 35b tag.
   - Hugging Face Qwen official model page confirms the corresponding upstream `Qwen/Qwen3.6-35B-A3B` model remains available.

2. The `qwen3` / Qwen3.6 family has new sibling information that should be recorded but does not automatically change this single-model candidate.
   - Qwen official release information records `Qwen3.6-35B-A3B` availability on 2026-04-16.
   - Qwen official release information also records `Qwen3.6-27B` availability on 2026-04-22.
   - The Hugging Face Qwen3.6 collection includes both 35B-A3B and 27B family entries.
   - This stage does not compare sibling models and does not broaden the single-model candidate beyond `qwen3.6:35b`.

3. The KG-RUNTIME-139 candidate judgment should be updated only in status:
   - From: candidate requires later controlled latest-version recheck.
   - To: controlled latest-version recheck completed for KG-RUNTIME-152, with `qwen3.6:35b` retained as the single-model upgrade candidate for a separate future preflight authorization gate.

4. Unable-to-confirm items:
   - Local installation state was not checked because `ollama list` and all Ollama commands are forbidden.
   - Local disk space, available model cache state, download behavior, and actual runtime compatibility were not checked because those belong to a later preflight or execution stage.
   - Qwen official blog direct text extraction was limited, but the official QwenLM repository and Hugging Face Qwen model card provided sufficient official release evidence for this stage.

5. Blocked / insufficient-source items:
   - No blocker was found for official availability of `qwen3.6:35b` as a future preflight candidate.
   - The local readiness and execution feasibility questions remain blocked by design until a separate upgrade preflight authorization gate.

6. Recommendation:
   - Proceed only to a later docs-only upgrade preflight authorization gate.
   - Do not execute any model command in KG-RUNTIME-152.

7. Further user authorization required:
   - Any upgrade preflight still requires explicit user authorization.
   - Any actual command execution still requires separate explicit user authorization after preflight.

## 7. Candidate Decision After Recheck

Candidate decision after recheck:

`KEEP qwen3.6:35b as single-model upgrade candidate`

Decision meaning:

- `qwen3.6:35b` remains the single-model upgrade candidate for a future preflight path.
- The candidate is retained only as a future preflight candidate.
- This stage does not execute an upgrade.
- This stage does not execute any model command.
- A later upgrade preflight is still required.
- A later user authorization for actual commands is still required.
- The `qwen3.6:35b` candidate must not be broadened into wildcard tags, batch model operations, sibling model substitution, or delete/replace actions.

## 8. Upgrade Preflight Implications

The recheck result affects only a later preflight gate. It implies that a later docs-only preflight should still confirm:

- Download size and whether the 24GB Ollama package size is acceptable.
- Local disk space and cache headroom.
- Network stability and whether online pull is explicitly allowed.
- Old model retention policy.
- Explicit prohibition on deleting old models.
- Whether `latest` tag association is allowed to matter.
- Failure retry rule and maximum retry count.
- Execution time window.
- Worktree cleanliness before any execution node.
- That any successful upgrade leads only to stability verification.
- That stability verification does not enter real use, formal trial use, or controlled trial use.

None of these preflight checks were executed in KG-RUNTIME-152.

## 9. Future Command Candidate Boundary

KG-RUNTIME-152 executes no future command candidate.

The following command string is recorded only as a future preflight candidate command if a later stage keeps the same single-model candidate and receives explicit user authorization:

`ollama pull qwen3.6:35b`

Status:

`future preflight candidate command / not executed in KG-RUNTIME-152`

Boundary:

- KG-RUNTIME-152 does not execute this command.
- The command candidate is only for later preflight and user authorization review.
- No command may be executed without explicit later authorization.
- Any future command must remain strictly limited to the final confirmed single-model candidate.
- Wildcards are prohibited.
- Batch model commands are prohibited.
- Delete commands are prohibited.
- Model replacement is prohibited unless separately and explicitly authorized in a later stage.

## 10. Decision for Next Runtime

Recommended next stage:

`KG-RUNTIME-153: single-model upgrade preflight authorization gate docs-only`

KG-RUNTIME-153, if requested later, must still:

- Not run Ollama unless a later user instruction explicitly authorizes the exact limited preflight action.
- Not execute `ollama pull qwen3.6:35b`.
- Not upgrade, pull, delete, or replace any model.
- Not enter actual upgrade execution.
- Not enter real use, formal trial use, or controlled trial use.
- Require separate review before any command can be considered.

KG-RUNTIME-152 does not enter KG-RUNTIME-153.

## 11. Hard NO-GO Conditions

Any current or later stage must remain NO-GO if any of the following applies:

- Recheck sources cannot be accessed.
- Official availability of `qwen3.6:35b` cannot be confirmed.
- The `qwen3` model family has new information affecting the candidate but the impact cannot be confirmed.
- The task requires expanding to other model families.
- The task requires running Ollama.
- The task requires running `ollama list`.
- The task requires running `ollama pull qwen3.6:35b`.
- The task requires running any model command.
- The task requires upgrading, pulling, deleting, or replacing any model.
- A service is found running and service runtime was not authorized.
- There is endpoint access risk.
- There is real KG file body read risk.
- There is real KG JSON parse risk.
- There is generation, export, or writeback risk.
- There is output/job/export write risk.
- There is code, frontend, tests, config, JSON, RAG, registry, or CI modification risk.

NO-GO means stop, report, and wait for user review. It does not mean retry, broaden scope, run services, access endpoints, run Ollama, or continue into real use or trial use.

## 12. Trial Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only chain is completed.
3. The local model is upgraded to the latest available usable version through a separately and explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Preview-only validation before model upgrade remains internal technical validation only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 13. Final Compliance Statement

- This stage only adds one docs file.
- This stage performed user-authorized read-only internet recheck.
- The internet recheck scope was limited to `qwen3.6:35b` / the `qwen3` model family.
- The accessed sources were limited to the Ollama official model library, Qwen official release channels, and Hugging Face Qwen official organization pages.
- This stage did not run Ollama.
- This stage did not execute `ollama list`.
- This stage did not execute any Ollama command.
- This stage did not execute `ollama pull qwen3.6:35b`.
- This stage did not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- This stage did not upgrade, pull, delete, or replace any model.
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
- KG-RUNTIME-153 has not been entered.
