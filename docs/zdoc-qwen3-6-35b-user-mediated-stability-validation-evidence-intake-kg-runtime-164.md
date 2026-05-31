# ZDoc Qwen3.6 35B User-Mediated Stability Validation Evidence Intake - KG-RUNTIME-164

## 1. Scope

KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE is a docs-only evidence intake node for the user-mediated lightweight stability validation of:

`qwen3.6:35b`

This node only organizes user-provided local terminal screenshot evidence after the user selected Option A and manually completed lightweight stability validation in the local terminal.

Codex did not run Ollama in this node.

This node is not an Ollama command node, not a ZDoc service node, not an endpoint node, not a real KG read node, not a generation/export/write-back node, and not a real-use or trial-use node.

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

- Starting HEAD: `2451c11a2c25ce52d78e6bcfce57dd044f71ee29`
- Starting remote tag: `v0.1.553-zdoc-qwen3-6-35b-stability-authorization-gate`
- Candidate: `qwen3.6:35b`
- Prior completed node: `KG-RUNTIME-164-STABILITY-AUTHORIZATION-GATE`
- Prior recommended Option A node: `KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE: qwen3.6:35b user-mediated stability validation evidence intake docs-only`

The following prior docs were read for this docs-only evidence intake:

1. `docs/zdoc-qwen3-6-35b-post-upgrade-stability-validation-authorization-gate-kg-runtime-164.md`
2. `docs/zdoc-single-model-upgrade-qwen3-6-35b-user-mediated-pull-execution-evidence-intake-kg-runtime-163-pull-user-mediated-evidence-intake.md`
3. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-retry-path-authorization-gate-kg-runtime-163-pull-retry-authorization-gate.md`
4. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-pre-list-blocked-audit-kg-runtime-163-pull-blocked-audit.md`
5. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-execution-explicit-authorization-gate-kg-runtime-163-pull-authorization-gate.md`
6. `docs/zdoc-single-model-upgrade-user-mediated-ollama-service-startup-and-pre-upgrade-inventory-intake-kg-runtime-163-service-check-intake.md`

## 3. User-Mediated Option A Evidence Received

The user selected Option A.

The user manually completed lightweight stability validation in the local terminal and provided screenshot evidence.

This node only organizes user-provided local terminal screenshot evidence.

Codex did not run Ollama.

Codex did not execute:

- `ollama list`
- `ollama run`
- `ollama pull`
- `ollama rm`
- `ollama serve`
- Any other Ollama command

## 4. Local Inventory Evidence

The user-provided screenshot evidence shows that local `ollama list` succeeded.

The list includes the target model:

| Model name | ID | SIZE |
|---|---|---|
| `qwen3.6:35b` | `07d35212591f` | `23 GB` |

The evidence includes one `ollama list` result with `qwen3.6:35b` modified `13 seconds ago`.

The later evidence includes another `ollama list` result with `qwen3.6:35b` modified `9 hours ago`.

The original 7 models still appear in the user-provided list:

| # | Model name | ID | SIZE |
|---|---|---|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `fc9e251df737` | `84 GB` |
| 2 | `qwen3-coder:30b` | `06c1097efce0` | `18 GB` |
| 3 | `deepseek-r1:32b` | `edba8017331d` | `19 GB` |
| 4 | `qwen3:30b` | `ad815644918f` | `18 GB` |
| 5 | `qwen3:14b` | `bddb181c33f2` | `9.3 GB` |
| 6 | `qwen3:8b` | `500a1f067a9f` | `5.2 GB` |
| 7 | `qwen3:0.6b` | `7df6b6e09427` | `522 MB` |

Inventory evidence conclusion:

- User local `ollama list` succeeded.
- `qwen3.6:35b` appears in the user-provided local list.
- `qwen3.6:35b` ID is `07d35212591f`.
- `qwen3.6:35b` SIZE is `23 GB`.
- The original 7 models still appear in the user-provided list.
- No evidence shows deletion, replacement, or overwrite of any other model.
- No evidence shows modification of the `latest` pointer.
- Codex did not run `ollama list`.

## 5. Lightweight Synthetic Prompt Response Evidence

The user manually performed 1 lightweight response validation against `qwen3.6:35b` using a minimal synthetic prompt.

The prompt was not project data, not real KG, and not business data.

The user-provided screenshot evidence shows that the model completed a response and produced a final Chinese 3-sentence answer about a generic local large language model.

The response validation evidence does not show:

1. Missing model failure.
2. Service unavailable failure.
3. Response interruption.
4. CLI error.
5. ZDoc service participation.
6. Endpoint access.
7. Real KG, project material, or business data reference.

Response validation conclusion:

- User local lightweight synthetic prompt response validation completed once.
- The validation did not connect to ZDoc.
- The validation did not access endpoints.
- The validation did not read or parse real KG.
- The validation did not trigger generation, export, or write-back.
- The validation is not formal trial use.

## 6. Output Format Observation

The user-provided screenshot evidence shows a longer thinking / self-check / mixed Chinese-English process text before the final answer.

This is recorded as:

`OUTPUT FORMAT OBSERVATION / verbose reasoning-like trace visible before final answer`

This observation is not treated as a hard failure for this lightweight stability validation evidence intake.

If a later node enters ZDoc preview-only readiness review or small internal technical validation authorization, output format control, prompt constraints, and unnecessary process text should remain explicit observation items.

## 7. Current Decision

Current decision:

`USER-MEDIATED LIGHT STABILITY EVIDENCE RECEIVED / qwen3.6:35b responded to synthetic prompt`

Decision basis:

1. The user selected Option A.
2. This node only organizes user-provided local terminal screenshot evidence.
3. Codex did not run Ollama.
4. User local `ollama list` succeeded.
5. `qwen3.6:35b` appears in the user-provided local list.
6. `qwen3.6:35b` ID is `07d35212591f`.
7. `qwen3.6:35b` SIZE is `23 GB`.
8. The original 7 models still appear in the user-provided list.
9. User local lightweight synthetic prompt response validation completed once.
10. The response validation does not show missing model, service unavailable, response interruption, or CLI error.
11. The response validation did not connect to ZDoc.
12. The response validation did not access endpoints.
13. The response validation did not read or parse real KG.
14. The response validation did not trigger generation, export, or write-back.
15. The response validation is not formal trial use.
16. The response output contains a longer thinking / self-check / mixed Chinese-English process text and is recorded as an output format observation.

This decision is not a GO for real use or trial use.

This decision is not a GO for 1-2 person controlled trial use.

This decision is not a GO for 2-5 person limited concurrent trial use.

This decision does not authorize running the ZDoc service.

This decision does not authorize endpoint access.

This decision does not authorize reading real KG.

This decision does not authorize generation, export, or write-back.

## 8. Next Node Suggestion

Suggested next node:

`KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE: stability evidence review and preview-only readiness gate docs-only`

The next node may only review stability evidence, record the output format observation, and judge whether the prerequisites are satisfied to return to a ZDoc preview-only validation path.

The next node must not directly enter real use or trial use.

The next node must not directly enter 1-2 person controlled trial use.

The next node must not directly enter 2-5 person limited concurrent trial use.

The next node must not run the ZDoc service.

The next node must not access endpoints.

The next node must not read real KG.

The next node must not trigger generation, export, or write-back.

This node does not enter the next node.

## 9. Final Status

- KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE completed as docs-only evidence intake.
- User selected Option A.
- This node only organized user-provided local terminal screenshot evidence.
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
- `qwen3.6:35b` appears in the user-provided local list.
- `qwen3.6:35b` ID is `07d35212591f`.
- `qwen3.6:35b` SIZE is `23 GB`.
- The original 7 models still appear in the user-provided list.
- User local lightweight synthetic prompt response validation completed once.
- The response validation does not show missing model, service unavailable, response interruption, or CLI error.
- The response validation did not connect to ZDoc.
- The response validation did not access endpoints.
- The response validation did not read or parse real KG.
- The response validation did not trigger generation, export, or write-back.
- The response validation is not formal trial use.
- Output format observation: `OUTPUT FORMAT OBSERVATION / verbose reasoning-like trace visible before final answer`.
- Current decision: `USER-MEDIATED LIGHT STABILITY EVIDENCE RECEIVED / qwen3.6:35b responded to synthetic prompt`
- Next node suggestion: `KG-RUNTIME-165-STABILITY-EVIDENCE-REVIEW-AND-PREVIEW-ONLY-READINESS-GATE: stability evidence review and preview-only readiness gate docs-only`
- Real use or trial use was not entered.
- 1-2 person controlled trial use was not entered.
- 2-5 person limited concurrent trial use was not entered.
- The next node was not entered.

KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE stops here and waits for human review.
