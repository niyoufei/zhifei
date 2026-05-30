# ZDoc Single-Model Upgrade Qwen3.6 35B Pull Retry Path Authorization Gate - KG-RUNTIME-163-PULL-RETRY-AUTHORIZATION-GATE

## 1. Scope

KG-RUNTIME-163-PULL-RETRY-AUTHORIZATION-GATE is a docs-only authorization gate for a possible later retry path after the blocked `qwen3.6:35b` pull-precondition attempt.

This node only forms the retry-path authorization threshold. It is not a pull retry node, not a pull execution node, not a model upgrade node, not a stability verification node, and not a real-use or trial-use node.

This node explicitly:

- Does not run Ollama.
- Does not execute `ollama serve`.
- Does not execute `ollama list`.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute `ollama run`.
- Does not execute `ollama rm`.
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

KG-RUNTIME-163-PULL-BLOCKED-AUDIT has completed and passed.

Current repository baseline for this node:

- Current HEAD: `c7a44ba66030ce85c5b06fb208df0440037be8f7`
- Starting remote tag: `v0.1.550-zdoc-single-model-upgrade-qwen3-6-35b-pull-pre-list-blocked-audit`
- Candidate: `qwen3.6:35b`
- Current blocked audit source: `KG-RUNTIME-163-PULL-BLOCKED-AUDIT`

This node starts from the blocked audit result and does not convert that result into retry authorization or pull execution authorization.

## 3. Current Blocked State

Current blocked reason:

`PULL PRE-LIST BLOCKED / localhost Ollama endpoint access not permitted`

The complete recorded failure output is:

```text
Error: Head "http://127.0.0.1:11434/": dial tcp 127.0.0.1:11434: connect: operation not permitted
```

Blocked state details:

- `ollama pull qwen3.6:35b` was not executed.
- The post-pull `ollama list` was not executed.
- Whether `qwen3.6:35b` is installed remains unconfirmed.
- Model upgrade has not started.
- KG-RUNTIME-164 was not entered.
- Stability verification was not entered.
- Real use was not entered.
- Trial use was not entered.

This blocked state must not be interpreted as pull execution, model upgrade, retry execution, stability validation, or trial readiness.

## 4. Retry Paths

The following retry paths are future options only. This node does not execute either path.

### Option A: user-mediated pull execution evidence intake, recommended

The user manually executes the following commands in the local machine terminal:

```bash
ollama list
ollama pull qwen3.6:35b
ollama list
```

The user then pastes the complete terminal output back to the controller. A later Codex node may only perform docs-only evidence intake from the user-provided output. Codex must not directly run Ollama under Option A.

Recommended reasons:

1. Codex currently cannot access the local `127.0.0.1:11434` endpoint.
2. The observed failure point is not model-source unavailability; it is Codex-side local endpoint permission restriction.
3. The user's local terminal has previously executed `ollama list` successfully.
4. The user-mediated path avoids repeatedly triggering sandbox or localhost permission blocking.

### Option B: Codex command-limited retry after explicit authorization, fallback

Only after later explicit user authorization may Codex attempt the following command-limited retry:

```bash
ollama list
ollama pull qwen3.6:35b
ollama list
```

Because the previous attempt already failed with `operation not permitted`, Option B has a material risk of failing again at the local endpoint permission boundary.

Even if Option B is later explicitly selected, the following remain prohibited:

- `ollama run`
- `ollama rm`
- `ollama serve`
- Deleting, replacing, or overwriting other models
- Modifying the `latest` pointer
- Running the ZDoc service
- Accessing endpoints
- Reading real KG
- Reading real KG file body content
- Parsing real KG JSON
- Triggering generation, export, or write-back
- Writing `output`, `job`, or `export`
- Entering KG-RUNTIME-164
- Entering stability verification
- Entering real use or trial use

## 5. Recommended Conclusion

Recommended path:

`Option A / user-mediated pull execution evidence intake`

Current retry restrictions:

- Do not directly retry `ollama list`.
- Do not execute `ollama pull qwen3.6:35b`.
- Do not execute any Ollama command.

Current decision:

`NO-GO FOR RETRY EXECUTION / pending explicit retry path authorization`

This decision means the retry path has not been selected, retry execution has not been authorized, and pull execution remains stopped.

## 6. Future User Authorization Templates

