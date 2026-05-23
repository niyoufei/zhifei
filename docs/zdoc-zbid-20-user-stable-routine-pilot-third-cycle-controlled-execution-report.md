# ZDoc-ZBid 20-user stable routine pilot third-cycle controlled execution report

## 1. Step 255 执行摘要

本报告归档 Step 255「ZDoc-ZBid 20-user stable routine pilot third-cycle controlled execution」执行结果。

- 执行范围：约 20 人团队稳定常态试运行第三轮受控验证。
- 执行边界：preview-only / no-write / no-evidence。
- ZDoc 仓库：`/Users/youfeini/Desktop/文档生成系统`
- ZDoc 分支：`main`
- ZDoc 开始前 HEAD：`23522cbb4d076e661325482143705b756a25fece`
- ZBid 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- ZBid 分支：`local-llm-integration-clean`
- ZBid 开始前 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 本轮请求总数：40 条。
- 批次数：4 个。
- 模拟用户标识覆盖：20 个。
- 角色 / 场景覆盖：11 类。
- 异常 / 边界输入：10 条。
- ZDoc outbound adapter 成功发送 preview-only payload：是。
- ZBid receiver 成功接收 preview-only payload：是。
- ZDoc preview-only endpoint HTTP 结果：40/40 为 200。
- ZBid receiver endpoint HTTP 结果：40/40 为 200。
- `preview_only=true`、`no_write=true`、`no_evidence=true`：40/40 成立。
- 五个 no-write / no-formal-chain flags：40/40 均为 false。
- Step 254 稳定运行基线：40/40 符合。
- 与 Step 251、Step 253 对比：未发现退化。

本轮未修改代码、tests、frontend、backend 或既有 docs；仅在 ZDoc 仓库新增本报告文件。

## 2. 运行环境与端口记录

### 2.1 ZDoc 服务

- 启动命令：`ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766`
- 工作目录：`/Users/youfeini/Desktop/文档生成系统`
- PID：`67391`
- 端口：`127.0.0.1:18766`
- 用途：仅支撑本轮 preview-only 入口验证。

### 2.2 ZBid 服务

- 启动命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767`
- 工作目录：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- PID：`67392`
- 端口：`127.0.0.1:18767`
- 用途：仅支撑 ZBid preview-only receiver API 验证。

### 2.3 临时环境变量

ZDoc outbound adapter 调用期间仅使用临时环境变量：

- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`
- `PYTHONDONTWRITEBYTECODE=1`

上述配置未写入 `.env`、配置文件或任何持久文件。

### 2.4 调用 endpoint 清单

本轮仅调用 preview-only endpoint：

- ZDoc：`POST /local-trial/preview-only`
- ZBid：`POST /local-llm/zdoc-preview-only/receive`

未调用 `/generate`、`/export_docx`、`/review/apply`，未调用任何 ZBid 写回 endpoint，未调用未知业务 endpoint。

## 3. 第三轮稳定常态试运行批次安排

| 批次 | 批次名称 | 请求数 | 主要目标 | 执行方式 |
| --- | --- | ---: | --- | --- |
| B1 | 启动复核批次 | 10 | 验证服务启动后 preview-only 链路基础可用性 | 顺序请求 |
| B2 | 常态使用批次 | 12 | 覆盖常态角色与多用户使用路径 | 6 workers |
| B3 | 连续稳定批次 | 8 | 验证连续常态请求下的稳定性 | 4 workers |
| B4 | 异常边界批次 | 10 | 验证异常 / 边界输入仍保持 no-write / no-evidence | 5 workers |

合计：40 条请求，4 个批次。

## 4. 20 人用户 / 角色覆盖情况

### 4.1 模拟用户标识

本轮覆盖 20 个模拟用户标识：

`pilot3-user-01` 至 `pilot3-user-20`。

### 4.2 角色 / 场景类别

本轮覆盖 11 类角色 / 场景：

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

本轮使用脱敏 / 模拟 / preview-only payload，不包含真实投标 evidence，不产生评分依据，不写入正式业务数据。

## 5. 每个批次验证结果

