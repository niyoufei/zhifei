# ZDoc-ZBid 20-user controlled routine observation-period execution report

## 1. Step 257 执行摘要

本报告归档 Step 257「ZDoc-ZBid 20-user controlled routine observation-period execution」执行结果。

- ZDoc 仓库：`/Users/youfeini/Desktop/文档生成系统`
- ZDoc 分支：`main`
- ZDoc 开始前 HEAD：`c1ef07cc72b72a44df7f2e014d68197c09b0c187`
- ZBid 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- ZBid 分支：`local-llm-integration-clean`
- ZBid 开始前 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 执行边界：preview-only / no-write / no-evidence。
- 本轮有效观察期请求数：50 条。
- 批次数：5 个。
- 模拟用户标识覆盖：20 个。
- 角色 / 场景覆盖：11 类。
- 异常 / 边界输入：12 条。
- ZDoc HTTP 200：50/50。
- ZBid HTTP 200：50/50。
- `preview_only=true`、`no_write=true`、`no_evidence=true`：50/50。
- 五个禁止 flags 均为 false：50/50。
- Step 256 三轮稳定基线：50/50 符合。
- 与 Step 251、Step 253、Step 255 对比：未发现退化。

执行中出现一次前置 payload 校准：第一组 50 条请求因 `zbid_input_status`、`zbid_mapping_status`、`zbid_scoring_matrix_status` 使用了非枚举值，ZDoc route 返回 HTTP 200，但 outbound adapter 按 preview-only 安全边界阻断发送，未调用 ZBid receiver。该前置校准未触发正式链、未写入、未生成 DOCX、未写回；随后使用合法 preview-only 枚举和默认值重新执行 50 条有效观察期请求并全部通过。

## 2. 运行环境与端口记录

### 2.1 ZDoc 服务

- 启动命令：`ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766`
- 工作目录：`/Users/youfeini/Desktop/文档生成系统`
- PID：`71818`
- 端口：`127.0.0.1:18766`
- 用途：支撑本轮 ZDoc preview-only 入口。

### 2.2 ZBid 服务

- 启动命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767`
- 工作目录：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- PID：`71819`
- 端口：`127.0.0.1:18767`
- 用途：支撑本轮 ZBid preview-only receiver。

### 2.3 临时环境变量

仅在本轮 ZDoc outbound adapter 调用进程内临时启用：

- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive`
- `PYTHONDONTWRITEBYTECODE=1`

上述配置未写入 `.env`、配置文件或持久化文件。

## 3. 观察期批次安排

| 批次 | 批次名称 | 有效请求数 | 执行目标 | 执行方式 |
| --- | --- | ---: | --- | --- |
| B1 | 启动复核批次 | 10 | 服务启动后 preview-only 链路复核 | 顺序请求 |
| B2 | 常态使用批次 | 12 | 多角色、多用户常态请求观察 | 6 workers |
| B3 | 连续观察批次 | 10 | 连续观察期稳定性 | 5 workers |
| B4 | 异常边界批次 | 12 | 异常 / 边界输入保持 no-write / no-evidence | 6 workers |
| B5 | 关闭前复核批次 | 6 | 服务关闭前链路复核 | 3 workers |

有效观察期请求合计 50 条。

## 4. 20 人用户 / 角色覆盖情况

### 4.1 模拟用户标识

本轮有效观察期覆盖 20 个模拟用户标识：

`obs-user-01` 至 `obs-user-20`。

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

本轮数据均为脱敏 / 模拟 / preview-only payload，不包含真实投标 evidence，不产生评分依据，不写入正式业务数据。

## 5. 每个批次验证结果

| 批次 | 有效请求数 | ZDoc HTTP 200 | ZBid HTTP 200 | preview-only / no-write / no-evidence | 五个 flags | Step 256 基线 | 回退 |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| B1 | 10 | 10/10 | 10/10 | 全部成立 | 全部 false | 全部符合 | 不需要 |
| B2 | 12 | 12/12 | 12/12 | 全部成立 | 全部 false | 全部符合 | 不需要 |
| B3 | 10 | 10/10 | 10/10 | 全部成立 | 全部 false | 全部符合 | 不需要 |
| B4 | 12 | 12/12 | 12/12 | 全部成立 | 全部 false | 全部符合 | 不需要 |
| B5 | 6 | 6/6 | 6/6 | 全部成立 | 全部 false | 全部符合 | 不需要 |

