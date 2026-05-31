# ZDoc Qwen3.6 35B Post-Upgrade Stability Validation Authorization Gate - KG-RUNTIME-164

## 1. Scope

KG-RUNTIME-164-STABILITY-AUTHORIZATION-GATE is a docs-only authorization gate for post-upgrade stability validation of:

`qwen3.6:35b`

This node only forms the authorization threshold for possible later stability validation. It is not a stability validation execution node, not an Ollama command node, not a ZDoc service node, not an endpoint node, not a KG read node, and not a real-use or trial-use node.

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
- Does not enter stability validation execution.
- Does not enter real use or trial use.

## 2. Baseline

This node starts from:

- Starting HEAD: `6cf60929784c8ae72379df12ca3e6f9d033d6094`
- Starting remote tag: `v0.1.552-zdoc-single-model-upgrade-qwen3-6-35b-user-mediated-pull-evidence-intake`
- Candidate: `qwen3.6:35b`
- Prior completed node: `KG-RUNTIME-163-PULL-USER-MEDIATED-EXECUTION-EVIDENCE-INTAKE`
- Prior recommended next node: `KG-RUNTIME-164-STABILITY-AUTHORIZATION-GATE: post-upgrade stability validation authorization gate docs-only`

The following prior docs were read for this docs-only authorization gate:

1. `docs/zdoc-single-model-upgrade-qwen3-6-35b-user-mediated-pull-execution-evidence-intake-kg-runtime-163-pull-user-mediated-evidence-intake.md`
2. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-retry-path-authorization-gate-kg-runtime-163-pull-retry-authorization-gate.md`
3. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-pre-list-blocked-audit-kg-runtime-163-pull-blocked-audit.md`
4. `docs/zdoc-single-model-upgrade-qwen3-6-35b-pull-execution-explicit-authorization-gate-kg-runtime-163-pull-authorization-gate.md`
5. `docs/zdoc-single-model-upgrade-user-mediated-ollama-service-startup-and-pre-upgrade-inventory-intake-kg-runtime-163-service-check-intake.md`
6. `docs/zdoc-single-model-upgrade-execution-authorization-gate-after-evidence-closure-kg-runtime-162.md`

## 3. Prior Pull Evidence State

`KG-RUNTIME-163-PULL-USER-MEDIATED-EXECUTION-EVIDENCE-INTAKE` has completed and passed.

The user selected Option A and manually completed the `qwen3.6:35b` pull on the local machine. The user-provided screenshot evidence shows:

- The user manually ran `ollama pull qwen3.6:35b`.
- The pull output reached `success`.
- The user pull-after `ollama list` output includes `qwen3.6:35b`.

The post-pull inventory evidence records the new model entry:

| Model name | ID | SIZE |
|---|---|---|
| `qwen3.6:35b` | `07d35212591f` | `23 GB` |

The post-pull inventory evidence also shows the original 7 models still in the list:

| # | Model name | ID | SIZE |
|---|---|---|---|
| 1 | `qwen3-next:80b-a3b-instruct-q8_0` | `fc9e251df737` | `84 GB` |
| 2 | `qwen3-coder:30b` | `06c1097efce0` | `18 GB` |
| 3 | `deepseek-r1:32b` | `edba8017331d` | `19 GB` |
| 4 | `qwen3:30b` | `ad815644918f` | `18 GB` |
| 5 | `qwen3:14b` | `bddb181c33f2` | `9.3 GB` |
| 6 | `qwen3:8b` | `500a1f067a9f` | `5.2 GB` |
| 7 | `qwen3:0.6b` | `7df6b6e09427` | `522 MB` |

No evidence shows deletion, replacement, or overwrite of any other model.

No evidence shows modification of the `latest` pointer.

Prior official-source evidence recorded the `qwen3.6:35b` download size as `24GB`. The local user-provided Ollama inventory shows `23 GB`. This difference is recorded only as a display-unit or display-rounding difference between the prior official-source evidence and the local Ollama list display. It is not treated as an abnormal condition in this docs-only authorization gate.

Current installed-state wording is limited to:

`qwen3.6:35b appears installed based on user-provided evidence`

## 4. Current Non-Execution Facts

This node did not run Ollama.

This node did not execute:

- `ollama list`
- `ollama run`
- `ollama pull`
- `ollama rm`
- `ollama serve`
- Any other Ollama command

This node also did not:

- Delete, replace, or overwrite any model.
- Modify the `latest` pointer.
- Run the ZDoc service.
- Access endpoints.
- Read real KG.
- Read real KG file body content.
- Parse real KG JSON.
- Trigger generation, export, or write-back.
- Write `output`, `job`, or `export`.
- Enter stability validation execution.
- Enter real use or trial use.

Stability validation has not been authorized.

Stability validation has not started.

Real use has not started.

Trial use has not started.

## 5. Future Stability Validation Paths

The following paths are future options only. This node does not execute either path and does not treat either path as already authorized.

### Option A: user-mediated stability validation evidence intake, recommended

The user manually executes later stability validation commands in the local terminal and pastes the complete output back to the controller. Codex may then only perform docs-only evidence intake from the user-provided output.

Recommended validation scope is limited to:

1. `ollama list` to recheck whether `qwen3.6:35b` is still present in the local list.
2. One lightweight response validation using a minimal synthetic prompt that is not project data, not real KG, and not business data.
3. Record whether the model returns normally.
4. Record whether there is any obvious error, missing-model failure, service unavailable state, response interruption, or similar issue.

This validation is not formal trial use. It must not connect to ZDoc, access endpoints, read real KG, trigger generation, trigger export, or trigger write-back.

