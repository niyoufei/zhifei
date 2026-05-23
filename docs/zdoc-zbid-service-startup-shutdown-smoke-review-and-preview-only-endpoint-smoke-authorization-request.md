# ZDoc-ZBid service startup-shutdown smoke review and preview-only endpoint smoke authorization request

## 1. Step 268 服务启动关闭 smoke 结果复盘

Step 268 已完成 ZDoc-ZBid 20-user service startup-shutdown smoke controlled execution。本次复盘仅基于 Step 268 已归档报告，不代表本步重新启动服务、访问端口或调用 endpoint。

Step 268 的验证范围为：

- 启动 ZDoc 本地服务。
- 启动 ZBid 本地服务。
- 使用 `lsof` / `ps` 只读检查监听与进程状态。
- 记录服务 PID。
- 关闭本步骤启动的服务。
- 检查 PID 停止与端口释放。
- 不发起 HTTP 请求。
- 不调用任何业务 endpoint。
- 不发送 preview payload。

Step 268 结论：

- ZDoc 服务可在授权端口启动并监听。
- ZBid 服务可在授权端口启动并监听。
- 两侧服务均可关闭。
- 两个授权端口均已释放。
- 未触发正式链、写回链、DOCX 生成或 `output/job/export` 写入。

## 2. ZDoc / ZBid 服务启动、监听、PID、关闭与端口释放结论

### ZDoc

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- Step 268 开始前 HEAD：`e53b7ed06f305ff01e836b6092040a4babc15279`
- 启动命令：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- 端口：`127.0.0.1:18766`
- PID：`11240`
- 监听检查：`lsof -nP -iTCP:18766 -sTCP:LISTEN` 显示 PID `11240` 监听。
- 关闭方式：对本步骤启动的 PID `11240` 发送正常 `TERM`。
- 关闭结果：应用 shutdown complete，server process `11240` finished。
- 端口释放：`127.0.0.1:18766` 关闭后无监听输出。

### ZBid

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- Step 268 开始前 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 启动命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- 端口：`127.0.0.1:18767`
- PID：`11241`
- 监听检查：`lsof -nP -iTCP:18767 -sTCP:LISTEN` 显示 PID `11241` 监听。
- 关闭方式：对本步骤启动的 PID `11241` 发送正常 `TERM`。
- 关闭结果：应用 shutdown complete，server process `11241` finished。
- 端口释放：`127.0.0.1:18767` 关闭后无监听输出。

## 3. endpoint 与 preview payload 边界确认

Step 268 明确未调用任何 endpoint：

- 未调用 ZDoc endpoint。
- 未调用 ZBid endpoint。
- 未调用 `POST /local-trial/preview-only`。
- 未调用 `POST /local-llm/zdoc-preview-only/receive`。
- 未调用 `/generate`。
- 未调用 `/export_docx`。
- 未调用 `/review/apply`。

Step 268 明确未发送任何 preview payload：

- 未发送 `preview_packet`。
- 未发送 `validator_result`。
- 未发送 `blocked_reasons`。
- 未发送 no-write / no-formal-chain flags payload。
- 未进行 ZDoc -> ZBid preview-only payload 发送。

## 4. 禁止接口、禁止写入与 DOCX 复核结论

Step 268 复核结论：

- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未创建 evidence。
- 未写入评分依据。
- 未进入 50 人正式部署设计。
- 未实施顶级模型升级。

`output/job/export` 检查结果：

- ZDoc：`output/job/export` 路径缺失，未观察到写入。
- ZBid：`output/job/export` 路径缺失，未观察到写入。

DOCX 检查结果：

- ZDoc `git status --short -- '*.docx'` 为空。
- ZBid `git status --short -- '*.docx'` 为空。

## 5. AI知识图谱大全 文件夹未访问声明

用户已暂停以下文件夹识别任务：

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

Step 268 未访问、扫描、读取、复制、移动、分析或识别该文件夹。本 Step 269 亦不得访问、扫描、读取、复制、移动、分析或识别该文件夹。

## 6. 当前已验证能力清单

当前已验证能力仅限以下范围：

1. ZDoc 仓库在授权 HEAD 下可启动本地服务。
2. ZBid 仓库在授权 HEAD 下可启动本地 receiver 服务。
3. ZDoc 服务可监听 `127.0.0.1:18766`。
4. ZBid 服务可监听 `127.0.0.1:18767`。
5. 两侧服务均可通过本步骤记录的 PID 正常关闭。
6. 两侧服务关闭后授权端口均可释放。
7. 在不调用 endpoint 的情况下，服务启动关闭 smoke 未产生 DOCX。
8. 在不调用 endpoint 的情况下，服务启动关闭 smoke 未写 `output/job/export`。
9. 在不调用 endpoint 的情况下，服务启动关闭 smoke 未触发正式生成、导出、review apply 或 ZBid 写回。

