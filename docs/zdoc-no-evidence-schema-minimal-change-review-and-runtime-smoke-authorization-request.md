# ZDoc no_evidence schema minimal change review and runtime smoke authorization request

## 1. Step 273 最小代码变更结果复盘

Step 273 已完成 ZDoc `POST /local-trial/preview-only` route 顶层 response schema 的最小代码变更。

本次变更目标是修正 Step 270 / Step 271 发现的 response schema 观察项：ZDoc route 顶层已返回 `preview_only=true`、`no_write=true`，但未在顶层显式返回 `no_evidence=true`。

Step 273 的实际处理结果：

- 在 ZDoc route 顶层 response 中补充 `no_evidence=true`。
- 保持既有 `preview_only=true`。
- 保持既有 `no_write=true`。
- 保持 `blocked_reasons` 可读。
- 保持 `validator_result` 可读。
- 保持 `preview_packet` 可读。
- 保持五个 no-write / no-formal-chain flags 为 false。
- 未改变 outbound adapter 的 preview-only / no-write / no-evidence 语义。
- 未改变 ZBid receiver payload 语义。
- 未改变正式业务链路。

## 2. 实际修改文件清单

Step 273 实际修改文件为：

- `backend/app/routers/local_trial_preview_only.py`
- `backend/tests/test_local_trial_preview_only_route.py`

未修改其他代码文件、frontend 文件、backend 主链路文件、既有 docs 文件或 ZBid 仓库文件。

## 3. route 顶层 response 新增 no_evidence=true 的变更说明

`backend/app/routers/local_trial_preview_only.py` 中，`local_trial_preview_only_route` 的顶层返回对象新增：

```text
no_evidence=true
```

该字段与既有顶层字段共同表达 ZDoc preview-only route 的安全边界：

- `preview_only=true` 表示仅为预览用途。
- `no_write=true` 表示不得写入正式业务数据、结果文件或写回链路。
- `no_evidence=true` 表示不得把 preview-only 结果作为正式 evidence。

本次只补齐顶层 response schema 的显示一致性，不改变 route 的业务执行路径，不增加正式链能力。

## 4. 必要测试补充说明

`backend/tests/test_local_trial_preview_only_route.py` 中，既有 `_assert_no_write_route_flags` 增加顶层断言：

```text
result["no_evidence"] is True
```

该断言与既有 `preview_only`、`no_write`、route name、endpoint path、formal flags false、no output/write/export、no Ollama、no external model API 等断言保持同一检查入口。

测试仍覆盖：

- route 返回 HTTP 200。
- 顶层 `preview_only=true`。
- 顶层 `no_write=true`。
- 顶层 `no_evidence=true`。
- `preview_packet` 为可读对象。
- `validator_result` 为可读对象。
- `blocked_reasons` 为可读列表。
- formal flags 在顶层、`preview_packet`、`validator_result` 中保持 false。
- 缺失 scoring refs 时仍仅 blocked，不写入。
- unsafe evidence request 仍被 blocked，不写入。
- formal requests 仍被 blocked，不触发正式链。
- route 模块不导入主生成链或写回模块。
- route 源码不调用正式 route、HTTP client 或 ZBid 写回逻辑。

## 5. targeted pytest 结果

Step 273 运行的 targeted test：

```bash
python -m pytest backend/tests/test_local_trial_preview_only_route.py -vv
```

结果：

```text
7 passed
```

该测试为本地 in-process TestClient route 单元测试。Step 273 未启动 ZDoc 服务、未启动 ZBid 服务、未访问端口、未调用 runtime endpoint、未发送 preview payload。

## 6. 未修改主生成链路的结论

Step 273 未修改主生成链路。

未修改范围包括但不限于：

- orchestration / generation 相关逻辑。
- LLM provider / client 相关逻辑。
- 正式生成任务链路。
- 正式证据链路。
- 正式评分链路。
- 正式导出链路。
- 正式写回链路。

本次变更仅限 ZDoc preview-only route 顶层 response schema 与必要测试断言。

## 7. 未修改 /generate、/export_docx、/review/apply 相关逻辑的结论

Step 273 未修改以下正式接口相关逻辑：

- `/generate`
- `/export_docx`
- `/review/apply`

Step 273 未触发这些接口，也未增加任何 fallback 到正式接口的路径。

## 8. 未修改 ZBid 文件的结论

Step 273 未修改 ZBid 仓库文件。

ZBid 仓库仍保持既有 preview-only receiver 行为边界：

- receiver 侧 `preview_only=true`。
- receiver 侧 `no_write=true`。
- receiver 侧 `no_evidence=true`。
- 不写回。
- 不生成 DOCX。
- 不写 output/job/export。

## 9. 未运行服务、未调用 runtime endpoint、未发送 preview payload 的边界说明

Step 273 的执行边界为最小代码变更与 targeted unit test。

Step 273 未发生：

- 未运行 ZDoc 服务。
- 未运行 ZBid 服务。
- 未运行 Ollama。
- 未访问端口。
- 未调用 `POST /local-trial/preview-only` runtime endpoint。
- 未调用 `POST /local-llm/zdoc-preview-only/receive` runtime endpoint。
- 未发送 preview payload。
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未把 preview-only 结果作为 evidence。
- 未把 preview-only 结果作为评分依据。

