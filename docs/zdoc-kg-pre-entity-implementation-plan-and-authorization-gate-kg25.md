# ZDoc KG-25 Pre-Entity Implementation Plan and Authorization Gate

## 1. KG-25 执行摘要

KG-25 是 KG pre-registration packet 阶段关闭后的 docs-only 实体化前实施方案设计。本步骤承接 KG-24 阶段关闭结论，只设计未来如果进入实体化前准备时应采用的目录规划、字段冻结、字段映射、静态校验、人工复核、回退策略和授权门槛。

KG-25 不创建真实 manifest，不创建真实 registry，不创建 validator 脚本，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包，不运行服务，不访问端口或 endpoint，不触发生成、导出、review apply 或 ZBid 写回。

KG-25 结论：KG-08 manifest candidate 与 KG-15 registry candidate 可继续作为 docs-only、candidate-only、registry-candidate-only、not-registered、disabled 的受控资料包对象，用于后续人工审查和实体化前方案讨论。任何从候选态进入真实实体、真实注册或运行链路的动作，都必须在 KG-26 或后续步骤中重新获得 ChatGPT 总控明确授权。

## 2. KG-24 阶段关闭结论承接

KG-24 已确认 KG-08 至 KG-23 的受控预注册资料包完成最终验收处置并可关闭。KG-25 对该结论的承接如下：

| KG-24 关闭结论 | KG-25 承接方式 |
| --- | --- |
| KG-08 + KG-15 + KG-16 至 KG-23 可作为受控预注册资料包归档 | 作为实体化前方案设计的只读依据 |
| 资料包继续保持 docs-only、candidate-only、registry-candidate-only、not-registered、disabled | KG-25 不改变任何状态 |
| 阶段关闭不代表注册、不代表启用、不代表运行读取授权 | KG-25 继续执行 no-registration / no-runtime |
| 不注册 manifest、不创建真实 registry、不接入三类 registry | KG-25 仅设计未来路径，不实施 |
| 不得作为 evidence、scoring basis 或 ZBid 写回依据 | KG-25 继续锁定 |
| system instruction 类内容继续隔离 | KG-25 继续设计隔离层，不接入 system instruction registry |
| 青天评标 / 满分门控类内容继续隔离 | KG-25 继续设计参考边界，不进入评分 |
| KG-25 建议仅做实体化前实施方案设计 | 本文即为该 docs-only 方案 |

KG-25 不扩大 KG-24 授权范围。

## 3. KG-08 Manifest Candidate 当前状态

KG-08 manifest candidate 文件：

`docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`

当前状态确认：

| 字段或状态 | 当前值 | KG-25 结论 |
| --- | --- | --- |
| `status` | `candidate_only` | 继续锁定为候选态 |
| `registration_status` | `not_registered` | 继续锁定为未注册 |
| `source_mode` | `path_and_summary_only` | 只允许路径与摘要，不承载原文 |
| `pilot_direction` | `全能索引 + 市政桥梁 KG01` | 继续作为首个试点方向 |
| `backup_direction` | `全能索引 + 医院装修改造 KG02` | 继续作为备选方向 |
| `risk_level` | source 层为 `R2` | 仍需人工复核 |
| disabled flags | 全部 `false` | 不启用任何运行能力 |
| `sources.source_path` | 指向 `AI知识图谱大全` 原始路径 | 仅记录路径，不复制文件 |
| `sources.source_summary` | 仅为摘要 | 不搬运原文，不写系统指令 |

KG-25 不修改该 JSON，不新增字段，不调整 source list，不改变 disabled flags。

## 4. KG-15 Registry Candidate 当前状态

KG-15 registry candidate 文件：

`docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json`

当前状态确认：

| 字段或状态 | 当前值 | KG-25 结论 |
| --- | --- | --- |
| `status` | `registry_candidate_only` | 继续锁定为 registry 候选态 |
| `registration_status` | `not_registered` | 继续锁定为未注册 |
| `source_mode` | `path_and_summary_only` | 不承载原文 |
| `manifest_candidate_path` | 指向 KG-08 manifest candidate | 仅用于人工溯源 |
| `linked_manifest_candidate_path` | 指向同一 KG-08 manifest candidate | 链路一致 |
| `manual_authorization_required` | `true` | 后续必须人工授权 |
| `risk_level` | `R2` | 仍需人工复核 |
| disabled flags | 全部 `false` | 不启用任何运行能力 |
| `pre_registration_rules` | draft-only / forbidden rules | 不授权注册或运行 |

