# ZDoc KG-20 Frozen Registry Candidate Pre-Registration Readiness and Authorization Gate

## 1. KG-20 执行摘要

KG-20 是对 KG-19 frozen registry candidate 的 docs-only 预注册就绪性复核。本步骤只记录冻结结论承接、当前状态确认、预注册前检查项、不得注册项、不得进入运行 registry 的条件和 KG-21 授权门槛。

KG-20 不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON，不创建 validator，不注册 manifest，不创建真实 registry 文件，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包，不进入 ZDoc 运行链路。

KG-20 结论：KG-15 registry candidate 当前仍可作为 docs-only、`registry_candidate_only`、`not_registered`、disabled 的 frozen registry candidate 保留。其具备进入后续“预注册申请设计”复核的文档基础，但不得注册，不得启用，不得被运行链路读取。KG-21 若继续推进，仍必须由 ChatGPT 总控再次人工授权。

## 2. KG-19 Freeze 结论承接

KG-19 已将 KG-15 registry candidate JSON 冻结为非运行态候选实体，并明确 freeze 不等于注册、不等于启用、不等于可读取。KG-20 继承以下 KG-19 结论：

| KG-19 结论 | KG-20 承接 |
| --- | --- |
| KG-15 registry candidate JSON 可冻结为 docs-only disabled registry candidate | 保持冻结对象不变 |
| `status="registry_candidate_only"` | 继续作为 registry candidate 候选，不升级状态 |
| `registration_status="not_registered"` | 继续未注册，不进入 registry |
| disabled flags 全部锁定为 `false` | 继续禁止 runtime / RAG / evidence / scoring / registry / writeback / export |
| `source_mode="path_and_summary_only"` | 继续只允许路径和摘要，不承载原文 |
| RAG / prompt / system instruction registry 继续隔离 | KG-20 不接入任何 registry |
| system instruction 类内容不得转为 system instruction | KG-20 不创建 system instruction |
| 青天评标 / 满分门控类内容不得作为 evidence 或 scoring basis | KG-20 不证据化、不评分依据化 |
| KG-20 需要再次人工授权 | 本文件仅作为 KG-20 归档，不自动进入 KG-21 |

## 3. Frozen Registry Candidate 当前状态确认

| 项目 | 当前值 | KG-20 结论 |
| --- | --- | --- |
| registry candidate 文件 | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 仍为 docs 下候选文件 |
| `registry_candidate_id` | `zdoc-kg-pilot-qn-index-municipal-bridge-kg01-disabled-registry-candidate` | 可作为候选 ID |
| `manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 仅作 docs-only 溯源 |
| `linked_manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 与 manifest path 一致 |
| 试点方向 | `全能索引 + 市政桥梁 KG01` | 与 KG-04 至 KG-19 基线一致 |
| 备选方向 | `全能索引 + 医院装修改造 KG02` | 仅作备选记录 |
| `source_mode` | `path_and_summary_only` | 不承载原文 |
| `status` | `registry_candidate_only` | 仍为候选态 |
| `registration_status` | `not_registered` | 仍未注册 |
| `activation_requires` | `manual_authorization_after_KG15_review` | 后续仍需人工授权 |
| `manual_authorization_required` | `true` | 人工授权必需 |
| `risk_level` | `R2` | 仍需人工复核，不代表可运行 |

KG-20 对 KG-15 registry candidate JSON 只做静态状态确认，不做字段修改、格式化、补写或重排。

## 4. 状态复核结论

KG-20 对核心状态作出如下复核：

| 状态字段 | 期望值 | 复核结论 |
| --- | --- | --- |
| `status` | `registry_candidate_only` | 通过，仍为 registry candidate 候选 |
| `registration_status` | `not_registered` | 通过，仍未注册 |
| `source_mode` | `path_and_summary_only` | 通过，仍只允许路径与摘要 |
| `manual_authorization_required` | `true` | 通过，仍需人工授权 |
| `pre_registration_status` | `draft_only` | 通过，仍为预注册草案态 |
| `approval_status` | `not_approved` | 通过，未获得注册或启用审批 |

结论：KG-15 registry candidate 仍处于 `registry_candidate_only / not_registered / disabled` 状态，不具备自动注册、自动启用或运行链路读取资格。

## 5. 预注册就绪性检查项

