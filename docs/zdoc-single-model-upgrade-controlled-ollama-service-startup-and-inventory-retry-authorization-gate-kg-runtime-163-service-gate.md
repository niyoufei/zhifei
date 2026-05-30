# ZDoc Single-Model Upgrade Controlled Ollama Service Startup And Inventory Retry Authorization Gate — KG-RUNTIME-163-SERVICE-GATE

## 1. Scope

KG-RUNTIME-163-SERVICE-GATE is a docs-only service startup and inventory retry authorization gate for the ZDoc single-model upgrade chain.

This node only records the authorization boundary required before any later Ollama service startup or inventory retry can occur. It is not a service startup node, not an inventory retry node, not a model upgrade node, not a stability verification node, and not a real-use or trial-use node.

This node explicitly:

- Does not run Ollama.
- Does not execute `ollama serve`.
- Does not execute `ollama list`.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute any Ollama model command.
- Does not upgrade, pull, delete, or replace models.
- Does not download model files.
- Does not run the ZDoc service.
- Does not access endpoints.
- Does not read or parse real KG.
- Does not read real KG file body content.
- Does not parse real KG JSON.
- Does not trigger generation, export, or write-back.
- Does not write `output`, `job`, or `export`.
- Does not enter KG-RUNTIME-164.
- Does not enter stability verification.
- Does not enter real use or trial use.

KG-RUNTIME-163-SERVICE-GATE only forms the decision gate for whether a later step may start the Ollama server and retry inventory collection.

## 2. Baseline

KG-RUNTIME-163-BLOCKED-1 established the following baseline:

- HEAD: `17f3a50632a9068755dcbc552efcd62c79d0f398`
- tag: `v0.1.546-zdoc-single-model-upgrade-inventory-blocked-ollama-service-stopped`
- Target docs file: `docs/zdoc-single-model-upgrade-user-mediated-inventory-blocked-ollama-service-stopped-kg-runtime-163-blocked-1.md`
- Candidate: `qwen3.6:35b`
- Official-source download size evidence: `24GB`
- Current blocker: `OLLAMA SERVER NOT RUNNING / pre-upgrade inventory unavailable`
- Current decision: `BLOCKED / service startup authorization required before inventory retry`

KG-RUNTIME-163-SERVICE-GATE starts from that blocked state. It does not convert the blocked state into service startup authorization, inventory retry authorization, or model upgrade authorization.

## 3. Blocked State Summary

The blocked state is recorded as follows:

1. The user manually executed `ollama list`.
2. The output was:

   ```text
   Error: could not connect to ollama server, run 'ollama serve' to start it
   ```

3. This output shows that the Ollama CLI is callable, but the Ollama server is not running.
4. Because the server is not running, the pre-upgrade model inventory remains unavailable.
5. The previous authorization did not include `ollama serve`.
6. Because the pre-upgrade inventory has not been obtained, `ollama pull qwen3.6:35b` must not be executed.

Current blocker remains:

`OLLAMA SERVER NOT RUNNING / pre-upgrade inventory unavailable`

## 4. Why Service Startup Gate Is Required

`ollama list` depends on the Ollama server.

The current server is not running. If the Ollama server is not started, the pre-upgrade model inventory cannot be obtained. If the pre-upgrade model inventory cannot be obtained, the model upgrade must not proceed.

Starting the Ollama server is a new authorization item because previous docs-only and command-limited boundaries continued to prohibit `ollama serve`. Therefore, the user must explicitly choose and authorize the startup path before any later service startup or inventory retry occurs.

This gate preserves the following decision:

`BLOCKED / service startup authorization required before inventory retry`

## 5. Startup / Inventory Retry Options

The following options are future paths only. KG-RUNTIME-163-SERVICE-GATE does not execute either option.

### Option A: user-mediated service startup and inventory retry

The user may manually start the Ollama application on the local machine, or manually execute the following command in the local machine terminal:

```bash
ollama serve
```

The user may then open another local terminal and manually execute:

```bash
ollama list
```

The user would paste the complete `ollama list` output back to the controller as later inventory evidence.

Under Option A:

- Codex does not run Ollama.
- Codex does not execute `ollama serve`.
- Codex does not execute `ollama list`.
- Codex does not execute `ollama pull qwen3.6:35b`.
- The user-manual output becomes the evidence basis for a later inventory intake node.

### Option B: Codex command-limited service startup and inventory retry

After separate explicit user authorization, Codex may perform a later command-limited service check with only the following operational intent:

1. Start the Ollama server.
2. Retry only `ollama list`.
3. Record the pre-upgrade model inventory.
4. Stop after the inventory retry record is complete.

Even under Option B, the following remain prohibited:

- `ollama pull qwen3.6:35b`
- `ollama run`
- `ollama rm`
- Any other Ollama command beyond the explicitly authorized service startup and `ollama list` retry.
- Deleting or replacing other models.
- Modifying the `latest` pointer.
- Running the ZDoc service.
- Accessing endpoints.
- Reading real KG.
- Reading real KG file body content.
- Parsing KG JSON.
- Triggering generation, export, or write-back.
- Writing `output`, `job`, or `export`.
- Entering KG-RUNTIME-164.
- Entering stability verification.
- Entering trial use.
- Entering real use.

