# SYSTEM-AUTONOMY-003 Goal Mode Permission Matrix And State Machine Gate

## 1. 节点定位

`SYSTEM-AUTONOMY-003-GOAL-MODE-PERMISSION-MATRIX-AND-STATE-MACHINE-GATE` 是 ZDoc / 本地 AI 应用 / LOCAL-LAUNCHER 系统自治路线的权限矩阵与状态机 Gate。

本节点承接 `SYSTEM-AUTONOMY-001-GOAL-MODE-GOVERNANCE-AND-ROADMAP-GATE` 的治理总纲，以及 `SYSTEM-AUTONOMY-002-GOAL-MODE-TASK-DECOMPOSITION-GATE` 的任务分解结果，将后续系统自治建设固化为可审计、可阻断、可回滚、可逐级审批的权限矩阵和状态机。

本节点结论边界如下：

1. 本节点只定义权限矩阵、系统自治状态机、状态转换规则和审批转换规则。
2. 本节点不实施任何后续能力。
3. 本节点不运行或验证 runtime。
4. 本节点不启动服务。
5. 本节点不启动 Web UI。
6. 本节点不访问 endpoint，不执行 curl / HTTP request / localhost / 端口探测。
7. 本节点不运行 Ollama，不执行模型命令，不进行模型推理，不输入 prompt。
8. 本节点不读取真实 KG / 真实项目资料 / 招标文件 / 图纸 / 清单 / 项目样本。
9. 本节点不读取 secrets / tokens / credentials / 环境变量敏感信息。
10. 本节点不读取 output / job / export / 生成结果 / 日志正文。
11. 本节点不执行 generation / export / write-back。
12. 本节点不替代后续实现 Gate、runtime preflight Gate、dry-run Gate 或 trial Gate。
13. 本节点完成后必须停止，等待 ChatGPT 总控师审核。

## 2. 权限矩阵总表

默认原则：

1. 未在当前 Gate 明确允许的权限，默认禁止。
2. 旧节点授权不得自动继承到新节点。
3. docs-only 证据不得替代 runtime、endpoint、模型、真实资料、trial 或正式使用证据。
4. 证据不足时默认阻断，不得补写结论替代证据。

