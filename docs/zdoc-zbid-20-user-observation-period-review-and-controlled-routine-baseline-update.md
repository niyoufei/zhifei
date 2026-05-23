# ZDoc-ZBid 20-user observation-period review and controlled routine baseline update

## 1. Step 257 观察期执行结果复盘

本文档归档 Step 257「ZDoc-ZBid 20-user controlled routine observation-period execution」结果，并在 Step 256 三轮稳定基线基础上更新 20 人受控常态试运行基线。

Step 257 执行范围：

- 20 人受控常态观察期验证。
- preview-only / no-write / no-evidence。
- 允许启动 ZDoc 与 ZBid 本地必要服务。
- 允许调用经授权 preview-only endpoint。
- 允许临时启用 preview-only network-send。
- 仅允许在 ZDoc 仓库新增观察期执行报告。

Step 257 执行结论：

- 有效观察期 50 条请求通过。
- 有效观察期 5 个批次通过。
- 覆盖 20 个模拟用户标识。
- 覆盖 11 类角色 / 场景。
- 覆盖 12 条异常 / 边界输入。
- ZDoc 与 ZBid 有效观察期调用均 HTTP 200。
- `preview_only=true`、`no_write=true`、`no_evidence=true` 均成立。
- 五个禁止 flags 均为 false。
- 符合 Step 256 三轮稳定基线。
- 与 Step 251、Step 253、Step 255 对比未发现退化。

Step 257 中出现一次前置 payload 校准：第一组 50 条请求因 ZBid status 枚举值不合法，被 ZDoc outbound adapter 阻断发送。该校准单独归档，不计入 ZBid 有效观察期调用。

## 2. 有效观察期结果摘要

有效观察期结果：

- 请求数：50 条。
- 批次数：5 个。
- 模拟用户标识：20 个。
- 角色 / 场景：11 类。
- 异常 / 边界输入：12 条。
- ZDoc HTTP 200：50/50。
- ZBid HTTP 200：50/50。
- `preview_only=true`：50/50。
- `no_write=true`：50/50。
- `no_evidence=true`：50/50。
- 五个禁止 flags false：50/50。
- ZDoc outbound 已发送：50/50。
- ZBid receiver 已接收：50/50。
- 需要回退请求：0。
- output/job/export 写入：0。
- DOCX 生成：0。
- ZBid 写回：0。

批次摘要：

| 批次 | 名称 | 有效请求数 | 结果 |
| --- | --- | ---: | --- |
| B1 | 启动复核批次 | 10 | 通过 |
| B2 | 常态使用批次 | 12 | 通过 |
| B3 | 连续观察批次 | 10 | 通过 |
| B4 | 异常边界批次 | 12 | 通过 |
| B5 | 关闭前复核批次 | 6 | 通过 |

## 3. 前置 payload 校准 50 条的单独说明

前置 payload 校准发生在 Step 257 正式有效观察期前。

校准事实：

- 校准请求数：50 条。
- ZDoc `POST /local-trial/preview-only`：50/50 HTTP 200。
- ZBid receiver 调用：0/50。
- ZDoc outbound adapter 发送：0/50。
- 阻断原因：payload 中 `zbid_input_status`、`zbid_mapping_status`、`zbid_scoring_matrix_status` 使用了非枚举值。
- 结果：adapter 按 preview-only / no-write 安全边界阻断发送，未 fallback 到正式接口。

校准期间未发生：

- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- 未写 output/job/export。
- 未把 preview-only 结果作为 evidence。
- 未把 preview-only 结果作为评分依据。

## 4. 非法 ZBid status 枚举被 outbound adapter 阻断的归档说明

Step 257 前置校准中，非法 ZBid status 枚举被识别为 preview-only payload 问题。

归档结论：

- 该问题属于 payload 构造观察项，不属于正式链误触发。
- outbound adapter 未发送不合法 payload 至 ZBid receiver。
- adapter 阻断行为符合 no-write / no-evidence 边界。
- adapter 未 fallback 到 `/generate`、`/export_docx`、`/review/apply` 或其他正式接口。
- adapter 未触发 ZBid 写回。
- adapter 未产生 output/job/export 写入。

后续要求：

- 观察期 payload 应使用合法 preview-only 枚举值或 route 默认值。
- 如后续需要优化错误提示或 payload 构造约束，必须单独授权。
- 不得现场修改代码修复。

## 5. 前置校准不计入 ZBid 有效观察期调用

前置校准不计入有效观察期通过统计，原因如下：

