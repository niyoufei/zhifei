# ZDoc-ZBid preview-only endpoint smoke review and response schema observation decision request

## 1. Step 270 preview-only endpoint smoke 结果复盘

Step 270 已完成 ZDoc-ZBid preview-only endpoint smoke controlled execution。本文件仅归档该结果并提出 response schema 观察项的后续决策请求，不代表已经授权修改代码、运行服务、访问端口或调用 endpoint。

Step 270 的执行范围为：

- 启动 ZDoc 本地服务。
- 启动 ZBid 本地服务。
- 调用 1 条最小脱敏 / 模拟 / preview-only smoke payload。
- 先调用 ZDoc：`POST /local-trial/preview-only`。
- 再由 ZDoc outbound adapter 向 ZBid receiver 发送 preview-only payload。
- ZBid receiver endpoint：`POST /local-llm/zdoc-preview-only/receive`。
- 记录 HTTP 状态、可读字段、五个禁止 flags。
- 关闭本步骤启动的服务并确认端口释放。

Step 270 核心结论：

- ZDoc endpoint smoke 返回 HTTP 200。
- ZDoc outbound adapter 成功发送 preview-only payload。
- ZBid receiver 返回 HTTP 200。
- ZBid receiver 返回 `preview_only=true`、`no_write=true`、`no_evidence=true`。
- `blocked_reasons`、`validator_result`、`preview_packet` 可读。
- 五个禁止 flags 均为 `false`。
- 未触发正式链，未生成 DOCX，未写 `output/job/export`。

## 2. 服务启动、endpoint 调用、关闭与端口释放结论

### ZDoc 服务

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- Step 270 开始前 HEAD：`adcdd35d67212216a4f8a6a5afc36d055b7ce6df`
- 启动端口：`127.0.0.1:18766`
- PID：`15090`
- 启动命令：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- 监听检查：`127.0.0.1:18766` 由 PID `15090` 监听。
- 关闭方式：对本步骤启动的 PID `15090` 发送正常 `TERM`。
- 关闭结果：服务进程结束。
- 端口释放：关闭后 `127.0.0.1:18766` 无监听。

### ZBid 服务

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- Step 270 开始前 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 启动端口：`127.0.0.1:18767`
- PID：`15091`
- 启动命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- 监听检查：`127.0.0.1:18767` 由 PID `15091` 监听。
- 关闭方式：对本步骤启动的 PID `15091` 发送正常 `TERM`。
- 关闭结果：服务进程结束。
- 端口释放：关闭后 `127.0.0.1:18767` 无监听。

## 3. ZDoc endpoint HTTP 200 结论

Step 270 调用了 1 次 ZDoc preview-only endpoint：

```text
POST http://127.0.0.1:18766/local-trial/preview-only
```

结果：

- HTTP 状态：`200`
- 返回 `preview_only=true`
- 返回 `no_write=true`
- 返回 `preview_packet`
- 返回 `validator_result`
- 返回 `blocked_reasons`

该调用使用脱敏 / 模拟 / preview-only payload，不包含真实投标 evidence，不产生评分依据，不写入正式业务数据。

## 4. ZBid receiver HTTP 200 结论

Step 270 中，ZDoc outbound adapter 使用 ZDoc 返回的 `preview_packet`、`validator_result`、`blocked_reasons` 构造 preview-only outbound payload，并调用：

```text
POST http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive
```

结果：

- HTTP 状态：`200`
- `outbound_status=sent_preview_only`
- `outbound_ok=true`
- `network_send_attempted=true`
- `network_send_succeeded=true`
- ZBid receiver `status=accepted_preview_only`
- ZBid receiver `receiver_accepted=true`

## 5. ZBid receiver preview-only / no-write / no-evidence 结论

ZBid receiver 侧返回结果成立：

| Field | Result |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

该结果确认 Step 270 的 ZBid receiver endpoint smoke 保持 preview-only / no-write / no-evidence 边界。

## 6. 可读性结论

Step 270 中以下字段可读：

| Field | ZDoc route response | ZBid receiver response |
| --- | --- | --- |
| `blocked_reasons` | 可读 | 可读 |
| `validator_result` | 可读 | 可读 |
| `preview_packet` | 可读 | 可读 |

观察到的 `blocked_reasons` 包括：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

这些 blocked reasons 用于人工复核 preview-only 边界，不得作为正式 evidence 或评分依据。

## 7. 五个禁止 flags 结论

ZBid receiver response 中五个禁止 flags 均为 `false`：

| Flag | Result |
| --- | --- |
| `generate_called` | `false` |
| `export_docx_called` | `false` |
| `review_apply_called` | `false` |
| `zbid_writeback_called` | `false` |
| `output_job_export_written` | `false` |

该结论不代表正式链开放，只说明本次 preview-only endpoint smoke 未触发这些正式链行为。

## 8. 禁止接口与写回复核结论

Step 270 未触发：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- evidence generation
- scoring basis write
- storage write
- top local model upgrade
- 50 人正式部署设计

Step 270 仅调用授权 preview-only endpoint：

- `POST /local-trial/preview-only`
- `POST /local-llm/zdoc-preview-only/receive`

未调用其他业务 endpoint。

## 9. DOCX 与 output/job/export 复核结论

Step 270 复核结果：

- 未生成 DOCX。
- ZDoc `git status --short -- '*.docx'` 为空。
- ZBid `git status --short -- '*.docx'` 为空。
- ZDoc `output/job/export` 路径缺失，未观察到写入。
- ZBid `output/job/export` 路径缺失，未观察到写入。

