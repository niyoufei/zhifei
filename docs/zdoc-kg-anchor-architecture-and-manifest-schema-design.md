# ZDoc 知识锚点架构与 manifest schema 设计

## 1. 背景与边界

本文是 KG-03 docs-only 架构设计归档，用于承接 KG-01 与 KG-02 的只读盘点结论，设计 ZDoc 后续知识锚点体系、manifest schema、风险隔离规则、知识包分层与 KG-04 受控接入授权请求草案。

本文件仅为方案文档，不生成 manifest 实体文件，不复制 `/Users/youfeini/Desktop/AI知识图谱大全` 中的任何原始资料，不接入 RAG、prompt registry 或 system instruction registry，不改变 ZDoc 运行链、评分链、导出链、写回链或任何 endpoint 行为。

## 2. KG-01 / KG-02 结果摘要

KG-01 对 `/Users/youfeini/Desktop/AI知识图谱大全` 完成只读盘点，确认该目录存在，总文件数约 170，总目录数约 49，总大小约 5.4M。排除 `.git`、`.DS_Store` 与 `.sample` 等非业务内容后，业务候选文件约 131 个，核心文件类型为 `.md`。

KG-02 完成分类治理、风险分级与 manifest 草案分析，结论如下：

- 系统指令候选：24 个。
- prompt pack 候选：4 个。
- 知识图谱 / schema 候选：86 个。
- 施工组织设计 / RAG 候选：43 个。
- 青天评标 / 评分响应候选：59 个。
- 模板 / 案例库候选：22 个。
- 约 123 个文件为 Medium 风险。
- 系统指令类不得原样作为 ZDoc system instruction。
- 青天评标 / 满分门控类不得作为自动评分依据。
- 后续必须先建立 manifest、风险分级、冲突组、隔离层与受控接入架构。

## 3. 知识锚点定位

AI知识图谱大全中的材料应定位为 ZDoc 内容输出的“知识锚点”，而不是直接驱动生成、评分或写回的运行时指令。

知识锚点的用途是：

- 约束施工组织设计内容方向，减少空话、套话、官话。
- 为专业工艺、施工流程、质量安全、接口专项、章节模板提供候选参考。
- 为后续可控 RAG、模板库、prompt pack 和知识包接入提供来源清单。
- 为 ChatGPT 总控与人工审核提供文件级风险、用途、启用状态与冲突关系。

知识锚点不得承担的职责：

- 不得直接成为 system instruction。
- 不得直接作为 evidence。
- 不得直接触发生成、导出、写回、评分或 ZBid 回写。
- 不得绕过 preview-only、no-write、no-evidence 以及人工审核边界。

## 4. 总体架构设计

ZDoc 知识锚点体系建议分为八层：

1. `source_archive`
2. `manifest_registry`
3. `knowledge_pack`
4. `prompt_pack`
5. `system_instruction_quarantine`
6. `rag_corpus_candidate`
7. `template_library_candidate`
8. `human_reference_only`

各层之间只允许单向提升：原始来源先进入 `source_archive`，再由 `manifest_registry` 记录风险和权限。只有通过人工审核的条目，才可进入后续候选层。任何条目进入检索、生成引用或系统指令化之前，必须显式通过对应权限字段。

建议的受控流转：

```text
AI知识图谱大全
  -> source_archive 只读索引
  -> manifest_registry 一文件一记录
  -> 风险分级 / 冲突组 / 人工审核
  -> knowledge_pack / prompt_pack / rag_corpus_candidate / template_library_candidate
  -> KG-04 受控接入试点
```

## 5. 知识包分层设计

### 5.1 source_archive

`source_archive` 是原始资料只读索引层。

规则：

- 不复制原文件。
- 仅记录原始路径、文件名、类型、大小、修改时间等元数据。
- 默认不进入生成。
- 默认不进入检索。
- 不创建运行时 KG。
- 不写入 `backend/data/kg`。

### 5.2 manifest_registry

`manifest_registry` 是治理总账层。

规则：

- 一文件一记录。
- 记录风险等级、冲突组、用途、启用状态、人工审核状态。
- 默认 `enabled=false`。
- 默认 `allow_retrieval=false`。
- 默认 `allow_generation_reference=false`。
- 默认 `allow_system_instruction=false`。
- 任何权限提升都必须有人工审核记录。

### 5.3 knowledge_pack

