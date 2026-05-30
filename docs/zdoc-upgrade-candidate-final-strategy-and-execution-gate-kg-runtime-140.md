# KG-RUNTIME-140 ZDoc Upgrade Candidate Final Strategy and Execution Gate

## 1. Runtime Scope

- Stage: KG-RUNTIME-140
- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Stage type: docs-only strategy and execution gate
- New artifact: `docs/zdoc-upgrade-candidate-final-strategy-and-execution-gate-kg-runtime-140.md`
- Stop line: do not enter KG-RUNTIME-141

KG-RUNTIME-140 is a docs-only strategy stage. It records the final upgrade-candidate strategy and the authorization gate required before any later upgrade execution stage.

KG-RUNTIME-140 does not run Ollama, does not execute `ollama list`, does not execute any Ollama command, does not pull, upgrade, delete, replace, or select any model for runtime use, does not run the ZDoc service, does not access endpoints, and does not enter real use, formal trial use, controlled trial use, or preview-only operational use.

## 2. Baseline

KG-RUNTIME-139 ended with the following recorded state:

- End HEAD: `b9b28770ffe5b4f41e2fbedcd7f45ad8d75c0086`
- Remote tag: `v0.1.522-zdoc-controlled-latest-version-lookup`
- New docs-only file: `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`
- Worktree state after KG-RUNTIME-139: clean
- Network behavior in KG-RUNTIME-139: read-only version lookup only
- Lookup scope in KG-RUNTIME-139: only model families already present in the local model inventory basis

KG-RUNTIME-139 maintained the key non-execution boundaries:

- It did not run Ollama.
- It did not execute `ollama list`.
- It did not execute `ollama pull`, `ollama run`, `ollama rm`, `ollama serve`, or any other Ollama command.
- It did not upgrade, pull, delete, or replace any model.
- It did not run the ZDoc service.
- It did not access endpoints.
- It did not read real KG file body content.
- It did not parse real KG JSON.
- It did not trigger generation, export, or writeback.
- It did not write `output`, `job`, or `export`.
- It did not enter real use or trial use.

## 3. Source Boundary

KG-RUNTIME-140 uses only the KG-RUNTIME-139 lookup result in `docs/zdoc-controlled-latest-version-lookup-kg-runtime-139-review.md`.

This stage does not add any internet lookup, does not expand model families, does not re-check official model pages, does not query model registries, does not run `ollama list`, does not collect a new local inventory, and does not scan directories.

The only model families considered are:

- `qwen3-next`
- `qwen3-coder`
- `qwen3`
- `deepseek-r1`

## 4. Candidate Model Family Review

### qwen3-next

- KG-RUNTIME-139 latest available version summary:
  - Official Ollama latest alias: `qwen3-next:latest`
  - Official Ollama size alias marked latest: `qwen3-next:80b`
  - Provider model line observed: `Qwen/Qwen3-Next-80B-A3B-Instruct` and `Qwen/Qwen3-Next-80B-A3B-Thinking`
- Relationship to current local model family:
  - Local model basis includes `qwen3-next:80b-a3b-instruct-q8_0`.
  - The local model is in the same model family and appears to be an instruct quantized tag, while the official Ollama latest alias points to the general `80b` tag.
- Upgrade-candidate recommendation:
  - Recommended as a candidate, but not as the first execution candidate unless the user explicitly prioritizes maximum quality over download size, memory pressure, and runtime latency.
- Suggested priority:
  - P1.
- Main use positioning:
  - High-capability general ZDoc drafting, long-context reasoning, and technical-bid language quality evaluation after stability is proven.
- Main risks:
  - Large model footprint.
  - Potential memory pressure on the local machine.
  - Potential response-time degradation.
  - Ambiguity between the existing quantized instruct local tag and the official latest alias.
  - Higher blast radius if upgraded before the preview-only and stability gates are ready.
- Allowed into next execution preparation:
  - Yes, but only as an authorization-request candidate. No execution command is allowed by this stage.
- Separate user authorization required:
  - Yes. The user must explicitly authorize the exact model name, command, network pull permission, size allowance, old-model retention policy, retry policy, and latest-tag behavior before any execution.

### qwen3-coder

- KG-RUNTIME-139 latest available version summary:
  - Series-level official Ollama latest line observed: `qwen3-coder-next:latest`
  - Existing local-library latest alias: `qwen3-coder:latest`
  - Existing local-library size alias marked latest: `qwen3-coder:30b`
  - Provider model line observed: `Qwen/Qwen3-Coder-Next`
- Relationship to current local model family:
  - Local model basis includes `qwen3-coder:30b`.
  - The local model matches the official Ollama `qwen3-coder:30b` alias, while `qwen3-coder-next` is a newer official code-model line.
- Upgrade-candidate recommendation:
  - Not recommended as the primary ZDoc model-upgrade candidate for this stage because it is code-specialized and the current upgrade decision is about ZDoc / AI knowledge-graph document workflows.
- Suggested priority:
  - Hold.
