# ZDoc-ZBid schema observation closure baseline update and regression authorization request

## 1. Step 270 至 Step 276 处理链路摘要

本文件基于 Step 270 至 Step 276 的处理结果，归档 ZDoc-ZBid preview-only schema 观察项关闭后的基线更新，并起草 Step 278 回归验证授权请求。

处理链路摘要：

1. Step 270 完成 ZDoc-ZBid preview-only endpoint smoke controlled execution。
2. Step 270 发现 ZDoc `POST /local-trial/preview-only` route 顶层返回 `preview_only=true`、`no_write=true`，但未返回顶层 `no_evidence` 字段。
3. Step 270 同时验证 ZBid receiver 侧 `preview_only=true`、`no_write=true`、`no_evidence=true`，且五个禁止 flags 均为 `false`。
4. Step 271 将该差异归档为 response schema 可读性 / 显示一致性观察项。
5. Step 272 起草最小变更授权请求，建议仅补齐 ZDoc route 顶层 `no_evidence=true`。
6. Step 273 已按授权完成最小代码变更和 targeted pytest。
7. Step 274 已归档 Step 273 最小代码变更结果，并起草 runtime smoke 授权请求。
8. Step 275 已完成 runtime preview-only endpoint smoke，验证 ZDoc 顶层 `no_evidence=true` 已在真实 HTTP response 中成立。
9. Step 276 已归档 no_evidence schema 观察项关闭结论。

本处理链路仅关闭 response schema 显示一致性观察项，不代表正式链开放，不代表 evidence 生成，不代表评分依据写入，不代表 DOCX 导出，不代表 ZBid 写回。

## 2. no_evidence 顶层字段观察项关闭结论

原观察项：

```text
ZDoc route 顶层缺少 no_evidence 字段。
```

关闭依据：

- Step 273 已在 ZDoc route 顶层 response 中补充 `no_evidence=true`。
- Step 273 targeted pytest 通过，结果为 `7 passed`。
- Step 275 runtime smoke 已验证 ZDoc HTTP response 顶层 `no_evidence=true`。
- Step 275 runtime smoke 已验证 ZDoc 顶层 `preview_only=true`、`no_write=true` 未退化。
- Step 275 runtime smoke 已验证 ZBid receiver 侧 `preview_only=true`、`no_write=true`、`no_evidence=true` 未退化。
- Step 275 runtime smoke 已验证五个禁止 flags 均为 `false`。
- Step 275 未触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
- Step 275 未生成 DOCX。
- Step 275 未写 `output/job/export`。

关闭结论：

```text
ZDoc route top-level no_evidence schema observation: closed.
```

该关闭结论仅针对 schema 显示一致性问题，不改变 preview-only / no-write / no-evidence 安全边界。

## 3. Step 273 最小代码变更纳入基线的说明

Step 273 的最小代码变更应纳入后续 ZDoc-ZBid preview-only 基线。

纳入基线的变更：

- `backend/app/routers/local_trial_preview_only.py`
  - ZDoc `POST /local-trial/preview-only` route 顶层 response 返回 `no_evidence=true`。
- `backend/tests/test_local_trial_preview_only_route.py`
  - targeted route test 增加顶层 `no_evidence` 断言。

纳入基线后的含义：

- ZDoc route 顶层 response 应稳定包含 `preview_only=true`。
- ZDoc route 顶层 response 应稳定包含 `no_write=true`。
- ZDoc route 顶层 response 应稳定包含 `no_evidence=true`。
- 该字段只表达 preview-only 结果不得作为 evidence，不开放任何正式 evidence 链。
- 后续回归、试运行、管理员检查表和观察期记录应将该字段作为固定复核项。

不纳入本次基线的范围：

- 不开放 `/generate`。
- 不开放 `/export_docx`。
- 不开放 `/review/apply`。
- 不开放 ZBid 写回。
- 不开放 DOCX 生成。
- 不开放 `output/job/export` 写入。
- 不开放 preview-only 结果证据化或评分化。

## 4. Step 275 runtime smoke 验证结论

Step 275 runtime smoke 已完成 1 条有效脱敏 / 模拟 / preview-only payload 验证。

服务与调用结果：

| 项目 | 结果 |
| --- | --- |
| ZDoc 服务 | 启动于 `127.0.0.1:18766`，PID `25833` |
| ZBid 服务 | 启动于 `127.0.0.1:18767`，PID `25830` |
| ZDoc endpoint | `POST /local-trial/preview-only` |
| ZDoc HTTP 状态 | `200` |
| ZBid receiver endpoint | `POST /local-llm/zdoc-preview-only/receive` |
| ZBid HTTP 状态 | `200` |
| 有效 smoke payload | `1` 条 |
| 服务关闭 | 已关闭 |
| 端口释放 | `18766` / `18767` 均无监听 |

