# SYSTEM-AUTONOMY-002 Goal Mode Task Decomposition Gate

## 1. 节点定位

`SYSTEM-AUTONOMY-002-GOAL-MODE-TASK-DECOMPOSITION-GATE` 是 ZDoc / 本地 AI 应用 / LOCAL-LAUNCHER 系统自治路线的任务分解 Gate。

本节点承接 `SYSTEM-AUTONOMY-001-GOAL-MODE-GOVERNANCE-AND-ROADMAP-GATE` 已形成的治理框架，进一步把后续系统自治建设拆解为可执行、可审计、可分阶段授权、可被 ChatGPT 总控师逐项审核的 Gate。

本节点结论边界如下：

1. 本节点只做任务拆解与 Gate 规划。
2. 本节点不实施任何后续能力。
3. 本节点不运行 runtime。
4. 本节点不验证 runtime。
5. 本节点不启动服务。
6. 本节点不访问 endpoint。
7. 本节点不运行 Ollama。
8. 本节点不进行模型推理。
9. 本节点不读取真实 KG / 真实项目资料。
10. 本节点不执行 generation/export/write-back。
11. 本节点不替代后续实现 Gate。
12. 本节点不授权自动进入 `SYSTEM-AUTONOMY-003`、`LOCAL-LAUNCHER-026` 或任何后续节点。

## 2. 系统自治目标树

### 2.1 一级目标

系统自治建设的一级目标是：在不越过 ChatGPT 总控师人工授权边界的前提下，让 ZDoc / 本地 AI 应用 / LOCAL-LAUNCHER 具备可规划、可拆解、可审计、可回滚、可逐步授权的受控自治能力。

该目标不是让系统自行进入真实使用，而是让后续每一类能力都有明确 Gate、权限矩阵、证据链、停止点和人工审批条件。

### 2.2 二级能力域

| 二级能力域 | 能力定位 | 默认授权状态 | 必须保留的人工控制点 |
| --- | --- | --- | --- |
| G1：治理与权限边界 | 固化节点授权、禁止事项、停止条件和回报字段 | docs-only 规划可授权 | 改变权限边界、进入实现、进入运行 |
| G2：任务编排与状态机 | 拆解任务节点、定义状态迁移和不可跨越路径 | docs-only 设计可授权 | 状态机落地、自动执行、跨节点推进 |
| G3：本地运行控制边界 | 定义服务、endpoint、Ollama、模型、KG 的控制边界 | 仅规划可授权 | 任何 runtime 预检、启动、访问、调用 |
| G4：人工审批与回滚 | 定义审批点、失败停止和回退策略 | docs-only 规划可授权 | 执行回滚、删除、覆盖、reset、checkout |
| G5：证据链与审计 | 规定 HEAD、tag、status、读取范围、禁止项确认 | docs-only 规划可授权 | 读取日志正文、output/job/export、真实结果 |
| G6：mock / dry-run | 设计受控 mock / dry-run 方案 | 仅设计可授权 | 执行 mock-run、生成结果、写出产物 |
| G7：runtime preflight | 规划后续 runtime 前置检查 | 仅规划可授权 | 读取脚本、端口探测、服务状态探测 |
| G8：小范围试运行 | 规划个人试用、多人试用和正式使用前门槛 | 仅规划可授权 | trial、真实使用、50 人正式使用 |

### 2.3 三级任务包

