# ZDoc KG-22 Frozen Registry Candidate Pre-Registration Packet and Handoff Index

## 1. KG-22 执行摘要

KG-22 是对 KG-08 manifest candidate、KG-15 registry candidate 以及 KG-16 至 KG-21 校验、冻结、授权处置链路的 docs-only 预注册资料包索引与受控移交归档。本步骤只建立文档层面的资料包索引，不注册 manifest，不创建真实 registry，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包，不进入运行链路。

KG-22 结论：当前资料包只允许作为 docs-only frozen registry candidate 的人工审查索引。KG-15 registry candidate 继续保持 `registry_candidate_only`、`not_registered`、disabled；KG-08 manifest candidate 继续保持 `candidate_only`、`not_registered`、disabled。资料包内任一文件均不得作为运行输入、evidence、scoring basis、prompt source、system instruction source、RAG corpus、写回源或导出源。

## 2. 受控资料包对象

| 对象 | 路径 | 当前状态 | KG-22 处置 |
| --- | --- | --- | --- |
| KG-08 manifest candidate | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | `candidate_only` / `not_registered` / disabled | 仅作为路径与摘要候选，人工溯源 |
| KG-15 registry candidate | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | `registry_candidate_only` / `not_registered` / disabled | 仅作为 frozen registry candidate，人工审查 |
| KG-16 static validation rules | `docs/zdoc-kg-disabled-registry-candidate-static-validation-rules-kg16.md` | docs-only rules | 静态校验规则依据 |
| KG-17 manual validation report | `docs/zdoc-kg-disabled-registry-candidate-manual-static-validation-report-kg17.md` | docs-only report | 人工静态校验证据 |
| KG-18 validation disposition | `docs/zdoc-kg-disabled-registry-candidate-validation-disposition-and-freeze-gate-kg18.md` | docs-only disposition | freeze gate 处置依据 |
| KG-19 freeze record | `docs/zdoc-kg-disabled-registry-candidate-freeze-record-and-next-gate-kg19.md` | docs-only freeze record | 冻结状态记录 |
| KG-20 readiness gate | `docs/zdoc-kg-frozen-registry-candidate-pre-registration-readiness-and-authorization-gate-kg20.md` | docs-only readiness review | 预注册就绪性复核 |
| KG-21 authorization disposition | `docs/zdoc-kg-frozen-registry-candidate-pre-registration-authorization-disposition-kg21.md` | docs-only authorization disposition | no-registration 授权处置 |

该资料包仅用于 ChatGPT 总控人工复核和后续 KG-23 授权判断，不是运行配置包。

## 3. KG-16 至 KG-21 链路摘要

| 阶段 | 核心结论 | 对 KG-22 的约束 |
| --- | --- | --- |
| KG-16 | 定义 registry candidate 静态校验规则，包括必填字段、禁止字段、path 指向、状态、禁用 flags、隔离规则和失败条件 | 资料包必须保留 KG-16 作为校验规则依据 |
| KG-17 | 人工静态校验通过，未发现 blocker、major 或 minor 问题 | 资料包可引用 KG-17 作为人工校验证据 |
| KG-18 | KG-15 registry candidate 满足 freeze gate，可冻结为 docs-only disabled candidate | 资料包必须保持 frozen / disabled / not registered |
| KG-19 | 正式记录 KG-15 registry candidate freeze，明确 freeze 不等于注册或启用 | 资料包不得被解释为注册包 |
| KG-20 | 预注册就绪性仅限文档 readiness，不代表可以注册 | 资料包只可作为后续审查材料 |
| KG-21 | 授权处置为仅保留 docs-only frozen registry candidate，暂不注册 manifest，暂不创建真实 registry，暂不接入三类 registry | KG-22 继续执行 no-registration 边界 |

链路结论：KG-16 至 KG-21 已形成校验、冻结、就绪性复核和授权处置闭环，但闭环结果是“继续保留候选且不注册”，不是“可以注册”。

## 4. Frozen Registry Candidate 当前状态确认

| 字段 | 当前值 | KG-22 结论 |
| --- | --- | --- |
| `registry_candidate_id` | `zdoc-kg-pilot-qn-index-municipal-bridge-kg01-disabled-registry-candidate` | 仅为候选 ID |
| `manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 仅作 docs-only 溯源 |
| `linked_manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 与 manifest path 一致 |
| `pilot_direction` | `全能索引 + 市政桥梁 KG01` | 仅为受控试点方向 |
| `backup_direction` | `全能索引 + 医院装修改造 KG02` | 仅为备选方向 |
| `source_mode` | `path_and_summary_only` | 不承载原文 |
| `status` | `registry_candidate_only` | 继续锁定为候选态 |
| `registration_status` | `not_registered` | 继续锁定为未注册 |
| `manual_authorization_required` | `true` | 后续仍需人工授权 |
| `risk_level` | `R2` | 仍需人工复核，不代表可运行 |