KG-25 不修改该 JSON，不创建真实 registry，不把 registry candidate 放入任何运行配置目录。

## 5. 实体化前目录规划建议

以下目录规划仅为未来授权后的设计建议，不在 KG-25 创建任何目录或文件。

| 规划层 | 建议位置 | 目的 | KG-25 边界 |
| --- | --- | --- | --- |
| pre-entity planning docs | `docs/kg-pre-entity-plans/` | 存放实体化前实施方案、签收表和回退设计 | 仅建议，不创建 |
| disabled manifest draft | `docs/kg-manifest-candidates/` | 保留 candidate-only / disabled JSON | 已存在候选文件，不修改 |
| disabled registry draft | `docs/kg-registry-candidates/` | 保留 registry-candidate-only / disabled JSON | 已存在候选文件，不修改 |
| validation rule docs | `docs/kg-validation-rules/` | 存放未来 validator 规则说明 | 仅建议，不创建 validator |
| review ledger docs | `docs/kg-review-ledgers/` | 存放人工审查签收和处置记录 | 仅建议，不创建 |
| runtime registry | 不建议在 KG-25 规划落地路径 | 真实运行注册表 | KG-25 禁止创建 |
| RAG corpus/index | 不建议在 KG-25 规划落地路径 | 运行检索语料或索引 | KG-25 禁止接入 |
| prompt registry | 不建议在 KG-25 规划落地路径 | 可执行 prompt 片段注册 | KG-25 禁止接入 |
| system instruction registry | 不建议在 KG-25 规划落地路径 | 系统指令注册 | KG-25 禁止接入 |

目录规划原则：实体化前文件应继续停留在 docs-only 候选区或方案区，不得进入 `backend`、`frontend`、`config`、运行配置目录、任务目录、输出目录、job 目录或任何会被 ZDoc 自动读取的位置。

## 6. 字段冻结原则

KG-25 建议将以下字段视为实体化前冻结字段。后续任何变更都必须经过人工复核和单独授权。

| 对象 | 冻结字段 | 冻结原因 |
| --- | --- | --- |
| KG-08 manifest candidate | `status` | 必须保持 `candidate_only`，防止被解释为真实 manifest |
| KG-08 manifest candidate | `registration_status` | 必须保持 `not_registered` |
| KG-08 manifest candidate | `source_mode` | 必须保持 `path_and_summary_only`，防止复制原文 |
| KG-08 manifest candidate | `disabled_flags` | 必须全部保持 `false` |
| KG-08 manifest candidate | `sources.source_path` | 仅允许原始路径引用，不复制文件 |
| KG-08 manifest candidate | `sources.source_summary` | 只允许摘要，不允许系统指令或正文搬运 |
| KG-08 manifest candidate | `isolation_rules` | 保持 no-runtime / no-evidence / no-scoring |
| KG-15 registry candidate | `status` | 必须保持 `registry_candidate_only` |
| KG-15 registry candidate | `registration_status` | 必须保持 `not_registered` |
| KG-15 registry candidate | `manifest_candidate_path` | 必须继续指向 docs 下 KG-08 candidate |
| KG-15 registry candidate | `linked_manifest_candidate_path` | 必须与 `manifest_candidate_path` 一致 |
| KG-15 registry candidate | `disabled_flags` | 必须全部保持 `false` |
| KG-15 registry candidate | `pre_registration_rules` | 保持 draft-only 和 forbidden 边界 |
| KG-15 registry candidate | `manual_authorization_required` | 必须保持 `true` |

冻结字段不等于永久不可变；它表示在 KG-25 范围内不得变更，并且后续变更必须通过新的授权步骤执行。

## 7. 字段映射原则

如果未来进入实体化前草案设计，字段映射必须遵守以下原则：

