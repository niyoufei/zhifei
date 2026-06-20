# SYSTEM-AUTONOMY-001 Goal Mode Governance And Roadmap Gate

## 1. SYSTEM-AUTONOMY-001 节点结论

`SYSTEM-AUTONOMY-001-GOAL-MODE-GOVERNANCE-AND-ROADMAP-GATE` 是系统自治建设的目标模式治理总纲 Gate。

本节点结论如下：

1. 本节点是系统自治建设的目标模式治理总纲 Gate。
2. 本节点不是 runtime ready。
3. 本节点不是 release ready。
4. 本节点不是 trial ready。
5. 本节点不是真实使用 ready。
6. 本节点不是 50 人正式使用 ready。
7. 本节点不授权服务启动。
8. 本节点不授权 endpoint。
9. 本节点不授权 Ollama。
10. 本节点不授权模型推理。
11. 本节点不授权真实 KG / 真实项目资料接入。
12. 本节点不授权 generation/export/write-back。
13. 本节点不授权系统自主执行真实任务。

本节点仅建立 ZDoc / 本地 AI 应用 / LOCAL-LAUNCHER 后续系统自治建设的治理框架、路线图、权限边界、人工审批点、失败回滚机制和证据链要求。

## 2. 与 LOCAL-LAUNCHER-024 / 025 的关系

1. `LOCAL-LAUNCHER-024` 已完成静态 UI 封版闭环。
2. `LOCAL-LAUNCHER-025-RETRY-1` 已完成 runtime 独立边界 Gate。
3. `SYSTEM-AUTONOMY-001` 不改变 024 / 025 结论。
4. `SYSTEM-AUTONOMY-001` 不继承任何 runtime 执行授权。
5. 本节点只建立后续系统自治路线图。
6. 自治路线必须继续分 Gate 推进。
7. 024 的静态 UI 封版成果仍不得解释为 runtime ready、release ready、trial ready、真实使用 ready 或 50 人正式使用 ready。
8. 025 的 runtime 边界结论仍保持有效：服务启动、Web UI 启动、endpoint、Ollama、模型推理、真实资料接入和 generation/export/write-back 均未授权。

## 3. 系统自治建设总目标

| 目标 | 建设目的 | 可自治边界 | 不可自治边界 | 前置 Gate | 需要人工确认的触发条件 |
| --- | --- | --- | --- | --- | --- |
| 总控治理自治 | 将节点目标、边界、停止条件和回报格式结构化，降低授权混线风险 | 归纳已授权文本、生成 docs-only 治理草案、提示阻断项 | 替代 ChatGPT 总控师作出运行授权、自动进入下一节点 | `SYSTEM-AUTONOMY-001` 审核通过 | 需要改变授权边界、扩大读取范围、进入后续 Gate |
| 任务拆解自治 | 将复杂目标拆成可审核 Gate，避免一次性大范围执行 | 生成 docs-only 任务树、依赖关系和停止点 | 自行执行拆出的后续任务或默认承接旧授权 | `SYSTEM-AUTONOMY-002` | 拆解中出现 runtime、endpoint、Ollama、真实资料或写回需求 |
| 文档生成治理自治 | 让治理文档具备固定章节、证据链和禁止事项矩阵 | 按授权新增或修改指定 docs 文件 | 修改未授权 docs、生成运行代码、写入真实产物 | docs-only 文档 Gate | 目标文件不唯一、需读取未授权资料、需修改既有结论 |
| runtime 状态识别自治 | 在不触发运行行为前提下识别是否需要 runtime Gate | 仅生成状态核查建议和问题清单 | 启动服务、端口探测、PID 操作、localhost 访问 | runtime readiness questionnaire Gate | 需要真实状态、端口、PID、服务进程或 endpoint 证据 |
| 风险识别自治 | 在执行前识别越界、敏感信息、授权继承和 Git 错位风险 | 生成风险矩阵、阻断动作和回报要求 | 自动修复 runtime 风险、读取敏感文件、删除或回滚未授权提交 | governance matrix Gate | 发现基线错位、禁止事项触发、敏感路径或未审核提交 |
| Gate 生成自治 | 标准化后续 Gate 的允许范围、禁止范围和验收标准 | 生成后续 Gate 建议文本 | 自动创建、执行或跳转后续 Gate | goal mode runbook Gate | 任何 Gate 涉及运行、模型、真实资料、写回或多人使用 |
| 回报校核自治 | 确保完成回报覆盖实际读取、修改、验证和禁止事项 | 生成 checklist、比对 git 状态、列出明确否定项 | 隐瞒越界读取、用推断替代实际结果 | docs-only reporting Gate | 回报项无法由已授权证据支撑 |
| 证据链归档自治 | 固化 HEAD、tag、状态、文件清单和结论，便于审计 | 在授权 docs 中记录证据链字段 | 读取 output/job/export/日志正文或真实业务结果 | evidence policy Gate | 需要运行日志、生成结果、真实资料证据 |
| 人工审批触发自治 | 在遇到高风险动作前自动提示必须等待总控师 | 提示审批点、生成审批清单、停止执行 | 自行批准运行、模型、资料接入、写回、试用 | approval gate policy | 任何不可自治或半自治事项被提出 |
| 失败停止与回滚建议自治 | 将失败时的停止、保全、回报和回滚建议制度化 | 给出停止和回滚建议，不执行破坏性动作 | 未授权 reset、checkout、删除、覆盖、回滚提交 | rollback policy Gate | 工作区不 clean、HEAD/tag 不符、提交混入、禁止事项触发 |