`knowledge_pack` 存放专业知识图谱候选。

适合内容：

- 专业工程知识图谱。
- 本体、节点、映射、标签体系、规则引擎候选。
- 工艺逻辑、接口专项、质量安全闭环、条款证据索引。

限制：

- 不直接作为 system instruction。
- 不直接作为 evidence。
- 不直接改写评分规则。
- 不自动激活为在线 KG。

### 5.4 prompt_pack

`prompt_pack` 存放可复用提示词片段。

规则：

- 必须拆短。
- 必须人工审核。
- 不允许含写回、提交、导出、覆盖、删除、强制执行等动作。
- 不允许覆盖 ZDoc 系统边界。
- 只能作为可选 prompt snippet，不得默认注入。

### 5.5 system_instruction_quarantine

`system_instruction_quarantine` 是系统指令隔离层。

规则：

- 所有系统指令类文件默认进入隔离层。
- 默认风险等级不低于 R3。
- 不得原样启用。
- 不得原样作为 ZDoc system instruction。
- 只能由人工抽取低风险、短规则、无动作语义的片段，再重新审核。

### 5.6 rag_corpus_candidate

`rag_corpus_candidate` 是可检索候选语料层。

规则：

- 默认不启用。
- 启用前需人工确认。
- 仅可作为参考检索来源。
- 检索结果不得直接作为 evidence。
- 检索结果进入生成前必须经过生成引用权限检查。

### 5.7 template_library_candidate

`template_library_candidate` 存放章节模板、评分词库、产物模板、输出样例。

规则：

- 后续可拆分为可选模板。
- 不自动覆盖招标文件目录。
- 不自动成为固定章节模板。
- 不能包含写回、导出、自动评分动作。

### 5.8 human_reference_only

`human_reference_only` 存放仅供人工查看的资料。

适用内容：

- 系统指令原文。
- 青天评标 / 满分门控原文。
- 版本冲突明显的 FINAL、V9、上传版混合资料。
- 含客户、联系人、账号、endpoint 或写回语义的文件。

规则：

- 不进入检索。
- 不参与生成。
- 不参与评分。
- 不进入 system instruction。

## 6. manifest schema 设计

建议 manifest 采用 JSONL 或 JSON array。KG-03 不生成实体文件，仅定义 schema。

字段定义：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `file_id` | string | 文件级稳定 ID，例如 `kgsrc-000001` |
| `original_path` | string | 原始绝对路径 |
| `source_root` | string | 来源根目录 |
| `normalized_name` | string | 规范化文件名 |
| `file_type` | string | 文件类型，例如 `md` |
| `file_size` | integer | 文件大小，单位 byte |
| `modified_time` | string | 原始文件修改时间 |
| `professional_domain` | string | 专业域，例如 `市政桥梁工程` |
| `content_class` | array | 内容类别，如 `knowledge_pack`、`rag_candidate` |
| `source_category` | string | 来源类别，如 `AI知识图谱大全` |
| `version_label` | string | 版本标签，如 `V9`、`FINAL`、`上传版`、`unknown` |
| `risk_level` | string | `R0` 至 `R4` |
| `risk_reasons` | array | 风险原因列表 |
| `conflict_group_id` | string | 冲突组 ID |
| `duplicate_group_id` | string | 重复组 ID |
| `recommended_target` | array | 建议目标层 |
| `enabled` | boolean | 是否启用，默认 false |
| `allow_retrieval` | boolean | 是否允许进入检索，默认 false |
| `allow_generation_reference` | boolean | 是否允许生成引用，默认 false |
| `allow_system_instruction` | boolean | 是否允许系统指令化，默认 false |
| `human_only` | boolean | 是否仅人工查看，默认 true |
| `human_review_required` | boolean | 是否需要人工审核，默认 true |
| `review_status` | string | `pending`、`approved`、`rejected`、`quarantined` |
| `reviewer` | string | 审核人 |
| `review_notes` | string | 审核说明 |
| `created_at` | string | 记录创建时间 |
| `updated_at` | string | 记录更新时间 |

示例记录：

