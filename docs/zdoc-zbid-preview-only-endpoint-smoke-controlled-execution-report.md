# ZDoc-ZBid preview-only endpoint smoke controlled execution report

## 1. Step 270 execution summary

- Step: Step 270 - ZDoc-ZBid preview-only endpoint smoke controlled execution.
- Execution time: 2026-05-23 13:52:41 CST.
- Scope: one effective preview-only endpoint smoke request.
- ZDoc service was started on `127.0.0.1:18766`.
- ZBid service was started on `127.0.0.1:18767`.
- One ZDoc preview-only endpoint call was executed:
  - `POST http://127.0.0.1:18766/local-trial/preview-only`
- The returned `preview_packet`, `validator_result`, and `blocked_reasons` were passed to the ZDoc outbound adapter.
- The ZDoc outbound adapter sent one preview-only payload to the ZBid receiver endpoint:
  - `POST http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`
- ZDoc HTTP status: `200`.
- ZBid HTTP status: `200`.
- ZBid receiver returned `preview_only=true`, `no_write=true`, and `no_evidence=true`.
- Five forbidden flags were all `false`.
- Services were stopped after the smoke and both ports were released.
- No code, tests, frontend, backend, or existing docs were modified.
- The only repository write is this report file.

## 2. Pre-start environment checks

| Check item | Result |
| --- | --- |
| ZDoc branch / HEAD / status | `main`, `adcdd35d67212216a4f8a6a5afc36d055b7ce6df`, clean |
| ZBid branch / HEAD / status | `local-llm-integration-clean`, `378355755372e03ac4f4064af59b287054984c25`, clean |
| `127.0.0.1:18766` before startup | No listener output |
| `127.0.0.1:18767` before startup | No listener output |
| Suspected residual ZDoc / ZBid service process | No matching residual process output |
| Ollama process | No matching process output |
| ZDoc `output/job/export` | Path missing |
| ZBid `output/job/export` | Path missing |
| ZDoc DOCX git status check | Empty |
| ZBid DOCX git status check | Empty |

## 3. ZDoc repository state

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Authorized start HEAD: `adcdd35d67212216a4f8a6a5afc36d055b7ce6df`
- Verified start HEAD: `adcdd35d67212216a4f8a6a5afc36d055b7ce6df`
- `git status --short` before startup: empty
- `git status --short` after shutdown and before report creation: empty

## 4. ZBid repository state

- Repository: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- Branch: `local-llm-integration-clean`
- Authorized start HEAD: `378355755372e03ac4f4064af59b287054984c25`
- Verified start HEAD: `378355755372e03ac4f4064af59b287054984c25`
- `git status --short` before startup: empty
- `git status --short` after shutdown: empty

## 5. Service startup commands, ports, and PIDs

### ZDoc

Startup command:

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- Port: `127.0.0.1:18766`
- PID: `15090`

### ZBid

Startup command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- Port: `127.0.0.1:18767`
- PID: `15091`

## 6. Port listener checks

| Port | Listener check | Result |
| --- | --- | --- |
| `127.0.0.1:18766` | `lsof -nP -iTCP:18766 -sTCP:LISTEN` | PID `15090` listening |
| `127.0.0.1:18767` | `lsof -nP -iTCP:18767 -sTCP:LISTEN` | PID `15091` listening |

Process check:

```text
15090 ... Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
15091 ... Python -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

## 7. Minimal preview-only payload

The smoke used one desensitized / simulated / preview-only payload.

Payload characteristics:

- `integration_request_id`: `step-270-endpoint-smoke-001`
- `source_system`: `zdoc`
- `target_system`: `zbid`
- `project_id`: `project-step-270-preview-only`
- `document_id`: `doc-step-270-preview-only`
- `section_id`: `section-step-270-preview-only`
- `section_title`: `Step 270 Preview Only Smoke Section`
- `response_mode`: `preview_advisory`
- `zbid_preview_mode`: `preview_only`
- All evidence-as-formal flags were set to `false`.
- All writeback / DOCX / review apply / output write requests were set to `false`.
- No real tender evidence, formal scoring basis, DOCX, writeback data, or formal business data was used.

## 8. ZDoc endpoint call result

- Endpoint: `POST http://127.0.0.1:18766/local-trial/preview-only`
- HTTP status: `200`
- Uvicorn log:

```text
POST /local-trial/preview-only HTTP/1.1" 200 OK
```

ZDoc response checks:

| Field | Result |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | Top-level field not present in current ZDoc route response |
| `preview_packet` | Readable dict |
| `validator_result` | Readable dict |
| `blocked_reasons` | Readable list |

Observation:

- The current ZDoc `/local-trial/preview-only` route returns `preview_only=true` and `no_write=true`.
- The current ZDoc route response does not expose a top-level `no_evidence` field.
- No evidence write was observed, and the downstream ZBid receiver response did return `no_evidence=true`.

## 9. ZBid receiver endpoint result

The ZDoc outbound adapter was invoked with the ZDoc response fields and sent one payload to the configured receiver endpoint.

- Endpoint: `POST http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`
- HTTP status: `200`
- Uvicorn log:

```text
POST /local-llm/zdoc-preview-only/receive HTTP/1.1" 200 OK
```

ZDoc outbound adapter result:

| Field | Result |
| --- | --- |
| `outbound_status` | `sent_preview_only` |
| `ok` | `true` |
| `network_send_attempted` | `true` |
| `network_send_succeeded` | `true` |

ZBid receiver response:

| Field | Result |
| --- | --- |
| `status` | `accepted_preview_only` |
| `receiver_accepted` | `true` |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |
| `preview_packet` | Readable dict |
| `validator_result` | Readable dict |
| `blocked_reasons` | Readable list |

## 10. HTTP result summary

| Endpoint | Caller path | HTTP status | Result |
| --- | --- | --- | --- |
| `POST /local-trial/preview-only` | Explicit ZDoc endpoint smoke call | `200` | Returned preview packet, validator result, blocked reasons |
| `POST /local-llm/zdoc-preview-only/receive` | ZDoc outbound adapter network-send | `200` | Receiver accepted preview-only payload |

Effective smoke payload count: `1`.

Endpoint interactions:

- ZDoc endpoint call: `1`.
- ZBid receiver endpoint call via ZDoc outbound adapter: `1`.

## 11. preview-only / no-write / no-evidence review

| Scope | `preview_only` | `no_write` | `no_evidence` |
| --- | --- | --- | --- |
| ZDoc route response | `true` | `true` | Not present as top-level field |
| ZBid receiver response | `true` | `true` | `true` |

Conclusion:

- `preview_only=true` and `no_write=true` were confirmed in both the ZDoc route response and the ZBid receiver response.
- `no_evidence=true` was confirmed in the ZBid receiver response.
- The ZDoc route currently does not return a top-level `no_evidence` field; this is recorded as an observation for future review and does not indicate evidence generation.

## 12. Readability review

| Field | ZDoc route response | ZBid receiver response |
| --- | --- | --- |
| `blocked_reasons` | Readable | Readable |
| `validator_result` | Readable | Readable |
| `preview_packet` | Readable | Readable |

Blocked reasons observed:

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

## 13. Five forbidden flags review

ZBid receiver response:

| Flag | Result |
| --- | --- |
| `generate_called` | `false` |
| `export_docx_called` | `false` |
| `review_apply_called` | `false` |
| `zbid_writeback_called` | `false` |
| `output_job_export_written` | `false` |

All five forbidden flags were `false`.

## 14. Forbidden chain confirmation

The smoke did not trigger:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid writeback
- evidence generation
- scoring basis write
- storage write
- DOCX generation
- `output/job/export` write
- top local model upgrade
- 50-user formal deployment design

## 15. Ollama status

- Ollama was not run.
- Pre-start process check had no matching Ollama process output.
- Endpoint smoke did not call Ollama.

## 16. DOCX and output/job/export review

DOCX checks:

- ZDoc `git status --short -- '*.docx'`: empty.
- ZBid `git status --short -- '*.docx'`: empty.

`output/job/export` checks:

- ZDoc: `output/job/export` path missing.
- ZBid: `output/job/export` path missing.

No DOCX generation or `output/job/export` write was observed.

## 17. Service shutdown

Shutdown command:

```bash
kill 15090 15091
```

Shutdown scope:

- Only the two PIDs started by this step were targeted.
- No unknown process was killed.

Shutdown result:

- ZDoc shutdown log indicated application shutdown completed and server process `15090` finished.
- ZBid shutdown log indicated application shutdown completed and server process `15091` finished.

## 18. PID stop result

Post-shutdown check:

```bash
ps -p 15090,15091 -o pid,ppid,stat,command
```

Result:

```text
PID  PPID STAT COMMAND
```

Both PIDs were stopped.

## 19. Port release result

| Port | Post-shutdown check | Result |
| --- | --- | --- |
| `127.0.0.1:18766` | `lsof -nP -iTCP:18766 -sTCP:LISTEN` | No listener output |
| `127.0.0.1:18767` | `lsof -nP -iTCP:18767 -sTCP:LISTEN` | No listener output |

Both ports were released.

## 20. AI knowledge graph folder access statement

The paused folder was not accessed, scanned, read, copied, moved, analyzed, or identified:

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

No command in this step targeted that path.

## 21. Risks and observations

- The endpoint smoke succeeded for one effective preview-only request.
- ZDoc returned HTTP 200 and produced readable `preview_packet`, `validator_result`, and `blocked_reasons`.
- The ZDoc outbound adapter sent one preview-only payload to ZBid receiver.
- ZBid returned HTTP 200 and accepted the payload as preview-only / no-write / no-evidence.
- The current ZDoc route response does not include a top-level `no_evidence` field. Future review may decide whether to expose that field directly on the ZDoc route response.
- The smoke did not run a multi-user workload or long-running stability test.
- The host remains only a 20-user controlled pilot host, not a formal production server.

## 22. Step 271 recommendation

Step 271 is recommended only as a separately authorized docs-only review and next-step authorization request. It should not be entered automatically.

Recommended Step 271 direction:

- Archive Step 270 endpoint smoke results.
- Record the ZDoc top-level `no_evidence` field observation.
- Decide whether to authorize a follow-up docs-only review, a minimal response-field alignment request, or another controlled observation run.
- Preserve preview-only / no-write / no-evidence boundaries.
- Continue forbidding `/generate`, `/export_docx`, `/review/apply`, ZBid writeback, DOCX generation, and `output/job/export` writes unless separately authorized.

## 23. Step 271 authorization request draft

```text
执行 Step 271：ZDoc-ZBid preview-only endpoint smoke review and next-step authorization request

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<待填入 Step 270 结束后 HEAD>

特别说明：
用户已暂停 /Users/youfeini/Desktop/AI知识图谱大全 文件夹识别任务。本步骤不得访问、扫描、读取、复制、移动、分析或识别该文件夹。

授权范围：
仅 docs-only 归档 Step 270 preview-only endpoint smoke controlled execution 结果，并起草下一步授权请求。

严格边界：
1. 不修改代码 / tests / frontend / backend / 既有 docs；
2. 不运行 ZDoc / ZBid 服务；
3. 不运行 Ollama；
4. 不访问端口；
5. 不调用任何 endpoint；
6. 不发送 preview payload；
7. 不触发 /generate、/export_docx、/review/apply；
8. 不触发 ZBid 写回；
9. 不生成 DOCX；
10. 不写 output/job/export；
11. 不把 preview-only 结果作为 evidence；
12. 不把 preview-only 结果作为评分依据；
13. 不访问或识别 /Users/youfeini/Desktop/AI知识图谱大全；
14. 不进入 50 人正式部署设计；
15. 不实施顶级模型升级；
16. 不自动进入后续步骤。

文档必须说明：
1. Step 270 endpoint smoke 结果；
2. ZDoc / ZBid HTTP 状态；
3. ZDoc outbound adapter 是否发送；
4. ZBid receiver 是否接收；
5. preview_only / no_write / no_evidence 复核结果；
6. blocked_reasons / validator_result / preview_packet 可读性；
7. 五个禁止 flags 是否均为 false；
8. 未触发正式链、未生成 DOCX、未写 output/job/export；
9. ZDoc route 当前未返回 top-level no_evidence 字段的观察项；
10. 下一步是否需要 response-field alignment 授权请求。

完成后停止，不得进入下一步。
```
