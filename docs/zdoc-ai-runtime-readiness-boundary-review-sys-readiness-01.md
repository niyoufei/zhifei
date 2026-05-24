# ZDoc SYS-READINESS-01 AI Runtime Readiness Boundary Review

## 1. 执行摘要

SYS-READINESS-01 是 KG-ARCHIVE-01 之后的 docs-only 可用性边界复核。本步骤围绕“知识图谱接入系统后，本地化部署模型升级到最新版本，并以 ChatGPT 作为系统总控，最终达到单机受控可使用阶段”建立下一阶段路线边界。

本步骤不接入知识图谱，不运行 validator，不执行 `py_compile`，不接入测试或 CI，不运行服务、Ollama、端口或 endpoint，不升级、拉取、删除或替换任何本地模型，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。

## 2. 当前基线

| 项目 | 当前状态 |
| --- | --- |
| 仓库 | `/Users/youfeini/Desktop/文档生成系统` |
| 分支 | `main` |
| 开始前 HEAD | `224ca03392e9604539502e951bb76b5687bd66d2` |
| 开始前 tag | `v0.1.380-zdoc-kg-static-anchor-phase-master-archive-index` |
| KG 静态阶段 | 已完成阶段性归档 |
| 总索引 | KG-ARCHIVE-01 已完成 |
| AI 知识图谱接入系统 | 未接入 |
| 本地模型升级 | 未升级 |
| 50 人并发 / 正式生产服务器 | 当前不考虑 |
| 当前运行状态 | no-runtime / no-registration / no-integration |

## 3. KG-ARCHIVE-01 后状态复核

KG-ARCHIVE-01 后，AI 知识图谱锚点静态阶段已完成以下归档对象：

| 对象 | 文件 | 当前状态 | SYS-READINESS-01 结论 |
| --- | --- | --- | --- |
| KG-08 manifest candidate | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | `candidate_only` / `not_registered` / disabled | 仍不作为运行输入 |
| KG-15 registry candidate | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | `registry_candidate_only` / `not_registered` / disabled | 仍不是真实 registry |
| KG-31 disabled manifest entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | `disabled_entity_only` / `not_registered` / disabled | 仍不可加载 |
| KG-33 disabled registry entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | `disabled_registry_entity_only` / `not_registered` / disabled | 仍不可注册、不可加载 |
| KG-41 validator draft | `docs/kg-controlled-validators/zdoc_kg_disabled_entity_pair_static_validator_draft.py` | `static_draft_only` / not executed / not compiled | 仍不可运行、不可 `py_compile`、不可接入测试或 CI |

复核结论：KG 静态阶段只是完成候选、禁用实体、validator 草案、静态复核和归档索引；它不等于系统接入、不等于模型升级、不等于真实使用阶段。

## 4. 当前明确未发生事项

SYS-READINESS-01 确认当前仍未发生以下事项：

1. AI 知识图谱未接入 ZDoc 运行系统；
2. KG-08 / KG-15 / KG-31 / KG-33 未注册、未启用、未加载；
3. KG-41 validator 草案未运行、未 `py_compile`、未接入测试或 CI；
4. RAG / prompt registry / system instruction registry 未接入；
5. 本地模型未升级、未拉取、未替换、未删除；
6. 没有启动 ZDoc 服务、ZBid 服务、Ollama、端口或 endpoint；
7. 没有触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
8. 没有生成 DOCX；
9. 没有写 `output/job/export`；
10. 没有进入真实使用阶段、模型升级阶段、50 人正式部署或生产服务器阶段。

## 5. 下一阶段路线总览

建议后续路线必须拆成独立授权阶段，禁止跨阶段合并执行：

| 阶段 | 定位 | 是否可自动进入 |
| --- | --- | --- |
| 1. KG read-only preview 接入设计 | 只设计只读预览接入，不注册、不加载、不运行 | 否 |
| 2. validator 受控启用评估 | 只评估是否允许运行 validator，不直接运行 | 否 |
| 3. 本地模型升级评估 | 只盘点模型、版本、磁盘、回退方案，不拉取或升级 | 否 |
| 4. 本地模型受控升级 | 如获授权，最小化升级并可回退 | 否 |
| 5. ChatGPT 总控运行边界 | 设计 ChatGPT 作为总控的指挥、审批、暂停、回退边界 | 否 |
| 6. 单机受控可使用阶段验收 | 只在前序全部通过后做单机验收 | 否 |

