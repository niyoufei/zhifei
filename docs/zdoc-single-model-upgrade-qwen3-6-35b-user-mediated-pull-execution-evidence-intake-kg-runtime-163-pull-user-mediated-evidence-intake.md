# ZDoc Single-Model Upgrade Qwen3.6 35B User-Mediated Pull Execution Evidence Intake - KG-RUNTIME-163-PULL-USER-MEDIATED-EXECUTION-EVIDENCE-INTAKE

## 1. Scope

KG-RUNTIME-163-PULL-USER-MEDIATED-EXECUTION-EVIDENCE-INTAKE is a docs-only evidence intake node for the user-mediated `qwen3.6:35b` pull path.

This node only organizes the user-provided local terminal screenshot evidence after the user selected Option A and manually completed:

```bash
ollama list
ollama pull qwen3.6:35b
ollama list
```

Codex did not run Ollama in this node.

This node is not an Ollama command node, not a model pull node, not a model replacement node, not KG-RUNTIME-164, not a stability verification node, and not a real-use or trial-use node.

This node explicitly:

- Does not run Ollama.
- Does not execute `ollama list`.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute `ollama run`.
- Does not execute `ollama rm`.
- Does not execute `ollama serve`.
- Does not execute any other Ollama command.
- Does not pull any model.
- Does not delete, replace, or overwrite any model.
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
- Does not enter KG-RUNTIME-164.
- Does not enter stability verification.
- Does not enter real use or trial use.

## 2. Baseline

This node starts from:

- Starting HEAD: `c788d328cb748b6961bd9723379dec25673d04e6`
- Starting remote tag: `v0.1.551-zdoc-single-model-upgrade-qwen3-6-35b-pull-retry-authorization-gate`
- Candidate: `qwen3.6:35b`
- Prior recommended path: `Option A / user-mediated pull execution evidence intake`
- Prior blocked reason: `PULL PRE-LIST BLOCKED / localhost Ollama endpoint access not permitted`
- Prior official-source download size evidence: `24GB`

The following prior docs were read as the evidence chain for this docs-only intake:

1. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-retry-path-authorization-gate-kg-runtime-163-pull-retry-authorization-gate.md`
2. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-pre-list-blocked-audit-kg-runtime-163-pull-blocked-audit.md`
3. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-execution-explicit-authorization-gate-kg-runtime-163-pull-authorization-gate.md`
4. `docs/zdoc-single-model-upgrade-user-mediated-ollama-service-startup-and-pre-upgrade-inventory-intake-kg-runtime-163-service-check-intake.md`
5. `docs/zdoc-single-model-upgrade-controlled-ollama-service-startup-and-inventory-retry-authorization-gate-kg-runtime-163-service-gate.md`
6. `docs/zdoc-single-model-upgrade-execution-authorization-gate-after-evidence-closure-kg-runtime-162.md`

## 3. User-Mediated Option A Evidence Received

The user selected Option A.

The user-provided screenshot evidence shows that the user manually executed the following local terminal sequence:

```bash
ollama list
ollama pull qwen3.6:35b
ollama list
```

Codex did not execute any of those commands in this node.

## 4. Pull-Precondition Inventory Evidence

The user-provided pull-before `ollama list` screenshot shows that the local pre-pull inventory command succeeded.

The pre-pull inventory contained the following 7 models:

| # | Model name | ID | Size | Modified |
|---|---|---|---|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `fc9e251df737` | `84 GB` | `5 weeks ago` |
| 2 | `qwen3-coder:30b` | `06c1097efce0` | `18 GB` | `5 weeks ago` |
| 3 | `deepseek-r1:32b` | `edba8017331d` | `19 GB` | `5 weeks ago` |
| 4 | `qwen3:30b` | `ad815644918f` | `18 GB` | `5 weeks ago` |
| 5 | `qwen3:14b` | `bddb181c33f2` | `9.3 GB` | `5 weeks ago` |
| 6 | `qwen3:8b` | `500a1f067a9f` | `5.2 GB` | `5 weeks ago` |
| 7 | `qwen3:0.6b` | `7df6b6e09427` | `522 MB` | `5 weeks ago` |

Pull-precondition inventory conclusion:

- User local pull-before `ollama list` succeeded.
- The original 7 models were visible before the user-mediated pull.
- Codex did not run `ollama list`.

## 5. User-Mediated Pull Evidence

The user-provided screenshot shows that the user manually executed:

```bash
ollama pull qwen3.6:35b
```

The screenshot shows the pull process reached:

```text
pulling manifest
pulling 55ee307a2982: 100%    23 GB
pulling 5f3a3c817e78: 100%    11 KB
pulling 86eff881e8d2: 100%    94 B
pulling 5d1c86a949f7: 100%    462 B
verifying sha256 digest
writing manifest
success
```

Pull execution evidence conclusion:

- User local `ollama pull qwen3.6:35b` displayed `success`.
- The successful pull evidence was user-mediated.
- Codex did not execute `ollama pull qwen3.6:35b`.
- Codex did not pull, delete, replace, or overwrite any model.
- Codex did not modify the `latest` pointer.

## 6. Post-Pull Inventory Evidence

The user-provided pull-after `ollama list` screenshot shows that the local post-pull inventory command succeeded.

The post-pull inventory includes the new model entry:

| Model name | ID | Size | Modified |
|---|---|---|---|
| `qwen3.6:35b` | `07d35212591f` | `23 GB` | `13 seconds ago` |

The post-pull inventory also still includes the original 7 models:

| # | Model name | ID | Size | Modified |
|---|---|---|---|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `fc9e251df737` | `84 GB` | `5 weeks ago` |
| 2 | `qwen3-coder:30b` | `06c1097efce0` | `18 GB` | `5 weeks ago` |
| 3 | `deepseek-r1:32b` | `edba8017331d` | `19 GB` | `5 weeks ago` |
| 4 | `qwen3:30b` | `ad815644918f` | `18 GB` | `5 weeks ago` |
| 5 | `qwen3:14b` | `bddb181c33f2` | `9.3 GB` | `5 weeks ago` |
| 6 | `qwen3:8b` | `500a1f067a9f` | `5.2 GB` | `5 weeks ago` |
| 7 | `qwen3:0.6b` | `7df6b6e09427` | `522 MB` | `5 weeks ago` |

Post-pull inventory conclusion:

- User local pull-after `ollama list` succeeded.
- Pull-after inventory shows `qwen3.6:35b`.
- Pull-after inventory shows `qwen3.6:35b` ID `07d35212591f`.
- Pull-after inventory shows `qwen3.6:35b` SIZE `23 GB`.
- Pull-after inventory shows `qwen3.6:35b` MODIFIED `13 seconds ago`.
- The original 7 models still appear in the post-pull inventory.
- No evidence shows deletion, replacement, or overwrite of any other model.
- Codex did not run `ollama list`.

## 7. Size Display Note

Prior official-source evidence recorded the `qwen3.6:35b` download size as `24GB`.

The user-provided local Ollama inventory shows `qwen3.6:35b` SIZE as `23 GB`.

This difference is recorded only as a display-unit or display-rounding difference between the prior official-source evidence and the local Ollama list display. It is not handled as an abnormal condition in this docs-only intake node.

## 8. Current Decision

Current decision:

`USER-MEDIATED PULL EVIDENCE RECEIVED / qwen3.6:35b appears installed in user-provided ollama list`

Decision basis:

1. The user selected Option A.
2. This node only organizes user-provided local terminal screenshot evidence.
3. Codex did not run Ollama.
4. User local pull-before `ollama list` succeeded.
5. User local `ollama pull qwen3.6:35b` displayed `success`.
6. User local pull-after `ollama list` succeeded.
7. Pull-after inventory shows `qwen3.6:35b` with ID `07d35212591f`, SIZE `23 GB`, and MODIFIED `13 seconds ago`.
8. The original 7 models still appear in the pull-after inventory.
9. No evidence shows deletion, replacement, or overwrite of any other model.
10. The `24GB` official-source evidence and `23 GB` local Ollama list display difference is recorded only as a display difference.

This decision is not a GO for KG-RUNTIME-164.

This decision is not a GO for stability verification.

This decision is not a GO for real use or trial use.

## 9. Next Node Suggestion

Suggested next node:

`KG-RUNTIME-164-STABILITY-AUTHORIZATION-GATE: post-upgrade stability validation authorization gate docs-only`

The next node suggestion is only a suggestion.

The following remain true:

- This node does not enter KG-RUNTIME-164.
- Stability verification has not been authorized.
- Stability verification has not started.
- Real use has not started.
- Trial use has not started.
- The next step can only be a stability validation authorization gate docs-only node.

## 10. Final Status

- KG-RUNTIME-163-PULL-USER-MEDIATED-EXECUTION-EVIDENCE-INTAKE completed as docs-only evidence intake.
- User selected Option A.
- This node only organized user-provided local terminal screenshot evidence.
- Codex did not run Ollama.
- Codex did not execute `ollama list`.
- Codex did not execute `ollama pull qwen3.6:35b`.
- Codex did not execute `ollama run`.
- Codex did not execute `ollama rm`.
- Codex did not execute `ollama serve`.
- Codex did not execute any other Ollama command.
- Codex did not pull any model.
- Codex did not delete, replace, or overwrite any model.
- Codex did not modify the `latest` pointer.
- Codex did not run the ZDoc service.
- Codex did not access endpoints.
- Codex did not read real KG.
- Codex did not read real KG file body content.
- Codex did not parse real KG JSON.
- Codex did not trigger generation, export, or write-back.
- Codex did not write `output`, `job`, or `export`.
- User local pull-before `ollama list` succeeded.
- User local `ollama pull qwen3.6:35b` displayed `success`.
- User local pull-after `ollama list` succeeded.
- Pull-after inventory shows `qwen3.6:35b`.
- Pull-after inventory shows `qwen3.6:35b` ID `07d35212591f`.
- Pull-after inventory shows `qwen3.6:35b` SIZE `23 GB`.
- Pull-after inventory shows `qwen3.6:35b` MODIFIED `13 seconds ago`.
- The original 7 models still appear in the pull-after inventory.
- No evidence shows deletion, replacement, or overwrite of any other model.
- The prior official-source `24GB` evidence and the local Ollama `23 GB` inventory display difference is recorded only as a display difference.
- Current decision: `USER-MEDIATED PULL EVIDENCE RECEIVED / qwen3.6:35b appears installed in user-provided ollama list`
- Next node suggestion: `KG-RUNTIME-164-STABILITY-AUTHORIZATION-GATE: post-upgrade stability validation authorization gate docs-only`
- KG-RUNTIME-164 was not entered.
- Stability verification was not entered.
- Real use was not entered.
- Trial use was not entered.

KG-RUNTIME-163-PULL-USER-MEDIATED-EXECUTION-EVIDENCE-INTAKE stops here and waits for human review.