KG-20 将“预注册就绪”限定为文档层面的 readiness，不代表可以注册。后续如设计 registration request draft，至少需要满足以下检查项：

| 检查项 | 当前复核结论 | 后续要求 |
| --- | --- | --- |
| JSON 语法有效 | KG-17/KG-18/KG-19 已确认，KG-20 再次复核通过 | 后续任何变更后必须重校验 |
| 候选 ID 明确 | 已明确 | 不得与正式 registry ID 混用 |
| manifest path 明确 | 已明确 | 只允许指向 docs 下 KG-08 manifest candidate |
| linked manifest path 明确 | 已明确 | 必须与 manifest path 一致 |
| 状态为候选态 | 已确认 | 不得改为 active / registered / runtime |
| 注册状态未注册 | 已确认 | 不得改为 registered |
| source mode 为路径摘要 | 已确认 | 不得加入 source text / raw content |
| disabled flags 全 false | 已确认 | 不得开启任何 flag |
| isolation rules 完整 | 已确认 | 不得删除隔离规则 |
| pre-registration rules 完整 | 已确认 | 不得绕过 draft-only / not-approved |
| manual authorization required | 已确认 | 不得自动授权 |
| system instruction 隔离 | 已确认 | 不得转为 system instruction |
| evidence / scoring 隔离 | 已确认 | 不得证据化或评分依据化 |

KG-20 只确认具备“后续可设计预注册申请草案”的文档基础，不确认可以进入真实 registry。

## 6. 不得注册项清单

以下内容在 KG-20 阶段不得注册：

1. KG-15 registry candidate JSON 不得注册为正式 registry；
2. KG-08 manifest candidate JSON 不得注册为 manifest registry；
3. `manifest_candidate_path` 不得注册为 runtime source；
4. `linked_manifest_candidate_path` 不得注册为 runtime source；
5. `sources.source_path` 不得注册为 RAG corpus path；
6. `source_summary` 不得注册为 prompt template；
7. 全能索引不得注册为 system instruction；
8. 市政桥梁 KG01 不得注册为自动生成依据；
9. 医院装修改造 KG02 不得注册为当前试点启用项；
10. 青天评标 / 满分门控类内容不得注册为 evidence 或 scoring basis；
11. 任何候选内容不得注册到 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回路径；
12. 任何候选内容不得注册到 output / job / export 写入链路。

## 7. 不得进入运行 Registry 的条件

只要存在以下任一情况，frozen registry candidate 不得进入运行 registry：

1. `registration_status` 仍为 `not_registered`；
2. `approval_status` 仍为 `not_approved`；
3. `pre_registration_status` 仍为 `draft_only`；
4. 未形成独立 KG-21 授权；
5. 未形成真实 registry 的隔离验证方案；
6. 未定义可回滚的注册撤销规则；
7. 未定义运行链路不可读取的技术边界；
8. 未完成 system instruction 隔离复核；
9. 未完成 evidence / scoring 隔离复核；
10. 未完成 RAG / prompt / system instruction registry 三类隔离复核；
11. 任一 disabled flag 被改为 `true`；
12. 任一 source path 被替换为原文、复制件、运行目录或外部路径；
13. 出现 `endpoint`、`runtime_config`、`registry_id`、`rag_index`、`prompt_template`、`system_instruction`、`evidence`、`scoring_basis`、`writeback_target` 或 `export_target` 等运行字段。

## 8. RAG / Prompt / System Instruction Registry 边界

KG-20 继续确认三类 registry 的隔离边界：

| Registry 类型 | KG-20 边界 | 结论 |
| --- | --- | --- |
| RAG registry | 不创建 corpus，不创建 index，不生成 embedding，不启用 retrieval | 继续隔离 |
| prompt registry | 不创建 prompt pack，不创建 prompt template，不生成 generation prompt | 继续隔离 |
| system instruction registry | 不创建 system instruction，不写入系统指令原文，不通过 prompt 绕过隔离 | 继续隔离 |

KG-20 不授权任何 RAG / prompt registry / system instruction registry 接入。

## 9. Linked Manifest Candidate Path 复核

KG-20 对 registry candidate 与 KG-08 manifest candidate 的对应关系作出复核：