- Main use positioning:
  - Code-oriented support, adapter/debug analysis, and future developer-assistance workflows, not the first ZDoc content-generation upgrade candidate.
- Main risks:
  - Misalignment with the document-generation target.
  - Possible regression for long-form Chinese technical-bid prose if used as a general text model.
  - Newer `qwen3-coder-next` line may require a separate compatibility and behavior review.
- Allowed into next execution preparation:
  - No, not for the KG-RUNTIME-141 single-model ZDoc upgrade authorization request unless the user explicitly changes the target to a code-model upgrade.
- Separate user authorization required:
  - Yes for any future execution, and especially yes if the user wants to replace or supplement `qwen3-coder:30b` with `qwen3-coder-next`.

### qwen3

- KG-RUNTIME-139 latest available version summary:
  - Series-level official Ollama latest line observed: `qwen3.6:latest`
  - Series-level official Ollama size alias marked latest: `qwen3.6:35b`
  - Provider current open-weight model line observed: `Qwen3.6-35B-A3B`
  - Existing local-library latest alias: `qwen3:latest`
  - Existing local-library size alias marked latest: `qwen3:8b`
  - Earlier official Qwen3 updated model tags observed in family: `qwen3:30b`, `qwen3:235b`
- Relationship to current local model family:
  - Local model basis includes `qwen3:30b`, `qwen3:14b`, `qwen3:8b`, and `qwen3:0.6b`.
  - The local models are in the broad Qwen3 line, while the current series-level line observed by KG-RUNTIME-139 is `qwen3.6`.
- Upgrade-candidate recommendation:
  - Recommended as the primary candidate for the next authorization-request stage because it is the closest general-purpose continuation of the existing local Qwen3 family and is better aligned with ZDoc document-generation work than the code-specialized candidate.
- Suggested priority:
  - P0.
- Main use positioning:
  - Primary ZDoc general document-generation, technical-bid text drafting, structured long-text response, and preview-only chain compatibility candidate after explicit authorization and upgrade execution.
- Main risks:
  - `qwen3.6:35b` is not identical to existing local `qwen3:30b`, `qwen3:14b`, `qwen3:8b`, or `qwen3:0.6b` tags.
  - Download size and runtime memory requirements must be confirmed before execution.
  - Output style may change from the existing Qwen3 local models.
  - Stability and preview-only compatibility are not proven until after upgrade and verification.
- Allowed into next execution preparation:
  - Yes, as the recommended single-model authorization-request candidate.
- Separate user authorization required:
  - Yes. KG-RUNTIME-141 or any later stage must ask for explicit user authorization before running any command.

### deepseek-r1

- KG-RUNTIME-139 latest available version summary:
  - Official Ollama latest alias: `deepseek-r1:latest`
  - Official Ollama size alias marked latest: `deepseek-r1:8b`
  - Provider current full model line observed: `deepseek-ai/DeepSeek-R1-0528`
  - Provider current small distilled model line observed: `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`
- Relationship to current local model family:
  - Local model basis includes `deepseek-r1:32b`.
  - The local model is in the same DeepSeek-R1 family but corresponds to a distilled Qwen 32B line, while the official Ollama latest alias points to the 0528 Qwen3 8B distilled line.
- Upgrade-candidate recommendation:
  - Recommended only as a secondary candidate for reasoning-focused evaluation, not as the first ZDoc upgrade execution candidate.
- Suggested priority:
  - P2.
- Main use positioning:
  - Reasoning-oriented review, critique, and fallback analysis after the primary general ZDoc model path is stable.
- Main risks:
  - Latest Ollama alias points to a smaller 8B distilled line rather than the existing 32B local line.
  - Output style may be more reasoning-heavy than desired for polished technical-bid prose.
  - Replacement could reduce capacity for some tasks if the 32B local model is removed or overwritten.
  - Must not delete or replace the existing 32B model without separate authorization.
- Allowed into next execution preparation:
  - Yes only as a later secondary candidate; not recommended for KG-RUNTIME-141 if KG-RUNTIME-141 remains a single primary ZDoc upgrade authorization request.
- Separate user authorization required:
  - Yes for any execution, and explicit no-delete confirmation is required before any command is allowed.

## 5. Upgrade Candidate Priority

| Priority | Candidate | Recommendation | Reason |
|---|---|---|---|
| P0 | `qwen3.6:35b` / Qwen3 general line | Primary single-model authorization-request candidate | Best fit for ZDoc general document-generation and closest broad continuation of existing local `qwen3` models. |
| P1 | `qwen3-next:80b` / Qwen3-Next line | High-quality secondary candidate | Strong potential quality candidate, but larger footprint and higher runtime risk make it a second step after the P0 path is evaluated. |
| P2 | `deepseek-r1:latest` / DeepSeek-R1 0528 line | Reasoning-focused secondary candidate | Useful for review and reasoning, but latest alias differs materially from existing local 32B line and is not the first document-generation candidate. |
| Hold | `qwen3-coder-next:latest` / Qwen3-Coder line | Hold for ZDoc model upgrade | Code-specialized model line; not aligned as the first ZDoc document-generation upgrade candidate. |

