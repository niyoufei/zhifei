# ZDoc-ZBid post-schema-closure regression smoke controlled execution report

## 1. Step 278 执行摘要

- Step: Step 278 - ZDoc-ZBid post-schema-closure regression smoke controlled execution.
- 执行时间: 2026-05-23 14:51:42 CST.
- 回归目标: 在 no_evidence schema 观察项关闭后，验证 ZDoc -> ZBid preview-only 链路未退化。
- 有效 smoke payload 数量: `3`.
- payload 类型:
  1. 标准 preview-only 请求。
  2. 角色类 preview-only 请求。
  3. 边界但合法的 preview-only 请求。
- 未做非法枚举校准。
- 未做大批量压测。
- ZDoc 服务已启动于 `127.0.0.1:18766`。
- ZBid 服务已启动于 `127.0.0.1:18767`。
- 每条 payload 均调用 ZDoc:
  - `POST /local-trial/preview-only`
- 每条 payload 均由 ZDoc outbound adapter 发送至 ZBid receiver:
  - `POST /local-llm/zdoc-preview-only/receive`
- 3 条 ZDoc HTTP 结果均为 `200`。
- 3 条 ZBid receiver HTTP 结果均为 `200`。
- 3 条 ZDoc route 顶层 `preview_only=true`、`no_write=true`、`no_evidence=true` 均成立。
- 3 条 ZBid receiver 侧 `preview_only=true`、`no_write=true`、`no_evidence=true` 均成立。
- `blocked_reasons`、`validator_result`、`preview_packet` 均可读。
- 五个禁止 flags 均为 `false`。
- 未发现较 Step 275 退化。
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
| ZDoc HEAD | `9be802a1c6f096d991fd8f3f7d3314f85e159315` |
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

## 3. ZDoc / ZBid 仓库、分支、HEAD、git status

### ZDoc

- 仓库路径: `/Users/youfeini/Desktop/文档生成系统`
- 授权分支: `main`
- 授权开始前 HEAD: `9be802a1c6f096d991fd8f3f7d3314f85e159315`
- 实际核验 HEAD: `9be802a1c6f096d991fd8f3f7d3314f85e159315`
- 启动前 `git status --short`: 空
- 关闭服务后、生成报告前 `git status --short`: 空

### ZBid

- 仓库路径: `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 授权分支: `local-llm-integration-clean`
- 授权开始前 HEAD: `378355755372e03ac4f4064af59b287054984c25`
- 实际核验 HEAD: `378355755372e03ac4f4064af59b287054984c25`
- 启动前 `git status --short`: 空
- 关闭服务后 `git status --short`: 空

## 4. 服务启动命令、端口、PID

### ZDoc

启动命令:

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- 端口: `127.0.0.1:18766`
- PID: `31959`

### ZBid

启动命令:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- 端口: `127.0.0.1:18767`
- PID: `31956`

## 5. 端口监听检查结果

启动后端口监听检查:

| 端口 | 命令 | 结果 |
| --- | --- | --- |
| `127.0.0.1:18766` | `lsof -nP -iTCP:18766 -sTCP:LISTEN` | PID `31959` listening |
| `127.0.0.1:18767` | `lsof -nP -iTCP:18767 -sTCP:LISTEN` | PID `31956` listening |

进程核验:

```text
31956 ... Python -m uvicorn app.main:app --host 127.0.0.1 --port 18767
31959 ... Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

## 6. 3 条 preview-only smoke payload 说明

本次回归 smoke 使用 3 条脱敏 / 模拟 / preview-only payload。

| 序号 | 场景 | 说明 |
| --- | --- | --- |
| 1 | 标准 preview-only 请求 | 常规 preview-only payload，包含有效 tender refs、scoring refs、evidence anchor refs。 |
| 2 | 角色类 preview-only 请求 | 模拟技术标编制人员角色场景，仍保持 preview-only / no-write / no-evidence。 |
| 3 | 边界但合法的 preview-only 请求 | 使用短 section title 和合法 refs，验证边界但合法输入不造成 schema 退化。 |

统一约束:

- 均为脱敏 / 模拟数据。
- 均不包含真实投标 evidence。
- 均不产生评分依据。
- 均不生成 DOCX。
- 均不发送 writeback 数据。
- 所有 evidence-as-formal flags 均为 `false`。
- 所有 writeback / DOCX / review apply / output write requests 均为 `false`。
- 未执行非法枚举校准。
- 未执行大批量压测。

## 7. ZDoc POST /local-trial/preview-only 调用结果

| 序号 | 场景 | HTTP 状态 | 顶层 `preview_only` | 顶层 `no_write` | 顶层 `no_evidence` |
| --- | --- | --- | --- | --- | --- |
| 1 | 标准 preview-only 请求 | `200` | `true` | `true` | `true` |
| 2 | 角色类 preview-only 请求 | `200` | `true` | `true` | `true` |
| 3 | 边界但合法的 preview-only 请求 | `200` | `true` | `true` | `true` |

