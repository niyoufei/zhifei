# ZDoc-ZBid 20-user routine pilot review and operation management baseline

## 1. Step 251 常态试运行结果复盘

Step 251 已完成约 20 人团队口径下的常态试运行受控验证。本轮执行范围仍限定为 preview-only / no-write / no-evidence，不开放正式生成链、正式证据链、正式评分链、DOCX 导出链、review/apply 链或 ZBid 写回链。

Step 251 执行结果摘要如下：

- ZDoc 仓库：`/Users/youfeini/Desktop/文档生成系统`
- ZDoc 分支：`main`
- ZDoc Step 251 开始前 HEAD：`e6d03340ea57ea91586303274d9fa62fc2e79135`
- ZDoc Step 251 结束后 HEAD：`b2d28c1c3e5dec5a40e0dd2358fbc2c10299449d`
- ZBid 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- ZBid 分支：`local-llm-integration-clean`
- ZBid HEAD：`378355755372e03ac4f4064af59b287054984c25`
- Step 251 报告：`docs/zdoc-zbid-20-user-routine-pilot-controlled-execution-report.md`
- ZDoc 服务端口：`127.0.0.1:18766`
- ZBid 服务端口：`127.0.0.1:18767`
- 调用 endpoint：
  - ZDoc `POST /local-trial/preview-only`
  - ZBid `POST /local-llm/zdoc-preview-only/receive`
- 服务结束后：ZDoc 与 ZBid 服务均已关闭，`18766`、`18767` 均无监听。

## 2. 20 人常态试运行阶段验收结论

本阶段可作为 20 人常态试运行的受控基线，但不能作为正式生产上线结论。

验收结论：

- 20 人常态试运行代表性验证通过。
- ZDoc preview-only route 可用于常态试运行入口。
- ZDoc outbound adapter 可在临时启用 preview-only network-send 后向 ZBid receiver 发送 payload。
- ZBid receiver API 可接收并返回 preview-only / no-write / no-evidence 结果。
- 30 条请求全部 HTTP 200。
- 30 条请求全部保持 `preview_only=true`、`no_write=true`、`no_evidence=true`。
- 五个 no-write / no-formal-chain flags 全部为 false。
- 未发现正式链误触发、ZBid 写回、DOCX 生成、evidence 写入或评分依据写入。
- 两侧 `output/job/export` 未发现新增写入。

限制结论：

- 本阶段不是正式生产验收。
- 本阶段不是 50 人正式部署设计。
- 本阶段不是正式业务联调开放。
- 本阶段没有验证长期运行、真实用户并发、真实投标数据、正式导出或写回。

## 3. 结果摘要

| 指标 | Step 251 结果 |
| --- | --- |
| 总请求数 | 30 |
| 批次数 | 3 |
| 模拟用户标识数 | 20 |
| 角色 / 场景数 | 11 |
| 异常 / 边界输入数 | 8 |
| ZDoc HTTP 200 | 30/30 |
| ZBid HTTP 200 | 30/30 |
| preview_only=true | 30/30 |
| no_write=true | 30/30 |
| no_evidence=true | 30/30 |
| 五个 false flags | 30/30 均为 false |
| 回退请求 | 0 |

批次摘要：

| 批次 | 名称 | 请求数 | 执行方式 | 结果 |
| --- | --- | ---: | --- | --- |
| B1 | 启动验证批次 | 10 | 顺序请求 | 全部 HTTP 200，全部保持 preview-only / no-write / no-evidence |
| B2 | 常态使用批次 | 12 | 6-worker 并发请求 | 全部 HTTP 200，未发现服务异常 |
| B3 | 异常边界批次 | 8 | 4-worker 并发请求 | 全部 HTTP 200，blocked_reasons 可读 |

角色 / 场景摘要：