## 6. 每个场景验证结果

| 场景 | 批次 | 用户 | 角色 / 场景 | payload 类型 | HTTP | outbound | receiver | 可读性 | flags | 基线 | 回退 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | B1 | obs-user-01 | 总控管理员 | admin_control_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S02 | B1 | obs-user-02 | 技术标主编 | chief_editor_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S03 | B1 | obs-user-03 | 施工组织设计编制人员 | construction_org_writer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S04 | B1 | obs-user-04 | 专项施工方案编制人员 | special_plan_writer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S05 | B1 | obs-user-05 | 进度计划编制人员 | schedule_planner_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S06 | B1 | obs-user-06 | 质量安全复核人员 | quality_safety_reviewer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S07 | B1 | obs-user-07 | 商务 / 清单协同人员 | commercial_boq_collab_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S08 | B1 | obs-user-08 | 项目资料整理人员 | document_controller_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S09 | B1 | obs-user-09 | ZBid 评标辅助观察人员 | zbid_observer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S10 | B1 | obs-user-10 | 普通试用人员 | general_user_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S11 | B2 | obs-user-11 | 总控管理员 | admin_control_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S12 | B2 | obs-user-12 | 技术标主编 | chief_editor_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S13 | B2 | obs-user-13 | 施工组织设计编制人员 | construction_org_writer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S14 | B2 | obs-user-14 | 专项施工方案编制人员 | special_plan_writer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S15 | B2 | obs-user-15 | 进度计划编制人员 | schedule_planner_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S16 | B2 | obs-user-16 | 质量安全复核人员 | quality_safety_reviewer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S17 | B2 | obs-user-17 | 商务 / 清单协同人员 | commercial_boq_collab_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S18 | B2 | obs-user-18 | 项目资料整理人员 | document_controller_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S19 | B2 | obs-user-19 | ZBid 评标辅助观察人员 | zbid_observer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S20 | B2 | obs-user-20 | 普通试用人员 | general_user_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S21 | B2 | obs-user-01 | 总控管理员 | admin_control_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S22 | B2 | obs-user-02 | 技术标主编 | chief_editor_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S23 | B3 | obs-user-03 | 施工组织设计编制人员 | construction_org_writer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S24 | B3 | obs-user-04 | 专项施工方案编制人员 | special_plan_writer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S25 | B3 | obs-user-05 | 进度计划编制人员 | schedule_planner_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S26 | B3 | obs-user-06 | 质量安全复核人员 | quality_safety_reviewer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S27 | B3 | obs-user-07 | 商务 / 清单协同人员 | commercial_boq_collab_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S28 | B3 | obs-user-08 | 项目资料整理人员 | document_controller_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S29 | B3 | obs-user-09 | ZBid 评标辅助观察人员 | zbid_observer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S30 | B3 | obs-user-10 | 普通试用人员 | general_user_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S31 | B3 | obs-user-11 | 总控管理员 | admin_control_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S32 | B3 | obs-user-12 | 技术标主编 | chief_editor_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S33 | B4 | obs-user-13 | 异常输入 / 边界输入场景 | boundary_input_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S34 | B4 | obs-user-14 | 施工组织设计编制人员 | construction_org_writer_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S35 | B4 | obs-user-15 | 专项施工方案编制人员 | special_plan_writer_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S36 | B4 | obs-user-16 | 异常输入 / 边界输入场景 | boundary_input_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S37 | B4 | obs-user-17 | 异常输入 / 边界输入场景 | boundary_input_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S38 | B4 | obs-user-18 | 进度计划编制人员 | schedule_planner_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S39 | B4 | obs-user-19 | 质量安全复核人员 | quality_safety_reviewer_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S40 | B4 | obs-user-20 | 异常输入 / 边界输入场景 | boundary_input_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S41 | B4 | obs-user-01 | 异常输入 / 边界输入场景 | boundary_input_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S42 | B4 | obs-user-02 | 商务 / 清单协同人员 | commercial_boq_collab_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S43 | B4 | obs-user-03 | 项目资料整理人员 | document_controller_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S44 | B4 | obs-user-04 | 异常输入 / 边界输入场景 | boundary_input_boundary_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S45 | B5 | obs-user-05 | ZBid 评标辅助观察人员 | zbid_observer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S46 | B5 | obs-user-06 | 普通试用人员 | general_user_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S47 | B5 | obs-user-07 | 总控管理员 | admin_control_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S48 | B5 | obs-user-08 | 技术标主编 | chief_editor_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S49 | B5 | obs-user-09 | 施工组织设计编制人员 | construction_org_writer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |
| S50 | B5 | obs-user-10 | 专项施工方案编制人员 | special_plan_writer_routine_observation_period_preview_payload | ZDoc 200 / ZBid 200 | 已发送 | 已接收 | 可读 | false | 符合 | 否 |

