# ZDoc KG-21 Frozen Registry Candidate Pre-Registration Authorization Disposition

## 1. KG-21 执行摘要

KG-21 是对 KG-20 预注册就绪性复核后的 docs-only 授权处置归档。本步骤只记录授权处置结论、no-registration 边界、当前状态锁定、KG-08 manifest candidate 与 KG-15 registry candidate 的对应关系，以及 KG-22 后续授权条件。

KG-21 不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON，不创建 validator，不注册 manifest，不创建真实 registry 文件，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包，不进入 ZDoc 运行链路。

KG-21 结论：KG-15 frozen registry candidate 当前只允许继续保留为 docs-only frozen registry candidate。KG-21 不授权 manifest 注册，不授权真实 registry 创建，不授权 RAG / prompt registry / system instruction registry 接入，不授权 evidence 化、评分依据化、写回、导出或运行链路读取。

## 2. KG-20 预注册就绪性复核结论承接

KG-20 将“预注册就绪”限定为文档层面的 readiness，不代表可以注册。KG-21 继承以下 KG-20 结论：

| KG-20 结论 | KG-21 处置 |
| --- | --- |
| KG-19 freeze 结论继续成立 | 继续保持 frozen registry candidate 状态 |
| KG-15 registry candidate 仍为 `registry_candidate_only` | 不升级为 registered / active / runtime |
| KG-15 registry candidate 仍为 `not_registered` | 不注册 manifest，不注册 registry |
| KG-15 registry candidate 仍保持 disabled | 所有 disabled flags 继续为 `false` |
| KG-08 manifest candidate 仍为 `candidate_only` 与 `not_registered` | 不注册 manifest candidate |
| `manifest_candidate_path` 与 `linked_manifest_candidate_path` 均指向 KG-08 manifest candidate | 只用于人工溯源和静态复核 |
| 不接入 RAG / prompt registry / system instruction registry | KG-21 不创建任何 registry 接入 |
| system instruction 类内容继续隔离 | 不创建 system instruction |
| 青天评标 / 满分门控类内容不得作为 evidence 或 scoring basis | 不证据化、不评分依据化 |
| KG-21 需要人工授权 | 本文件仅归档授权处置，不自动进入 KG-22 |

## 3. Frozen Registry Candidate 当前状态确认

| 项目 | 当前值 | KG-21 结论 |
| --- | --- | --- |
| registry candidate 文件 | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 继续作为 docs-only 候选实体 |
| `registry_candidate_id` | `zdoc-kg-pilot-qn-index-municipal-bridge-kg01-disabled-registry-candidate` | 仅为候选 ID |
| `manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 仅作 docs-only 溯源 |
| `linked_manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 与 manifest path 一致 |
| 试点方向 | `全能索引 + 市政桥梁 KG01` | 仅作试点候选方向 |
| 备选方向 | `全能索引 + 医院装修改造 KG02` | 仅作备选记录 |
| `source_mode` | `path_and_summary_only` | 不承载原文 |
| `status` | `registry_candidate_only` | 仍为 registry candidate 候选 |
| `registration_status` | `not_registered` | 仍未注册 |
| `manual_authorization_required` | `true` | 后续仍需人工授权 |
| `risk_level` | `R2` | 仍需人工复核，不代表可运行 |

KG-21 不对上述 JSON 做任何字段变更、格式化、补写或重排。

## 4. 本阶段授权处置结论

KG-21 的授权处置结论如下：

| 事项 | 处置结论 |
| --- | --- |
| 保留 KG-15 registry candidate | 允许，继续作为 docs-only frozen registry candidate |
| 注册 manifest | 不允许 |
| 创建真实 registry 文件 | 不允许 |
| 接入 RAG registry | 不允许 |
| 接入 prompt registry | 不允许 |
| 接入 system instruction registry | 不允许 |
| 启用 runtime access | 不允许 |
| 启用 retrieval / generation reference | 不允许 |
| 作为 evidence | 不允许 |
| 作为 scoring basis | 不允许 |
| 写回或导出 | 不允许 |
| 被 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回读取 | 不允许 |