| 任务包 | 所属能力域 | 边界 | 输入 | 输出 | 风险等级 | 审批等级 |
| --- | --- | --- | --- | --- | --- | --- |
| TP-001 节点授权模板固化 | G1 | 只定义 docs-only 节点模板，不执行节点 | 001/002 治理结论、当前节点要求 | 标准授权模板和禁止项模板 | 中 | ChatGPT 总控师审批 |
| TP-002 权限维度枚举 | G1 | 只枚举权限维度，不扩大权限 | 已授权治理文档 | 权限矩阵字段集 | 中 | ChatGPT 总控师审批 |
| TP-003 状态机草案 | G2 | 只设计状态，不实现自动状态机 | 任务树、Gate 清单 | 状态、迁移、阻断规则 | 中 | ChatGPT 总控师审批 |
| TP-004 Gate 依赖编排 | G2 | 只标注串行/并行关系，不自动执行 | 后续 Gate 候选清单 | 依赖图谱和不可跨越节点 | 中 | ChatGPT 总控师审批 |
| TP-005 runtime 禁止边界 | G3 | 只定义禁止范围，不触发 runtime | 001 边界结论 | 服务、endpoint、Ollama、模型、KG 禁止边界 | 高 | ChatGPT 总控师强审批 |
| TP-006 runtime preflight 规划 | G3 | 只规划未来预检，不读取脚本、不探测端口 | runtime 边界原则 | preflight Gate 草案 | 高 | ChatGPT 总控师强审批 |
| TP-007 审批点清单 | G4 | 只列审批条件，不替代审批 | 任务阶段和权限矩阵 | 人工审批触发表 | 高 | ChatGPT 总控师强审批 |
| TP-008 失败停止与回滚策略 | G4 | 只写策略，不执行回滚 | Git 证据要求、禁止项 | 分阶段回滚机制 | 高 | ChatGPT 总控师强审批 |
| TP-009 证据链字段标准 | G5 | 只定义回报字段，不读取运行证据 | 001 回报模板、002 回报要求 | 后续 Gate 证据链模板 | 中 | ChatGPT 总控师审批 |
| TP-010 禁止项确认标准 | G5 | 只要求显式否定，不补证未授权内容 | 禁止范围清单 | 禁止项确认矩阵 | 中 | ChatGPT 总控师审批 |
| TP-011 mock / dry-run 方案 | G6 | 只设计 mock，不执行 mock | 脱敏/模拟原则 | mock-run Gate 设计 | 高 | ChatGPT 总控师强审批 |
| TP-012 runtime 预检 Gate 设计 | G7 | 只定义未来 Gate，不做预检 | runtime preflight 条件 | runtime preflight 节点建议 | 高 | ChatGPT 总控师强审批 |
| TP-013 小范围试运行 Gate 设计 | G8 | 只定义 trial 门槛，不进入 trial | 使用范围分级 | 个人/多人/正式使用 Gate | 高 | ChatGPT 总控师强审批 |
| TP-014 正式使用冻结 Gate 设计 | G8 | 只定义冻结和回退条件 | trial 之后的证据要求 | 50 人正式使用前冻结 Gate | 极高 | ChatGPT 总控师最高审批 |

## 3. 分阶段任务拆解

| 阶段 | 阶段名称 | 阶段目标 | 允许内容 | 禁止内容 | 输出物 | 进入下一阶段条件 |
| --- | --- | --- | --- | --- | --- | --- |
| Phase A | 治理与权限边界固化 | 固化节点授权模板、禁止项和停止条件 | docs-only 权限模板、禁止项矩阵 | runtime、endpoint、Ollama、真实资料 | 权限边界 Gate | ChatGPT 总控师审核通过 |
| Phase B | 任务编排与状态机设计 | 定义任务状态、迁移、阻断和不可跨越关系 | docs-only 状态机设计 | 自动执行状态机、跨节点推进 | 状态机 Gate | 状态迁移规则审核通过 |
| Phase C | 本地应用运行控制边界设计 | 定义服务、端口、endpoint、Ollama、KG 的运行边界 | docs-only 控制边界 | 启动服务、端口探测、HTTP request | runtime 控制边界 Gate | 明确后续 preflight 权限 |
| Phase D | 人工审批与回滚机制设计 | 明确规划、实现、运行、试用、正式使用的审批点 | docs-only 审批和回滚策略 | 执行回滚、删除、覆盖、reset | 审批回滚 Gate | 审批点完整且可审计 |
| Phase E | 证据链、审计日志与可追溯机制设计 | 规定后续 Gate 必交证据 | docs-only 证据链模板 | 读取日志正文、output/job/export | 证据链 Gate | 证据字段审核通过 |
| Phase F | 受控 dry-run / mock-run 设计 | 设计 mock 数据、dry-run 和无真实资料验证边界 | docs-only 方案设计 | 执行 mock-run、生成、导出、写回 | mock-run 设计 Gate | mock 来源和输出处置审核通过 |
| Phase G | 后续 runtime 预检 Gate | 设计 runtime 前置检查授权方式 | docs-only preflight 计划 | 读取脚本正文、启动服务、探测端口 | runtime preflight Gate | 明确命令清单和停止条件 |
| Phase H | 后续小范围试运行 Gate | 设计个人试用和多人试用边界 | docs-only trial 规划 | 真实使用、多人使用、业务写回 | trial readiness Gate | 支持、回滚、审计闭环 |
| Phase I | 正式使用前安全冻结 Gate | 设计 50 人正式使用前冻结、回退和最终审批 | docs-only release freeze 规划 | 直接进入正式使用 | formal-use freeze Gate | 最高级人工审批通过 |