| 权限维度 | 默认状态 | 允许条件 | 禁止条件 | 人工审批等级 | 必须提交的证据 | 触发回滚或阻断的条件 |
| --- | --- | --- | --- | --- | --- | --- |
| docs 读取 | 仅授权清单内允许 | 当前 Gate 明确列出路径，且目的为治理、规划或审计 | 读取未列入 allowlist 的 docs；读取 output/job/export/log 正文补证 | A0 | 实际读取文件清单、读取目的、未读范围声明 | 需要读取未授权 docs 或证据链无法支撑 |
| docs 写入 | 默认禁止，除目标 docs 外 | 当前 Gate 指定唯一目标 docs 文件 | 修改既有 docs 或新增非目标文件 | A1 | 新增/修改文件清单、diff 检查、Git 状态 | 出现非目标 docs 变更或目标文件不唯一 |
| 代码读取 | 默认禁止 | 进入 code-read-only Gate，路径 allowlist 明确 | 未获 A2 审批；读取 runtime、API、模型、KG 代码超出清单 | A2 | 代码读取 allowlist、实际读取文件、未修改确认 | 读取范围不明确或碰到敏感/真实资料边界 |
| 代码修改 | 默认禁止 | 进入 code-change Gate，目标文件和 patch 范围唯一 | 未获 A3 审批；顺手重构；改无关模块 | A3 | 变更文件、diff、最小回归、回滚建议 | 混入无关文件、测试缺失、改动范围失控 |
| 脚本读取 | 默认禁止 | 当前 Gate 明确脚本路径和只读目的 | 读取 runtime 脚本正文、启动脚本或含敏感字段脚本 | A2 或 A4 | 脚本路径 allowlist、读取字段、敏感字段排除声明 | 脚本可能触发 runtime 或包含凭据 |
| 脚本执行 | 默认禁止 | 明确命令 allowlist，且命令不会启动服务或访问 endpoint | 未列入命令清单；执行启动、探测、模型或写回脚本 | A4 起 | 命令、参数、输出摘要、退出码、无副作用说明 | 命令超出 allowlist 或产生运行副作用 |
| 服务启动 | 默认禁止 | controlled runtime Gate 明确启动、停止、端口、回滚 | docs-only、preflight 或未获服务授权 | A4 起 | 启动命令、停止命令、PID/端口证据、回滚方案 | 服务无法停止、端口/进程不一致、日志处置不清 |
| Web UI 启动 | 默认禁止 | Web UI Gate 明确启动方式、访问范围和停止条件 | docs-only；未授权打开页面或启动脚本 | A4 起 | 启动命令、窗口/页面证据、停止证据 | UI 启动影响 runtime、端口或真实数据 |
| endpoint 访问 | 默认禁止 | endpoint Gate 明确 endpoint、method、payload、只读保证 | 未完成 runtime preflight；访问业务 endpoint | A5 | endpoint 清单、请求方法、返回摘要、无写入保证 | endpoint 不在清单、返回含敏感/真实资料 |
| curl / HTTP request / localhost / 端口探测 | 默认禁止 | 当前 Gate 逐项授权目标地址、方法、超时和只读边界 | docs-only；未获 endpoint/preflight 授权 | A5 | 命令清单、目标、结果摘要、无业务调用确认 | 出现未授权地址、端口、HTTP 行为 |
| Ollama | 默认禁止 | Ollama inventory Gate 明确命令仅做 inventory 且不推理 | 未授权执行 `ollama`；触发模型进程或推理 | A5 | 命令、模型清单摘要、无推理确认 | 命令包含 run/chat/generate/prompt 或输出不可审计 |
| 模型命令 | 默认禁止 | 独立模型命令 Gate 明确命令和禁止推理边界 | 未获授权；命令可能触发推理或下载 | A5 | 命令 allowlist、参数、输出摘要、无 prompt 确认 | 命令目的不清或改变模型环境 |
| 模型推理 | 默认禁止 | 独立推理 Gate 明确模型、prompt、输入、输出处置 | docs-only、preflight、inventory 阶段 | A5 起 | 模型、prompt、输入来源、输出保存/删除规则 | prompt 未审、输出处置不清、混入真实资料 |
| prompt 输入 | 默认禁止 | prompt Gate 明确目标系统、prompt 内容、输出边界 | 未获 dry-run 或推理授权；向本地/远程模型输入 | A5 起 | prompt 文本、目标系统、输入来源、输出处置 | prompt 含真实资料或触发生成/写回 |
| KG 读取 | 默认禁止 | 真实 KG 授权 Gate 明确 KG 范围、字段、访问方式 | docs-only；未获真实数据授权 | A6 | KG 清单、字段范围、访问方式、责任边界 | 读取未列字段、无法证明授权、含敏感资料 |
| 真实项目资料读取 | 默认禁止 | 真实项目资料 Gate 明确项目、资料类别、脱敏/授权证据 | 未获 A6；资料来源或脱敏状态不明 | A6 | 资料清单、授权证明、脱敏证明或真实使用审批 | 资料不在清单、授权链不完整 |
| 招标文件 / 图纸 / 清单 / 项目样本读取 | 默认禁止 | 资料 Gate 逐类授权，且用途、保留、删除规则明确 | docs-only；未列明资料类别和范围 | A6 | 文件类别、路径清单、用途、保留/删除规则 | 误读真实资料或样本脱敏不足 |
| secrets / tokens / credentials / 环境变量敏感信息读取 | 默认禁止 | 原则不授权；如确需，由最高审批另设安全 Gate | 任意普通 Gate；通过 env、配置或日志读取敏感值 | A8 | 不读取确认；如特殊授权则需脱敏回报和安全方案 | 任何误读敏感值立即阻断并停止扩散 |
| output / job / export / 日志正文读取 | 默认禁止 | 仅在审计 Gate 明确范围且不含真实/敏感正文 | 为补证读取生成结果、运行日志或导出正文 | A6 起 | 路径清单、字段范围、是否正文、敏感排除声明 | 误读正文、生成结果或真实业务输出 |
| generation | 默认禁止 | generation Gate 明确输入、输出、保留、删除和责任 | docs-only、dry-run 未授权、真实资料未授权 | A5 起 | 输入来源、输出路径、保留/删除、审计证据 | 输出对象不清、生成结果不可回滚 |
| export | 默认禁止 | export Gate 明确格式、目标、对象、接收方和回滚 | 未授权导出；导出真实/敏感资料 | A5 起 | 导出路径、格式、对象、接收边界、回滚方案 | 目标路径不清、导出范围超授权 |
| write-back | 默认禁止 | write-back Gate 明确写回对象、备份、回滚和审批责任 | 未获写回授权；覆盖系统/资料/结果 | A5 起 | 写回对象、备份证据、回滚命令、审计证据 | 写回不可逆、备份缺失、对象不唯一 |
| trial | 默认禁止 | trial Gate 明确人员、范围、数据、支持和回滚 | 未完成 dry-run、真实数据授权或 readiness 审核 | A7 | 试用范围、账号、问题处理、回滚方案 | 试用范围扩大、问题未闭环 |
| 真实使用 | 默认禁止 | production authorization Gate 审核通过 | 未完成 trial、freeze、正式审批 | A8 | 生产范围、责任边界、支持、审计、回滚 | 审计/支持/回滚不闭环 |
| 50 人正式使用 | 默认禁止 | 50-user readiness 最高审批通过 | 未完成小范围试运行和冻结审查 | A8 | 人员范围、培训、权限、支持、风险接受、最终签核 | freeze 清单不完整、风险未接受、无最高审批 |

