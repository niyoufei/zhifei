# ZDoc KG-05 Controlled Pilot Manifest Review and Disabled Entity Design

## 1. KG-05 执行摘要

本文件是 KG-05 的 docs-only 设计归档，用于复核 KG-04 的受控知识包试点 manifest 草案，并定义后续可落地的 disabled entity 设计口径。

KG-05 不生成真实 manifest 实体文件，不生成知识包实体文件，不复制 `AI知识图谱大全` 中任何文件，不接入 RAG、prompt registry 或 system instruction registry，不启用任何知识包，不进入 ZDoc 运行链路。

本阶段只完成三件事：

1. 复核 KG-04 试点方向和草案条目是否符合禁用边界。
2. 设计 manifest disabled entity 的字段、默认值、风险隔离和审核规则。
3. 给出 KG-06 是否可进入的授权条件。

## 2. KG-04 文档复核结论

复核文件：

- `docs/zdoc-kg-controlled-knowledge-pack-pilot-manifest-draft-and-authorization-request.md`

复核结论：

1. KG-04 的首个试点方向仍成立：`全能索引 + 市政桥梁 KG01`。
2. KG-04 的备选试点方向仍成立：`全能索引 + 医院装修改造 KG02`。
3. KG-04 已明确 `全能` 只能作为索引、术语、模板候选，不得作为 system instruction。
4. KG-04 已明确 `市政桥梁 KG01` 只能作为 knowledge pack 候选，默认不启用。
5. KG-04 已明确 RAG 候选默认 `allow_retrieval=false`。
6. KG-04 已明确所有 manifest 条目默认 `enabled=false`。
7. KG-04 已明确系统指令类进入隔离层，不得原样作为 ZDoc system instruction。
8. KG-04 已明确青天评标 / 满分门控类不得作为评分依据。
9. KG-04 已明确任何条目不得作为 evidence。
10. KG-04 未实施接入，KG-05 也不得把 KG-04 草案升级为运行实体。

KG-05 对 KG-04 的校正意见：

1. KG-05 应将 `allow_retrieval=false` 进一步拆成 `rag_enabled=false` 与 `runtime_access=false`，避免“候选可检索”被误解为“运行时可检索”。
2. KG-05 应显式增加 `evidence_enabled=false` 和 `scoring_enabled=false`，避免知识锚点被误当证据或评分依据。
3. KG-05 应显式增加 `source_text_copied=false`，确保 source file 仅引用路径与摘要，不复制原文。
4. KG-05 应显式增加 `entity_status=disabled_draft`，标识该设计即使未来实体化也只能是禁用草案。

## 3. 试点方向确认

首个试点方向：

- `全能索引 + 市政桥梁 KG01`

首个试点的边界：

1. `全能` 仅作为 source archive 索引、术语入口、模板候选。
2. `全能` 不得作为 system instruction。
3. `全能` 不得直接参与生成。
4. `市政桥梁 KG01` 仅作为专业 knowledge pack 候选。
5. `市政桥梁 KG01` 默认不启用，不进入 RAG，不进入生成引用，不进入 evidence，不进入评分。

备选试点方向：

- `全能索引 + 医院装修改造 KG02`

备选试点的边界：

1. 仅在首个试点 manifest disabled entity 设计通过后，才允许进入备选草案。
2. 医院装修改造涉及医疗专项上下文，必须保持人工复核。
3. 默认不启用，不进入运行链路。

## 4. Disabled Entity 定位

`manifest disabled entity` 是后续可能落地的禁用态登记单元，不是知识包本体，也不是 RAG 语料，不是 prompt，不是 system instruction。

它只表达：

1. 某个源文件是否可被纳入候选清单。
2. 源文件属于哪个专业域和用途类别。
3. 源文件有哪些风险、冲突和审核要求。
4. 源文件默认禁止进入哪些运行权限。
5. 后续人工审核需要看哪些字段。

它不表达：

1. 不表达可直接生成。
2. 不表达可直接检索。
3. 不表达可作为证据。
4. 不表达可作为评分依据。
5. 不表达可作为系统指令。
6. 不包含源文件正文。