```json
{
  "file_id": "kgsrc-000001",
  "original_path": "/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG01_市政桥梁工程核心知识图谱_上传版.md",
  "source_root": "/Users/youfeini/Desktop/AI知识图谱大全",
  "normalized_name": "municipal_bridge_kg01_core_knowledge_graph",
  "file_type": "md",
  "file_size": 12258,
  "modified_time": "2026-05-12 12:55:32",
  "professional_domain": "市政桥梁工程",
  "content_class": ["knowledge_pack", "rag_corpus_candidate"],
  "source_category": "AI知识图谱大全",
  "version_label": "上传版",
  "risk_level": "R2",
  "risk_reasons": ["version_label_uploaded", "manual_review_required"],
  "conflict_group_id": "domain_municipal_bridge_kg01",
  "duplicate_group_id": "",
  "recommended_target": ["knowledge_pack", "rag_corpus_candidate"],
  "enabled": false,
  "allow_retrieval": false,
  "allow_generation_reference": false,
  "allow_system_instruction": false,
  "human_only": true,
  "human_review_required": true,
  "review_status": "pending",
  "reviewer": "",
  "review_notes": "",
  "created_at": "2026-05-23T00:00:00+08:00",
  "updated_at": "2026-05-23T00:00:00+08:00"
}
```

## 7. 风险分级标准

### R0：可进入候选池，但仍需审核

适用：

- 普通专业术语、工艺节点、章节结构索引。
- 无系统指令语义。
- 无写回、导出、提交、覆盖、强制执行语义。
- 无隐私、账号、token、endpoint 风险。

默认权限：

- `enabled=false`
- `allow_retrieval=false`
- `allow_generation_reference=false`
- `allow_system_instruction=false`
- `human_review_required=true`

### R1：需轻度清洗

适用：

- 有少量格式、版本、标题、命名不一致问题。
- 内容可用，但需拆段、归一化术语或删除重复说明。

默认权限：

- 可进入候选池。
- 不得直接启用。
- 清洗后再由人工审核。

### R2：需人工复核

适用：

- `FINAL`、`V9`、`V35`、`上传版`、`增强`、`融合` 等版本语义混杂。
- 同名不同内容。
- 跨专业复用但边界不清。
- 可能用于 RAG 或 template library，但需要人工决定。

默认权限：

- 默认仅人工查看。
- 可作为 KG-04 试点候选，但不得自动启用。

### R3：隔离，不得自动进入生成链

适用：

- 系统指令类。
- 写回、导出、提交、覆盖、删除、强制执行类。
- 满分门控、自动评分、评分响应强约束类。
- endpoint、账号、客户、联系人等上下文风险类。

默认权限：

- `human_only=true`
- `allow_retrieval=false`
- `allow_generation_reference=false`
- `allow_system_instruction=false`
- 进入 `system_instruction_quarantine` 或 `human_reference_only`。

强制规则：

- 系统指令类默认不低于 R3。
- 写回 / 导出 / 提交 / 覆盖 / 满分门控类默认不低于 R3。
- 青天评标 / 满分门控类不得直接参与评分。

### R4：禁止整合

适用：

- `.git` 内部文件。
- `.DS_Store`。
- `.sample`。
- `.gitignore`。
- 非知识文件、缓存、临时文件、二进制无关文件。
- 明确含硬编码密钥、账号密码、个人敏感信息且无法清洗的内容。

默认权限：

- 不进入候选池。
- 不进入检索。
- 不参与生成。
- 不进入系统指令。

全局规则：

- 任何内容不得直接作为 evidence。
- 任何内容不得绕过 source hash、人工审核、preview-only、no-write、no-evidence 边界。

## 8. 冲突组规则

冲突组用于阻止重复、过时、相互矛盾或同名不同义的文件被同时启用。

冲突组生成依据：

- 同一专业下同类 KG 编号，例如 `KG01`、`KG02`。
- 同名文件但位于不同专业目录。
- 含 `FINAL`、`V2`、`V9`、`V34`、`V35`、`上传版` 等版本标签。
- 同一用途但内容定位不同，例如系统指令、模板、满分门控。
- 文件名高度相似但大小、修改时间或专业域不同。

冲突组启用规则：

- 一个 conflict group 同一时间最多允许一个条目进入可检索状态。
- 系统指令冲突组默认全部隔离。
- 版本冲突组必须由 ChatGPT 总控指定优先版本。
- 不允许自动按“最新修改时间”覆盖旧版本。

## 9. 系统指令隔离层设计

系统指令隔离层只保存系统指令类来源的治理记录，不保存运行时 system prompt。

进入条件：

