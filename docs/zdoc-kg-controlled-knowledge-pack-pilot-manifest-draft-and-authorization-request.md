# ZDoc KG-04 Controlled Knowledge Pack Pilot Manifest Draft and Authorization Request

## 1. KG-04 执行摘要

本文件是 KG-04 的 docs-only 设计归档，用于在 KG-05 前形成受控知识包试点的 manifest 草案、试点条目清单、字段落地规则、人工审核规则和授权请求草案。

KG-04 不实施知识接入，不生成 manifest 实体文件，不复制原始知识图谱文件，不启用 RAG，不接入 prompt registry，不接入 system instruction registry，不启用任何知识包，不进入真实生成链。

首个试点固定为：

- `全能索引 + 市政桥梁 KG01`

备选试点为：

- `全能索引 + 医院装修改造 KG02`

试点目标是建立 ZDoc 内容输出锚点的受控清单和审核边界，而不是让知识图谱直接参与正式生成、评分或 evidence 链路。

## 2. KG-01 到 KG-03R 结论继承关系

KG-04 继承以下基线：

| 阶段 | 继承结论 | KG-04 使用方式 |
| --- | --- | --- |
| KG-01 | `AI知识图谱大全` 已完成只读盘点，文件具备系统指令、prompt、知识图谱、施工组织设计、青天评标、模板案例等多类内容 | 仅引用盘点结论和路径结构，不复制原文件 |
| KG-02 | 已形成初步分类、风险分级、manifest 草案和试点建议 | 作为 KG-04 条目筛选与风险隔离的初始依据 |
| KG-02R | 校正 RAG 候选数量、风险等级口径、其他专业拆分和 manifest 字段 | 作为 KG-04 最新分类基线 |
| KG-03 | 已设计 ZDoc 知识锚点架构、manifest schema、风险隔离规则和试点路线 | KG-04 沿用其分层架构 |
| KG-03R | 已将 KG-02R 修正纳入 KG-04 readiness 基线 | KG-04 按其边界仅设计草案，不接入系统 |

必须继续遵守的硬规则：

- 系统指令类不得原样作为 ZDoc system instruction。
- 青天评标 / 满分门控类不得直接作为评分依据。
- RAG 候选默认 `allow_retrieval=false`。
- 所有 manifest 条目默认 `enabled=false`。
- 任何条目不得直接作为 evidence。
- KG-04 不进入 KG-05 的实体落地。

## 3. 首个试点选择结论

首个试点选择：

- `全能索引 + 市政桥梁 KG01`

选择理由：

1. `全能` 适合作为跨专业索引、术语、模板候选来源，但不适合直接系统指令化。
2. `市政桥梁 KG01` 是专业边界较清晰的核心知识图谱文件，适合作为首个专业知识锚点候选。
3. 该组合能验证 `source_archive -> manifest_registry -> knowledge_pack candidate` 的受控链路设计。
4. 该组合避免一开始引入青天评标、满分门控、自动评分或写回类高风险内容。
5. 该组合可以优先验证专业术语、章节逻辑、工艺节点和施工组织设计内容锚点，而不触发生成链路。

KG-04 中，`全能` 仅作为索引、术语、模板候选；`市政桥梁 KG01` 仅作为 knowledge pack 候选；两者均默认不启用。

## 4. 备选试点

备选试点：

- `全能索引 + 医院装修改造 KG02`

备选理由：

1. 医院装修改造具备明确专业边界，适合验证接口、专项、医疗流程和装修改造工艺知识锚点。
2. 相比全能单独试点，备选路线更容易限定专业域。
3. 适合作为市政桥梁试点后的第二专业验证对象。

备选风险：

1. 医疗专项内容涉及专业边界、功能房间、洁污分流、院感控制等上下文，人工复核要求更高。
2. 不得将专业规范性表述直接变成系统指令或自动生成约束。
3. 默认仍应 `enabled=false`、`allow_retrieval=false`、`allow_generation_reference=false`。

## 5. 为什么不选择全能单独试点

`全能` 不适合单独作为首个试点，原因如下：