任何阶段均不得默认进入下一阶段；每一步必须由 ChatGPT 总控单独授权。

## 6. 阶段一：KG Read-Only Preview 接入设计

### 目标

设计 KG 静态资料进入 ZDoc 的只读预览方案，只允许“看见候选、看见状态、看见禁用原因”，不允许生成链路使用。

### 输入

1. KG-ARCHIVE-01 总索引；
2. KG-08 manifest candidate；
3. KG-15 registry candidate；
4. KG-31 disabled manifest entity；
5. KG-33 disabled registry entity；
6. KG-47 no-execution closeout。

### 输出

1. read-only preview 的页面或文档设计；
2. 字段展示规则；
3. 禁用状态展示规则；
4. 人工审核入口设计；
5. 不可生成、不可 evidence、不可 scoring 的边界说明。

### 禁止项

1. 不得注册 manifest 或 registry；
2. 不得启用知识包；
3. 不得接入 RAG / prompt registry / system instruction registry；
4. 不得让 `/generate`、`/export_docx`、`/review/apply` 读取 KG；
5. 不得写 ZBid；
6. 不得把 source summary 当成正文知识自动生成。

### 回退要求

若发现 preview 设计会被误认为运行接入，必须回退为 docs-only 说明，不进入 UI、API 或运行配置。

## 7. 阶段二：Validator 受控启用评估

### 目标

评估是否允许从 KG-41 静态 validator 草案进入受控运行前的最小化离线校验。该阶段只评估，不运行 validator。

### 输入

1. KG-41 validator draft；
2. KG-42 至 KG-46 validator 复核、审计、归档文件；
3. KG-31 / KG-33 disabled entity pair；
4. 禁用字段与引用关系检查清单。

### 输出

1. 是否允许运行 validator 的人工判断；
2. 若允许，限定命令、输入、输出、失败处理；
3. 若不允许，保持静态草案的冻结记录；
4. validator 输出不得写运行目录的规则。

### 禁止项

1. 不得直接运行 validator；
2. 不得 `py_compile`；
3. 不得接入测试或 CI；
4. 不得让 validator 自动扫描仓库或读取 `AI知识图谱大全` 原文；
5. 不得修改 KG-08 / KG-15 / KG-31 / KG-33；
6. 不得把 validator 结果转化为注册、启用或生成授权。

### 回退要求

若 validator 评估发现草案边界不足，应冻结 KG-41，重新回到 docs-only validator 设计，不运行任何脚本。

## 8. 阶段三：本地模型升级评估

### 目标

评估本地化部署模型是否具备升级条件。该阶段只做评估，不拉取、不升级、不删除、不替换模型。

### 输入

1. 当前本地模型清单的人工授权盘点结果；
2. 当前机器磁盘、内存、芯片、系统版本的只读盘点结果；
3. ZDoc 模型调用边界；
4. 目标模型选择原则；
5. 回退策略草案。

### 输出

1. 模型升级可行性报告；
2. 候选模型选择原则；
3. 资源约束与风险清单；
4. 回退策略；
5. 是否允许进入受控升级的授权请求。

### 禁止项

1. 不得运行 Ollama；
2. 不得访问模型 endpoint；
3. 不得拉取模型；
4. 不得删除模型；
5. 不得替换模型；
6. 不得修改 ZDoc 模型配置；
7. 不得触发任何生成链路。

### 回退要求

若资源或兼容性不确定，应保持当前模型状态不变，并输出需要人工确认的缺口。

## 9. 阶段四：本地模型受控升级

### 目标

仅在阶段三通过并获得单独授权后，执行最小化、可回退的本地模型升级。

### 输入

1. 已审核的升级评估报告；
2. 明确的目标模型；
3. 磁盘与资源确认；
4. 旧模型保留策略；
5. 回退命令和失败条件。

### 输出

1. 模型升级执行记录；
2. 版本与资源变化记录；
3. 回退状态；
4. 最小化离线验证记录；
5. 不接入 ZDoc 运行链的确认。

### 禁止项

1. 不得同时升级多个模型；
2. 不得删除旧模型，除非单独授权；
3. 不得修改 ZDoc 生成链路；
4. 不得把模型升级等同于系统可用；
5. 不得触发 `/generate`、`/export_docx`、`/review/apply`；
6. 不得写 `output/job/export`。

### 回退要求

升级失败或性能不可接受时，应保留旧模型并回退到升级前状态；回退不应修改 KG 文件或 registry 状态。