- 该阶段未调用 ZBid receiver endpoint。
- 该阶段用于发现和确认 payload 枚举校准问题。
- ZDoc outbound adapter 已在发送前阻断。
- 未形成 ZDoc -> ZBid 有效观察期链路。

有效观察期统计仅包括随后重新执行的 50 条合法 preview-only payload：

- ZDoc outbound 已发送：50/50。
- ZBid receiver 已接收：50/50。
- ZBid receiver HTTP 200：50/50。

## 6. HTTP 200 结果汇总

有效观察期 HTTP 结果：

| 项目 | 结果 |
| --- | ---: |
| ZDoc preview-only HTTP 200 | 50/50 |
| ZBid receiver HTTP 200 | 50/50 |
| 非 200 响应 | 0 |
| 失败请求 | 0 |

前置 payload 校准 HTTP 结果：

| 项目 | 结果 |
| --- | ---: |
| ZDoc preview-only HTTP 200 | 50/50 |
| ZBid receiver 调用 | 0/50 |
| outbound adapter 发送 | 0/50 |

结论：有效观察期 HTTP 层未发现失败；前置校准的 ZBid 调用为 0，是 adapter 阻断后的预期结果。

## 7. preview-only / no-write / no-evidence 复核结论

有效观察期 50 条请求均满足：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

复核结论：

- ZDoc preview-only 入口可构造 preview-only payload。
- ZDoc outbound adapter 可发送 preview-only payload。
- ZBid receiver 可接收并返回 no-write / no-evidence 状态。
- 观察期结果不得写入正式业务数据。
- 观察期结果不得作为 evidence。
- 观察期结果不得作为评分依据。

前置校准同样未突破 no-write 边界，因为不合法 payload 被阻断发送。

## 8. 五个禁止 flags 复核结论

有效观察期 50 条请求均满足：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

复核结论：

- 未触发正式生成链。
- 未触发 DOCX 导出链。
- 未触发 review/apply 链。
- 未触发 ZBid 写回。
- 未写 output/job/export。

任一 flag 后续如非 false，必须立即暂停试运行并进入回退流程。

## 9. 与 Step 251、Step 253、Step 255、Step 256 的一致性结论

Step 256 汇总的三轮稳定基线：

- Step 251：30 条请求、3 个批次、20 个模拟用户、11 类角色 / 场景、8 条异常 / 边界输入。
- Step 253：30 条请求、3 个批次、20 个模拟用户、11 类角色 / 场景、8 条异常 / 边界输入。
- Step 255：40 条请求、4 个批次、20 个模拟用户、11 类角色 / 场景、10 条异常 / 边界输入。

Step 257 有效观察期：

- 50 条请求、5 个批次、20 个模拟用户、11 类角色 / 场景、12 条异常 / 边界输入。

一致性结论：

- 均保持 preview-only / no-write / no-evidence。
- 均保持五个禁止 flags false。
- 均未生成 DOCX。
- 均未写 output/job/export。
- 均未触发 ZBid 写回。
- 均未把 preview-only 结果作为 evidence 或评分依据。

Step 257 继承 Step 256 三轮稳定基线，并在有效请求数、批次数和异常 / 边界输入数上扩展观察。

## 10. 是否存在退化的结论

未发现退化：

- HTTP 200 成功率未退化。
- preview-only / no-write / no-evidence 未退化。
- 五个禁止 flags 未退化。
- ZDoc outbound 发送能力未退化。
- ZBid receiver 接收能力未退化。
- blocked_reasons 可读性未退化。
- validator_result 可读性未退化。
- output/job/export 零写入边界未退化。
- DOCX 零生成边界未退化。
- ZBid 零写回边界未退化。

前置校准不是运行退化，而是 payload enum 使用不合法后的安全阻断，需作为后续观察项管理。

## 11. 已验证能力清单

已验证能力：

- ZDoc preview-only 入口在本地受控观察期可达。
- ZDoc outbound adapter 可在临时授权环境变量下发送 preview-only payload。
- ZDoc outbound adapter 可阻断不合法 payload，且不 fallback 到正式接口。
- ZBid preview-only receiver 可接收合法 preview-only payload。
- ZDoc -> ZBid preview-only 链路可完成发送与接收。
- preview_packet 可读。
- validator_result 可读。
- blocked_reasons 可读。
- 五个禁止 flags 可被逐条复核。
- 异常 / 边界输入可保持 no-write / no-evidence。
- 20 人受控常态观察期可按批次、角色、模拟用户记录。
- 未触发正式链、写回、DOCX、output/job/export。