- 文件名包含 `SYSTEM`、`系统指令`、`GPT系统指令`、`ChatGPT配置`、`INSTRUCTIONS`。
- 正文含最高优先级、强制执行、自动写回、自动导出、满分目标等语义。

处理规则：

- 默认 `risk_level=R3`。
- 默认 `human_only=true`。
- 默认 `allow_system_instruction=false`。
- 原文不得原样启用。
- 可由人工抽取短规则，但抽取后的规则必须形成新记录并重新审核。

## 10. prompt pack 管理规则

prompt pack 只管理短片段，不管理整篇长文。

准入规则：

- 必须短、明确、无副作用。
- 不得包含写回、提交、导出、覆盖、删除、调用 endpoint、触发服务等动作。
- 不得覆盖 ZDoc 全局边界。
- 不得含“自动满分”“直接应用”“无需人工确认”等语义。

启用规则：

- 先进入 `review_status=pending`。
- 人工审核后才可设置 `allow_generation_reference=true`。
- 仍不得设置 `allow_system_instruction=true`，除非另有专门授权。

## 11. knowledge pack 管理规则

knowledge pack 用于内容方向约束，不用于直接执行。

准入内容：

- 专业知识图谱。
- 工序、工艺、接口、规范、验收、质量安全、风险闭环。
- 章节结构、条款证据索引、术语体系。

限制：

- 不写入 `backend/data/kg`。
- 不激活 `active_kg`。
- 不触发 `/kg/upload`、`/kg/activate` 或 `/kg/search`。
- 不直接作为 evidence。
- 不参与自动评分。

## 12. RAG corpus 候选管理规则

RAG corpus 候选用于后续检索试点，但 KG-03 不接入 RAG。

候选准入：

- 专业工艺、接口专项、施工组织设计条款、质量安全闭环。
- 风险等级不高于 R2。
- 无系统指令、写回、导出、满分门控语义。

启用前置条件：

- 人工审核通过。
- 冲突组中无更高优先级文件。
- 明确 `allow_retrieval=true`。
- 明确仍不得作为 evidence。

## 13. template library 管理规则

template library 候选用于章节模板、评分词库、产物模板和输出样例。

规则：

- 模板必须可选，不得默认覆盖招标目录。
- 模板必须保留适用专业域。
- 模板必须标注来源和风险等级。
- 评分词库不得作为自动评分依据。
- 输出样例不得作为固定格式强制套用。

## 14. 青天评标 / 满分门控限制规则

青天评标、满分门控、评分响应类文件只能作为人工参考或候选知识锚点，不得直接参与评分链。

禁止：

- 不得作为自动评分依据。
- 不得改写评分主链。
- 不得作为 system instruction。
- 不得声明或承诺“满分”。
- 不得绕过用户项目资料和招标文件证据。
- 不得作为 evidence。

允许：

- 可作为人工审核参考。
- 可作为术语、常见评分关注点、章节检查项的候选来源。
- 经清洗后可进入 template library 或 knowledge pack，但默认不进入生成链。

## 15. 人工参考资料库设计

`human_reference_only` 是人工参考资料库。

适用资料：

- 原始系统指令。
- 青天评标 / 满分门控原文。
- 版本冲突明显资料。
- 中高风险资料。
- 含动作语义、endpoint 语义或客户上下文语义的资料。

权限：

- `enabled=false`
- `allow_retrieval=false`
- `allow_generation_reference=false`
- `allow_system_instruction=false`
- `human_only=true`

## 16. 文件启用状态设计

建议状态：

- `discovered`：只读发现，尚未审核。
- `indexed`：已进入 manifest，但未启用。
- `pending_review`：等待人工审核。
- `approved_for_reference`：允许人工参考。
- `approved_for_retrieval`：允许检索，但不允许生成引用。
- `approved_for_generation_reference`：允许作为生成引用来源，但不得作为 evidence。
- `quarantined`：隔离。
- `rejected`：拒绝整合。
- `retired`：过时停用。

状态提升必须单向、显式、可追溯。

## 17. 人工审核流程

建议流程：

1. 只读发现文件。
2. 写入 manifest 草案记录。
3. 自动初分内容类别、风险等级、冲突组。
4. ChatGPT 总控确认试点范围。
5. 人工逐文件审核。
6. 设置 `review_status`、`reviewer`、`review_notes`。
7. 如需清洗，生成清洗任务，不直接改原文件。
8. 如需接入，另走 KG-04 授权。