| 来源字段 | 未来草案字段建议 | 映射原则 |
| --- | --- | --- |
| `pilot_direction` | `pilot_scope.name` | 仅保留试点名称，不启用运行 |
| `backup_direction` | `pilot_scope.backup` | 仅保留备选说明 |
| `source_mode` | `source_policy.mode` | 必须保持 `path_and_summary_only` |
| `sources[].source_path` | `source_archive[].original_path` | 只记录原路径，不复制文件 |
| `sources[].source_summary` | `source_archive[].summary` | 只写摘要，不复制正文 |
| `sources[].risk_level` | `risk.level` | 不得降级，R2 仍需人工复核 |
| `sources[].domain_tags` | `domain.tags` | 只作人工分类，不作为路由依据 |
| `disabled_flags.enabled` | `access.enabled` | 必须保持 `false` |
| `disabled_flags.runtime_access` | `access.runtime` | 必须保持 `false` |
| `disabled_flags.rag_enabled` | `access.rag` | 必须保持 `false` |
| `disabled_flags.evidence_enabled` | `access.evidence` | 必须保持 `false` |
| `disabled_flags.scoring_enabled` | `access.scoring` | 必须保持 `false` |
| `disabled_flags.prompt_registry_enabled` | `registry.prompt.enabled` | 必须保持 `false` |
| `disabled_flags.system_instruction_registry_enabled` | `registry.system_instruction.enabled` | 必须保持 `false` |
| `disabled_flags.writeback_enabled` | `access.writeback` | 必须保持 `false` |
| `disabled_flags.export_enabled` | `access.export` | 必须保持 `false` |
| `isolation_rules` | `controls.isolation_rules` | 只能增强隔离，不得弱化 |
| `pre_registration_rules` | `controls.pre_registration_rules` | 继续作为禁止注册与禁止运行依据 |

字段映射不得引入 loader、runtime registry id、endpoint、job id、output path、export path、writeback target 或任何会触发运行链路的字段。

## 8. 静态校验策略

KG-25 仅设计静态校验策略，不创建 validator 脚本。未来如获授权，静态校验应至少覆盖以下规则：

1. JSON 语法有效；
2. KG-08 `status` 必须为 `candidate_only`；
3. KG-15 `status` 必须为 `registry_candidate_only`；
4. 两个 candidate 的 `registration_status` 必须为 `not_registered`；
5. 两个 candidate 的 `source_mode` 必须为 `path_and_summary_only`；
6. 所有 disabled flags 必须为 `false`；
7. `manual_authorization_required` 必须为 `true`；
8. `manifest_candidate_path` 与 `linked_manifest_candidate_path` 必须指向 docs 下 KG-08 candidate；
9. `source_path` 不得指向 ZDoc 运行配置目录；
10. `source_summary` 不得包含原文长段、系统指令正文、执行命令或评分门控规则；
11. `isolation_rules` 必须包含 no-runtime、not-evidence、not-scoring-basis；
12. `pre_registration_rules` 必须禁止 runtime registry、RAG registry、prompt registry、system instruction registry、evidence、scoring、writeback、export；
13. 不得出现 `enabled=true`、`runtime_access=true`、`rag_enabled=true`、`evidence_enabled=true`、`scoring_enabled=true`；
14. 不得出现 `prompt_registry_enabled=true` 或 `system_instruction_registry_enabled=true`；
15. 不得出现 `writeback_enabled=true` 或 `export_enabled=true`；
16. 不得出现 `/generate`、`/export_docx`、`/review/apply` 的运行绑定字段；
17. 不得出现 ZBid 写回目标；
18. 不得出现 `output`、`job`、`export` 写入路径；
19. 不得出现真实 manifest registration id；
20. 不得出现真实 registry activation id。

静态校验失败时，不允许进入任何实体化、注册、接入或运行步骤。

## 9. 人工复核策略

未来实体化前人工复核应至少包含以下检查项：

