# ZDoc no_evidence schema runtime smoke review and schema observation closure archive

## 1. Step 270 至 Step 275 观察项处理链路复盘

本文件归档 ZDoc `POST /local-trial/preview-only` 顶层 `no_evidence` response schema 观察项的处理链路与关闭结论。

处理链路如下：

1. Step 270 完成 ZDoc-ZBid preview-only endpoint smoke controlled execution。
2. Step 270 发现 ZDoc route 顶层返回 `preview_only=true`、`no_write=true`，但未返回顶层 `no_evidence` 字段。
3. Step 270 同时验证 ZBid receiver 侧返回 `preview_only=true`、`no_write=true`、`no_evidence=true`。
4. Step 271 将该差异归档为 response schema 可读性 / 显示一致性观察项。
5. Step 272 起草最小变更授权请求，限定只补齐 ZDoc route 顶层 `no_evidence=true`。
6. Step 273 在授权范围内完成最小代码变更与 targeted pytest。
7. Step 274 归档 Step 273 最小代码变更结果，并申请 runtime smoke 授权。
8. Step 275 完成 runtime preview-only endpoint smoke，验证 ZDoc 顶层 `no_evidence=true` 已在真实 HTTP response 中成立。

该链路仅处理 response schema 显示一致性问题，不代表正式链开放，不代表 evidence 生成，不代表评分依据写入，不代表 ZBid 写回开放。

## 2. 原观察项：ZDoc route 顶层缺少 no_evidence 字段

原观察项来自 Step 270 runtime smoke：

- ZDoc `POST /local-trial/preview-only` 返回 HTTP `200`。
- ZDoc route 顶层返回 `preview_only=true`。
- ZDoc route 顶层返回 `no_write=true`。
- ZDoc route 顶层未返回 `no_evidence` 字段。
- ZDoc route 返回 `blocked_reasons`、`validator_result`、`preview_packet`。
- ZBid receiver 返回 HTTP `200`。
- ZBid receiver 返回 `preview_only=true`、`no_write=true`、`no_evidence=true`。
- 五个禁止 flags 均为 `false`。

Step 271 已明确该观察项性质：

- 属于 response schema 可读性 / 显示一致性问题。
- 不属于写入问题。
- 不属于 evidence 生成问题。
- 不属于评分依据写入问题。
- 不属于 ZBid 写回问题。
- 未突破 preview-only / no-write / no-evidence 安全边界。

## 3. Step 273 最小代码变更说明

Step 273 已完成最小代码变更。

实际修改文件：

- `backend/app/routers/local_trial_preview_only.py`
- `backend/tests/test_local_trial_preview_only_route.py`

变更说明：

- 在 ZDoc `POST /local-trial/preview-only` route 顶层 response 中补充 `no_evidence=true`。
- 在 route 相关 targeted test 中增加顶层 `no_evidence` 断言。
- 保持既有 `preview_only=true`。
- 保持既有 `no_write=true`。
- 保持 `blocked_reasons`、`validator_result`、`preview_packet` 可读。
- 保持五个 no-write / no-formal-chain flags 为 `false`。

Step 273 未修改：

- 主生成链路。
- `/generate` 相关逻辑。
- `/export_docx` 相关逻辑。
- `/review/apply` 相关逻辑。
- output / job / export 写入链路。
- ZBid 仓库文件。
- frontend 文件。
- 既有 docs 文件。

## 4. Step 273 targeted pytest 结果

Step 273 运行的 targeted test：

```bash
python -m pytest backend/tests/test_local_trial_preview_only_route.py -vv
```

结果：

```text
7 passed
```

该测试为本地 in-process TestClient route 单元测试。Step 273 未启动 ZDoc 服务、未启动 ZBid 服务、未访问端口、未调用 runtime endpoint、未发送 preview payload。

## 5. Step 275 runtime smoke 验证结果

Step 275 已完成 runtime preview-only endpoint smoke。

执行范围：

- 启动 ZDoc 本地服务。
- 启动 ZBid 本地服务。
- 调用 1 条脱敏 / 模拟 / preview-only smoke payload。
- 调用 ZDoc endpoint：
  - `POST /local-trial/preview-only`
- 由 ZDoc outbound adapter 调用 ZBid receiver endpoint：
  - `POST /local-llm/zdoc-preview-only/receive`
