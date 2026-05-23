# ZDoc KG-18 Disabled Registry Candidate Validation Disposition and Freeze Gate

## 1. KG-18 执行摘要

KG-18 是对 KG-15 disabled registry candidate JSON 的 docs-only 校验处置与 freeze gate 归档。本步骤承接 KG-17 人工静态校验报告与 KG-16 静态校验规则，只记录处置结论、冻结条件和后续 KG-19 授权门槛，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON，不创建 validator，不注册 manifest，不创建真实 registry 文件，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包。

KG-18 结论：KG-15 registry candidate JSON 已通过 KG-17 人工静态校验，未发现 blocker、major 或 minor 问题。当前 registry candidate 可冻结为 docs-only、`registry_candidate_only`、`not_registered`、disabled 的候选实体。freeze 不代表注册，不代表启用，不代表运行链路可读取。

## 2. 复核对象

| 对象 | 路径 | KG-18 用途 |
| --- | --- | --- |
| KG-17 manual validation report | `docs/zdoc-kg-disabled-registry-candidate-manual-static-validation-report-kg17.md` | 提取人工静态校验结论和问题清单 |
| KG-16 static validation rules | `docs/zdoc-kg-disabled-registry-candidate-static-validation-rules-kg16.md` | 复核 KG-17 所依据的规则边界 |
| KG-15 registry candidate JSON | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 确认 registry candidate 当前状态 |
| KG-15 review | `docs/zdoc-kg-disabled-registry-candidate-entity-creation-kg15-review.md` | 承接 docs-only、非正式 registry、不可自动读取结论 |
| KG-08 manifest candidate JSON | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 确认 linked path / manifest path 指向 |

## 3. KG-17 人工静态校验结论摘要

| 校验项 | KG-17 结论 | KG-18 处置 |
| --- | --- | --- |
| JSON 语法 | 通过 | 可作为 freeze 前置条件 |
| 必填字段 | 通过 | 无需补字段 |
| 禁止字段 | 通过 | 不需要清理字段 |
| linked / manifest path 指向 | 通过 | 可作为路径冻结依据 |
| `status` | `registry_candidate_only` | freeze 后保持不变 |
| `registration_status` | `not_registered` | freeze 后保持不变 |
| `source_mode` | `path_and_summary_only` | 继续禁止正文承载 |
| disabled flags | 通过 | 继续锁定为禁用 |
| `isolation_rules` | 通过 | 继续保留 |
| `pre_registration_rules` | 通过 | 继续保留 |
| `manual_authorization_required` | 通过 | 继续要求人工授权 |
| RAG / prompt / system instruction registry 隔离 | 通过 | 继续隔离 |
| system instruction 类内容 | 不得转为 system instruction | 边界继续有效 |
| 青天评标 / 满分门控类内容 | 不得作为 evidence 或 scoring basis | 边界继续有效 |

KG-17 未发现 blocker、major 或 minor 问题。KG-17 的唯一 note 是当前仍为人工静态校验报告，尚无真实 validator；该 note 符合 KG-17/KG-18 docs-only 边界，不构成 freeze blocker。

## 4. KG-15 Registry Candidate 当前状态确认

| 字段 | 当前状态 | KG-18 结论 |
| --- | --- | --- |
| `registry_candidate_id` | `zdoc-kg-pilot-qn-index-municipal-bridge-kg01-disabled-registry-candidate` | 可作为候选 ID |
| `manifest_candidate_path` | 指向 docs 下 KG-08 frozen manifest candidate | 仅作溯源 |
| `linked_manifest_candidate_path` | 指向同一 docs 下 KG-08 frozen manifest candidate | 仅作溯源 |
| `pilot_direction` | `全能索引 + 市政桥梁 KG01` | 与试点方向一致 |
| `backup_direction` | `全能索引 + 医院装修改造 KG02` | 仅作备选记录 |
| `source_mode` | `path_and_summary_only` | 禁止正文承载 |
| `status` | `registry_candidate_only` | 仍为 registry candidate 候选 |
| `registration_status` | `not_registered` | 未注册 |
| `activation_requires` | `manual_authorization_after_KG15_review` | 后续必须人工授权 |
| `manual_authorization_required` | `true` | 人工授权必需 |
| `risk_level` | `R2` | 仅为候选风险，不代表可运行 |

