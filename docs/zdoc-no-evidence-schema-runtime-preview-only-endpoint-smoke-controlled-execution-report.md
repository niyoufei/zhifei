# ZDoc no_evidence schema runtime preview-only endpoint smoke controlled execution report

## 1. Step 275 执行摘要

- Step: Step 275 - ZDoc no_evidence schema runtime preview-only endpoint smoke controlled execution.
- 执行时间: 2026-05-23 14:35:49 CST.
- 范围: 1 条有效脱敏 / 模拟 / preview-only smoke payload.
- ZDoc 服务已在 `127.0.0.1:18766` 启动。
- ZBid 服务已在 `127.0.0.1:18767` 启动。
- 已调用 ZDoc preview-only endpoint:
  - `POST http://127.0.0.1:18766/local-trial/preview-only`
- ZDoc route 顶层返回:
  - `preview_only=true`
  - `no_write=true`
  - `no_evidence=true`
- 已使用 ZDoc outbound adapter 将同一条 preview-only payload 发送至 ZBid receiver:
  - `POST http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`
- ZBid receiver 返回:
  - HTTP `200`
  - `preview_only=true`
  - `no_write=true`
  - `no_evidence=true`
- `blocked_reasons`、`validator_result`、`preview_packet` 均可读。
- 五个禁止 flags 均为 `false`。
- 未运行 Ollama。
- 未触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 服务已关闭，端口已释放。

## 2. 启动前环境检查结果

| 检查项 | 结果 |
| --- | --- |
| ZDoc 仓库 | `/Users/youfeini/Desktop/文档生成系统` |
| ZDoc 分支 | `main` |
| ZDoc HEAD | `1f850fa0aee6dd63ffc7e04e0e3b378197710a06` |
| ZDoc `git status --short` | 空 |
| ZBid 仓库 | `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean` |
| ZBid 分支 | `local-llm-integration-clean` |
| ZBid HEAD | `378355755372e03ac4f4064af59b287054984c25` |
| ZBid `git status --short` | 空 |
| `127.0.0.1:18766` 启动前监听 | 无监听 |
| `127.0.0.1:18767` 启动前监听 | 无监听 |
| 疑似残留 ZDoc / ZBid 服务进程 | 未发现非检查命令自身的残留服务进程 |
| Ollama 运行进程 | 未发现非检查命令自身的 Ollama 运行进程 |
| ZDoc `output/job/export` | `output`、`job`、`export` 均不存在 |
| ZBid `output/job/export` | `output`、`job`、`export` 均不存在 |
| ZDoc DOCX 数量 | 启动前 `223` |
| ZBid DOCX 数量 | 启动前 `0` |

## 3. ZDoc 仓库路径、分支、HEAD、git status

- 仓库路径: `/Users/youfeini/Desktop/文档生成系统`
- 授权分支: `main`
- 授权开始前 HEAD: `1f850fa0aee6dd63ffc7e04e0e3b378197710a06`
- 实际核验 HEAD: `1f850fa0aee6dd63ffc7e04e0e3b378197710a06`
- 启动前 `git status --short`: 空
- 关闭服务后、生成报告前 `git status --short`: 空

## 4. ZBid 仓库路径、分支、HEAD、git status

- 仓库路径: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 授权分支: `local-llm-integration-clean`
- 授权开始前 HEAD: `378355755372e03ac4f4064af59b287054984c25`
- 实际核验 HEAD: `378355755372e03ac4f4064af59b287054984c25`
- 启动前 `git status --short`: 空
- 关闭服务后 `git status --short`: 空

## 5. 服务启动命令、端口、PID

### ZDoc

启动命令:

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- 端口: `127.0.0.1:18766`
- PID: `25833`

### ZBid

启动命令:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- 端口: `127.0.0.1:18767`
- PID: `25830`

## 6. 端口监听检查结果

启动后端口监听检查:

| 端口 | 命令 | 结果 |
| --- | --- | --- |
| `127.0.0.1:18766` | `lsof -nP -iTCP:18766 -sTCP:LISTEN` | PID `25833` listening |
| `127.0.0.1:18767` | `lsof -nP -iTCP:18767 -sTCP:LISTEN` | PID `25830` listening |

进程核验:

```text
25830 ... Python -m uvicorn app.main:app --host 127.0.0.1 --port 18767
25833 ... Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

## 7. 最小 preview-only payload 说明

本次 smoke 使用 1 条脱敏 / 模拟 / preview-only payload。

payload 特征:

- `integration_request_id`: `step-275-no-evidence-runtime-smoke-001`
- `source_system`: `zdoc`
- `target_system`: `zbid`
- `project_id`: `project-step-275-preview-only`
- `document_id`: `doc-step-275-preview-only`
- `section_id`: `section-step-275-preview-only`
- `section_title`: `Step 275 No Evidence Schema Runtime Smoke Section`
- `response_mode`: `preview_advisory`
- `zbid_preview_mode`: `preview_only`
- 所有 evidence-as-formal flags 均为 `false`。
- 所有 writeback / DOCX / review apply / output write requests 均为 `false`。
- 未使用真实投标 evidence。
- 未生成评分依据。
- 未发送 DOCX。
- 未发送 writeback 数据。

## 8. ZDoc POST /local-trial/preview-only 调用结果

- Endpoint: `POST http://127.0.0.1:18766/local-trial/preview-only`
- 调用次数: `1`
- HTTP 状态: `200`
- Uvicorn 日志:

```text
POST /local-trial/preview-only HTTP/1.1" 200 OK
```

ZDoc route 顶层 response 复核:

| 字段 | 结果 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |
| `blocked_reasons` | 可读 list |
| `validator_result` | 可读 dict |
| `preview_packet` | 可读 dict |

blocked reasons:

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

结论:

- Step 273 新增的 ZDoc route 顶层 `no_evidence=true` 已通过 runtime endpoint smoke 验证。
- `preview_only=true`、`no_write=true` 未退化。
- `blocked_reasons`、`validator_result`、`preview_packet` 仍可读。

## 9. ZBid POST /local-llm/zdoc-preview-only/receive 接收结果

ZDoc outbound adapter 使用 ZDoc route response 中的 `preview_packet`、`validator_result`、`blocked_reasons` 发送 1 条 preview-only payload 至 ZBid receiver。

- Endpoint: `POST http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`
- 调用次数: `1`
- HTTP 状态: `200`
- Uvicorn 日志:

```text
POST /local-llm/zdoc-preview-only/receive HTTP/1.1" 200 OK
```

ZDoc outbound adapter 结果:

| 字段 | 结果 |
| --- | --- |
| `ok` | `true` |
| `outbound_status` | `sent_preview_only` |
| `http_status` | `200` |
| `network_send_attempted` | `true` |
| `network_send_succeeded` | `true` |

ZBid receiver response:

| 字段 | 结果 |
| --- | --- |
| `status` | `accepted_preview_only` |
| `receiver_accepted` | `true` |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |
| `blocked_reasons` | 可读 list |
| `validator_result` | 可读 dict |
| `preview_packet` | 可读 dict |

## 10. HTTP 状态汇总

| Endpoint | 调用方式 | 次数 | HTTP 状态 |
| --- | --- | --- | --- |
| `POST /local-trial/preview-only` | 显式 ZDoc preview-only endpoint smoke 调用 | `1` | `200` |
| `POST /local-llm/zdoc-preview-only/receive` | ZDoc outbound adapter network-send | `1` | `200` |

有效 smoke payload 数量: `1`。

## 11. ZDoc route 顶层 preview_only / no_write / no_evidence 复核结果

| 字段 | 结果 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

结论:

- ZDoc route 顶层 `no_evidence=true` 已在 runtime HTTP response 中验证通过。
- Step 270 / Step 271 记录的顶层 `no_evidence` 缺失观察项已通过 Step 273 最小变更在 runtime 层闭环。

## 12. ZBid receiver 侧 preview_only / no_write / no_evidence 复核结果

| 字段 | 结果 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

结论:

- ZBid receiver 仍保持 preview-only / no-write / no-evidence。
- Step 273 的 ZDoc route schema 变更未造成 ZBid receiver 语义退化。

## 13. blocked_reasons、validator_result、preview_packet 可读性结果

| 字段 | ZDoc route response | ZBid receiver response |
| --- | --- | --- |
| `blocked_reasons` | 可读 list | 可读 list |
| `validator_result` | 可读 dict | 可读 dict |
| `preview_packet` | 可读 dict | 可读 dict |

## 14. 五个禁止 flags 复核结果

ZBid receiver response 中五个禁止 flags:

| Flag | 结果 |
| --- | --- |
| `generate_called` | `false` |
| `export_docx_called` | `false` |
| `review_apply_called` | `false` |
| `zbid_writeback_called` | `false` |
| `output_job_export_written` | `false` |

结论: 五个禁止 flags 均为 `false`。

## 15. 未触发禁止接口和写回链路

本次 smoke 未触发:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- 正式 evidence 生成
- 评分依据写入
- DOCX 生成
- `output/job/export` 写入

## 16. 未运行 Ollama

本次 smoke 未运行 Ollama。

启动前残留进程检查未发现非检查命令自身的 Ollama 运行进程。

## 17. 未生成 DOCX

DOCX 数量复核:

| 仓库 | 启动前 | 关闭后 |
| --- | --- | --- |
| ZDoc | `223` | `223` |
| ZBid | `0` | `0` |

结论: 未生成新的 DOCX。

## 18. 未写 output/job/export

关闭后复核:

| 仓库 | 结果 |
| --- | --- |
| ZDoc | `output`、`job`、`export` 均不存在 |
| ZBid | `output`、`job`、`export` 均不存在 |

结论: 未写 `output/job/export`。

## 19. 服务关闭方式

关闭方式:

```bash
kill 25833 25830
```

说明:

- `25833` 为本步骤启动的 ZDoc uvicorn 进程。
- `25830` 为本步骤启动的 ZBid uvicorn 进程。
- 两个 uvicorn 进程均完成 shutdown。

ZDoc shutdown 日志:

```text
Shutting down
Waiting for application shutdown.
Application shutdown complete.
Finished server process [25833]
```

ZBid shutdown 日志:

```text
Shutting down
Waiting for application shutdown.
Application shutdown complete.
Finished server process [25830]
```

## 20. PID 停止结果

关闭后 PID 检查:

```text
PID COMMAND
```

结论:

- PID `25833` 已停止。
- PID `25830` 已停止。

## 21. 端口释放结果

关闭后端口检查:

| 端口 | 命令 | 结果 |
| --- | --- | --- |
| `127.0.0.1:18766` | `lsof -nP -iTCP:18766 -sTCP:LISTEN` | 无监听 |
| `127.0.0.1:18767` | `lsof -nP -iTCP:18767 -sTCP:LISTEN` | 无监听 |

结论: 两个端口均已释放。

## 22. AI知识图谱大全 文件夹未访问声明

本步骤未访问、扫描、读取、复制、移动、分析或识别以下文件夹:

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

## 23. 风险与观察项

风险与观察项:

- 本次 smoke 仅验证 1 条最小脱敏 / 模拟 / preview-only payload。
- 本次 smoke 不代表正式生成链开放。
- 本次 smoke 不代表正式 evidence 开放。
- 本次 smoke 不代表评分依据写入开放。
- 本次 smoke 不代表 DOCX 导出开放。
- 本次 smoke 不代表 review/apply 开放。
- 本次 smoke 不代表 ZBid 写回开放。
- 本次 smoke 不代表 50 人正式部署设计开放。
- 后续若继续常态试运行，仍应保持 preview-only / no-write / no-evidence 和五个禁止 flags 复核。

## 24. 是否建议进入 Step 276

建议进入 Step 276，但仅限用户明确授权后执行。

建议理由:

- Step 273 最小 schema 变更已通过 targeted unit test。
- Step 275 runtime endpoint smoke 已验证 ZDoc 顶层 `no_evidence=true`。
- ZDoc -> ZBid preview-only receiver 链路仍返回 HTTP 200。
- ZBid receiver 侧 preview-only / no-write / no-evidence 与五个 false flags 未退化。
- 下一步可归档本次 runtime smoke 的 stage review，并明确仍未开放正式链。

## 25. Step 276 授权请求草案

以下为可复制的 Step 276 授权请求草案。

```text
执行 Step 276：ZDoc no_evidence schema runtime smoke stage review

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<以 Step 275 完成后 HEAD 为准>

特别说明：
用户已暂停 /Users/youfeini/Desktop/AI知识图谱大全 文件夹识别任务。本步骤不得访问、扫描、读取、复制、移动或分析该文件夹。

严格边界：
1. docs-only；
2. 不得修改代码 / tests / frontend / backend / 既有 docs；
3. 不得运行 ZDoc / ZBid 服务；
4. 不得运行 Ollama；
5. 不得访问端口；
6. 不得调用任何 endpoint；
7. 不得发送 preview payload；
8. 不得触发 /generate、/export_docx、/review/apply；
9. 不得触发 ZBid 写回；
10. 不得生成 DOCX；
11. 不得写 output/job/export；
12. 不得把 preview-only 结果作为 evidence 或评分依据；
13. 不得进入 50 人正式部署设计；
14. 不得实施顶级模型升级；
15. 不得自动进入 Step 277。

任务：
仅新增 1 个 docs 文件，归档 Step 275 runtime preview-only endpoint smoke 结果。

文档必须说明：
1. Step 275 启动 ZDoc / ZBid 服务、端口、PID、关闭与释放结果；
2. ZDoc POST /local-trial/preview-only HTTP 200；
3. ZDoc route 顶层 preview_only=true、no_write=true、no_evidence=true；
4. ZBid POST /local-llm/zdoc-preview-only/receive HTTP 200；
5. ZBid receiver 侧 preview_only=true、no_write=true、no_evidence=true；
6. blocked_reasons、validator_result、preview_packet 可读；
7. 五个禁止 flags 均为 false；
8. 未运行 Ollama；
9. 未触发 /generate、/export_docx、/review/apply、ZBid 写回；
10. 未生成 DOCX；
11. 未写 output/job/export；
12. 未访问 AI知识图谱大全 文件夹；
13. 风险与下一步建议。

完成后提交、打 tag、推送，并立即停止等待审核。
```
