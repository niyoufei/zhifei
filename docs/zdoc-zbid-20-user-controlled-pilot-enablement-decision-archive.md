# ZDoc-ZBid 20-user controlled pilot enablement decision archive

## 1. Step 245 至 Step 279 阶段成果总览

本文档归档 ZDoc-ZBid 约 20 人团队受控试运行启用决策。本文档仅代表当前阶段的决策归档，不代表进入正式生产系统，不代表进入 50 人正式部署设计，不代表开放正式生成链、正式证据链、评分依据写入、DOCX 导出、review/apply 或 ZBid 写回。

阶段成果概览：

| 阶段 | 主要成果 | 边界结论 |
| --- | --- | --- |
| Step 245 | 完成 20 人本地化部署与试运行 controlled execution report。 | 仅 preview-only / no-write / no-evidence。 |
| Step 247 | 完成 limited human pilot controlled execution。 | 未开放正式链。 |
| Step 249 | 完成 20 人 expanded pilot controlled execution。 | 代表性角色与流程验证通过。 |
| Step 251 / 253 / 255 | 完成三轮 routine pilot controlled execution。 | 合计 100 条请求、10 个批次、20 个模拟用户、11 类角色 / 场景、26 条异常 / 边界输入。 |
| Step 256 | 归档三轮稳定试运行 baseline。 | 可作为 20 人受控常态试运行基线。 |
| Step 257 / 259 / 261 | 完成三轮 observation-period controlled execution。 | 合计 180 条有效观察期请求、18 个批次、20 个模拟用户、11 类角色 / 场景、50 条异常 / 边界输入。 |
| Step 262 | 归档三轮观察期 baseline。 | 前置 payload 校准必须与有效请求分开计数。 |
| Step 263 | 归档 20 人受控常态观察阶段闭环与下一阶段决策请求。 | 未自动进入下一阶段。 |
| Step 264 | 完成 20 人受控常态运行手册与管理员 SOP。 | 操作规程文档已形成。 |
| Step 265 | 完成环境 preflight checklist 与启动关闭控制归档。 | 启动前检查边界已形成。 |
| Step 266 | 完成 read-only preflight controlled execution。 | 未启动服务、未调用 endpoint、未写入。 |
| Step 267 | 完成 preflight readiness decision request。 | 启动前置条件可进入后续授权。 |
| Step 268 | 完成服务启动关闭 smoke controlled execution。 | 仅验证服务启动、监听、关闭、端口释放；未调用 endpoint。 |
| Step 269 | 完成 endpoint smoke authorization request。 | 仅申请下一步 endpoint smoke。 |
| Step 270 | 完成 preview-only endpoint smoke controlled execution。 | 链路可达，同时发现 ZDoc 顶层 `no_evidence` schema 观察项。 |
| Step 271 / 272 | 归档 schema 观察项并起草最小变更授权。 | 观察项被定义为 response schema 可读性 / 显示一致性问题。 |
| Step 273 | 完成 ZDoc 顶层 `no_evidence=true` 最小代码变更。 | targeted pytest `7 passed`。 |
| Step 274 / 275 / 276 | 完成最小变更 review、runtime smoke 与观察项关闭归档。 | ZDoc 顶层 `no_evidence=true` runtime 验证成立。 |
| Step 277 | 完成 schema observation closure baseline update 与 regression authorization request。 | 进入回归 smoke 前置条件成立。 |
| Step 278 | 完成 post-schema-closure regression smoke。 | 3 条 preview-only payload 全部 HTTP 200，未发现较 Step 275 退化。 |
| Step 279 | 完成 final admission readiness review 与 controlled pilot enablement authorization request。 | 已具备进入本文档所述启用决策归档的条件。 |

总体结论：

- ZDoc-ZBid preview-only 链路已经完成 20 人口径下的多阶段受控验证。
- no_evidence schema 观察项已完成最小修正、runtime smoke 和回归 smoke。
- 当前阶段可定义为“20 人 preview-only 受控试运行可用”。
- 当前仍不得定义为正式生产可用、50 人正式部署可用或正式链开放。

## 2. 20 人受控试运行启用结论

启用决策结论：

