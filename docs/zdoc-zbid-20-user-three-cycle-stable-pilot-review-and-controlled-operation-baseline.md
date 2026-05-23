# ZDoc-ZBid 20-user three-cycle stable pilot review and controlled operation baseline

## 1. Step 251、Step 253、Step 255 三轮稳定常态试运行总复盘

本文档归档 ZDoc-ZBid 20 人试运行口径下三轮稳定常态试运行的总复盘，并形成受控常态试运行观察期的运行基线。

三轮范围均保持：

- preview-only
- no-write
- no-evidence
- 不开放正式生成链
- 不开放正式证据链
- 不开放评分依据写入
- 不开放 DOCX 导出
- 不开放 review/apply
- 不开放 ZBid 写回

三轮对应步骤：

| 步骤 | 轮次 | 性质 | 结果 |
| --- | --- | --- | --- |
| Step 251 | 第一轮常态试运行 | 20 人口径 routine pilot controlled execution | 30 条请求通过 |
| Step 253 | 第二轮常态试运行 | 按 Step 252 运行管理基线复验 | 30 条请求通过 |
| Step 255 | 第三轮稳定常态试运行 | 按 Step 254 稳定运行基线复验 | 40 条请求通过 |

结论：三轮均未发现阻断 preview-only 链路的问题，未发现正式链误触发、写回、DOCX、evidence、评分依据写入或 output/job/export 写入。

## 2. 三轮结果摘要

三轮合计结果：

- 请求总数：100 条。
- 批次数：10 个。
- 模拟用户标识：20 个。
- 角色 / 场景：11 类。
- 异常 / 边界输入：26 条。
- ZDoc HTTP 200：100/100。
- ZBid HTTP 200：100/100。
- `preview_only=true`：100/100。
- `no_write=true`：100/100。
- `no_evidence=true`：100/100。
- 五个禁止 flags 均为 false：100/100。
- 需要回退请求：0。
- output/job/export 写入：0。
- DOCX 生成：0。
- ZBid 写回：0。

分轮摘要：

| 轮次 | 请求数 | 批次数 | 模拟用户 | 角色 / 场景 | 异常 / 边界输入 | 结果 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Step 251 第一轮 | 30 | 3 | 20 | 11 | 8 | 通过 |
| Step 253 第二轮 | 30 | 3 | 20 | 11 | 8 | 通过 |
| Step 255 第三轮 | 40 | 4 | 20 | 11 | 10 | 通过 |
| 合计 | 100 | 10 | 20 | 11 | 26 | 通过 |

## 3. 三轮 HTTP 200 结果汇总

| 轮次 | ZDoc preview-only HTTP 200 | ZBid receiver HTTP 200 | 非 200 | 失败请求 |
| --- | ---: | ---: | ---: | ---: |
| Step 251 | 30/30 | 30/30 | 0 | 0 |
| Step 253 | 30/30 | 30/30 | 0 | 0 |
| Step 255 | 40/40 | 40/40 | 0 | 0 |
| 合计 | 100/100 | 100/100 | 0 | 0 |

HTTP 结果结论：三轮均保持 ZDoc preview-only 入口和 ZBid preview-only receiver 入口可达，未出现 HTTP 层失败。

## 4. preview-only / no-write / no-evidence 三轮复核结论

三轮所有请求均满足：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

复核结论：

- preview-only 链路成立。
- no-write 边界成立。
- no-evidence 边界成立。
- preview-only 结果不得写入正式业务数据。
- preview-only 结果不得作为正式 evidence。
- preview-only 结果不得作为评分依据。

## 5. 五个禁止 flags 三轮复核结论

三轮所有请求均确认以下 flags 为 false：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

复核结论：

- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未写 `output/job/export`。

任一 flag 后续如非 false，必须立即暂停试运行并进入回退与问题记录流程。

## 6. 与 Step 254 稳定运行基线的一致性结论

Step 255 已按 Step 254 稳定运行基线执行，并与 Step 251、Step 253 的结果形成三轮连续复核。

一致性结论：