## 4. 自治能力分级

| 等级 | 能力定义 | 当前是否授权 | 后续授权前置条件 | 禁止越级行为 | 失败停止条件 | 是否需要 ChatGPT 总控师审批 |
| --- | --- | --- | --- | --- | --- | --- |
| A0：人工总控，仅由 ChatGPT 裁定 | 所有路线、授权、节点进入和停止由 ChatGPT 总控师裁定 | 是 | 当前即为默认总控层 | Codex 自行批准后续节点 | 指令冲突、边界不明、需总控裁定 | 是 |
| A1：Codex 只读归纳 | 只读授权文档并归纳结论 | 本节点范围内授权 | 明确只读文件清单 | 读取未授权资料、敏感文件、真实资料 | 文件不在 allowlist、内容涉及敏感边界 | 是 |
| A2：Codex docs-only 计划生成 | 生成治理计划、路线图和 checklist | 本节点目标文件内授权 | 指定唯一 docs 输出 | 修改代码、运行服务、扩大文档范围 | 目标文件不唯一或需修改既有文件 | 是 |
| A3：Codex docs-only Gate 自动拆解 | 将路线拆成后续 Gate 建议 | 仅建议，不执行 | `SYSTEM-AUTONOMY-002` 或独立 Gate 授权 | 自动进入下一 Gate | 拆解结果包含未授权执行项 | 是 |
| A4：Codex 受控状态检查 | 执行明确授权的 git 或静态状态命令 | 仅本节点授权的 git 命令 | 状态检查 Gate 明确命令清单 | 端口探测、服务探测、HTTP request | 命令超出授权清单 | 是 |
| A5：Codex 受控配置审查 | 只读审查明确配置清单的非敏感字段 | 否 | runtime 配置清点 Gate | 读取 runtime 脚本正文、secrets、tokens、credentials | 配置含敏感字段或清单不明确 | 是 |
| A6：Codex 受控服务前预检 | 生成或执行明确授权的服务前 checklist | 否 | 服务启动前预检 Gate | 启动服务、端口探测、PID 操作 | 需要真实服务状态但未授权 | 是 |
| A7：Codex 受控服务启动建议 | 给出受控启动建议、停止条件和回滚方案 | 否 | 受控服务启动 Gate | 自行启动、停止、重启服务 | 缺少命令、端口、日志、退出条件 | 是 |
| A8：Codex 受控 mock 验证建议 | 设计 mock 验证方案和验收项 | 否 | mock 数据闭环 Gate | 执行真实闭环、导出或写回 | mock 来源不清或混入真实资料 | 是 |
| A9：Codex 脱敏样本验证建议 | 设计脱敏样本验证方案 | 否 | 脱敏样本 Gate | 读取未证明脱敏的样本 | 脱敏证明不足、样本范围不明 | 是 |
| A10：真实资料接入建议 | 仅提出真实 KG / 项目资料接入审批建议 | 否 | 真实资料接入 Gate | 读取真实 KG、招标文件、图纸、清单、项目样本 | 任何真实资料读取需求出现 | 是 |
| A11：generation/export/write-back 建议 | 仅提出生成、导出、写回的治理方案 | 否 | generation/export/write-back Gate | 触发生成、导出、写回、覆盖结果 | 输出路径、写回对象、回滚方案不清 | 是 |
| A12：trial / 多人试用 / 正式使用建议 | 仅提出试用和正式使用 readiness 评估框架 | 否 | trial Gate；50-user readiness Gate | 进入 trial、真实使用、多人使用、50 人正式使用 | 支持、责任、回滚、审计不闭环 | 是 |

