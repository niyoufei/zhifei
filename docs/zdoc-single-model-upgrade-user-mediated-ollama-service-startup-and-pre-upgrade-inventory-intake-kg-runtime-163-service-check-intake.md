# ZDoc Single-Model Upgrade User-Mediated Ollama Service Startup And Pre-Upgrade Inventory Intake - KG-RUNTIME-163-SERVICE-CHECK-INTAKE

## 1. Scope

KG-RUNTIME-163-SERVICE-CHECK-INTAKE is a docs-only intake node for the ZDoc single-model upgrade chain.

This node records the user's manual completion of Option A from KG-RUNTIME-163-SERVICE-GATE:

`Option A / user-mediated service startup and inventory retry`

This node only archives the user-provided successful Ollama service startup and `ollama list` inventory evidence. It is not a Codex-side Ollama command node, not a model pull node, not a model upgrade node, not a stability verification node, and not a real-use or trial-use node.

This node explicitly:

- Does not run Ollama.
- Does not execute `ollama serve`.
- Does not execute `ollama list`.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute `ollama run`.
- Does not execute `ollama rm`.
- Does not execute any other Ollama command.
- Does not upgrade, pull, delete, or replace models.
- Does not download model files.
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

KG-RUNTIME-163-SERVICE-GATE established the controlled service startup and inventory retry authorization boundary.

KG-RUNTIME-163-SERVICE-CHECK-INTAKE starts from the following user-stated repository baseline:

- Starting HEAD: `2519cb171dd5fec0ded3c82fae23aad9eb1b8101`
- Starting remote tag: `v0.1.547-zdoc-single-model-upgrade-ollama-service-startup-inventory-retry-gate`
- Candidate: `qwen3.6:35b`
- Official-source download size evidence retained from prior evidence closure: `24GB`
- Previous blocker: `OLLAMA SERVER NOT RUNNING / pre-upgrade inventory unavailable`
- Previous gate decision: `WAITING FOR USER ACTION OR EXPLICIT SERVICE-CHECK AUTHORIZATION`

KG-RUNTIME-163-SERVICE-CHECK-INTAKE records that the user selected and completed Option A. It does not convert the successful inventory intake into pull authorization.

## 3. User-Mediated Option A Completion

The user reported that they manually started the local Ollama server and manually executed:

```bash
ollama list
```

Codex did not execute that command in this node.

The user-provided screenshot shows that `ollama list` successfully returned an inventory table. Therefore:

- User completed Option A: `user-mediated service startup and inventory retry`.
- The Ollama server not running blocker is closed by user manual action.
- The pre-upgrade inventory unavailable blocker is closed by user manual `ollama list` output.
- Pre-upgrade inventory is now available for review.
- KG-RUNTIME-163-SERVICE-GATE has passed for the user-mediated service startup and inventory retry path.

## 4. Pre-Upgrade Local Model Inventory

The user-provided successful `ollama list` output is recorded as follows:

```text
NAME                                      ID            SIZE    MODIFIED
qwen3-next:80b-a3b-instruct-q8_0          fc9e251df737  84 GB   5 weeks ago
qwen3-coder:30b                           06c1097efce0  18 GB   5 weeks ago
deepseek-r1:32b                           edba8017331d  19 GB   5 weeks ago
qwen3:30b                                 ad815644918f  18 GB   5 weeks ago
qwen3:14b                                 bddb181c33f2  9.3 GB  5 weeks ago
qwen3:8b                                  500a1f067a9f  5.2 GB  5 weeks ago
qwen3:0.6b                                7df6b6e09427  522 MB  5 weeks ago
```

Structured pre-upgrade inventory:

| # | Model name | ID | Size | Modified |
|---|---|---|---|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `fc9e251df737` | `84 GB` | `5 weeks ago` |
| 2 | `qwen3-coder:30b` | `06c1097efce0` | `18 GB` | `5 weeks ago` |
| 3 | `deepseek-r1:32b` | `edba8017331d` | `19 GB` | `5 weeks ago` |
| 4 | `qwen3:30b` | `ad815644918f` | `18 GB` | `5 weeks ago` |
| 5 | `qwen3:14b` | `bddb181c33f2` | `9.3 GB` | `5 weeks ago` |
| 6 | `qwen3:8b` | `500a1f067a9f` | `5.2 GB` | `5 weeks ago` |
| 7 | `qwen3:0.6b` | `7df6b6e09427` | `522 MB` | `5 weeks ago` |

Inventory result:

- The current local pre-upgrade model inventory contains 7 models.
- `qwen3.6:35b` is not present in the current local inventory.
- No installed model entry named `qwen3.6:35b` appears in the user-provided list.

## 5. Candidate And Download Size Status

The single-model upgrade candidate remains:

`qwen3.6:35b`