## 3. 系统自治状态机定义

状态机原则：

1. 状态只能沿已审批路径推进。
2. 任一状态发现越权、证据不足、Git 不一致或敏感边界触发，必须进入 `SX_BLOCKED_OR_ROLLBACK`。
3. 状态名中的允许动作不得被解释为更高状态授权。
4. 每个状态完成后必须停止，等待 ChatGPT 总控师审核后才能转换。

| 状态 | 状态目标 | 允许动作 | 禁止动作 | 可读取范围 | 可写入范围 | 进入条件 | 退出条件 | 所需人工审批 | 必须提交证据 | 失败回滚路径 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `S0_DOCS_ONLY_PLANNING` | 仅做路线规划和节点定义 | 读取授权 pasted text / docs；新增授权 docs | 代码读取、runtime、endpoint、模型、真实资料 | 当前 Gate allowlist | 当前 Gate 唯一目标 docs | ChatGPT 总控师给出 docs-only 节点 | 规划文档完成、Git 证据完整、停止 | A0/A1 | 分支、HEAD/tag、读取文件、新增文件、禁止项否定 | 证据不足则阻断，不提交 |
| `S1_DOCS_GOVERNANCE_LOCKED` | 固化治理总纲 | 引用已审核治理结论 | 修改治理结论、继承 runtime 授权 | 已授权治理 docs | 当前授权 docs | `SYSTEM-AUTONOMY-001` 审核通过 | 治理边界被后续 Gate 正确引用 | A1 | 001 结论引用、未扩大边界确认 | 回到 S0 修正文档口径 |
| `S2_TASK_DECOMPOSITION_LOCKED` | 固化任务分解和 Gate 依赖 | 引用任务树、Gate 清单、停止点 | 自动进入拆出的后续 Gate | 001/002 授权 docs | 当前授权 docs | `SYSTEM-AUTONOMY-002` 审核通过 | 任务分解被状态机承接 | A1 | 002 结论引用、未进入后续节点确认 | 回到 S1 重审依赖关系 |
| `S3_PERMISSION_MATRIX_LOCKED` | 固化权限矩阵、状态机和转换规则 | 完成权限矩阵、状态机、审批等级 | 进入 004、读代码、运行验证 | 001/002/当前授权文本 | 当前唯一目标 docs | 003 docs-only 授权生效 | 003 commit/tag/clean 完成并停止 | A1 | 权限矩阵、状态表、转换表、commit/tag/status | 证据不足进入 SX |
| `S4_CODE_READ_ONLY_INVENTORY` | 只读盘点代码结构 | 读取明确 allowlist 中代码/配置 | 修改代码、执行脚本、runtime、endpoint | A2 授权文件清单 | 默认不得写入；只允许授权盘点报告 | S3 审核通过且 A2 授权 | 盘点报告完成并停止 | A2 | 读取清单、未修改确认、风险清单 | 读取越界进入 SX |
| `S5_CODE_CHANGE_PROPOSAL` | 提出代码修改方案 | 生成 patch 方案、测试计划、回滚建议 | 直接改代码、运行服务、扩大范围 | S4 盘点证据和授权 docs | 授权方案 docs | S4 审核通过且需改动被确认 | 方案被批准或驳回 | A3 前置 | 目标文件、改动理由、最小回归、回滚方案 | 方案不唯一则回 S4 或 SX |
| `S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME` | 实施代码修改但禁止 runtime | 修改授权代码、运行授权静态/单测 | 启动服务、endpoint、Ollama、模型、真实资料 | 授权代码和测试文件 | 授权代码/测试文件 | S5 获 A3 审批 | patch 完成、最小回归完成、未运行 runtime | A3 | diff、测试结果、未运行确认、Git 状态 | 测试失败按授权回滚或进入 SX |
| `S7_STATIC_VALIDATION_ONLY` | 只做静态校验 | lint、typecheck、文本检查或授权单测 | 服务启动、HTTP、端口、模型、真实资料 | 授权代码/配置/报告 | 不写入或只写校验报告 | S6 完成且校验命令 allowlist 明确 | 静态证据通过并停止 | A3/A4 | 命令、退出码、耗时、失败摘要 | 静态失败回 S6 或 SX |
| `S8_RUNTIME_PREFLIGHT_AUTHORIZATION_REQUIRED` | runtime 预检授权等待 | 起草 preflight 命令清单和停止条件 | 执行 preflight、启动服务、端口探测 | 授权 docs 和方案 | preflight 授权文档 | S7 通过且需要 runtime 预检 | A4 审批通过或拒绝 | A4 | 命令 allowlist、禁止命令、回滚策略 | 未获授权保持阻断 |
| `S9_RUNTIME_PREFLIGHT_NO_ENDPOINT` | 执行 runtime 前置检查但禁止 endpoint | 执行 A4 allowlist 中非 endpoint 预检 | endpoint、curl、HTTP、localhost、端口探测，除非逐项授权 | A4 指定文件/命令输出摘要 | preflight 报告 | S8 获 A4 审批 | preflight 通过并停止 | A4 | 命令、退出码、无 endpoint/Ollama/模型确认 | 预检失败进入 SX |
| `S10_MOCK_OR_DRY_RUN_AUTHORIZATION_REQUIRED` | 等待 mock / dry-run 授权 | 设计 mock 输入、输出处置、删除规则 | 输入 prompt、生成、导出、写回 | 授权 docs 和 mock 方案 | mock/dry-run 授权文档 | S9 通过且需 dry-run | A5 审批通过或拒绝 | A5 | mock 来源、无真实资料证明、输出处置 | 来源不明保持阻断 |
| `S11_CONTROLLED_DRY_RUN_NO_REAL_DATA` | 受控 dry-run，禁止真实数据 | 使用 mock 或证明脱敏数据进行授权 dry-run | 真实 KG、真实项目资料、未审 prompt、写回 | A5 授权 mock/脱敏输入 | dry-run 输出或报告，仅限授权路径 | S10 获 A5 审批 | dry-run 完成、输出处置完成、停止 | A5 | 输入证明、命令、输出处置、无真实资料确认 | dry-run 失败进入 SX |
| `S12_SINGLE_USER_TRIAL_AUTHORIZATION_REQUIRED` | 等待单人试用授权 | 起草单人试用范围、账号、支持、回滚 | 直接试用、多人使用、真实使用 | dry-run 证据和 trial 方案 | trial 授权文档 | S11 审核通过 | A7 单人试用审批通过或拒绝 | A7 | 试用范围、数据边界、问题处理、回滚方案 | 未获授权保持阻断 |
| `S13_LIMITED_PILOT_AUTHORIZATION_REQUIRED` | 等待小范围试运行授权 | 起草小范围试运行和支持方案 | 扩大真实使用、50 人使用 | 单人试用证据和 pilot 方案 | pilot 授权文档 | 单人试用完成且问题闭环 | A7 小范围审批通过或拒绝 | A7 | 试用结果、问题闭环、支持机制 | 问题未闭环回 S12 或 SX |
| `S14_PRODUCTION_FREEZE_REVIEW` | 正式使用前冻结审查 | freeze 清单、风险接受、回退演练方案 | 新增功能、大范围改动、直接生产 | pilot 证据、审计资料、freeze 清单 | freeze 审查文档 | S13 审核通过 | freeze 审核通过并停止 | A8 | 风险清单、回退方案、审计、责任边界 | freeze 不通过回 S13 或 SX |
| `S15_PRODUCTION_USE_AUTHORIZATION_REQUIRED` | 正式使用和 50 人使用待授权 | 汇总正式使用审批材料 | 未获 A8 前进入真实使用或 50 人使用 | freeze 证据和正式使用材料 | production 授权文档 | S14 通过 | A8 最高审批通过或拒绝 | A8 | 生产范围、人员、权限、支持、回滚、最终签核 | 未获最高审批保持阻断 |
| `SX_BLOCKED_OR_ROLLBACK` | 阻断或等待授权回滚 | 停止、保全证据、回报实际状态、提出回滚建议 | 擅自 reset/checkout/delete/覆盖、继续执行 | 已读取的授权证据和 Git 状态 | 阻断报告，仅限授权路径 | 任一状态越权、失败或证据不足 | 获得新授权后回到指定安全状态 | 由触发项决定，通常需上一级审批 | 触发条件、已执行动作、未执行动作、风险、建议 | 等待 ChatGPT 总控师裁定 |

