# ZDoc Single-Model Upgrade Execution Authorization Gate After Evidence Closure — KG-RUNTIME-162

## 1. Scope

KG-RUNTIME-162 is a docs-only upgrade execution authorization gate for the ZDoc single-model upgrade chain.

This node is based on KG-RUNTIME-161 evidence closure and records the authorization boundary required before any later upgrade execution node may proceed.

This node explicitly:

- Does not execute the upgrade.
- Does not run Ollama.
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
- Does not perform a directory scan.
- Does not enter real use or trial use.

KG-RUNTIME-162 is not an upgrade execution node and does not grant permission to execute `ollama pull qwen3.6:35b`.

## 2. Baseline

KG-RUNTIME-161 ended with the following baseline for this node:

- HEAD: `31ea0ffe1dfecee6f1ed35b009637eca41a314aa`
- tag: `v0.1.544-zdoc-single-model-upgrade-controller-mediated-evidence-intake`
- Target docs file: `docs/zdoc-single-model-upgrade-controller-mediated-official-source-evidence-intake-kg-runtime-161.md`
- Evidence completeness result: `CLOSED / official-source evidence received from controller`
- Current decision: `EVIDENCE CLOSED / upgrade execution still not authorized`
- Candidate: `qwen3.6:35b`

KG-RUNTIME-162 starts from evidence closure only. It does not convert evidence closure into upgrade execution authorization.

## 3. Evidence Closure Summary

### 3.1 Network connectivity

- Status: `CLOSED / official-source evidence received from controller`
- Evidence basis: KG-RUNTIME-161 recorded controller-mediated official-source evidence intake.
- Codex did not independently perform network re-verification in KG-RUNTIME-161 or KG-RUNTIME-162.

### 3.2 Download size

- Status: `CLOSED / 24GB official-source evidence received from controller`
- Official-source download size evidence: `24GB`
- Evidence basis: KG-RUNTIME-161 recorded Ollama official model page and Ollama official tags page evidence showing `24GB`.

### 3.3 Candidate mapping

- Ollama-side candidate: `qwen3.6:35b`
- Ollama tags-side related candidate: `qwen3.6:35b-a3b`
- Upstream official model identity reference: `Qwen3.6-35B-A3B`

The only upgrade candidate remains `qwen3.6:35b`.

### 3.4 Safety state

- Ollama was not run.
- `ollama list` was not executed.
- `ollama pull qwen3.6:35b` was not executed.
- No Ollama model command was executed.
- No model was downloaded.
- No model was upgraded.
- Real use or trial use was not entered.

## 4. Upgrade Execution Readiness Gate

`Readiness gate result: READY FOR EXPLICIT USER AUTHORIZATION / upgrade execution still not authorized`

Readiness meaning:

- Evidence closure has been completed.
- The single-model candidate has been confirmed.
- Official-source download size evidence has been confirmed as `24GB`.
- ZDoc service state was previously closed as not running.
- Endpoint / KG / Generation / Export / Write-Back safety was previously closed.
- Upgrade execution still requires explicit user authorization in a later node.
- KG-RUNTIME-162 grants no execution permission.
- KG-RUNTIME-162 grants no Ollama command permission.

Readiness does not mean GO for execution. It only means the record is ready for the user to decide whether to explicitly authorize a later command-limited execution node.

## 5. Current Gate Decision

`Current gate decision: NO-GO FOR EXECUTION / pending explicit user authorization`

Decision meaning:

- KG-RUNTIME-162 does not execute the upgrade.
- KG-RUNTIME-162 does not execute `ollama pull qwen3.6:35b`.
- KG-RUNTIME-162 does not execute `ollama list`.
- KG-RUNTIME-162 does not run any Ollama command.
- KG-RUNTIME-162 only forms the authorization wording required for KG-RUNTIME-163.
- Only after the user explicitly authorizes each required permission in a later node may KG-RUNTIME-163 execute command-limited upgrade operations.

Upgrade remains not authorized.

`ollama pull qwen3.6:35b` remains not authorized.

No Ollama command is authorized by KG-RUNTIME-162.

## 6. Future KG-RUNTIME-163 Authorization Boundary

This section defines only a possible future authorization boundary. It does not execute anything and must not be treated as already authorized.

If KG-RUNTIME-163 later receives explicit user authorization, the recommended command boundary is limited to:

1. `git status --short`
2. `git rev-parse HEAD`
3. Read KG-RUNTIME-162 / 161 / 160 / 159 target docs files.
4. Perform a quick pre-upgrade disk-space confirmation.
5. Execute `ollama list` for pre-upgrade inventory recording.
6. Execute `ollama pull qwen3.6:35b` for single-model pull / upgrade.
7. Execute `ollama list` for post-upgrade inventory recording.
8. Add a docs-only upgrade execution record file.
9. `git diff --check`
10. `git diff --cached --check`
11. Commit.
12. Push.
13. Create a remote tag.