| 检查项 | 复核要求 | 失败处置 |
| --- | --- | --- |
| 范围复核 | 是否仍限于 `全能索引 + 市政桥梁 KG01`，备选是否仍为医院装修改造 KG02 | 暂停推进 |
| 状态复核 | 是否仍为 candidate-only / not-registered / disabled | 暂停推进 |
| source path 复核 | 是否只引用 `AI知识图谱大全` 原路径 | 禁止实体化 |
| source summary 复核 | 是否只写摘要，未复制原文 | 禁止实体化 |
| 风险复核 | R2 是否仍需人工复核，是否存在 R3/R4 未隔离内容 | 暂停推进 |
| system instruction 复核 | 是否存在系统指令原文或隐性系统指令 | 进入隔离 |
| 青天评标复核 | 是否存在评分依据、满分门控或 evidence 倾向 | 进入隔离 |
| disabled flags 复核 | 是否全部保持 `false` | 禁止进入下一步 |
| registry 边界复核 | 是否未创建真实 registry | 禁止进入下一步 |
| RAG 边界复核 | 是否未生成 corpus、embedding、index 或 retriever 配置 | 禁止进入下一步 |
| prompt 边界复核 | 是否未注册 prompt pack | 禁止进入下一步 |
| system instruction 边界复核 | 是否未进入 system instruction registry | 禁止进入下一步 |
| ZBid 边界复核 | 是否未生成写回目标或 review apply 绑定 | 禁止进入下一步 |

人工复核必须由 ChatGPT 总控或其明确授权的人工审核人完成。自动校验不得替代人工授权。

## 10. 回退策略

KG-25 建议未来实体化前采用以下回退策略：

1. 若候选 JSON 被误改，立即停止后续 KG 步骤，优先恢复候选 JSON 的冻结状态；
2. 若新增文件进入运行配置目录，立即停止并移出未来方案范围，不得加载；
3. 若出现 `enabled=true` 或任一运行 flag 被置为 `true`，立即判定为 blocker；
4. 若出现原文复制、系统指令原文或评分门控正文，立即进入隔离复核；
5. 若出现 RAG、prompt registry 或 system instruction registry 接入字段，立即判定为越界；
6. 若出现 endpoint、job、output、export 或 writeback 字段，立即判定为越界；
7. 若静态校验失败，禁止进入人工验收后的下一步；
8. 若人工复核未签收，禁止进入任何实体化；
9. 若 Git 工作树出现非目标文件变更，必须先收口变更范围；
10. 若后续授权描述不清，默认保持 KG-25 关闭状态，不进入 KG-26。

回退策略目标是保持资料包可审计、可冻结、可停止，而不是恢复到运行可用状态。

## 11. 不得复制 AI知识图谱大全 原文的约束

KG-25 明确：任何未来实体化前方案都不得复制 `AI知识图谱大全` 原文件或原文正文。

允许的信息类型：

1. 原始路径；
2. 文件名；
3. 文件类型；
4. 摘要；
5. 风险等级；
6. 专业标签；
7. 隔离规则；
8. 人工审核状态；
9. 是否允许进入后续候选；
10. 是否继续 disabled。

禁止的信息类型：

1. 原始文件全文；
2. 大段正文复制；
3. 系统指令原文；
4. prompt 原文长段；
5. 青天评标评分规则原文；
6. 满分门控规则原文；
7. 客户、账号、token、密钥或隐私信息；
8. 可直接用于生成、评分、写回或导出的运行参数；
9. 可被 loader 自动读取的 corpus 内容；
10. 任何绕过 `path_and_summary_only` 的内容。

## 12. RAG / Prompt Registry / System Instruction Registry 边界

KG-25 继续保持三类 registry 隔离：

| Registry 类型 | KG-25 边界 | 后续进入条件 |
| --- | --- | --- |
| RAG registry | 不创建 corpus，不建 embedding，不建 retriever，不启用 `rag_enabled` | 需要单独授权、静态校验、人工审核和运行隔离设计 |
| prompt registry | 不拆分 prompt pack，不注册 prompt，不启用 `prompt_registry_enabled` | 需要单独授权、prompt 清洗、人工审核和 forbidden action 检查 |
| system instruction registry | 不接入任何 system instruction，不启用 `system_instruction_registry_enabled` | 需要单独授权，但系统指令类默认隔离，不得原样启用 |

任何后续方案即使进入实体化前准备，也不得默认开启 retrieval、generation reference、prompt execution 或 system instruction injection。

## 13. System Instruction 类内容隔离方案