1. 总控管理员
2. 技术标主编
3. 施工组织设计编制人员
4. 专项施工方案编制人员
5. 进度计划编制人员
6. 质量安全复核人员
7. 商务 / 清单协同人员
8. 项目资料整理人员
9. ZBid 评标辅助观察人员
10. 普通试用人员
11. 异常输入 / 边界输入场景

## 4. 已验证能力清单

已验证能力：

- ZDoc 本地服务可启动并处理 preview-only 请求。
- ZBid receiver 本地服务可启动并接收 preview-only payload。
- ZDoc `POST /local-trial/preview-only` 在本地试运行中可达。
- ZBid `POST /local-llm/zdoc-preview-only/receive` 在本地试运行中可达。
- ZDoc outbound adapter 可向 ZBid receiver endpoint 发送 preview-only payload。
- ZBid receiver 可返回 HTTP 200。
- 返回结果可体现 `preview_only=true`、`no_write=true`、`no_evidence=true`。
- `preview_packet` 可读。
- `validator_result` 可读。
- `blocked_reasons` 可读。
- 五个 no-write / no-formal-chain flags 均保持 false：
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- 异常 / 边界输入下 blocked_reasons 可作为人工复核提示。
- 服务关闭后端口释放可复核。
- `output/job/export` 前后无新增写入。

## 5. 未验证能力清单

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

## 6. 已发现问题清单

本轮未发现阻断 preview-only 链路的问题。

本轮未发现以下安全问题：

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

## 7. 问题分级

| 分级 | 当前结论 | 处理要求 |
| --- | --- | --- |
| 阻断级 | 本轮未发现 | 如出现 endpoint 不可达、批量失败、正式链误触发，应立即停止 |
| 高风险 | 本轮未发现 | 如出现 ZBid 写回、DOCX 生成、evidence 写入、评分依据写入，应立即停止 |
| 中风险 | 长周期稳定性、真实并发仍未验证 | 需要后续单独授权验证，不得默认扩大为生产结论 |
| 低风险 | 日志模板、问题清单、回退记录仍需常态固化 | 可在 docs-only 或受控试运行中持续完善 |
| 观察项 | blocked_reasons 可读性、人工复核分级、服务关闭检查 | 继续记录，不得直接视为代码缺陷或已授权修复 |

## 8. 常态运行管理规则

常态试运行期间必须遵守以下规则：

1. 每次试运行前确认 ZDoc 与 ZBid 仓库分支、HEAD、`git status --short`。
2. 每次只使用临时环境变量启用 preview-only network-send。
3. 不写入 `.env`、配置文件或持久运行配置。
4. 仅启动必要的 preview-only 服务。
5. 仅访问授权端口。
6. 仅调用授权 preview-only endpoint。
7. 每次运行记录请求数量、角色 / 场景、HTTP 状态、五个 false flags。
8. 每次运行前后检查 `output/job/export`。
9. 每次运行结束后关闭本步启动服务。
10. 每次运行结束后确认端口无监听。
11. 任何失败不得现场修复，必须记录问题并另行授权。

## 9. preview-only / no-write / no-evidence 长期边界

长期运行边界必须保持：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

以上字段只用于试运行边界确认，不得作为正式 evidence，不得作为评分依据，不得写入正式业务数据。

## 10. 禁止接口、禁止写入、禁止证据化、禁止评分化要求

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

## 11. 日志记录模板

建议每次常态试运行按以下模板记录日志摘要：

| 字段 | 记录内容 |
| --- | --- |
| 运行日期 | YYYY-MM-DD |
| 运行批次 | B1 / B2 / B3 / 自定义批次 |
| 操作角色 | 总控管理员 / 技术标主编 / 复核人员等 |
| 用户标识 | 脱敏或模拟标识 |
| 请求入口 | ZDoc preview-only / ZBid receiver |
| payload 类型 | routine / boundary / validation |
| HTTP 状态 | 200 / 非 200 |
| preview_only | true / false |
| no_write | true / false |
| no_evidence | true / false |
| 五个 flags | 全部 false / 存在异常 |
| blocked_reasons | 摘要，不记录敏感业务数据 |
| validator_result | 摘要，不记录正式 evidence |
| 人工复核结论 | 通过 / 观察 / 停止 |
| 是否需要回退 | 是 / 否 |

