# ZDoc Single-Model Upgrade Execution Authorization Request - KG-RUNTIME-141

## 1. Runtime Scope

- Stage: KG-RUNTIME-141
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only single-model upgrade execution authorization request
- New artifact: `docs/zdoc-single-model-upgrade-execution-authorization-request-kg-runtime-141.md`
- Stop line: do not enter KG-RUNTIME-142

KG-RUNTIME-141 is only an authorization request stage. It does not execute a model upgrade, does not run Ollama, does not execute `ollama list`, does not execute any model command, and does not enter real use, formal trial use, controlled trial use, or preview-only operational use.

This stage records which one model should be proposed for later explicit authorization, which future command boundary should be reviewed, and which actions remain prohibited unless the user separately authorizes them in a later stage.

## 2. Baseline

KG-RUNTIME-140 ended with the following recorded state:

- End HEAD: `fc16356837775e9e7ff0fb40e7f7a473d245ec5b`
- Remote tag: `v0.1.523-zdoc-upgrade-candidate-final-strategy-gate`
- New docs-only file: `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
- Worktree state after KG-RUNTIME-140: clean
- Model upgrade state: not executed
- Trial state: not entered

KG-RUNTIME-141 preflight observed:

- Current branch: `main`
- Start HEAD: `fc16356837775e9e7ff0fb40e7f7a473d245ec5b`
- Local tag at start HEAD: none observed by `git tag --points-at HEAD`
- Worktree before this docs-only change: clean

The KG-RUNTIME-140 non-execution boundaries remain active:

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

## 3. Source Boundary

KG-RUNTIME-141 is based only on the KG-RUNTIME-140 strategy document:

- `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`

KG-RUNTIME-141 also reviewed the KG-RUNTIME-139 lookup document only to confirm the candidate source boundary:

- `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`

This stage does not perform new internet lookup, does not re-check official pages, does not query model registries, does not collect a new local model list, does not execute `ollama list`, does not run any model command, does not rescan directories, and does not expand beyond the model families already bounded by KG-RUNTIME-139:

- `qwen3-next`
- `qwen3-coder`
- `qwen3`
- `deepseek-r1`

## 4. Candidate Selection Basis

KG-RUNTIME-140 defines the upgrade candidate priority as follows:

| Priority | Candidate | Recommendation | KG-RUNTIME-141 treatment |
|---|---|---|---|
| P0 | `qwen3.6:35b` / Qwen3 general line | Primary single-model authorization-request candidate | Selected as the only proposed single-model upgrade candidate. |
| P1 | `qwen3-next:80b` / Qwen3-Next line | High-quality secondary candidate | Deferred because it has a larger footprint and higher runtime risk. |
| P2 | `deepseek-r1:latest` / DeepSeek-R1 0528 line | Reasoning-focused secondary candidate | Deferred because it is not the first document-generation candidate and differs materially from the existing local 32B line. |
| Hold | `qwen3-coder-next:latest` / Qwen3-Coder line | Hold for ZDoc model upgrade | Deferred because it is code-specialized and not aligned as the first ZDoc document-generation upgrade candidate. |

The single-model selection rule for this stage is therefore straightforward:

- KG-RUNTIME-140 contains one explicit P0 candidate.
- The P0 candidate is `qwen3.6:35b`.
- KG-RUNTIME-141 must select only that one candidate for user authorization.
- No P1, P2, or Hold candidate may be upgraded at the same time.
- No candidate order is changed by this document.
- No external source, local inventory rerun, model command, or new lookup is used to reorder candidates.

This stage does not authorize execution. It only records the proposed single-model candidate and the approval items required before any later execution node.

## 5. Proposed Single-Model Upgrade Candidate

- Proposed model name: `qwen3.6:35b`
- Model family: Qwen3 general line
- KG-RUNTIME-139 basis: KG-RUNTIME-139 recorded the `qwen3` family as an authorized lookup family and recorded `qwen3.6:latest` / `qwen3.6:35b` as the series-level latest line observed for the broad Qwen3 family.
- KG-RUNTIME-140 basis: KG-RUNTIME-140 assigned `qwen3.6:35b` / Qwen3 general line to P0 and named it the primary single-model authorization-request candidate.
- Expected use after separately authorized upgrade and validation: primary ZDoc general document-generation, technical-bid text drafting, structured long-text response, and preview-only chain compatibility validation.
- Reason for priority: it is the closest general-purpose continuation of the existing local Qwen3 family and is better aligned with ZDoc document-generation work than code-specialized or reasoning-secondary candidates.
- Reason not to upgrade other models at the same time: simultaneous model upgrades would make regressions hard to attribute, increase download and runtime risk, broaden latest-tag and retention decisions, and violate the staged single-model authorization boundary.
- Risk points requiring user confirmation: exact command, network pull permission, download size, runtime memory pressure, response-time risk, old-model retention policy, `latest` tag behavior, retry policy, and no-delete boundary.
- Allowed into later upgrade execution node: not by this document alone.
- Requirement before later node: the user must explicitly approve the exact model name and the exact command whitelist again before any command is executed.

Deferred candidates:

- `qwen3-next:80b` is deferred because KG-RUNTIME-140 marks it P1, not P0, and records a larger footprint and higher memory / latency risk.
- `deepseek-r1:latest` is deferred because KG-RUNTIME-140 marks it P2 and positions it as reasoning-focused secondary review support rather than the first general ZDoc document-generation candidate.
- `qwen3-coder-next:latest` is deferred because KG-RUNTIME-140 marks it Hold for ZDoc model upgrade and positions it as code-specialized rather than document-generation-first.

## 6. Authorization Items Required from User

Before any later upgrade execution node, the user must explicitly authorize all of the following:

1. Whether the next execution node may target only `qwen3.6:35b`.
2. Whether network download / online pull for `qwen3.6:35b` is allowed.
3. Whether the exact model command or commands are allowed.
4. Whether any command may replace, update, or affect a `latest` tag.
5. Whether the old local Qwen3 models must be retained.
6. Whether deletion of old models remains prohibited.
7. Whether a failed pull, failed load, or failed validation may be retried.
8. Whether a maximum download size limit applies.
9. Whether execution is restricted to a time window.
10. Whether successful upgrade may proceed only to stability verification.
11. Whether real use, formal trial use, and controlled trial use remain prohibited after upgrade.
12. Whether every later step still requires separate report, review, and authorization.

If any of these items is not explicitly authorized, the later execution node must not run upgrade commands.

## 7. Proposed Command Allowlist for Future Runtime

KG-RUNTIME-141 does not execute any command in this section.

These examples are only future authorization candidate commands. They may be considered only if the user later gives explicit approval in KG-RUNTIME-142 or a later stage. The final command list must be restricted to a single model and must not use wildcards, batch model names, batch deletion, or automatic upgrade logic.

Future authorization candidate commands may include only narrowly reviewed single-model actions such as:

```bash
ollama pull qwen3.6:35b
```

If a later stage needs a load check, it must request separate explicit approval for the exact command. Any load check must remain limited to the same single model:

```bash
ollama run qwen3.6:35b
```

The above commands are not approved by KG-RUNTIME-141 and were not run by KG-RUNTIME-141.

No command may be generalized to:

- multiple model names;
- wildcard tags;
- all installed models;
- automatic latest replacement;
- deletion;
- background serving;
- ZDoc service integration;
- generation, export, or writeback.

## 8. Explicitly Prohibited Commands

Even if a later stage enters an upgrade-execution authorization path, the following remain prohibited by default unless the user separately authorizes the exact action:

- Delete old models.
- Batch-delete models.
- Upgrade multiple models at the same time.
- Automatically replace all `latest` tags.
- Start long-running `ollama serve`.
- Connect the upgraded model to the ZDoc formal chain.
- Trigger generation.
- Trigger export.
- Trigger writeback.
- Read real KG file body content.
- Parse real KG JSON.
- Enter real use.
- Enter formal trial use.
- Enter controlled trial use.

KG-RUNTIME-141 also prohibits `ollama list`, `ollama show`, `ollama ps`, `ollama pull`, `ollama run`, `ollama rm`, `ollama serve`, and any other Ollama command during this stage.

## 9. Upgrade Execution Pre-Conditions

If the user later asks to enter KG-RUNTIME-142 or another execution-preparation node, all of the following must be satisfied before any upgrade command is allowed:

1. The user explicitly approves the single model name.
2. The user explicitly approves the command whitelist.
3. The user explicitly approves whether network pull is allowed.
4. The user explicitly approves whether old models must be retained.
5. The worktree is clean.
6. The current HEAD and tag state are recorded.
7. ZDoc service runtime remains prohibited.
8. Endpoint calls remain prohibited.
9. Real KG file body reads remain prohibited.
10. Real KG JSON parsing remains prohibited.
11. Generation, export, and writeback remain prohibited.
12. Completion of upgrade allows only stability verification.

KG-RUNTIME-142 must still be an explicit user authorization gate unless the user provides exact execution authorization. It must not default to model upgrade execution.

## 10. Post-Upgrade Validation Boundary

If a later explicitly authorized stage completes a single-model upgrade, the next allowed phase is stability verification only. It is not real use, not formal trial use, and not controlled trial use.

Post-upgrade stability verification must include at least:

- Confirm the model can load.
- Confirm basic question-answer stability.
- Confirm long-text response stability.
- Confirm technical-bid-style text output stability.
- Confirm preview-only path compatibility before any operational use.
- Confirm generation, export, and writeback paths are not triggered.
- Confirm real KG file body content is not read.
- Confirm real KG JSON is not parsed.
- Inspect output quality for obvious format, language, hallucination, truncation, and refusal-pattern issues.
- Record failures and reviewer notes.

No stability check may silently broaden into service runtime, endpoint access, real KG reading, JSON parsing, generation, export, writeback, or trial use.

## 11. Trial Boundary

The following sequence must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only path is completed.
3. The local model is upgraded to the latest available usable version through an explicitly authorized single-model execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Preview-only verification before model upgrade is internal technical verification only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 12. KG-RUNTIME-142 Recommendation

Recommended next stage:

`KG-RUNTIME-142: single-model upgrade execution explicit user authorization gate`

KG-RUNTIME-142 should remain an explicit authorization gate by default. It should not automatically execute an upgrade.

Only after the user reviews KG-RUNTIME-141 and explicitly approves the model name, exact command whitelist, network pull permission, old-model retention policy, latest-tag behavior, download-size boundary, retry policy, and failure handling rules may a later node execute any upgrade command.

If the user does not provide explicit authorization, no upgrade execution node may begin.

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
- This stage does not connect RAG, registry, or CI.
- This stage does not trigger generation, export, or writeback.
- This stage does not write `output`, `job`, or `export`.
- This stage does not modify code.
- This stage does not modify frontend, tests, config, or JSON.
- This stage does not add `.pyc` or `__pycache__`.
- This stage does not enter real use.
- This stage does not enter formal trial use.
- This stage does not enter controlled trial use.
- Model upgrade has not been executed.
- KG-RUNTIME-142 has not been entered.
