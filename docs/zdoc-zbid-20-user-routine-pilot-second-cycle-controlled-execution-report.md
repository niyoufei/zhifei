# ZDoc-ZBid 20-user routine pilot second-cycle controlled execution report

## 1. Step 253 执行摘要

Step 253 按 Step 252《20-user routine pilot review and operation management baseline》执行第二轮常态试运行。执行范围仍限定为 preview-only / no-write / no-evidence，不开放正式生成链、证据链、评分链、DOCX 导出链、review/apply 链或 ZBid 写回链。

本轮使用脱敏 / 模拟 / preview-only payload，完成 30 条请求、3 个批次、20 个模拟用户标识、11 类角色 / 场景、8 条异常或边界输入。所有请求均返回 HTTP 200，ZDoc outbound adapter 均成功向 ZBid receiver 发送 preview-only payload，ZBid receiver 均成功接收并返回 preview-only / no-write / no-evidence 结果。

核心结论：

- `preview_only=true`：30/30 成立
- `no_write=true`：30/30 成立
- `no_evidence=true`：30/30 成立
- 五个 no-write / no-formal-chain flags：30/30 均为 false
- Step 252 运行管理基线：30/30 符合
- 回退请求：0
- 未触发正式链、未生成 DOCX、未写 `output/job/export`

## 2. 运行环境与端口记录

### ZDoc

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`1ea100119ea82c3145a1e127ec10ccf4d8a3fa38`
- 执行结束、写入本报告前 HEAD：`1ea100119ea82c3145a1e127ec10ccf4d8a3fa38`
- 执行前 `git status --short`：空
- 执行后、写入本报告前 `git status --short`：空
- 服务启动命令：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- 服务 PID：`63514`
- 服务端口：`127.0.0.1:18766`