KG-22 不修改 KG-15 registry candidate JSON，也不修改 KG-08 manifest candidate JSON。

## 5. 本阶段结论

KG-22 的本阶段结论如下：

1. 仅允许将资料包保留为 docs-only frozen registry candidate 的人工审查索引；
2. 不允许注册 manifest；
3. 不允许创建真实 registry；
4. 不允许接入 RAG / prompt registry / system instruction registry；
5. 不允许启用任何知识包；
6. 不允许作为运行输入；
7. 不允许作为 evidence；
8. 不允许作为 scoring basis；
9. 不允许写回或导出；
10. 不允许进入 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回路径；
11. 不允许写入 `output/job/export`；
12. 不允许复制、移动、删除、重命名或改写 `AI知识图谱大全` 原文件。

## 6. No-Registration / No-Registry / No-Runtime 边界

| 边界 | KG-22 结论 | 原因 |
| --- | --- | --- |
| 不注册 manifest | 继续禁止 | KG-08 仍为 `candidate_only` / `not_registered`，且仅路径摘要 |
| 不创建真实 registry | 继续禁止 | KG-15 仍为 `registry_candidate_only` / `not_registered`，未获得批准 |
| 不接入 RAG | 继续禁止 | `rag_enabled=false`，未创建 corpus/index/embedding |
| 不接入 prompt registry | 继续禁止 | `prompt_registry_enabled=false`，未拆分 prompt pack，未完成人工审核 |
| 不接入 system instruction registry | 继续禁止 | `system_instruction_registry_enabled=false`，系统指令类内容必须隔离 |
| 不启用运行访问 | 继续禁止 | `runtime_access=false`，没有运行读取授权 |
| 不证据化 | 继续禁止 | `evidence_enabled=false`，任何内容不得直接作为 evidence |
| 不评分依据化 | 继续禁止 | `scoring_enabled=false`，青天评标 / 满分门控不得作为 scoring basis |
| 不写回 / 不导出 | 继续禁止 | `writeback_enabled=false`，`export_enabled=false` |

## 7. 预注册资料包文件清单

| 文件 | 用途 | 当前状态 | 是否可作为运行输入 |
| --- | --- | --- | --- |
| `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | KG-08 manifest candidate，登记源路径、摘要、试点方向和禁用 flags | candidate only / not registered / disabled | 否 |
| `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | KG-15 registry candidate，连接 KG-08 candidate 并记录 registry candidate 禁用状态 | registry candidate only / not registered / disabled | 否 |
| `docs/zdoc-kg-disabled-registry-candidate-static-validation-rules-kg16.md` | 静态校验规则设计 | docs-only | 否 |
| `docs/zdoc-kg-disabled-registry-candidate-manual-static-validation-report-kg17.md` | 人工静态校验报告 | docs-only | 否 |
| `docs/zdoc-kg-disabled-registry-candidate-validation-disposition-and-freeze-gate-kg18.md` | 校验处置与 freeze gate | docs-only | 否 |
| `docs/zdoc-kg-disabled-registry-candidate-freeze-record-and-next-gate-kg19.md` | freeze record 与下一授权门槛 | docs-only | 否 |
| `docs/zdoc-kg-frozen-registry-candidate-pre-registration-readiness-and-authorization-gate-kg20.md` | 预注册就绪性复核 | docs-only | 否 |
| `docs/zdoc-kg-frozen-registry-candidate-pre-registration-authorization-disposition-kg21.md` | 授权处置与 no-registration 边界 | docs-only | 否 |
| `docs/zdoc-kg-frozen-registry-candidate-pre-registration-packet-and-handoff-index-kg22.md` | 本资料包索引与受控移交记录 | docs-only | 否 |

资料包索引不新增 manifest 实体，不新增 registry 实体，不改变任何候选 JSON 的注册状态。

## 8. 文件用途与运行输入判断

KG-22 对资料包内文件的运行输入判断如下：

1. JSON candidate 文件只可用于人工静态复核，不可被 ZDoc 自动加载；
2. docs review 文件只可用于审计链路说明，不可作为运行配置；
3. KG-08 source paths 只记录 `AI知识图谱大全` 原始路径，不复制原文；
4. KG-08 source summaries 只记录摘要，不提供系统指令、prompt、评分规则或证据正文；
5. KG-15 registry candidate 只连接 KG-08 candidate，不创建真实 registry；
6. KG-16 至 KG-21 只提供校验、冻结和授权处置依据，不提供运行参数；
7. KG-22 只建立资料包索引，不提供任何 loader、endpoint、runtime config、corpus path 或 registry ID。

结论：资料包内全部文件均不可作为运行输入。

## 9. Disabled Flags 锁定结论

KG-22 对 disabled flags 继续作出锁定结论：

| 字段 | 锁定值 | KG-22 结论 |
| --- | --- | --- |
| `enabled` | `false` | 不启用 |
| `runtime_access` | `false` | 运行链路不可访问 |
| `rag_enabled` | `false` | 不接入 RAG |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 不进入 system instruction registry |
| `writeback_enabled` | `false` | 不触发写回 |
| `export_enabled` | `false` | 不触发导出 |