## 5. 可自治事项清单

| 事项 | 允许条件 | 禁止条件 |
| --- | --- | --- |
| docs-only 摘要归纳 | 文件路径在授权清单内，目的为治理归纳 | 读取真实资料、runtime 脚本正文、日志正文或敏感信息 |
| Gate 文档结构生成 | 目标 docs 文件唯一，章节来自授权要求 | 修改未授权文件或创建运行代码 |
| 风险清单生成 | 基于已授权文档和节点要求描述风险 | 通过探测、访问 endpoint 或读取运行产物补证 |
| 禁止事项矩阵生成 | 明确列出禁止行为和阻断动作 | 将禁止事项改写成默认可执行事项 |
| 后续路线图建议 | 仅提出 Gate 建议，不执行下一阶段 | 自动进入 `SYSTEM-AUTONOMY-002`、`LOCAL-LAUNCHER-026` 或任何后续节点 |
| 回报格式生成 | 覆盖 HEAD、tag、文件、禁止事项和最终结论 | 省略实际读取文件或越界风险 |
| commit/tag 建议 | 仅在授权节点内使用指定 message 和 tag | 自行修改 commit message、创建额外 tag、推送远端 |
| 只读状态核查建议 | 仅建议或执行明确授权的只读命令 | curl、HTTP request、localhost、端口、PID、Ollama 或服务状态探测 |
| 失败停止建议 | 发现不一致时建议停止并回报 | 自动修复、删除、覆盖、reset 或 checkout 未授权内容 |
| 人工审批点提示 | 对半自治和不可自治事项触发审批提示 | Codex 自行批准执行高风险动作 |

## 6. 不可自治事项清单

| 事项 | 不能自治的原因 |
| --- | --- |
| 服务启动 | 会改变 runtime 状态，可能产生进程、端口、日志和副作用，必须独立授权。 |
| endpoint 访问 | 会触发 HTTP 行为或业务调用，可能改变服务状态或读取运行结果。 |
| Ollama 调用 | 会触发模型环境、模型进程或 inventory 行为，当前未授权。 |
| 模型推理 | 会产生模型输出，可能涉及 prompt、真实资料和生成结果。 |
| prompt 输入 | 输入内容、模型对象和输出处置必须由总控师明确授权。 |
| 真实 KG 读取 | 可能包含真实项目知识、敏感结构或可溯源业务资料。 |
| 真实项目资料读取 | 招标文件、图纸、清单、项目样本等均属于真实资料边界。 |
| generation | 会产生业务结果或生成产物，需要输入、输出和审计授权。 |
| export | 会写出或转移结果，必须明确目录、格式、责任和回滚方案。 |
| write-back | 会覆盖或写入系统/资料/结果，风险高且必须可回滚。 |
| trial | 涉及真实用户或真实流程，必须经过独立 readiness Gate。 |
| 真实使用 | 涉及生产性使用和责任边界，不能由 Codex 自行决定。 |
| 多人使用 | 会扩大影响面，需要支持、回滚、权限和审计闭环。 |
| 50 人正式使用 | 属于正式使用 readiness，必须经过 50-user Gate。 |
| 删除、覆盖、回滚未授权提交 | 可能破坏用户或历史工作，必须明确授权。 |
| 修改 runtime 脚本 | 会改变运行行为和安全边界，当前禁止。 |
| 创建运行代码 | 会推进 runtime 能力建设，超出 docs-only Gate。 |
| 改动安全边界 | 会改变后续授权基础，必须由总控师裁定。 |
| 读取 secrets/tokens/credentials | 涉及敏感信息泄露风险，当前禁止读取。 |
| 读取 output/job/export/日志正文 | 可能包含生成结果、真实资料、敏感日志或运行证据正文。 |