### ZBid

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 开始前 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 结束时 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 执行前 `git status --short`：空
- 执行后 `git status --short`：空
- 服务启动命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18767
```

- 服务 PID：`63526`
- 服务端口：`127.0.0.1:18767`

### 临时环境变量

```bash
ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true
ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true
ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive
PYTHONDONTWRITEBYTECODE=1
```

以上环境变量仅用于本轮运行命令，未写入 `.env`、配置文件或持久文件。

## 3. 第二轮常态试运行批次安排

| 批次 | 名称 | 请求数 | 执行方式 | 目标 |
| --- | --- | ---: | --- | --- |
| B1 | 启动复核批次 | 10 | 顺序请求 | 复核服务启动后 preview-only 链路可达 |
| B2 | 常态使用批次 | 12 | 6-worker 并发请求 | 复核常态使用下发送、接收和响应稳定性 |
| B3 | 异常边界批次 | 8 | 4-worker 并发请求 | 复核异常 / 边界输入下 blocked_reasons 与人工复核可读性 |

## 4. 20 人用户 / 角色覆盖情况

本轮覆盖 20 个模拟用户标识：`pilot2-user-01` 至 `pilot2-user-20`。这些标识仅用于脱敏试运行记录，不代表真实用户登录或正式生产账号。

覆盖角色 / 场景共 11 类：

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

## 5. 每个批次验证结果

| 批次 | HTTP 结果 | preview_only | no_write | no_evidence | 五个 false flags | Step 252 基线 | 回退 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | 10/10 为 HTTP 200 | 10/10 为 true | 10/10 为 true | 10/10 为 true | 10/10 均为 false | 符合 | 不需要 |
| B2 | 12/12 为 HTTP 200 | 12/12 为 true | 12/12 为 true | 12/12 为 true | 12/12 均为 false | 符合 | 不需要 |
| B3 | 8/8 为 HTTP 200 | 8/8 为 true | 8/8 为 true | 8/8 为 true | 8/8 均为 false | 符合 | 不需要 |

## 6. 每个场景验证结果

| 批次 | 场景 | 模拟用户标识 | 角色 / 场景 | payload 类型 | ZDoc HTTP | ZBid HTTP | outbound | receiver | blocked_reasons | validator_result | P/NW/NE | flags | 基线 | 人工复核 | 回退 |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | S01 | pilot2-user-01 | 总控管理员 | admin_control_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S02 | pilot2-user-02 | 技术标主编 | chief_editor_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S03 | pilot2-user-03 | 施工组织设计编制人员 | construction_org_writer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S04 | pilot2-user-04 | 专项施工方案编制人员 | special_plan_writer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S05 | pilot2-user-05 | 进度计划编制人员 | schedule_planner_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S06 | pilot2-user-06 | 质量安全复核人员 | quality_safety_reviewer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S07 | pilot2-user-07 | 商务 / 清单协同人员 | commercial_boq_collab_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S08 | pilot2-user-08 | 项目资料整理人员 | document_controller_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S09 | pilot2-user-09 | ZBid 评标辅助观察人员 | zbid_observer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B1 | S10 | pilot2-user-10 | 普通试用人员 | general_user_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S11 | pilot2-user-11 | 技术标主编 | chief_editor_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S12 | pilot2-user-12 | 施工组织设计编制人员 | construction_org_writer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S13 | pilot2-user-13 | 专项施工方案编制人员 | special_plan_writer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S14 | pilot2-user-14 | 进度计划编制人员 | schedule_planner_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S15 | pilot2-user-15 | 质量安全复核人员 | quality_safety_reviewer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S16 | pilot2-user-16 | 商务 / 清单协同人员 | commercial_boq_collab_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S17 | pilot2-user-17 | 项目资料整理人员 | document_controller_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S18 | pilot2-user-18 | ZBid 评标辅助观察人员 | zbid_observer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S19 | pilot2-user-19 | 普通试用人员 | general_user_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S20 | pilot2-user-20 | 总控管理员 | admin_control_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S21 | pilot2-user-01 | 技术标主编 | chief_editor_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B2 | S22 | pilot2-user-02 | 质量安全复核人员 | quality_safety_reviewer_routine_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过 | 否 |
| B3 | S23 | pilot2-user-03 | 异常输入 / 边界输入场景 | boundary_input_boundary_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过-需关注 blocked_reasons | 否 |
| B3 | S24 | pilot2-user-04 | 异常输入 / 边界输入场景 | boundary_input_boundary_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过-需关注 blocked_reasons | 否 |
| B3 | S25 | pilot2-user-05 | 项目资料整理人员 | document_controller_boundary_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过-需关注 blocked_reasons | 否 |
| B3 | S26 | pilot2-user-06 | 质量安全复核人员 | quality_safety_reviewer_boundary_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过-需关注 blocked_reasons | 否 |
| B3 | S27 | pilot2-user-07 | 专项施工方案编制人员 | special_plan_writer_boundary_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过-需关注 blocked_reasons | 否 |
| B3 | S28 | pilot2-user-08 | ZBid 评标辅助观察人员 | zbid_observer_boundary_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过-需关注 blocked_reasons | 否 |
| B3 | S29 | pilot2-user-09 | 普通试用人员 | general_user_boundary_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过-需关注 blocked_reasons | 否 |
| B3 | S30 | pilot2-user-10 | 商务 / 清单协同人员 | commercial_boq_collab_boundary_second_cycle_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 成立 | 均 false | 符合 | 通过-需关注 blocked_reasons | 否 |

说明：表中 `P/NW/NE` 表示 `preview_only=true`、`no_write=true`、`no_evidence=true` 均成立。

## 7. HTTP 结果汇总

- 总请求数：30
- ZDoc `POST /local-trial/preview-only`：30/30 为 HTTP 200
- ZBid `POST /local-llm/zdoc-preview-only/receive`：30/30 为 HTTP 200
- 失败请求数：0
- 回退请求数：0

## 8. preview-only / no-write / no-evidence 复核结果

- `preview_only=true`：30/30 成立
- `no_write=true`：30/30 成立
- `no_evidence=true`：30/30 成立
- ZDoc outbound adapter 均成功发送 preview-only payload。
- ZBid receiver 均接收 preview-only payload。
- 所有结果均不作为 evidence，不作为评分依据。

## 9. 禁止接口与禁止写入复核结果

本次实际调用 endpoint 清单仅包括：

1. ZDoc `POST /local-trial/preview-only`
2. ZBid `POST /local-llm/zdoc-preview-only/receive`

本次未调用：

- `/generate`
- `/export_docx`
- `/review/apply`
- 任何 ZBid 写回 endpoint
- 任何未知业务 endpoint

本次未生成 DOCX，未写入 `output/job/export`，未把 preview-only 结果作为 evidence，未把 preview-only 结果作为评分依据。

## 10. ZDoc -> ZBid 发送与接收结果

- ZDoc outbound adapter 发送 preview-only payload：30/30 成功
- ZBid receiver 接收 preview-only payload：30/30 成功
- ZBid receiver HTTP 200：30/30 成功
- ZBid receiver 返回 `receiver_accepted=true`：30/30 成功
- 未发送 evidence、DOCX、正式评分结果、writeback 数据或正式业务数据。

## 11. Step 252 运行管理基线执行情况

本轮执行符合 Step 252 运行管理基线：

- 运行前核验 ZDoc 与 ZBid 分支、HEAD、clean 状态：已完成。
- 仅使用临时环境变量启用 preview-only network-send：已遵守。
- 未写入 `.env`、配置文件或持久配置：已遵守。
- 仅启动必要 preview-only 服务：已遵守。
- 仅访问授权端口：`127.0.0.1:18766`、`127.0.0.1:18767`。
- 仅调用授权 preview-only endpoint：已遵守。
- 每条请求均记录 HTTP、blocked_reasons、validator_result、五个 false flags：已完成。
- 运行前后检查 `output/job/export`：已完成，均为空。
- 运行后关闭本步启动服务：已完成。
- 运行后确认端口无监听：已完成。
- 任何失败不得现场修复：本轮无失败、无修复动作。

## 12. 与 Step 251 第一轮结果对比

| 指标 | Step 251 第一轮 | Step 253 第二轮 | 对比结论 |
| --- | --- | --- | --- |
| 总请求数 | 30 | 30 | 持平 |
| 批次数 | 3 | 3 | 持平 |
| 模拟用户标识数 | 20 | 20 | 持平 |
| 角色 / 场景数 | 11 | 11 | 持平 |
| 异常 / 边界输入数 | 8 | 8 | 持平 |
| ZDoc HTTP 200 | 30/30 | 30/30 | 持续通过 |
| ZBid HTTP 200 | 30/30 | 30/30 | 持续通过 |
| preview_only / no_write / no_evidence | 30/30 成立 | 30/30 成立 | 持续成立 |
| 五个 false flags | 30/30 均 false | 30/30 均 false | 持续成立 |
| output/job/export 写入 | 无 | 无 | 持续无写入 |
| 回退请求 | 0 | 0 | 持平 |

响应观察对比：

- Step 251 ZDoc latency：min 0.53 ms，median 1.15 ms，max 15.57 ms。
- Step 253 ZDoc latency：min 0.51 ms，median 1.23 ms，max 15.38 ms。
- Step 251 outbound latency：min 1.10 ms，median 2.42 ms，max 4.73 ms。
- Step 253 outbound latency：min 1.06 ms，median 2.41 ms，max 6.00 ms。

两轮结果整体一致，未发现第二轮新增阻断问题。

## 13. 异常输入 / 边界输入表现

本轮 8 条异常 / 边界输入均返回 HTTP 200，并保持 preview-only / no-write / no-evidence。

边界输入 blocked_reasons 主要包括：

- `missing_tender_file_refs`
- `missing_scoring_clause_refs`
- `missing_evidence_anchor`
- `high_input_risk_not_validated`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`

