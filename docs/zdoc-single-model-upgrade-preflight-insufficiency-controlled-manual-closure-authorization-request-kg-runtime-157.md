# ZDoc Single-Model Upgrade Preflight Insufficiency Controlled Manual-Closure Authorization Request — KG-RUNTIME-157

## 1. Scope

KG-RUNTIME-157 is a docs-only authorization request document for a possible later controlled manual closure of the remaining single-model upgrade preflight insufficiencies.

This node only records the authorization request boundary. It does not execute real-machine closure, recheck, preflight, model upgrade, model download, service runtime, endpoint access, KG access, generation, export, or write-back.

KG-RUNTIME-157 explicitly:

- Does not execute real-machine supplementary checks.
- Does not re-execute network HEAD, GET, or download tests.
- Does not execute service process checks.
- Does not execute disk-space checks.
- Does not run Ollama.
- Does not execute `ollama list`.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute any Ollama model command.
- Does not upgrade, pull, delete, or replace any model.
- Does not run the ZDoc service.
- Does not access any endpoint.
- Does not read or parse real KG.
- Does not read real KG file body content.
- Does not parse real KG JSON.
- Does not trigger generation, export, or write-back.
- Does not write `output`, `job`, or `export`.
- Does not enter real use or trial use.

## 2. Baseline

KG-RUNTIME-156 ended with the following recorded baseline:

- HEAD: `1f654a1`
- Full HEAD observed by `git rev-parse HEAD`: `1f654a1dcc11159fca301884867851a278200c8c`
- tag: `v0.1.539-zdoc-single-model-upgrade-preflight-manual-closure-authorization-gate`
- Target docs file: `docs/zdoc-single-model-upgrade-preflight-insufficiency-manual-closure-authorization-gate-kg-runtime-156.md`
- Current gate decision: `NO-GO / pending manual-closure authorization`
- Candidate: `qwen3.6:35b`

KG-RUNTIME-157 starts from that NO-GO state and does not convert it into preflight completion, manual-closure completion, upgrade authorization, or upgrade execution authorization.

## 3. Still-Unclosed Preflight Insufficiencies

1. Network insufficiency:
   - The network HEAD check was previously refused by the local proxy `127.0.0.1:7897`.
   - The download channel remains unconfirmed.
   - The project does not have upgrade execution authorization conditions.

2. Download size live reconfirmation insufficiency:
   - `24GB` remains only the KG-RUNTIME-152 historical record.
   - Current download size live reconfirmation has not been completed.
   - The carried size record cannot be used as the final pre-execution download size confirmation.

3. ZDoc service state insufficiency:
   - The ZDoc service state has not been closed.
   - No endpoint has been accessed.
   - If this item needs later closure, it must use a user-explicitly authorized minimal read-only method.

## 4. Current Request Decision

`Current request decision: NO-GO / awaiting explicit user authorization for controlled manual closure`

Decision meaning:

- KG-RUNTIME-157 does not grant upgrade execution permission.
- KG-RUNTIME-157 does not grant permission to run `ollama pull qwen3.6:35b`.
- KG-RUNTIME-157 does not grant permission to run any Ollama command.
- KG-RUNTIME-157 does not execute any manual-closure command.
- KG-RUNTIME-157 only forms the authorization request for a possible next-step controlled manual-closure preflight.
- If the user does not explicitly authorize each item, KG-RUNTIME-158 must not execute any supplementary preflight command.

## 5. Explicit User Authorization Required For Future KG-RUNTIME-158

If future KG-RUNTIME-158 is requested to perform controlled manual closure, the user must explicitly authorize each item.

Future authorization must explicitly state whether the user allows:

1. Executing `git status --short`.
2. Executing `git rev-parse HEAD`.
3. Reading KG-RUNTIME-157 / 156 / 155 / 154 target docs files.
4. Executing a minimal read-only network connectivity recheck.
5. Executing `qwen3.6:35b` download size live reconfirmation.
6. Executing read-only ZDoc service state confirmation.
7. Confirming that no endpoint has been accessed.
8. Confirming that real KG has not been read.
9. Confirming that KG JSON has not been parsed.
10. Confirming that generation, export, and write-back have not been triggered.
11. Executing `git diff --check`.
12. Executing `git diff --cached --check`.
13. Adding a docs-only result file.
14. Committing.
15. Pushing.
16. Creating a remote tag.

The user must also explicitly confirm that the following remain prohibited:

1. Running Ollama.
2. Executing `ollama list`.
3. Executing `ollama pull qwen3.6:35b`.
4. Executing `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
5. Executing any Ollama model command.
6. Upgrading, pulling, deleting, or replacing any model.
7. Running the ZDoc service.
8. Accessing any endpoint.
9. Reading real KG file body content.
10. Parsing real KG JSON.
11. Triggering generation, export, or write-back.
12. Writing `output`, `job`, or `export`.
13. Entering real use or trial use.

Missing, implied, partial, or template-only approval remains insufficient.

## 6. Future KG-RUNTIME-158 Command Boundary Proposal

`The following boundary is proposed only for a future node and is not authorized in KG-RUNTIME-157.`

Candidate boundary for future KG-RUNTIME-158, if separately and explicitly authorized by the user:

1. `git status --short`
2. `git rev-parse HEAD`
3. Reading KG-RUNTIME-157 / 156 / 155 / 154 target docs files.
4. Minimal read-only network connectivity recheck, limited to user-explicitly authorized `qwen3.6:35b` / `qwen3` official trusted sources.
5. Download size live reconfirmation that records size only and does not download any model.
6. Read-only ZDoc service state confirmation.
7. Endpoint non-access confirmation without accessing any endpoint.
8. KG / generation / export / write-back non-trigger confirmation without reading real KG, parsing JSON, or triggering any chain.
9. `git diff --check`
10. `git diff --cached --check`
11. Docs-only file addition, commit, push, and remote tag creation.

The following commands and actions must still not be included in any future KG-RUNTIME-158 candidate boundary:

- `ollama list`
- `ollama pull qwen3.6:35b`
- `ollama run`
- `ollama rm`
- `ollama serve`
- Any Ollama model command.
- Any model upgrade, pull, delete, or replacement command.
- Any ZDoc service startup command.
- Any endpoint access command.
- Any real KG read or parse command.
- Any generation, export, or write-back command.

## 7. Required User Authorization Wording For Next Step

The following wording is a required authorization request template for KG-RUNTIME-158. It is not authorization for KG-RUNTIME-157 and must not be treated as already granted:

"我明确授权 KG-RUNTIME-158 进行 single-model upgrade preflight insufficiency controlled manual-closure checks。授权范围仅限：git 状态确认、读取 KG-RUNTIME-157 / 156 / 155 / 154 目标 docs 文件、最小化只读网络连通性复核、`qwen3.6:35b` 下载体积 live reconfirmation、ZDoc 服务状态只读确认、确认 endpoint 未访问、确认真实 KG 未读取、确认 KG JSON 未解析、确认 generation / export / write-back 未触发、生成 docs-only 结果文件、git diff 检查、commit、push、远端 tag 创建。禁止运行 Ollama，禁止执行 `ollama list`，禁止执行 `ollama pull qwen3.6:35b`，禁止执行任何 Ollama 模型命令，禁止升级、拉取、删除或替换任何模型。完成后必须回报并停止，不得直接升级。"

Template status:

- The wording above is only an authorization request template.
- KG-RUNTIME-157 must not treat this template as granted authorization.
- Only if the user explicitly replies with authorization in a later conversation may KG-RUNTIME-158 execute within the granted boundary.
- Even if KG-RUNTIME-158 is authorized, it still must not run Ollama or execute any model command.

## 8. Next Recommended Node

Next recommended node:

`KG-RUNTIME-158: single-model upgrade preflight insufficiency controlled manual-closure checks command-limited`

KG-RUNTIME-158 is still not an upgrade node.

KG-RUNTIME-158 may only perform controlled manual-closure preflight after explicit item-by-item user authorization.

KG-RUNTIME-158 must still:

- Not run Ollama.
- Not execute `ollama list`.
- Not execute `ollama pull qwen3.6:35b`.
- Not execute any Ollama model command.
- Not upgrade, pull, delete, or replace any model.

## 9. Explicit Prohibitions Preserved

The following prohibitions remain preserved after KG-RUNTIME-157:

- Do not run Ollama.
- Do not execute `ollama list`.
- Do not execute `ollama pull qwen3.6:35b`.
- Do not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- Do not execute any Ollama model command.
- Do not upgrade, pull, delete, or replace any model.
- Do not run the ZDoc service.
- Do not access any endpoint.
- Do not read real KG.
- Do not parse real KG JSON.
- Do not trigger generation, export, or write-back.
- Do not write `output`, `job`, or `export`.
- Do not enter real use or trial use.

## 10. Final Status

- KG-RUNTIME-157 completed as docs-only controlled manual-closure authorization request.
- No manual-closure command was executed.
- No network HEAD, GET, or download test was executed.
- No service process check was executed.
- Upgrade remains not authorized.
- `ollama pull qwen3.6:35b` remains not authorized.
- No Ollama command is authorized.
- Model upgrade has not been executed.
- Trial / real use has not started.
- Candidate remains `qwen3.6:35b`.
- Overall status remains: `NO-GO / awaiting explicit user authorization for controlled manual closure`
- Next recommended node: `KG-RUNTIME-158: single-model upgrade preflight insufficiency controlled manual-closure checks command-limited`