## 4. 状态转换规则

| 转换 | 转换触发条件 | 必须人工审批 | 允许目标模式 | 是否 docs-only | 允许代码读取 | 允许代码修改 | 允许 runtime | 允许 endpoint | 允许 Ollama | 允许模型推理 | 允许真实 KG | 允许真实项目资料 | 最小证据要求 | 阻断条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `S0 -> S1` | 治理总纲 docs-only Gate 完成并通过审核 | 是，A1 | 是 | 是 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 001 文档、HEAD/tag/status、禁止项确认 | 001 结论不完整或越权 |
| `S1 -> S2` | 任务分解 Gate 获授权并完成 | 是，A1 | 是 | 是 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 002 文档、Gate 清单、停止确认 | 自动进入后续节点或证据不足 |
| `S2 -> S3` | 权限矩阵与状态机 Gate 获授权 | 是，A1 | 是 | 是 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 003 文档、权限矩阵、状态机、commit/tag/status | 读取越界、修改非目标文件 |
| `S3 -> S4` | 003 审核通过，ChatGPT 总控师授权代码只读盘点 | 是，A2 | 待审核决定 | 否，code-read-only | 是，仅 allowlist | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 代码读取 allowlist、停止条件、回报模板 | 未获 A2 或读取范围不唯一 |
| `S4 -> S5` | 只读盘点完成且确认需要代码修改方案 | 是，A3 前置 | 待审核决定 | 可为 docs-only 方案 | 是，仅盘点证据 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 盘点报告、目标文件候选、风险清单 | 目标文件不清或需 runtime 证据 |
| `S5 -> S6` | 代码修改方案被批准 | 是，A3 | 待审核决定 | 否 | 是，仅授权文件 | 是，仅授权 patch | 否 | 否 | 否 | 否 | 否 | 否 | 批准范围、patch 计划、回滚方案、最小回归 | 未获 A3 或方案混入无关改动 |
| `S6 -> S7` | 代码修改完成，需要静态校验 | 是，A3/A4 | 待审核决定 | 否 | 是，仅授权文件 | 仅已授权变更 | 否 | 否 | 否 | 否 | 否 | 否 | diff、命令 allowlist、无 runtime 确认 | 需要服务、端口、endpoint 或模型验证 |
| `S7 -> S8` | 静态校验通过，需要 runtime preflight 授权 | 是，A4 | 待审核决定 | 是，授权文档阶段 | 否，除审批材料 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 静态校验证据、preflight 候选命令、停止条件 | 静态失败或命令清单不完整 |
| `S8 -> S9` | runtime preflight 命令清单获 A4 审批 | 是，A4 | 待审核决定 | 否，preflight-only | 仅 allowlist | 否 | 仅 preflight，不启动服务 | 否 | 否 | 否 | 否 | 否 | A4 审批、命令 allowlist、无 endpoint 边界 | 命令包含服务启动、HTTP、Ollama 或推理 |
| `S9 -> S10` | preflight 通过，需要 mock / dry-run 授权 | 是，A5 | 待审核决定 | 是，授权文档阶段 | 否，除审批材料 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | preflight 结果、mock/dry-run 方案、输出处置 | preflight 失败或证据不足 |
| `S10 -> S11` | mock / dry-run 获 A5 审批 | 是，A5 | 待审核决定 | 否 | 仅 allowlist | 仅授权范围 | 仅授权 dry-run 依赖 | 仅明确授权时允许 | 仅明确授权时允许 | 仅明确授权时允许 | 否 | 否 | mock 来源、无真实资料证明、输出处置 | mock 来源不明、prompt 未审、输出不可控 |
| `S11 -> S12` | dry-run 通过且输出处置完成 | 是，A7 | 待审核决定 | 是，trial 授权文档阶段 | 否，除审批材料 | 否 | 否 | 否 | 否 | 否 | 否，除 A6 已授权材料 | 否，除 A6 已授权材料 | dry-run 报告、问题清单、回滚证明 | dry-run 失败、真实资料误读 |
| `S12 -> S13` | 单人试用获授权并完成，问题闭环 | 是，A7 | 待审核决定 | 否 | 仅 allowlist | 仅授权修复 | 仅授权范围 | 仅授权范围 | 仅授权范围 | 仅授权范围 | 仅 A6 授权范围 | 仅 A6 授权范围 | 单人试用报告、问题闭环、支持机制 | 问题未闭环或试用范围扩大 |
| `S13 -> S14` | 小范围试运行完成，进入正式使用前冻结审查 | 是，A8 | 待审核决定 | 可为 freeze docs | 仅审查 allowlist | 原则禁止，除冻结修复授权 | 仅审查授权范围 | 仅审查授权范围 | 仅审查授权范围 | 仅审查授权范围 | 仅 A6 授权范围 | 仅 A6 授权范围 | pilot 报告、风险清单、回退方案 | 支持、审计、回滚不闭环 |
| `S14 -> S15` | freeze 审查通过，提交正式使用审批 | 是，A8 | 待审核决定 | 可为审批 docs | 仅审批材料 | 否 | 否，除正式授权后 | 否，除正式授权后 | 否，除正式授权后 | 否，除正式授权后 | 仅 A6/A8 授权范围 | 仅 A6/A8 授权范围 | freeze 签核、生产范围、人员、权限、支持、回滚 | 风险未接受或最高审批缺失 |
| `任意状态 -> SX_BLOCKED_OR_ROLLBACK` | 越权、证据不足、Git 不一致、测试失败、敏感边界触发 | 是，按触发项升级 | 否，除阻断回报 | 仅阻断报告 | 否，除保全已授权证据 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 触发原因、已执行/未执行动作、当前 Git 状态、建议 | 继续执行、补写结论替代证据、擅自回滚 |

