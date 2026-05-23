# ZDoc-ZBid 20-user routine pilot controlled execution report

## 1. Step 251 执行摘要

本次 Step 251 在 ZDoc 与 ZBid 双仓基线均匹配、工作区均 clean 的前提下执行，目标是验证约 20 人团队口径下的常态试运行流程。

本次执行保持 preview-only / no-write / no-evidence 边界，仅调用经授权的 preview-only endpoint，未触发正式生成链、正式证据链、正式评分链、正式导出链或写回链。

本轮常态试运行共执行 30 条脱敏 / 模拟 / preview-only 请求，覆盖 20 个模拟用户标识、11 类角色 / 场景、3 个批次，其中包含 8 条异常或边界输入。全部请求返回 HTTP 200，全部保持 preview_only=true、no_write=true、no_evidence=true，五个 no-write / no-formal-chain flags 均为 false。

## 2. 运行环境与端口记录

### ZDoc

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`e6d03340ea57ea91586303274d9fa62fc2e79135`
- 执行结束、写入本报告前 HEAD：`e6d03340ea57ea91586303274d9fa62fc2e79135`
- 执行前 `git status --short`：空
- 执行后、写入本报告前 `git status --short`：空
- 服务启动命令：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=1 PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18766
```

- 服务 PID：`58725`
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

- 服务 PID：`58737`
- 服务端口：`127.0.0.1:18767`

## 3. 常态试运行批次安排

| 批次 | 名称 | 请求数 | 执行方式 | 目标 |
| --- | --- | ---: | --- | --- |
| B1 | 启动验证批次 | 10 | 顺序请求 | 验证服务启动后 preview-only 链路可达 |
| B2 | 常态使用批次 | 12 | 6-worker 并发请求 | 观察常态使用下发送、接收和响应稳定性 |
| B3 | 异常边界批次 | 8 | 4-worker 并发请求 | 观察异常 / 边界输入下 blocked_reasons、错误提示和人工复核可读性 |

## 4. 20 人用户 / 角色覆盖情况

本次使用 20 个模拟用户标识：`pilot-user-01` 至 `pilot-user-20`。这些标识仅用于脱敏常态试运行记录，不代表真实用户登录或正式生产账号。

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

## 5. 每个批次的验证结果

| 批次 | HTTP 结果 | preview_only | no_write | no_evidence | 五个 false flags | 回退 |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | 10/10 为 HTTP 200 | 10/10 为 true | 10/10 为 true | 10/10 为 true | 10/10 均为 false | 不需要 |
| B2 | 12/12 为 HTTP 200 | 12/12 为 true | 12/12 为 true | 12/12 为 true | 12/12 均为 false | 不需要 |
| B3 | 8/8 为 HTTP 200 | 8/8 为 true | 8/8 为 true | 8/8 为 true | 8/8 均为 false | 不需要 |

## 6. 每个场景的验证结果

| 批次 | 场景 | 用户标识 | 角色 / 场景 | payload 类型 | ZDoc HTTP | ZBid HTTP | ZDoc outbound | ZBid receiver | blocked_reasons | validator_result | flags | 人工复核 | 回退 |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| B1 | S01 | pilot-user-01 | 总控管理员 | admin_control_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S02 | pilot-user-02 | 技术标主编 | chief_editor_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S03 | pilot-user-03 | 施工组织设计编制人员 | construction_org_writer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S04 | pilot-user-04 | 专项施工方案编制人员 | special_plan_writer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S05 | pilot-user-05 | 进度计划编制人员 | schedule_planner_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S06 | pilot-user-06 | 质量安全复核人员 | quality_safety_reviewer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S07 | pilot-user-07 | 商务 / 清单协同人员 | commercial_boq_collab_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S08 | pilot-user-08 | 项目资料整理人员 | document_controller_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S09 | pilot-user-09 | ZBid 评标辅助观察人员 | zbid_observer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B1 | S10 | pilot-user-10 | 普通试用人员 | general_user_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S11 | pilot-user-11 | 技术标主编 | chief_editor_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S12 | pilot-user-12 | 施工组织设计编制人员 | construction_org_writer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S13 | pilot-user-13 | 专项施工方案编制人员 | special_plan_writer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S14 | pilot-user-14 | 进度计划编制人员 | schedule_planner_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S15 | pilot-user-15 | 质量安全复核人员 | quality_safety_reviewer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S16 | pilot-user-16 | 商务 / 清单协同人员 | commercial_boq_collab_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S17 | pilot-user-17 | 项目资料整理人员 | document_controller_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S18 | pilot-user-18 | ZBid 评标辅助观察人员 | zbid_observer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S19 | pilot-user-19 | 普通试用人员 | general_user_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S20 | pilot-user-20 | 总控管理员 | admin_control_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S21 | pilot-user-01 | 技术标主编 | chief_editor_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B2 | S22 | pilot-user-02 | 质量安全复核人员 | quality_safety_reviewer_routine_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B3 | S23 | pilot-user-03 | 异常输入 / 边界输入场景 | boundary_input_boundary_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B3 | S24 | pilot-user-04 | 异常输入 / 边界输入场景 | boundary_input_boundary_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B3 | S25 | pilot-user-05 | 项目资料整理人员 | document_controller_boundary_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B3 | S26 | pilot-user-06 | 质量安全复核人员 | quality_safety_reviewer_boundary_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B3 | S27 | pilot-user-07 | 专项施工方案编制人员 | special_plan_writer_boundary_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B3 | S28 | pilot-user-08 | ZBid 评标辅助观察人员 | zbid_observer_boundary_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B3 | S29 | pilot-user-09 | 普通试用人员 | general_user_boundary_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |
| B3 | S30 | pilot-user-10 | 商务 / 清单协同人员 | commercial_boq_collab_boundary_preview_payload | 200 | 200 | 已发送 | 已接收 | 可读 | 可读 | 均 false | 通过 | 否 |

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
- ZDoc outbound adapter 已按临时环境变量启用 preview-only network-send。
- ZBid receiver 已接收 preview-only payload，并返回 preview-only / no-write / no-evidence 结果。

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

ZDoc 侧临时启用如下环境变量：

```bash
ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true
ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true
ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18767/local-llm/zdoc-preview-only/receive
PYTHONDONTWRITEBYTECODE=1
```

发送与接收结论：

- ZDoc outbound adapter 发送 preview-only payload：30/30 成功
- ZBid receiver 接收 preview-only payload：30/30 成功
- ZBid receiver HTTP 200：30/30 成功
- 未发送 evidence、DOCX、正式评分结果、writeback 数据或正式业务数据。

## 11. 异常输入 / 边界输入表现

本轮包含 8 条异常或边界输入，集中在 B3 批次及部分边界 payload。blocked_reasons 可读，能够提示人工复核人员关注输入、配置或边界风险。

本轮记录到的 blocked_reasons 类型包括：

- `missing_tender_file_refs`
- `missing_scoring_clause_refs`
- `high_input_risk_not_validated`
- `missing_evidence_anchor`
- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`

