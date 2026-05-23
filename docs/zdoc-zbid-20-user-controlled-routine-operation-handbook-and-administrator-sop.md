# ZDoc-ZBid 20-user controlled routine operation handbook and administrator SOP

## 1. 编制目的与适用范围

本文档用于归档 ZDoc-ZBid 20 人受控常态试运行的运行手册与管理员操作规程。本文档只服务于 preview-only / no-write / no-evidence 的受控试运行管理，不代表开放正式链，不代表进入 50 人正式部署设计，不代表实施顶级本地大模型升级。

适用范围：

- ZDoc 与 ZBid 的 20 人受控常态试运行。
- 管理员每日启动前检查、运行中记录、每日收口检查。
- preview-only 链路的日志、问题清单、回退记录和人工复核。
- 前置 payload 校准、非法 ZBid status 枚举阻断和有效请求计数口径管理。

不适用范围：

- 正式生成链。
- DOCX 导出链。
- review/apply 链。
- ZBid 写回链。
- 正式 evidence 写入。
- 评分依据写入。
- 长期正式生产服务器运维。
- 50 人正式部署设计。
- 顶级本地大模型升级实施。
- `/Users/youfeini/Desktop/AI知识图谱大全` 文件夹识别、扫描、读取、复制、移动或分析。

## 2. 20 人受控常态试运行定位

当前运行定位为 20 人受控常态试运行。

该定位意味着：

- 当前主机仅作为 20 人试运行主机。
- 试运行目标是验证本地可用、流程闭环、preview-only 链路稳定、人工复核可执行。
- 当前运行只允许 preview-only / no-write / no-evidence。
- 当前运行不允许正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply 或 ZBid 写回。
- 当前运行不等同于长期正式生产服务。
- 当前运行不等同于 50 人正式部署。

## 3. 管理员职责

管理员负责：

- 确认每次试运行前均获得明确授权。
- 确认仓库、分支、HEAD、`git status --short` 与授权一致。
- 确认服务、端口、endpoint 调用均在授权范围内。
- 确认所有请求保持 preview-only / no-write / no-evidence。
- 确认五个 no-write / no-formal-chain flags 均为 false。
- 记录每日运行日志、问题清单和回退记录。
- 区分有效请求、前置 payload 校准、adapter 阻断和 preview-only calibration call。
- 发现暂停触发条件时立即停止试运行并记录。
- 每日收口时确认服务关闭、端口释放、无 DOCX、无 `output/job/export` 写入、无 ZBid 写回。

管理员不得：

- 现场修改代码、tests、frontend、backend 或既有 docs。
- 将 preview-only 结果转为 evidence。
- 将 preview-only 结果转为评分依据。
- 因 HTTP 200 将结果解释为正式审批或正式链开放。
- 在未授权情况下扩大试运行范围、启动 50 人正式部署设计或实施顶级模型升级。

## 4. 试运行人员角色划分

建议的 20 人受控常态试运行角色包括：

| 角色 | 使用范围 | 关键边界 |
| --- | --- | --- |
| 管理员 / 总控 | 启动、关闭、日志、问题清单、回退记录 | 不得将 preview-only 结果视为正式审批 |
| 技术标主编 | 观察 preview_packet 与 blocked_reasons | 不得形成正式 evidence |
| 施工组织设计编制人员 | 检查 preview-only 提示与材料补充方向 | 不得写入正式成果 |
| 专项施工方案编制人员 | 观察异常 / 边界输入提示 | 不得触发正式生成 |
| 进度计划编制人员 | 观察 validator_result 可读性 | 不得形成评分依据 |
| 质量安全复核人员 | 复核 blocked_reasons 与人工判断 | 不得调用 review/apply |
| 商务 / 清单协同人员 | 观察跨角色协同提示 | 不得触发 ZBid 写回 |
| 项目资料整理人员 | 核对材料缺口提示 | 不得上传真实投标 evidence |
| ZBid 评标辅助观察人员 | 观察 ZBid receiver 接收表现 | 不得评分化 |
| 普通试用人员 | 体验 preview-only 流程 | 不得导出 DOCX |
| 异常 / 边界输入观察角色 | 验证阻断与错误提示 | 不得 fallback 到正式接口 |

## 5. 每日启动前检查清单

每次受控常态试运行前，管理员必须逐项确认：

