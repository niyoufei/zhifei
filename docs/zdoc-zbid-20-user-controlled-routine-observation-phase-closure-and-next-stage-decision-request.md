# ZDoc-ZBid 20-user controlled routine observation phase closure and next-stage decision request

## 1. Step 245 至 Step 262 阶段成果总览

本文档归档 Step 245 至 Step 262 的阶段成果，并提出下一阶段决策请求。本文档仅为 docs-only 阶段收口与授权请求草案，不代表进入 Step 264，不代表开放正式链，不代表进入 50 人正式部署设计。

阶段成果概览：

| 阶段 | 对应步骤 | 主要成果 | 结论 |
| --- | --- | --- | --- |
| 20 人本地化部署与试运行 | Step 245、Step 246 | 完成本地 ZDoc / ZBid preview-only 链路代表性试运行与 stage review | 5 个代表性角色 payload 通过，ZDoc 与 ZBid 均 HTTP 200 |
| 小范围人工试运行 | Step 247、Step 248 | 完成 5 类人工试运行场景与 readiness review | preview-only / no-write / no-evidence 成立 |
| 20 人扩展试运行 | Step 249、Step 250 | 完成 20 条扩展试运行请求与验收基线归档 | 20/20 HTTP 200，10 类角色 / 场景覆盖 |
| 常态试运行 | Step 251、Step 252、Step 253、Step 254、Step 255、Step 256 | 完成三轮常态试运行与稳定运行基线 | 合计 100 条请求、10 个批次、20 个模拟用户、11 类角色 / 场景、26 条异常 / 边界输入 |
| 受控观察期 | Step 257、Step 258、Step 259、Step 260、Step 261、Step 262 | 完成三轮观察期验证与阶段基线归档 | 合计 180 条有效观察期请求、18 个批次、20 个模拟用户、11 类角色 / 场景、50 条异常 / 边界输入 |

所有阶段均保持 preview-only / no-write / no-evidence；未开放 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回、DOCX 生成、`output/job/export` 写入、正式 evidence、评分依据写入、50 人正式部署设计或顶级模型升级实施。

## 2. 20 人本地化部署与试运行阶段结论

20 人本地化部署与试运行阶段已经形成可归档结论：

- ZDoc 本地 preview-only 入口可用于代表性 20 人团队口径试运行。
- ZBid preview-only receiver 可接收 ZDoc outbound adapter 发送的 preview-only payload。
- 试运行过程可记录请求入口、payload 类型、HTTP 状态、blocked_reasons、validator_result、人工复核结论和回退判断。
- 本阶段验证的是本地可用、流程闭环、试运行稳定，不是长期正式生产服务器验收。
- 本阶段没有验证正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply 或 ZBid 写回。

## 3. preview-only / no-write / no-evidence 边界执行结论

自 Step 245 至 Step 262，核心边界保持一致：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

这些结果只证明 preview-only 试运行边界成立，不构成正式 evidence，不构成评分依据，不构成正式链开放，不构成写回授权。

## 4. ZDoc -> ZBid preview-only 联调链路结论

已验证的联调链路为：

1. ZDoc preview-only 入口构造脱敏 / 模拟 / 非正式 payload。
2. ZDoc outbound adapter 在显式临时启用 preview-only network-send 后发送 payload。
3. ZBid receiver endpoint `POST /local-llm/zdoc-preview-only/receive` 接收 payload。
4. ZBid 返回 preview-only / no-write / no-evidence 结果。
5. `preview_packet`、`validator_result`、`blocked_reasons` 可读。

该链路未进入正式生成链、正式证据链、正式评分链、DOCX 导出链、review/apply 链或 ZBid 写回链。

## 5. 试运行阶段结果摘要