Candidate status:

- `qwen3.6:35b` is still the only single-model upgrade candidate.
- `qwen3.6:35b` is currently not installed according to the user-provided pre-upgrade inventory.
- The download size remains the prior official-source evidence value: `24GB`.
- The `24GB` value is inherited from the controller-mediated official-source evidence intake recorded in KG-RUNTIME-161 and preserved by KG-RUNTIME-162.

This node does not reconfirm official sources, does not run network checks, and does not download the model.

## 6. Pull Authorization Status

`ollama pull qwen3.6:35b` remains not authorized and not executed.

This node records inventory readiness only. It does not authorize pull execution.

The following remain true:

- Model upgrade has not started.
- No model was pulled by Codex.
- No model was upgraded by Codex.
- No model was deleted or replaced by Codex.
- No model file was downloaded by Codex.
- `latest` was not modified by Codex.
- `ollama run` was not executed.
- `ollama rm` was not executed.
- No other Ollama command was executed by Codex.

## 7. Current Decision

`Current decision: NO-GO FOR PULL EXECUTION / pending explicit user authorization`

Decision basis:

1. The service startup blocker has been closed by user manual action.
2. The pre-upgrade inventory blocker has been closed by user manual `ollama list` output.
3. The installed model inventory is now available and recorded.
4. `qwen3.6:35b` is not currently installed.
5. `qwen3.6:35b` remains the only single-model upgrade candidate.
6. The candidate download size evidence remains `24GB`.
7. Pull execution still requires a later explicit user authorization gate.

This is not a GO for pull execution.

## 8. Next Recommended Node

Next recommended node:

`KG-RUNTIME-163-PULL-AUTHORIZATION-GATE: single-model qwen3.6:35b pull execution explicit authorization gate docs-only`

Next-node constraints:

- The next node may only form the explicit authorization gate for whether `ollama pull qwen3.6:35b` may be executed later.
- The next node must not directly execute `ollama pull qwen3.6:35b`.
- The next node must not execute `ollama run`.
- The next node must not execute `ollama rm`.
- The next node must not delete or replace other models.
- The next node must not modify the `latest` pointer.
- The next node must not run the ZDoc service.
- The next node must not access endpoints.
- The next node must not read real KG.
- The next node must not parse KG JSON.
- The next node must not trigger generation, export, or write-back.
- The next node must not write `output`, `job`, or `export`.
- The next node must not enter KG-RUNTIME-164.
- The next node must not enter stability verification.
- The next node must not enter real use or trial use.

KG-RUNTIME-163-SERVICE-CHECK-INTAKE stops here and does not enter KG-RUNTIME-163-PULL-AUTHORIZATION-GATE.

## 9. Explicit Prohibitions Preserved

After KG-RUNTIME-163-SERVICE-CHECK-INTAKE, the following prohibitions remain preserved:

- Do not execute `ollama pull qwen3.6:35b`.
- Do not execute `ollama run`.
- Do not execute `ollama rm`.
- Do not execute any other Ollama command.
- Do not delete or replace other models.
- Do not modify the `latest` pointer.
- Do not run the ZDoc service.
- Do not access endpoints.
- Do not read real KG.
- Do not read real KG file body content.
- Do not parse KG JSON.
- Do not trigger generation, export, or write-back.
- Do not write `output`, `job`, or `export`.
- Do not enter KG-RUNTIME-164.
- Do not enter stability verification.
- Do not enter real use or trial use.

## 10. Final Status

- KG-RUNTIME-163-SERVICE-CHECK-INTAKE completed as docs-only user-mediated inventory intake.
- KG-RUNTIME-163-SERVICE-GATE has passed.
- User selected and completed Option A.
- Ollama server not running blocker has been closed by user manual action.
- Pre-upgrade inventory unavailable blocker has been closed by user manual `ollama list` output.
- Pre-upgrade inventory is available.
- The current local pre-upgrade inventory contains 7 models.
- `qwen3.6:35b` is not present in the current local inventory.
- `qwen3.6:35b` remains the only single-model upgrade candidate.
- Official-source download size evidence remains `24GB`.
- `ollama pull qwen3.6:35b` remains not authorized and not executed.
- Model upgrade has not started.
- KG-RUNTIME-164 was not entered.
- Stability verification was not entered.
- Trial / real use was not entered.
- Current decision: `NO-GO FOR PULL EXECUTION / pending explicit user authorization`
- Next recommended node: `KG-RUNTIME-163-PULL-AUTHORIZATION-GATE: single-model qwen3.6:35b pull execution explicit authorization gate docs-only`

KG-RUNTIME-163-SERVICE-CHECK-INTAKE stops here and waits for human review. It does not enter the next node, KG-RUNTIME-164, stability verification, trial use, or real use.