- 关闭本步骤启动的 ZDoc / ZBid 服务。
- 确认端口释放。

Step 275 HTTP 结果：

| Endpoint | HTTP 状态 | 调用次数 |
| --- | --- | --- |
| `POST /local-trial/preview-only` | `200` | `1` |
| `POST /local-llm/zdoc-preview-only/receive` | `200` | `1` |

Step 275 服务结果：

- ZDoc 服务端口：`127.0.0.1:18766`
- ZDoc 服务 PID：`25833`
- ZBid 服务端口：`127.0.0.1:18767`
- ZBid 服务 PID：`25830`
- 服务关闭方式：`kill 25833 25830`
- 关闭后 `127.0.0.1:18766` 无监听。
- 关闭后 `127.0.0.1:18767` 无监听。

## 6. ZDoc 顶层 preview_only / no_write / no_evidence 均为 true 的结论

Step 275 已验证 ZDoc runtime HTTP response 顶层字段：

| 字段 | 结果 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

结论：

- ZDoc route 顶层 `no_evidence=true` 已在 runtime endpoint smoke 中验证通过。
- Step 270 / Step 271 记录的顶层 `no_evidence` 缺失观察项已完成 runtime 闭环。
- `preview_only=true` 与 `no_write=true` 未发生退化。

## 7. ZBid receiver 侧 preview_only / no_write / no_evidence 均为 true 的结论

Step 275 已验证 ZBid receiver response：

| 字段 | 结果 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

结论：

- ZBid receiver 仍保持 preview-only / no-write / no-evidence。
- Step 273 的 ZDoc route schema 最小变更未造成 ZBid receiver 语义退化。
- ZDoc -> ZBid preview-only 链路在本次 schema 修正后仍可达，且保持 no-write / no-evidence 边界。

## 8. blocked_reasons / validator_result / preview_packet 可读性结论

Step 275 已验证以下字段可读：

| 字段 | ZDoc route response | ZBid receiver response |
| --- | --- | --- |
| `blocked_reasons` | 可读 list | 可读 list |
| `validator_result` | 可读 dict | 可读 dict |
| `preview_packet` | 可读 dict | 可读 dict |

已观察到的 blocked reasons 包括：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

这些字段仅用于 preview-only 人工复核和边界提示，不得作为正式 evidence，不得作为评分依据。

## 9. 五个禁止 flags 均为 false 的结论

Step 275 已验证 ZBid receiver response 中五个禁止 flags 均为 `false`：

| Flag | 结果 |
| --- | --- |
| `generate_called` | `false` |
| `export_docx_called` | `false` |
| `review_apply_called` | `false` |
| `zbid_writeback_called` | `false` |
| `output_job_export_written` | `false` |

结论：

- 未触发生成链。
- 未触发 DOCX 导出链。
- 未触发 review/apply 链。
- 未触发 ZBid 写回链。
- 未写 `output/job/export`。

## 10. 未触发 /generate、/export_docx、/review/apply、ZBid 写回的结论

Step 275 未触发以下禁止接口或链路：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- 正式 evidence 生成
- 评分依据写入
- 正式业务数据写入
- 顶级本地模型升级
- 50 人正式部署设计

Step 275 仅调用授权 preview-only endpoint：

- `POST /local-trial/preview-only`
- `POST /local-llm/zdoc-preview-only/receive`

## 11. 未生成 DOCX、未写 output/job/export 的结论

Step 275 复核结果：

| 仓库 | DOCX 启动前 | DOCX 关闭后 | `output/job/export` |
| --- | --- | --- | --- |
| ZDoc | `223` | `223` | `output`、`job`、`export` 均不存在 |
| ZBid | `0` | `0` | `output`、`job`、`export` 均不存在 |

结论：

- 未生成新的 DOCX。
- 未写 `output/job/export`。
- 未产生 storage write。
- 未产生正式成果输出。

## 12. 观察项关闭结论

原观察项：

```text
ZDoc route 顶层缺少 no_evidence 字段。
```

关闭依据：

