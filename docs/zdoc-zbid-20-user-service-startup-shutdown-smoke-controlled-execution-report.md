# ZDoc-ZBid 20-user service startup-shutdown smoke controlled execution report

## 1. Step 268 execution summary

- Step: Step 268 - ZDoc-ZBid 20-user service startup-shutdown smoke controlled execution.
- Execution time: 2026-05-23 13:44:15 CST.
- Scope: service startup and shutdown smoke only.
- ZDoc service was started on `127.0.0.1:18766`, verified by `lsof` / `ps`, then stopped.
- ZBid service was started on `127.0.0.1:18767`, verified by `lsof` / `ps`, then stopped.
- No HTTP request was sent.
- No business endpoint was called.
- No preview payload was sent.
- No code, tests, frontend, backend, or existing docs were modified.
- The only intended repository write is this report file.

## 2. Pre-start environment checks

| Check item | Result |
| --- | --- |
| ZDoc git branch / HEAD / status | Matched authorized baseline and clean before startup |
| ZBid git branch / HEAD / status | Matched authorized baseline and clean before startup |
| `127.0.0.1:18766` listener before startup | No listener output |
| `127.0.0.1:18767` listener before startup | No listener output |
| Suspected residual ZDoc / ZBid service process | No matching residual process output |
| Ollama process | No matching process output |
| ZDoc `output/job/export` | Path missing |
| ZBid `output/job/export` | Path missing |

## 3. ZDoc repository check

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Authorized start HEAD: `e53b7ed06f305ff01e836b6092040a4babc15279`
- Verified HEAD before execution: `e53b7ed06f305ff01e836b6092040a4babc15279`
- `git status --short` before startup: empty
- `git status --short` after shutdown and before report creation: empty

## 4. ZBid repository check

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- Authorized start HEAD: `378355755372e03ac4f4064af59b287054984c25`
- Verified HEAD before execution: `378355755372e03ac4f4064af59b287054984c25`
- `git status --short` before startup: empty
- `git status --short` after shutdown: empty

## 5. Pre-start port occupancy

| Port | Command | Result |
| --- | --- | --- |
| `127.0.0.1:18766` | `lsof -nP -iTCP:18766 -sTCP:LISTEN` | No listener output |
| `127.0.0.1:18767` | `lsof -nP -iTCP:18767 -sTCP:LISTEN` | No listener output |

No adjacent port was needed.

## 6. Pre-start residual process checks

- Residual service process command: `ps -axo pid,ppid,stat,command | rg -i 'uvicor[n]|backend\.app\.main:ap[p]|app\.main:ap[p]|文档生成系[统]|ZhiFei_BizSystem-local-llm-clea[n]'`
- Result: no matching residual ZDoc / ZBid service process output before startup.
- Ollama process command: `ps -axo pid,ppid,stat,command | rg -i 'ollam[a]'`
- Result: no matching Ollama process output.

## 7. ZDoc service startup result

- Startup command:

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- Port: `127.0.0.1:18766`
- PID: `11240`
- Listening check command: `lsof -nP -iTCP:18766 -sTCP:LISTEN`
- Listening check result:

```text
COMMAND   PID     USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
Python  11240 youfeini   10u  IPv4 ...    0t0      TCP 127.0.0.1:18766 (LISTEN)
```

- Process check result:

```text
11240 ... Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

## 8. ZBid service startup result

- Startup command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- Port: `127.0.0.1:18767`
- PID: `11241`
- Listening check command: `lsof -nP -iTCP:18767 -sTCP:LISTEN`
- Listening check result:

```text
COMMAND   PID     USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
Python  11241 youfeini   10u  IPv4 ...    0t0      TCP 127.0.0.1:18767 (LISTEN)
```

- Process check result:

```text
11241 ... Python -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

## 9. Endpoint and preview payload boundary

- No business endpoint was called.
- `POST /local-trial/preview-only` was not called.
- `POST /local-llm/zdoc-preview-only/receive` was not called.
- No `preview_packet`, `validator_result`, or `blocked_reasons` payload was sent.
- No preview payload was sent to ZBid.
- No external endpoint was called.