## 12. 未验证能力清单

未验证能力：

- 未验证 50 人正式部署。
- 未验证长期正式生产服务器运行。
- 未验证正式生成链开放。
- 未验证正式 evidence 写入。
- 未验证评分依据写入。
- 未验证 DOCX 正式导出。
- 未验证 review/apply 正式流程。
- 未验证 ZBid 正式写回。
- 未验证真实业务联调。
- 未验证真实投标 evidence 进入链路。
- 未验证顶级本地模型升级。
- 未验证高并发压测、队列、熔断、告警、备份、恢复和正式运维方案。
- 未验证多终端真实登录和权限体系。

这些事项不得因 Step 257 观察期通过而被视为已授权或已完成。

## 13. 已发现问题与观察项清单

已发现问题：

- 未发现阻断级 preview-only 链路问题。
- 未发现正式链误触发。
- 未发现 ZBid 写回。
- 未发现 DOCX 生成。
- 未发现 output/job/export 写入。
- 未发现 evidence 写入。
- 未发现评分依据写入。

观察项：

- 前置 payload 校准中，非法 ZBid status 枚举被 adapter 阻断发送。
- payload 构造应继续使用合法 preview-only 枚举值或 route 默认值。
- blocked_reasons 仍需人工复核，不能自动作为正式结论。
- 当前主机仍仅适合作为 20 人试运行主机。
- 长期运行所需正式运维、日志、告警、备份、恢复和权限方案尚未形成。

## 14. 问题分级

| 级别 | 当前结论 | 处置要求 |
| --- | --- | --- |
| 阻断级 | 未发现 | 如后续出现，立即暂停试运行 |
| 高风险 | 未发现正式链误触发、写回、DOCX、evidence、评分依据写入 | 如后续出现，立即停止并回退 |
| 中风险 | 正式运维、权限、日志、备份、恢复方案尚未形成 | 后续需单独设计和授权 |
| 低风险 | 非法 ZBid status 枚举会被 adapter 阻断发送 | 继续使用合法枚举或默认值，必要优化另行授权 |
| 观察项 | blocked_reasons、错误提示、人工复核流程仍需持续观察 | 纳入常态观察期记录 |

## 15. 20 人受控常态观察期阶段结论

阶段结论：

- 20 人受控常态观察期有效请求通过。
- Step 257 扩展了 Step 256 三轮稳定基线。
- 当前可继续在 20 人 preview-only / no-write / no-evidence 边界内进行受控常态试运行。
- 当前不代表正式生产验收。
- 当前不代表 50 人正式部署设计已授权。
- 当前不代表正式链开放。
- 当前不代表顶级模型升级已授权。

## 16. 当前可继续受控常态试运行的条件

继续试运行必须满足：

- 继续限定 20 人试运行口径。
- 继续限定 preview-only / no-write / no-evidence。
- 继续使用脱敏样例、测试文档、非正式投标成果。
- 使用合法 preview-only payload 枚举值或 route 默认值。
- 每次启动服务前记录仓库、分支、HEAD、git status。
- 每次启动服务前确认端口范围和 endpoint 范围已授权。
- 每次运行后关闭服务并确认端口释放。
- 每次运行前后检查 output/job/export。
- 每次运行记录日志、问题清单、回退记录。
- 任一正式链 flag 非 false 时立即暂停。
- 任何代码修改、服务范围扩大、端口变更、endpoint 变更均需单独授权。

## 17. 必须暂停试运行的触发条件

出现以下任一情况，必须暂停试运行：

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
- 写入 output/job/export。
- 产生正式 evidence。
- 产生评分依据。
- 写入正式业务数据。
- 调用未授权 endpoint。
- fallback 到正式接口。
- 服务无法关闭或端口无法释放。
- 出现敏感业务数据泄漏风险。

暂停后不得现场修改代码，必须先形成问题记录和后续授权请求。

## 18. preview-only / no-write / no-evidence 长期运行边界

长期运行边界：

- 所有试运行请求必须明确为 preview-only。
- 所有试运行请求必须保持 no-write。
- 所有试运行请求必须保持 no-evidence。
- 试运行结果仅用于人工观察、问题记录和流程复盘。
- 试运行结果不得写入正式业务数据。
- 试运行结果不得作为 evidence。
- 试运行结果不得作为评分依据。
- 不得 fallback 到正式接口。
- 不得在未授权情况下扩大 endpoint 范围。