- 已获得本轮试运行明确授权。
- 授权中明确允许启动的服务、访问的端口、调用的 endpoint。
- 授权中明确仍保持 preview-only / no-write / no-evidence。
- ZDoc 仓库路径、分支、HEAD 与授权一致。
- ZBid 仓库路径、分支、HEAD 与授权一致。
- ZDoc 与 ZBid 的 `git status --short` 均符合授权要求。
- 本轮 payload 使用脱敏 / 模拟 / 非正式数据。
- 本轮不使用真实投标 evidence。
- 本轮不生成 DOCX。
- 本轮不写 `output/job/export`。
- 本轮不触发 ZBid 写回。
- 本轮日志模板、问题清单模板、回退记录模板已准备。
- 前置 payload 校准如有必要，已明确单独计数、单独归档、不得混入有效请求。

## 6. 服务启动、端口、关闭、释放检查操作规程说明

本节仅说明运行规程，不代表当前步骤已授权启动服务、访问端口或调用 endpoint。

服务启动规程：

- 仅在用户明确授权的执行步骤中启动服务。
- 仅启动授权范围内的 ZDoc preview-only 服务和 ZBid preview-only receiver 服务。
- 记录启动命令、服务名称、PID、端口、启动时间、操作者角色。
- 优先使用临时环境变量，不写入 `.env`、配置文件或持久配置。
- 仅启用 preview-only network-send 相关临时变量，不启用正式链开关。

端口管理规程：

- 仅访问授权端口。
- 记录 ZDoc 端口、ZBid 端口、是否沿用既有试运行端口、是否发生端口占用。
- 如需使用相邻空闲端口，必须记录原因、实际端口、PID 和关闭结果。
- 不得扫描未知端口，不得调用未知 endpoint。

关闭与释放规程：

- 每轮试运行结束后关闭本轮启动的服务进程。
- 记录关闭时间、PID、关闭方式、日志末尾状态。
- 确认授权端口无监听。
- 如端口未释放，立即暂停试运行并记录问题，不得现场修代码。

## 7. preview-only / no-write / no-evidence 使用边界

每条有效请求必须保持：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

边界解释：

- preview-only 表示只用于预览、提示、人工复核和问题发现。
- no-write 表示不得写入正式业务数据、正式结果、正式存储或 ZBid 写回链。
- no-evidence 表示不得将 preview-only 结果作为 evidence。
- 五个 false flags 是安全边界确认，不是正式 evidence，不是评分依据。

## 8. 禁止接口、禁止写入、禁止证据化、禁止评分化要求

严格禁止：

- 调用 `/generate`。
- 调用 `/export_docx`。
- 调用 `/review/apply`。
- 调用任何 ZBid 写回 endpoint。
- 生成 DOCX。
- 写入 `output/job/export`。
- 将 preview-only 结果作为 evidence。
- 将 preview-only 结果作为评分依据。
- 写入正式业务数据。
- fallback 到正式接口。
- 以 HTTP 200 作为正式审批依据。
- 未授权启动服务、访问端口或调用 endpoint。

## 9. ZDoc -> ZBid preview-only 链路使用注意事项

授权执行时，ZDoc -> ZBid preview-only 链路应保持以下口径：

1. ZDoc 侧仅构造 preview-only payload。
2. ZDoc outbound adapter 仅在显式临时启用后发送。
3. 目标 endpoint 仅限 ZBid receiver preview-only endpoint。
4. payload 仅承载 preview_packet、validator_result、blocked_reasons 与 no-write / no-formal-chain flags。
5. payload 不得包含 DOCX、正式 evidence、正式评分结果、writeback 数据或正式业务数据。
6. ZBid receiver 返回结果仅用于 preview-only 人工复核。
7. ZBid receiver 返回 HTTP 200 不代表正式放行。
8. 任一正式链 flag 非 false 时，必须停止。

## 10. 前置 payload 校准管理规则

前置 payload 校准必须严格管理：

- 数量从严控制。
- 单独计数。
- 单独归档。
- 单独标记校准类型。
- 单独记录是否被 adapter 阻断。
- 单独记录是否作为 preview-only calibration call 到达 ZBid receiver。
- 不得混入有效请求。
- 不得计入有效观察期请求。
- 不得归为 evidence。
- 不得归为评分依据。
- 不得用于证明正式链可用。