- 每轮均覆盖 20 人口径的模拟用户标识。
- 每轮均覆盖 11 类角色 / 场景。
- 每轮均包含异常 / 边界输入。
- 每轮均复核 preview-only / no-write / no-evidence。
- 每轮均复核五个禁止 flags。
- 每轮均确认未生成 DOCX、未写 output/job/export、未触发 ZBid 写回。
- 每轮均形成运行报告和阶段性基线。

结论：三轮结果与 Step 254 稳定运行基线一致。

## 7. 是否存在退化的结论

三轮对比未发现退化：

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

Step 255 在请求数、批次数和异常 / 边界输入数上高于前两轮，仍未发现退化。

## 8. 已验证能力清单

已验证能力：

- ZDoc preview-only 入口在本地试运行中可达。
- ZDoc outbound adapter 可在临时授权环境变量下发送 preview-only payload。
- ZBid preview-only receiver API 可接收 preview-only payload。
- ZDoc -> ZBid preview-only 链路可完成发送与接收。
- preview_packet 可读。
- validator_result 可读。
- blocked_reasons 可读。
- 五个禁止 flags 可被复核。
- 异常 / 边界输入可保持 no-write / no-evidence。
- 三轮常态试运行均未触发正式链。
- 三轮常态试运行均未产生 DOCX。
- 三轮常态试运行均未写 output/job/export。
- 三轮常态试运行均未触发 ZBid 写回。
- 20 人试运行口径下的代表性角色与流程验证可成立。

## 9. 未验证能力清单

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

上述事项不得因三轮 preview-only 试运行通过而被视为已开放或已授权。

## 10. 已发现问题清单

三轮未发现以下问题：

- 未发现阻断级 preview-only 链路问题。
- 未发现正式链误触发。
- 未发现 ZBid 写回。
- 未发现 DOCX 生成。
- 未发现 output/job/export 写入。
- 未发现 evidence 写入。
- 未发现评分依据写入。

观察项：

- blocked_reasons 仍需人工复核，不能自动解释为正式结论。
- 当前主机仅适合 20 人试运行观察，不应定位为长期正式生产服务器。
- 长期运行仍需要独立设计运维日志、权限、告警、备份、恢复、变更控制和停机回退方案。
- 如后续需要 UI、日志或错误提示优化，必须另行授权。

## 11. 问题分级

| 级别 | 当前结论 | 处置要求 |
| --- | --- | --- |
| 阻断级 | 未发现 | 如后续出现，立即暂停试运行 |
| 高风险 | 未发现正式链误触发、写回、DOCX、evidence、评分依据写入 | 如后续出现，立即停止并回退 |
| 中风险 | 正式运维、权限、日志、备份、恢复方案尚未形成 | 后续需单独设计和授权 |
| 低风险 | 错误提示、blocked_reasons 可读性、人工复核流程仍需持续观察 | 纳入问题清单持续记录 |
| 观察项 | 当前仅为 preview-only 试运行，不代表正式生产 | 每轮试运行后复核边界 |

## 12. 20 人试运行阶段稳定性验收结论

验收结论：

- 20 人试运行阶段的 preview-only / no-write / no-evidence 链路可作为受控常态试运行观察期基线。
- 三轮累计 100 条请求均通过，未发现退化。
- 当前可继续在 20 人试运行边界内观察运行稳定性、错误提示、blocked_reasons 可读性、日志留痕和人工复核流程。

限制说明：

- 该结论不代表正式生产验收。
- 该结论不代表 50 人正式部署设计已授权。
- 该结论不代表正式链开放。
- 该结论不代表顶级模型升级已授权。

## 13. 当前可进入受控常态试运行观察期的条件

可进入受控常态试运行观察期的条件：

- 继续限定 20 人试运行口径。
- 继续限定 preview-only / no-write / no-evidence。
- 继续使用脱敏样例、测试文档、非正式投标成果。
- 每次启动服务前记录仓库、分支、HEAD、git status。
- 每次启动服务前确认端口范围和 endpoint 范围已授权。
- 每次运行后关闭服务并确认端口释放。
- 每次运行前后检查 output/job/export。
- 每次运行记录日志、问题清单、回退记录。
- 任一正式链 flag 非 false 时立即暂停。
- 任何代码修改、服务范围扩大、端口变更、endpoint 变更均需单独授权。

