# ZDoc KG-RUNTIME-01 Read-Only Preview Integration Design

## 1. 执行摘要

KG-RUNTIME-01 是知识图谱 read-only preview 接入设计文档。本步骤仅设计目标形态、边界和下一阶段授权条件，不写代码，不创建 adapter，不创建运行态文件，不接入 ZDoc 系统。

本步骤不修改任何 JSON，不修改 KG-41 validator 草案，不修改代码 / tests / frontend / backend / config，不修改既有 docs，不复制、移动、删除 `AI知识图谱大全` 文件，不创建真实 registry，不注册、启用、加载知识包，不接入 RAG / prompt registry / system instruction registry，不运行服务 / validator / Ollama / 端口 / endpoint，不执行 `py_compile`，不升级或拉取本地模型，不生成 DOCX，不写 `output/job/export`。

## 2. KG-ARCHIVE-01 与 SYS-READINESS-01 结论承接

| 来源 | 关键结论 | KG-RUNTIME-01 承接 |
| --- | --- | --- |
| KG-ARCHIVE-01 | AI 知识图谱锚点静态阶段已完成总索引归档 | 可作为 read-only preview 的设计依据 |
| KG-ARCHIVE-01 | KG-08 / KG-15 / KG-31 / KG-33 / KG-41 均保持静态、禁用、未注册或未执行 | 不改变这些状态 |
| KG-47 | KG-31 / KG-33 entity pair 仍为 docs 非运行目录下的静态禁用草案 | preview 只能读取其展示字段设计，不授权加载 |
| KG-47 | KG-41 validator 草案不运行、不 `py_compile`、不接入测试或 CI | KG-RUNTIME-01 不启用 validator |
| SYS-READINESS-01 | 下一阶段优先为 KG read-only preview 接入设计 | 本文件仅完成设计，不进入实现 |
| SYS-READINESS-01 | 不得直接接入 RAG / prompt registry / system instruction registry | 继续冻结 |
| SYS-READINESS-01 | 不得直接升级模型或进入真实使用阶段 | 继续冻结 |

## 3. 当前静态对象状态

| 对象 | 文件 | 当前状态 | Preview 设计结论 |
| --- | --- | --- | --- |
| KG-08 manifest candidate | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | `candidate_only` / `not_registered` / disabled | 只可作为人工预览来源说明 |
| KG-15 registry candidate | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | `registry_candidate_only` / `not_registered` / disabled | 不是真实 registry |
| KG-31 disabled manifest entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | `disabled_entity_only` / `not_registered` / disabled | 不可加载、不可启用 |
| KG-33 disabled registry entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | `disabled_registry_entity_only` / `not_registered` / disabled | 不可注册、不可加载 |
| KG-41 validator draft | `docs/kg-controlled-validators/zdoc_kg_disabled_entity_pair_static_validator_draft.py` | `static_draft_only` / not executed / not compiled | 不可运行、不可 `py_compile`、不可接入测试或 CI |

## 4. Read-Only Preview 目标形态

read-only preview 的目标不是让知识图谱进入生成链，而是让人工可以在受控界面或受控文档结构中查看静态候选状态。

目标形态应满足：

1. 仅人工触发；
2. 仅只读查看；
3. 仅展示路径、摘要、风险等级、禁用状态、审核状态、隔离规则和下一步授权条件；
4. 不展示或复制 `AI知识图谱大全` 原文；
5. 不展示系统指令原文；
6. 不展示 prompt 原文；
7. 不写回正文；
8. 不写回 ZBid；
9. 不进入 `/generate` 主生成链；
10. 不作为 evidence；
11. 不作为评分依据；
12. 不进入 RAG / prompt registry / system instruction registry。

## 5. Preview 信息架构设计

建议 read-only preview 分为以下只读区域：

| 区域 | 展示内容 | 禁止内容 |
| --- | --- | --- |
| Static Archive Summary | KG 静态阶段完成状态、总索引链接、no-runtime 状态 | 不展示运行入口 |
| Candidate Overview | KG-08 / KG-15 candidate 的 status、registration_status、disabled flags | 不允许注册或启用按钮 |
| Entity Pair Overview | KG-31 / KG-33 的 entity_status、enabled=false、not_registered、not_loadable | 不允许加载或写入配置 |
| Source Summary | source_path、source_summary、risk_level、domain_tags | 不复制原文、不展示系统指令或 prompt 原文 |
| Isolation Rules | not_evidence、not_scoring_basis、not_rag_loadable、not_system_instruction_loadable | 不提供绕过隔离的操作 |
| Manual Review Notes | 人工审核状态、待确认事项、下一阶段授权条件 | 不自动推进下一阶段 |
| Boundary Banner | 当前仅为 read-only preview，不可生成、不可导出、不可写回 | 不提供 `/generate`、export、review apply 入口 |