Even if KG-RUNTIME-163 receives explicit authorization, it must still prohibit:

- Executing `ollama run`.
- Executing `ollama rm`.
- Executing `ollama serve`.
- Deleting or replacing other models.
- Modifying the `latest` pointer, unless separately and explicitly authorized by the user.
- Running the ZDoc service.
- Accessing endpoints.
- Reading real KG.
- Reading real KG file body content.
- Parsing KG JSON.
- Triggering generation, export, or write-back.
- Writing `output`, `job`, or `export`.
- Entering real use or trial use.

The future KG-RUNTIME-163 boundary is single-model only and applies only to `qwen3.6:35b`.

## 7. Required User Authorization Wording For KG-RUNTIME-163

The following text is only an authorization template for a later KG-RUNTIME-163 node. It is not authorization granted to KG-RUNTIME-162.

"我明确授权 KG-RUNTIME-163 执行 single-model upgrade execution command-limited。授权对象仅限 `qwen3.6:35b`。允许执行：`git status --short`、`git rev-parse HEAD`、读取 KG-RUNTIME-162 / 161 / 160 / 159 目标 docs 文件、升级前磁盘空间快速确认、`ollama list` 升级前清单记录、`ollama pull qwen3.6:35b` 单模型拉取 / 升级、`ollama list` 升级后清单记录、生成 docs-only 升级执行记录文件、`git diff --check`、`git diff --cached --check`、commit、push、远端 tag 创建。禁止执行 `ollama run`，禁止执行 `ollama rm`，禁止执行 `ollama serve`，禁止删除或替换其他模型，禁止修改 latest 指向，禁止运行 ZDoc 服务，禁止访问 endpoint，禁止读取真实 KG，禁止解析 KG JSON，禁止触发 generation / export / write-back，禁止写 output / job / export，禁止进入真实使用 / 试用阶段。完成后必须回报并停止，不得进入稳定性验证或试用。"

Template status:

- The text above is only the KG-RUNTIME-163 authorization template.
- KG-RUNTIME-162 must not treat the template as already authorized.
- Only if the user explicitly replies with authorization in a later conversation may KG-RUNTIME-163 execute.
- Even if KG-RUNTIME-163 is authorized, it is limited to the single model `qwen3.6:35b` and must not expand to other models.

## 8. Next Recommended Node

Next recommended node:

`KG-RUNTIME-163: single-model upgrade execution command-limited after explicit user authorization`

KG-RUNTIME-163 requirements:

- KG-RUNTIME-163 must first obtain explicit user authorization.
- KG-RUNTIME-163 is limited to `qwen3.6:35b`.
- KG-RUNTIME-163 must not run the ZDoc service.
- KG-RUNTIME-163 must not access endpoints.
- KG-RUNTIME-163 must not read real KG.
- KG-RUNTIME-163 must not parse KG JSON.
- KG-RUNTIME-163 must not trigger generation, export, or write-back.
- KG-RUNTIME-163 must not write `output`, `job`, or `export`.
- KG-RUNTIME-163 must not enter real use or trial use.

KG-RUNTIME-162 stops here and does not enter KG-RUNTIME-163.

## 9. Explicit Prohibitions Preserved

After KG-RUNTIME-162 and before KG-RUNTIME-163 receives explicit authorization, the following prohibitions remain preserved:

- Do not run Ollama.
- Do not execute `ollama list`.
- Do not execute `ollama pull qwen3.6:35b`.
- Do not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- Do not execute any Ollama model command.
- Do not upgrade, pull, delete, or replace models.
- Do not download model files.
- Do not run the ZDoc service.
- Do not access endpoints.
- Do not read real KG.
- Do not read real KG file body content.
- Do not parse real KG JSON.
- Do not trigger generation, export, or write-back.
- Do not write `output`, `job`, or `export`.
- Do not enter real use or trial use.

## 10. Final Status

- KG-RUNTIME-162 completed as docs-only upgrade execution authorization gate after evidence closure.
- Evidence closure was confirmed from KG-RUNTIME-161.
- Candidate remains `qwen3.6:35b`.
- Official-source download size evidence remains `24GB`.
- Upgrade execution remains not authorized.
- `ollama pull qwen3.6:35b` remains not authorized.
- No Ollama command was executed.
- Model upgrade has not been executed.
- Trial / real use has not started.
- Current gate decision: `NO-GO FOR EXECUTION / pending explicit user authorization`
- Next recommended node: `KG-RUNTIME-163: single-model upgrade execution command-limited after explicit user authorization`

KG-RUNTIME-162 stops here and waits for human review. It does not enter KG-RUNTIME-163.
