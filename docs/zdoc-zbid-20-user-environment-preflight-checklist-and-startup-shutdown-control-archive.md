# ZDoc-ZBid 20-user environment preflight checklist and startup-shutdown control archive

## 1. 编制目的

本文档用于归档 ZDoc-ZBid 20 人受控常态试运行的环境预检清单、启动前控制项、关闭后收口项与管理员签核模板。

本文档仅作为 docs-only 操作规程归档，不代表当前步骤允许启动服务、访问端口、调用 endpoint、运行 Ollama、生成 DOCX、写入 `output/job/export`、触发 ZBid 写回、进入 50 人正式部署设计或实施顶级模型升级。

## 2. 适用范围

适用范围限定为 20 人受控常态试运行：

- ZDoc preview-only 本地试运行。
- ZBid preview-only receiver 本地试运行。
- ZDoc -> ZBid preview-only payload 发送与接收。
- 管理员启动前检查、运行中记录、关闭后收口。
- 有效请求、前置 payload 校准、adapter 阻断、preview-only calibration call 的计数与归档。

不适用范围：

- 正式生成链。
- DOCX 导出链。
- review/apply 链。
- ZBid 写回链。
- 正式 evidence 写入。
- 评分依据写入。
- 长期正式生产服务器运行。
- 50 人正式部署设计。
- 顶级本地大模型升级实施。
- `/Users/youfeini/Desktop/AI知识图谱大全` 文件夹识别、扫描、读取、复制、移动或分析。

## 3. 启动前 Git 状态检查清单

每次授权试运行前，管理员必须完成 Git 状态检查：

- 确认 ZDoc 仓库路径与授权一致。
- 确认 ZDoc 分支与授权一致。
- 确认 ZDoc 开始前 HEAD 与授权一致。
- 确认 ZDoc `git status --short` 符合授权要求。
- 确认 ZBid 仓库路径与授权一致。
- 确认 ZBid 分支与授权一致。
- 确认 ZBid 开始前 HEAD 与授权一致。
- 确认 ZBid `git status --short` 符合授权要求。
- 如任一仓库分支、HEAD 或 clean 状态不一致，立即停止，不得启动服务，不得访问端口，不得调用 endpoint。

## 4. ZDoc / ZBid 仓库路径与分支核验清单

授权执行时建议按以下表格记录：

| 项目 | 核验内容 | 结果 |
| --- | --- | --- |
| ZDoc 仓库路径 | `/Users/youfeini/Desktop/文档生成系统` | 待填写 |
| ZDoc 分支 | `main` 或用户授权分支 | 待填写 |
| ZDoc 开始前 HEAD | 用户授权 HEAD | 待填写 |
| ZDoc git status | 应符合授权要求 | 待填写 |
| ZBid 仓库路径 | `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean` | 待填写 |
| ZBid 分支 | `local-llm-integration-clean` 或用户授权分支 | 待填写 |
| ZBid 开始前 HEAD | 用户授权 HEAD | 待填写 |
| ZBid git status | 应符合授权要求 | 待填写 |

本文档不执行 ZBid 仓库访问；表格仅作为未来已授权执行步骤的核验模板。

## 5. 主机状态检查清单

管理员应在授权运行步骤中确认主机状态：

- 当前主机仅作为 20 人试运行主机。
- 当前主机不作为长期正式生产服务器。
- 当前主机不作为 50 人正式部署服务器。
- 当前主机不作为 DOCX 生成服务器。
- 当前主机不作为 ZBid 写回服务器。
- 当前主机不作为正式 evidence 或评分依据写入服务器。
- 当前主机不实施顶级本地大模型升级。
- 试运行期间仅允许使用脱敏 / 模拟 / 非正式 payload。

## 6. 端口占用检查清单

端口检查只允许在用户明确授权启动服务和访问端口的步骤中执行。docs-only 阶段不得执行端口访问或端口探测。

授权运行时需记录：

- ZDoc 计划端口。
- ZBid 计划端口。
- 端口是否沿用上一轮已验证端口。
- 如端口被占用，记录占用原因、替代端口和审批依据。
- 记录服务 PID 与端口绑定关系。
- 记录关闭后端口是否释放。
- 如端口未释放，立即暂停试运行并记录问题，不得现场修代码。

## 7. 服务启动前禁止项复核

服务启动前必须确认以下事项均为否：

- 是否准备调用 `/generate`。
- 是否准备调用 `/export_docx`。
- 是否准备调用 `/review/apply`。
- 是否准备调用 ZBid 写回 endpoint。
- 是否准备生成 DOCX。
- 是否准备写入 `output/job/export`。
- 是否准备将 preview-only 结果作为 evidence。
- 是否准备将 preview-only 结果作为评分依据。
- 是否准备写入正式业务数据。
- 是否准备进入 50 人正式部署设计。
- 是否准备实施顶级模型升级。
- 是否准备访问、扫描、读取、复制、移动或分析 `/Users/youfeini/Desktop/AI知识图谱大全`。