```text
允许将当前系统状态归档为 20 人 preview-only 受控试运行可用基线。
```

该结论的含义：

- 可在管理员监管下开展 20 人团队 preview-only 受控试运行。
- 可按已形成的管理员 SOP、preflight checklist、日志模板、问题清单模板和回退记录模板执行。
- 可继续以 preview-only / no-write / no-evidence 方式验证人工复核流程和使用稳定性。
- 所有运行都必须继续记录日志、问题清单和回退记录。

该结论不代表：

- 正式生产系统启用。
- 50 人正式部署启用。
- 正式生成链开放。
- 正式 evidence 开放。
- 评分依据写入开放。
- DOCX 导出开放。
- review/apply 开放。
- ZBid 写回开放。
- 顶级本地模型升级实施。

## 3. 当前系统阶段定义

当前系统阶段定义为：

```text
20 人 preview-only 受控试运行可用。
```

阶段能力边界：

- 支持 20 人团队口径下的 preview-only 受控试运行。
- 支持管理员监管、人工复核、日志留痕、问题清单和回退记录。
- 支持 ZDoc -> ZBid preview-only 链路验证。
- 支持 `blocked_reasons`、`validator_result`、`preview_packet` 的人工可读复核。
- 支持五个 no-write / no-formal-chain flags 的持续复核。

阶段限制：

- 不承诺长期正式生产稳定性。
- 不承诺 50 人正式并发能力。
- 不承诺正式生成、正式证据、正式评分、正式导出或正式写回能力。
- 不承诺真实业务数据接入。
- 不承诺顶级本地模型升级完成。

## 4. 当前不是正式生产系统

当前系统不得被描述为正式生产系统。

原因：

- 当前验证目标仍是 preview-only / no-write / no-evidence。
- 试运行主机定位仍是 20 人受控试运行主机，不是长期正式生产服务器。
- 正式生产所需的容量设计、权限设计、运维监控、备份恢复、变更控制、正式链开放条件和故障处置机制尚未作为生产方案完成。
- 正式链相关能力仍未开放。

因此，任何外部沟通或内部交接都应使用以下表述：

```text
当前可用于 20 人 preview-only 受控试运行，不是正式生产系统。
```

## 5. no_evidence schema 观察项关闭结论

原观察项：

- Step 270 发现 ZDoc `POST /local-trial/preview-only` route 顶层 response 返回 `preview_only=true`、`no_write=true`，但缺少顶层 `no_evidence` 字段。

问题性质：

- response schema 可读性 / 显示一致性问题。
- 不属于写入问题。
- 不属于 evidence 生成问题。
- 不属于评分依据写入问题。
- 不属于 ZBid 写回问题。

关闭依据：

- Step 273 已完成最小代码变更，在 ZDoc route 顶层 response 中补充 `no_evidence=true`。
- Step 273 targeted pytest 结果为 `7 passed`。
- Step 275 runtime smoke 已验证 ZDoc 顶层 `no_evidence=true`。
- Step 278 regression smoke 已验证 3 条 payload 下 ZDoc 顶层 `no_evidence=true` 持续成立。
- ZBid receiver 侧 `preview_only=true`、`no_write=true`、`no_evidence=true` 持续成立。
- 五个禁止 flags 均为 `false`。

关闭结论：

```text
ZDoc route top-level no_evidence schema observation: closed.
```

## 6. Step 278 regression smoke 通过结论

Step 278 回归 smoke 结论：

- 有效 smoke payload 数量：`3`。
- 场景覆盖：
  - 标准 preview-only 请求。
  - 角色类 preview-only 请求。
  - 边界但合法的 preview-only 请求。
- ZDoc `POST /local-trial/preview-only`：`3/3` HTTP `200`。
- ZBid `POST /local-llm/zdoc-preview-only/receive`：`3/3` HTTP `200`。
- ZDoc 顶层 `preview_only=true`、`no_write=true`、`no_evidence=true`：`3/3` 成立。
- ZBid receiver 侧 `preview_only=true`、`no_write=true`、`no_evidence=true`：`3/3` 成立。
- `blocked_reasons`、`validator_result`、`preview_packet`：均可读。
- 五个禁止 flags：均为 `false`。
- 未发现较 Step 275 退化。
- 服务已关闭，端口已释放。