| 字段 | 当前值 | KG-20 结论 |
| --- | --- | --- |
| `manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 指向 docs 下 KG-08 manifest candidate |
| `linked_manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 与 `manifest_candidate_path` 一致 |
| KG-08 manifest candidate `status` | `candidate_only` | 仍为候选态 |
| KG-08 manifest candidate `registration_status` | `not_registered` | 仍未注册 |
| KG-08 manifest candidate `source_mode` | `path_and_summary_only` | 仍只记录路径和摘要 |

该对应关系只允许用于人工溯源、静态复核和 docs-only 预注册设计，不得用于运行读取、RAG 检索、prompt 构造、system instruction 注入、evidence 引用、scoring basis、写回或导出。

## 10. Disabled Flags 锁定结论

KG-20 对 KG-15 registry candidate 的 disabled flags 作出以下锁定结论：

| 字段 | 锁定值 | KG-20 结论 |
| --- | --- | --- |
| `enabled` | `false` | 锁定，不启用 |
| `runtime_access` | `false` | 锁定，运行链路不可访问 |
| `rag_enabled` | `false` | 锁定，不接入 RAG |
| `evidence_enabled` | `false` | 锁定，不作为 evidence |
| `scoring_enabled` | `false` | 锁定，不作为评分依据 |
| `prompt_registry_enabled` | `false` | 锁定，不进入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 锁定，不进入 system instruction registry |
| `writeback_enabled` | `false` | 锁定，不写回 |
| `export_enabled` | `false` | 锁定，不导出 |

KG-20 不允许任何字段由 `false` 改为 `true`。如未来需要讨论启用，必须另行授权，并重新从风险、隔离、回滚、不可证据化和不可评分依据化角度复核。

## 11. System Instruction 类内容隔离结论

KG-20 结论：system instruction 类内容继续隔离，不得转为 ZDoc system instruction。

本结论覆盖：

1. 全能索引相关资料；
2. 市政桥梁 KG01 试点资料；
3. 医院装修改造 KG02 备选资料；
4. KG-08 manifest candidate；
5. KG-15 registry candidate；
6. 后续任何 pre-registration 或 registry candidate 草案；
7. 任何含系统指令、执行命令、写回、导出、提交、覆盖、自动评分或满分门控倾向的内容。

KG-20 不允许新增 system instruction 字段，不允许复制系统指令原文，不允许将 source summary 改写为隐性 system instruction，不允许通过 prompt registry 绕过隔离。

## 12. 青天评标 / 满分门控隔离结论

KG-20 结论：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

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

## 13. KG-21 授权条件

KG-21 不得自动进入。若 ChatGPT 总控决定继续，KG-21 建议只能在明确人工授权后进入以下 docs-only / static-only 范围之一：

1. 设计 registry candidate pre-registration request 草案；
2. 设计 pre-registration request 的字段清单；
3. 设计 pre-registration request 与 frozen registry candidate 的关联规则；
4. 设计 registration denial / approval 的人工审核清单；
5. 设计保持 `not_registered` 与 disabled flags 的审计规则；
6. 设计禁止运行 registry 读取的静态规则；
7. 设计真实 validator 的规则规格，但不创建脚本；
8. 设计 future registration gate，但不执行注册。

KG-21 如涉及以下任一动作，必须取得更高等级明确授权：

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

## 14. KG-20 最终记录

KG-20 最终记录如下：

1. KG-19 freeze 结论继续成立；
2. KG-15 registry candidate 当前仍保持 `registry_candidate_only`；
3. KG-15 registry candidate 当前仍保持 `registration_status="not_registered"`；
4. KG-15 registry candidate 当前仍保持 disabled；
5. KG-08 manifest candidate 当前仍保持 `candidate_only` 与 `not_registered`；
6. `linked_manifest_candidate_path` 与 `manifest_candidate_path` 均指向 docs 下 KG-08 manifest candidate；
7. 所有 disabled flags 继续锁定为 `false`；
8. KG-20 不注册 manifest；
9. KG-20 不创建真实 registry 文件；
10. KG-20 不接入 RAG / prompt registry / system instruction registry；
11. KG-20 不启用任何知识包；
12. KG-20 不允许 evidence 化或评分依据化；
13. system instruction 类内容继续隔离；
14. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
15. KG-21 需要 ChatGPT 总控再次人工授权，不得自动进入。