| 批次 | 请求数 | ZDoc HTTP 200 | ZBid HTTP 200 | preview-only / no-write / no-evidence | 五个 flags | Step 254 基线 | 回退 |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| B1 | 10 | 10/10 | 10/10 | 全部成立 | 全部 false | 全部符合 | 不需要 |
| B2 | 12 | 12/12 | 12/12 | 全部成立 | 全部 false | 全部符合 | 不需要 |
| B3 | 8 | 8/8 | 8/8 | 全部成立 | 全部 false | 全部符合 | 不需要 |
| B4 | 10 | 10/10 | 10/10 | 全部成立 | 全部 false | 全部符合 | 不需要 |

## 6. 每个场景验证结果

| 场景 | 批次 | 模拟用户 | 角色 / 场景 | payload 类型 | HTTP | outbound | receiver | blocked_reasons | validator_result | flags | 基线 | 对比观察 | 回退 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | B1 | pilot3-user-01 | 总控管理员 | admin_control_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S02 | B1 | pilot3-user-02 | 技术标主编 | chief_editor_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S03 | B1 | pilot3-user-03 | 施工组织设计编制人员 | construction_org_writer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S04 | B1 | pilot3-user-04 | 专项施工方案编制人员 | special_plan_writer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S05 | B1 | pilot3-user-05 | 进度计划编制人员 | schedule_planner_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S06 | B1 | pilot3-user-06 | 质量安全复核人员 | quality_safety_reviewer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S07 | B1 | pilot3-user-07 | 商务 / 清单协同人员 | commercial_boq_collab_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S08 | B1 | pilot3-user-08 | 项目资料整理人员 | document_controller_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S09 | B1 | pilot3-user-09 | ZBid 评标辅助观察人员 | zbid_observer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S10 | B1 | pilot3-user-10 | 普通试用人员 | general_user_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S11 | B2 | pilot3-user-11 | 技术标主编 | chief_editor_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S12 | B2 | pilot3-user-12 | 施工组织设计编制人员 | construction_org_writer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S13 | B2 | pilot3-user-13 | 专项施工方案编制人员 | special_plan_writer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S14 | B2 | pilot3-user-14 | 进度计划编制人员 | schedule_planner_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S15 | B2 | pilot3-user-15 | 质量安全复核人员 | quality_safety_reviewer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S16 | B2 | pilot3-user-16 | 商务 / 清单协同人员 | commercial_boq_collab_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S17 | B2 | pilot3-user-17 | 项目资料整理人员 | document_controller_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S18 | B2 | pilot3-user-18 | ZBid 评标辅助观察人员 | zbid_observer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S19 | B2 | pilot3-user-19 | 普通试用人员 | general_user_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S20 | B2 | pilot3-user-20 | 总控管理员 | admin_control_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S21 | B2 | pilot3-user-01 | 技术标主编 | chief_editor_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S22 | B2 | pilot3-user-02 | 质量安全复核人员 | quality_safety_reviewer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S23 | B3 | pilot3-user-03 | 总控管理员 | admin_control_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S24 | B3 | pilot3-user-04 | 施工组织设计编制人员 | construction_org_writer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S25 | B3 | pilot3-user-05 | 进度计划编制人员 | schedule_planner_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S26 | B3 | pilot3-user-06 | 商务 / 清单协同人员 | commercial_boq_collab_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S27 | B3 | pilot3-user-07 | ZBid 评标辅助观察人员 | zbid_observer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S28 | B3 | pilot3-user-08 | 普通试用人员 | general_user_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S29 | B3 | pilot3-user-09 | 专项施工方案编制人员 | special_plan_writer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S30 | B3 | pilot3-user-10 | 质量安全复核人员 | quality_safety_reviewer_routine_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S31 | B4 | pilot3-user-11 | 异常输入 / 边界输入场景 | boundary_input_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S32 | B4 | pilot3-user-12 | 异常输入 / 边界输入场景 | boundary_input_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S33 | B4 | pilot3-user-13 | 项目资料整理人员 | document_controller_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S34 | B4 | pilot3-user-14 | 质量安全复核人员 | quality_safety_reviewer_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S35 | B4 | pilot3-user-15 | 专项施工方案编制人员 | special_plan_writer_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S36 | B4 | pilot3-user-16 | ZBid 评标辅助观察人员 | zbid_observer_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S37 | B4 | pilot3-user-17 | 普通试用人员 | general_user_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S38 | B4 | pilot3-user-18 | 商务 / 清单协同人员 | commercial_boq_collab_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S39 | B4 | pilot3-user-19 | 施工组织设计编制人员 | construction_org_writer_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |
| S40 | B4 | pilot3-user-20 | 进度计划编制人员 | schedule_planner_boundary_third_cycle_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | 可读 | false | 符合 | 无退化 | 否 |

