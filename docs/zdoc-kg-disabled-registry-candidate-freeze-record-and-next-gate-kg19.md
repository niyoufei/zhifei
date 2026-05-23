# ZDoc KG-19 Disabled Registry Candidate Freeze Record and Next Gate

## 1. KG-19 执行摘要

KG-19 是对 KG-15 disabled registry candidate JSON 的 docs-only freeze 记录。本步骤只记录冻结对象、冻结依据、冻结后约束和 KG-20 授权门槛，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON，不创建 validator，不注册 manifest，不创建真实 registry 文件，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包，不进入 ZDoc 运行链路。

KG-19 结论：KG-15 registry candidate JSON 已通过 KG-16 静态校验规则设计、KG-17 人工静态校验和 KG-18 validation disposition / freeze gate 复核，可冻结为 docs-only、`registry_candidate_only`、`not_registered`、disabled 的 registry candidate。freeze 不代表注册，不代表启用，不代表运行链路可读取。

## 2. 冻结对象说明

| 项目 | 内容 |
| --- | --- |
| 冻结对象 | KG-15 disabled registry candidate JSON |
| 文件路径 | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` |
| `registry_candidate_id` | `zdoc-kg-pilot-qn-index-municipal-bridge-kg01-disabled-registry-candidate` |
| `manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` |
| `linked_manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` |
| 试点方向 | `全能索引 + 市政桥梁 KG01` |
| 备选方向 | `全能索引 + 医院装修改造 KG02` |
| `source_mode` | `path_and_summary_only` |
| `status` | `registry_candidate_only` |
| `registration_status` | `not_registered` |
| `activation_requires` | `manual_authorization_after_KG15_review` |
| 当前用途 | docs-only registry candidate，人工审核候选，不参与运行 |

冻结对象只作为候选实体记录，不代表真实 registry，不代表已注册 manifest，不代表可被 ZDoc 自动读取，不代表已获得检索、生成、证据、评分、写回或导出权限。

## 3. KG-16 / KG-17 / KG-18 承接结论

| 阶段 | 承接结论 | KG-19 处置 |
| --- | --- | --- |
| KG-16 | 已定义 registry candidate 必填字段、禁止字段、path 指向、状态、注册状态、source mode、disabled flags、isolation rules、pre-registration rules、三类 registry 隔离和失败条件 | 作为 freeze 的规则依据 |
| KG-17 | 人工静态校验通过，未发现 blocker、major 或 minor 问题；两个 JSON 语法有效；disabled flags 全部为 `false` | 作为 freeze 的校验证据 |
| KG-18 | 判定 registry candidate 满足 freeze gate，可冻结为 docs-only、disabled、not registered 的 registry candidate | 作为 KG-19 freeze 记录的直接依据 |

KG-19 不扩大 KG-16/KG-17/KG-18 的授权范围。所有结论仅用于 docs-only freeze record。

## 4. Registry Candidate Freeze 判定结论

KG-19 freeze 判定如下：

1. KG-15 registry candidate JSON 语法有效；
2. KG-08 manifest candidate JSON 语法有效；
3. KG-16 必填字段均存在；
4. KG-16 禁止字段均不存在；
5. `manifest_candidate_path` 与 `linked_manifest_candidate_path` 均存在；
6. 两个 path 均指向 docs 下 KG-08 frozen manifest candidate；
7. `status="registry_candidate_only"`；
8. `registration_status="not_registered"`；
9. `source_mode="path_and_summary_only"`；
10. disabled flags 全部为 boolean `false`；
11. `manual_authorization_required=true`；
12. `pre_registration_rules.pre_registration_status="draft_only"`；
13. `pre_registration_rules.approval_status="not_approved"`；
14. RAG registry 隔离规则完整；
15. prompt registry 隔离规则完整；
16. system instruction registry 隔离规则完整；
17. system instruction 类内容继续隔离；
18. 青天评标 / 满分门控类内容不得作为 evidence 或 scoring basis；
19. KG-17 未发现 blocker、major 或 minor 问题；
20. KG-18 已确认可进入 freeze gate。

结论：KG-15 registry candidate JSON 可冻结为非运行态、不可自动读取、不可注册、不可启用的 docs-only registry candidate。

## 5. Freeze 后状态

freeze 后必须继续保持以下状态：

| 字段 | 冻结后状态 | 说明 |
| --- | --- | --- |
| `status` | `registry_candidate_only` | 只允许作为 registry candidate 候选 |
| `registration_status` | `not_registered` | 未注册到 manifest registry 或任何运行 registry |
| `source_mode` | `path_and_summary_only` | 只允许路径与摘要，不承载正文 |
| `enabled` | `false` | 不启用 |
| `runtime_access` | `false` | 运行链路不可访问 |
| `rag_enabled` | `false` | 不进入 RAG |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 不进入 system instruction registry |
| `writeback_enabled` | `false` | 不触发写回 |
| `export_enabled` | `false` | 不触发导出 |
| `manual_authorization_required` | `true` | 后续必须人工授权 |

freeze 是候选状态锁定，不是启用审批，不是注册审批。

## 6. 禁止变更项

在 KG-20 获得新的明确人工授权前，以下内容不得变更：

| 禁止变更项 | 禁止原因 |
| --- | --- |
| KG-15 registry candidate JSON | KG-19 只做 freeze record，不做实体修改 |
| `linked_manifest_candidate_path` | 防止改变关联对象或引入运行路径 |
| `manifest_candidate_path` | 防止改变溯源对象或引入运行路径 |
| disabled flags | 防止 registry candidate 被误启用 |
| `registration_status` | 防止候选被误判为已注册 |
| `status` | 防止候选态被绕过 |
| `source_mode` | 防止从路径摘要模式扩展为正文承载 |
| `risk_level` | 风险等级调整必须重新复核 |
| `domain_tags` | 专业标签调整必须重新复核 |
| `isolation_rules` | 隔离规则调整必须重新复核 |
| `pre_registration_rules` | 预注册规则调整必须重新复核 |
| `future_authorization_conditions` | 后续授权条件调整必须重新复核 |

如未来确需变更上述任一项，应先形成独立授权任务，并重新执行静态校验。

## 7. 锁定结论

KG-19 对以下锁定项作出冻结结论：

| 锁定项 | 冻结值 | KG-19 结论 |
| --- | --- | --- |
| `enabled` | `false` | 锁定 |
| `runtime_access` | `false` | 锁定 |
| `rag_enabled` | `false` | 锁定 |
| `evidence_enabled` | `false` | 锁定 |
| `scoring_enabled` | `false` | 锁定 |
| `prompt_registry_enabled` | `false` | 锁定 |
| `system_instruction_registry_enabled` | `false` | 锁定 |
| `writeback_enabled` | `false` | 锁定 |
| `export_enabled` | `false` | 锁定 |

任何将上述字段改为 `true` 的动作都不属于 KG-19 范围，也不得在未取得后续明确授权前执行。

## 8. RAG Registry 隔离结论

KG-19 继续确认 RAG registry 隔离：

1. `rag_enabled=false` 必须保持；
2. `pre_registration_rules.rag_registry_forbidden=true` 必须保持；
3. `isolation_rules` 必须包含 `rag_registry_disabled`；
4. 不得创建 RAG index；
5. 不得创建 embedding 配置；
6. 不得创建 corpus entry；
7. 不得将 `manifest_candidate_path` 或 `linked_manifest_candidate_path` 作为 RAG corpus path；
8. 不得生成或引用向量索引。

KG-19 不授权任何 RAG 接入。

## 9. Prompt Registry 隔离结论

KG-19 继续确认 prompt registry 隔离：

1. `prompt_registry_enabled=false` 必须保持；
2. `pre_registration_rules.prompt_registry_forbidden=true` 必须保持；
3. `isolation_rules` 必须包含 `prompt_registry_disabled`；
4. 不得创建 prompt pack；
5. 不得创建 prompt template；
6. 不得创建 generation prompt；
7. 不得把 path 或 summary 改写成 prompt；
8. 不得通过 prompt registry 绕过 system instruction 隔离。

KG-19 不授权任何 prompt registry 接入。

## 10. System Instruction Registry 隔离结论

KG-19 继续确认 system instruction registry 隔离：

1. `system_instruction_registry_enabled=false` 必须保持；
2. `pre_registration_rules.system_instruction_registry_forbidden=true` 必须保持；
3. `isolation_rules` 必须包含 `system_instruction_registry_disabled`；
4. `isolation_rules` 必须包含 `system_instruction_sources_must_remain_quarantined`；
5. 不得新增 `system_instruction` 正文字段；
6. 不得写入系统指令原文；
7. 不得把 source summary 改写成隐性 system instruction；
8. 不得通过 prompt registry 绕过隔离。

KG-19 不授权任何 system instruction registry 接入。

## 11. System Instruction 类内容结论

KG-19 结论：system instruction 类内容不得转为 ZDoc system instruction。

本结论适用于：

1. KG-08 manifest candidate；
2. KG-15 registry candidate；
3. 后续可能出现的 pre-registration、registry 草案或 freeze record；
4. 全能索引相关资料；
5. 市政桥梁 KG01 试点资料；
6. 医院装修改造 KG02 备选资料；
7. 任何被识别为系统指令、执行命令、写回、导出、提交、覆盖或自动评分的内容。

## 12. 青天评标 / 满分门控隔离结论

KG-19 结论：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

强制边界如下：

1. `evidence_enabled=false` 必须保持；
2. `scoring_enabled=false` 必须保持；
3. `pre_registration_rules.evidence_forbidden=true` 必须保持；
4. `pre_registration_rules.scoring_basis_forbidden=true` 必须保持；
5. `not_evidence` 必须保持；
6. `not_scoring_basis` 必须保持；
7. 不得作为自动评分依据；
8. 不得作为满分门控依据；
9. 不得作为复评优化依据；
10. 不得作为 ZBid 写回依据；
11. 不得进入 `/review/apply`；
12. 不得生成正式证据引用。

## 13. KG-20 授权条件

KG-20 不得自动进入。若 ChatGPT 总控决定继续，建议 KG-20 只能在明确人工授权后执行，并优先限定为以下 docs-only / static-only 事项之一：

1. 设计 registry candidate post-freeze review checklist；
2. 设计 registry candidate 变更审计规则；
3. 设计 registry candidate freeze 签署字段；
4. 设计从 `registry_candidate_only` 到未来注册态的门槛清单，但不执行注册；
5. 设计真实 validator 的伪代码或规格映射，但不创建脚本；
6. 复核是否需要补充 `frozen_at`、`frozen_by`、`freeze_reason`、`freeze_source_commit` 等字段，但不得直接修改 JSON；
7. 复核是否需要进入 registration request draft，但不得创建真实 registry 文件。

KG-20 如涉及以下动作，必须取得更高等级明确授权：

1. 修改 KG-08 manifest candidate JSON；
2. 修改 KG-15 registry candidate JSON；
3. 创建真实 validator 脚本；
4. 注册 manifest；
5. 创建真实 registry 文件；
6. 把 registry candidate 放入任何运行配置目录；
7. 接入 RAG / prompt registry / system instruction registry；
8. 启用任何知识包；
9. 运行 ZDoc、ZBid、Ollama、端口或 endpoint；
10. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
11. 生成 DOCX；
12. 写入 `output/job/export`；
13. 复制、移动、删除、重命名或改写 `AI知识图谱大全` 原文件。

## 14. KG-19 最终记录

KG-19 最终记录如下：

1. KG-15 registry candidate JSON 被冻结为 docs-only disabled registry candidate；
2. freeze 不改变 KG-15 registry candidate JSON；
3. freeze 不改变 KG-08 manifest candidate JSON；
4. freeze 不注册 manifest；
5. freeze 不创建真实 registry 文件；
6. freeze 不启用知识包；
7. freeze 不接入 RAG、prompt registry、system instruction registry；
8. freeze 不允许 evidence 化或评分依据化；
9. freeze 后仍保持 `registry_candidate_only`、`not_registered`、`path_and_summary_only`；
10. 所有 disabled flags 继续锁定为 `false`；
11. RAG registry、prompt registry、system instruction registry 继续隔离；
12. system instruction 类内容继续不得转为 system instruction；
13. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
14. KG-20 需要 ChatGPT 总控再次人工授权，不得自动进入。