- Step 273 已完成最小代码变更，ZDoc route 顶层补充 `no_evidence=true`。
- Step 273 targeted pytest 通过，结果为 `7 passed`。
- Step 275 runtime smoke 已验证 ZDoc HTTP response 顶层 `no_evidence=true`。
- Step 275 runtime smoke 已验证 ZDoc 顶层 `preview_only=true`、`no_write=true` 未退化。
- Step 275 runtime smoke 已验证 ZBid receiver 侧 `preview_only=true`、`no_write=true`、`no_evidence=true` 未退化。
- Step 275 runtime smoke 已验证五个禁止 flags 均为 `false`。
- Step 275 未触发正式链、未生成 DOCX、未写 `output/job/export`。

关闭结论：

```text
ZDoc route top-level no_evidence schema observation: closed.
```

该关闭结论仅针对 response schema 显示一致性观察项，不代表开放正式 evidence、评分依据、DOCX 导出、review/apply、ZBid 写回或正式生产部署。

## 13. 对 20 人受控常态试运行基线的影响

对 20 人受控常态试运行基线的影响：

- 正向影响：ZDoc route 顶层状态字段现在与 ZBid receiver 的 `preview_only / no_write / no_evidence` 三项显示保持一致。
- 人工复核更直接：管理员和试运行人员可直接从 ZDoc route 顶层 response 读取 `no_evidence=true`。
- 安全边界未放宽：仍保持 preview-only / no-write / no-evidence。
- 正式链未开放：`/generate`、`/export_docx`、`/review/apply`、ZBid 写回仍禁止。
- 输出边界未变化：仍不得生成 DOCX，仍不得写 `output/job/export`。
- 证据化与评分化边界未变化：preview-only 结果仍不得作为 evidence，仍不得作为评分依据。

对既有 20 人试运行基线的归档建议：

- 后续常态试运行记录中，应将 ZDoc 顶层 `no_evidence=true` 纳入日常复核项。
- 后续 smoke / observation report 中，应区分 ZDoc 顶层三项状态和 ZBid receiver 三项状态。
- 后续如发现任一状态字段缺失或非 true，应按暂停条件处理，不得现场修复，必须另行授权。

## 14. 后续仍需保持的边界

后续仍需保持以下边界：

- 必须保持 `preview_only=true`。
- 必须保持 `no_write=true`。
- 必须保持 `no_evidence=true`。
- 必须保持五个禁止 flags 为 `false`：
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得触发 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。
- 不得把 preview-only 结果作为 evidence。
- 不得把 preview-only 结果作为评分依据。
- 不得进入 50 人正式部署设计。
- 不得实施顶级模型升级。
- 未授权时不得启动服务、访问端口或调用 endpoint。

用户已暂停以下文件夹识别任务，后续步骤仍不得访问、扫描、读取、复制、移动、分析或识别：

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

## 15. 是否建议进入 Step 277

建议进入 Step 277，但仅限用户明确授权后执行。

建议理由：

- no_evidence schema 观察项已完成代码最小修正、targeted pytest 与 runtime smoke 闭环。
- 20 人受控常态试运行基线可吸收该字段作为日常复核项。
- 下一步更合理的是归档或更新 20 人受控常态试运行的 schema baseline / administrator checklist，而不是进入正式生产部署。

Step 277 不得自动执行，必须由用户单独授权。

## 16. Step 277 授权请求草案

以下为可复制的 Step 277 授权请求草案。

```text
执行 Step 277：ZDoc-ZBid 20-user controlled routine baseline no_evidence schema update archive

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<以 Step 276 完成后 HEAD 为准>

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
15. 不得自动进入 Step 278。

任务：
仅新增 1 个 docs 文件，归档 no_evidence schema 观察项关闭后对 20 人受控常态试运行基线、管理员检查表和后续观察期记录模板的影响。

文档必须说明：
1. Step 270 至 Step 276 的 no_evidence schema 观察项闭环；
2. ZDoc 顶层 preview_only / no_write / no_evidence 均为 true 的 runtime 结论；
3. ZBid receiver 侧 preview_only / no_write / no_evidence 均为 true 的 runtime 结论；
4. 五个禁止 flags 均为 false 的结论；
5. 20 人受控常态试运行中新增或强化的日常复核字段；
6. 管理员每日启动前、运行中、关闭后如何记录 no_evidence；
7. 仍需保持的 preview-only / no-write / no-evidence 边界；
8. 仍禁止 /generate、/export_docx、/review/apply、ZBid 写回、DOCX 生成、output/job/export 写入、证据化、评分化；
9. 风险与后续建议。

完成后提交、打 tag、推送，并立即停止等待审核。
```
