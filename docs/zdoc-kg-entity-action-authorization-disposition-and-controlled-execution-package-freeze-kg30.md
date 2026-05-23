# ZDoc KG-30 Entity-Action Authorization Disposition and Controlled Execution Package Freeze

## 1. KG-30 执行摘要

KG-30 是对 KG-29 entity-action authorization request 的 docs-only / no-execution 最终处置与 KG-31 受控实体化动作前冻结记录。

KG-30 只做授权处置、输入输出边界冻结、禁止项冻结和回退要求冻结。KG-30 不创建真实 manifest，不创建真实 registry，不创建 validator 脚本，不注册，不启用，不接入系统，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON。

KG-30 结论：当前资料包具备进入 KG-31 “首次受控实体化动作”单独授权评审的基础，但不具备自动进入 KG-31 的执行许可。KG-31 只能在 ChatGPT 后续单独审核并明确授权后执行。

## 2. 复核输入

KG-30 复核以下冻结资料：

| 阶段 | 文件 | KG-30 用途 |
| --- | --- | --- |
| KG-08 | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | manifest candidate 冻结对象 |
| KG-15 | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | registry candidate 冻结对象 |
| KG-25 | `docs/zdoc-kg-pre-entity-implementation-plan-and-authorization-gate-kg25.md` | 实体化前方案基线 |
| KG-26 | `docs/zdoc-kg-pre-entity-implementation-plan-completeness-and-no-execution-review-kg26.md` | 完整性与 no-execution 复核 |
| KG-27 | `docs/zdoc-kg-pre-entity-implementation-final-authorization-disposition-and-execution-package-freeze-gate-kg27.md` | execution package freeze gate |
| KG-28 | `docs/zdoc-kg-pre-entity-execution-package-frozen-index-and-manual-readiness-checklist-kg28.md` | frozen index 与人工 readiness checklist |
| KG-29 | `docs/zdoc-kg-pre-entity-execution-package-final-acceptance-and-entity-action-authorization-request-kg29.md` | final acceptance 与 entity-action authorization request |

KG-30 不读取、复制、移动、删除或改写 `AI知识图谱大全` 原文件。

## 3. KG-08 与 KG-15 当前冻结状态

| 对象 | 当前状态 | 注册状态 | 运行状态 | KG-30 处置 |
| --- | --- | --- | --- | --- |
| KG-08 manifest candidate | `candidate_only` | `not_registered` | disabled | 继续作为冻结候选，不转为真实 manifest |
| KG-15 registry candidate | `registry_candidate_only` | `not_registered` | disabled | 继续作为冻结候选，不转为真实 registry |

KG-08 与 KG-15 继续保持以下约束：

1. `enabled=false`；
2. `runtime_access=false`；
3. `rag_enabled=false`；
4. `evidence_enabled=false`；
5. `scoring_enabled=false`；
6. `prompt_registry_enabled=false`；
7. `system_instruction_registry_enabled=false`；
8. `writeback_enabled=false`；
9. `export_enabled=false`；
10. `source_mode="path_and_summary_only"`。

KG-30 不修改上述任一字段。

## 4. KG-25 至 KG-29 验收结论汇总

| 阶段 | 冻结或验收结论 | KG-30 承接 |
| --- | --- | --- |
| KG-25 | 建立实体化前目录规划、字段冻结、字段映射、静态校验、人工复核、回退策略；不执行 | 作为 KG-31 输入边界设计基础 |
| KG-26 | 确认 KG-25 完整性，未发现 blocker / major / minor；继续 no-execution | 作为 KG-31 前置完整性依据 |
| KG-27 | 冻结未来 execution package 的输入条件、禁止项和人工授权门槛；不授权创建实体 | 作为 KG-31 freeze gate 来源 |
| KG-28 | 建立 frozen execution package index 与 manual readiness checklist；不授权执行 | 作为 KG-31 输入索引来源 |
| KG-29 | 接受 pre-entity execution package 为 frozen docs-only package；提出 entity-action authorization request | 由 KG-30 作出处置 |

承接结论：KG-25 至 KG-29 已形成完整的 docs-only 审查链路，但该链路只支持进入下一步授权评审，不支持自动执行实体化。

## 5. KG-29 Entity-Action Authorization Request 处置

KG-30 对 KG-29 提出的 entity-action authorization request 作出以下处置：

1. 接受 KG-29 对 pre-entity execution package 的最终人工验收结论；
2. 接受 KG-29 对 entity action 的定义；
3. 接受 KG-29 对 KG-30 的输入条件、禁止项和人工授权门槛；
4. 确认 KG-30 不执行任何 entity action；
5. 确认 KG-31 如需进入首次受控实体化动作，必须重新由 ChatGPT 单独授权；
6. 确认 KG-31 授权文本必须明确允许创建什么、禁止什么、如何校验、如何回退；
7. 确认未获得 KG-31 授权前，KG-08 与 KG-15 仍只作为 docs-only frozen candidates。