| 阶段 | 核心数量 | 覆盖范围 | 结果 |
| --- | ---: | --- | --- |
| Step 245 20 人本地化代表性试运行 | 5 个代表性角色 payload | 技术标编制、复核、项目负责人、质控审核、备用综合角色 | ZDoc / ZBid 均 HTTP 200 |
| Step 247 小范围人工试运行 | 5 类场景 | 管理员 / 总控、技术标编制、复核、评标辅助观察、异常输入 / 边界输入 | 5/5 HTTP 200 |
| Step 249 20 人扩展试运行 | 20 条请求 | 10 类角色 / 场景，6 条异常 / 边界输入 | 20/20 HTTP 200 |
| Step 251、253、255 三轮常态试运行 | 100 条请求 | 10 个批次、20 个模拟用户、11 类角色 / 场景、26 条异常 / 边界输入 | 100/100 HTTP 200 |
| Step 257、259、261 三轮观察期 | 180 条有效请求 | 18 个批次、20 个模拟用户、11 类角色 / 场景、50 条异常 / 边界输入 | 180/180 HTTP 200 |

阶段总结：小范围、扩展、常态、观察期验证均未发现阻断 preview-only 链路的问题，未发现正式链误触发、ZBid 写回、DOCX 生成、`output/job/export` 写入、evidence 写入或评分依据写入。

## 6. 三轮稳定试运行与三轮观察期验证结论

三轮稳定常态试运行：

- Step 251：30 条请求、3 个批次、20 个模拟用户、11 类角色 / 场景、8 条异常 / 边界输入。
- Step 253：30 条请求、3 个批次、20 个模拟用户、11 类角色 / 场景、8 条异常 / 边界输入。
- Step 255：40 条请求、4 个批次、20 个模拟用户、11 类角色 / 场景、10 条异常 / 边界输入。
- 合计：100 条请求、10 个批次、20 个模拟用户、11 类角色 / 场景、26 条异常 / 边界输入。
- 结论：100/100 HTTP 200，preview-only / no-write / no-evidence 均成立，五个禁止 flags 均为 false，未发现退化。

三轮观察期验证：

- Step 257：50 条有效观察期请求、5 个批次、20 个模拟用户、11 类角色 / 场景、12 条异常 / 边界输入。
- Step 259：60 条有效观察期请求、6 个批次、20 个模拟用户、11 类角色 / 场景、18 条异常 / 边界输入。
- Step 261：70 条有效观察期请求、7 个批次、20 个模拟用户、11 类角色 / 场景、20 条异常 / 边界输入。
- 合计：180 条有效观察期请求、18 个批次、20 个模拟用户、11 类角色 / 场景、50 条异常 / 边界输入。
- 结论：180/180 HTTP 200，preview-only / no-write / no-evidence 均成立，五个禁止 flags 均为 false，与 Step 256、Step 258、Step 260 基线一致，未发现退化。

## 7. 前置 payload 校准口径与边界阻断归档结论

前置 payload 校准必须单独归档，不得计入有效观察期请求。

| 来源步骤 | 校准类型 | 校准数量 | 发送至 ZBid receiver | adapter 阻断 | 是否计入有效观察期 |
| --- | --- | ---: | ---: | ---: | --- |
| Step 257 | 非法 ZBid status 枚举校准 | 50 | 0 | 50 | 否 |
| Step 259 | 非法 ZBid status 枚举校准 | 8 | 0 | 8 | 否 |
| Step 261 | 非法枚举校准 | 10 | 0 | 10 | 否 |
| Step 261 | 预有效 payload-shape 校准 | 70 | 25 | 45 | 否 |
| 合计 | 全部前置校准 | 138 | 25 | 113 | 否 |

归档结论：

- Step 257 的 50 条前置校准和 Step 259 的 8 条前置校准均被 outbound adapter 按 preview-only 边界阻断，未发送至 ZBid receiver。
- Step 261 的 10 条非法枚举校准被 adapter 阻断，未发送至 ZBid receiver。
- Step 261 的 70 条预有效 payload-shape 校准中，25 条作为 preview-only calibration call 发送至 ZBid receiver，45 条被 adapter 阻断。
- 25 条发送至 ZBid 的预有效校准只能归为 preview-only calibration call，不得归入有效观察期请求，不得归为 evidence，不得归为评分依据。
- 前置校准规模偏大、口径需严格区分，已列为观察项。
- 后续前置校准必须数量从严控制、单独计数、单独归档、不得混入有效请求。

