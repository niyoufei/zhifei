# ZDoc Single-Model Upgrade Preflight Insufficiency Controlled Manual-Closure Checks — KG-RUNTIME-158

## 1. Scope

KG-RUNTIME-158 is a command-limited controlled manual-closure checks node for the ZDoc single-model upgrade preflight insufficiency chain.

The user has granted limited authorization for this node only. The authorization is limited to closing preflight insufficiency checks and must not be interpreted as model upgrade authorization.

This node explicitly:

- Does not run Ollama.
- Does not execute `ollama list`.
- Does not execute `ollama pull qwen3.6:35b`.
- Does not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- Does not execute any Ollama model command.
- Does not upgrade, pull, delete, or replace any model.
- Does not download model files.
- Does not run the ZDoc service.
- Does not access any endpoint.
- Does not read or parse real KG.
- Does not read real KG file body content.
- Does not parse real KG JSON.
- Does not trigger generation, export, or write-back.
- Does not write `output`, `job`, or `export`.
- Does not enter real use or trial use.

KG-RUNTIME-158 is not an upgrade node, not a model download node, and not a trial node.

## 2. Baseline

KG-RUNTIME-157 baseline recorded for this node:

- HEAD: `305310f81226a85e79ad0d7f52f2b6fff96ba783`
- tag: `v0.1.540-zdoc-single-model-upgrade-controlled-manual-closure-request`
- Target docs file: `docs/zdoc-single-model-upgrade-preflight-insufficiency-controlled-manual-closure-authorization-request-kg-runtime-157.md`
- Current request decision: `NO-GO / awaiting explicit user authorization for controlled manual closure`
- Candidate: `qwen3.6:35b`

KG-RUNTIME-158 starts from that authorization state and does not convert it into upgrade execution authorization.

Observed start state for this node:

- `git status --short`: empty output
- `git rev-parse HEAD`: `305310f81226a85e79ad0d7f52f2b6fff96ba783`
- Worktree before this docs-only file: clean

## 3. Authorized Checks Actually Performed

The following command-limited checks were actually performed:

1. Git status and HEAD confirmation:
   - `git status --short`
   - `git rev-parse HEAD`
2. Target docs read:
   - `docs/zdoc-single-model-upgrade-preflight-insufficiency-controlled-manual-closure-authorization-request-kg-runtime-157.md`
   - `docs/zdoc-single-model-upgrade-preflight-insufficiency-manual-closure-authorization-gate-kg-runtime-156.md`
   - `docs/zdoc-single-model-upgrade-preflight-insufficiency-closure-kg-runtime-155.md`
   - `docs/zdoc-single-model-upgrade-controlled-preflight-checks-kg-runtime-154.md`
3. Network connectivity check against official trusted sources only.
4. Download size live reconfirmation attempt against official trusted sources only.
5. ZDoc service state read-only confirmation using process/listener inspection.
6. Endpoint not accessed confirmation based on this node's command record.
7. KG / generation / export / write-back not triggered confirmation based on this node's command record.

No directory scan was executed. No search engine was used. No model file was downloaded.

## 4. Network Connectivity Closure Result

Official trusted sources used:

- Ollama official model library: `https://ollama.com/library/qwen3.6:35b`
- Qwen official release channel: `https://github.com/QwenLM/Qwen3.6`
- Qwen official blog: `https://qwen.ai/blog?id=qwen3.6-35b-a3b`
- Hugging Face Qwen official organization page: `https://huggingface.co/Qwen/Qwen3.6-35B-A3B`

Check method:

- Read-only `curl -sSIL --max-time 15` HEAD requests.
- No model download request.
- No Ollama command.

Observed result:

- Each official-source request failed before reaching the source because `curl` attempted to use unavailable local proxy `127.0.0.1:7897`.
- Failure text observed for each request: `Failed to connect to 127.0.0.1 port 7897`.
- The node stopped deeper network attempts after the proxy block was observed.

Model download status:

- Model file downloaded: no.
- Ollama run: no.

Conclusion:

`INCOMPLETE / official source not reachable or blocked`

## 5. Download Size Live Reconfirmation Result

`qwen3.6:35b` size confirmation sources attempted:

- Ollama official model library: `https://ollama.com/library/qwen3.6:35b`
- Qwen official release channel: `https://github.com/QwenLM/Qwen3.6`
- Qwen official blog: `https://qwen.ai/blog?id=qwen3.6-35b-a3b`
- Hugging Face Qwen official organization page: `https://huggingface.co/Qwen/Qwen3.6-35B-A3B`

Confirmation method:

- Read-only official-source HEAD requests.
- No page body expansion after the local proxy block.
- No model download.
- No Ollama command.

Observed size:

- Live size was not confirmed.
- KG-RUNTIME-152's historical `24GB` record remains a carried prior record only.
- This node did not live-reconfirm whether the current size is still `24GB`.

Model download status:

- Model file downloaded: no.
- Ollama run: no.

Conclusion:

`INCOMPLETE / live size not confirmed`

## 6. ZDoc Service State Closure Result

Read-only confirmation methods used:

- `pgrep -fl 'uvicorn|fastapi|zdoc|文档生成系统|vite|next|node|npm'`
- `ps -ax -o pid=,command=`
- `lsof -nP -iTCP -sTCP:LISTEN`

Observed result:

- `pgrep` could not obtain the process list and returned:
  - `sysmon request failed with error: sysmond service not found`
  - `pgrep: Cannot get process list`
- `ps` returned a process snapshot. No ZDoc service, uvicorn, fastapi, vite, next, or npm service process was identified from the visible process snapshot.
- `lsof` returned active TCP listeners for `rapportd`, `ControlCenter`, and `clash-verge-service` only.
- No ZDoc, uvicorn, fastapi, node, vite, npm, or project service listener was observed.

Service actions:

- ZDoc service started: no.
- Endpoint accessed: no.

Conclusion:

`CLOSED / ZDoc service not running`

## 7. Endpoint / KG / Generation / Export / Write-Back Safety Result

This node confirms the following based on the actual commands executed in KG-RUNTIME-158:

- Endpoint accessed: no.
- Real KG file body content read: no.
- KG JSON parsed: no.
- Generation triggered: no.
- Export triggered: no.
- Write-back triggered: no.
- `output`, `job`, or `export` written: no.

Conclusion:

`CLOSED / no endpoint, KG, generation, export, or write-back activity`

## 8. Overall Manual-Closure Result

Component results:

- Network Connectivity Closure Result: `INCOMPLETE / official source not reachable or blocked`
- Download Size Live Reconfirmation Result: `INCOMPLETE / live size not confirmed`
- ZDoc Service State Closure Result: `CLOSED / ZDoc service not running`
- Endpoint / KG / Generation / Export / Write-Back Safety Result: `CLOSED / no endpoint, KG, generation, export, or write-back activity`

Overall result:

`MANUAL CLOSURE INCOMPLETE / remaining confirmation required`

Reason:

- Network connectivity is still blocked by unavailable local proxy `127.0.0.1:7897`.
- Download size live reconfirmation was not completed.
- Therefore KG-RUNTIME-158 cannot be marked as a full manual-closure pass.

Upgrade execution remains not authorized.

`ollama pull qwen3.6:35b` remains not authorized.

No Ollama command is authorized by this node.

The model upgrade has not been executed.

The next node must still be docs-only and must not directly upgrade.

## 9. Next Recommended Node

Next recommended node:

`KG-RUNTIME-159: single-model upgrade remaining preflight insufficiency closure docs-only`

Reason:

KG-RUNTIME-158 still has remaining unclosed confirmation items:

- Network connectivity to official trusted sources remains incomplete.
- `qwen3.6:35b` live download size remains unconfirmed.

KG-RUNTIME-159 must still not directly upgrade.

## 10. Explicit Prohibitions Preserved

The following prohibitions remain preserved after KG-RUNTIME-158:

- Do not run Ollama.
- Do not execute `ollama list`.
- Do not execute `ollama pull qwen3.6:35b`.
- Do not execute `ollama pull`, `ollama run`, `ollama rm`, or `ollama serve`.
- Do not execute any Ollama model command.
- Do not upgrade, pull, delete, or replace any model.
- Do not download model files.
- Do not run the ZDoc service.
- Do not access endpoint.
- Do not read real KG.
- Do not parse real KG JSON.
- Do not trigger generation, export, or write-back.
- Do not write `output`, `job`, or `export`.
- Do not enter real use or trial use.

## 11. Final Status

- KG-RUNTIME-158 completed as command-limited controlled manual-closure checks.
- No Ollama command was executed.
- `ollama pull qwen3.6:35b` was not executed.
- No model upgrade, pull, deletion, or replacement was executed.
- No model file was downloaded.
- ZDoc service was not started.
- Endpoint was not accessed.
- Real KG was not read.
- KG JSON was not parsed.
- Generation, export, and write-back were not triggered.
- `output`, `job`, and `export` were not written.
- Trial / real use has not started.
- Candidate remains `qwen3.6:35b`.
- Overall manual-closure result: `MANUAL CLOSURE INCOMPLETE / remaining confirmation required`
- Next recommended node: `KG-RUNTIME-159: single-model upgrade remaining preflight insufficiency closure docs-only`

KG-RUNTIME-158 stops here and does not enter KG-RUNTIME-159.