## 7. HTTP 结果汇总

有效观察期请求：

- ZDoc `POST /local-trial/preview-only`：50/50 HTTP 200。
- ZBid `POST /local-llm/zdoc-preview-only/receive`：50/50 HTTP 200。
- 非 200 响应：0。
- 失败请求：0。
- 需要回退请求：0。

前置 payload 校准：

- ZDoc `POST /local-trial/preview-only`：50/50 HTTP 200。
- ZBid receiver 调用：0/50；outbound adapter 因 invalid enum blocked，未发送。
- 该校准不计入有效观察期通过统计。

响应观察：

- 有效观察期 ZDoc 响应：min 0.51 ms，median 1.38 ms，max 15.58 ms。
- 有效观察期 outbound -> ZBid receiver 响应：min 1.08 ms，median 2.38 ms，max 4.66 ms。

## 8. preview-only / no-write / no-evidence 复核结果

50 条有效观察期请求均满足：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

前置 payload 校准中，outbound adapter 阻断 invalid enum payload 发送，仍保持 preview-only / no-write 安全边界，未 fallback 到正式接口。

## 9. 禁止接口与禁止写入复核结果

本轮未发生：

- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未调用其他未知业务 endpoint。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未将 preview-only 结果作为 evidence。
- 未将 preview-only 结果作为评分依据。
- 未写入正式业务数据。
- 未运行 Ollama。
- 未进入 50 人正式部署设计。
- 未实施顶级模型升级。

ZDoc 与 ZBid 两侧 output/job/export 前后快照均为空。

## 10. ZDoc -> ZBid 发送与接收结果

有效观察期 50 条请求均完成：

1. ZDoc preview-only 入口构造 preview-only payload。
2. ZDoc outbound adapter 在临时授权环境变量下发送 preview-only payload。
3. ZBid receiver endpoint 接收 preview-only payload。
4. ZBid 返回 preview-only / no-write / no-evidence 结果。

结果：

- ZDoc outbound 已发送：50/50。
- ZBid receiver 已接收：50/50。
- ZBid receiver HTTP 200：50/50。
- 发送 payload 不包含 DOCX、正式 evidence、正式评分结果或 writeback 数据。

前置 payload 校准中，ZDoc outbound 已正确阻断 invalid enum payload，未发送至 ZBid receiver。

## 11. Step 256 三轮稳定基线执行情况

本轮有效观察期按 Step 256 三轮稳定基线执行：

- 覆盖 20 个模拟用户标识。
- 覆盖 11 类角色 / 场景。
- 包含 12 条异常 / 边界输入。
- 逐条复核 HTTP 状态、ZDoc outbound、ZBid receiver。
- 逐条复核 blocked_reasons 与 validator_result 可读性。
- 逐条复核 preview-only / no-write / no-evidence。
- 逐条复核五个禁止 flags。
- 逐条确认不需要回退。

结论：50/50 符合 Step 256 三轮稳定基线。

## 12. 与 Step 251、Step 253、Step 255 三轮结果对比

