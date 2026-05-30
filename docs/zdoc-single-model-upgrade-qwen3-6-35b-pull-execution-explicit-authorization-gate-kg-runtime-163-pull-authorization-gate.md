# ZDoc Single-Model Upgrade Qwen3.6 35B Pull Execution Explicit Authorization Gate - KG-RUNTIME-163-PULL-AUTHORIZATION-GATE

## 1. Scope

KG-RUNTIME-163-PULL-AUTHORIZATION-GATE is a docs-only explicit authorization gate for a possible later single-model pull execution of:

`qwen3.6:35b`

This node forms the authorization threshold only. It is not a pull execution node, not a model upgrade node, not a stability verification node, and not a real-use or trial-use node.

This node explicitly:

- Does not run Ollama.
- Does not execute `ollama serve`.
- Does not execute `ollama list`.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute `ollama run`.
- Does not execute `ollama rm`.
- Does not execute any other Ollama command.
- Does not upgrade, pull, delete, or replace any model.
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

KG-RUNTIME-163-SERVICE-CHECK-INTAKE completed and passed.

The service-check intake established the following state:

- User completed Option A: `user-mediated service startup and inventory retry`.
- The Ollama server was started manually by the user.
- The user manually executed `ollama list`.
- The user-provided `ollama list` output successfully returned a pre-upgrade inventory.
- Pre-upgrade inventory is available.
- The prior service-not-running and pre-upgrade-inventory-unavailable blockers are closed by user manual action.

This node starts from that user-mediated inventory intake result and does not convert it into pull authorization.

## 3. Pre-Upgrade Inventory

The user-provided successful `ollama list` inventory contains 7 models:

| # | Model name | ID | Size |
|---|---|---|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `fc9e251df737` | `84 GB` |
| 2 | `qwen3-coder:30b` | `06c1097efce0` | `18 GB` |
| 3 | `deepseek-r1:32b` | `edba8017331d` | `19 GB` |
| 4 | `qwen3:30b` | `ad815644918f` | `18 GB` |
| 5 | `qwen3:14b` | `bddb181c33f2` | `9.3 GB` |
| 6 | `qwen3:8b` | `500a1f067a9f` | `5.2 GB` |
| 7 | `qwen3:0.6b` | `7df6b6e09427` | `522 MB` |

Inventory conclusion:

- The local pre-upgrade inventory contains 7 recorded models.
- The current inventory does not show `qwen3.6:35b`.
- No installed model entry named `qwen3.6:35b` appears in the user-provided list.

## 4. Candidate And Download Size Status

The single-model upgrade candidate remains:

`qwen3.6:35b`

Candidate status:

- `qwen3.6:35b` remains the only single-model upgrade candidate.
- `qwen3.6:35b` is currently not installed according to the user-provided pre-upgrade inventory.
- Prior official-source evidence recorded the `qwen3.6:35b` download size as `24GB`.
- The `24GB` value is inherited from the controller-mediated official-source evidence intake recorded in KG-RUNTIME-161 and preserved by KG-RUNTIME-162 and KG-RUNTIME-163-SERVICE-CHECK-INTAKE.
- This node did not recheck the download size online.
- This node did not run network verification.

## 5. Pull Authorization Gate

`ollama pull qwen3.6:35b` remains not authorized and not executed.

This node forms the explicit authorization gate for a later pull execution node only. It must not be interpreted as pull authorization.

The following remain true:

- Pull execution has not been authorized.
- Pull execution has not started.
- `ollama pull qwen3.6:35b` was not executed.
- No Ollama command was executed.
- No model was pulled, upgraded, deleted, or replaced.
- No model file was downloaded.
- The `latest` pointer was not modified.
- The upgrade execution state remains `NO-GO FOR PULL EXECUTION / pending explicit user authorization`.

## 6. Future User Authorization Template

Only if the user later explicitly authorizes the following scope may a later pull execution node begin.

Recommended future authorization wording:

"我明确授权 KG-RUNTIME-163-PULL-EXECUTION 执行 `qwen3.6:35b` 单模型拉取。授权范围仅限：读取前序目标 docs、确认 git 状态、记录 pull 前 `ollama list`、执行 `ollama pull qwen3.6:35b`、记录 pull 后 `ollama list`、生成 docs-only pull 执行记录、commit、push、创建远端 tag。禁止 `ollama run`、禁止 `ollama rm`、禁止 `ollama serve`、禁止删除或替换其他模型、禁止修改 latest 指向、禁止运行 ZDoc 服务、禁止访问 endpoint、禁止读取真实 KG、禁止解析真实 KG JSON、禁止触发 generation/export/write-back、禁止进入稳定性验证或试用。"