## 10. 阶段五：ChatGPT 总控运行边界

### 目标

设计 ChatGPT 作为系统总控时的审批、暂停、回退、证据隔离和人工确认边界。该阶段仍优先 docs-only，不默认接入运行系统。

### 输入

1. KG 静态归档成果；
2. validator 评估结论；
3. 本地模型升级评估或升级记录；
4. ZDoc 当前运行链路说明；
5. ChatGPT 总控职责清单。

### 输出

1. ChatGPT 总控允许动作清单；
2. ChatGPT 总控禁止动作清单；
3. 人工确认点；
4. 暂停与回退规则；
5. 审计日志建议；
6. 单机受控验收前置条件。

### 禁止项

1. 不得让 ChatGPT 自动触发生成、导出、review apply 或 ZBid 写回；
2. 不得让 ChatGPT 自动启用知识包；
3. 不得让 ChatGPT 自动修改模型配置；
4. 不得绕过人工审核；
5. 不得把 KG 内容作为 evidence 或 scoring basis；
6. 不得把 system instruction 类资料直接变成系统指令。

### 回退要求

若总控职责与系统运行权限边界不清，应回退到人工审批模式，不进入受控可使用阶段。

## 11. 阶段六：单机受控可使用阶段验收

### 目标

在前序阶段全部单独授权并通过后，评估是否达到单机受控可使用状态。该阶段不考虑 50 人并发，不考虑正式生产服务器。

### 输入

1. KG read-only preview 接入设计或实现结果；
2. validator 评估或受控校验结果；
3. 本地模型升级评估或升级记录；
4. ChatGPT 总控边界；
5. 回退与暂停策略；
6. 禁止项执行记录。

### 输出

1. 单机受控可使用验收报告；
2. 可用范围；
3. 不可用范围；
4. 风险与回退清单；
5. 是否允许进入更大范围试点的授权请求。

### 禁止项

1. 不得直接进入真实使用阶段；
2. 不得默认扩大到多人并发；
3. 不得部署到正式生产服务器；
4. 不得绕过 ChatGPT 总控审核；
5. 不得把验收通过等同于 50 人正式部署；
6. 不得解除 no-evidence、no-scoring、no-writeback 边界。

### 回退要求

若验收失败，应回退到最近一个已审核通过的静态或单机阶段；不得继续扩大使用范围。

## 12. 跨阶段硬边界

以下边界在所有阶段默认保持，除非 ChatGPT 总控后续单独授权并明确覆盖：

1. 不得直接进入真实使用阶段；
2. 不得直接运行 validator；
3. 不得直接 `py_compile`；
4. 不得直接接入测试或 CI；
5. 不得直接接入 RAG / prompt registry / system instruction registry；
6. 不得直接升级模型；
7. 不得运行服务、Ollama、端口或 endpoint；
8. 不得触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
9. 不得生成 DOCX；
10. 不得写 `output/job/export`；
11. 不得修改任何 JSON；
12. 不得修改 KG-41 validator 草案；
13. 不得复制、移动、删除 `AI知识图谱大全` 文件；
14. 不得把 KG 内容作为 evidence；
15. 不得把 KG 内容作为 scoring basis；
16. 不得把 system instruction 类资料原样启用。

## 13. 推荐下一授权请求

若后续继续，建议 ChatGPT 总控优先授权一个新的 docs-only 阶段：

`SYS-READINESS-02：KG read-only preview access design`

建议边界：

1. 仅设计 read-only preview；
2. 不创建运行 registry；
3. 不注册、启用、加载知识包；
4. 不运行 validator；
5. 不升级模型；
6. 不运行服务或 endpoint；
7. 不触发生成、导出、review apply 或 ZBid 写回；
8. 输出一个 docs-only 设计文档后停止。

## 14. SYS-READINESS-01 最终结论

SYS-READINESS-01 确认：KG-ARCHIVE-01 后 AI 知识图谱锚点静态阶段已经完成归档，但 AI 知识图谱仍未接入系统，本地模型仍未升级，当前也不考虑 50 人并发与正式生产服务器。

下一阶段路线应拆分为 KG read-only preview 接入设计、validator 受控启用评估、本地模型升级评估、本地模型受控升级、ChatGPT 总控运行边界、单机受控可使用阶段验收。每一阶段均需单独授权、单独验证、可回退，不得自动进入下一阶段。

本步骤不进入 KG-48，不进入真实使用阶段。