Step 278 未发生：

- 未运行 Ollama。
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。

## 7. ZDoc route 顶层 response 当前基线

当前 ZDoc `POST /local-trial/preview-only` route 顶层 response 基线：

| 字段 | 基线值 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

后续 20 人受控试运行中，以上三项必须作为固定复核项。任一字段缺失或非 `true` 时，必须暂停试运行并记录为异常。

## 8. ZBid receiver 侧当前基线

当前 ZBid receiver 侧基线：

| 字段 | 基线值 |
| --- | --- |
| `preview_only` | `true` |
| `no_write` | `true` |
| `no_evidence` | `true` |

该基线仅证明 ZBid receiver 在 preview-only 链路中保持 no-write / no-evidence 语义，不代表 ZBid 写回开放。

## 9. blocked_reasons / validator_result / preview_packet 可读性基线

当前可读性基线：

| 字段 | 基线要求 | 使用边界 |
| --- | --- | --- |
| `blocked_reasons` | 可读 | 仅用于边界提示、失败原因说明和人工复核。 |
| `validator_result` | 可读 | 仅用于 preview-only validator 结果复核。 |
| `preview_packet` | 可读 | 仅用于 preview-only payload 结构和链路复核。 |

这些字段不得作为正式 evidence，不得作为评分依据，不得写入正式业务数据。

## 10. 五个禁止 flags 均为 false 的基线

当前 no-write / no-formal-chain flags 基线：

| Flag | 基线值 |
| --- | --- |
| `generate_called` | `false` |
| `export_docx_called` | `false` |
| `review_apply_called` | `false` |
| `zbid_writeback_called` | `false` |
| `output_job_export_written` | `false` |

任一 flag 非 `false` 时：

1. 立即暂停试运行。
2. 停止继续发送 payload。
3. 记录日志、问题清单和回退记录。
4. 不得现场修复。
5. 不得 fallback 到正式接口。
6. 等待单独授权后再处理。

## 11. 允许使用范围

当前允许使用范围仅限：

- 20 人团队。
- 管理员监管。
- preview-only。
- 人工复核。
- 使用脱敏样例、测试文档、非正式投标成果。
- 记录完整日志。
- 记录问题清单。
- 记录回退记录。
- 使用已授权的 preview-only endpoint。
- 按管理员 SOP 和 preflight checklist 执行启动、关闭和端口释放检查。

允许范围中的所有输出均为受控试运行记录，不得升级为正式 evidence、评分依据或正式业务交付物。

## 12. 禁止使用范围

以下范围继续禁止：

- `/generate`。
- `/export_docx`。
- `/review/apply`。
- ZBid 写回。
- DOCX 生成。
- `output/job/export` 写入。
- evidence 化。
- 评分依据化。
- 50 人正式部署。
- 正式生产服务器定位。
- 顶级模型升级。
- 正式业务数据写入。
- 未授权服务启动。
- 未授权端口访问。
- 未授权 endpoint 调用。
- 未授权 preview payload 发送。

## 13. 管理员启动前签核要求

管理员每次启动受控试运行前必须完成签核：

| 签核项 | 要求 |
| --- | --- |
| ZDoc 仓库路径、分支、HEAD | 已记录 |
| ZBid 仓库路径、分支、HEAD | 已记录 |
| ZDoc `git status --short` | 空 |
| ZBid `git status --short` | 空 |
| 服务端口 | 已确认未被未知进程占用 |
| 残留服务进程 | 已检查 |
| Ollama | 未运行，除非未来另行授权 |
| 试运行数据 | 脱敏 / 模拟 / 非正式 |
| endpoint 清单 | 仅 preview-only |
| 日志目录或记录方式 | 已确认 |
| 问题清单记录方式 | 已确认 |
| 回退记录方式 | 已确认 |
| 暂停触发条件 | 已确认 |
| 关闭和端口释放检查 | 已确认 |

任一签核项不满足时，不得启动试运行。

## 14. 试运行人员使用边界

试运行人员必须遵守：