## 12. 问题清单记录模板

建议问题清单按以下模板记录：

| 字段 | 记录内容 |
| --- | --- |
| 问题编号 | ISSUE-YYYYMMDD-001 |
| 发现时间 | YYYY-MM-DD HH:mm |
| 发现批次 | B1 / B2 / B3 |
| 角色 / 场景 | 具体角色或边界输入 |
| 问题描述 | 简短事实描述 |
| 影响范围 | 单请求 / 批次 / 全链路 |
| 分级 | 阻断级 / 高风险 / 中风险 / 低风险 / 观察项 |
| 是否触发停止条件 | 是 / 否 |
| 是否涉及正式链 | 是 / 否 |
| 是否涉及写入 | 是 / 否 |
| 初步处置 | 记录 / 停止 / 回退 / 申请授权 |
| 后续授权需求 | docs / code / smoke / trial |

## 13. 回退记录模板

建议回退记录按以下模板记录：

| 字段 | 记录内容 |
| --- | --- |
| 回退编号 | ROLLBACK-YYYYMMDD-001 |
| 触发时间 | YYYY-MM-DD HH:mm |
| 触发条件 | flag 异常 / DOCX 生成 / 写入 / endpoint 异常 |
| 涉及服务 | ZDoc / ZBid / 双仓 |
| 涉及端口 | 端口号 |
| 已执行动作 | 停止服务 / 停止试运行 / 保留现场 |
| 服务是否关闭 | 是 / 否 |
| 端口是否释放 | 是 / 否 |
| output/job/export 快照 | 空 / 非空 |
| 是否需要代码修复 | 是 / 否，需另行授权 |
| 复核人 | 角色或脱敏标识 |

## 14. 服务启动、端口、关闭、释放检查要求

每次常态试运行必须记录：

- ZDoc 服务启动命令。
- ZDoc PID。
- ZDoc 端口。
- ZBid 服务启动命令。
- ZBid PID。
- ZBid 端口。
- 是否使用 `PYTHONDONTWRITEBYTECODE=1`。
- 是否使用临时环境变量启用 preview-only network-send。
- 实际调用 endpoint 清单。
- 服务关闭命令或方式。
- 服务关闭后 PID 是否退出。
- 服务关闭后端口是否无监听。

不得在未授权情况下访问其他端口或调用未知 endpoint。

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

当前主机的定位是验证本地可用、流程闭环、preview-only 常态试运行稳定性、日志留痕、问题清单和回退流程。

## 16. 继续试运行的准入条件

继续 20 人常态试运行前必须满足：

- 用户明确授权。
- ZDoc 与 ZBid 仓库分支、HEAD、工作区状态已核验。
- 试运行人员或模拟用户范围已明确。
- 试运行数据保持脱敏、测试、非正式成果范围。
- preview-only endpoint 范围已明确。
- 服务端口已授权。
- 临时环境变量启用范围已明确。
- 日志记录模板、问题清单模板、回退记录模板已准备。
- `output/job/export` 前快照已确认。
- 停止条件已明确。

## 17. 必须暂停试运行的触发条件

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

## 18. Step 253 授权请求草案

以下为可复制的 Step 253 授权请求草案：

```text
执行 Step 253：ZDoc-ZBid 20-user routine pilot continued operation authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 252 提交后的 ZDoc HEAD>

本步性质：
ZDoc docs-only / authorization-request-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
基于 Step 251 常态试运行报告和 Step 252 运行管理基线，起草 20 人常态试运行持续运行授权请求。该文档只代表申请授权，不代表已启动持续运行。

授权请求必须继续限定：
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