## 19. 禁止接口、禁止写入、禁止证据化、禁止评分化要求

继续禁止：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- DOCX 生成
- output/job/export 写入
- preview-only 结果作为 evidence
- preview-only 结果作为评分依据
- 正式业务数据写入
- 未授权服务启动
- 未授权端口访问
- 未授权 endpoint 调用
- 未授权真实业务联调
- 未授权 50 人正式部署设计
- 未授权顶级模型升级实施

## 20. 主机定位说明

当前主机定位：

- 仅作为 20 人试运行主机。
- 仅用于 preview-only / no-write / no-evidence 受控观察。
- 不作为长期正式生产服务器。
- 不承诺正式生产 SLA。
- 不承诺正式并发容量。
- 不承诺正式备份、恢复、告警和权限体系已完成。

如需将主机定位为正式生产服务器，必须另行完成部署设计、运维设计、安全边界、备份恢复、日志告警、权限控制、回退方案和验收标准。

## 21. 服务启动、端口、关闭、日志、问题清单、回退记录管理要求

服务启动要求：

- 每次启动前确认授权范围。
- 每次启动前记录 ZDoc / ZBid 仓库、分支、HEAD、git status。
- 每次启动前确认端口未被占用。
- 仅启动 preview-only 相关必要服务。
- 不运行 Ollama，除非未来另行授权。

端口管理要求：

- 仅使用授权端口。
- 如端口被占用，需记录原因、实际端口、PID、关闭结果和端口释放结果。
- 每次结束后必须确认端口无监听。

日志管理要求：

- 记录时间、批次、场景、模拟用户标识、角色、请求入口、payload 类型。
- 记录 HTTP 状态、preview-only / no-write / no-evidence 状态。
- 记录五个禁止 flags。
- 记录 blocked_reasons 和 validator_result 可读性。
- 不记录敏感业务数据。
- 不记录正式 evidence。
- 不写入正式评分依据。

问题清单要求：

- 区分阻断级、高风险、中风险、低风险和观察项。
- 明确是否触发暂停条件。
- 明确是否需要回退。
- 明确是否需要单独授权修复。
- 不得现场修改代码修复。

回退记录要求：

- 记录触发原因。
- 记录涉及批次、场景、用户标识、端口和 endpoint。
- 记录服务关闭结果。
- 记录 output/job/export 检查结果。
- 记录后续是否需要单独授权。

## 22. Step 259 授权请求草案

可复制授权语：

```text
执行 Step 259：ZDoc-ZBid 20-user continued controlled routine observation-period execution。

一、仓库与分支

ZDoc 仓库：
/Users/youfeini/Desktop/文档生成系统

ZDoc 分支：
main

ZDoc 开始前 HEAD：
<待填入 Step 258 结束后 HEAD>

ZBid 仓库：
/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean

ZBid 分支：
local-llm-integration-clean

ZBid 开始前 HEAD：
378355755372e03ac4f4064af59b287054984c25

二、授权范围

允许：
1. 启动必要的 ZDoc 本地服务；
2. 启动必要的 ZBid 本地服务；
3. 访问必要本地端口；
4. 调用经授权的 preview-only endpoint；
5. 临时启用 preview-only network-send；
6. 按 Step 258 更新后的受控常态基线执行继续观察期验证；
7. 记录运行日志、问题清单、回退记录和观察期运行报告；
8. 在 ZDoc 仓库仅新增 1 个 docs 报告文件。

三、验证要求

1. 继续保持 preview-only / no-write / no-evidence。
2. 继续使用脱敏 / 模拟 / preview-only payload。
3. 继续覆盖 20 人试运行口径、11 类角色 / 场景和异常 / 边界输入。
4. 继续复核五个禁止 flags：
   - generate_called=false
   - export_docx_called=false
   - review_apply_called=false
   - zbid_writeback_called=false
   - output_job_export_written=false
5. 继续复核是否符合 Step 258 受控常态基线。
6. 继续记录非法 payload 或 blocked_reasons，但不得现场修代码。

四、严格禁止

不修改代码 / tests / frontend / backend / 既有 docs。
不运行 Ollama。
不触发 /generate、/export_docx、/review/apply。
不触发 ZBid 写回。
不生成 DOCX。
不写 output/job/export。
不把 preview-only 结果作为 evidence。
不把 preview-only 结果作为评分依据。
不进入 50 人正式部署设计。
不实施顶级模型升级。
不自动进入 Step 260。
```