## 10. AI知识图谱大全 文件夹未访问声明

用户已暂停以下文件夹识别任务：

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

Step 270 未访问、扫描、读取、复制、移动、分析或识别该文件夹。本 Step 271 亦未访问、扫描、读取、复制、移动、分析或识别该文件夹。

## 11. response schema 观察项

Step 270 发现一个 response schema 显示一致性观察项：

- ZDoc `POST /local-trial/preview-only` 顶层返回 `preview_only=true`。
- ZDoc `POST /local-trial/preview-only` 顶层返回 `no_write=true`。
- ZDoc `POST /local-trial/preview-only` 顶层未返回 `no_evidence` 字段。
- ZBid receiver response 返回 `preview_only=true`、`no_write=true`、`no_evidence=true`。

该观察项的性质：

- 属于响应字段可读性 / schema 显示一致性问题。
- 不属于写入问题。
- 不属于 evidence 生成问题。
- 不属于评分依据写入问题。
- 不属于 ZBid 写回问题。
- 不表示 preview-only / no-write / no-evidence 安全边界被突破。

## 12. 安全边界确认

虽然 ZDoc route 顶层未返回 `no_evidence` 字段，但 Step 270 未发现 evidence 生成或写入迹象：

- ZDoc route 返回 `preview_only=true`。
- ZDoc route 返回 `no_write=true`。
- ZDoc route 返回的 `blocked_reasons` 包含 `preview_only_is_not_evidence`。
- ZBid receiver 返回 `no_evidence=true`。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未触发正式证据链。
- 未触发评分依据写入。

因此，该观察项未突破 preview-only / no-write / no-evidence 安全边界。

## 13. 后续处理选项

### 选项 A：继续作为观察项，仅在 docs 中说明

- 不修改代码。
- 不修改 tests。
- 继续在操作手册、smoke 报告和后续 stage review 中说明：
  - ZDoc 顶层当前返回 `preview_only=true`、`no_write=true`。
  - ZDoc 顶层当前未返回 `no_evidence`。
  - ZBid receiver 侧返回 `no_evidence=true`。
- 适用于暂不调整 response schema 的情形。

### 选项 B：后续单独发起代码最小变更

可单独申请授权，在 ZDoc `/local-trial/preview-only` route 顶层补充：

```json
{
  "no_evidence": true
}
```

建议边界：

- 仅允许最小修改 ZDoc route response schema。
- 仅允许修改直接相关测试。
- 不修改正式生成链、导出链、review apply 链、ZBid 写回链。
- 不启动服务、不访问端口、不调用 endpoint，除非后续另行授权 smoke。

### 选项 C：后续增加 response schema smoke 测试方案

可先起草 docs-only 测试方案，明确后续如需验证：

- ZDoc route 顶层 `preview_only=true`。
- ZDoc route 顶层 `no_write=true`。
- ZDoc route 顶层 `no_evidence=true`。
- ZBid receiver `preview_only=true`、`no_write=true`、`no_evidence=true`。
- 五个禁止 flags 均为 `false`。

该方案本身仍不代表授权执行代码修改或 runtime smoke。

## 14. 风险与观察项

- Step 270 endpoint smoke 只执行 1 条有效 preview-only payload，不代表多用户并发或长期稳定性结论。
- ZDoc 顶层缺少 `no_evidence` 字段可能影响人工复核时的字段一致性。
- 当前观察项应作为 response schema 显示一致性问题管理，不应扩大解释为安全边界失效。
- 后续若要补齐字段，应单独授权最小代码变更与最小测试。
- 后续若要再次 runtime 验证，应单独授权服务启动、端口访问和 endpoint 调用。

## 15. 是否建议进入 Step 272

建议进入 Step 272，但仅建议作为单独授权请求或 docs-only 设计步骤，不得自动进入。

推荐 Step 272 方向：

- 起草 ZDoc preview-only response schema alignment authorization request。
- 或起草 response schema smoke test plan。
- 目标仅限解决或管理 ZDoc route 顶层 `no_evidence` 字段显示一致性观察项。
- 继续保持 preview-only / no-write / no-evidence。
- 继续禁止正式链、写回链、DOCX、`output/job/export` 和 50 人正式部署设计。

## 16. Step 272 授权请求草案

```text
执行 Step 272：ZDoc preview-only response schema alignment authorization request

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<待填入 Step 271 结束后 HEAD>

特别说明：
用户已暂停 /Users/youfeini/Desktop/AI知识图谱大全 文件夹识别任务。本步骤不得访问、扫描、读取、复制、移动、分析或识别该文件夹。

任务性质：
ZDoc docs-only / authorization-request-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
基于 Step 270 endpoint smoke 和 Step 271 stage review，起草 ZDoc preview-only response schema alignment 授权请求。该请求仅用于后续申请明确授权，不代表已经允许修改代码。

拟申请后续最小变更范围：
1. 仅允许在 ZDoc /local-trial/preview-only route 顶层响应中补充 no_evidence=true；
2. 仅允许同步修改直接相关测试；
3. 不得修改正式生成链、导出链、review apply 链、ZBid 写回链；
4. 不得改变 preview_packet、validator_result、blocked_reasons 的既有含义；
5. 不得新增写入行为；
6. 不得生成 DOCX；
7. 不得写 output/job/export。

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
13. 不进入 50 人正式部署设计；
14. 不实施顶级模型升级。

完成后停止，不得进入下一步。
```
