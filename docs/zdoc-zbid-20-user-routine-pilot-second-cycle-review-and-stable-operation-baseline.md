# ZDoc-ZBid 20-user routine pilot second-cycle review and stable operation baseline

## 1. Step 253 第二轮常态试运行结果复盘

Step 253 已按 Step 252 运行管理基线完成第二轮 20 人常态试运行受控验证。本轮继续保持 preview-only / no-write / no-evidence，不开放正式生成链、正式证据链、正式评分链、DOCX 导出链、review/apply 链或 ZBid 写回链。

Step 253 结果摘要：

- ZDoc 仓库：`/Users/youfeini/Desktop/文档生成系统`
- ZDoc 分支：`main`
- Step 253 开始前 HEAD：`1ea100119ea82c3145a1e127ec10ccf4d8a3fa38`
- Step 253 结束后 HEAD：`e46b7f464f9db8d618c03b87593b7d1aa3af94b3`
- ZBid 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- ZBid 分支：`local-llm-integration-clean`
- ZBid HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 报告文件：`docs/zdoc-zbid-20-user-routine-pilot-second-cycle-controlled-execution-report.md`
- 请求数：30
- 批次数：3
- 模拟用户标识：20 个
- 角色 / 场景：11 类
- 异常 / 边界输入：8 条
- ZDoc HTTP 200：30/30
- ZBid HTTP 200：30/30
- `preview_only=true`、`no_write=true`、`no_evidence=true`：30/30 成立
- 五个 no-write / no-formal-chain flags：30/30 均为 false
- Step 252 运行管理基线：30/30 符合
- 回退请求：0

## 2. Step 251 与 Step 253 两轮结果对比

| 指标 | Step 251 第一轮 | Step 253 第二轮 | 对比结论 |
| --- | --- | --- | --- |
| 请求数 | 30 | 30 | 持平 |
| 批次数 | 3 | 3 | 持平 |
| 20 人模拟用户覆盖 | 20 个模拟用户标识 | 20 个模拟用户标识 | 持续覆盖 20 人规模口径 |
| 角色 / 场景 | 11 类 | 11 类 | 持平 |
| 异常 / 边界输入 | 8 条 | 8 条 | 持平 |
| ZDoc HTTP 200 | 30/30 | 30/30 | 持续通过 |
| ZBid HTTP 200 | 30/30 | 30/30 | 持续通过 |
| preview-only / no-write / no-evidence | 30/30 成立 | 30/30 成立 | 持续成立 |
| 五个 false flags | 30/30 均 false | 30/30 均 false | 持续成立 |
| output/job/export 写入 | 无 | 无 | 持续无写入 |
| 回退请求 | 0 | 0 | 持平 |

响应观察：

- Step 251 ZDoc latency：min 0.53 ms，median 1.15 ms，max 15.57 ms。
- Step 253 ZDoc latency：min 0.51 ms，median 1.23 ms，max 15.38 ms。
- Step 251 outbound latency：min 1.10 ms，median 2.42 ms，max 4.73 ms。
- Step 253 outbound latency：min 1.06 ms，median 2.41 ms，max 6.00 ms。

两轮结果整体一致，未发现第二轮相较第一轮出现新增阻断问题或安全边界回退。

## 3. 两轮稳定性摘要

两轮合计结果：

| 指标 | 两轮合计 |
| --- | ---: |
| 请求数 | 60 |
| 批次数 | 6 |
| 20 人模拟用户规模 | 每轮 20 个模拟用户标识，按 20 人规模口径持续覆盖 |
| 角色 / 场景 | 11 类 |
| 异常 / 边界输入 | 16 条 |
| ZDoc HTTP 200 | 60/60 |
| ZBid HTTP 200 | 60/60 |
| preview_only=true | 60/60 |
| no_write=true | 60/60 |
| no_evidence=true | 60/60 |
| 五个 false flags | 60/60 均为 false |
| 回退请求 | 0 |