KG-18 不对 KG-15 registry candidate JSON 做任何修改。若未来需要调整字段、风险等级、路径、隔离规则或授权条件，应另行授权，并重新执行静态校验。

## 5. 问题分级与处置

| 级别 | 是否存在 | 说明 | KG-18 处置 |
| --- | --- | --- | --- |
| Blocker | 否 | 未发现阻止 freeze 的结构性问题 | 允许进入 freeze gate 判断 |
| Major | 否 | 未发现注册、启用、运行链路、证据化或评分依据化风险 | 保持全部禁用 |
| Minor | 否 | 未发现需立即修正的字段或文档问题 | 不修改 JSON |
| Note | 是 | 尚无真实 validator，且 KG-18 不创建 validator | 后续若需要 validator，必须另行授权 |

问题处置建议：保留 KG-15 registry candidate JSON 原样冻结为 docs-only disabled registry candidate。KG-18 不进行字段修正、补写、重排或格式化。

## 6. Registry Candidate Freeze 判定条件

registry candidate 进入 freeze gate 至少满足以下条件：

1. KG-15 registry candidate JSON 语法有效；
2. KG-16 必填字段均存在；
3. KG-16 禁止字段均不存在；
4. `manifest_candidate_path` 与 `linked_manifest_candidate_path` 均存在；
5. 两个 path 均指向 docs 下 KG-08 frozen manifest candidate；
6. `status="registry_candidate_only"`；
7. `registration_status="not_registered"`；
8. `source_mode="path_and_summary_only"`；
9. `enabled=false`；
10. `runtime_access=false`；
11. `rag_enabled=false`；
12. `evidence_enabled=false`；
13. `scoring_enabled=false`；
14. `prompt_registry_enabled=false`；
15. `system_instruction_registry_enabled=false`；
16. `writeback_enabled=false`；
17. `export_enabled=false`；
18. `manual_authorization_required=true`;
19. `pre_registration_rules.pre_registration_status="draft_only"`;
20. `pre_registration_rules.approval_status="not_approved"`;
21. RAG / prompt / system instruction registry 隔离规则完整；
22. system instruction 类内容继续隔离；
23. 青天评标 / 满分门控类内容不得作为 evidence 或 scoring basis；
24. 未发现 blocker、major 或 minor 问题。

KG-18 判定：当前 KG-15 registry candidate 满足上述 freeze gate 条件，可冻结为 docs-only、disabled、not registered 的 registry candidate。

## 7. Freeze 后状态约束

freeze 后 registry candidate 仍必须保持以下状态：

| 约束 | 必须状态 |
| --- | --- |
| `status` | `registry_candidate_only` |
| `registration_status` | `not_registered` |
| `source_mode` | `path_and_summary_only` |
| `enabled` | `false` |
| `runtime_access` | `false` |
| `rag_enabled` | `false` |
| `evidence_enabled` | `false` |
| `scoring_enabled` | `false` |
| `prompt_registry_enabled` | `false` |
| `system_instruction_registry_enabled` | `false` |
| `writeback_enabled` | `false` |
| `export_enabled` | `false` |
| `manual_authorization_required` | `true` |
| `pre_registration_status` | `draft_only` |
| `approval_status` | `not_approved` |

freeze 不等同于真实 registry 创建、manifest 注册、RAG 接入、prompt registry 接入、system instruction registry 接入、生成链启用、证据链启用、评分链启用、写回或导出。

## 8. Path 指向结论

KG-18 对 path 指向作出以下结论：

| 字段 | 当前值 | 结论 |
| --- | --- | --- |
| `manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 指向 docs 下 KG-08 frozen manifest candidate |
| `linked_manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 与 `manifest_candidate_path` 一致 |

该 path 只允许用于人工溯源和静态校验，不得用于：

1. 运行时读取；
2. 真实 registry 注册；
3. RAG corpus path；
4. prompt template source；
5. system instruction source；
6. evidence source；
7. scoring basis source；
8. writeback source；
9. export source。

## 9. Disabled Flags 锁定复核

KG-18 对 disabled flags 作出以下锁定复核：