这些 blocked_reasons 仅用于 preview-only 复核和风险提示，不得作为 evidence 或评分依据。

## 12. 人工复核流程可用性

人工复核流程在本轮常态试运行中可用：

- 每条场景均能看到 preview-only / no-write / no-evidence 状态。
- 每条场景均能读取 validator_result。
- 每条场景均能读取 blocked_reasons。
- 每条场景均能确认五个 no-write / no-formal-chain flags 均为 false。
- 边界输入场景能提供可识别的停止和上报线索。

建议后续继续使用人工复核检查表记录：操作入口、payload 类型、blocked_reasons、validator_result、五个 false flags、人工结论、是否需要回退。

## 13. 错误提示与 blocked_reasons 可读性

错误提示与 blocked_reasons 在本轮验证中可读。异常或边界输入未造成正式链 fallback，也未产生写入。

当前仍需保持的解释边界：

- blocked_reasons 是 preview-only 风险提示，不是正式 evidence。
- validator_result 是 preview-only 校验结果，不是评分依据。
- 任一正式链 flag 非 false 时必须立即停止并记录。

## 14. 常态运行稳定性观察

本轮短周期常态运行未发现阻断 preview-only 链路的问题。

响应观察：

- ZDoc preview-only latency：最小约 0.53 ms，中位约 1.15 ms，最大约 15.57 ms。
- ZDoc outbound 到 ZBid receiver latency：最小约 1.10 ms，中位约 2.42 ms，最大约 4.73 ms。
- B1 顺序验证、B2 6-worker 常态并发、B3 4-worker 边界并发均完成。