任何将上述字段改为 `true` 的动作都不属于 KG-22 范围。

## 10. System Instruction 类内容隔离结论

KG-22 结论：system instruction 类内容继续隔离，不得转为 ZDoc system instruction。

本结论覆盖：

1. 全能索引相关资料；
2. 市政桥梁 KG01 试点资料；
3. 医院装修改造 KG02 备选资料；
4. KG-08 manifest candidate；
5. KG-15 registry candidate；
6. KG-16 至 KG-22 的校验、冻结、授权处置和资料包索引文档；
7. 后续任何 pre-registration、registration request、registry candidate、freeze record 或 handoff index；
8. 任何含系统指令、执行命令、写回、导出、提交、覆盖、自动评分或满分门控倾向的内容。

KG-22 不允许新增 system instruction 字段，不允许复制系统指令原文，不允许将 source summary 改写为隐性 system instruction，不允许通过 prompt registry 绕过隔离。

## 11. 青天评标 / 满分门控隔离结论

KG-22 结论：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

强制边界如下：

1. `evidence_enabled=false` 必须保持；
2. `scoring_enabled=false` 必须保持；
3. `pre_registration_rules.evidence_forbidden=true` 必须保持；
4. `pre_registration_rules.scoring_basis_forbidden=true` 必须保持；
5. `isolation_rules` 中的 `not_evidence` 必须保持；
6. `isolation_rules` 中的 `not_scoring_basis` 必须保持；
7. 不得作为自动评分依据；
8. 不得作为满分门控依据；
9. 不得作为复评优化依据；
10. 不得作为 ZBid 写回依据；
11. 不得进入 `/review/apply`；
12. 不得生成正式证据引用。

## 12. 受控移交规则

KG-22 资料包如后续移交给 ChatGPT 总控或 KG-23，只允许按以下规则处理：

1. 只移交路径、状态、用途、风险和边界信息；
2. 不移交 `AI知识图谱大全` 原文；
3. 不把资料包复制到运行配置目录；
4. 不将任何候选 JSON 注册为 manifest 或 registry；
5. 不将任何 docs 文件作为 loader 输入；
6. 不从资料包派生 endpoint、service、job、output、export 或 writeback 配置；
7. 不将资料包用作 evidence、scoring basis、prompt source 或 system instruction source；
8. KG-23 必须重新获得 ChatGPT 总控人工授权。

## 13. KG-23 授权条件

KG-23 不得自动进入。若 ChatGPT 总控决定继续，KG-23 建议只能在明确人工授权后进入以下 docs-only / static-only 范围之一：

1. 设计资料包人工审阅签收记录；
2. 设计 no-registration retention record；
3. 设计 registration denial / deferral record 草案；
4. 设计 future registration request 的人工审核清单，但不创建真实 registry；
5. 设计资料包变更审计规则；
6. 设计真实 validator 的规则规格，但不创建脚本；
7. 设计运行 registry 禁止读取的静态边界文档；
8. 复核是否继续暂停在 frozen candidate / handoff index 阶段。

KG-23 如涉及以下任一动作，必须取得更高等级明确授权：

1. 修改 KG-08 manifest candidate JSON；
2. 修改 KG-15 registry candidate JSON；
3. 创建真实 validator 脚本；
4. 注册 manifest；
5. 创建真实 registry 文件；
6. 把 candidate 文件放入任何运行配置目录；
7. 接入 RAG / prompt registry / system instruction registry；
8. 启用任何知识包；
9. 运行 ZDoc、ZBid、Ollama、端口或 endpoint；
10. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
11. 生成 DOCX；
12. 写入 `output/job/export`；
13. 复制、移动、删除、重命名或改写 `AI知识图谱大全` 原文件。

## 14. KG-22 最终记录

KG-22 最终记录如下：

1. KG-08 manifest candidate 与 KG-15 registry candidate 已形成受控资料包索引；
2. KG-16 至 KG-21 的校验、冻结、授权处置链路已纳入资料包摘要；
3. KG-15 registry candidate 继续保持 `registry_candidate_only`；
4. KG-15 registry candidate 继续保持 `registration_status="not_registered"`；
5. KG-15 registry candidate 继续保持 disabled；
6. KG-08 manifest candidate 继续保持 `candidate_only` 与 `not_registered`；
7. 资料包仅允许作为 docs-only frozen registry candidate 的人工审查索引；
8. KG-22 不注册 manifest；
9. KG-22 不创建真实 registry；
10. KG-22 不接入 RAG / prompt registry / system instruction registry；
11. KG-22 不启用任何知识包；
12. 资料包内全部文件均不可作为运行输入；
13. 所有 disabled flags 继续锁定为 `false`；
14. system instruction 类内容继续隔离；
15. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
16. KG-23 需要 ChatGPT 总控再次人工授权，不得自动进入。