| 项目 | Step 251 | Step 253 | Step 255 | Step 257 |
| --- | ---: | ---: | ---: | ---: |
| 请求数 | 30 | 30 | 40 | 50 |
| 批次数 | 3 | 3 | 4 | 5 |
| 模拟用户标识 | 20 | 20 | 20 | 20 |
| 角色 / 场景类别 | 11 | 11 | 11 | 11 |
| 异常 / 边界输入 | 8 | 8 | 10 | 12 |
| ZDoc HTTP 200 | 30/30 | 30/30 | 40/40 | 50/50 |
| ZBid HTTP 200 | 30/30 | 30/30 | 40/40 | 50/50 |
| preview-only / no-write / no-evidence | 30/30 | 30/30 | 40/40 | 50/50 |
| 五个禁止 flags false | 30/30 | 30/30 | 40/40 | 50/50 |
| output/job/export 写入 | 0 | 0 | 0 | 0 |
| 回退请求 | 0 | 0 | 0 | 0 |

对比结论：Step 257 有效观察期请求数、批次数和异常 / 边界输入数均增加，未发现相较 Step 251、Step 253、Step 255 的退化。

## 13. 观察期稳定性结论

本轮有效观察期结论：

- ZDoc preview-only 入口稳定可达。
- ZDoc outbound adapter 可稳定发送 preview-only payload。
- ZBid receiver 可稳定接收 preview-only payload。
- 50 条有效请求均保持 preview-only / no-write / no-evidence。
- 12 条异常 / 边界输入未突破安全边界。
- 未发现回退需求。

观察期结论仅适用于当前本地受控 20 人试运行边界，不代表正式生产能力。

## 14. 异常输入 / 边界输入表现

异常 / 边界输入 12 条，均满足：

- ZDoc HTTP 200。
- ZBid HTTP 200。
- ZDoc outbound 已发送。
- ZBid receiver 已接收。
- blocked_reasons 可读。
- validator_result 可读。
- preview-only / no-write / no-evidence 成立。
- 五个禁止 flags 均为 false。

可读 blocked_reasons 样例：

- `missing_tender_file_refs`
- `missing_scoring_clause_refs`
- `unverifiable_scoring_clause_refs`
- `missing_evidence_anchor`
- `high_input_risk_not_validated`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

上述 blocked_reasons 仅用于人工复核，不得作为 evidence 或评分依据。

## 15. 人工复核流程可用性

本轮有效观察期中，人工复核流程可用性表现为：

- 批次、场景、模拟用户标识、角色、payload 类型可追踪。
- blocked_reasons 可用于识别输入问题和边界风险。
- validator_result 可用于确认 preview-only 校验状态。
- 五个禁止 flags 可用于快速确认未触发正式链。
- 回退条件未触发。

继续要求：人工复核记录不得写入正式 evidence，不得写入评分依据，不得触发正式业务数据写入。

## 16. 错误提示与 blocked_reasons 可读性

本轮前置 payload 校准暴露出一个可读的错误提示场景：

- 非法 `zbid_input_status`、`zbid_mapping_status`、`zbid_scoring_matrix_status` 会产生 invalid enum blocked_reasons。
- outbound adapter 会阻断这类 payload 发送。
- 阻断过程保持 preview-only / no-write，不 fallback 到正式接口。

有效观察期中，异常 / 边界输入 blocked_reasons 可读，能提示缺少投标文件引用、评分条款引用、证据锚点、高风险输入未验证，以及 preview-only 不等于写回授权或 evidence。

## 17. 并发与响应风险观察

本轮使用有限 worker 执行观察：

- B2：6 workers。
- B3：5 workers。
- B4：6 workers。
- B5：3 workers。

观察结果：

- 有效观察期 HTTP 200 成功率为 100%。
- preview-only / no-write / no-evidence 成功率为 100%。
- 未出现服务崩溃、端口释放失败或回退需求。

风险说明：

- 本轮不是正式并发压测。
- 当前主机仍仅作为 20 人试运行主机，不作为长期正式生产服务器。
- 若后续需要长期运行或更大规模并发，应单独设计容量、队列、监控、告警、备份、恢复和回退策略。

## 18. 已发现问题