该观察仅代表本地短周期受控试运行，不代表生产级并发压测或长期稳定性结论。

## 15. 并发与响应风险观察

本轮并发观察未出现 HTTP 失败、服务崩溃或端口异常。

仍需保留的风险：

- 本轮不是 20 个真实用户同时在线压测。
- 本轮未验证长期连续运行。
- 本轮未验证真实业务数据规模。
- 本轮未开放正式生成、DOCX 导出、review/apply 或 ZBid 写回。
- 后续如进入更长周期常态试运行，应继续记录端口、PID、请求数、失败数、响应时间和停止条件。

## 16. 已发现问题

本轮未发现阻断 preview-only 链路的问题。

本轮未发现：

- 正式链误触发
- ZBid 写回
- DOCX 生成
- evidence 写入
- 评分依据写入
- `output/job/export` 写入

观察项仍包括：

- 长周期运行稳定性仍未验证。
- 真实多用户操作节奏仍未验证。
- 日志留痕模板可继续固化。
- blocked_reasons 的人工分级处置可继续细化。

## 17. 风险等级

| 风险项 | 等级 | 处置 |
| --- | --- | --- |
| 正式链误触发 | 低 | 本轮未发生；后续继续逐条复核五个 flags |
| output/job/export 写入 | 低 | 本轮未发生；后续继续做前后快照 |
| DOCX 生成 | 低 | 本轮未发生；继续禁止 `/export_docx` |
| ZBid 写回 | 低 | 本轮未发生；继续禁止写回 endpoint 和写回数据 |
| 长周期稳定性 | 中 | 本轮为短周期受控验证，后续需单独授权验证 |
| 真实用户并发 | 中 | 本轮使用模拟用户标识，后续需单独授权扩大验证 |

## 18. 回退记录

本轮无场景需要回退。

预设回退条件仍为：

- 任一正式链 flag 非 false
- 出现 `output/job/export` 写入
- 出现 DOCX 生成
- 出现 ZBid 写回
- 出现 evidence 写入
- 出现评分依据写入
- 出现未知 endpoint 调用
- 出现 fallback 到正式接口

如触发上述任一条件，必须停止试运行、记录问题、关闭本步启动服务，并等待单独授权，不得现场修复。

## 19. 服务关闭与端口释放结果

本步启动服务已关闭：

- ZDoc PID `58725`：已停止
- ZBid PID `58737`：已停止

端口释放结果：

- `127.0.0.1:18766`：无监听
- `127.0.0.1:18767`：无监听

`output/job/export` 快照结果：

- ZDoc：`output`、`job`、`export` 目录不存在或无文件，未发现新增写入。
- ZBid：`output`、`job`、`export` 目录不存在或无文件，未发现新增写入。

## 20. 是否建议进入 Step 252

建议进入 Step 252，但仅限在用户明确授权后执行。

建议 Step 252 定位为 docs-only stage review / routine pilot readiness review，不得自动启动服务、访问端口、调用 endpoint、修改代码或进入正式链。

## 21. Step 252 授权请求草案

以下为可复制的 Step 252 授权请求草案：

```text
执行 Step 252：ZDoc-ZBid 20-user routine pilot stage review and next authorization request。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 251 提交后的 ZDoc HEAD>

本步性质：
docs-only / stage-review-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

授权范围：
仅允许新增 Step 251 常态试运行 stage review 文档，归档 30 条请求、3 个批次、20 个模拟用户标识、11 类角色 / 场景、8 条异常或边界输入的验证结果。

严格禁止：
不修改代码 / tests / frontend / backend / 既有 docs。
不运行服务。
不运行 Ollama。
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

完成后停止，不得自动进入下一步。
```