Template status:

- The wording above is a future user authorization template only.
- This node must not treat the template as already authorized.
- This node must not treat authorization-gate formation as pull authorization.
- A later node may proceed only after the user explicitly grants that authorization.

## 7. Explicit Prohibitions Preserved

After this node, the following prohibitions remain preserved:

- Do not run Ollama.
- Do not execute `ollama serve`.
- Do not execute `ollama list`.
- Do not execute `ollama pull qwen3.6:35b`.
- Do not execute `ollama run`.
- Do not execute `ollama rm`.
- Do not execute any other Ollama command.
- Do not upgrade, pull, delete, or replace models.
- Do not download model files.
- Do not modify the `latest` pointer.
- Do not run the ZDoc service.
- Do not access endpoints.
- Do not read real KG.
- Do not read real KG file body content.
- Do not parse real KG JSON.
- Do not trigger generation, export, or write-back.
- Do not write `output`, `job`, or `export`.
- Do not enter KG-RUNTIME-164.
- Do not enter stability verification.
- Do not enter real use or trial use.

## 8. Current Decision

`Current decision: NO-GO FOR PULL EXECUTION / pending explicit user authorization`

Decision basis:

1. KG-RUNTIME-163-SERVICE-CHECK-INTAKE completed and passed.
2. User completed Option A: `user-mediated service startup and inventory retry`.
3. Pre-upgrade inventory is available.
4. The user-provided inventory contains 7 models.
5. The current inventory does not show `qwen3.6:35b`.
6. `qwen3.6:35b` remains the only single-model upgrade candidate.
7. Prior official-source evidence records the download size as `24GB`.
8. This node did not recheck the `24GB` download size online.
9. This node did not run Ollama.
10. `ollama pull qwen3.6:35b` remains not authorized and not executed.

This is not a GO for pull execution.

## 9. Next Recommended Node

Next recommended node:

`KG-RUNTIME-163-PULL-EXECUTION: command-limited single-model qwen3.6:35b pull execution after explicit user authorization`

Next-node constraints:

- The next node may only execute after explicit user authorization.
- The next node must be limited to the user-authorized single-model pull scope for `qwen3.6:35b`.
- The next node must not execute `ollama run`.
- The next node must not execute `ollama rm`.
- The next node must not execute `ollama serve`.
- The next node must not delete or replace other models.
- The next node must not modify the `latest` pointer.
- The next node must not run the ZDoc service.
- The next node must not access endpoints.
- The next node must not read real KG.
- The next node must not parse KG JSON.
- The next node must not trigger generation, export, or write-back.
- The next node must not enter KG-RUNTIME-164.
- The next node must not enter stability verification.
- The next node must not enter real use or trial use.

This node does not enter the next node.

## 10. Final Status

- KG-RUNTIME-163-PULL-AUTHORIZATION-GATE completed as a docs-only explicit authorization gate.
- KG-RUNTIME-163-SERVICE-CHECK-INTAKE completed and passed.
- User completed Option A.
- Pre-upgrade inventory is available.
- The user-provided local inventory contains 7 models.
- `qwen3.6:35b` is not present in the current local inventory.
- `qwen3.6:35b` remains the only single-model upgrade candidate.
- Official-source download size evidence remains `24GB`.
- This node did not recheck the download size online.
- This node did not run Ollama.
- This node did not execute `ollama serve`.
- This node did not execute `ollama list`.
- This node did not execute `ollama pull qwen3.6:35b`.
- This node did not execute `ollama run`.
- This node did not execute `ollama rm`.
- This node did not execute any other Ollama command.
- This node did not upgrade, pull, delete, or replace models.
- This node did not download model files.
- This node did not modify the `latest` pointer.
- This node did not run the ZDoc service.
- This node did not access endpoints.
- This node did not read real KG.
- This node did not parse KG JSON.
- This node did not trigger generation, export, or write-back.
- This node did not write `output`, `job`, or `export`.
- Future user authorization wording is recorded only as a template.
- The future template is not treated as already authorized.
- Current decision: `NO-GO FOR PULL EXECUTION / pending explicit user authorization`
- KG-RUNTIME-164 was not entered.
- Stability verification was not entered.
- Trial / real use was not entered.
- Next recommended node: `KG-RUNTIME-163-PULL-EXECUTION: command-limited single-model qwen3.6:35b pull execution after explicit user authorization`

KG-RUNTIME-163-PULL-AUTHORIZATION-GATE stops here and waits for human review. It does not enter the next node, KG-RUNTIME-164, stability verification, trial use, or real use.