任一项为是，必须停止。

## 8. preview-only / no-write / no-evidence 边界复核

每轮试运行必须确认：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

复核口径：

- preview-only 只允许预览、提示、人工复核和问题发现。
- no-write 表示不得写正式业务数据、正式结果、正式存储、ZBid 写回或 `output/job/export`。
- no-evidence 表示 preview-only 输出不得作为 evidence。
- 五个 false flags 只用于边界确认，不得作为正式 evidence 或评分依据。

## 9. ZDoc 服务启动前检查项

ZDoc 服务仅允许在后续明确授权步骤中启动。启动前必须确认：

- 授权允许启动 ZDoc 本地服务。
- 授权允许访问指定本地端口。
- 授权允许调用指定 preview-only endpoint。
- ZDoc 仓库、分支、HEAD 与授权一致。
- ZDoc 工作区状态符合授权要求。
- 不写入 `.env`、配置文件或持久配置。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不使用真实投标 evidence。

## 10. ZBid 服务启动前检查项

ZBid 服务仅允许在后续明确授权步骤中启动。启动前必须确认：

- 授权允许启动 ZBid preview-only receiver 本地服务。
- 授权允许访问指定本地端口。
- 授权允许调用 `POST /local-llm/zdoc-preview-only/receive` 或用户明确授权的 preview-only endpoint。
- ZBid 仓库、分支、HEAD 与授权一致。
- ZBid 工作区状态符合授权要求。
- ZBid 不 commit、不 tag、不 push，除非用户明确授权。
- 不触发 ZBid 写回。
- 不写正式业务数据。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不将 preview-only 结果作为 evidence 或评分依据。

## 11. preview-only network-send 启用前检查项

preview-only network-send 只允许在明确授权执行步骤中临时启用。

启用前必须确认：

- 已获得用户明确授权。
- 仅使用临时环境变量。
- 不写入 `.env`、配置文件或持久配置。
- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true` 仅限本轮授权使用。
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true` 仅限本轮授权使用。
- ZBid receiver endpoint 仅配置为授权本地 preview-only 地址。
- payload 仅包含 preview_packet、validator_result、blocked_reasons 与 no-write / no-formal-chain flags。
- payload 不包含 DOCX、正式 evidence、正式评分结果、writeback 数据或正式业务数据。

## 12. 有效请求与前置校准计数规则

有效请求必须与前置 payload 校准分开统计。

有效请求计数条件：

- 已进入授权的试运行批次。
- payload 使用合法 preview-only 枚举和合法 payload-shape。
- ZDoc outbound 已按授权发送。
- ZBid receiver 已按授权接收。
- 返回结果保持 preview-only / no-write / no-evidence。
- 五个 no-write / no-formal-chain flags 均为 false。

前置校准计数规则：

- 数量从严控制。
- 单独计数。
- 单独归档。
- 单独记录是否被 adapter 阻断。
- 单独记录是否作为 preview-only calibration call 到达 ZBid receiver。
- 不得混入有效请求。
- 不得计入有效观察期请求。
- 不得归为 evidence。
- 不得归为评分依据。

## 13. 日志、问题清单、回退记录检查项

每轮试运行必须准备并归档：

- 运行日志。
- 有效请求清单。
- 前置校准清单。
- adapter 阻断清单。
- preview-only calibration call 清单。
- 问题清单。
- 回退记录。
- 服务启动记录。
- 服务关闭记录。
- 端口释放记录。

每条日志至少记录：

- 时间。
- 操作者角色。
- 批次编号。
- 场景编号。
- 模拟用户标识。
- 角色类型。
- 请求入口。
- payload 类型。
- HTTP 状态。
- ZDoc outbound 是否发送。
- ZBid receiver 是否接收。
- blocked_reasons 是否可读。
- validator_result 是否可读。
- preview-only / no-write / no-evidence 是否成立。
- 五个 false flags 是否均为 false。
- 是否需要回退。

## 14. 服务关闭检查项

每轮授权运行结束后，管理员必须确认：

- 本轮启动的 ZDoc 服务已关闭。
- 本轮启动的 ZBid 服务已关闭。
- 关闭方式已记录。
- 服务 PID 已记录。
- 日志末尾状态已记录。
- 无后续未授权请求继续执行。
- 未因关闭失败修改代码。
- 未因关闭失败修改配置。
- 如服务无法关闭，立即暂停并记录，不得进入下一轮。

## 15. 端口释放检查项