## 7. 半自治事项清单

| 事项 | Codex 可建议 | Codex 不可自行执行 | 另行授权要求 | 需要用户侧明确环境状态时的回报要求 |
| --- | --- | --- | --- | --- |
| runtime 配置清点 | 建议清点字段、路径白名单和敏感字段排除规则 | 读取未授权 runtime 配置或脚本正文 | `LOCAL-LAUNCHER-026` 明确授权 | 回报配置清单、敏感字段处理方式和未读范围 |
| 服务启动前预检 | 建议 checklist、停止条件和回滚条件 | 端口探测、PID 操作、服务状态探测 | `LOCAL-LAUNCHER-027` 明确授权 | 回报预检项、缺失证据和阻断点 |
| 端口状态核查 | 建议需核查端口和安全边界 | 执行端口探测或 localhost 访问 | endpoint / preflight Gate 明确授权 | 回报端口清单、方法、超时和无写入保证 |
| PID 陈旧记录识别 | 建议识别规则和保全方案 | 读取、清理、删除 `.runtime/docgen/` PID 文件 | PID 处理 Gate 明确授权 | 回报 PID 路径、只读/清理授权和风险 |
| endpoint 健康检查 | 建议 endpoint 清单和只读方法 | curl、HTTP request、访问 endpoint | `LOCAL-LAUNCHER-029` 明确授权 | 回报 endpoint、方法、返回字段和无业务调用保证 |
| Ollama inventory | 建议 inventory 字段和回报格式 | 执行 Ollama 命令 | `LOCAL-LAUNCHER-030` 明确授权 | 回报命令、字段范围、是否触发模型进程 |
| mock 数据验证 | 建议 mock 数据结构和验收标准 | 执行 runtime 闭环或生成导出 | `LOCAL-LAUNCHER-031` 明确授权 | 回报 mock 来源、无真实资料证明和输出处置 |
| 脱敏样本验证 | 建议样本验收和脱敏证明要求 | 读取样本或运行验证 | `LOCAL-LAUNCHER-032` 明确授权 | 回报样本范围、脱敏证据、保留/删除规则 |
| 本地 Web UI 可用性检查 | 建议检查路径和截图/DOM 证据要求 | 启动 UI、打开 HTML、访问 localhost | Web UI 检查 Gate 明确授权 | 回报启动方式、端口、窗口、停止条件 |
| 桌面 App 启动器检查 | 建议启动器检查项和回滚方案 | 执行创建脚本或启动应用 | launcher 检查 Gate 明确授权 | 回报脚本、生成文件、是否改变系统状态 |

## 8. 风险与阻断机制

