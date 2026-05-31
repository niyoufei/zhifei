# ZDoc Preview-Only Readiness Authorization Gate - KG-RUNTIME-166

## 1. Scope

KG-RUNTIME-166-PREVIEW-ONLY-READINESS-AUTHORIZATION-GATE is a docs-only authorization gate for ZDoc preview-only readiness.

This node is based on the conclusion of `KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE`.

This node only records the current state, preview-only prerequisites, prohibited boundaries, later authorization wording, and next-step recommendation.

This node is not an Ollama command node, not a ZDoc service node, not an endpoint node, not a real KG read node, not a generation/export/write-back node, not preview-only execution, and not real use or trial use.

This node explicitly:

- Does not run Ollama.
- Does not execute `ollama list`.
- Does not execute `ollama run`.
- Does not execute `ollama pull`.
- Does not execute `ollama rm`.
- Does not execute `ollama serve`.
- Does not execute any other Ollama command.
- Does not pull, delete, replace, or overwrite any model.
- Does not modify the `latest` pointer.
- Does not run the ZDoc service.
- Does not access endpoints.
- Does not read real KG.
- Does not read real KG file body content.
- Does not parse real KG JSON.
- Does not trigger generation, export, or write-back.
- Does not write `output`, `job`, or `export`.
- Does not modify adapter, route, helper, or `main.py` files.
- Does not modify frontend, tests, config, or JSON files.
- Does not connect RAG, registry, or CI.
- Does not enter real use or trial use.
- Does not enter 1-2 person controlled trial use.
- Does not enter 2-5 person limited concurrent trial use.

## 2. Baseline

This node starts from:

- Starting HEAD: `338d27432d54cd4f60ac1649857079882775d4b8`
- Starting remote tag: `v0.1.555-zdoc-qwen3-6-35b-stability-evidence-review-preview-readiness-gate`
- Prior completed node: `KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE`
- Current node: `KG-RUNTIME-166-PREVIEW-ONLY-READINESS-AUTHORIZATION-GATE`

The following target docs were read for this docs-only authorization gate:

1. `docs/zdoc-qwen3-6-35b-stability-evidence-review-and-preview-only-readiness-gate-kg-runtime-165.md`
2. `docs/zdoc-qwen3-6-35b-user-mediated-stability-validation-evidence-intake-kg-runtime-164.md`
3. `docs/zdoc-qwen3-6-35b-post-upgrade-stability-validation-authorization-gate-kg-runtime-164.md`
4. `docs/zdoc-single-model-upgrade-qwen3-6-35b-user-mediated-pull-execution-evidence-intake-kg-runtime-163-pull-user-mediated-evidence-intake.md`
5. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-retry-path-authorization-gate-kg-runtime-163-pull-retry-authorization-gate.md`
6. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-pre-list-blocked-audit-kg-runtime-163-pull-blocked-audit.md`

## 3. Current Evidence State

`KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE` has completed and passed.

`qwen3.6:35b` local installation and basic response capability are supported by user-provided evidence.

The current state may only be interpreted as preliminary evidence of local model availability and basic response capability.

This state must not be expanded to mean the ZDoc chain has been validated.

This state must not be expanded to mean KG safe access has been validated.

This state must not be expanded to mean the preview-only chain has been validated.

This state must not be expanded to mean formal trial readiness conditions are satisfied.

The output format observation has been recorded as:

`OUTPUT FORMAT OBSERVATION / verbose reasoning-like trace visible before final answer`

This observation is not a hard failure for the lightweight stability validation.

This observation must be a focus item for later preview-only validation.

Current state remains:

`NO-GO FOR TRIAL`

Current state remains:

`NO-GO FOR REAL USE`

Current state remains:

`NO-GO FOR ZDOC SERVICE EXECUTION`

## 4. Preview-Only Readiness Authorization Threshold

If a later node enters ZDoc preview-only readiness or preview-only validation, it must continue to satisfy the following boundaries:

1. Preview-only / no-write only.
2. Do not trigger `/generate`.
3. Do not trigger `/export_docx`.
4. Do not trigger `/review/apply`.
5. Do not trigger ZBid write-back.
6. Do not write `output`, `job`, or `export`.
7. Do not read or parse real KG unless a later node separately grants explicit KG safe-access authorization and boundaries.
8. Do not enter real use or trial use.
9. Do not enter 1-2 person controlled trial use.
10. Do not enter 2-5 person limited concurrent trial use.
11. Must specifically observe whether model output exposes process-style thinking text.
12. Must specifically observe whether mixed Chinese-English process text appears.
13. Must specifically observe whether the target output format can be followed consistently.
14. Must specifically observe whether the boundary of no real KG reference and no formal chain trigger can be followed consistently.

This authorization threshold does not mean preview-only has been validated.