推荐记录字段：

| 字段 | 说明 |
| --- | --- |
| calibration_id | 前置校准编号 |
| calibration_type | 非法枚举 / payload-shape / 其他 |
| request_count | 校准请求数量 |
| adapter_blocked_count | adapter 阻断数量 |
| receiver_call_count | 到达 ZBid receiver 的 preview-only calibration call 数量 |
| effective_request_counted | 必须为否 |
| evidence_counted | 必须为否 |
| scoring_basis_counted | 必须为否 |
| notes | 校准原因与处理结论 |

## 11. 非法 ZBid status 枚举阻断处置规则

若出现非法 ZBid status 枚举：

1. 标记为前置 payload 校准或边界阻断记录。
2. 确认 outbound adapter 是否阻断。
3. 确认未发送至 ZBid receiver；如已发送，必须单独说明原因与边界。
4. 确认未 fallback 到正式接口。
5. 确认未触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
6. 确认未生成 DOCX。
7. 确认未写 `output/job/export`。
8. 确认未形成 evidence 或评分依据。
9. 将记录归档到校准清单，不计入有效请求。
10. 如非法枚举阻断无法解释，暂停试运行并申请单独修复授权。

## 12. 试运行日志记录模板

```text
日期：
试运行轮次：
授权步骤：
操作者角色：
ZDoc 仓库 / 分支 / HEAD：
ZBid 仓库 / 分支 / HEAD：
ZDoc git status --short：
ZBid git status --short：
服务清单：
端口清单：
PID 清单：
临时环境变量：
调用 endpoint 清单：
有效请求数：
前置校准数：
adapter 阻断数：
preview-only calibration call 数：
HTTP 200 结果：
preview_only / no_write / no_evidence 结果：
五个 false flags 结果：
blocked_reasons 可读性：
validator_result 可读性：
是否触发禁止接口：
是否生成 DOCX：
是否写 output/job/export：
是否 ZBid 写回：
是否 evidence 化：
是否评分化：
人工复核结论：
服务关闭结果：
端口释放结果：
```

## 13. 问题清单记录模板

```text
问题编号：
发现时间：
发现角色：
所属批次 / 场景：
请求入口：
payload 类型：
问题类型：
问题分级：阻断级 / 高风险 / 中风险 / 低风险 / 观察项
现象描述：
blocked_reasons：
validator_result：
是否 preview_only：
是否 no_write：
是否 no_evidence：
五个 false flags 是否均为 false：
是否触发禁止接口：
是否写入：
是否 evidence 化：
是否评分化：
是否需要暂停：
是否需要回退：
是否需要单独授权修复：
处理结论：
```

## 14. 回退记录模板

```text
回退编号：
触发时间：
触发角色：
触发条件：
涉及服务：
涉及端口：
涉及 endpoint：
涉及请求编号：
涉及 payload 类型：
是否出现 /generate：
是否出现 /export_docx：
是否出现 /review/apply：
是否出现 ZBid 写回：
是否生成 DOCX：
是否写 output/job/export：
是否形成 evidence：
是否形成评分依据：
已采取动作：
服务关闭状态：
端口释放状态：
数据与文件检查：
后续是否需要授权修复：
复核人：
最终结论：
```

## 15. 每日收口检查清单

每日试运行结束后，管理员必须确认：

- 本日有效请求数已记录。
- 本日前置校准数已单独记录。
- 本日 adapter 阻断数已单独记录。
- 本日 preview-only calibration call 数已单独记录。
- 本日所有有效请求均保持 preview-only / no-write / no-evidence。
- 本日五个 no-write / no-formal-chain flags 均为 false。
- 本日未触发 `/generate`、`/export_docx`、`/review/apply`。
- 本日未触发 ZBid 写回。
- 本日未生成 DOCX。
- 本日未写 `output/job/export`。
- 本日未将 preview-only 结果作为 evidence。
- 本日未将 preview-only 结果作为评分依据。
- 本日问题清单已归档。
- 本日回退记录已归档或标记为无。
- 本日启动的服务已关闭。
- 本日授权端口已释放。
- 本日不得进入 50 人正式部署设计或顶级模型升级。

## 16. 必须暂停试运行的触发条件

出现以下任一情况，必须立即暂停：