结论：

- blocked_reasons 可读。
- 边界输入能够提示人工复核关注输入缺失、配置不足或边界风险。
- 边界输入不构成 evidence，不构成评分依据，不触发写回。

## 14. 人工复核流程可用性

人工复核流程在第二轮中继续可用：

- 每条请求均可确认 preview-only / no-write / no-evidence。
- 每条请求均可读取 validator_result。
- 每条请求均可读取 blocked_reasons。
- 每条请求均可确认五个 no-write / no-formal-chain flags 均为 false。
- 边界输入可形成“通过-需关注 blocked_reasons”的人工复核结论。

后续常态运行仍建议按 Step 252 的日志模板、问题清单模板和回退记录模板执行。

## 15. 错误提示与 blocked_reasons 可读性

本轮未出现服务级错误或 HTTP 失败。异常 / 边界输入下的 blocked_reasons 可读，能够辅助人工判断：

- 输入缺失类：如 tender refs、scoring refs、evidence anchor refs 缺失。
- 边界风险类：如 high input risk 未验证。
- 安全边界类：如 preview-only 不是 writeback permission，preview-only 不是 evidence。

blocked_reasons 仅用于 preview-only 风险提示和人工复核，不得写入正式 evidence 或评分依据。

## 16. 常态运行稳定性观察

本轮短周期常态运行未发现阻断 preview-only 链路的问题。

响应观察：