## 10. Forbidden chain review

The following were not triggered:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback
- DOCX generation
- `output/job/export` write
- evidence creation
- scoring basis creation
- top local model upgrade
- 50-user formal deployment design

## 11. Service shutdown result

- Shutdown method: sent normal `TERM` to the two PIDs started by this step only.
- Command used:

```bash
kill 11240 11241
```

- No unknown process was killed.
- ZDoc shutdown log indicated application shutdown completed and server process `11240` finished.
- ZBid shutdown log indicated application shutdown completed and server process `11241` finished.

## 12. PID stop result

Post-shutdown command:

```bash
ps -p 11240,11241 -o pid,ppid,stat,command
```

Result:

```text
PID  PPID STAT COMMAND
```

Both PIDs were stopped.

## 13. Port release result

| Port | Post-shutdown check | Result |
| --- | --- | --- |
| `127.0.0.1:18766` | `lsof -nP -iTCP:18766 -sTCP:LISTEN` | No listener output |
| `127.0.0.1:18767` | `lsof -nP -iTCP:18767 -sTCP:LISTEN` | No listener output |

Both ports were released after shutdown.

## 14. output/job/export check

| Repository | Check result |
| --- | --- |
| ZDoc | `output/job/export` path missing |
| ZBid | `output/job/export` path missing |

No `output/job/export` write was observed.

## 15. DOCX generation check

- ZDoc `git status --short -- '*.docx'`: empty
- ZBid `git status --short -- '*.docx'`: empty
- No DOCX generation signal was observed in this step.

## 16. AI knowledge graph folder access statement

The paused folder was not accessed, scanned, read, copied, moved, analyzed, or identified:

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

No command in this step targeted that path.

## 17. Risks and observations

- This smoke only confirms that the ZDoc and ZBid local services can start, listen on the authorized local ports, and shut down cleanly.
- This smoke does not confirm endpoint runtime behavior because HTTP calls were explicitly forbidden.
- This smoke does not validate preview payload send/receive behavior.
- `TERM` was used only for the two PIDs started by this step after non-TTY sessions could not receive interactive Ctrl-C input. Shutdown completed cleanly.
- The host remains positioned only as a 20-user controlled pilot host, not a long-term formal production server.

## 18. Step 269 recommendation

Step 269 is recommended only as a separately authorized docs-only review or authorization request. It should not be entered automatically.

Recommended Step 269 direction:

- Archive the Step 268 startup-shutdown smoke result.
- Decide whether to authorize a later preview-only controlled endpoint smoke.
- Preserve `preview-only / no-write / no-evidence`.
- Continue forbidding `/generate`, `/export_docx`, `/review/apply`, ZBid writeback, DOCX generation, and `output/job/export` writes unless separately authorized.

## 19. Step 269 authorization request draft

```text
执行 Step 269：ZDoc-ZBid 20-user service startup-shutdown smoke review and next controlled execution authorization request

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<待填入 Step 268 结束后 HEAD>

授权范围：
仅 docs-only 归档 Step 268 服务启动关闭 smoke 结果，并起草下一步受控执行授权请求。

严格边界：
1. 不修改代码 / tests / frontend / backend / 既有 docs；
2. 不运行 ZDoc / ZBid 服务；
3. 不运行 Ollama；
4. 不访问端口；
5. 不调用任何 endpoint；
6. 不触发 /generate、/export_docx、/review/apply；
7. 不触发 ZBid 写回；
8. 不生成 DOCX；
9. 不写 output/job/export；
10. 不把 preview-only 结果作为 evidence；
11. 不把 preview-only 结果作为评分依据；
12. 不访问或识别 /Users/youfeini/Desktop/AI知识图谱大全；
13. 不进入 50 人正式部署设计；
14. 不实施顶级模型升级。

完成后停止，不得自动进入后续步骤。
```