## 6. Preview 触发规则

read-only preview 必须人工触发，不得自动触发：

1. 只能由 ChatGPT 总控或人工审核者明确请求；
2. 不得在 ZDoc 打开文档、生成文档、导出文档、审校应用时自动加载；
3. 不得在评分、证据、RAG、prompt 组装、system instruction 组装时触发；
4. 不得被定时任务、后台 job、watcher、endpoint 自动触发；
5. 不得从 ZBid 写回链路触发；
6. 不得把 preview 打开动作视为启用知识包。

## 7. 数据读取边界设计

KG-RUNTIME-01 不实现读取逻辑。若后续单独授权进入实现设计，读取边界应限定为：

1. 只读取 docs 下已冻结的 candidate/entity 文件；
2. 只读取路径、摘要、状态、禁用 flags、风险等级、隔离规则；
3. 不读取 `AI知识图谱大全` 原文件正文；
4. 不扫描外部目录；
5. 不读取 backend / frontend / config 运行配置作为 KG 来源；
6. 不读取 RAG index；
7. 不读取 prompt registry；
8. 不读取 system instruction registry；
9. 不读取 ZBid 写回目标。

## 8. 写入边界设计

read-only preview 必须保持无写入：

1. 不写正文；
2. 不写候选 JSON；
3. 不写 entity JSON；
4. 不写 registry；
5. 不写 backend / frontend / config；
6. 不写 job / output / export；
7. 不写 DOCX；
8. 不写 ZBid；
9. 不写 RAG index；
10. 不写 prompt registry；
11. 不写 system instruction registry。

如需记录人工审核意见，必须在后续单独授权的新文档或新审核记录中处理，不得由 preview 自动写入。

## 9. Evidence / Scoring / Generation 隔离

read-only preview 必须明确显示并强制保留以下隔离结论：

| 链路 | 结论 |
| --- | --- |
| evidence | 不得作为 evidence |
| scoring | 不得作为评分依据或 scoring basis |
| `/generate` | 不得进入主生成链 |
| generation reference | 不得作为自动生成引用 |
| `/export_docx` | 不得进入导出链 |
| `/review/apply` | 不得进入审校应用链 |
| ZBid writeback | 不得写回 |
| RAG | 不得被索引或检索 |
| prompt registry | 不得注册为 prompt pack |
| system instruction registry | 不得转为 system instruction |

## 10. KG-31 / KG-33 Disabled Entity Pair 保持规则

KG-31 / KG-33 在 read-only preview 设计中继续保持：

1. `enabled=false`；
2. `registration_status=not_registered`；
3. `runtime_loadable=false`；
4. `rag_loadable=false`；
5. `prompt_registry_loadable=false`；
6. `system_instruction_loadable=false`；
7. `evidence_allowed=false`；
8. `scoring_allowed=false`；
9. KG-33 `registry_loadable=false`；
10. KG-33 `runtime_registered=false`；
11. KG-33 `manifest_entity_registered=false`；
12. KG-33 `manifest_entity_loadable=false`。

preview 不得改变上述任何字段，也不得通过其他配置绕过这些字段。

## 11. KG-41 Validator 草案保持规则

KG-41 validator 草案继续保持：

1. 不运行；
2. 不 `py_compile`；
3. 不接入测试；
4. 不接入 CI；
5. 不接入 preview；
6. 不自动读取 KG-08 / KG-15 / KG-31 / KG-33；
7. 不写任何报告；
8. 不生成通过或失败结论；
9. 不作为 preview 是否可展示的自动门槛；
10. 不进入 ZDoc 运行链路。

若后续要评估 validator 受控启用，必须进入独立授权阶段，不得由 KG-RUNTIME-01 推导。

## 12. UI / API / Adapter 边界

KG-RUNTIME-01 不创建 UI、不创建 API、不创建 adapter、不修改运行代码。

后续若进入 KG-RUNTIME-02，也应先限定为 docs-only 或最小实现方案设计，并明确：