阻断级问题：未发现。

高风险问题：未发现正式链误触发、ZBid 写回、DOCX 生成、output/job/export 写入、evidence 写入或评分依据写入。

中风险问题：

- 长期运行所需正式运维、日志、告警、备份、恢复、权限边界尚未形成正式方案。

低风险 / 观察项：

- 前置 payload 校准说明：非法 ZBid status 枚举会被 outbound adapter 阻断发送，需要后续试运行继续使用合法 preview-only enum 或默认值。
- blocked_reasons 仍需人工复核，不能自动作为正式结论。
- 当前主机仅适合作为 20 人试运行主机。

## 19. 风险等级

| 风险级别 | 当前结论 | 处置要求 |
| --- | --- | --- |
| 阻断级 | 未发现 | 如后续出现，立即暂停 |
| 高风险 | 未发现正式链误触发或写回 | 如后续出现，立即停止并回退 |
| 中风险 | 正式运维方案尚未形成 | 后续单独设计授权 |
| 低风险 | payload enum 需保持合法；blocked_reasons 需人工复核 | 纳入观察期记录 |
| 观察项 | 当前不代表正式生产 | 保持 20 人试运行主机定位 |

## 20. 回退记录

本轮无回退执行。

回退条件复核：

- 任一正式链 flag 非 false：未发生。
- `/generate` 调用：未发生。
- `/export_docx` 调用：未发生。
- `/review/apply` 调用：未发生。
- ZBid 写回：未发生。
- DOCX 生成：未发生。
- output/job/export 写入：未发生。
- evidence 写入：未发生。
- 评分依据写入：未发生。
- 未授权 endpoint 调用：未发生。
- fallback 到正式接口：未发生。

前置 payload 校准不触发回退，因为 outbound adapter 按 preview-only 边界阻断发送，未进入正式链。

## 21. 服务关闭与端口释放结果

本轮启动服务已关闭：

- ZDoc PID `71818` 已停止。
- ZBid PID `71819` 已停止。

端口释放结果：

- `127.0.0.1:18766` 无监听。
- `127.0.0.1:18767` 无监听。

ZDoc 与 ZBid 两侧 output/job/export 前后快照均为空。

## 22. 是否建议进入 Step 258

建议进入 Step 258，但仅限 docs-only stage review / 观察期基线归档 / 后续授权请求。

Step 258 不得默认授权：

- 不得修改代码。
- 不得启动服务。
- 不得访问端口。
- 不得调用 endpoint。
- 不得进入 50 人正式部署设计。
- 不得实施顶级模型升级。
- 不得开放正式链。
- 不得生成 DOCX。
- 不得写 output/job/export。
- 不得触发 ZBid 写回。

## 23. Step 258 授权请求草案

可复制授权语：

```text
执行 Step 258：ZDoc-ZBid 20-user controlled routine observation-period review and next-stage authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<待填入 Step 257 结束后 HEAD>

本步性质：
docs-only / stage-review-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
归档 Step 257 20 人受控常态观察期执行结果，并起草下一阶段授权请求。该文档只做阶段复核与授权请求，不代表启动下一阶段。

必须记录：
1. Step 257 有效观察期 50 条请求、5 个批次、20 个模拟用户、11 类角色 / 场景、12 条异常 / 边界输入结果。
2. ZDoc 与 ZBid 均 HTTP 200。
3. preview_only=true、no_write=true、no_evidence=true。
4. generate_called=false、export_docx_called=false、review_apply_called=false、zbid_writeback_called=false、output_job_export_written=false。
5. 符合 Step 256 三轮稳定基线。
6. 与 Step 251、Step 253、Step 255 对比未发现退化。
7. 前置 payload 校准中 invalid enum 被 adapter 阻断，未发送 ZBid，未触发正式链。
8. 未运行 Ollama，未触发 /generate、/export_docx、/review/apply、ZBid 写回。
9. 未生成 DOCX，未写 output/job/export。
10. 当前仍仅为 20 人本地试运行观察期，不代表正式生产服务器，不进入 50 人正式部署设计，不实施顶级模型升级。

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
不进入 Step 259。
```