处置结论：KG-29 的授权请求被归档为 KG-31 的授权评审输入，不在 KG-30 执行。

## 6. 是否具备进入 KG-31 的条件

KG-30 判定如下：

| 判定项 | 结果 | 说明 |
| --- | --- | --- |
| KG-08 / KG-15 状态可审计 | 具备 | 两个 JSON 仍为 candidate / not_registered / disabled |
| KG-25 至 KG-29 链路完整 | 具备 | 已形成方案、复核、冻结、索引、验收与授权请求 |
| 禁止项已明确 | 具备 | 已覆盖 no-runtime、no-registry、no-evidence、no-scoring、no-writeback |
| 回退要求已具备设计基础 | 具备 | KG-25 至 KG-29 已多次冻结误改、误启用、误接入处置 |
| KG-31 自动执行许可 | 不具备 | 必须由 ChatGPT 单独审核授权 |
| KG-30 内部实体化许可 | 不具备 | KG-30 仍为 docs-only / no-execution |

最终判定：具备进入 KG-31 授权评审的资料条件；不具备自动进入 KG-31 或在 KG-30 执行首次实体化动作的条件。

## 7. KG-31 输入文件冻结

若 ChatGPT 后续单独授权 KG-31，KG-31 输入文件应冻结为以下清单：

| 输入 ID | 文件 | 是否可修改 | 是否可作为运行输入 |
| --- | --- | --- | --- |
| `kg08_manifest_candidate` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 否，除非 KG-31 明确授权 | 否 |
| `kg15_registry_candidate` | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 否，除非 KG-31 明确授权 | 否 |
| `kg25_plan` | `docs/zdoc-kg-pre-entity-implementation-plan-and-authorization-gate-kg25.md` | 否 | 否 |
| `kg26_review` | `docs/zdoc-kg-pre-entity-implementation-plan-completeness-and-no-execution-review-kg26.md` | 否 | 否 |
| `kg27_freeze_gate` | `docs/zdoc-kg-pre-entity-implementation-final-authorization-disposition-and-execution-package-freeze-gate-kg27.md` | 否 | 否 |
| `kg28_index` | `docs/zdoc-kg-pre-entity-execution-package-frozen-index-and-manual-readiness-checklist-kg28.md` | 否 | 否 |
| `kg29_acceptance` | `docs/zdoc-kg-pre-entity-execution-package-final-acceptance-and-entity-action-authorization-request-kg29.md` | 否 | 否 |
| `kg30_freeze` | `docs/zdoc-kg-entity-action-authorization-disposition-and-controlled-execution-package-freeze-kg30.md` | 否 | 否 |

KG-31 不得扩大输入范围到 `AI知识图谱大全` 原文或其他桌面目录，除非后续授权明确改变范围。

## 8. KG-31 输出文件冻结建议

KG-30 不创建 KG-31 输出文件。若 KG-31 后续获得单独授权，应在授权文本中先明确输出类型。

建议 KG-31 仅允许以下两种路线之一：

| 路线 | 可选输出 | 说明 |
| --- | --- | --- |
| 保守路线 | 仅新增一个 docs-only KG-31 授权实施方案文件 | 继续 no-execution，不创建真实实体 |
| 受控实体化路线 | 仅创建一个明确命名的 disabled entity draft 文件，并新增一个 docs review 文件 | 必须继续 disabled、not_registered、not_runtime_readable |

若 KG-31 选择受控实体化路线，输出文件必须满足：

1. 不在 `backend`、`frontend`、`config`、运行 registry、任务目录、job、output 或 export 目录；
2. 文件名必须包含 `disabled`、`draft` 或 `candidate` 类标识；
3. 所有运行能力必须为 `false`；
4. 不得复制 `AI知识图谱大全` 原文；
5. 不得包含 loader、endpoint、registration id、activation id、writeback target 或 export path；
6. 不得被 ZDoc 自动读取。

## 9. KG-31 执行范围冻结

若 KG-31 后续获授权，执行范围必须在授权文本中逐项明确。默认冻结范围如下：

1. 可读取 KG-08、KG-15、KG-25 至 KG-30；
2. 可执行 `python3 -m json.tool` 校验 KG-08 与 KG-15；
3. 可执行 `git status --short`、`git diff --check`、`git diff --cached --check`；
4. 可新增授权文本指定的文件；
5. 不得修改既有 docs，除非授权文本明确列出；
6. 不得修改 KG-08 或 KG-15，除非授权文本明确列出；
7. 不得修改代码、tests、frontend、backend、config；
8. 不得进入运行链路；
9. 不得启用任何 registry 或知识包；
10. 不得自动进入 KG-32。

KG-31 的最小安全执行单位应是一份明确文件清单加一次静态校验闭环。

## 10. KG-31 禁止项冻结

KG-31 默认禁止以下动作，除非 ChatGPT 后续单独给出更高等级、逐项明确的授权：