## 7. HTTP 结果汇总

- ZDoc `POST /local-trial/preview-only`：40/40 HTTP 200。
- ZBid `POST /local-llm/zdoc-preview-only/receive`：40/40 HTTP 200。
- 非 200 响应：0。
- 失败请求：0。
- 需要回退请求：0。

延迟观察：

- ZDoc preview-only 响应时间：min 0.53 ms，median 1.27 ms，max 15.53 ms。
- ZDoc outbound -> ZBid receiver 响应时间：min 1.11 ms，median 2.72 ms，max 5.59 ms。

上述延迟仅为本地受控试运行观察，不代表正式生产容量指标。

## 8. preview-only / no-write / no-evidence 复核结果

40 条请求均满足：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

所有 payload 均仅用于 preview-only 试运行，不作为正式 evidence，不作为评分依据，不写入正式业务数据。

## 9. 禁止接口与禁止写入复核结果

本轮确认未发生：

- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未将 preview-only 结果作为 evidence。
- 未将 preview-only 结果作为评分依据。
- 未写入正式业务数据。
- 未运行 Ollama。
- 未进入 50 人正式部署设计。
- 未实施顶级模型升级。

ZDoc 与 ZBid 两侧 `output/job/export` 前后快照均无新增写入；检查时相关路径不存在，因此未发现任何输出文件。

## 10. ZDoc -> ZBid 发送与接收结果

本轮 40 条请求均完成以下链路：

1. ZDoc preview-only 入口构造 preview-only payload。
2. ZDoc outbound adapter 在临时授权环境变量下发送 preview-only payload。
3. ZBid receiver endpoint 接收 payload。
4. ZBid 返回 preview-only / no-write / no-evidence 结果。

结果：

- ZDoc outbound 已发送：40/40。
- ZBid receiver 已接收：40/40。
- ZBid receiver 返回 HTTP 200：40/40。
- 发送 payload 未包含 DOCX、正式 evidence、正式评分结果或 writeback 数据。

## 11. Step 254 稳定运行基线执行情况

本轮按 Step 254 稳定运行基线执行：

- 每条请求记录批次编号、场景编号、模拟用户标识、角色类型、请求入口和 payload 类型。
- 每条请求复核 HTTP 状态、ZDoc outbound、ZBid receiver、blocked_reasons、validator_result。
- 每条请求复核 `preview_only=true`、`no_write=true`、`no_evidence=true`。
- 每条请求复核五个禁止 flags 均为 false。
- 每条请求确认不需要回退。
- 每条请求确认未产生正式 evidence 或评分依据。
- 每条请求确认未写入正式业务数据。

结论：40/40 符合 Step 254 稳定运行基线。

## 12. 与 Step 251、Step 253 两轮结果对比

| 项目 | Step 251 第一轮 | Step 253 第二轮 | Step 255 第三轮 |
| --- | ---: | ---: | ---: |
| 请求数 | 30 | 30 | 40 |
| 批次数 | 3 | 3 | 4 |
| 模拟用户标识 | 20 | 20 | 20 |
| 角色 / 场景类别 | 11 | 11 | 11 |
| 异常 / 边界输入 | 8 | 8 | 10 |
| ZDoc HTTP 200 | 30/30 | 30/30 | 40/40 |
| ZBid HTTP 200 | 30/30 | 30/30 | 40/40 |
| preview-only / no-write / no-evidence | 30/30 | 30/30 | 40/40 |
| 五个禁止 flags false | 30/30 | 30/30 | 40/40 |
| output/job/export 写入 | 0 | 0 | 0 |
| 回退请求 | 0 | 0 | 0 |