1. 覆盖面过宽，容易把索引、模板、术语、提示词、系统约束混在一起。
2. 含有 `FINAL` 等版本标签，存在版本并存和冲突风险。
3. 全能类内容容易被误用为全局系统指令，直接影响 ZDoc 输出边界。
4. 其价值更适合作为 source archive 索引、术语入口、模板候选，而不是单独进入生成链。
5. 单独试点无法充分验证专业 KG 文件对施工方案输出不跑题的约束效果。

因此 KG-04 仅允许 `全能` 作为索引和候选来源，不允许其作为 system instruction，不允许其直接参与生成。

## 6. 为什么暂不选择市政道路 KG01

暂不选择 `全能 + 市政道路 KG01` 作为首个试点，原因如下：

1. 市政道路与市政桥梁、市政管网、室外附属等专业边界容易交叉。
2. 道路专业常与交通组织、排水、照明、绿化、附属工程联动，需要更细的冲突组设计。
3. 若直接进入首批试点，容易把道路通用措施、专项工艺和评分响应混成一个候选包。
4. KG-04 先用边界更清晰的市政桥梁验证 manifest 规则，再扩展到市政道路更稳妥。

## 7. 为什么暂不选择污水处理厂 KG01

暂不选择 `全能 + 污水处理厂 KG01` 作为首个试点，原因如下：

1. 污水处理厂涉及市政给排水厂站、工艺设备、构筑物、管线、电气自控等多专业耦合。
2. 该类内容后续可能需要独立拆分为 `市政给排水厂站工程` 专业域。
3. 设备工艺和土建施工的正文上下文风险较高，直接试点容易造成知识包边界不清。
4. 应在 KG-05 或后续阶段先完成专业域拆分、manifest 标注和人工审核后再考虑接入草案。

## 8. 试点目标

KG-04 试点目标是建立内容输出锚点，不进入正式生成链。

允许验证的设计问题：

1. 原始资料如何只读登记到 source archive。
2. manifest 条目如何表达风险、冲突、审核和启用状态。
3. 全能索引如何仅作为术语、模板和导航候选。
4. 市政桥梁 KG01 如何作为专业 knowledge pack 候选。
5. 如何防止系统指令、青天评标和满分门控内容越权进入生成链。

不允许验证的事项：

1. 不允许真实检索。
2. 不允许真实生成引用。
3. 不允许系统指令化。
4. 不允许评分依据化。
5. 不允许 evidence 化。
6. 不允许向 output、job、export 写入产物。

## 9. 试点文件候选筛选原则

试点候选应满足以下原则：

1. 优先选择专业边界明确、文件用途清晰、非系统指令、非评分门控、非写回导出类文件。
2. 优先选择核心 KG、索引、术语、模板候选，而不是 prompt 或 system instruction。
3. 文件可进入 manifest 草案表，但不得生成 JSON / YAML / CSV / DB 等实体 manifest。
4. 文件可被标记为 `knowledge_pack_candidate` 或 `template_library_candidate`，但不得启用。
5. 所有条目默认 `enabled=false`。
6. 所有条目默认 `allow_retrieval=false`。
7. 所有条目默认 `allow_generation_reference=false`。
8. 所有条目默认 `allow_system_instruction=false`。
9. 所有条目默认 `human_review_required=true`。
10. 系统指令、青天评标、满分门控、自动评分、写回、导出、提交、覆盖类文件不得进入首批启用项。

## 10. 试点条目清单草案

以下仅为 docs 文档中的草案表，不是 manifest 实体文件。