## 5. Manifest Disabled Entity 字段设计

以下是 KG-06 如获授权后可用于实体草案的字段设计。KG-05 仅定义字段，不创建实体文件。

| 字段 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `entity_id` | 是 | 无 | 禁用实体稳定 ID，例如 `kg05-pilot-0001` |
| `entity_status` | 是 | `disabled_draft` | 固定表示禁用草案，不允许直接运行 |
| `source_root` | 是 | `/Users/youfeini/Desktop/AI知识图谱大全` | 原始资料根路径 |
| `source_path` | 是 | 无 | 原始文件绝对路径，仅作引用 |
| `source_path_hash` | 是 | 无 | 用于稳定识别路径，不替代原始路径 |
| `source_text_copied` | 是 | `false` | 必须为 false，不复制原文 |
| `source_summary` | 是 | 无 | 人工摘要或短说明，不得大段摘录原文 |
| `normalized_name` | 是 | 无 | 规范文件名 |
| `file_type` | 是 | 无 | 文件类型 |
| `professional_domain` | 是 | 无 | 专业域，例如 `全能通用`、`市政桥梁` |
| `content_class` | 是 | 无 | 内容类别，例如 `index_candidate`、`knowledge_pack_candidate` |
| `recommended_target` | 是 | 无 | 推荐目标层，例如 `source_archive`、`knowledge_pack_candidate` |
| `risk_level` | 是 | 无 | R0 到 R4 |
| `risk_reasons` | 是 | 无 | 风险原因列表 |
| `conflict_group_id` | 是 | 无 | 冲突组 |
| `duplicate_group_id` | 否 | `none` | 疑似重复组 |
| `enabled` | 是 | `false` | 禁止启用 |
| `runtime_access` | 是 | `false` | 禁止运行时访问 |
| `rag_enabled` | 是 | `false` | 禁止 RAG 检索 |
| `prompt_registry_enabled` | 是 | `false` | 禁止进入 prompt registry |
| `system_instruction_enabled` | 是 | `false` | 禁止系统指令化 |
| `generation_reference_enabled` | 是 | `false` | 禁止生成引用 |
| `evidence_enabled` | 是 | `false` | 禁止 evidence 化 |
| `scoring_enabled` | 是 | `false` | 禁止作为评分依据 |
| `zbid_writeback_enabled` | 是 | `false` | 禁止 ZBid 写回 |
| `docx_export_enabled` | 是 | `false` | 禁止触发 DOCX 导出 |
| `human_only` | 是 | `true` | 默认仅人工查看 |
| `human_review_required` | 是 | `true` | 必须人工审核 |
| `review_status` | 是 | `pending` | 默认未审核 |
| `reviewer` | 否 | 空 | 审核人 |
| `review_notes` | 否 | 空 | 审核说明 |
| `created_at` | 是 | 无 | 实体草案创建时间 |
| `updated_at` | 是 | 无 | 实体草案更新时间 |

## 6. 默认禁用约束

所有 disabled entity 必须满足以下默认值：