说明：Step 251 使用 `pilot-user-01` 至 `pilot-user-20`，Step 253 使用 `pilot2-user-01` 至 `pilot2-user-20` 以区分周期；两轮均按同一 20 人规模口径执行，不代表扩大到 40 人。

稳定性结论：

- 两轮均完成启动验证 / 启动复核批次、常态使用批次、异常边界批次。
- 两轮均未发现 preview-only 链路阻断。
- 两轮均未发现正式链误触发。
- 两轮均未发现 ZBid 写回。
- 两轮均未生成 DOCX。
- 两轮均未写入 `output/job/export`。
- 两轮均未把 preview-only 结果作为 evidence 或评分依据。

## 4. HTTP 与安全 flags 复核结论

两轮 HTTP 结果：

- ZDoc `POST /local-trial/preview-only`：60/60 为 HTTP 200。
- ZBid `POST /local-llm/zdoc-preview-only/receive`：60/60 为 HTTP 200。

两轮 preview-only 边界：

- `preview_only=true`：60/60 成立。
- `no_write=true`：60/60 成立。
- `no_evidence=true`：60/60 成立。

两轮五个禁止 flags：

- `generate_called=false`：60/60 成立。
- `export_docx_called=false`：60/60 成立。
- `review_apply_called=false`：60/60 成立。
- `zbid_writeback_called=false`：60/60 成立。
- `output_job_export_written=false`：60/60 成立。

结论：两轮常态试运行均保持 preview-only / no-write / no-evidence，且五个禁止 flags 未出现异常。

## 5. Step 252 运行管理基线执行情况

Step 253 已按 Step 252 运行管理基线执行：

- 运行前核验 ZDoc 与 ZBid 分支、HEAD、`git status --short`：已完成。
- 仅使用临时环境变量启用 preview-only network-send：已遵守。
- 未写入 `.env`、配置文件或持久配置：已遵守。
- 仅启动必要 preview-only 服务：已遵守。
- 仅访问授权端口：`127.0.0.1:18766`、`127.0.0.1:18767`。
- 仅调用授权 preview-only endpoint：已遵守。
- 运行前后检查 `output/job/export`：已完成，均为空。
- 运行后关闭本步启动服务：已完成。
- 运行后确认端口无监听：已完成。
- 失败不得现场修复：本轮无失败、无修复动作。

因此，Step 252 运行管理基线可作为后续 20 人常态试运行的基础管理规则继续使用。

## 6. 已验证能力清单

已验证能力：

- ZDoc 本地服务可启动并处理 preview-only 请求。
- ZBid receiver 本地服务可启动并接收 preview-only payload。
- ZDoc `POST /local-trial/preview-only` 本地可达。
- ZBid `POST /local-llm/zdoc-preview-only/receive` 本地可达。
- ZDoc outbound adapter 可向 ZBid receiver endpoint 发送 preview-only payload。
- ZBid receiver 可返回 HTTP 200。
- 返回结果可体现 `preview_only=true`、`no_write=true`、`no_evidence=true`。
- `preview_packet` 可读。
- `validator_result` 可读。
- `blocked_reasons` 可读。
- 五个 no-write / no-formal-chain flags 可持续保持 false。
- 异常 / 边界输入下 blocked_reasons 可作为人工复核提示。
- 服务关闭后端口释放可复核。
- `output/job/export` 前后无新增写入。
- 两轮常态试运行的结果具有一致性。

## 7. 未验证能力清单

未验证能力：

- 长时间连续运行。
- 真实 20 人同时在线并发压测。
- 真实投标资料、大体量文件或敏感业务数据处理。
- 正式生成链 `/generate`。
- 正式 DOCX 导出链 `/export_docx`。
- `review/apply` 正式应用链。
- ZBid 正式写回链。
- 正式 evidence 写入。
- 正式评分依据写入。
- 正式数据库、文件存储、qingtian results 或 score basis 写入。
- 故障注入、服务宕机恢复、主机重启后的恢复流程。
- 长期日志轮转、备份、监控、告警。
- 50 人正式部署容量设计。
- 顶级本地模型升级实施。