| draft_id | original_path | source_root | normalized_name | professional_domain | content_class | recommended_target | risk_level | risk_reasons | conflict_group_id | duplicate_group_id | enabled | allow_retrieval | allow_generation_reference | allow_system_instruction | human_only | human_review_required | review_status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KG04-DRAFT-001 | `/Users/youfeini/Desktop/AI知识图谱大全/全能/00-HCX8-FINAL-KG-总索引版本说明.md` | `/Users/youfeini/Desktop/AI知识图谱大全` | `00-HCX8-FINAL-KG-总索引版本说明` | 全能通用 | `source_archive,index_candidate` | `source_archive,manifest_registry` | R2 | `version_label_FINAL,universal_index_requires_review` | `general_index_final_family` | `none` | false | false | false | false | true | true | `pending` | 仅作为索引和版本线索，不得作为系统指令或生成输入 |
| KG04-DRAFT-002 | `/Users/youfeini/Desktop/AI知识图谱大全/全能/06-HCX8-FINAL-KG-行业模块库.md` | `/Users/youfeini/Desktop/AI知识图谱大全` | `06-HCX8-FINAL-KG-行业模块库` | 全能通用 | `source_archive,terminology_or_domain_module_candidate` | `source_archive,manifest_registry,template_library_candidate` | R2 | `version_label_FINAL,domain_module_requires_review` | `general_domain_module_final_family` | `none` | false | false | false | false | true | true | `pending` | 可作为术语和行业模块候选，需人工拆分后再决定用途 |
| KG04-DRAFT-003 | `/Users/youfeini/Desktop/AI知识图谱大全/全能/09-HCX8-FINAL-KG-标准产物模板库.md` | `/Users/youfeini/Desktop/AI知识图谱大全` | `09-HCX8-FINAL-KG-标准产物模板库` | 全能通用 | `template_library_candidate` | `source_archive,manifest_registry,template_library_candidate` | R2 | `version_label_FINAL,template_candidate_requires_review` | `general_template_final_family` | `none` | false | false | false | false | true | true | `pending` | 仅作为模板候选，不得直接参与生成 |
| KG04-DRAFT-004 | `/Users/youfeini/Desktop/AI知识图谱大全/全能/14-HCX8-FINAL-KG-关键词回归样例与使用清单.md` | `/Users/youfeini/Desktop/AI知识图谱大全` | `14-HCX8-FINAL-KG-关键词回归样例与使用清单` | 全能通用 | `keyword_library_candidate,prompt_pack_quarantine` | `source_archive,manifest_registry,human_reference_only` | R2 | `version_label_FINAL,prompt_like_sample_requires_split` | `general_keyword_sample_final_family` | `none` | false | false | false | false | true | true | `pending` | 可人工参考关键词和样例，不得原样作为 prompt pack |
| KG04-DRAFT-005 | `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG01_市政桥梁工程核心知识图谱_上传版.md` | `/Users/youfeini/Desktop/AI知识图谱大全` | `KG01_市政桥梁工程核心知识图谱_上传版` | 市政桥梁 | `knowledge_pack_candidate,rag_corpus_candidate` | `source_archive,manifest_registry,knowledge_pack` | R2 | `version_label_uploaded,manual_review_required` | `municipal_bridge_kg01_uploaded_family` | `none` | false | false | false | false | true | true | `pending` | 首个专业试点锚点，仅作为 knowledge pack 候选 |
| KG04-BACKUP-001 | `/Users/youfeini/Desktop/AI知识图谱大全/医院装修改造/02_医院装修改造接口与医疗专项知识图谱.md` | `/Users/youfeini/Desktop/AI知识图谱大全` | `02_医院装修改造接口与医疗专项知识图谱` | 医院装修改造 | `backup_knowledge_pack_candidate,rag_corpus_candidate` | `source_archive,manifest_registry,knowledge_pack` | R2 | `medical_specialty_boundary_requires_review` | `hospital_renovation_kg02_medical_specialty_family` | `none` | false | false | false | false | true | true | `pending` | 备选试点，不进入首个试点启用范围 |

## 11. 明确排除出首批试点的文件类型

以下类型不得进入首批试点启用项，只能隔离或人工参考：