结论：KG-21 只授权“继续保留冻结候选状态”，不授权任何注册、接入、启用或运行使用。

## 5. 暂不注册 Manifest 的原因

KG-21 暂不注册 manifest，原因如下：

1. KG-08 manifest candidate 当前仍为 `candidate_only`；
2. KG-08 manifest candidate 当前仍为 `registration_status="not_registered"`；
3. KG-08 manifest candidate 仅为 docs 下候选实体，不属于运行 manifest registry；
4. KG-08 manifest candidate 仍采用 `source_mode="path_and_summary_only"`；
5. KG-08 manifest candidate 的 source path 指向 `AI知识图谱大全` 原始路径，只能用于人工溯源；
6. KG-08 manifest candidate 不得作为 evidence、scoring basis、RAG corpus、prompt source 或 system instruction source；
7. KG-08 manifest candidate 尚未获得真实注册授权；
8. 当前没有真实 validator、注册撤销规则、运行读取隔离验证和回滚方案。

因此，KG-21 不允许将 KG-08 manifest candidate 注册为 manifest registry 条目。

## 6. 暂不创建真实 Registry 的原因

KG-21 暂不创建真实 registry，原因如下：

1. KG-15 registry candidate 当前仍为 `registry_candidate_only`；
2. KG-15 registry candidate 当前仍为 `registration_status="not_registered"`；
3. KG-15 registry candidate 是 docs-only 候选文件，不是运行配置；
4. `pre_registration_rules.pre_registration_status="draft_only"`；
5. `pre_registration_rules.approval_status="not_approved"`；
6. disabled flags 全部为 `false`，不具备运行读取权限；
7. 尚未定义真实 registry 的隔离验证、回滚、撤销和审计机制；
8. 尚未定义运行链路不可自动读取的技术防线；
9. 尚未形成针对 RAG / prompt / system instruction registry 的真实注册隔离测试；
10. 当前阶段目标是授权处置归档，不是实体注册实施。

因此，KG-21 不允许创建真实 registry 文件，也不允许把候选文件放入任何运行配置目录。

## 7. 暂不接入 RAG / Prompt / System Instruction Registry 的原因

KG-21 暂不接入三类 registry，原因如下：

| Registry 类型 | 暂不接入原因 |
| --- | --- |
| RAG registry | `rag_enabled=false`，未创建 corpus、index、embedding 或 retrieval 边界验证 |
| prompt registry | `prompt_registry_enabled=false`，未拆分 prompt pack，未完成人工审查，且禁止将 summary 改写为 prompt |
| system instruction registry | `system_instruction_registry_enabled=false`，系统指令类内容必须隔离，不得转为 system instruction |

额外原因：

1. 任何内容不得直接作为 evidence；
2. 青天评标 / 满分门控内容不得作为 scoring basis；
3. 全能索引仅能作为索引、术语、模板候选，不得直接参与生成；
4. 市政桥梁 KG01 仅为 knowledge anchor candidate，不得启用检索或生成；
5. 医院装修改造 KG02 仅为备选方向，不进入当前试点运行范围。

## 8. 状态锁定结论

KG-21 对核心状态作出以下锁定结论：

| 字段 | 锁定值 | 结论 |
| --- | --- | --- |
| `status` | `registry_candidate_only` | 锁定为候选态 |
| `registration_status` | `not_registered` | 锁定为未注册 |
| `source_mode` | `path_and_summary_only` | 锁定为路径与摘要模式 |
| `manual_authorization_required` | `true` | 后续仍需人工授权 |
| `pre_registration_status` | `draft_only` | 仍为预注册草案态 |
| `approval_status` | `not_approved` | 未获得批准 |

任何将上述状态升级为 `registered`、`active`、`runtime`、`approved`、`enabled` 或类似运行态的动作，均不属于 KG-21 授权范围。

## 9. KG-08 与 KG-15 对应关系复核

KG-21 复核 KG-08 manifest candidate 与 KG-15 registry candidate 的对应关系如下：