以上未验证能力不得因两轮 preview-only 常态试运行通过而视为已开放。

## 8. 已发现问题清单

两轮未发现阻断 preview-only 链路的问题。

两轮未发现以下安全问题：

- 正式链误触发。
- ZBid 写回。
- DOCX 生成。
- evidence 写入。
- 评分依据写入。
- `output/job/export` 写入。
- 未授权 endpoint 调用。
- fallback 到正式接口。

观察项：

- 长周期常态运行仍未验证。
- 真实多用户同时操作节奏仍未验证。
- 日志留痕模板需要在后续常态运行中持续固定。
- blocked_reasons 的人工分级处置规则可继续细化。
- 服务启动、关闭、端口释放仍需每次运行前后人工复核。

## 9. 问题分级

| 分级 | 当前结论 | 处理要求 |
| --- | --- | --- |
| 阻断级 | 两轮未发现 | 如出现 endpoint 不可达、批量失败、正式链误触发，应立即停止 |
| 高风险 | 两轮未发现 | 如出现 ZBid 写回、DOCX 生成、evidence 写入、评分依据写入，应立即停止 |
| 中风险 | 长周期稳定性、真实并发仍未验证 | 需要后续单独授权验证，不得默认扩大为生产结论 |
| 低风险 | 日志模板、问题清单、回退记录仍需常态固化 | 可在 docs-only 或受控试运行中持续完善 |
| 观察项 | blocked_reasons 可读性、人工复核分级、服务关闭检查 | 继续记录，不得直接视为代码缺陷或已授权修复 |

## 10. 20 人试运行稳定运行条件

当前可作为 20 人试运行稳定运行基线的条件：

- 限定 preview-only / no-write / no-evidence。
- 仅使用脱敏样例、测试文档、非正式成果。
- 仅调用授权 preview-only endpoint。
- 每次运行前核验分支、HEAD、工作区状态。
- 每次运行前确认端口使用计划。
- 仅使用临时环境变量启用 preview-only network-send。
- 每次运行记录请求数、批次、角色、HTTP、blocked_reasons、validator_result 和五个 flags。
- 每次运行前后检查 `output/job/export`。
- 每次运行结束关闭本步启动服务。
- 每次运行结束确认端口无监听。
- 出现停止条件时不现场修复，先记录并等待单独授权。

## 11. 继续常态试运行的准入条件

继续常态试运行前必须满足：

- 用户明确授权。
- ZDoc 与 ZBid 仓库路径、分支、开始前 HEAD 已确认。
- ZDoc 与 ZBid 工作区 clean。
- 试运行人员或模拟用户范围已明确。
- 试运行数据保持脱敏、测试、非正式成果范围。
- preview-only endpoint 范围已明确。
- 服务端口已授权。
- 临时环境变量启用范围已明确。
- 日志记录模板、问题清单模板、回退记录模板已准备。
- `output/job/export` 前快照已确认。
- 停止条件已明确。

## 12. 必须暂停试运行的触发条件

出现任一情况必须暂停试运行：

- `generate_called` 非 false。
- `export_docx_called` 非 false。
- `review_apply_called` 非 false。
- `zbid_writeback_called` 非 false。
- `output_job_export_written` 非 false。
- 触发 `/generate`。
- 触发 `/export_docx`。
- 触发 `/review/apply`。
- 触发 ZBid 写回。
- 生成 DOCX。
- 写入 `output/job/export`。
- 写入 evidence。
- 写入评分依据。
- 写入正式业务数据。
- 调用未知 endpoint。
- fallback 到正式接口。
- 服务无法关闭或端口无法释放。
- 出现未授权代码、tests、frontend、backend 或既有 docs 修改。

## 13. preview-only / no-write / no-evidence 长期边界

长期边界必须保持：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

以上字段只用于试运行边界确认，不得作为正式 evidence，不得作为评分依据，不得写入正式业务数据。