| 风险 | 风险描述 | 触发条件 | 阻断动作 | 回报要求 | 是否允许自动修复 |
| --- | --- | --- | --- | --- | --- |
| 授权继承风险 | 将旧节点授权误认为当前节点授权 | 引用 024/025 后出现 runtime 执行需求 | 停止，不继承授权 | 回报旧节点仅作事实参考 | 否 |
| 上下文污染风险 | 旧对话、旧目标或旧总结影响当前边界 | 当前任务与旧节点混线 | 停止并按当前附件边界重述 | 回报当前节点名称和禁止后续节点 | 否 |
| runtime 误启动风险 | 执行脚本或命令导致服务启动 | 需要运行启动脚本、服务命令或后台进程 | 停止，不执行命令 | 回报命令名称和未执行原因 | 否 |
| endpoint 误访问风险 | curl、HTTP、localhost 或端口探测触发运行访问 | 需要访问 `127.0.0.1`、localhost、endpoint 或端口 | 停止，不访问 | 回报目标地址和禁止依据 | 否 |
| 模型误调用风险 | Ollama 或模型推理被触发 | 需要执行模型命令、输入 prompt、读取输出 | 停止，不运行 | 回报模型、命令或 prompt 需求 | 否 |
| 真实资料误读取风险 | 读取真实 KG、招标文件、图纸、清单、项目样本 | 路径或内容属于真实资料 | 停止，不读取 | 回报路径类别和阻断原因 | 否 |
| 日志正文误读取风险 | 查看 output/job/export/日志正文造成敏感暴露 | 需要打开运行日志、生成结果或导出文件 | 停止，不读取 | 回报路径类别和未读事实 | 否 |
| secrets/tokens/credentials 泄露风险 | 读取密钥、令牌、凭据或敏感环境变量 | 需要查看 `.env`、token、credential 或 env 值 | 停止，不读取 | 回报敏感类别和阻断原因 | 否 |
| generation/export/write-back 误触发风险 | 生成、导出或写回真实产物 | 需要写入结果、覆盖资料或导出文件 | 停止，不执行 | 回报动作名称和目标对象 | 否 |
| 多人试用误启动风险 | 未经 readiness 审核进入 trial 或多人使用 | 出现试用、真实使用、多人、50 人使用需求 | 停止，不推进 | 回报使用范围和缺失 Gate | 否 |
| Git 基线错位风险 | 分支、HEAD、tag 或工作区状态不符合节点要求 | 开始前或结束后 git 状态不符 | 停止，不继续提交 | 回报实际分支、HEAD、tag、status | 否 |
| 未审核提交混入风险 | 本节点提交混入其他文件或历史修改 | `git status --short` 出现非目标文件 | 停止，不提交或不继续 | 回报混入文件和目标文件差异 | 否 |

## 9. 人工审批闸门

以下事项必须由 ChatGPT 总控师另行授权：

1. 进入 runtime 配置清点。
2. 进入服务启动前预检。
3. 启动服务。
4. 访问 endpoint。
5. 运行 Ollama。
6. 模型推理。
7. 输入 prompt。
8. 接入 mock 数据。
9. 接入脱敏样本。
10. 接入真实 KG。
11. 接入真实项目资料。
12. generation。
13. export。
14. write-back。
15. trial。
16. 多人试用。
17. 50 人正式使用。

统一审批结论：任一审批闸门触发时，Codex 只能停止并回报，不得自动执行、自动修复、自动进入下一阶段。

## 10. 后续 Gate 路线图

| Gate | Gate 定位 | 是否 docs-only | 是否只读 | 是否允许 runtime | 是否需要新建 Codex 对话框 | 完成后是否允许自动进入下一阶段 |
| --- | --- | --- | --- | --- | --- | --- |
| `SYSTEM-AUTONOMY-002-GOAL-MODE-TASK-DECOMPOSITION-GATE` | 系统自治任务拆解 Gate | 是 | 是 | 否 | 是 | 否 |
| `SYSTEM-AUTONOMY-003-GOVERNANCE-MATRIX-AND-POLICY-GATE` | 治理矩阵和策略 Gate | 是 | 是 | 否 | 是 | 否 |
| `SYSTEM-AUTONOMY-004-RUNTIME-READINESS-QUESTIONNAIRE-GATE` | runtime readiness 问卷 Gate | 是 | 是 | 否 | 是 | 否 |
| `SYSTEM-AUTONOMY-005-CODEX-GOAL-MODE-RUNBOOK-GATE` | Codex 目标模式 runbook Gate | 是 | 是 | 否 | 是 | 否 |
| `LOCAL-LAUNCHER-026-RUNTIME-CONFIG-READONLY-INVENTORY-GATE` | runtime 配置只读清点 Gate | 否，需另行定义 | 是 | 否 | 是 | 否 |
| `LOCAL-LAUNCHER-027-SERVICE-START-PREFLIGHT-GATE` | 服务启动前预检 Gate | 否，需另行定义 | 仅限授权项 | 否 | 是 | 否 |
| `LOCAL-LAUNCHER-028-CONTROLLED-SERVICE-START-GATE` | 受控服务启动 Gate | 否 | 否 | 仅在明确授权后允许 | 是 | 否 |
| `LOCAL-LAUNCHER-029-ENDPOINT-HEALTHCHECK-GATE` | endpoint 健康检查 Gate | 否 | 仅限授权 endpoint | 仅在明确授权后允许 | 是 | 否 |
| `LOCAL-LAUNCHER-030-OLLAMA-INVENTORY-GATE` | Ollama inventory Gate | 否 | 仅限授权命令 | 否 | 是 | 否 |
| `LOCAL-LAUNCHER-031-MOCK-DATA-CLOSED-LOOP-GATE` | mock 数据闭环 Gate | 否 | 否 | 仅在明确授权后允许 | 是 | 否 |
| `LOCAL-LAUNCHER-032-SANITIZED-SAMPLE-GATE` | 脱敏样本验证 Gate | 否 | 仅限授权样本 | 仅在明确授权后允许 | 是 | 否 |
| `LOCAL-LAUNCHER-033-REAL-DATA-AUTHORIZATION-GATE` | 真实资料授权 Gate | 否 | 仅限授权资料 | 仅在明确授权后允许 | 是 | 否 |
| `LOCAL-LAUNCHER-034-GENERATION-EXPORT-WRITEBACK-GATE` | generation/export/write-back Gate | 否 | 否 | 仅在明确授权后允许 | 是 | 否 |
| `LOCAL-LAUNCHER-035-TRIAL-GATE` | trial Gate | 否 | 否 | 仅在明确授权后允许 | 是 | 否 |
| `LOCAL-LAUNCHER-036-50-USER-READINESS-GATE` | 50 人正式使用 readiness Gate | 否 | 否 | 仅在明确授权后允许 | 是 | 否 |