## 5. 不可跨越红线

1. 未完成 docs-only Gate，不得进入代码读取。
2. 未完成人工审批，不得进入代码修改。
3. 未完成静态验证，不得进入 runtime preflight。
4. 未完成 runtime preflight，不得访问 endpoint。
5. 未完成 mock / dry-run 授权，不得输入 prompt。
6. 未完成真实数据授权，不得读取真实 KG / 真实项目资料。
7. 未完成 trial 授权，不得进入真实使用。
8. 未完成小范围试运行与冻结审查，不得进入 50 人正式使用。
9. 任一节点证据不足，必须阻断，不得补写结论替代证据。
10. 任一节点完成后必须停止，不得自动进入下一节点。
11. 任一旧节点授权不得自动继承为当前节点授权。
12. 任一 runtime、endpoint、Ollama、模型、KG、真实资料、generation、export、write-back 行为必须独立授权。

## 6. 审批等级体系

| 审批等级 | 授权范围 | 禁止范围 | 生效条件 | 失效条件 | 必须回报字段 |
| --- | --- | --- | --- | --- | --- |
| `A0`：无需新增审批，仅限读取已授权 docs | 读取当前 Gate 明确授权的 pasted text 和 docs | 写入、代码读取、runtime、endpoint、模型、真实资料 | allowlist 明确且目的为归纳/核对 | 需要新增读取范围或发现敏感边界 | 实际读取文件、未读范围、禁止项确认 |
| `A1`：docs-only 新增文档审批 | 新增或修改唯一授权 docs 文件，执行文本级检查、Git commit/tag | 代码读取/修改、服务、endpoint、模型、真实资料 | 目标文件唯一、Git 基线 clean、commit/tag 指定 | 出现非目标文件变更或基线错位 | 分支、HEAD/tag、目标文件、diff 检查、commit/tag/status |
| `A2`：代码只读盘点审批 | 读取明确 allowlist 中代码/配置，用于 inventory | 代码修改、脚本执行、runtime、真实资料 | 文件清单、读取目的、停止条件明确 | 需要读取未列文件或脚本含敏感/运行边界 | 读取文件、未修改确认、发现风险、阻断项 |
| `A3`：代码修改审批 | 修改授权代码和测试文件，运行最小授权回归 | 无关重构、runtime、endpoint、模型、真实资料 | patch 范围、测试命令、回滚方案批准 | 混入无关文件、测试失败无法处置 | diff、测试结果、变更范围、回滚建议、Git 状态 |
| `A4`：runtime preflight 审批 | 执行明确 allowlist 中不访问 endpoint 的 preflight | 启动服务、HTTP、端口探测、Ollama、推理，除非逐项授权 | 命令、参数、超时、输出边界明确 | 命令产生副作用或需要更高权限 | 命令、退出码、输出摘要、无 endpoint/模型确认 |
| `A5`：endpoint / dry-run / prompt 审批 | 访问授权 endpoint、执行受控 dry-run、输入授权 prompt | 真实 KG/真实项目资料，未审输出写回 | endpoint/prompt/mock 来源和输出处置明确 | 返回含敏感数据、输出不可控、prompt 越界 | 请求/命令、输入来源、输出处置、无真实资料确认 |
| `A6`：真实 KG / 真实项目资料审批 | 读取明确授权的真实 KG、项目资料或脱敏样本 | 未列资料、secrets、无保留/删除规则资料 | 资料清单、责任边界、访问方式和用途明确 | 读取范围扩大或授权链不完整 | 资料清单、授权证明、读取范围、保留/删除规则 |
| `A7`：trial / 小范围试运行审批 | 单人试用、小范围试运行和支持机制验证 | 50 人正式使用、未授权生产写回 | dry-run 通过、问题处理、回滚、支持机制明确 | 试用范围扩大、问题未闭环、支持缺失 | 试用范围、人员、问题清单、回滚、支持响应 |
| `A8`：正式使用 / 50 人使用审批 | 正式使用、50 人使用、最高风险接受 | 无最高审批时的真实生产使用或扩大范围 | freeze 通过、风险接受、支持/回滚/审计闭环 | 风险未接受、审计缺失、回滚不可用 | freeze 证据、生产范围、人员、权限、支持、最终签核 |