- 只使用管理员允许的 preview-only 入口。
- 只使用脱敏样例、测试文档和非正式投标成果。
- 不上传真实敏感业务材料。
- 不将返回结果作为正式 evidence。
- 不将返回结果作为评分依据。
- 不要求生成 DOCX。
- 不要求触发 review/apply。
- 不要求 ZBid 写回。
- 不绕过管理员启动、关闭、日志和问题记录要求。
- 发现异常时停止继续操作并上报管理员。

## 15. 日志记录要求

每次受控试运行必须记录：

- 日期与时间。
- 管理员或操作者角色。
- ZDoc / ZBid 仓库 HEAD。
- 服务启动命令。
- 服务 PID。
- 端口。
- endpoint 清单。
- 请求数量。
- HTTP 状态汇总。
- ZDoc 顶层 `preview_only`、`no_write`、`no_evidence`。
- ZBid receiver 侧 `preview_only`、`no_write`、`no_evidence`。
- `blocked_reasons`、`validator_result`、`preview_packet` 可读性。
- 五个禁止 flags。
- 服务关闭方式。
- PID 停止结果。
- 端口释放结果。
- 是否生成 DOCX。
- 是否写 `output/job/export`。

## 16. 问题清单记录要求

问题清单必须包含：

- 问题编号。
- 发现时间。
- 角色或场景。
- 请求类型。
- 现象描述。
- 风险等级。
- 是否影响 preview-only。
- 是否涉及写入风险。
- 是否涉及证据化或评分化风险。
- 是否需要暂停。
- 是否需要回退。
- 是否需要单独授权修复。

问题不得现场修复，除非用户另行明确授权。

## 17. 回退记录要求

回退记录必须包含：

- 回退触发原因。
- 触发时间。
- 操作人。
- 涉及服务。
- 停止服务方式。
- PID 停止结果。
- 端口释放结果。
- `git status --short` 复核结果。
- DOCX 生成复核结果。
- `output/job/export` 写入复核结果。
- 后续处理建议。

## 18. 服务启动、端口监听、关闭、释放检查要求

服务运行控制要求：

1. 启动前检查授权端口是否空闲。
2. 启动前检查残留服务进程。
3. 启动前检查仓库状态。
4. 启动时记录完整命令。
5. 启动后记录 PID。
6. 启动后确认端口监听。
7. 仅调用授权 preview-only endpoint。
8. 关闭时只关闭本次启动的服务。
9. 不强制结束未知进程。
10. 关闭后确认 PID 已停止。
11. 关闭后确认端口无监听。
12. 关闭后复核未生成 DOCX。
13. 关闭后复核未写 `output/job/export`。

## 19. 必须暂停试运行的触发条件

出现以下任一情况必须暂停试运行：

- ZDoc 顶层 `preview_only` 缺失或非 `true`。
- ZDoc 顶层 `no_write` 缺失或非 `true`。
- ZDoc 顶层 `no_evidence` 缺失或非 `true`。
- ZBid receiver 侧 `preview_only` 缺失或非 `true`。
- ZBid receiver 侧 `no_write` 缺失或非 `true`。
- ZBid receiver 侧 `no_evidence` 缺失或非 `true`。
- 任一禁止 flag 非 `false`。
- `/generate` 被调用或疑似被调用。
- `/export_docx` 被调用或疑似被调用。
- `/review/apply` 被调用或疑似被调用。
- ZBid 写回被调用或疑似被调用。
- DOCX 被生成。
- `output/job/export` 被写入。
- preview-only 结果被作为 evidence 或评分依据。
- 出现未授权 endpoint 调用。
- 出现未授权端口访问。
- 服务关闭失败或端口无法释放。
- 引入真实敏感业务数据。
- 试运行人员无法理解边界要求。

## 20. 回退条件

满足以下任一条件时必须执行回退：

- 服务启动进入未知状态。
- PID 与授权服务无法对应。
- 端口释放失败。
- 出现正式链调用迹象。
- 出现写入迹象。
- 出现 DOCX 生成迹象。
- 出现 ZBid 写回迹象。
- 出现证据化或评分化使用。
- 出现正式业务数据写入。
- 管理员无法确认当前状态安全。