## 14. 当前不得进入的事项

当前不得进入：

- 50 人正式部署。
- 长期正式生产服务器定位。
- 顶级模型升级实施。
- 正式生成链。
- 正式证据链。
- 正式评分链。
- 正式导出链。
- review/apply 正式流程。
- ZBid 写回。
- DOCX 生成。
- output/job/export 写入。
- preview-only 结果证据化。
- preview-only 结果评分化。
- 真实业务联调。

上述事项必须另行申请授权，不得由三轮试运行结果自动推导。

## 15. preview-only / no-write / no-evidence 长期运行边界

长期运行边界：

- 所有试运行请求必须明确为 preview-only。
- 所有试运行请求必须保持 no-write。
- 所有试运行请求必须保持 no-evidence。
- 试运行结果仅用于人工观察、问题记录和流程复盘。
- 试运行结果不得写入正式业务数据。
- 试运行结果不得作为正式 evidence。
- 试运行结果不得作为评分依据。
- 不得 fallback 到正式接口。
- 不得在未授权情况下扩大 endpoint 范围。

## 16. 禁止接口、禁止写入、禁止证据化、禁止评分化要求

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

## 17. 主机定位说明

当前主机定位：

- 仅作为 20 人试运行主机。
- 仅用于 preview-only / no-write / no-evidence 受控观察。
- 不作为长期正式生产服务器。
- 不承诺正式生产 SLA。
- 不承诺正式并发容量。
- 不承诺正式备份、恢复、告警和权限体系已完成。

如需将主机定位为正式生产服务器，必须另行完成部署设计、运维设计、安全边界、备份恢复、日志告警、权限控制、回退方案和验收标准。

## 18. 服务启动、端口、关闭、日志、问题清单、回退记录管理要求

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

## 19. 必须暂停试运行的触发条件

出现以下任一情况，必须立即暂停试运行：

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

暂停后不得现场修复，必须先形成问题记录和后续授权请求。

## 20. 回退条件

必须回退的条件：

- 任一正式链 flag 非 false。
- 任一禁止接口被调用。
- 任一禁止写入发生。
- 任一 evidence 或评分依据写入发生。
- ZBid 写回发生。
- DOCX 生成发生。
- output/job/export 写入发生。
- 未授权端口或 endpoint 被使用。
- 服务关闭失败或端口释放失败。

回退动作边界：

- 停止本次试运行。
- 关闭本次启动的服务。
- 确认端口释放。
- 记录问题清单。
- 记录 output/job/export 前后状态。
- 不修改代码。
- 不进入正式链。
- 不继续扩大试运行。
- 后续修复必须另行授权。

## 21. Step 257 授权请求草案

可复制授权语：

```text
执行 Step 257：ZDoc-ZBid 20-user controlled routine observation period authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<待填入 Step 256 结束后 HEAD>

本步性质：
docs-only / authorization-request-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
基于 Step 256 三轮稳定常态试运行总复盘与受控运行基线，起草 20 人受控常态试运行观察期授权请求文档。该文档只代表申请授权，不代表已启动观察期。

文档必须限定：
1. 继续保持 preview-only / no-write / no-evidence。
2. 继续禁止 /generate、/export_docx、/review/apply、ZBid 写回。
3. 继续禁止 DOCX 生成、output/job/export 写入。
4. 继续禁止 preview-only 结果 evidence 化或评分化。
5. 明确观察期人员、数据、服务、端口、endpoint、日志、问题清单、回退条件。
6. 明确当前主机仅作为 20 人试运行主机，不作为长期正式生产服务器。
7. 明确不进入 50 人正式部署设计。
8. 明确不实施顶级模型升级。

严格禁止：
不修改代码 / tests / frontend / backend / 既有 docs。
不启动服务。
不访问端口。
不调用任何 endpoint。
不触发 /generate、/export_docx、/review/apply。
不触发 ZBid 写回。
不生成 DOCX。
不写 output/job/export。
不把 preview-only 结果作为 evidence。
不把 preview-only 结果作为评分依据。
不进入 50 人正式部署设计。
不实施顶级模型升级。
不进入 Step 258。
```