Step 275 验证结论：

- ZDoc route 顶层 `preview_only=true`。
- ZDoc route 顶层 `no_write=true`。
- ZDoc route 顶层 `no_evidence=true`。
- ZBid receiver 侧 `preview_only=true`。
- ZBid receiver 侧 `no_write=true`。
- ZBid receiver 侧 `no_evidence=true`。
- `blocked_reasons`、`validator_result`、`preview_packet` 可读。
- 五个禁止 flags 均为 `false`。
- 未触发正式链。
- 未生成 DOCX。
- 未写 `output/job/export`。

## 5. 当前 ZDoc route 顶层 response 基线

当前 ZDoc `POST /local-trial/preview-only` route 顶层 response 基线为：

| 字段 | 基线值 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

该三项字段应作为后续 preview-only runtime smoke、20 人受控常态试运行和观察期记录的固定复核项。

若后续任一字段缺失或非 `true`：

- 应立即记录为异常或回归风险。
- 不得现场修复。
- 不得 fallback 到正式接口。
- 不得扩大调用范围。
- 必须等待单独授权后再处理。

## 6. ZBid receiver 侧 preview_only / no_write / no_evidence 仍成立的结论

Step 275 已确认 ZBid receiver response：

| 字段 | 结果 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

结论：

- ZBid receiver 仍保持 preview-only / no-write / no-evidence。
- ZDoc route 顶层 schema 修正未改变 ZBid receiver payload 语义。
- ZDoc -> ZBid preview-only 链路仍保持 no-write / no-evidence。

## 7. blocked_reasons / validator_result / preview_packet 可读性基线

当前可读性基线：

| 字段 | ZDoc route response | ZBid receiver response |
| --- | --- | --- |
| `blocked_reasons` | 可读 list | 可读 list |
| `validator_result` | 可读 dict | 可读 dict |
| `preview_packet` | 可读 dict | 可读 dict |

后续回归验证应继续确认：

- `blocked_reasons` 可读，并可用于人工复核。
- `validator_result` 可读，并保持 preview-only validator 语义。
- `preview_packet` 可读，并不包含正式 evidence、正式评分依据、DOCX 或 writeback 数据。

`blocked_reasons` 仅用于边界说明和人工复核，不得作为正式 evidence，不得作为评分依据。

## 8. 五个禁止 flags 均为 false 的基线

当前 no-write / no-formal-chain flags 基线：

| Flag | 基线值 |
| --- | --- |
| `generate_called` | `false` |
| `export_docx_called` | `false` |
| `review_apply_called` | `false` |
| `zbid_writeback_called` | `false` |
| `output_job_export_written` | `false` |

后续任何 preview-only smoke、试运行或观察期验证均必须复核上述五项。

若任一 flag 非 `false`：

- 立即停止本轮验证或试运行。
- 记录异常。
- 不得继续发送 payload。
- 不得现场修复。
- 不得进入正式链。
- 等待单独授权后再处理。

## 9. 对 20 人受控常态试运行手册、preflight 清单、观察期基线的影响

本次 schema 观察项关闭后，对 20 人受控常态试运行基线产生以下影响。

### 9.1 对运行手册的影响

后续 20 人受控常态试运行手册应将 ZDoc 顶层 `no_evidence=true` 纳入固定复核项。

建议管理员运行中记录：

- ZDoc 顶层 `preview_only=true`。
- ZDoc 顶层 `no_write=true`。
- ZDoc 顶层 `no_evidence=true`。
- ZBid receiver 侧 `preview_only=true`。
- ZBid receiver 侧 `no_write=true`。
- ZBid receiver 侧 `no_evidence=true`。
- 五个禁止 flags 均为 `false`。

### 9.2 对 preflight 清单的影响

后续 preflight 清单中，启动前仍不应调用 endpoint，但应提示管理员在获得 runtime smoke 或试运行授权后检查：

- ZDoc route 顶层三项状态字段。
- ZBid receiver 三项状态字段。
- `blocked_reasons`、`validator_result`、`preview_packet` 可读性。
- 五个禁止 flags。

preflight 本身仍应保持只读，除非用户另行授权启动服务、访问端口或调用 endpoint。

### 9.3 对观察期基线的影响

后续观察期记录模板应增加或强化：

- ZDoc top-level `no_evidence` 字段记录。
- ZDoc / ZBid 双侧 no-evidence 对照。
- 任一 no-evidence 缺失或非 true 时的暂停条件。
- 禁止将 preview-only 结果证据化或评分化的复核声明。

## 10. 当前仍不得进入事项

当前仍不得进入以下事项：