## 8. 已验证能力清单

已验证能力包括：

- ZDoc preview-only route 可在本地返回 HTTP 200。
- ZDoc outbound adapter 可在显式临时启用后向 ZBid receiver 发送 preview-only payload。
- ZBid receiver 可接收 preview-only payload 并返回 HTTP 200。
- `preview_packet`、`validator_result`、`blocked_reasons` 可读。
- 常态试运行与观察期请求可保持 preview-only / no-write / no-evidence。
- 五个 no-write / no-formal-chain flags 可保持 false。
- 非法 ZBid status 枚举可被 outbound adapter 阻断。
- 前置校准可与有效观察期请求分开归档。
- 小范围、扩展、常态、观察期均未发现正式链误触发、ZBid 写回、DOCX 生成、`output/job/export` 写入、evidence 写入或评分依据写入。

## 9. 未验证能力清单

未验证且不得推断为已开放的能力包括：

- `/generate` 正式生成链。
- `/export_docx` DOCX 导出链。
- `/review/apply` 链路。
- ZBid 写回链。
- 正式 evidence 写入。
- 正式评分依据写入。
- DOCX 生成。
- `output/job/export` 写入。
- 真实业务数据联调。
- 长期正式生产服务器运行。
- 50 人正式部署。
- 顶级本地大模型升级。
- 大规模真实并发压测。

## 10. 已发现问题与观察项清单

阻断问题：

- 当前未发现阻断 preview-only 链路的问题。

高风险问题：

- 当前未发现正式链误触发、ZBid 写回、DOCX 生成、evidence 写入、评分依据写入或 `output/job/export` 写入。

中风险问题：

- 如果未来将前置 payload 校准混入有效请求统计，会造成验收口径失真。
- 如果未来将 HTTP 200 误解为正式审批或正式链开放，会造成操作边界风险。

低风险问题：

- 试运行仍依赖人工复核 blocked_reasons、validator_result 和日志摘要。
- 主机仍只适合作为 20 人试运行主机，不适合作为长期正式生产服务器。

观察项：

- 前置校准规模偏大、口径需严格区分。
- blocked_reasons 可读性仍需持续观察。
- 错误提示、日志留痕、人工复核检查表仍可继续完善。
- 后续若延长观察期，应继续记录服务 PID、端口、请求批次、失败数、响应风险和回退记录。

## 11. 当前可继续 20 人受控常态试运行的条件

继续 20 人受控常态试运行必须同时满足：

- 用户明确授权后再启动服务、访问端口或调用 endpoint。
- 仍限定 preview-only / no-write / no-evidence。
- 仍只使用脱敏 / 模拟 / 非正式 payload。
- 五个 no-write / no-formal-chain flags 必须全部为 false。
- 前置校准必须单独计数、单独归档、不得混入有效请求。
- 不得使用真实投标 evidence。
- 不得产生评分依据。
- 不得写入正式业务数据。
- 服务启动、端口释放、日志、问题清单和回退记录必须可追踪。

## 12. 必须暂停试运行的触发条件

出现以下任一情况必须暂停试运行：

- `/generate` 被调用。
- `/export_docx` 被调用。
- `/review/apply` 被调用。
- ZBid 写回被触发。
- DOCX 被生成。
- `output/job/export` 被写入。
- preview-only 结果被作为 evidence。
- preview-only 结果被作为评分依据。
- `generate_called` 非 false。
- `export_docx_called` 非 false。
- `review_apply_called` 非 false。
- `zbid_writeback_called` 非 false。
- `output_job_export_written` 非 false。
- 前置校准与有效请求无法区分。
- 出现未知 endpoint 调用或 fallback 到正式接口。
- 服务无法关闭或端口无法释放。

## 13. 回退条件

需要回退时，应先停止试运行，再记录：