## 7. 证据链模板

后续所有 Gate 必须使用以下统一回报字段模板：

1. 是否完成当前节点：
2. 是否新建 Codex 对话框：
3. 是否使用目标模式：
4. 开始前分支：
5. 开始前 HEAD / tag：
6. 结束后 HEAD：
7. `git status --short` 是否 clean：
8. 实际新增文件：
9. 实际修改文件：
10. 是否仅在授权范围内变更：
11. 实际读取文件：
12. 是否读取 runtime 脚本正文：
13. 是否执行脚本：
14. 是否启动服务：
15. 是否访问 endpoint：
16. 是否运行 Ollama：
17. 是否模型推理：
18. 是否输入 prompt：
19. 是否读取真实 KG：
20. 是否读取真实项目资料：
21. 是否读取 secrets / tokens / credentials：
22. 是否读取 output / job / export / 日志正文：
23. 是否 generation / export / write-back：
24. commit：
25. tag：
26. 测试或校验证据：
27. 本节点结论：
28. 是否已停止、未进入后续节点：
29. 目标模式用量与耗时：
30. 回滚与阻断机制：

证据链要求：

1. 回报字段必须基于实际执行证据，不得用推断替代。
2. 禁止项必须显式否定。
3. Git 证据必须覆盖开始前和结束后状态。
4. 不得通过读取 output / job / export / 日志正文、真实 KG、真实项目资料或敏感信息来补证。
5. 若任一字段无法确认，必须阻断并说明原因。