No priority entry authorizes upgrade execution. These priorities are strategy guidance only.

## 6. Recommended Upgrade Strategy

- Do not upgrade all models at once.
- Select exactly one primary candidate for controlled upgrade execution after explicit user authorization.
- Recommended first authorization-request candidate: the Qwen3 general line represented by `qwen3.6:35b`, subject to user confirmation of exact model name, command, download size, and local retention policy.
- Before upgrade execution, preserve the current model list and version record.
- Before upgrade execution, record which local tags must be retained.
- After upgrade execution, run stability verification before any preview-only integration use.
- Before stability verification passes, do not connect the upgraded model to the formal preview-only path.
- Before preview-only path verification passes, do not enter 1 to 2 person controlled trial.
- Before 1 to 2 person controlled trial passes, do not expand to 2 to 5 person small-concurrency trial.
- Do not replace `latest` tags, delete old models, or change runtime selection unless the user separately authorizes those exact actions.
- Treat model upgrade as a technical prerequisite only; it is not trial authorization and not real-use authorization.

## 7. Upgrade Execution Authorization Gate

KG-RUNTIME-141 or any later upgrade-execution stage must obtain explicit user authorization before any model command is run.

The authorization request must include, at minimum:

- The exact model command or commands the user allows.
- The exact model name or tag the user allows to upgrade or pull.
- Whether network download / online pull is allowed.
- Whether replacing or updating a `latest` tag is allowed.
- Whether the old model must be retained.
- The maximum allowed download size, or an explicit user confirmation that no size limit is imposed.
- Whether a failed download or failed load may be retried.
- A default prohibition on deleting old models unless the user separately authorizes deletion.
- A statement that upgrade completion only permits stability verification and does not permit real use.
- A statement that upgrade completion only permits stability verification and does not permit trial use.
- A statement that multiple models must not be upgraded at the same time unless the user separately authorizes multi-model execution.

Without this explicit authorization, KG-RUNTIME-141 must remain an authorization-request stage and must not execute `ollama pull`, `ollama run`, `ollama rm`, `ollama serve`, `ollama show`, `ollama ps`, `ollama list`, or any other Ollama command.

## 8. Rollback and Abort Criteria

The upgrade process must abort or roll back according to the separately authorized retention policy if any of the following occur:

- Download fails.
- Download is incomplete or checksum / model availability cannot be trusted.
- Model cannot be loaded.
- Model loads but fails basic question-answer stability.
- Model output quality is clearly abnormal for ZDoc technical-bid text.
- Response time is materially worse than the current acceptable local baseline.
- Memory use exceeds the local machine's acceptable operating range.
- Runtime causes system instability.
- Preview-only validation is unstable.
- There is any risk that real KG file body content will be read.
- There is any risk that real KG JSON will be parsed.
- There is any risk that generation, export, or writeback could be triggered.
- There is any risk that `output`, `job`, or `export` will be written.
- The execution command differs from the exact user-authorized command.
- The process would delete, replace, or retag an old model without separate authorization.
- The process would upgrade more than one model without separate authorization.

## 9. Stability Verification Requirements

After an explicitly authorized upgrade completes, the minimum stability verification must include:

- Confirm the model can load.
- Confirm basic question-answer stability.
- Confirm long-text response stability.
- Confirm technical-bid-style text output stability.
- Confirm preview-only path compatibility before any formal preview-only use.
- Confirm generation, export, and writeback paths are not triggered.
- Confirm real KG file body content is not read.
- Confirm real KG JSON is not parsed.
- Inspect output quality for obvious format, language, hallucination, truncation, and refusal-pattern issues.
- Record failures with command, input class, observed behavior, timestamp, and reviewer note.
- Record review results before any later trial-readiness decision.

This verification is not real use, not trial use, and not authorization to connect the model to production-facing or user-facing workflows.

## 10. Trial Readiness Boundary

The following order must not be skipped:

1. KG safe integration is completed.
2. ZDoc preview-only path is completed.
3. The local model is upgraded to the latest available usable version through an explicitly authorized execution stage.
4. Post-upgrade stability verification passes.
5. Only then may the project enter 1 to 2 person controlled trial.
6. Only after that may the project expand to 2 to 5 person small-concurrency trial.

Preview-only verification before model upgrade is internal technical verification only. It does not count as formal trial use, controlled trial use, production use, or real use.

## 11. KG-RUNTIME-141 Recommendation

Recommended next stage:

`KG-RUNTIME-141: single-model upgrade execution authorization request`

KG-RUNTIME-141 should first request explicit user authorization for a single model. KG-RUNTIME-141 must not execute concrete upgrade commands unless the user explicitly authorizes the exact command, exact model name, network behavior, old-model retention, latest-tag behavior, size limit, retry policy, and no-delete boundary.

If the user does not provide explicit execution authorization, KG-RUNTIME-141 must stop as an authorization-request stage.

## 12. Final Compliance Statement

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
- This stage does not enter trial use.
- Model upgrade has not been executed.
- KG-RUNTIME-141 has not been entered.