| 字段 | 当前值 | KG-18 结论 |
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

任何将上述字段改为 `true` 的动作都不属于 KG-18 范围，也不得在未取得后续明确授权前执行。

## 10. RAG Registry 隔离结论

KG-18 确认 RAG registry 继续隔离：

1. `rag_enabled=false`；
2. `pre_registration_rules.rag_registry_forbidden=true`；
3. `isolation_rules` 包含 `rag_registry_disabled`；
4. 未发现 `rag_index`；
5. 未发现 `embedding_model`；
6. 未发现 `corpus_path`；
7. `manifest_candidate_path` 不得作为 RAG corpus path；
8. 不得生成或引用向量索引。

KG-18 不授权任何 RAG 接入。

## 11. Prompt Registry 隔离结论

KG-18 确认 prompt registry 继续隔离：

1. `prompt_registry_enabled=false`；
2. `pre_registration_rules.prompt_registry_forbidden=true`；
3. `isolation_rules` 包含 `prompt_registry_disabled`；
4. 未发现 `prompt_template`；
5. 未发现 `generation_prompt`；
6. 不得把 path 或 summary 改写成 prompt；
7. 不得通过 prompt registry 绕过 system instruction 隔离。

KG-18 不授权任何 prompt registry 接入。

## 12. System Instruction Registry 隔离结论

KG-18 确认 system instruction registry 继续隔离：

1. `system_instruction_registry_enabled=false`；
2. `pre_registration_rules.system_instruction_registry_forbidden=true`；
3. `isolation_rules` 包含 `system_instruction_registry_disabled`；
4. `isolation_rules` 包含 `system_instruction_sources_must_remain_quarantined`；
5. 未发现 `system_instruction` 正文字段；
6. 未发现系统指令原文；
7. 不得把 source summary 改写成隐性 system instruction；
8. 不得通过 prompt registry 绕过隔离。

KG-18 不授权任何 system instruction registry 接入。

## 13. System Instruction 类内容结论

KG-18 结论：system instruction 类内容不得转为 ZDoc system instruction。

本结论适用于：

1. KG-08 manifest candidate；
2. KG-15 registry candidate；
3. 后续可能出现的 pre-registration 或 registry 草案；
4. 全能索引相关资料；
5. 市政桥梁 KG01 试点资料；
6. 医院装修改造 KG02 备选资料；
7. 任何被识别为系统指令、执行命令、写回、导出、提交、覆盖或自动评分的内容。

## 14. 青天评标 / 满分门控结论

KG-18 结论：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

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

## 15. KG-19 授权条件

KG-19 不得自动进入。若 ChatGPT 总控决定继续，建议 KG-19 只能在明确人工授权后执行，并优先限定为以下 docs-only / static-only 事项之一：

1. 形成 registry candidate freeze record；
2. 设计 registry candidate 变更审计规则；
3. 设计 registry candidate freeze 签署字段；
4. 设计从 registry candidate 到未来注册态的门槛清单，但不执行注册；
5. 设计真实 validator 的伪代码或规格映射，但不创建脚本；
6. 复核是否需要补充 `frozen_at`、`frozen_by`、`freeze_reason`、`freeze_source_commit` 等字段，但不得直接修改 JSON。

KG-19 如涉及以下动作，必须取得更高等级明确授权：

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

## 16. KG-18 最终结论

KG-18 最终结论如下：

1. KG-17 人工静态校验未发现 blocker、major 或 minor 问题；
2. KG-15 registry candidate JSON 当前仍为 `registry_candidate_only`、`not_registered`、disabled 状态；
3. `manifest_candidate_path` 与 `linked_manifest_candidate_path` 指向 docs 下 KG-08 frozen manifest candidate；
4. registry candidate 可冻结为非运行态、不可自动读取、不可注册、不可启用的 docs candidate；
5. freeze 后仍不得进入真实 registry、RAG、prompt registry、system instruction registry、生成链、证据链、评分链或写回链；
6. RAG registry、prompt registry、system instruction registry 继续隔离；
7. system instruction 类内容继续不得转为 system instruction；
8. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
9. KG-19 需要 ChatGPT 总控再次人工授权，不得自动进入。