## 8. 回滚与阻断机制

| 场景 | 触发条件 | 立即动作 | 回滚或阻断规则 | 回报要求 |
| --- | --- | --- | --- | --- |
| docs-only 阶段回滚 | 分支、HEAD、tag、status、目标文件状态不符 | 停止，不新增或不继续提交 | 不执行 reset/checkout/delete；仅回报实际状态 | 实际分支、HEAD/tag/status、目标文件状态 |
| 代码只读阶段阻断 | 读取范围不唯一或需要未授权文件 | 停止，不读取正文 | 等待 A2 重新授权 allowlist | 需要读取的路径、原因、禁止依据 |
| 代码修改阶段回滚 | patch 范围失控、混入无关文件、最小回归失败 | 停止修改，不扩大范围 | 仅提出回滚建议；执行回滚需新授权 | 变更文件、失败测试、建议回滚点 |
| 静态验证失败回滚 | lint/typecheck/text check/单测失败 | 停止进入 runtime | 回到 S6 修复或进入 SX；不得跳过静态失败 | 命令、耗时、失败用例或最后报错 |
| runtime preflight 前阻断 | 静态验证未完成或 preflight 命令清单不完整 | 停止，不执行 preflight | 等待 A4 审批 | 缺失命令、风险点、禁止项确认 |
| runtime preflight 失败回滚 | preflight 命令失败或出现未授权 endpoint/服务/Ollama 需求 | 停止，不追加探测 | 回到 S8 重新审批或进入 SX | 命令、退出码、失败摘要、未执行项 |
| dry-run 失败回滚 | mock 来源不明、prompt 未审、输出处置失败 | 停止 dry-run | 回到 S10 重新授权；不得使用真实资料补证 | 输入来源、失败点、输出处置状态 |
| trial 失败回滚 | 试用范围扩大、问题未闭环、回滚不可用 | 停止扩展 | 回到 S12 或 S13；不得进入正式使用 | 试用范围、问题清单、回滚建议 |
| 真实数据误读阻断 | 误读真实 KG、真实项目资料、招标文件、图纸、清单、项目样本 | 立即停止，不扩散内容 | 进入 SX，等待 ChatGPT 总控师裁定 | 误读类别、路径类别、已停止确认 |
| secrets / tokens / credentials 误读阻断 | 误读密钥、令牌、凭据或敏感环境变量 | 立即停止，不复述敏感值 | 进入 SX，按安全 Gate 处理 | 敏感类别、未复述确认、停止状态 |
| output / job / export / 日志正文误读阻断 | 误读生成结果、导出结果或运行日志正文 | 立即停止 | 进入 SX，不用该内容补证 | 路径类别、误读原因、未继续读取确认 |
| 证据不足阻断 | 回报字段无法由实际证据支撑 | 停止，不补写结论 | 回到对应审批状态补证或进入 SX | 缺失字段、所需授权、当前状态 |
| tag / commit / clean 状态不一致阻断 | commit、tag、HEAD 或 `git status --short` 与要求不符 | 停止，不擅自回滚 | 等待授权后处理；不得 reset/checkout/delete | 实际 commit/tag/status、差异说明 |