## 10. 当前已验证事项

当前已验证事项：

- ZDoc route 顶层 response schema 已补充 `no_evidence=true`。
- 顶层 `preview_only=true` 保持。
- 顶层 `no_write=true` 保持。
- `blocked_reasons` 仍可读。
- `validator_result` 仍可读。
- `preview_packet` 仍可读。
- 五个 no-write / no-formal-chain flags 均保持 false：
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- formal write/export/review/writeback flags 仍保持 false。
- unsafe evidence request 仍被 blocked。
- formal request 仍被 blocked。
- targeted pytest 通过，结果为 `7 passed`。
- `git diff --check` 通过。
- `git diff --cached --check` 通过。

## 11. 当前未验证事项

当前未验证事项：

- runtime endpoint smoke 尚未验证。
- ZDoc 服务启动后的真实 HTTP response 顶层 `no_evidence=true` 尚未通过 runtime 调用确认。
- ZBid receiver runtime 接收链路在本次 schema 变更后尚未复验。
- ZDoc -> ZBid preview-only runtime 联动在本次 schema 变更后尚未复验。
- 服务启动、端口监听、endpoint 调用、服务关闭、端口释放尚未在本阶段执行。

上述事项需要 Step 275 或后续步骤由用户明确授权后才能执行。

## 12. 风险与观察项

风险与观察项：

- 当前变更为 schema 显示一致性修正，风险较低。
- 当前测试已覆盖 in-process route response，但尚未覆盖 runtime HTTP smoke。
- runtime smoke 需要启动服务、访问端口、调用 preview-only endpoint，因此必须单独授权。
- 后续 runtime smoke 必须继续保持 preview-only / no-write / no-evidence。
- 后续 runtime smoke 不得触发正式生成、导出、review apply、ZBid 写回、DOCX 生成或 `output/job/export` 写入。
- 后续 runtime smoke 不得把 preview-only 结果作为 evidence 或评分依据。

## 13. 是否建议进入 Step 275

建议进入 Step 275，但仅限用户明确授权后执行。

建议理由：

- Step 273 已完成最小代码变更和 targeted unit test。
- 当前唯一未闭环项是 runtime endpoint smoke。
- Step 275 可用于验证 ZDoc 服务启动后的真实 HTTP response 顶层是否包含 `no_evidence=true`。
- Step 275 还可复核 ZDoc -> ZBid preview-only receiver 链路在本次 schema 修正后仍保持 no-write / no-evidence。

Step 275 不得默认执行，必须由用户单独授权。

## 14. Step 275 runtime preview-only endpoint smoke 授权请求草案

以下为可复制的 Step 275 授权请求草案。

```text
执行 Step 275：ZDoc no_evidence schema runtime preview-only endpoint smoke controlled execution

ZDoc 仓库：
/Users/youfeini/Desktop/文档生成系统

ZDoc 分支：
main

ZDoc 开始前 HEAD：
<以 Step 274 完成后 HEAD 为准>

ZBid 仓库：
/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean

ZBid 分支：
local-llm-integration-clean

ZBid 开始前 HEAD：
378355755372e03ac4f4064af59b287054984c25

授权范围：
1. 允许启动必要的 ZDoc 本地服务。
2. 允许启动必要的 ZBid 本地服务。
3. 允许访问必要本地端口。
4. 允许调用 ZDoc preview-only endpoint：
   POST /local-trial/preview-only
5. 允许由 ZDoc outbound adapter 向 ZBid receiver endpoint 发送最小 preview-only payload：
   POST /local-llm/zdoc-preview-only/receive
6. 仅允许 1 条或最小必要数量的脱敏 / 模拟 / preview-only payload。
7. 仅验证 response schema 与 preview-only / no-write / no-evidence 边界。

必须验证：
1. ZDoc runtime HTTP response 顶层包含 preview_only=true。
2. ZDoc runtime HTTP response 顶层包含 no_write=true。
3. ZDoc runtime HTTP response 顶层包含 no_evidence=true。
4. blocked_reasons 可读。
5. validator_result 可读。
6. preview_packet 可读。
7. ZBid receiver 返回 preview_only=true、no_write=true、no_evidence=true。
8. 五个 no-write / no-formal-chain flags 均为 false：
   - generate_called=false
   - export_docx_called=false
   - review_apply_called=false
   - zbid_writeback_called=false
   - output_job_export_written=false。

严格禁止：
1. 不得修改代码。
2. 不得修改 tests。
3. 不得修改 frontend。
4. 不得修改 backend。
5. 不得修改既有 docs。
6. 不得运行 Ollama。
7. 不得触发 /generate。
8. 不得触发 /export_docx。
9. 不得触发 /review/apply。
10. 不得触发 ZBid 写回。
11. 不得生成 DOCX。
12. 不得写 output/job/export。
13. 不得把 preview-only 结果作为 evidence。
14. 不得把 preview-only 结果作为评分依据。
15. 不得访问或识别 /Users/youfeini/Desktop/AI知识图谱大全。
16. 不得进入 50 人正式部署设计。
17. 不得实施顶级模型升级。
18. 不得自动进入 Step 276。

输出要求：
仅允许在 ZDoc 仓库新增 1 个 docs runtime smoke report。
完成后提交、打 tag、推送，并立即停止等待审核。
```