| 权限字段 | 默认值 | 约束含义 |
| --- | --- | --- |
| `enabled` | `false` | 不启用知识条目 |
| `runtime_access` | `false` | 运行链路不可读取 |
| `rag_enabled` | `false` | 不进入 RAG 检索 |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_enabled` | `false` | 不进入 system instruction registry |
| `generation_reference_enabled` | `false` | 不作为生成引用 |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `zbid_writeback_enabled` | `false` | 不触发 ZBid 写回 |
| `docx_export_enabled` | `false` | 不触发 DOCX 导出 |
| `human_only` | `true` | 仅供人工查看 |
| `human_review_required` | `true` | 需要人工审核 |
| `review_status` | `pending` | 未审核 |

任何字段从 `false` 改为 `true` 都不得在 KG-05 或 KG-06 中发生，必须另设后续授权阶段。

## 7. Source File 引用规则

source file 仅允许引用路径与摘要，不得复制原文。

允许：

1. 记录 `source_root`。
2. 记录 `source_path`。
3. 记录 `normalized_name`。
4. 记录文件类型、大小、修改时间。
5. 记录人工摘要或短说明。
6. 记录风险、冲突、审核状态。

禁止：

1. 不得复制原文件到 ZDoc。
2. 不得移动、删除、重命名原文件。
3. 不得把原文大段写入 manifest。
4. 不得把原文转成知识包实体。
5. 不得把原文转成 prompt。
6. 不得把原文转成 system instruction。
7. 不得把原文写入 output、job、export。

## 8. KG-05 试点条目复核表

以下为 KG-04 草案条目的 KG-05 复核结果。该表仍是 docs-only 设计表，不是 manifest 实体文件。

| review_id | source_path | role | review_result | disabled_entity_decision |
| --- | --- | --- | --- | --- |
| KG05-REVIEW-001 | `/Users/youfeini/Desktop/AI知识图谱大全/全能/00-HCX8-FINAL-KG-总索引版本说明.md` | 全能索引 | 可保留为索引候选 | 可进入 disabled entity 草案，全部运行权限 false |
| KG05-REVIEW-002 | `/Users/youfeini/Desktop/AI知识图谱大全/全能/06-HCX8-FINAL-KG-行业模块库.md` | 行业模块候选 | 可保留为术语与专业入口候选 | 可进入 disabled entity 草案，需人工摘要，不复制正文 |
| KG05-REVIEW-003 | `/Users/youfeini/Desktop/AI知识图谱大全/全能/09-HCX8-FINAL-KG-标准产物模板库.md` | 模板候选 | 可保留为 template library 候选 | 可进入 disabled entity 草案，不启用生成引用 |
| KG05-REVIEW-004 | `/Users/youfeini/Desktop/AI知识图谱大全/全能/14-HCX8-FINAL-KG-关键词回归样例与使用清单.md` | 关键词 / prompt-like 候选 | 需继续隔离，防止原样 prompt 化 | 可进入 human reference only，全部运行权限 false |
| KG05-REVIEW-005 | `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG01_市政桥梁工程核心知识图谱_上传版.md` | 首个专业 knowledge pack 候选 | 首选试点文件成立 | 可进入 disabled entity 草案，`rag_enabled=false` |
| KG05-REVIEW-006 | `/Users/youfeini/Desktop/AI知识图谱大全/医院装修改造/02_医院装修改造接口与医疗专项知识图谱.md` | 备选专业 knowledge pack 候选 | 备选试点文件成立 | 可进入 disabled entity 草案，但不得进入首个试点启用范围 |

## 9. 系统指令类隔离规则

系统指令类内容必须隔离，不得作为 system instruction。

规则：

1. `system_instruction_enabled=false` 必须保持。
2. `allow_system_instruction` 或同义字段不得在 KG-05 / KG-06 中开启。
3. 系统指令类内容默认 R3 或更高风险。
4. 系统指令类文件不得进入首个试点启用项。
5. 系统指令类文件不得进入 prompt registry。
6. 系统指令类文件不得作为生成链全局约束。
7. 如未来需要使用，必须先改写为 ZDoc 专用短规则，再单独审核和授权。

隔离对象示例：

| source_path | 风险 | KG-05 处置 |
| --- | --- | --- |
| `/Users/youfeini/Desktop/AI知识图谱大全/全能/04-HCX8-FINAL-INSTRUCTIONS-安徽青天AI施组GPT系统指令.md` | 系统指令类 | `system_instruction_quarantine`，不启用 |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/SYSTEM_市政桥梁工程青天施组系统指令_上传版.md` | 专业系统指令类 | `system_instruction_quarantine`，不启用 |

## 10. 青天评标 / 满分门控限制规则

青天评标、满分门控、类人评标、评分响应、评分项、满分生成闭环类内容只能作为参考检索候选，且 KG-05 / KG-06 默认不得启用检索。

准确边界：

1. 可被记录为 `human_reference_only` 或 `reference_retrieval_candidate`。
2. 默认 `rag_enabled=false`。
3. 默认 `runtime_access=false`。
4. 默认 `evidence_enabled=false`。
5. 默认 `scoring_enabled=false`。
6. 不得作为自动评分依据。
7. 不得作为满分优化目标。
8. 不得作为生成链强制规则。