- 任一正式链 flag 非 false。
- `/generate` 被调用。
- `/export_docx` 被调用。
- `/review/apply` 被调用。
- ZBid 写回被触发。
- DOCX 被生成。
- `output/job/export` 被写入。
- preview-only 结果被作为 evidence。
- preview-only 结果被作为评分依据。
- 正式业务数据被写入。
- 前置校准混入有效请求。
- 未授权 endpoint 被调用。
- 服务无法关闭。
- 端口无法释放。
- 管理员无法确认本轮运行边界。

## 17. 回退流程

回退流程：

1. 立即停止新增请求。
2. 记录触发条件、时间、角色、批次、场景和 payload。
3. 停止本轮授权启动的服务。
4. 确认端口释放。
5. 检查是否出现 DOCX、`output/job/export`、ZBid 写回、evidence 或评分依据。
6. 固化日志、问题清单和回退记录。
7. 不现场修复代码。
8. 不修改 tests、frontend、backend 或既有 docs。
9. 起草单独授权请求后再进入修复或复验。

## 18. 管理员复核要点

管理员每日复核重点：

- 授权是否覆盖本轮动作。
- 服务、端口、endpoint 是否均在授权范围内。
- 有效请求与校准请求是否分开。
- preview-only / no-write / no-evidence 是否全程成立。
- 五个 false flags 是否全程为 false。
- 是否有被误认为正式证据或评分依据的记录。
- 是否存在 HTTP 200 被误解为正式审批的问题。
- 是否存在异常 / 边界输入绕过 adapter 阻断的问题。
- 是否存在 `output/job/export` 写入或 DOCX 生成。
- 是否存在 ZBid 写回或正式业务数据写入。

## 19. 试运行人员禁止事项

试运行人员不得：

- 使用真实敏感业务数据。
- 使用真实投标 evidence。
- 触发 `/generate`。
- 触发 `/export_docx`。
- 触发 `/review/apply`。
- 触发 ZBid 写回。
- 生成 DOCX。
- 写入 `output/job/export`。
- 将 preview-only 结果作为 evidence。
- 将 preview-only 结果作为评分依据。
- 将 HTTP 200 解释为正式审批。
- 绕过管理员直接扩大试运行范围。
- 进入 50 人正式部署设计。
- 实施顶级模型升级。

## 20. 当前不得进入事项

当前仍不得进入：

- 50 人正式部署。
- 正式生产服务器定位。
- 顶级模型升级。
- 证据化。
- 评分化。
- 写回。
- 正式生成链。
- DOCX 导出链。
- review/apply 链。
- `output/job/export` 写入。
- 正式业务数据写入。

## 21. Step 265 授权请求草案

以下为可复制的 Step 265 授权请求草案。该草案不代表当前已授权执行 Step 265。

```text
执行 Step 265：ZDoc-ZBid 20-user controlled routine operation handbook stage review and next action authorization request

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 264 结束后 HEAD>

特别说明：
不得访问、扫描、读取、复制、移动或分析 /Users/youfeini/Desktop/AI知识图谱大全。

本步性质：
docs-only / stage-review-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
归档 Step 264《20-user controlled routine operation handbook and administrator SOP》编制结果，并起草下一步授权请求。

允许新增文件：
docs/<填写 Step 265 目标文档名>.md

严格禁止：
1. 不修改代码 / tests / frontend / backend / 既有 docs。
2. 不运行服务。
3. 不运行 Ollama。
4. 不访问端口。
5. 不调用任何 endpoint。
6. 不触发 /generate、/export_docx、/review/apply。
7. 不触发 ZBid 写回。
8. 不生成 DOCX。
9. 不写 output/job/export。
10. 不把 preview-only 结果作为 evidence。
11. 不把 preview-only 结果作为评分依据。
12. 不进入 50 人正式部署设计。
13. 不实施顶级模型升级。

文档必须复核：
- Step 264 是否仅新增目标 docs 文件。
- 管理员 SOP 是否覆盖启动前检查、服务/端口规程、日志模板、问题清单、回退记录、每日收口、暂停条件和禁止事项。
- 是否继续保持 preview-only / no-write / no-evidence。
- 是否明确前置 payload 校准数量从严、单独计数、单独归档、不得混入有效请求。
- 是否明确当前主机仅作为 20 人试运行主机，不作为长期正式生产服务器。

完成后必须停止，不得自动进入后续步骤。
```