KG-25 建议 system instruction 类内容继续采用隔离层设计：

1. 所有系统指令类源文件默认进入 quarantine；
2. `全能` 仅可作为索引、术语、模板候选，不得作为 system instruction；
3. `市政桥梁 KG01` 仅作为 knowledge anchor candidate，不得转为 system instruction；
4. `医院装修改造 KG02` 仅作为备选方向，不得转为 system instruction；
5. source summary 不得写成可执行系统指令；
6. future registry candidate 不得增加 system instruction loader 字段；
7. prompt registry 不得作为系统指令绕行通道；
8. system instruction 原文不得复制进 ZDoc；
9. 任一文件若含写回、提交、导出、覆盖、自动评分或满分门控倾向，应默认隔离；
10. 隔离内容只能进入人工复核，不得直接参与生成链。

隔离结论：KG-25 不允许将任何 AI 知识图谱内容转为 ZDoc system instruction。

## 14. 青天评标 / 满分门控类内容隔离方案

KG-25 继续确认青天评标、评分响应、满分门控类内容的限制：

1. 不得作为 evidence；
2. 不得作为 scoring basis；
3. 不得作为自动评分规则；
4. 不得作为满分门控依据；
5. 不得作为复评优化依据；
6. 不得进入 `/review/apply`；
7. 不得写回 ZBid；
8. 不得进入导出链；
9. 不得影响评分结果；
10. 仅可作为人工参考候选或风险提示候选。

若未来需要处理此类内容，应先设计独立的人工参考资料库和风险标签，不得与 scoring chain 混用。

## 15. 实体化前实施路线建议

KG-25 建议未来如继续推进，应采用以下顺序：

1. KG-26：仅做实体化前实施方案二次复核与签收设计；
2. 后续步骤：设计真实 validator 规格，但不创建脚本；
3. 后续步骤：设计 candidate-to-draft 转换规则，但不执行转换；
4. 后续步骤：设计 manifest 实体草案位置和命名，但不创建真实 manifest；
5. 后续步骤：设计 registry 实体草案位置和命名，但不创建真实 registry；
6. 后续步骤：设计 rollback checklist；
7. 后续步骤：设计人工验收表；
8. 后续步骤：由 ChatGPT 总控决定是否进入真实实体创建授权。

该路线不包含任何运行接入、RAG 接入、prompt registry 接入、system instruction registry 接入、服务运行、endpoint 调用或正式生成使用。

## 16. KG-26 授权条件

KG-26 不得自动进入。若 ChatGPT 总控决定继续，建议 KG-26 仅限以下范围：

1. 新增一个 docs-only 二次复核或签收设计文件；
2. 继续读取 KG-25、KG-24、KG-23、KG-22 以及 KG-08 / KG-15 candidate；
3. 继续校验 KG-08 与 KG-15 JSON 语法；
4. 继续确认 candidate-only / registry-candidate-only / not-registered / disabled；
5. 继续设计实体化前静态检查和人工签收流程；
6. 继续禁止真实 manifest、真实 registry、真实 validator；
7. 继续禁止 RAG / prompt registry / system instruction registry；
8. 继续禁止服务、端口、endpoint、生成、导出、review apply 和 ZBid 写回。

KG-26 如需突破上述任一边界，必须由 ChatGPT 总控给出新的、更高等级明确授权。

## 17. KG-25 最终记录

KG-25 最终记录如下：

1. 已承接 KG-24 阶段关闭结论；
2. 已确认 KG-08 manifest candidate 继续保持 `candidate_only`、`not_registered`、disabled；
3. 已确认 KG-15 registry candidate 继续保持 `registry_candidate_only`、`not_registered`、disabled；
4. 已提出实体化前目录规划建议，但未创建目录；
5. 已提出字段冻结和字段映射原则；
6. 已提出静态校验、人工复核和回退策略；
7. 已确认不得复制 `AI知识图谱大全` 原文；
8. 已确认不得接入 RAG / prompt registry / system instruction registry；
9. 已确认 system instruction 类内容继续隔离；
10. 已确认青天评标 / 满分门控类内容继续隔离；
11. 已明确 KG-26 授权条件；
12. KG-25 不进入 KG-26。