阶段推进规则：

1. Phase A 到 Phase F 均应优先保持 docs-only。
2. Phase G 之前不得出现 runtime preflight 执行。
3. Phase H 之前不得出现 trial。
4. Phase I 之前不得出现正式使用或 50 人正式使用。
5. 任一阶段完成后均必须停止，等待 ChatGPT 总控师审核。

## 4. Gate 拆分建议

| 建议节点编号 | 节点名称 | 目标 | docs-only | 允许目标模式 | 禁止 runtime | 允许读取代码 | 允许修改代码 | 允许运行服务 | 允许 endpoint | 允许 Ollama | 允许真实 KG | 允许真实项目资料 | 需要人工审批 | 完成证据要求 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SYSTEM-AUTONOMY-003-GOAL-MODE-PERMISSION-MATRIX-AND-STATE-MACHINE-GATE` | 权限矩阵与状态机 Gate | 固化权限维度、状态、迁移、阻断规则 | 是 | 是 | 是 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 是 | 新增/修改授权 docs、HEAD/tag/status、读取范围、禁止项确认 |
| `SYSTEM-AUTONOMY-004-GOAL-MODE-APPROVAL-AND-ROLLBACK-POLICY-GATE` | 审批与回滚策略 Gate | 固化人工审批点和回滚策略 | 是 | 是 | 是 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 是 | 审批条件表、回滚表、Git 证据、停止确认 |
| `SYSTEM-AUTONOMY-005-GOAL-MODE-EVIDENCE-CHAIN-AND-AUDIT-GATE` | 证据链与审计 Gate | 固化后续节点证据字段和审计口径 | 是 | 是 | 是 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 是 | 证据字段模板、禁止读取项确认、停止确认 |
| `SYSTEM-AUTONOMY-006-GOAL-MODE-MOCK-RUN-DESIGN-GATE` | mock / dry-run 设计 Gate | 设计 mock-run 和 dry-run 的非真实资料边界 | 是 | 是 | 是 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 是 | mock 输入规则、输出处置规则、不得执行确认 |
| `LOCAL-LAUNCHER-026-RUNTIME-CONTROL-BOUNDARY-DOCS-GATE` | 本地运行控制边界 docs Gate | 只读规划 runtime 控制边界，不执行预检 | 是 | 是 | 是 | 否，除非另行授权 | 否 | 否 | 否 | 否 | 否 | 否 | 是 | runtime 权限边界文档、未读脚本确认、禁止项确认 |
| `LOCAL-LAUNCHER-027-RUNTIME-PREFLIGHT-AUTHORIZATION-GATE` | runtime 预检授权 Gate | 定义未来可执行预检的命令清单和停止条件 | 否，需另行授权 | 是 | 是，除明确预检外 | 仅限授权清单 | 否 | 否 | 否 | 否 | 否 | 否 | 是 | 命令 allowlist、风险清单、未启动服务确认 |
| `LOCAL-LAUNCHER-028-CONTROLLED-SERVICE-START-GATE` | 受控服务启动 Gate | 在独立授权下启动服务并记录停止条件 | 否 | 是 | 否，仅限明确授权动作 | 仅限授权清单 | 否 | 是，仅限授权命令 | 否，除另行授权 | 否 | 否 | 否 | 是 | 启动命令、PID/端口证据、停止/回滚证据 |
| `LOCAL-LAUNCHER-029-ENDPOINT-HEALTHCHECK-GATE` | endpoint 健康检查 Gate | 在独立授权下执行只读 endpoint 健康检查 | 否 | 是 | 否，仅限明确授权动作 | 仅限授权清单 | 否 | 否，除前置服务已授权 | 是，仅限授权 endpoint | 否 | 否 | 否 | 是 | endpoint 清单、请求方法、返回摘要、无业务调用确认 |
| `LOCAL-LAUNCHER-030-OLLAMA-INVENTORY-GATE` | Ollama inventory Gate | 在独立授权下执行模型 inventory，不推理 | 否 | 是 | 是，除授权 inventory | 否 | 否 | 否 | 否 | 是，仅限 inventory | 否 | 否 | 是 | 命令清单、模型清单摘要、无推理确认 |
| `LOCAL-LAUNCHER-031-MOCK-DATA-CLOSED-LOOP-GATE` | mock 数据闭环 Gate | 在 mock 输入下验证闭环，不接触真实资料 | 否 | 是 | 否，仅限明确授权动作 | 仅限授权清单 | 仅限授权代码 | 仅限授权服务 | 仅限授权 endpoint | 仅限授权命令 | 否 | 否 | 是 | mock 来源、无真实资料证明、输出处置、回滚证据 |
| `LOCAL-LAUNCHER-032-SANITIZED-SAMPLE-GATE` | 脱敏样本验证 Gate | 在脱敏证明下验证样本流程 | 否 | 是 | 否，仅限明确授权动作 | 仅限授权清单 | 仅限授权代码 | 仅限授权服务 | 仅限授权 endpoint | 仅限授权命令 | 否 | 仅限脱敏样本 | 是 | 脱敏证明、样本范围、保留/删除规则、审计证据 |
| `LOCAL-LAUNCHER-033-REAL-DATA-AUTHORIZATION-GATE` | 真实资料授权 Gate | 审核是否允许真实 KG / 项目资料读取 | 否 | 是 | 是，除另行授权 | 仅限授权清单 | 否 | 否 | 否 | 否 | 仅在本 Gate 明确授权后 | 仅在本 Gate 明确授权后 | 是 | 资料清单、责任边界、访问方式、停止条件 |
| `LOCAL-LAUNCHER-034-GENERATION-EXPORT-WRITEBACK-GATE` | generation/export/write-back Gate | 审核生成、导出、写回的授权和回滚 | 否 | 是 | 否，仅限明确授权动作 | 仅限授权清单 | 仅限授权代码 | 仅限授权服务 | 仅限授权 endpoint | 仅限授权命令 | 仅限授权资料 | 仅限授权资料 | 是 | 输入输出路径、写回对象、备份、回滚、审计证据 |
| `LOCAL-LAUNCHER-035-TRIAL-READINESS-GATE` | 小范围试运行 Gate | 审核个人试用和多人试用 readiness | 否 | 是 | 否，仅限明确授权动作 | 仅限授权清单 | 仅限授权代码 | 仅限授权服务 | 仅限授权 endpoint | 仅限授权命令 | 仅限授权资料 | 仅限授权资料 | 是 | 试用范围、人员、支持、回滚、问题处理证据 |
| `LOCAL-LAUNCHER-036-FORMAL-USE-FREEZE-GATE` | 正式使用前安全冻结 Gate | 审核正式使用和 50 人使用前冻结条件 | 否 | 是 | 否，仅限明确授权动作 | 仅限授权清单 | 原则禁止，除冻结修复授权 | 仅限授权服务 | 仅限授权 endpoint | 仅限授权命令 | 仅限授权资料 | 仅限授权资料 | 是 | freeze 清单、风险接受、回退方案、最终人工签核 |

统一拆分原则：

1. `SYSTEM-AUTONOMY-*` 节点优先承担治理、矩阵、状态机、证据链、审批、回滚、mock 设计。
2. `LOCAL-LAUNCHER-*` 节点承担本地应用运行边界、runtime preflight、endpoint、Ollama、mock-run、真实资料和试用。
3. docs-only Gate 不得被解释为 runtime ready。
4. runtime Gate 不得被解释为 trial ready。
5. trial Gate 不得被解释为 50 人正式使用 ready。

## 5. 依赖关系图谱

### 5.1 串行依赖

以下任务必须串行：

1. `SYSTEM-AUTONOMY-001` -> `SYSTEM-AUTONOMY-002` -> `SYSTEM-AUTONOMY-003`
2. 权限矩阵固化 -> 状态机设计 -> 审批与回滚策略 -> 证据链 Gate
3. docs-only 治理 Gate -> runtime 控制边界 docs Gate -> runtime preflight 授权 Gate
4. runtime preflight 授权 Gate -> 受控服务启动 Gate -> endpoint 健康检查 Gate
5. mock / dry-run 设计 Gate -> mock 数据闭环 Gate -> 脱敏样本 Gate
6. 脱敏样本 Gate -> 真实资料授权 Gate -> generation/export/write-back Gate
7. 小范围试运行 Gate -> 正式使用前安全冻结 Gate -> 50 人正式使用审批

### 5.2 可并行任务

以下任务可在各自独立 Gate 中并行规划，但不得共享未授权执行结果：

1. 权限维度枚举与证据链字段设计可并行。
2. 审批点清单与失败回滚策略可并行。
3. mock-run 设计与 runtime preflight 问卷设计可并行。
4. trial readiness 框架与 formal-use freeze 框架可并行设计。

并行前提：

1. 每个 Gate 必须有独立目标、独立 allowlist、独立停止条件。
2. 每个 Gate 完成后必须停止等待审核。
3. 任一 Gate 不得读取另一个 Gate 未授权产生的 output/job/export/log 正文。

### 5.3 禁止跨越的节点

以下跨越路径禁止：

1. 禁止从 `SYSTEM-AUTONOMY-002` 直接进入 `SYSTEM-AUTONOMY-003`。
2. 禁止从 docs-only Gate 直接进入 `LOCAL-LAUNCHER-026`。
3. 禁止从 runtime 控制边界 docs Gate 直接启动服务。
4. 禁止从 preflight Gate 直接访问 endpoint。
5. 禁止从 endpoint 健康检查 Gate 直接进行模型推理。
6. 禁止从 mock-run Gate 直接读取真实 KG 或真实项目资料。
7. 禁止从脱敏样本 Gate 直接进入真实使用。
8. 禁止从 trial Gate 直接宣布 50 人正式使用 ready。

### 5.4 从 docs-only 到 runtime preflight 的最小审批条件

从 docs-only 进入 runtime preflight 前，至少需要满足：

1. docs-only Gate 均已完成并由 ChatGPT 总控师审核通过。
2. 权限矩阵明确列出允许命令、禁止命令、读取范围和停止条件。
3. 状态机明确 runtime preflight 不是服务启动、不是 endpoint 访问、不是真实使用。
4. 回滚策略明确发生异常时不执行 destructive git 操作。
5. 证据链模板明确 HEAD、tag、status、读取范围、禁止项确认。
6. preflight 命令清单逐条列出，且不得包含服务启动、curl、HTTP request、localhost、端口探测、Ollama、模型推理，除非该 preflight Gate 明确逐项授权。
7. ChatGPT 总控师明确授权进入 runtime preflight Gate。

## 6. 权限矩阵

| 权限维度 | SYSTEM-AUTONOMY-002 当前状态 | 后续 docs-only Gate | runtime preflight Gate | controlled runtime Gate | trial / formal use Gate |
| --- | --- | --- | --- | --- | --- |
| docs 读取 | 仅授权清单 | 仅授权清单 | 仅授权清单 | 仅授权清单 | 仅授权清单 |
| docs 写入 | 仅目标 docs 文件 | 仅目标 docs 文件 | 仅授权 docs | 仅授权 docs | 仅授权 docs |
| 代码读取 | 禁止 | 默认禁止，除非另行授权 | 仅 allowlist | 仅 allowlist | 仅 allowlist |
| 代码修改 | 禁止 | 禁止 | 禁止，除非另行授权 | 仅授权 patch | 原则禁止，除冻结修复授权 |
| 脚本读取 | 禁止 runtime 脚本正文 | 默认禁止 | 仅 allowlist | 仅 allowlist | 仅 allowlist |
| 脚本执行 | 禁止 | 禁止 | 仅 allowlist 且不得启动服务，除非明确授权 | 仅授权脚本 | 仅授权脚本 |
| 服务启动 | 禁止 | 禁止 | 禁止 | 仅受控授权 | 仅受控授权 |
| endpoint 访问 | 禁止 | 禁止 | 禁止，除非 endpoint Gate 明确授权 | 仅授权 endpoint | 仅授权 endpoint |
| Ollama | 禁止 | 禁止 | 禁止，除非 inventory Gate 明确授权 | 仅授权命令 | 仅授权命令 |
| 模型推理 | 禁止 | 禁止 | 禁止 | 禁止，除非独立推理 Gate 授权 | 仅授权场景 |
| prompt 输入 | 禁止 | 禁止 | 禁止 | 禁止，除非独立授权 | 仅授权 prompt |
| KG 读取 | 禁止 | 禁止 | 禁止 | 仅授权 KG | 仅授权 KG |
| 项目资料读取 | 禁止 | 禁止 | 禁止 | 仅授权资料 | 仅授权资料 |
| output/job/export/log 读取 | 禁止读取正文 | 禁止读取正文 | 仅授权元数据或摘要 | 仅授权范围 | 仅授权范围 |
| generation/export/write-back | 禁止 | 禁止 | 禁止 | 仅独立授权 | 仅独立授权 |
| trial | 禁止 | 禁止 | 禁止 | 禁止 | 仅 trial Gate 授权 |
| 真实使用 | 禁止 | 禁止 | 禁止 | 禁止 | 仅 formal-use Gate 授权 |
| 50 人正式使用 | 禁止 | 禁止 | 禁止 | 禁止 | 仅最高审批授权 |

权限矩阵解释：

1. 未在当前 Gate 明确写入允许范围的权限，默认禁止。
2. 旧节点授权不得自动继承到新节点。
3. docs-only 输出不得作为 runtime、trial 或正式使用证据。
4. 任何权限扩大都必须新建独立 Gate 并等待 ChatGPT 总控师审核。

## 7. 人工审批点

### 7.1 从规划进入实现

任何能力从规划进入实现前，必须满足：

1. 目标能力被拆成唯一 Gate。
2. 读取范围、写入范围、允许命令、禁止命令均已列出。
3. 目标文件或目标代码范围唯一。
4. 风险等级和审批等级已标注。
5. 回滚策略和停止条件已写入。
6. ChatGPT 总控师明确授权进入实现 Gate。

### 7.2 从实现进入运行

任何能力从实现进入运行前，必须满足：

1. 实现 Gate 已完成并通过审核。
2. Git 状态 clean。
3. HEAD / tag / commit 可追溯。
4. runtime preflight Gate 已独立授权。
5. 启动命令、停止命令、端口、日志处置、PID 处置均已明确。
6. 禁止读取 secrets/tokens/credentials。
7. ChatGPT 总控师明确授权进入运行 Gate。

### 7.3 从 mock / dry-run 进入真实 runtime

从 mock / dry-run 进入真实 runtime 前，必须满足：

1. mock 数据来源已证明不含真实 KG / 真实项目资料。
2. dry-run 输出处置、保留和删除规则已明确。
3. mock-run 闭环证据已通过审核。
4. 真实 runtime 输入、输出、写回对象和回滚策略已列出。
5. 任何真实资料访问都必须另行授权。
6. ChatGPT 总控师明确授权进入真实 runtime Gate。

### 7.4 从个人试用进入多人试用

从个人试用进入多人试用前，必须满足：

1. 个人试用范围、账号、数据、操作路径已归档。
2. 试用问题清单和修复状态已归档。
3. 回滚方案、支持响应、责任人和故障处理机制已明确。
4. 证据链覆盖服务、endpoint、模型、资料、输出和写回边界。
5. ChatGPT 总控师明确授权进入多人试用 Gate。

### 7.5 从多人试用进入正式生产使用

从多人试用进入正式生产使用前，必须满足：

1. 多人试用已完成且问题闭环。
2. 安全冻结 Gate 已通过。
3. 50 人正式使用前权限、支持、回滚、审计、培训和责任边界已明确。
4. 生产数据、真实 KG、真实项目资料、生成结果和写回行为均有独立授权。
5. ChatGPT 总控师进行最高级人工审批。

## 8. 失败回滚机制

| 阶段 | 失败场景 | 立即动作 | 回滚机制 | 证据不足时阻断规则 |
| --- | --- | --- | --- | --- |
| docs-only 阶段 | 分支、HEAD、tag、工作区或目标文件状态不符 | 停止，不新增或不继续提交 | 仅回报实际状态，不执行 reset/checkout/delete | 缺少 Git 证据则不得提交 |
| code-change 阶段 | 代码范围不唯一、混入无关文件、测试缺失 | 停止，不扩大修改 | 建议新分支或新 Gate，不擅自回滚 | 缺少最小回归则不得建议合并 |
| runtime preflight 阶段 | 命令超出 allowlist、需要端口/服务/HTTP/Ollama | 停止，不执行命令 | 保全现状并回报缺口 | 命令清单不完整则不得进入 preflight |
| dry-run 阶段 | mock 数据来源不明、输出处置不清 | 停止，不运行 | 删除/保留规则须先获授权 | 无 mock 来源证明则不得执行 |
| trial 阶段 | 试用范围扩大、问题未闭环、回滚不可用 | 停止试用扩展 | 回退到上一个已审核 Gate | 支持和回滚证据不足则不得多人试用 |
| 正式使用前 | 风险未接受、冻结清单不完整、审计缺失 | 停止正式使用 | 回退到 trial 或 freeze Gate | 缺少最高审批则不得正式使用 |

统一回滚原则：

1. Codex 不得擅自执行 destructive git 操作。
2. Codex 不得删除、覆盖、清理未授权文件。
3. Codex 不得通过读取 output/job/export/log 正文补证。
4. 任何回滚执行动作都必须等待 ChatGPT 总控师另行授权。
5. 证据不足时默认阻断，而不是默认放行。

## 9. 证据链要求

### 9.1 每个后续 Gate 必须提交的回报字段

每个后续 Gate 至少必须提交：

1. 节点名称。
2. 是否完成节点。
3. 是否新建 Codex 对话框。
4. 是否使用 Codex 目标模式。
5. 开始前分支。
6. 开始前 HEAD / tag。
7. 结束后 HEAD / tag。
8. `git status --short` 是否 clean。
9. 实际新增文件。
10. 实际修改文件。
11. 实际删除文件。
12. 实际读取文件。
13. 是否读取 runtime 脚本正文。
14. 是否启动、停止或重启服务。
15. 是否执行 Web UI 启动脚本。
16. 是否打开、预览或运行 HTML 页面。
17. 是否访问 endpoint / curl / HTTP request / localhost / 端口探测。
18. 是否读取、清理、删除 PID 文件。
19. 是否运行 Ollama 或任何模型命令。
20. 是否进行模型推理。
21. 是否输入 prompt。
22. 是否读取真实 KG / 真实项目资料。
23. 是否读取 secrets/tokens/credentials。
24. 是否读取 output/job/export/生成结果/日志正文。
25. 是否执行 generation/export/write-back。
26. commit。
27. tag。
28. 节点结论。
29. 是否已停止，未进入后续节点。

### 9.2 HEAD / tag / commit / git status 要求

1. 开始前必须记录分支、HEAD、tag 和 `git status --short`。
2. 提交前必须确认只包含授权文件。
3. stage 只能包含授权文件。
4. commit message 必须使用当前 Gate 指定文本。
5. tag 必须使用当前 Gate 指定 tag。
6. 结束后必须确认 `git status --short` clean。
7. 如任一 Git 证据不一致，必须停止并回报。

### 9.3 新增文件 / 修改文件要求

1. docs-only Gate 只能新增或修改授权 docs 文件。
2. add-only Gate 必须确认目标文件此前不存在或未被跟踪。
3. 修改型 Gate 必须确认目标文件在 allowlist 内。
4. 不得创建 runtime 代码、server 代码、endpoint 代码、API 代码、模型接入代码或 KG 接入代码，除非独立 Gate 明确授权。

### 9.4 读取文件范围要求

1. 读取范围必须来自当前 Gate allowlist。
2. 未授权文件不得打开正文。
3. 真实 KG、真实项目资料、招标文件、图纸、清单、项目样本默认禁止读取。
4. output/job/export/生成结果/日志正文默认禁止读取。
5. secrets/tokens/credentials 和敏感环境变量默认禁止读取。
6. 如需要新增读取范围，必须停止并等待授权。

### 9.5 禁止项确认要求

后续 Gate 回报必须逐项确认：

1. 未运行 runtime。
2. 未启动服务。
3. 未访问 endpoint。
4. 未 curl / HTTP request / localhost / 端口探测。
5. 未运行 Ollama。
6. 未执行模型命令。
7. 未模型推理。
8. 未输入 prompt。
9. 未读取真实 KG / 真实项目资料。
10. 未读取 secrets/tokens/credentials。
11. 未读取 output/job/export/生成结果/日志正文。
12. 未执行 generation/export/write-back。
13. 未修改 local-launcher 静态文件，除非当前 Gate 明确授权。
14. 未修改 runtime 脚本，除非当前 Gate 明确授权。
15. 未进入下一节点。

### 9.6 测试或验证证据要求

1. docs-only Gate 默认不跑测试，除非当前 Gate 明确要求。
2. docs-only Gate 可执行 `git diff --check` 或等价文本级检查。
3. runtime Gate 的测试或验证必须使用当前 Gate 明确授权的命令。
4. endpoint、Ollama、模型、真实资料、generation/export/write-back 的验证必须分别独立授权。
5. 任何验证证据不得来自未授权日志正文或真实资料。

### 9.7 停止点确认要求

每个 Gate 完成后必须明确：

1. 已停止。
2. 未进入下一节点。
3. 未继承旧节点运行授权。
4. 后续动作必须等待 ChatGPT 总控师审核。

## 10. SYSTEM-AUTONOMY-003 建议

建议下一节点名称为：

`SYSTEM-AUTONOMY-003-GOAL-MODE-PERMISSION-MATRIX-AND-STATE-MACHINE-GATE`

建议下一节点目标：

1. 固化完整权限矩阵。
2. 固化系统自治状态机。
3. 定义状态迁移条件。
4. 定义不可跨越状态。
5. 定义各状态的证据链字段。
6. 定义从 docs-only 到 runtime preflight 的最小人工审批条件。

下一节点建议边界：

1. 原则上保持 docs-only。
2. 不授权 runtime。
3. 不授权服务启动。
4. 不授权 endpoint。
5. 不授权 Ollama。
6. 不授权模型推理。
7. 不授权真实 KG / 真实项目资料。
8. 不授权 generation/export/write-back。
9. 不授权进入 `LOCAL-LAUNCHER-026`。

本节点必须停止在 `SYSTEM-AUTONOMY-002`。

不得在本节点进入 `SYSTEM-AUTONOMY-003`。

必须等待 ChatGPT 总控师审核授权后，才能新建后续 Codex 对话框执行下一节点。

## 11. 本节点结论

`SYSTEM-AUTONOMY-002-GOAL-MODE-TASK-DECOMPOSITION-GATE` 的结论如下：

1. 本节点已完成系统自治路线任务拆解规划。
2. 本节点仅形成 docs-only Gate 文档。
3. 本节点不实施任何后续任务。
4. 本节点不运行 runtime。
5. 本节点不验证 runtime。
6. 本节点不启动服务。
7. 本节点不访问 endpoint。
8. 本节点不运行 Ollama。
9. 本节点不进行模型推理。
10. 本节点不读取真实 KG / 真实项目资料。
11. 本节点不执行 generation/export/write-back。
12. 本节点不授权进入 `SYSTEM-AUTONOMY-003`。
13. 本节点不授权进入 `LOCAL-LAUNCHER-026`。
14. 本节点完成后必须停止，等待 ChatGPT 总控师审核。