### Option B: Codex command-limited stability validation after explicit authorization, fallback

Only after later explicit user authorization may Codex attempt extremely limited stability validation commands.

Option B has a material risk of failing again because prior Codex access to the local `127.0.0.1:11434` Ollama endpoint failed with:

```text
operation not permitted
```

Even if Option B is later explicitly selected, the validation scope must remain limited to non-project, non-real-KG, non-business synthetic input and must not connect to ZDoc, access endpoints, read real KG, trigger generation, trigger export, or trigger write-back.

## 6. Current Recommendation And Decision

Recommended path:

`Option A / user-mediated stability validation evidence intake`

Current restrictions:

- Do not directly execute stability validation.
- Do not execute `ollama list`.
- Do not execute `ollama run qwen3.6:35b`.
- Do not run the ZDoc service.
- Do not access endpoints.
- Do not read or parse real KG.
- Do not trigger generation, export, or write-back.
- Do not enter real use or trial use.

Current decision:

`NO-GO FOR STABILITY VALIDATION EXECUTION / pending explicit user authorization`

This decision means stability validation has not been selected, stability validation execution has not been authorized, and real use or trial use remains stopped.

## 7. Future User Authorization Templates

The following templates are future authorization wording only. They are not authorization granted by this node.

### Option A authorization template

"我选择 Option A，采用 user-mediated stability validation evidence intake。我将在本机终端手动执行 `ollama list`，并使用非项目、非真实 KG、非业务数据的极简合成提示词对 `qwen3.6:35b` 做 1 次轻量响应验证，然后将完整输出粘贴回来。Codex 不得运行 Ollama，只能在后续节点整理我提供的输出证据。"

### Option B authorization template

"我选择 Option B，授权 Codex 进行 command-limited stability validation。授权范围仅限确认 git 状态、读取前序目标 docs、执行 `ollama list`、对 `qwen3.6:35b` 使用非项目、非真实 KG、非业务数据的极简合成提示词做 1 次轻量响应验证，并生成 docs-only 稳定性验证记录。禁止读取真实 KG，禁止运行 ZDoc 服务，禁止访问 endpoint，禁止触发 generation/export/write-back，禁止写 output/job/export，禁止进入真实使用/试用阶段。"

Template status:

- The Option A template is not treated as already authorized.
- The Option B template is not treated as already authorized.
- This node must not treat authorization-template recording as stability validation authorization.
- A later node may proceed only after the user explicitly chooses a stability validation path.

## 8. Next Node Suggestions

If the user chooses Option A, the suggested next node is:

`KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE: qwen3.6:35b user-mediated stability validation evidence intake docs-only`

If the user chooses Option B, the suggested next node is:

`KG-RUNTIME-164-STABILITY-COMMAND-LIMITED-VALIDATION: qwen3.6:35b command-limited stability validation after explicit authorization`

This node does not enter either next node.

This node does not enter stability validation execution, real use, or trial use.

## 9. Final Status

- KG-RUNTIME-164-STABILITY-AUTHORIZATION-GATE completed as a docs-only authorization gate.
- KG-RUNTIME-163-PULL-USER-MEDIATED-EXECUTION-EVIDENCE-INTAKE completed and passed.
- User selected Option A for the prior pull execution evidence intake path.
- User manually completed `ollama pull qwen3.6:35b`.
- User screenshot evidence shows `ollama pull qwen3.6:35b` reached `success`.
- User pull-after `ollama list` evidence shows `qwen3.6:35b`.
- User pull-after `ollama list` evidence shows ID `07d35212591f`.
- User pull-after `ollama list` evidence shows SIZE `23 GB`.
- The original 7 models still appear in the user pull-after list.
- No evidence shows deletion, replacement, or overwrite of other models.
- No evidence shows modification of the `latest` pointer.
- The prior official-source `24GB` evidence and local Ollama `23 GB` inventory display difference is recorded only as a display difference.
- Current installed-state wording: `qwen3.6:35b appears installed based on user-provided evidence`.
- This node did not run Ollama.
- This node did not execute `ollama list`.
- This node did not execute `ollama run`.
- This node did not execute `ollama pull`.
- This node did not execute `ollama rm`.
- This node did not execute `ollama serve`.
- This node did not execute any other Ollama command.
- This node did not delete, replace, or overwrite any model.
- This node did not modify the `latest` pointer.
- This node did not run the ZDoc service.
- This node did not access endpoints.
- This node did not read real KG.
- This node did not parse KG JSON.
- This node did not trigger generation, export, or write-back.
- This node did not write `output`, `job`, or `export`.
- Stability validation has not been authorized.
- Stability validation has not started.
- Real use has not started.
- Trial use has not started.
- Option A is recorded as the recommended future path.
- Option B is recorded as the fallback future path.
- Future user authorization templates are recorded only as templates.
- The future authorization templates are not treated as already authorized.
- Current decision: `NO-GO FOR STABILITY VALIDATION EXECUTION / pending explicit user authorization`
- Next node suggestion for Option A: `KG-RUNTIME-164-STABILITY-USER-MEDIATED-EVIDENCE-INTAKE: qwen3.6:35b user-mediated stability validation evidence intake docs-only`
- Next node suggestion for Option B: `KG-RUNTIME-164-STABILITY-COMMAND-LIMITED-VALIDATION: qwen3.6:35b command-limited stability validation after explicit authorization`
- This node does not enter either next node.

KG-RUNTIME-164-STABILITY-AUTHORIZATION-GATE stops here and waits for human review.