## 14. 禁止接口、禁止写入、禁止证据化、禁止评分化要求

继续禁止：

- 不得调用 `/generate`。
- 不得调用 `/export_docx`。
- 不得调用 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。
- 不得写正式 evidence。
- 不得写正式评分依据。
- 不得写正式业务数据。
- 不得把 advisory / preview / shadow / patch / diff / rollback / dry-run 作为 evidence。
- 不得把 preview-only 结果作为评分依据。
- 不得 fallback 到正式接口。

## 15. 主机定位说明

当前主机仅作为 20 人试运行主机。

当前主机不得视为：

- 长期正式生产服务器。
- 50 人正式部署服务器。
- 正式生成链服务器。
- 正式证据链服务器。
- 正式评分链服务器。
- DOCX 正式导出服务器。
- ZBid 写回服务器。
- 顶级本地模型升级实施主机。

当前主机定位是验证本地可用、流程闭环、preview-only 常态试运行稳定性、日志留痕、问题清单和回退流程。

## 16. 端口、服务、日志、问题清单和回退记录管理要求

### 端口与服务

- 运行前记录 ZDoc 服务启动命令、PID、端口。
- 运行前记录 ZBid 服务启动命令、PID、端口。
- 优先沿用已验证端口 `127.0.0.1:18766`、`127.0.0.1:18767`。
- 若端口被占用，必须记录原因、实际端口、PID、关闭结果和端口释放结果。
- 运行结束后关闭本步启动服务。
- 运行结束后确认端口无监听。

### 日志记录

每次记录至少包含：

- 运行日期。
- 批次编号。
- 模拟用户标识或脱敏用户标识。
- 角色 / 场景。
- 请求入口。
- payload 类型。
- HTTP 状态。
- `preview_only`、`no_write`、`no_evidence`。
- 五个 no-write / no-formal-chain flags。
- blocked_reasons 摘要。
- validator_result 摘要。
- 人工复核结论。
- 是否需要回退。

### 问题清单

问题清单至少包含：

- 问题编号。
- 发现时间。
- 发现批次。
- 角色 / 场景。
- 问题描述。
- 影响范围。
- 分级。
- 是否触发停止条件。
- 是否涉及正式链。
- 是否涉及写入。
- 初步处置。
- 后续授权需求。

### 回退记录

回退记录至少包含：

- 回退编号。
- 触发时间。
- 触发条件。
- 涉及服务。
- 涉及端口。
- 已执行动作。
- 服务是否关闭。
- 端口是否释放。
- `output/job/export` 快照。
- 是否需要代码修复及对应授权。

## 17. 是否建议进入 Step 255

建议进入 Step 255，但仅限在用户明确授权后执行。

建议 Step 255 定位为 20 人常态试运行持续运行授权请求，仍应限定 preview-only / no-write / no-evidence，不得自动启动服务、访问端口、调用 endpoint、修改代码或进入正式链。

## 18. Step 255 授权请求草案

以下为可复制的 Step 255 授权请求草案：

```text
执行 Step 255：ZDoc-ZBid 20-user routine pilot continued operation authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 254 提交后的 ZDoc HEAD>

本步性质：
ZDoc docs-only / authorization-request-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
基于 Step 251 第一轮常态试运行、Step 253 第二轮常态试运行和 Step 254 稳定运行基线，起草 20 人常态试运行持续运行授权请求。该文档只代表申请授权，不代表已启动下一轮运行。

必须继续限定：
1. preview-only / no-write / no-evidence。
2. 不开放 /generate。
3. 不开放 /export_docx。
4. 不开放 /review/apply。
5. 不开放 ZBid 写回。
6. 不生成 DOCX。
7. 不写 output/job/export。
8. 不把 preview-only 结果作为 evidence。
9. 不把 preview-only 结果作为评分依据。
10. 不进入 50 人正式部署设计。
11. 不实施顶级模型升级。

完成后停止，不得自动进入下一步。
```