统一要求：任何 Gate 完成后均不得自动进入下一阶段，必须回报 ChatGPT 总控师审核。

## 11. 回报模板

后续系统自治路线标准回报模板如下：

1. 是否完成节点：
2. 是否新建 Codex 对话框：
3. 开始前 HEAD / tag：
4. 结束后 HEAD：
5. git status 是否 clean：
6. 新增文件：
7. 修改文件：
8. 读取文件：
9. 是否触发禁止事项：
10. 是否执行 runtime：
11. 是否访问 endpoint：
12. 是否运行 Ollama：
13. 是否模型推理：
14. 是否读取真实资料：
15. 是否读取敏感信息：
16. commit：
17. tag：
18. 节点结论：
19. 是否停止、未进入下一阶段：

## 12. 失败停止与回滚机制

1. 开始前分支、HEAD、tag 或工作区状态不符合节点要求时，必须立即停止，不得读取后续项目文件，不得新增目标文件。
2. 执行中出现未授权读取需求时，必须停止并回报所需文件、原因和禁止依据。
3. 执行中出现 runtime、endpoint、Ollama、模型、真实资料、生成、导出、写回或试用需求时，必须停止并回报，不得执行。
4. 提交前如 `git status --short` 显示除目标 docs 文件外的变更，必须停止，不得提交。
5. 提交后如 tag 创建失败或状态不 clean，必须回报实际状态，不得擅自 reset、checkout、删除或覆盖。
6. 任何回滚建议只能以建议形式写入回报，实际回滚必须等待 ChatGPT 总控师另行授权。

## 13. 日志证据链要求

后续 Gate 的证据链必须至少记录：

1. 节点名称。
2. 是否新建 Codex 对话框。
3. 是否使用目标模式。
4. 开始前分支、HEAD、tag。
5. 结束后 HEAD、tag。
6. 开始前和结束后 `git status --short`。
7. 实际读取文件。
8. 实际新增、修改、删除文件。
9. 是否触发禁止事项。
10. 是否执行 runtime、endpoint、Ollama、模型推理、真实资料读取、generation/export/write-back。
11. commit 和 tag。
12. 最终结论和停止状态。

证据链不得通过读取 output/job/export/日志正文、真实 KG、真实项目资料、secrets/tokens/credentials 或敏感环境变量来补充。

## 14. 本节点最终结论

`SYSTEM-AUTONOMY-001 COMPLETED / GOAL MODE GOVERNANCE ONLY / DOCS ONLY / NO RUNTIME EXECUTION AUTHORIZED / STOPPED`

本节点不授权进入 `SYSTEM-AUTONOMY-002`、`LOCAL-LAUNCHER-026` 或任何后续节点。