回退后不得现场修复。任何代码、配置、endpoint、测试或运行方式变更都必须另行授权。

## 21. AI知识图谱大全 文件夹继续暂停说明

用户已暂停以下文件夹识别任务：

```text
/Users/youfeini/Desktop/AI知识图谱大全
```

当前 ZDoc-ZBid 20 人受控试运行启用决策与该文件夹无关。后续除非用户另行明确授权，不得访问、扫描、读取、复制、移动、分析或识别该文件夹。

若未来需要启动 AI知识图谱大全 KG 专项，应作为独立授权、独立边界、独立报告执行，不得混入 ZDoc-ZBid 受控试运行主线。

## 22. 后续可选路径

后续可选路径如下，均需用户另行明确授权：

1. 进入 20 人受控试运行执行。
2. 继续 observation-period controlled execution。
3. 编制管理员培训材料。
4. 编制自动化回归测试方案。
5. 后续单独启动 AI知识图谱大全 KG 专项。
6. 后续再评估 50 人正式部署。

建议优先顺序：

1. 若目标是实际使用，先进入 20 人受控试运行执行。
2. 若目标是继续稳态观察，继续 observation-period controlled execution。
3. 若目标是减少管理员操作风险，先编制管理员培训材料和自动化回归测试方案。
4. AI知识图谱大全 KG 专项和 50 人正式部署应保持后置，并单独授权。

## 23. 是否建议结束当前 20 人可用阶段建设主线

建议结论：

```text
建议结束当前“20 人 preview-only 受控试运行可用阶段建设主线”，并将后续工作切换为受控运行、培训、回归测试方案或专项授权。
```

理由：

- 20 人受控试运行所需的 preview-only 链路、人工复核、日志、问题清单、回退记录、管理员 SOP、preflight checklist、服务启动关闭 smoke、endpoint smoke、schema 观察项关闭和 post-schema 回归 smoke 已形成闭环。
- 当前主线继续堆叠建设文档的收益降低。
- 后续更有价值的工作是受控运行、人员培训、自动化回归测试方案和明确的专项授权。

该建议不代表自动停止后续试运行，也不代表自动进入任何下一步。

## 24. Step 281 授权请求草案

如需继续，可使用以下授权语：

```text
执行 Step 281：ZDoc-ZBid 20-user controlled pilot execution or next-stage controlled operation。

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<由用户填写 Step 281 开始前 HEAD>

ZBid 仓库：
/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean

ZBid 分支：
local-llm-integration-clean

ZBid 开始前 HEAD：
<由用户填写 ZBid 开始前 HEAD>

授权范围：
仅在 20 人 preview-only / no-write / no-evidence 受控试运行边界内执行。允许启动必要 ZDoc / ZBid 本地服务、访问必要本地端口、调用授权 preview-only endpoint、发送脱敏 / 模拟 / 非正式 preview-only payload，并记录日志、问题清单和回退记录。

必须保持：
1. ZDoc route 顶层 preview_only=true、no_write=true、no_evidence=true；
2. ZBid receiver 侧 preview_only=true、no_write=true、no_evidence=true；
3. blocked_reasons / validator_result / preview_packet 可读；
4. generate_called=false；
5. export_docx_called=false；
6. review_apply_called=false；
7. zbid_writeback_called=false；
8. output_job_export_written=false。

严格禁止：
1. 不修改代码 / tests / frontend / backend / 既有 docs，除非本步骤另行列明允许文件；
2. 不运行 Ollama；
3. 不触发 /generate；
4. 不触发 /export_docx；
5. 不触发 /review/apply；
6. 不触发 ZBid 写回；
7. 不生成 DOCX；
8. 不写 output/job/export；
9. 不把 preview-only 结果作为 evidence；
10. 不把 preview-only 结果作为评分依据；
11. 不访问、扫描、读取、复制、移动或分析 /Users/youfeini/Desktop/AI知识图谱大全；
12. 不进入 50 人正式部署设计；
13. 不将当前主机定位为长期正式生产服务器；
14. 不实施顶级模型升级。

完成后必须提交运行报告并停止，等待用户审核。
```