1. 是否允许创建 adapter；
2. adapter 是否只读取 docs 下冻结文件；
3. adapter 是否禁止写入；
4. adapter 是否禁止被 `/generate` 调用；
5. adapter 是否禁止被 export、review apply、ZBid writeback 调用；
6. adapter 是否禁止触发 validator；
7. adapter 是否禁止访问模型 endpoint；
8. adapter 失败后如何回退到 disabled 状态。

## 13. KG-RUNTIME-02 输入设计

若 ChatGPT 总控单独授权 KG-RUNTIME-02，建议输入限定为：

1. `docs/zdoc-kg-static-anchor-phase-master-archive-index-kg-archive-01.md`；
2. `docs/zdoc-ai-runtime-readiness-boundary-review-sys-readiness-01.md`；
3. `docs/zdoc-kg-read-only-preview-integration-design-kg-runtime-01.md`；
4. KG-08 manifest candidate；
5. KG-15 registry candidate；
6. KG-31 disabled manifest entity；
7. KG-33 disabled registry entity；
8. KG-47 no-execution closeout。

不得把 `AI知识图谱大全` 原文件正文、本地模型、Ollama endpoint、RAG index、prompt registry、system instruction registry 作为 KG-RUNTIME-02 默认输入。

## 14. KG-RUNTIME-02 输出设计

KG-RUNTIME-02 若继续，建议仅输出以下之一：

1. read-only preview adapter 方案设计；
2. read-only preview UI 字段设计；
3. preview 手工验收清单；
4. adapter 是否允许创建的授权请求；
5. 继续保持 docs-only 的边界复核。

KG-RUNTIME-02 不应直接输出：

1. adapter 代码；
2. runtime registry；
3. RAG index；
4. prompt registry 条目；
5. system instruction registry 条目；
6. DOCX；
7. output/job/export 产物；
8. ZBid 写回结果。

## 15. KG-RUNTIME-02 禁止项

KG-RUNTIME-02 不得自动进入。若获授权，也应默认禁止：

1. 修改任何 JSON；
2. 修改 KG-41 validator 草案；
3. 修改代码 / tests / frontend / backend / config，除非授权明确允许；
4. 修改既有 docs，除非授权明确允许；
5. 复制、移动、删除 `AI知识图谱大全` 文件；
6. 创建真实 registry；
7. 创建 adapter 或任何运行态文件，除非授权明确允许；
8. 注册、启用、加载知识包；
9. 接入 RAG / prompt registry / system instruction registry；
10. 运行服务 / validator / Ollama / 端口 / endpoint；
11. 执行 `py_compile`；
12. 升级、拉取、删除或替换任何本地模型；
13. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
14. 生成 DOCX；
15. 写 `output/job/export`。

## 16. KG-RUNTIME-02 回退要求

若后续授权进入 KG-RUNTIME-02，必须预设回退条件：

1. 发现 preview 会被主生成链读取，立即回退；
2. 发现 preview 需要写入任何文件，立即回退；
3. 发现 preview 需要注册或启用知识包，立即回退；
4. 发现 preview 会进入 evidence 或 scoring，立即回退；
5. 发现 preview 会触发 validator、模型 endpoint 或服务，立即回退；
6. 发现 preview 需要复制 `AI知识图谱大全` 原文，立即回退；
7. 回退后保持 KG-31 / KG-33 disabled 状态不变；
8. 回退后不得删除或修改 KG 静态归档文件。

## 17. 验收标准

KG-RUNTIME-01 的验收标准为：

1. 新增且仅新增本 docs-only 设计文档；
2. 明确 read-only preview 只能人工触发、只读查看、不可写回正文；
3. 明确不得作为 evidence、不得作为评分依据、不得进入 `/generate` 主生成链；
4. 明确不得接入 RAG / prompt registry / system instruction registry；
5. 明确不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回；
6. 明确不得写 `output/job/export`；
7. 明确 KG-31 / KG-33 disabled entity pair 保持禁用、不可加载、不可注册；
8. 明确 KG-41 validator 草案不得运行、不得 `py_compile`、不得接入测试或 CI；
9. 明确 KG-RUNTIME-02 输入、输出、禁止项、回退要求；
10. 明确下一阶段必须由 ChatGPT 单独授权。

## 18. 最终结论

KG-RUNTIME-01 只完成 ZDoc KG read-only preview integration design，不创建 adapter，不接入系统，不进入 KG-RUNTIME-02。

当前 AI 知识图谱仍未进入 ZDoc 运行链。KG-31 / KG-33 仍是 disabled entity pair，KG-41 validator 草案仍是未运行、未编译、未接入的静态草案。后续如需继续，必须由 ChatGPT 总控单独授权。