端口释放只允许在授权运行步骤中检查；docs-only 阶段不得访问端口。

授权运行收口时必须确认：

- ZDoc 授权端口已无监听。
- ZBid 授权端口已无监听。
- 如使用替代端口，替代端口也已无监听。
- 端口释放结果已写入运行日志。
- 端口未释放时立即暂停试运行。
- 端口未释放时不得进入下一批次或下一步骤。

## 16. 禁止接口复核清单

每日收口时必须确认以下接口未被调用：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回 endpoint
- 未授权 ZDoc endpoint
- 未授权 ZBid endpoint
- 未授权外部 endpoint

如发现任何禁止接口调用，必须立即暂停并进入回退流程。

## 17. output/job/export 路径复核清单

`output/job/export` 复核只用于确认无写入，不得写入该路径。

授权运行时应记录：

- ZDoc 侧 `output/job/export` 前后状态。
- ZBid 侧 `output/job/export` 前后状态。
- 是否出现新增文件。
- 是否出现 DOCX。
- 是否出现 job/export 产物。
- 是否出现评分依据或 evidence 产物。

发现任何新增写入，必须暂停试运行并记录。

## 18. 必须暂停试运行的触发条件

出现以下任一情况，必须暂停试运行：

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
- 主机被重新定位为正式生产服务器。
- 进入 50 人正式部署设计或顶级模型升级实施。

## 19. 回退流程

回退流程如下：

1. 立即停止新增请求。
2. 停止本轮授权启动的服务。
3. 确认端口释放。
4. 记录触发条件、时间、角色、批次、场景和 payload。
5. 固化运行日志、问题清单和回退记录。
6. 检查是否出现 DOCX、`output/job/export`、ZBid 写回、evidence 或评分依据。
7. 区分有效请求与前置校准。
8. 不现场修复代码。
9. 不修改 tests、frontend、backend 或既有 docs。
10. 起草单独授权请求后再进入修复或复验。

## 20. 管理员每日启动前与关闭后签核模板

```text
日期：
管理员：
授权步骤：

启动前签核：
- ZDoc 仓库 / 分支 / HEAD：
- ZDoc git status --short：
- ZBid 仓库 / 分支 / HEAD：
- ZBid git status --short：
- 授权服务：
- 授权端口：
- 授权 endpoint：
- 是否仅 preview-only / no-write / no-evidence：
- 是否禁止 /generate：
- 是否禁止 /export_docx：
- 是否禁止 /review/apply：
- 是否禁止 ZBid 写回：
- 是否禁止 DOCX：
- 是否禁止 output/job/export 写入：
- 是否禁止 evidence 化：
- 是否禁止评分化：
- 是否禁止访问 AI知识图谱大全 文件夹：
- 启动前结论：通过 / 不通过

关闭后签核：
- 有效请求数：
- 前置校准数：
- adapter 阻断数：
- preview-only calibration call 数：
- HTTP 200 结果：
- 五个 false flags 结果：
- 问题清单编号：
- 回退记录编号：
- ZDoc 服务关闭状态：
- ZBid 服务关闭状态：
- ZDoc 端口释放状态：
- ZBid 端口释放状态：
- output/job/export 前后状态：
- DOCX 生成情况：
- ZBid 写回情况：
- evidence 化情况：
- 评分化情况：
- 关闭后结论：通过 / 暂停 / 需回退
```

## 21. Step 266 授权请求草案

以下为可复制的 Step 266 授权请求草案。该草案不代表当前已授权执行 Step 266。

```text
执行 Step 266：ZDoc-ZBid 20-user environment preflight checklist stage review and next action authorization request

仓库：
/Users/youfeini/Desktop/文档生成系统

分支：
main

开始前 HEAD：
<填写 Step 265 结束后 HEAD>

特别说明：
不得访问、扫描、读取、复制、移动或分析 /Users/youfeini/Desktop/AI知识图谱大全。

本步性质：
docs-only / stage-review-only / no-code-change / no-service / no-port-access / no-endpoint-call / no-writeback

目标：
归档 Step 265《20-user environment preflight checklist and startup-shutdown control archive》编制结果，并起草下一步授权请求。

允许新增文件：
docs/<填写 Step 266 目标文档名>.md

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
- Step 265 是否仅新增目标 docs 文件。
- 环境预检是否覆盖 Git 状态、仓库路径、主机状态、端口、服务启停、preview-only 边界、前置校准计数、日志、问题清单、回退记录和每日签核。
- 是否继续保持 preview-only / no-write / no-evidence。
- 是否明确 docs-only 阶段不得执行端口访问或 endpoint 调用。
- 是否明确当前主机仅作为 20 人试运行主机，不作为长期正式生产服务器。

完成后必须停止，不得自动进入后续步骤。
```