- 50 人正式部署。
- 正式生产服务器定位。
- 顶级本地模型升级。
- 正式 evidence 开放。
- preview-only 结果证据化。
- 正式评分依据写入。
- preview-only 结果评分化。
- ZBid 写回。
- `/generate`。
- `/export_docx`。
- `/review/apply`。
- DOCX 生成。
- `output/job/export` 写入。
- 未授权的服务启动。
- 未授权的端口访问。
- 未授权的 endpoint 调用。

用户已暂停以下文件夹识别任务，后续仍不得访问、扫描、读取、复制、移动、分析或识别：

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

## 11. 建议的 Step 278 回归验证范围

建议 Step 278 作为 ZDoc-ZBid no_evidence schema regression controlled smoke。

建议范围：

- 启动 ZDoc 本地服务。
- 启动 ZBid 本地服务。
- 使用少量脱敏 / 模拟 / preview-only payload。
- 调用授权的 preview-only endpoint。
- 验证 ZDoc route 顶层 `no_evidence=true`。
- 验证 ZDoc route 顶层 `preview_only=true`、`no_write=true`。
- 验证 ZBid receiver 侧 `no_evidence=true`。
- 验证 ZBid receiver 侧 `preview_only=true`、`no_write=true`。
- 验证 `blocked_reasons`、`validator_result`、`preview_packet` 可读。
- 验证五个禁止 flags 均为 `false`。
- 关闭服务。
- 确认 PID 停止。
- 确认端口释放。
- 确认未生成 DOCX。
- 确认未写 `output/job/export`。

建议 payload 数量：

- 少量即可，建议 `3` 条以内。
- 必须全部为脱敏 / 模拟 / preview-only。
- 不得使用真实投标 evidence。
- 不得生成评分依据。
- 不得发送 DOCX。
- 不得发送 writeback 数据。

## 12. 风险与观察项

风险与观察项：

- Step 275 已验证 1 条最小 runtime smoke，但尚未做多 payload 回归。
- 后续回归验证应控制 payload 数量，避免扩大为常态试运行或压力测试。
- 后续回归验证仍需严格区分有效 preview-only request 与任何前置校准。
- 后续回归验证不得把 preview-only 结果作为 evidence。
- 后续回归验证不得把 preview-only 结果作为评分依据。
- 后续如发现字段缺失或 flags 异常，应停止并记录，不得现场修复。
- 当前主机仍只可作为 20 人受控试运行主机，不得定位为长期正式生产服务器。

## 13. Step 278 授权请求草案

以下为可复制的 Step 278 授权请求草案。

```text
执行 Step 278：ZDoc-ZBid no_evidence schema regression controlled smoke

ZDoc 仓库：
/Users/youfeini/Desktop/文档生成系统

ZDoc 分支：
main

ZDoc 开始前 HEAD：
<以 Step 277 完成后 HEAD 为准>

ZBid 仓库：
/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean

ZBid 分支：
local-llm-integration-clean

ZBid 开始前 HEAD：
378355755372e03ac4f4064af59b287054984c25

特别说明：
用户已暂停 /Users/youfeini/Desktop/AI知识图谱大全 文件夹识别任务。本步骤不得访问、扫描、读取、复制、移动或分析该文件夹。

授权范围：
1. 允许启动必要的 ZDoc 本地服务。
2. 允许启动必要的 ZBid 本地服务。
3. 允许访问必要本地端口。
4. 允许调用授权的 preview-only endpoint。
5. 允许发送少量脱敏 / 模拟 / preview-only payload，建议不超过 3 条。
6. 允许临时启用 preview-only network-send。
7. 允许记录 runtime 回归报告。
8. 仅允许在 ZDoc 仓库新增 1 个 docs 报告文件。

必须验证：
1. ZDoc route 顶层 preview_only=true。
2. ZDoc route 顶层 no_write=true。
3. ZDoc route 顶层 no_evidence=true。
4. ZBid receiver 侧 preview_only=true。
5. ZBid receiver 侧 no_write=true。
6. ZBid receiver 侧 no_evidence=true。
7. blocked_reasons 可读。
8. validator_result 可读。
9. preview_packet 可读。
10. 五个禁止 flags 均为 false：
    - generate_called=false
    - export_docx_called=false
    - review_apply_called=false
    - zbid_writeback_called=false
    - output_job_export_written=false。
11. 服务关闭后 PID 停止。
12. 服务关闭后端口释放。
13. 未生成 DOCX。
14. 未写 output/job/export。

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
15. 不得访问或识别 AI知识图谱大全 文件夹。
16. 不得进入 50 人正式部署设计。
17. 不得实施顶级模型升级。
18. 不得自动进入 Step 279。

完成后：
1. 运行 git status --short。
2. 运行 git diff --check。
3. 运行 git diff --cached --check。
4. 提交 runtime regression report。
5. 创建并推送 tag。
6. 推送 main 和 tag。
7. 完成后立即停止，等待审核，不得进入 Step 279。
```