第三轮相较前两轮增加请求数、批次数和异常 / 边界输入数量，未发现 HTTP、preview-only 边界、禁止 flags、写入边界或回退需求方面的退化。

## 13. 三轮累计稳定性观察

Step 251、Step 253、Step 255 三轮合计：

- 请求总数：100 条。
- 批次数：10 个。
- 模拟用户标识覆盖：每轮均覆盖 20 人口径。
- 角色 / 场景类别：每轮均覆盖 11 类。
- 异常 / 边界输入：26 条。
- ZDoc HTTP 200：100/100。
- ZBid HTTP 200：100/100。
- `preview_only=true`、`no_write=true`、`no_evidence=true`：100/100。
- 五个禁止 flags false：100/100。
- `output/job/export` 写入：0。
- DOCX 生成：0。
- ZBid 写回：0。
- 需要回退：0。

累计观察结论：在当前本地受控、preview-only、no-write、no-evidence 范围内，三轮常态试运行未发现阻断级问题或正式链误触发。

## 14. 异常输入 / 边界输入表现

本轮异常 / 边界输入 10 条，全部保持：

- HTTP 200。
- `preview_only=true`。
- `no_write=true`。
- `no_evidence=true`。
- 五个禁止 flags 均为 false。
- blocked_reasons 可读。
- validator_result 可读。
- 不需要回退。

边界输入中可读的 blocked_reasons 包括：

- `missing_tender_file_refs`
- `missing_scoring_clause_refs`
- `missing_evidence_anchor`
- `high_input_risk_not_validated`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

上述内容仅用于 preview-only 人工复核提示，不得作为正式 evidence 或评分依据。

## 15. 人工复核流程可用性

本轮人工复核流程可用性观察：

- 请求入口、payload 类型、角色类型与批次编号可追踪。
- blocked_reasons 可用于人工判断输入问题、配置问题和边界风险。
- validator_result 可用于确认 preview-only 校验结果。
- 五个禁止 flags 可用于快速复核是否误触正式链。
- 人工复核结论均为：继续保持 preview-only，未发现需要回退的问题。

人工复核流程仍应保持检查表化，不得将复核结果写入正式 evidence 或评分依据。

## 16. 错误提示与 blocked_reasons 可读性

本轮异常 / 边界输入均返回可读 blocked_reasons，并能表达以下含义：

- 输入缺少必要引用或证据锚点。
- preview-only 不等于写回授权。
- preview-only 不等于正式 evidence。
- ZBid preview scoring 观察不等于正式 evidence。
- 高风险输入未被正式校验时仍应保持阻断或人工复核。

结论：blocked_reasons 在本轮具备人工可读性，可继续作为试运行问题清单和人工复核提示来源；不得作为 evidence 或评分依据。

## 17. 常态运行稳定性观察

本轮常态运行观察：

- 服务启动后基础 preview-only 链路稳定。
- 常态使用批次中多用户模拟请求稳定返回。
- 连续稳定批次未出现失败请求。
- 异常边界批次未突破 no-write / no-evidence 边界。
- 无回退事件。

当前观察仅适用于本地受控试运行，不代表长期正式生产稳定性。

## 18. 并发与响应风险观察

本轮使用有限 worker 执行常态和边界批次：

- B2：6 workers。
- B3：4 workers。
- B4：5 workers。

观察结果：

- HTTP 成功率保持 100%。
- preview-only / no-write / no-evidence 保持 100%。
- 未出现端口占用、服务崩溃或请求失败。
- 未发现相较 Step 251、Step 253 的响应退化。

风险说明：

- 本轮不是正式并发压测。
- 当前主机仍仅作为 20 人试运行主机，不作为长期正式生产服务器。
- 若后续进入更高并发或正式部署设计，必须单独授权并重新定义容量、队列、日志、回退和监控要求。