审核通过不代表自动启用。启用必须再显式设置对应权限字段。

## 18. 权限分级

### 可检索权限

字段：`allow_retrieval`

允许含义：

- 可进入受控检索候选。
- 不代表可参与生成。
- 不代表可作为 evidence。

### 可生成引用权限

字段：`allow_generation_reference`

允许含义：

- 可被生成链作为背景参考。
- 输出仍必须以用户上传项目资料、招标文件、清单、图纸为事实依据。
- 不得输出为 evidence。

### 可系统指令化权限

字段：`allow_system_instruction`

默认禁止。仅当满足以下条件时才可考虑：

- 不是原始系统指令全文。
- 已拆成短规则。
- 无写回、导出、评分、满分、强制执行语义。
- 通过专门人工审核。
- 另有明确授权。

## 19. 首个试点建议

### 路线 1：`全能` 单独试点

优点：

- 覆盖索引、术语、模板和治理门控。
- 适合做总体目录和术语清单。

风险：

- 含系统指令、评标门控、模板、关键词强化等混合语义。
- 不适合作为 system instruction 试点。

结论：可作为索引、术语、模板候选，不建议作为首个运行接入试点。

### 路线 2：`全能 + 市政桥梁 KG01`

优点：

- `市政桥梁 KG01` 更像专业核心知识图谱，范围相对清晰。
- 适合验证 manifest、专业域、冲突组和 knowledge pack 分层。
- 与 `全能` 的索引、术语、模板候选可形成轻量组合。

风险：

- 文件名含 `上传版`，应按 R2 人工复核。

结论：推荐作为首个试点候选之一。

### 路线 3：`全能 + 医院装修改造 KG02`

优点：

- `医院装修改造 KG02` 偏接口与医疗专项，适合验证专业工艺和接口专项锚点。
- 有利于减少泛泛而谈，强化医疗专项施工约束。

风险：

- 医院专项可能涉及更强专业边界，审核时需避免把参考资料误作项目事实。

结论：推荐作为首个试点候选之一。

### 路线 4：`全能 + 市政道路 KG01`

优点：

- 市政道路通用性较强。
- 适合验证施工工艺、资源节拍和质量安全锚点。

风险：

- KG-02 中相关市政道路文件含 V34.1/V35 等版本标签，需先处理版本冲突。

结论：可作为第二批候选。

### 路线 5：`全能 + 污水处理厂 KG01`

优点：

- 内容体量大，专业价值高。
- 覆盖工艺、设备、厂站接口等复杂场景。

风险：

- 文件体量最大，治理成本高。
- 更适合 manifest 成熟后进入，不适合作为首个小试点。

结论：暂缓。

### 推荐

首个试点建议优先选择：

1. `全能索引 + 市政桥梁 KG01`
2. `全能索引 + 医院装修改造 KG02`

`全能` 不作为 system instruction 试点，只作为索引、术语、模板候选。

## 20. KG-04 受控知识包接入授权请求草案

KG-04 如需继续，应由 ChatGPT 总控明确授权，并限制为受控知识包试点。

建议授权请求内容：

```text
执行 KG-04：ZDoc KG anchor 受控知识包试点接入

试点范围：
- 仅允许使用 KG-03 已批准的试点组合之一：
  1. 全能索引 + 市政桥梁 KG01
  2. 全能索引 + 医院装修改造 KG02

允许：
- 新增 manifest 草案实体文件；
- 仅记录元数据、风险、冲突组、启用状态；
- 不复制 AI知识图谱大全 原始文件正文；
- 不启用检索；
- 不参与生成；
- 不接入 system instruction；
- 不写 backend/data/kg；
- 不触发 endpoint。

禁止：
- 不得运行服务；
- 不得运行 Ollama；
- 不得访问端口；
- 不得调用 /generate、/export_docx、/review/apply；
- 不得触发 ZBid 写回；
- 不得生成 DOCX；
- 不得写 output/job/export；
- 不得把青天评标 / 满分门控作为自动评分依据；
- 不得把任何内容作为 evidence。

验收：
- 只新增授权范围内的 manifest 草案；
- 所有记录 enabled=false；
- allow_retrieval=false；
- allow_generation_reference=false；
- allow_system_instruction=false；
- human_review_required=true；
- git diff --check 通过。
```

KG-03 完成后应停止，不得自动进入 KG-04。