- 触发回退的时间、角色、批次、场景和 payload 类型。
- 已调用 endpoint 清单。
- 服务 PID、端口、关闭状态和端口释放状态。
- `output/job/export` 前后快照。
- 是否出现 DOCX、ZBid 写回、evidence 写入或评分依据写入。
- 是否存在前置校准计数混入有效请求。
- 是否需要另行授权修复。

未经单独授权，不得在回退现场修改代码、tests、frontend、backend、既有 docs 或持久配置。

## 14. 主机定位说明

当前主机只能定位为 20 人试运行主机。

当前主机不是：

- 长期正式生产服务器；
- 50 人正式部署服务器；
- 正式 evidence 服务器；
- 正式评分服务器；
- DOCX 生成服务器；
- ZBid 写回服务器；
- 顶级本地大模型升级实施主机。

任何生产服务器定位、正式部署定位、顶级模型升级定位都必须另行授权。

## 15. 当前不得进入事项

当前不得进入：

- 50 人正式部署。
- 正式生产服务器定位。
- 顶级模型升级。
- 正式 evidence。
- 正式评分依据。
- ZBid 写回。
- DOCX 生成。
- `output/job/export` 写入。
- 正式业务数据写入。
- 将 preview-only 结果证据化。
- 将 preview-only 结果评分化。

## 16. 后续可选路径

后续路径需要由用户单独选择并授权。可选方向包括：

1. 继续 20 人受控观察期。
   - 继续做 preview-only / no-write / no-evidence 的受控运行记录。
   - 继续保持前置校准单独计数、单独归档。

2. 做 20 人运行手册与管理员操作规程。
   - 可优先 docs-only。
   - 覆盖启动、关闭、端口、日志、问题清单、回退、停止条件和人工复核规则。

3. 做部署脚本和环境检查 docs-only 方案。
   - 仅起草方案，不实施脚本。
   - 明确后续若进入脚本实现必须另行授权。

4. 做 ZDoc / ZBid 联调边界自动化测试方案。
   - 仅起草测试方案，不运行服务、不访问端口、不调用 endpoint。
   - 明确 preview-only / no-write / no-evidence 与正式链隔离断言。

5. 暂停试运行并进入人工复盘。
   - 汇总问题、观察项、人员反馈、日志留痕和回退记录。
   - 不启动服务、不访问端口、不调用 endpoint。

## 17. Step 264 授权请求草案

以下为可复制的 Step 264 授权请求草案。该草案不代表当前已授权执行 Step 264。

```text
执行 Step 264：ZDoc-ZBid 20-user next-stage controlled routine operation decision implementation

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 263 结束后 HEAD>

特别边界：
不得访问、扫描、读取、复制、移动或分析 /Users/youfeini/Desktop/AI知识图谱大全。

本步性质：
docs-only / next-stage-decision-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

授权来源：
- Step 245 至 Step 262 已完成 20 人本地化部署、试运行、常态试运行、观察期验证与阶段归档。
- 当前 preview-only / no-write / no-evidence 边界保持成立。
- 当前未开放正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply、ZBid 写回、50 人正式部署或顶级模型升级。

拟选择路径：
<用户从以下路径中明确选择一项>
1. 继续 20 人受控观察期；
2. 起草 20 人运行手册与管理员操作规程；
3. 起草部署脚本和环境检查 docs-only 方案；
4. 起草 ZDoc / ZBid 联调边界自动化测试方案；
5. 暂停试运行并进入人工复盘。

必须继续禁止：
- 不修改代码 / tests / frontend / backend / 既有 docs，除非本步另行明确授权新增目标 docs 文件。
- 不运行服务。
- 不运行 Ollama。
- 不访问端口。
- 不调用 endpoint。
- 不触发 /generate、/export_docx、/review/apply。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 output/job/export。
- 不把 preview-only 结果作为 evidence。
- 不把 preview-only 结果作为评分依据。
- 不进入 50 人正式部署设计。
- 不实施顶级模型升级。

完成后必须停止，不得自动进入后续步骤。
```