This authorization threshold does not mean formal trial readiness conditions are satisfied.

## 5. Later Optional Paths

The following paths are future options only. This node does not execute either path and does not treat either path as already authorized.

### Option A: docs-only preview-only readiness review, recommended

Continue in docs-only mode to organize the current ZDoc preview-only chain state, pending validation boundaries, verifiable items, and non-verifiable items.

Option A must not run services, access endpoints, or read real KG.

### Option B: command-limited preview-only technical validation after explicit authorization, fallback

Only after later explicit user authorization may Codex execute an extremely limited preview-only technical validation.

This path must separately form authorization and must still not trigger formal chain execution, must not write `output`, `job`, or `export`, must not read or parse real KG, and must not enter real use or trial use.

## 6. Current Decision

Current decision:

`PREVIEW-ONLY READINESS AUTHORIZATION GATE FORMED / NO EXECUTION AUTHORIZED`

This decision also explicitly means:

`NO-GO FOR TRIAL / NO-GO FOR REAL USE / NO-GO FOR ZDOC SERVICE EXECUTION`

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize reading or parsing real KG.

This decision does not authorize generation, export, or write-back.

This decision does not authorize preview-only execution.

This decision does not authorize real use or trial use.

This decision does not authorize 1-2 person controlled trial use.

This decision does not authorize 2-5 person limited concurrent trial use.

## 7. Future User Authorization Template

Any later execution-type preview-only validation requires explicit user authorization.

Authorization prompt must prominently show:

**是否需要用户授权：需要。**

Future authorization template:

“我明确授权 KG-RUNTIME-167 执行 command-limited preview-only technical validation。授权范围仅限：确认 git 状态、读取前序目标 docs、按 preview-only / no-write 边界执行最小验证。禁止触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回；禁止写 output / job / export；禁止读取或解析真实 KG；禁止进入真实使用 / 试用阶段。完成后必须回报并停止，等待人工审核。”

This template is not treated as authorization granted by this node.

## 8. Next Node Suggestion

Suggested next node:

`KG-RUNTIME-167-PREVIEW-ONLY-CURRENT-STATE-AND-VALIDATION-SCOPE-REVIEW: ZDoc preview-only current state and validation scope review docs-only`

The suggested next node should remain docs-only and should only organize the current preview-only chain state, verifiable scope, prohibited scope, and later execution-type validation authorization wording.

This node does not enter the suggested next node.

## 9. Final Status

- KG-RUNTIME-166-PREVIEW-ONLY-READINESS-AUTHORIZATION-GATE completed as a docs-only authorization gate.
- KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE has completed and passed.
- `qwen3.6:35b` local installation and basic response capability are supported by user-provided evidence.
- Current evidence supports only preliminary local model availability and basic response capability.
- This state must not be expanded to mean the ZDoc chain has been validated.
- This state must not be expanded to mean KG safe access has been validated.
- This state must not be expanded to mean the preview-only chain has been validated.
- This state must not be expanded to mean formal trial readiness conditions are satisfied.
- Output format observation: `OUTPUT FORMAT OBSERVATION / verbose reasoning-like trace visible before final answer`.
- The output format observation is not a hard failure for lightweight stability validation.
- The output format observation must remain a later preview-only focus item.
- Preview-only readiness authorization threshold is formed.
- Current decision: `PREVIEW-ONLY READINESS AUTHORIZATION GATE FORMED / NO EXECUTION AUTHORIZED`.
- Explicit NO-GO: `NO-GO FOR TRIAL / NO-GO FOR REAL USE / NO-GO FOR ZDOC SERVICE EXECUTION`.
- Future user authorization template is recorded.
- The future authorization template is not treated as already authorized.
- Suggested next node: `KG-RUNTIME-167-PREVIEW-ONLY-CURRENT-STATE-AND-VALIDATION-SCOPE-REVIEW: ZDoc preview-only current state and validation scope review docs-only`.
- Codex did not run Ollama.
- Codex did not execute `ollama list`.
- Codex did not execute `ollama run`.
- Codex did not execute `ollama pull`.
- Codex did not execute `ollama rm`.
- Codex did not execute `ollama serve`.
- Codex did not execute any other Ollama command.
- Codex did not run the ZDoc service.
- Codex did not access endpoints.
- Codex did not read real KG.
- Codex did not parse KG JSON.
- Codex did not trigger generation, export, or write-back.
- Codex did not write `output`, `job`, or `export`.
- Codex did not enter real use or trial use.
- Codex did not enter 1-2 person controlled trial use.
- Codex did not enter 2-5 person limited concurrent trial use.
- The next node was not entered.

KG-RUNTIME-166-PREVIEW-ONLY-READINESS-AUTHORIZATION-GATE stops here and waits for human review.