1. 创建真实 runtime manifest；
2. 创建真实 runtime registry；
3. 创建 validator 脚本；
4. 注册 manifest；
5. 注册 registry；
6. 启用知识包；
7. 接入 RAG；
8. 接入 prompt registry；
9. 接入 system instruction registry；
10. 启用 retrieval、generation reference、evidence、scoring、writeback 或 export；
11. 运行 ZDoc 服务；
12. 运行 ZBid 服务；
13. 运行 Ollama；
14. 访问端口或 endpoint；
15. 触发 `/generate`、`/export_docx`、`/review/apply`；
16. 触发 ZBid 写回；
17. 生成 DOCX；
18. 写入 `output/job/export`；
19. 复制、移动、删除、重命名或改写 `AI知识图谱大全` 文件；
20. 把 `AI知识图谱大全` 文件复制进 ZDoc；
21. 将任何候选内容作为 evidence；
22. 将任何候选内容作为 scoring basis；
23. 将 system instruction 类内容转为 ZDoc system instruction。

## 11. KG-31 回退要求冻结

若 KG-31 后续获授权并发生任何越界信号，应按以下回退要求处理：

| 越界信号 | 回退要求 |
| --- | --- |
| 出现非授权文件变更 | 停止，先报告 `git status --short` 与变更清单 |
| KG-08 / KG-15 被误改 | 停止，不继续提交，等待人工处置 |
| 任一 disabled flag 变为 `true` | 判定 blocker，停止 KG-31 |
| 出现真实 registration id 或 activation id | 判定 blocker，停止 KG-31 |
| 出现 loader、endpoint、job、output、export、writeback 字段 | 判定 blocker，停止 KG-31 |
| 出现原文复制、系统指令原文、评分门控正文 | 判定隔离失败，停止 KG-31 |
| JSON 校验失败 | 不得提交，不得进入下一阶段 |
| 授权文本含糊 | 默认保持 KG-30 冻结状态 |

回退目标是停止扩大风险，而不是尝试自行恢复或继续推进。

## 12. System Instruction 与青天评标隔离冻结

KG-30 继续冻结以下隔离结论：

1. `全能` 不得作为 system instruction；
2. `市政桥梁 KG01` 不得作为 system instruction；
3. `医院装修改造 KG02` 不得作为 system instruction；
4. source summary 不得改写为隐性系统指令；
5. system instruction 类内容不得进入 system instruction registry；
6. prompt registry 不得绕过 system instruction quarantine；
7. 青天评标与满分门控内容不得作为 evidence；
8. 青天评标与满分门控内容不得作为 scoring basis；
9. 评分响应类内容不得进入 `/review/apply`；
10. 相关内容不得写回 ZBid、进入导出链或影响评分结果。

## 13. 当前 No-Execution 结论

KG-30 当前结论如下：

| 项目 | KG-30 结果 |
| --- | --- |
| 创建真实 manifest | 否 |
| 创建真实 registry | 否 |
| 创建 validator 脚本 | 否 |
| 注册 manifest | 否 |
| 注册 registry | 否 |
| 启用知识包 | 否 |
| 接入 RAG | 否 |
| 接入 prompt registry | 否 |
| 接入 system instruction registry | 否 |
| 修改 KG-08 JSON | 否 |
| 修改 KG-15 JSON | 否 |
| 复制 `AI知识图谱大全` 文件 | 否 |
| 运行服务 / Ollama / 端口 / endpoint | 否 |
| 触发生成 / 导出 / review apply / ZBid 写回 | 否 |
| 生成 DOCX | 否 |
| 写 `output/job/export` | 否 |

## 14. KG-31 单独授权门槛

KG-31 如需继续，ChatGPT 授权文本必须至少回答：

1. KG-31 是否仍为 docs-only；
2. KG-31 是否允许首次受控实体化动作；
3. 若允许实体化，具体允许创建哪个文件；
4. 是否允许创建真实 manifest，还是只允许 disabled entity draft；
5. 是否允许创建真实 registry，还是只允许 disabled registry draft；
6. 是否允许创建 validator 脚本；
7. KG-08 与 KG-15 是否必须继续不可修改；
8. 所有 disabled flags 是否必须继续为 `false`；
9. 是否继续禁止 RAG / prompt registry / system instruction registry；
10. 是否继续禁止 evidence、scoring、writeback、export；
11. 是否继续禁止运行服务、端口、endpoint；
12. 如果越界，按什么方式停止与回退。

未逐项明确授权时，默认不得进入 KG-31。

## 15. KG-30 最终记录

KG-30 已完成对 KG-29 entity-action authorization request 的处置，已冻结 KG-31 的输入文件、潜在输出边界、执行范围、禁止项与回退要求。

KG-30 不创建真实 manifest，不创建真实 registry，不创建 validator，不注册，不启用，不接入系统。

KG-30 不进入 KG-31。