## 19. 已发现问题

本轮未发现：

- 阻断级问题。
- 高风险问题。
- 正式链误触发。
- ZBid 写回。
- DOCX 生成。
- output/job/export 写入。
- evidence 写入。
- 评分依据写入。

观察项：

- 异常 / 边界输入仍需要人工复核 blocked_reasons。
- 20 人试运行主机不应被视为长期正式生产服务器。
- 后续如进入长期运行，需要补充正式运维日志、告警、备份、恢复和权限管理方案。

## 20. 风险等级

| 风险级别 | 结论 |
| --- | --- |
| 阻断级 | 未发现 |
| 高风险 | 未发现正式链误触发、写回、DOCX、evidence、评分依据写入 |
| 中风险 | 长期运行所需运维、监控、备份、恢复、权限方案尚未正式设计 |
| 低风险 | blocked_reasons、错误提示和人工复核流程仍需持续观察 |
| 观察项 | 当前仅适用于 20 人本地受控试运行，不代表正式生产 |

## 21. 回退记录

本轮无回退执行。

回退条件复核：

- 任一正式链 flag 非 false：未发生。
- `output/job/export` 写入：未发生。
- DOCX 生成：未发生。
- ZBid 写回：未发生。
- evidence 写入：未发生。
- 评分依据写入：未发生。
- 未授权 endpoint 调用：未发生。
- fallback 到正式接口：未发生。

## 22. 服务关闭与端口释放结果

本轮启动的服务已关闭：

- ZDoc PID `67391` 已停止。
- ZBid PID `67392` 已停止。

端口释放结果：

- `127.0.0.1:18766` 无监听。
- `127.0.0.1:18767` 无监听。

ZDoc 与 ZBid 两侧未产生 `output/job/export` 写入。

## 23. 是否建议进入 Step 256

建议进入 Step 256，但仅限“第三轮稳定常态试运行 stage review / 稳定运行基线归档 / 后续授权请求”类 docs-only 工作。

Step 256 不得默认获得以下授权：

- 不得修改代码。
- 不得启动服务。
- 不得访问端口。
- 不得调用 endpoint。
- 不得进入 50 人正式部署设计。
- 不得实施顶级模型升级。
- 不得开放正式链。
- 不得生成 DOCX。
- 不得写 `output/job/export`。
- 不得触发 ZBid 写回。

## 24. Step 256 授权请求草案

可复制授权语：

```text
执行 Step 256：ZDoc-ZBid 20-user stable routine pilot third-cycle review and continued operation authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<待填入 Step 255 结束后 HEAD>

本步性质：
docs-only / stage-review-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

授权范围：
仅允许新增 Step 255 第三轮稳定常态试运行 stage review 与后续继续试运行授权请求文档。

必须记录：
1. Step 255 第三轮 40 条请求、4 个批次、20 个模拟用户、11 类角色 / 场景、10 条异常 / 边界输入结果。
2. ZDoc 与 ZBid 均 HTTP 200。
3. preview_only=true、no_write=true、no_evidence=true。
4. generate_called=false、export_docx_called=false、review_apply_called=false、zbid_writeback_called=false、output_job_export_written=false。
5. 符合 Step 254 稳定运行基线。
6. 与 Step 251、Step 253 对比未发现退化。
7. 未运行 Ollama，未触发 /generate、/export_docx、/review/apply、ZBid 写回。
8. 未生成 DOCX，未写 output/job/export。
9. 当前仍仅为 20 人本地试运行边界，不代表正式生产服务器，不进入 50 人正式部署设计，不实施顶级模型升级。

严格禁止：
不修改代码 / tests / frontend / backend / 既有 docs。
不启动服务。
不访问端口。
不调用任何 endpoint。
不触发 /generate、/export_docx、/review/apply。
不触发 ZBid 写回。
不生成 DOCX。
不写 output/job/export。
不把 preview-only 结果作为 evidence 或评分依据。
不进入 50 人正式部署设计。
不实施顶级模型升级。
不进入 Step 257。
```