Option B is not authorized by this file. It requires a later explicit user authorization.

## 6. Recommended Option

`Recommended option: Option A / user-mediated service startup and inventory retry`

Recommendation reasons:

1. Codex has previously encountered sandbox permission or approval-timeout limits around Ollama command execution.
2. The user's local terminal has already shown that the Ollama CLI is callable.
3. The current blocker only requires starting the Ollama server and then retrying `ollama list`.
4. Option A does not require Codex to execute a service startup command.
5. Option A has a clearer boundary and lower operational risk.
6. Option A better matches stable-progress principles.

Authorization status:

- Option A is only the recommended path.
- KG-RUNTIME-163-SERVICE-GATE must not be treated as the user having selected Option A.
- KG-RUNTIME-163-SERVICE-GATE must not be treated as authorization for the next step.
- The project must wait for later explicit user authorization or user-manual `ollama list` output.

## 7. Required User Authorization / Action Wording For Next Step

The following text may be used if the user chooses Option A. It is not authorization granted by this file.

"我选择 Option A：user-mediated service startup and inventory retry。我将在本机手动启动 Ollama 应用或执行 `ollama serve`，随后手动执行 `ollama list`，并将完整输出粘贴给总控师。仍禁止 Codex 执行 `ollama serve`，禁止 Codex 执行 `ollama list`，禁止执行 `ollama pull qwen3.6:35b`，禁止执行任何模型升级命令。"

The following text may be used only if the user chooses Option B. It is not authorization granted by this file.

"我明确授权 KG-RUNTIME-163-SERVICE-CHECK 采用 Option B：Codex command-limited service startup and inventory retry。授权范围仅限启动 Ollama server 并执行 `ollama list` 获取升级前清单。禁止执行 `ollama pull qwen3.6:35b`，禁止执行 `ollama run`，禁止执行 `ollama rm`，禁止删除或替换模型，禁止修改 latest 指向，禁止运行 ZDoc 服务，禁止访问 endpoint，禁止读取真实 KG，禁止解析 KG JSON，禁止触发 generation / export / write-back，禁止进入 KG-RUNTIME-164、稳定性验证或试用。"

Template status:

- The text above is only next-step wording.
- KG-RUNTIME-163-SERVICE-GATE must not treat either template as already authorized.
- A later node may proceed only after the user explicitly selects a path or provides manual inventory output.

## 8. Next Recommended Node

Next recommended node:

`KG-RUNTIME-163-SERVICE-CHECK: controlled Ollama service startup and inventory retry after explicit user action or authorization`

Next-node constraints:

- If the user chooses Option A, the next step should be a docs-only intake after the user manually provides complete `ollama list` output.
- If the user chooses Option B, the next step must first obtain explicit user authorization before Codex starts the Ollama server or retries `ollama list`.
- Both paths must continue to prohibit `ollama pull qwen3.6:35b`.
- Both paths must continue to prohibit entering KG-RUNTIME-164.
- Both paths must continue to prohibit stability verification, trial use, and real use.

KG-RUNTIME-163-SERVICE-GATE stops here and does not enter KG-RUNTIME-163-SERVICE-CHECK.

## 9. Explicit Prohibitions Preserved

After KG-RUNTIME-163-SERVICE-GATE, the following prohibitions remain preserved:

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
- Do not parse real KG JSON.
- Do not trigger generation, export, or write-back.
- Do not write `output`, `job`, or `export`.
- Do not enter KG-RUNTIME-164.
- Do not enter stability verification.
- Do not enter real use or trial use.

The following also remains true:

- Ollama server startup was not executed in this node.
- `ollama list` was not executed by Codex in this node.
- `ollama pull qwen3.6:35b` was not executed in this node.
- Pre-upgrade inventory remains unavailable.
- Model upgrade has not started.
- Trial or real use has not started.

## 10. Final Status

- KG-RUNTIME-163-SERVICE-GATE completed as docs-only authorization gate.
- Ollama server startup was not executed.
- `ollama list` was not executed by Codex.
- `ollama pull qwen3.6:35b` was not executed.
- Pre-upgrade inventory remains unavailable.
- Model upgrade has not started.
- Trial / real use has not started.
- Candidate remains `qwen3.6:35b`.
- Recommended option: `Option A / user-mediated service startup and inventory retry`
- Current decision: `WAITING FOR USER ACTION OR EXPLICIT SERVICE-CHECK AUTHORIZATION`
- Next recommended node: `KG-RUNTIME-163-SERVICE-CHECK: controlled Ollama service startup and inventory retry after explicit user action or authorization`

KG-RUNTIME-163-SERVICE-GATE stops here and waits for human review. It does not enter KG-RUNTIME-163-SERVICE-CHECK, KG-RUNTIME-164, stability verification, trial use, or real use.