- ZDoc preview-only latency：最小 0.51 ms，中位 1.23 ms，最大 15.38 ms。
- ZDoc outbound 到 ZBid receiver latency：最小 1.06 ms，中位 2.41 ms，最大 6.00 ms。
- B1 顺序验证、B2 6-worker 常态并发、B3 4-worker 边界并发均完成。

该观察只代表本地短周期受控运行，不代表长期运行或正式生产并发结论。

## 17. 并发与响应风险观察

本轮并发观察未出现 HTTP 失败、服务崩溃、端口异常或回退。

仍需保留的风险：

- 本轮不是 20 个真实用户同时在线压测。
- 本轮未验证长时间连续运行。
- 本轮未验证真实投标资料和大体量文件。
- 本轮未验证服务异常后的自动恢复。
- 本轮未开放正式生成、DOCX 导出、review/apply 或 ZBid 写回。

## 18. 已发现问题

本轮未发现阻断 preview-only 链路的问题。

本轮未发现：

- 正式链误触发。
- ZBid 写回。
- DOCX 生成。
- evidence 写入。
- 评分依据写入。
- `output/job/export` 写入。
- 未授权 endpoint 调用。
- fallback 到正式接口。

观察项：

- 长周期运行仍未验证。
- 真实多用户并发仍未验证。
- 日志留痕和人工分级处置仍需持续固化。

## 19. 风险等级

| 风险项 | 等级 | 本轮结论 | 后续处置 |
| --- | --- | --- | --- |
| 正式链误触发 | 低 | 未发生 | 继续逐条复核五个 flags |
| ZBid 写回 | 低 | 未发生 | 继续禁止写回 endpoint 与写回数据 |
| DOCX 生成 | 低 | 未发生 | 继续禁止 `/export_docx` |
| output/job/export 写入 | 低 | 未发生 | 继续执行前后快照 |
| 长周期稳定性 | 中 | 未验证 | 需另行授权长周期验证 |
| 真实用户并发 | 中 | 未验证 | 需另行授权真实并发或更长周期试运行 |
| 日志与问题处置固化 | 低 | 可继续改进 | 可通过 docs-only 或单独授权优化 |

## 20. 回退记录

本轮无场景需要回退。

回退触发条件仍保持：

- 任一正式链 flag 非 false。
- 出现 `output/job/export` 写入。
- 出现 DOCX 生成。
- 出现 ZBid 写回。
- 出现 evidence 写入。
- 出现评分依据写入。
- 出现未知 endpoint 调用。
- 出现 fallback 到正式接口。
- 服务无法关闭或端口无法释放。

本轮以上条件均未触发。

## 21. 服务关闭与端口释放结果

本步启动服务已关闭：

- ZDoc PID `63514`：已停止。
- ZBid PID `63526`：已停止。

端口释放结果：

- `127.0.0.1:18766`：无监听。
- `127.0.0.1:18767`：无监听。

`output/job/export` 快照结果：

- ZDoc：前后均为空，未发现新增写入。
- ZBid：前后均为空，未发现新增写入。

## 22. 是否建议进入 Step 254

建议进入 Step 254，但仅限在用户明确授权后执行。

建议 Step 254 定位为 docs-only stage review / second-cycle routine pilot readiness review，不得自动启动服务、访问端口、调用 endpoint、修改代码或进入正式链。

## 23. Step 254 授权请求草案

以下为可复制的 Step 254 授权请求草案：

```text
执行 Step 254：ZDoc-ZBid 20-user routine pilot second-cycle stage review and continued operation authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 253 提交后的 ZDoc HEAD>

本步性质：
ZDoc docs-only / stage-review-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
归档 Step 253 第二轮常态试运行结果，并起草后续持续运行授权请求。该文档只代表阶段复核和授权请求，不代表已启动下一轮运行。

授权边界：
1. 仅新增目标 docs 文件。
2. 不修改代码 / tests / frontend / backend / 既有 docs。
3. 不运行服务。
4. 不运行 Ollama。
5. 不访问端口。
6. 不调用任何 endpoint。
7. 不触发 /generate、/export_docx、/review/apply。
8. 不触发 ZBid 写回。
9. 不生成 DOCX。
10. 不写 output/job/export。
11. 不把 preview-only 结果作为 evidence。
12. 不把 preview-only 结果作为评分依据。
13. 不进入 50 人正式部署设计。
14. 不实施顶级模型升级。

完成后停止，不得自动进入下一步。
```