| 文件路径示例 | 排除原因 | 默认处置 |
| --- | --- | --- |
| `/Users/youfeini/Desktop/AI知识图谱大全/全能/04-HCX8-FINAL-INSTRUCTIONS-安徽青天AI施组GPT系统指令.md` | 系统指令类，存在越权成为 ZDoc system instruction 的风险 | R3，进入 `system_instruction_quarantine` |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/SYSTEM_市政桥梁工程青天施组系统指令_上传版.md` | 专业系统指令类，不得原样启用 | R3，进入 `system_instruction_quarantine` |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG03_青天AI类人评标门控知识图谱_上传版.md` | 青天评标门控类，不得直接参与评分 | R3，进入 `human_reference_only` |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG04_施组满分生成闭环知识图谱_上传版.md` | 满分生成闭环类，不得作为评分依据或生成强约束 | R3，进入 `human_reference_only` |
| `.git`、`.DS_Store`、`.sample`、`.gitignore` 等非知识内容 | 非知识内容或工具元数据 | R4，禁止整合 |

## 12. Manifest 字段落地草案

KG-04 不生成 manifest 实体文件，仅定义字段落地规则。

建议 KG-05 如获授权后，manifest 草案字段沿用以下结构：

| 字段 | 是否必填 | 规则 |
| --- | --- | --- |
| `file_id` | 是 | 稳定 ID，不依赖文件名变化；可由路径规范化后生成 |
| `original_path` | 是 | 记录原始绝对路径，不复制原文件 |
| `source_root` | 是 | 固定为 `/Users/youfeini/Desktop/AI知识图谱大全` |
| `normalized_name` | 是 | 去扩展名后的规范名称，保留版本标签 |
| `file_type` | 是 | 如 `md`、`txt`、`docx`、`pdf` |
| `file_size` | 是 | 只读记录字节大小 |
| `modified_time` | 是 | 只读记录原始修改时间 |
| `professional_domain` | 是 | 使用 KG-02R 专业域口径 |
| `content_class` | 是 | 系统指令、prompt、knowledge pack、RAG 候选、模板、人工参考等 |
| `source_category` | 是 | `source_archive`、`pilot_candidate`、`quarantine` 等 |
| `version_label` | 是 | 如 `FINAL`、`上传版`、`V2`、`V9`、`V34`、`V35` |
| `risk_level` | 是 | R0 到 R4；系统指令类默认不低于 R3 |
| `risk_reasons` | 是 | 数组或列表，记录触发风险的原因 |
| `conflict_group_id` | 是 | 同名、同类、跨专业、版本并存时必须记录 |
| `duplicate_group_id` | 否 | 疑似重复时填写 |
| `recommended_target` | 是 | 建议进入的架构层，不代表启用 |
| `enabled` | 是 | 默认 `false` |
| `allow_retrieval` | 是 | 默认 `false` |
| `allow_generation_reference` | 是 | 默认 `false` |
| `allow_system_instruction` | 是 | 默认 `false` |
| `human_only` | 是 | 默认 `true`，审核后才可调整 |
| `human_review_required` | 是 | 默认 `true` |
| `review_status` | 是 | 默认 `pending` |
| `reviewer` | 否 | 人工审核人 |
| `review_notes` | 否 | 审核说明 |
| `created_at` | 是 | manifest 条目创建时间 |
| `updated_at` | 是 | manifest 条目更新时间 |

## 13. Source Archive 索引规则

`source_archive` 是只读索引层，规则如下：

1. 只记录原始文件路径、元数据、分类和风险。
2. 不复制原文件。
3. 不移动原文件。
4. 不改名原文件。
5. 不从原文件生成知识包实体。
6. 默认不进入检索。
7. 默认不参与生成。
8. 默认不允许系统指令化。
9. 必须保留 `source_root` 和 `original_path` 以便人工溯源。

## 14. Risk / Conflict / Review 字段规则

风险字段规则：

| 风险等级 | 含义 | KG-04 默认处置 |
| --- | --- | --- |
| R0 | 可进入候选池，但仍需审核 | 本阶段不直接启用 |
| R1 | 需轻度清洗 | 本阶段不直接启用 |
| R2 | 需人工复核 | 允许进入试点草案表 |
| R3 | 隔离，不得自动进入生成链 | 仅可 quarantine 或 human reference |
| R4 | 禁止整合 | 不进入试点候选 |

冲突组规则：

1. 同名不同专业文件必须进入同一冲突组或专业化子冲突组。
2. `FINAL`、`上传版`、`V2`、`V9`、`V34`、`V35` 并存时必须记录版本冲突。
3. 系统指令类同名或近似同名文件必须进入 `system_instruction_*` 冲突组。
4. 青天评标门控、满分候选规则和评分项文件必须进入独立高风险冲突组。
5. `.git`、`.DS_Store`、`.sample`、`.gitignore` 不进入知识冲突组，直接按 R4 处理。

审核字段规则：

1. `human_review_required=true` 为默认值。
2. `review_status=pending` 为默认值。
3. 未完成审核前，不得将 `enabled` 改为 `true`。
4. 未完成审核前，不得将 `allow_retrieval` 改为 `true`。
5. 未完成审核前，不得将 `allow_generation_reference` 改为 `true`。
6. `allow_system_instruction` 对所有 AI 知识图谱原始文件默认并持续为 `false`，除非未来经独立改写、审查和授权。

## 15. 默认值规则

所有 KG-04 草案条目必须满足：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `enabled` | `false` | 不启用 |
| `allow_retrieval` | `false` | 不进入 RAG 检索 |
| `allow_generation_reference` | `false` | 不参与生成引用 |
| `allow_system_instruction` | `false` | 不进入系统指令 |
| `human_only` | `true` | 仅供人工查看 |
| `human_review_required` | `true` | 必须人工审核 |
| `review_status` | `pending` | 未审核 |

## 16. 人工审核流程

建议 KG-05 后续仍采用分步审核：

1. 路径审核：确认 `original_path` 是否仍存在，是否属于允许 source root。
2. 文件身份审核：确认文件类型、专业域、用途类别和版本标签。
3. 风险审核：判断是否含系统指令、写回、导出、提交、覆盖、自动评分、满分门控、敏感信息。
4. 冲突审核：检查同名、同专业、跨专业、版本并存、重复内容。
5. 目标层审核：决定仅归档、knowledge pack 候选、template 候选、RAG 候选、人工参考或隔离。
6. 权限审核：决定是否允许 retrieval、generation reference 或继续 human only。
7. 总控确认：任何启用动作必须由 ChatGPT 总控另行授权。

KG-04 不执行上述审核动作，只定义流程。

## 17. 系统指令隔离规则

系统指令类文件必须进入 `system_instruction_quarantine`，规则如下：

1. 默认风险等级不低于 R3。
2. 不得原样作为 ZDoc system instruction。
3. 不得进入首批试点启用项。
4. 不得写入 prompt registry。
5. 不得作为生成链的全局约束。
6. 后续如需使用，必须先重写为 ZDoc 专用的短规则片段，并经过人工审核、冲突检查和单独授权。
7. 即使后续改写，也不得包含写回、导出、提交、覆盖、自动评分、满分门控等动作指令。

## 18. Prompt Pack 隔离规则

prompt pack 类或疑似 prompt 类内容必须满足：

1. 默认不启用。
2. 必须拆短，不得整篇接入。
3. 必须去除写回、导出、提交、覆盖、自动评分、满分门控等动作。
4. 必须人工审核用途边界。
5. 不得直接作为 system instruction。
6. 不得作为 evidence。
7. 不得作为评分依据。
8. KG-04 仅允许标注为 `prompt_pack_quarantine` 或 `human_reference_only`。

## 19. 青天评标 / 满分门控限制规则

青天评标、类人评标门控、满分生成闭环、评分响应、评分项、满分候选规则等内容必须限制：

1. 默认风险等级不低于 R3。
2. 不得直接参与评分。
3. 不得作为 ZDoc 自动评分依据。
4. 不得作为 evidence。
5. 不得作为生成链强制目标。
6. 不得将“满分”作为系统优化目标。
7. 可作为人工理解评标关注点的参考资料，但必须与自动评分链隔离。

## 20. 不得作为 Evidence / 评分依据的规则

KG-04 草案中的所有条目均不得作为 evidence 或评分依据。

原因：

1. 文件来自知识图谱和提示体系，不等同于招标文件、规范原文、合同文件或可审计证据。
2. 其中可能包含经验性、策略性、生成性表述，不能替代项目事实依据。
3. 青天评标和满分门控内容可能引导评分导向，必须与真实评分依据隔离。
4. ZDoc 后续应区分 `knowledge_anchor`、`retrieval_reference`、`generation_reference`、`evidence` 和 `scoring_basis`。

KG-04 中，所有条目只能是 `knowledge_anchor_candidate` 或 `human_reference_only`，不得成为 `evidence` 或 `scoring_basis`。

## 21. KG-05 允许事项

如 ChatGPT 总控授权 KG-05，建议 KG-05 仅允许：

1. 创建 manifest 实体草案文件。
2. 设计试点条目清单的实体落地格式。
3. 设计 source archive 索引实体结构。
4. 落地 risk / conflict / review 字段。
5. 保持所有条目默认 `enabled=false`。
6. 保持所有条目默认 `allow_retrieval=false`。
7. 保持所有条目默认 `allow_generation_reference=false`。
8. 保持所有条目默认 `allow_system_instruction=false`。
9. 保持所有条目不 evidence 化。
10. 保持所有条目不评分依据化。
11. 只登记原始路径和元数据，不复制原文件。

## 22. KG-05 禁止事项

KG-05 即使获授权，也仍应禁止：

1. 不得复制原始知识图谱文件。
2. 不得生成知识包实体文件。
3. 不得接入 RAG。
4. 不得接入 prompt registry。
5. 不得接入 system instruction registry。
6. 不得启用任何知识包。
7. 不得让生成链直接使用。
8. 不得 evidence 化。
9. 不得评分依据化。
10. 不得运行 ZDoc 服务。
11. 不得运行 ZBid 服务。
12. 不得运行 Ollama。
13. 不得访问端口。
14. 不得调用 endpoint。
15. 不得触发 `/generate`、`/export_docx`、`/review/apply`。
16. 不得触发 ZBid 写回。
17. 不得生成 DOCX。
18. 不得写 output/job/export。
19. 不得进入真实使用阶段。

## 23. KG-05 授权请求草案

建议向 ChatGPT 总控提交以下 KG-05 授权请求：

> 请求授权执行 KG-05：ZDoc controlled knowledge pack pilot manifest entity draft。
>
> 目标是在 ZDoc 仓库中创建受控 manifest 实体草案文件，仅登记 `全能索引 + 市政桥梁 KG01` 首个试点条目及 `全能索引 + 医院装修改造 KG02` 备选条目所需的路径、元数据、风险、冲突和审核字段。
>
> KG-05 仅允许创建 manifest 实体草案文件，不得复制 `/Users/youfeini/Desktop/AI知识图谱大全` 中任何原始文件，不得生成知识包实体文件，不得接入 RAG，不得接入 prompt registry，不得接入 system instruction registry，不得启用任何条目，不得让生成链直接使用，不得 evidence 化，不得评分依据化，不得进入真实使用阶段。
>
> 所有 manifest 条目必须默认：
>
> - `enabled=false`
> - `allow_retrieval=false`
> - `allow_generation_reference=false`
> - `allow_system_instruction=false`
> - `human_only=true`
> - `human_review_required=true`
> - `review_status=pending`
>
> KG-05 完成后必须停止，不得自动进入 RAG、prompt、system instruction 或生成链接入阶段。

## 24. KG-04 结论

KG-04 建议可以进入 KG-05，但 KG-05 必须仍是受控 manifest 实体草案阶段。

KG-04 不建议立即进入任何知识包接入、RAG 接入、prompt registry 接入、system instruction registry 接入或真实生成阶段。

KG-04 最终试点结论：

- 推荐试点：`全能索引 + 市政桥梁 KG01`
- 备选试点：`全能索引 + 医院装修改造 KG02`
- 暂不推荐：`全能` 单独试点
- 暂不推荐：`全能 + 市政道路 KG01`
- 暂不推荐：`全能 + 污水处理厂 KG01`