| 对应项 | KG-08 manifest candidate | KG-15 registry candidate | KG-21 结论 |
| --- | --- | --- | --- |
| 文件路径 | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 均位于 docs 下候选目录 |
| 主状态 | `candidate_only` | `registry_candidate_only` | 均为候选态 |
| 注册状态 | `not_registered` | `not_registered` | 均未注册 |
| source mode | `path_and_summary_only` | `path_and_summary_only` | 均不承载原文 |
| 试点方向 | `全能索引 + 市政桥梁 KG01` | `全能索引 + 市政桥梁 KG01` | 一致 |
| 备选方向 | `全能索引 + 医院装修改造 KG02` | `全能索引 + 医院装修改造 KG02` | 一致 |
| disabled flags | 全部 `false` | 全部 `false` | 均不启用 |
| 隔离规则 | 包含 not evidence / not scoring basis / system instruction quarantine | 包含三类 registry 隔离与 not evidence / not scoring basis | 继续隔离 |

对应关系只允许用于人工溯源、静态复核和 docs-only 授权处置，不得用于运行读取、真实注册、RAG 检索、prompt 构造、system instruction 注入、evidence 引用、scoring basis、写回或导出。

## 10. Disabled Flags 锁定结论

KG-21 对 disabled flags 作出以下锁定结论：

| 字段 | 锁定值 | KG-21 结论 |
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

KG-21 不允许任何 disabled flag 被改为 `true`。后续如需讨论启用，必须重新进入独立授权、风险复核、静态校验和回滚边界设计。

## 11. System Instruction 类内容隔离结论

KG-21 结论：system instruction 类内容继续隔离，不得转为 ZDoc system instruction。

本结论覆盖：

1. 全能索引相关资料；
2. 市政桥梁 KG01 试点资料；
3. 医院装修改造 KG02 备选资料；
4. KG-08 manifest candidate；
5. KG-15 registry candidate；
6. 后续任何 pre-registration、registration request、registry candidate 或 freeze record；
7. 任何含系统指令、执行命令、写回、导出、提交、覆盖、自动评分或满分门控倾向的内容。

KG-21 不允许新增 system instruction 字段，不允许复制系统指令原文，不允许将 source summary 改写成隐性 system instruction，不允许通过 prompt registry 绕过隔离。

## 12. 青天评标 / 满分门控隔离结论

KG-21 结论：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

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

## 13. KG-22 授权条件

KG-22 不得自动进入。若 ChatGPT 总控决定继续，KG-22 建议只能在明确人工授权后进入以下 docs-only / static-only 范围之一：

1. 设计 no-registration audit checklist；
2. 设计 registry candidate retention record；
3. 设计 registration denial record 草案；
4. 设计 future registration request 的人工审核表，但不创建真实 registry；
5. 设计真实 validator 的规则规格，但不创建脚本；
6. 设计运行 registry 禁止读取的静态边界文档；
7. 设计候选文件变更审计规则；
8. 复核是否需要继续暂停在 frozen candidate 阶段。

KG-22 如涉及以下任一动作，必须取得更高等级明确授权：

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

## 14. KG-21 最终记录

KG-21 最终记录如下：

1. KG-20 预注册就绪性复核结论继续成立；
2. KG-15 registry candidate 仅允许继续保留为 docs-only frozen registry candidate；
3. KG-21 暂不注册 manifest；
4. KG-21 暂不创建真实 registry；
5. KG-21 暂不接入 RAG / prompt registry / system instruction registry；
6. KG-15 registry candidate 继续保持 `registry_candidate_only`；
7. KG-15 registry candidate 继续保持 `registration_status="not_registered"`；
8. KG-15 registry candidate 继续保持 disabled；
9. KG-08 manifest candidate 与 KG-15 registry candidate 对应关系清晰，但只允许人工溯源；
10. 所有 disabled flags 继续锁定为 `false`；
11. system instruction 类内容继续隔离；
12. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
13. KG-22 需要 ChatGPT 总控再次人工授权，不得自动进入。