## 7. 当前未验证能力清单

当前仍未验证以下能力：

1. ZDoc `POST /local-trial/preview-only` 在本轮服务启动后的 endpoint 可达性。
2. ZBid `POST /local-llm/zdoc-preview-only/receive` 在本轮服务启动后的 endpoint 可达性。
3. ZDoc outbound adapter 在本轮服务启动后的 preview-only payload 发送行为。
4. ZBid receiver 在本轮服务启动后的 preview-only payload 接收行为。
5. `preview_only=true`、`no_write=true`、`no_evidence=true` 在本轮 endpoint smoke 中的返回状态。
6. `preview_packet`、`validator_result`、`blocked_reasons` 在本轮 endpoint smoke 中的可读性。
7. 五个 no-write / no-formal-chain flags 在本轮 endpoint smoke 中是否均为 false：
   - `generate_called=false`
   - `export_docx_called=false`
   - `review_apply_called=false`
   - `zbid_writeback_called=false`
   - `output_job_export_written=false`
8. endpoint 调用后的 `output/job/export` 前后快照。
9. endpoint 调用后的 DOCX 生成迹象复核。
10. endpoint 调用后的禁止接口触发复核。

## 8. 风险与观察项

- Step 268 只验证服务启动、监听、关闭和端口释放，不验证 endpoint 行为。
- Step 268 未发送 preview payload，因此不能作为 ZDoc -> ZBid payload 链路的新增验证依据。
- 后续如进入 endpoint smoke，必须单独授权服务启动、端口访问和指定 preview-only endpoint 调用。
- 后续 endpoint smoke 必须继续保持 preview-only / no-write / no-evidence。
- 后续 endpoint smoke 不得扩大到正式生成、DOCX 导出、review apply、ZBid 写回或任何正式业务链。
- 主机仍仅可定位为 20 人受控试运行主机，不得视为长期正式生产服务器。

## 9. Step 270 前置条件判断

基于 Step 268 结果，当前满足起草 Step 270 preview-only endpoint smoke controlled execution 授权请求的前置条件：

- ZDoc 服务启动与关闭 smoke 已通过。
- ZBid 服务启动与关闭 smoke 已通过。
- 授权端口在关闭后已释放。
- 本轮未发现服务启动关闭层面的阻断问题。
- 本轮未触发禁止接口、preview payload、DOCX 生成、`output/job/export` 写入或写回。

但 Step 270 尚未授权，也不得在本步骤执行。Step 270 若被授权，应只允许受控调用 preview-only endpoint，并继续禁止正式链。

## 10. Step 270 授权请求草案

```text
执行 Step 270：ZDoc-ZBid preview-only endpoint smoke controlled execution

ZDoc 仓库：
/Users/youfeini/Desktop/文档生成系统

ZDoc 分支：
main

ZDoc 开始前 HEAD：
<待填入 Step 269 结束后 HEAD>

ZBid 仓库：
/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean

ZBid 分支：
local-llm-integration-clean

ZBid 开始前 HEAD：
378355755372e03ac4f4064af59b287054984c25

授权范围：
1. 允许启动必要的 ZDoc 本地服务；
2. 允许启动必要的 ZBid 本地服务；
3. 允许访问授权本地端口；
4. 仅允许调用 preview-only endpoint：
   - ZDoc preview-only 入口，如需使用必须限定为 preview-only；
   - ZBid POST /local-llm/zdoc-preview-only/receive；
5. 允许发送最小 preview-only payload；
6. 允许记录 endpoint smoke 报告；
7. 仅允许在 ZDoc 仓库新增 1 个 docs 报告文件。

严格边界：
1. 不修改代码 / tests / frontend / backend / 既有 docs；
2. 不运行 Ollama；
3. 不触发 /generate；
4. 不触发 /export_docx；
5. 不触发 /review/apply；
6. 不触发 ZBid 写回；
7. 不生成 DOCX；
8. 不写 output/job/export；
9. 不把 preview-only 结果作为 evidence；
10. 不把 preview-only 结果作为评分依据；
11. 不访问、扫描、读取、复制、移动、分析或识别 /Users/youfeini/Desktop/AI知识图谱大全；
12. 不进入 50 人正式部署设计；
13. 不实施顶级模型升级；
14. 不自动进入后续步骤。

验证目标：
1. ZDoc / ZBid 服务可启动；
2. 授权 preview-only endpoint 可达；
3. preview-only payload 可发送与接收；
4. 返回 preview_only=true、no_write=true、no_evidence=true；
5. preview_packet、validator_result、blocked_reasons 可读；
6. 五个禁止 flags 均为 false；
7. 未生成 DOCX；
8. 未写 output/job/export；
9. 未触发正式链；
10. 服务结束后关闭并确认端口释放。

完成后停止，不得进入下一步。
```