The following templates are future authorization wording only. They are not authorization granted by this node.

### Option A authorization template

"我选择 Option A，采用 user-mediated pull execution evidence intake。我将在本机终端手动执行 `ollama list`、`ollama pull qwen3.6:35b`、`ollama list`，并将完整输出粘贴回来。Codex 不得运行 Ollama，只能在后续节点整理我提供的输出证据。"

### Option B authorization template

"我选择 Option B，授权 Codex 进行 command-limited retry。授权范围仅限执行 `ollama list`、`ollama pull qwen3.6:35b`、`ollama list`，并生成 docs-only 执行记录。禁止 `ollama run`、`ollama rm`、`ollama serve`、删除或替换其他模型、修改 latest 指向、运行 ZDoc 服务、访问 endpoint、读取或解析真实 KG、触发 generation/export/write-back、进入 KG-RUNTIME-164、进入稳定性验证或试用。"

Template status:

- The Option A template is not treated as already authorized.
- The Option B template is not treated as already authorized.
- This node must not treat authorization-template recording as retry execution authorization.
- A later node may proceed only after the user explicitly chooses a retry path.

## 7. Explicit Prohibitions Preserved

After this node, the following remain prohibited:

1. Do not run Ollama.
2. Do not execute `ollama list`.
3. Do not execute `ollama pull qwen3.6:35b`.
4. Do not execute `ollama run`.
5. Do not execute `ollama rm`.
6. Do not execute `ollama serve`.
7. Do not execute any other Ollama command.
8. Do not pull any model.
9. Do not delete, replace, or overwrite other models.
10. Do not modify the `latest` pointer.
11. Do not run the ZDoc service.
12. Do not access endpoints.
13. Do not read real KG file body content.
14. Do not parse real KG JSON.
15. Do not trigger generation.
16. Do not trigger export.
17. Do not trigger write-back.
18. Do not write `output`, `job`, or `export`.
19. Do not perform another directory scan.
20. Do not modify adapter, route, helper, or `main.py`.
21. Do not modify frontend, tests, config, or JSON.
22. Do not connect RAG, registry, or CI.
23. Do not add `.pyc` or `__pycache__`.
24. Do not enter KG-RUNTIME-164.
25. Do not enter stability verification.
26. Do not enter real use or trial use.

## 8. Next Node Suggestions

If the user chooses Option A, the suggested next node is:

`KG-RUNTIME-163-PULL-USER-MEDIATED-EXECUTION-EVIDENCE-INTAKE: qwen3.6:35b pull user-mediated evidence intake docs-only`

If the user chooses Option B, the suggested next node is:

`KG-RUNTIME-163-PULL-COMMAND-LIMITED-RETRY: qwen3.6:35b pull command-limited retry after explicit authorization`

This node does not enter either next node.

This node does not enter KG-RUNTIME-164, stability verification, real use, or trial use.

## 9. Final Status

- KG-RUNTIME-163-PULL-RETRY-AUTHORIZATION-GATE completed as a docs-only retry-path authorization gate.
- KG-RUNTIME-163-PULL-BLOCKED-AUDIT has completed and passed.
- Starting HEAD for this node was `c7a44ba66030ce85c5b06fb208df0440037be8f7`.
- Starting remote tag for this node was `v0.1.550-zdoc-single-model-upgrade-qwen3-6-35b-pull-pre-list-blocked-audit`.
- Current blocked reason: `PULL PRE-LIST BLOCKED / localhost Ollama endpoint access not permitted`.
- Complete failure output is recorded in this document.
- `ollama pull qwen3.6:35b` was not executed.
- The post-pull `ollama list` was not executed.
- Whether `qwen3.6:35b` is installed remains unconfirmed.
- Model upgrade has not started.
- Recommended path: `Option A / user-mediated pull execution evidence intake`.
- Fallback path: `Option B / Codex command-limited retry after explicit authorization`.
- Current decision: `NO-GO FOR RETRY EXECUTION / pending explicit retry path authorization`.
- Future authorization templates are recorded only as templates.
- The future authorization templates are not treated as already authorized.
- KG-RUNTIME-164 was not entered.
- Stability verification was not entered.
- Real use was not entered.
- Trial use was not entered.

KG-RUNTIME-163-PULL-RETRY-AUTHORIZATION-GATE stops here and waits for human review.