统一原则：

1. Codex 不得擅自执行 destructive git 操作。
2. Codex 不得删除、覆盖、清理未授权文件。
3. Codex 不得通过读取未授权正文补证。
4. 回滚执行必须等待 ChatGPT 总控师另行授权。
5. 证据不足时必须阻断，不得默认放行。

## 9. 后续 Gate 建议

建议下一节点名称为：

`SYSTEM-AUTONOMY-004-GOAL-MODE-CODEBASE-READ-ONLY-INVENTORY-AUTHORIZATION-GATE`

建议定位：

1. `SYSTEM-AUTONOMY-004` 应作为代码只读盘点授权 Gate。
2. 004 的核心目标应是决定是否允许从 `S3_PERMISSION_MATRIX_LOCKED` 转入 `S4_CODE_READ_ONLY_INVENTORY`。
3. 004 应明确代码读取 allowlist、禁止读取范围、停止条件、回报字段和证据链。
4. 004 不应默认授权代码修改。
5. 004 不应默认授权 runtime、服务启动、Web UI、endpoint、curl / HTTP request / localhost / 端口探测、Ollama、模型命令、模型推理、prompt、真实 KG、真实项目资料、generation、export 或 write-back。

本节点对 004 的限制：

1. 本节点不得进入 `SYSTEM-AUTONOMY-004`。
2. 004 是否允许目标模式，必须由 ChatGPT 总控师审核后决定。
3. 004 是否 docs-only 或 code-read-only，必须由 ChatGPT 总控师审核后决定。
4. 004 仍默认禁止 runtime，除非另行明确授权。
5. 004 完成后也必须停止，等待 ChatGPT 总控师审核，不得自动进入后续节点。

## 10. 本节点结论

`SYSTEM-AUTONOMY-003-GOAL-MODE-PERMISSION-MATRIX-AND-STATE-MACHINE-GATE` 的结论如下：

1. 本节点已固化系统自治路线的权限矩阵。
2. 本节点已固化系统自治状态机。
3. 本节点已固化关键状态转换规则。
4. 本节点已明确不可跨越红线。
5. 本节点已定义 A0 到 A8 审批等级体系。
6. 本节点已定义后续 Gate 证据链模板。
7. 本节点已定义回滚与阻断机制。
8. 本节点仅形成 docs-only Gate 文档。
9. 本节点不实施、不运行、不验证 runtime。
10. 本节点不授权进入 `SYSTEM-AUTONOMY-004`。
11. 本节点不授权进入 `LOCAL-LAUNCHER-026`。
12. 本节点完成后必须停止，等待 ChatGPT 总控师审核。