ZDoc uvicorn 日志摘要:

```text
POST /local-trial/preview-only HTTP/1.1" 200 OK
POST /local-trial/preview-only HTTP/1.1" 200 OK
POST /local-trial/preview-only HTTP/1.1" 200 OK
```

ZDoc route response 可读性:

- 3 条 `blocked_reasons` 均为可读 list。
- 3 条 `validator_result` 均为可读 dict。
- 3 条 `preview_packet` 均为可读 dict。
- 3 条 `preview_packet.zbid_input_status` 均为 `accepted_preview_only`。
- 3 条 `validator_result.zbid_preview_validation_status` 均为 `accepted_preview_only`。

## 8. ZBid POST /local-llm/zdoc-preview-only/receive 接收结果

| 序号 | 场景 | HTTP 状态 | `receiver_accepted` | `preview_only` | `no_write` | `no_evidence` |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 标准 preview-only 请求 | `200` | `true` | `true` | `true` | `true` |
| 2 | 角色类 preview-only 请求 | `200` | `true` | `true` | `true` | `true` |
| 3 | 边界但合法的 preview-only 请求 | `200` | `true` | `true` | `true` | `true` |

ZBid uvicorn 日志摘要:

```text
POST /local-llm/zdoc-preview-only/receive HTTP/1.1" 200 OK
POST /local-llm/zdoc-preview-only/receive HTTP/1.1" 200 OK
POST /local-llm/zdoc-preview-only/receive HTTP/1.1" 200 OK
```

ZDoc outbound adapter 结果:

| 序号 | `ok` | `outbound_status` | `network_send_attempted` | `network_send_succeeded` |
| --- | --- | --- | --- | --- |
| 1 | `true` | `sent_preview_only` | `true` | `true` |
| 2 | `true` | `sent_preview_only` | `true` | `true` |
| 3 | `true` | `sent_preview_only` | `true` | `true` |

## 9. HTTP 状态汇总

| Endpoint | 调用方式 | 次数 | HTTP 状态 |
| --- | --- | --- | --- |
| `POST /local-trial/preview-only` | 显式 ZDoc preview-only endpoint smoke 调用 | `3` | 全部 `200` |
| `POST /local-llm/zdoc-preview-only/receive` | ZDoc outbound adapter network-send | `3` | 全部 `200` |

有效 smoke payload 数量: `3`。

endpoint interaction 数量: `6`。

## 10. ZDoc route 顶层 preview_only / no_write / no_evidence 复核结果

| 字段 | 3 条回归 smoke 结果 |
| --- | --- |
| `preview_only` | 全部 `true` |
| `no_write` | 全部 `true` |
| `no_evidence` | 全部 `true` |

结论:

- ZDoc route 顶层 `no_evidence=true` 在 3 条回归 smoke 中持续成立。
- 与 Step 275 相比，未发现 schema 退化。

## 11. ZBid receiver 侧 preview_only / no_write / no_evidence 复核结果

| 字段 | 3 条回归 smoke 结果 |
| --- | --- |
| `preview_only` | 全部 `true` |
| `no_write` | 全部 `true` |
| `no_evidence` | 全部 `true` |

结论:

- ZBid receiver 侧三项状态在 3 条回归 smoke 中持续成立。
- ZDoc schema 观察项关闭后，ZBid receiver preview-only / no-write / no-evidence 语义未退化。

## 12. blocked_reasons、validator_result、preview_packet 可读性结果

| 字段 | ZDoc route response | ZBid receiver response |
| --- | --- | --- |
| `blocked_reasons` | 3 条均可读 | 3 条均可读 |
| `validator_result` | 3 条均可读 | 3 条均可读 |
| `preview_packet` | 3 条均可读 | 3 条均可读 |

3 条 smoke 均观察到以下 blocked reasons:

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

这些字段仅用于 preview-only 边界说明与人工复核，不得作为正式 evidence，不得作为评分依据。

## 13. 五个禁止 flags 复核结果

ZBid receiver response 中五个禁止 flags:

| Flag | 3 条回归 smoke 结果 |
| --- | --- |
| `generate_called` | 全部 `false` |
| `export_docx_called` | 全部 `false` |
| `review_apply_called` | 全部 `false` |
| `zbid_writeback_called` | 全部 `false` |
| `output_job_export_written` | 全部 `false` |

结论: 五个禁止 flags 均为 `false`，未发现较 Step 275 退化。

## 14. 是否存在较 Step 275 退化

未发现较 Step 275 退化。

对比结论:

| 项目 | Step 275 | Step 278 |
| --- | --- | --- |
| 有效 payload 数量 | `1` | `3` |
| ZDoc HTTP | `200` | 全部 `200` |
| ZBid HTTP | `200` | 全部 `200` |
| ZDoc 顶层 `preview_only/no_write/no_evidence` | 全部成立 | 全部成立 |
| ZBid receiver `preview_only/no_write/no_evidence` | 全部成立 | 全部成立 |
| 字段可读性 | 成立 | 成立 |
| 五个禁止 flags | 全部 `false` | 全部 `false` |
| DOCX 生成 | 未发生 | 未发生 |
| `output/job/export` 写入 | 未发生 | 未发生 |
| 服务关闭与端口释放 | 成立 | 成立 |

## 15. 未触发禁止接口和写回链路

本次回归 smoke 未触发:

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- 正式 evidence 生成
- 评分依据写入
- 正式业务数据写入
- 顶级本地模型升级
- 50 人正式部署设计

本次仅调用授权 preview-only endpoint:

- `POST /local-trial/preview-only`
- `POST /local-llm/zdoc-preview-only/receive`

## 16. 未运行 Ollama

本次回归 smoke 未运行 Ollama。

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

## 19. 服务关闭方式、PID 停止结果、端口释放结果

关闭方式:

```bash
kill 31959 31956
```

说明:

- `31959` 为本步骤启动的 ZDoc uvicorn 进程。
- `31956` 为本步骤启动的 ZBid uvicorn 进程。
- 两个 uvicorn 进程均完成 shutdown。

关闭后 PID 检查:

```text
PID COMMAND
```

结论:

- PID `31959` 已停止。
- PID `31956` 已停止。

关闭后端口检查:

| 端口 | 命令 | 结果 |
| --- | --- | --- |
| `127.0.0.1:18766` | `lsof -nP -iTCP:18766 -sTCP:LISTEN` | 无监听 |
| `127.0.0.1:18767` | `lsof -nP -iTCP:18767 -sTCP:LISTEN` | 无监听 |

结论: 两个端口均已释放。

## 20. AI知识图谱大全 文件夹未访问声明

本步骤未访问、扫描、读取、复制、移动、分析或识别以下文件夹:

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

## 21. 风险与观察项

风险与观察项:

- 本次回归 smoke 仅验证 3 条脱敏 / 模拟 / preview-only payload。
- 本次回归 smoke 不代表正式生成链开放。
- 本次回归 smoke 不代表正式 evidence 开放。
- 本次回归 smoke 不代表评分依据写入开放。
- 本次回归 smoke 不代表 DOCX 导出开放。
- 本次回归 smoke 不代表 review/apply 开放。
- 本次回归 smoke 不代表 ZBid 写回开放。
- 本次回归 smoke 不代表 50 人正式部署设计开放。
- 后续若继续常态试运行，仍应保持 preview-only / no-write / no-evidence 和五个禁止 flags 复核。
- 后续若做更大样本回归，应单独授权，并继续区分有效请求、前置校准和非法枚举阻断。

## 22. 是否建议进入 Step 279

建议进入 Step 279，但仅限用户明确授权后执行。

建议理由:

- no_evidence schema 观察项已经完成 Step 273 最小代码变更、Step 275 runtime smoke、Step 278 三条 payload 回归 smoke。
- 当前未发现较 Step 275 退化。
- 下一步可做 regression smoke stage review / baseline consolidation，将 3 条回归结果纳入 20 人受控常态试运行基线。

Step 279 不得自动执行，必须由用户单独授权。

## 23. Step 279 授权请求草案

以下为可复制的 Step 279 授权请求草案。

```text
执行 Step 279：ZDoc-ZBid post-schema-closure regression smoke stage review

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<以 Step 278 完成后 HEAD 为准>

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
15. 不得自动进入 Step 280。

任务：
仅新增 1 个 docs 文件，归档 Step 278 post-schema-closure regression smoke 结果。

文档必须说明：
1. Step 278 的 3 条 preview-only payload 回归结果；
2. ZDoc HTTP 结果全部为 200；
3. ZBid HTTP 结果全部为 200；
4. ZDoc route 顶层 preview_only=true、no_write=true、no_evidence=true 全部成立；
5. ZBid receiver 侧 preview_only=true、no_write=true、no_evidence=true 全部成立；
6. blocked_reasons、validator_result、preview_packet 均可读；
7. 五个禁止 flags 均为 false；
8. 未发现较 Step 275 退化；
9. 未运行 Ollama；
10. 未触发 /generate、/export_docx、/review/apply、ZBid 写回；
11. 未生成 DOCX；
12. 未写 output/job/export；
13. 服务已关闭，端口已释放；
14. 风险与下一步建议。

完成后提交、打 tag、推送，并立即停止等待审核。
```
