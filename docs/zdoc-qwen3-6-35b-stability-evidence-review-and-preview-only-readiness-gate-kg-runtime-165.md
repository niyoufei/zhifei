# ZDoc Qwen3.6 35B Stability Evidence Review And Preview-Only Readiness Gate - KG-RUNTIME-165

## 1. Scope

KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE is a docs-only review and authorization gate node for the user-mediated lightweight stability evidence of:

`qwen3.6:35b`

This node only reviews user-provided local lightweight stability validation evidence, records output format observations, and forms the later ZDoc preview-only readiness authorization threshold.

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

- Starting HEAD: `ce1bd6703b217c4e7e19095420b422e23d41625c`
- Starting remote tag: `v0.1.554-zdoc-qwen3-6-35b-user-mediated-stability-evidence-intake`
- Candidate: `qwen3.6:35b`
- Prior completed node: `KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE`
- Current node: `KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE`

The following target docs were read for this docs-only review and authorization gate:

1. `docs/zdoc-qwen3-6-35b-user-mediated-stability-validation-evidence-intake-kg-runtime-164.md`
2. `docs/zdoc-qwen3-6-35b-post-upgrade-stability-validation-authorization-gate-kg-runtime-164.md`
3. `docs/zdoc-single-model-upgrade-qwen3-6-35b-user-mediated-pull-execution-evidence-intake-kg-runtime-163-pull-user-mediated-evidence-intake.md`
4. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-retry-path-authorization-gate-kg-runtime-163-pull-retry-authorization-gate.md`
5. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-pre-list-blocked-audit-kg-runtime-163-pull-blocked-audit.md`
6. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-execution-explicit-authorization-gate-kg-runtime-163-pull-authorization-gate.md`

## 3. Stability Evidence Reviewed

`KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE` has completed and passed.

The user selected Option A and completed lightweight stability validation on the user's local machine.

The user-provided evidence shows:

1. User local `ollama list` succeeded.
2. `qwen3.6:35b` appears in the user local list.
3. `qwen3.6:35b` ID is `07d35212591f`.
4. `qwen3.6:35b` SIZE is `23 GB`.
5. The original 7 models still appear in the list.
6. The user completed 1 minimal synthetic prompt response validation that was not project data, not real KG, and not business data.
7. The response validation did not show missing model failure, service unavailable failure, response interruption, or CLI error.
8. The response validation did not connect to ZDoc.
9. The response validation did not access endpoints.
10. The response validation did not read or parse real KG.
11. The response validation did not trigger generation, export, or write-back.
12. The validation is not formal trial use.
13. Current state still has not entered 1-2 person controlled trial use.
14. Current state still has not entered 2-5 person limited concurrent trial use.

No evidence reviewed by this node shows deletion, replacement, or overwrite of any other model.

No evidence reviewed by this node shows modification of the `latest` pointer.

## 4. Stability Evidence Review Conclusion

Review conclusion:

1. `qwen3.6:35b` local installation and basic response capability are supported by user-provided evidence.
2. This lightweight stability validation may be used only as preliminary evidence of local model availability and basic response capability.
3. This validation must not be expanded to mean the ZDoc chain has been validated.
4. This validation must not be expanded to mean KG safe access has been validated.
5. This validation must not be expanded to mean the preview-only chain has been validated.
6. This validation must not be expanded to mean formal trial readiness conditions are satisfied.

The user-provided output includes longer thinking / self-check / mixed Chinese-English process text before the final answer.

This is recorded as:

`OUTPUT FORMAT OBSERVATION / verbose reasoning-like trace visible before final answer`

This observation is not a hard failure for this lightweight stability validation.

This observation must be a focus item for later preview-only chain validation.

If a later node enters ZDoc preview-only validation, it must specifically check:

1. Whether output can be restricted to the target format.
2. Whether process-style thinking text is exposed.
3. Whether mixed Chinese-English process text appears.
4. Whether the boundary of no real KG reference and no formal chain trigger can be followed consistently.

## 5. Preview-Only Readiness Gate

Current state may only enter a preview-only readiness authorization threshold.

Current state must not directly enter preview-only execution.

If a later node enters preview-only related validation, it must continue to satisfy:

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

## 6. Current Decision

Current decision:

`LIGHT STABILITY EVIDENCE REVIEWED / OUTPUT FORMAT OBSERVATION RECORDED / PREVIEW-ONLY READINESS AUTHORIZATION REQUIRED`

This decision also explicitly means:

`NO-GO FOR TRIAL / NO-GO FOR REAL USE / NO-GO FOR ZDOC SERVICE EXECUTION`

Decision basis:

1. KG-RUNTIME-164 user-mediated lightweight stability evidence intake has completed and passed.
2. The user selected Option A.
3. User local `ollama list` evidence succeeded.
4. `qwen3.6:35b` appears in the user local list with ID `07d35212591f` and SIZE `23 GB`.
5. The original 7 models still appear in the user local list.
6. The user completed 1 minimal synthetic prompt response validation outside project data, real KG, and business data.
7. The response validation did not show missing model, service unavailable, response interruption, or CLI error.
8. The response validation did not connect to ZDoc, access endpoints, read or parse real KG, or trigger generation/export/write-back.
9. The validation is not formal trial use.
10. The output format observation has been recorded and must remain a later preview-only focus item.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize reading or parsing real KG.

This decision does not authorize generation, export, or write-back.

This decision does not authorize preview-only execution.

This decision does not authorize real use or trial use.

This decision does not authorize 1-2 person controlled trial use.

This decision does not authorize 2-5 person limited concurrent trial use.

## 7. Next Node Suggestion

Suggested next node:

`KG-RUNTIME-166-PREVIEW-ONLY-READINESS-AUTHORIZATION-GATE: ZDoc preview-only readiness authorization gate docs-only`

The suggested next node may only form the ZDoc preview-only readiness authorization threshold.

The suggested next node must not directly run the ZDoc service.

The suggested next node must not access endpoints.

The suggested next node must not read real KG.

The suggested next node must not trigger generation, export, or write-back.

The suggested next node must not enter real use or trial use.

The suggested next node must not enter 1-2 person controlled trial use.

The suggested next node must not enter 2-5 person limited concurrent trial use.

This node does not enter the suggested next node.

## 8. Final Status

- KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE completed as a docs-only review and authorization gate.
- KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE has completed and passed.
- User selected Option A.
- User local lightweight stability validation evidence was reviewed.
- Codex did not run Ollama.
- Codex did not execute `ollama list`.
- Codex did not execute `ollama run`.
- Codex did not execute `ollama pull`.
- Codex did not execute `ollama rm`.
- Codex did not execute `ollama serve`.
- Codex did not execute any other Ollama command.
- Codex did not delete, replace, or overwrite any model.
- Codex did not modify the `latest` pointer.
- Codex did not run the ZDoc service.
- Codex did not access endpoints.
- Codex did not read real KG.
- Codex did not parse KG JSON.
- Codex did not trigger generation, export, or write-back.
- Codex did not write `output`, `job`, or `export`.
- User local `ollama list` succeeded.
- `qwen3.6:35b` appears in the user local list.
- `qwen3.6:35b` ID is `07d35212591f`.
- `qwen3.6:35b` SIZE is `23 GB`.
- The original 7 models still appear in the list.
- User local lightweight synthetic prompt response validation completed once.
- The response validation did not show missing model, service unavailable, response interruption, or CLI error.
- The response validation did not connect to ZDoc.
- The response validation did not access endpoints.
- The response validation did not read or parse real KG.
- The response validation did not trigger generation, export, or write-back.
- The validation is not formal trial use.
- This validation only supports local model availability and basic response capability.
- This validation must not be expanded to mean the ZDoc chain has been validated.
- This validation must not be expanded to mean KG safe access has been validated.
- This validation must not be expanded to mean the preview-only chain has been validated.
- This validation must not be expanded to mean formal trial readiness conditions are satisfied.
- Output format observation: `OUTPUT FORMAT OBSERVATION / verbose reasoning-like trace visible before final answer`.
- The output format observation is not a hard failure for this lightweight stability validation.
- The output format observation must be a later preview-only focus item.
- Preview-only readiness threshold is recorded.
- Current decision: `LIGHT STABILITY EVIDENCE REVIEWED / OUTPUT FORMAT OBSERVATION RECORDED / PREVIEW-ONLY READINESS AUTHORIZATION REQUIRED`
- Explicit NO-GO: `NO-GO FOR TRIAL / NO-GO FOR REAL USE / NO-GO FOR ZDOC SERVICE EXECUTION`
- Next node suggestion: `KG-RUNTIME-166-PREVIEW-ONLY-READINESS-AUTHORIZATION-GATE: ZDoc preview-only readiness authorization gate docs-only`
- Real use or trial use was not entered.
- 1-2 person controlled trial use was not entered.
- 2-5 person limited concurrent trial use was not entered.
- The next node was not entered.

KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE stops here and waits for human review.