隔离对象示例：

| source_path | 风险 | KG-05 处置 |
| --- | --- | --- |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG03_青天AI类人评标门控知识图谱_上传版.md` | 青天评标门控 | 参考检索候选，但 `rag_enabled=false`，不得评分 |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG04_施组满分生成闭环知识图谱_上传版.md` | 满分生成闭环 | 参考检索候选，但 `scoring_enabled=false`，不得满分门控 |

## 11. Evidence 与 Scoring 禁止规则

KG-05 disabled entity 必须区分以下概念：

| 概念 | 是否允许 | 说明 |
| --- | --- | --- |
| `knowledge_anchor_candidate` | 允许登记 | 仅表示可能有助于约束内容方向 |
| `source_archive` | 允许登记 | 仅记录路径和元数据 |
| `human_reference_only` | 允许登记 | 仅供人工查看 |
| `reference_retrieval_candidate` | 允许登记 | 仅表示未来可能检索，默认不启用 |
| `evidence` | 不允许 | KG 文件不是招标文件、规范原文或可审计证据 |
| `scoring_basis` | 不允许 | KG 文件不得作为评分依据 |
| `system_instruction` | 不允许 | 原始系统指令类不得直接使用 |

`evidence_enabled=false` 和 `scoring_enabled=false` 必须作为实体级硬字段，不能只依赖说明文字。

## 12. Runtime Access 禁止规则

KG-05 disabled entity 即使未来实体化，也不得被 ZDoc 运行链路访问。

禁止运行入口：

1. 不得被 `/generate` 读取。
2. 不得被 `/export_docx` 读取。
3. 不得被 `/review/apply` 读取。
4. 不得被 ZBid 写回链路读取。
5. 不得被 prompt registry 读取。
6. 不得被 system instruction registry 读取。
7. 不得被 RAG 检索器读取。

`runtime_access=false` 是最高层开关。只要该字段为 false，其他运行权限即使被误配置，也不得生效。

## 13. 人工审核状态机

建议 disabled entity 使用以下审核状态：

| review_status | 含义 | 是否允许运行 |
| --- | --- | --- |
| `pending` | 未审核 | 否 |
| `needs_source_check` | 需要核对原始路径和摘要 | 否 |
| `needs_risk_review` | 需要风险复核 | 否 |
| `quarantined` | 隔离 | 否 |
| `human_reference_only` | 仅人工参考 | 否 |
| `approved_for_future_design` | 仅批准进入后续设计 | 否 |

KG-05 不定义任何“批准运行”的状态。

## 14. KG-06 可进入的授权条件

KG-06 只有在 ChatGPT 总控明确授权后才可进入。

进入 KG-06 前必须满足：

1. KG-05 文档已合并到 `main`。
2. KG-05 tag 已创建并推送。
3. 工作区干净。
4. ChatGPT 总控明确指定 KG-06 的唯一输出文件。
5. ChatGPT 总控明确说明是否允许创建真实 manifest disabled entity 草案文件。
6. 即使允许创建实体草案，也必须保持全部禁用字段为 false。
7. KG-06 仍不得复制原始知识图谱文件。
8. KG-06 仍不得生成知识包实体文件。
9. KG-06 仍不得接入 RAG / prompt registry / system instruction registry。
10. KG-06 仍不得启用任何知识包。
11. KG-06 仍不得运行服务、Ollama、端口或 endpoint。
12. KG-06 仍不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。

建议 KG-06 的授权标题为：

- `KG-06: create disabled manifest entity draft only`

KG-06 不应授权进入真实使用、检索、生成、评分或 evidence 链路。

## 15. KG-05 结论

KG-05 结论如下：

1. KG-04 manifest 草案方向成立。
2. 首个试点继续固定为 `全能索引 + 市政桥梁 KG01`。
3. 备选试点继续为 `全能索引 + 医院装修改造 KG02`。
4. KG-05 将 KG-04 的默认禁用口径扩展为 disabled entity 字段设计。
5. 后续如进入 KG-06，只能创建禁用态 manifest 草案实体，不得进入任何运行链路。
6. 当前阶段必须停止，等待 ChatGPT 总控审核。
