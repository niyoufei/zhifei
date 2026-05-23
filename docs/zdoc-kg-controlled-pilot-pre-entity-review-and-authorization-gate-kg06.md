# ZDoc KG-06 Controlled Pilot Pre-Entity Review and Authorization Gate

## 1. KG-06 执行摘要

本文件是 KG-06 的 docs-only 复核与授权门槛归档，用于在任何 manifest disabled entity 实体草案出现之前，冻结字段口径、校验规则和 KG-07 进入条件。

KG-06 不创建真实 manifest 实体文件，不创建知识包实体文件，不复制 `AI知识图谱大全` 中任何文件，不接入 RAG、prompt registry 或 system instruction registry，不启用任何知识包，不进入 ZDoc 运行链路。

KG-06 只回答三个问题：

1. KG-04 的 manifest 草案是否仍可作为试点方向依据。
2. KG-05 的 disabled entity 字段设计是否足以作为实体前门槛。
3. KG-07 如需进入，必须满足哪些人工授权条件。

## 2. 复核文件

本阶段只读复核以下文件：

- `docs/zdoc-kg-controlled-knowledge-pack-pilot-manifest-draft-and-authorization-request.md`
- `docs/zdoc-kg-controlled-pilot-manifest-disabled-entity-design-kg05.md`

复核结果用于文档归档，不代表任何实体落地或运行授权。

## 3. KG-04 Manifest 草案复核摘要

KG-04 的核心结论仍成立：

1. 首个试点方向为 `全能索引 + 市政桥梁 KG01`。
2. 备选试点方向为 `全能索引 + 医院装修改造 KG02`。
3. `全能` 只作为索引、术语、模板候选，不得作为 system instruction。
4. `市政桥梁 KG01` 只作为 knowledge pack 候选，不得启用。
5. 青天评标 / 满分门控类内容不得作为评分依据。
6. 系统指令类内容必须进入隔离层，不得原样作为 ZDoc system instruction。
7. 所有条目默认 `enabled=false`、`allow_retrieval=false`、`allow_generation_reference=false`、`allow_system_instruction=false`。
8. 所有条目不得 evidence 化、不得评分依据化。

KG-06 对 KG-04 的复核判断：

| 复核项 | 结论 | KG-06 处置 |
| --- | --- | --- |
| 试点方向 | 成立 | 继续固定首个试点为 `全能索引 + 市政桥梁 KG01` |
| 备选方向 | 成立 | 继续保留 `全能索引 + 医院装修改造 KG02` |
| 草案条目 | 可作为设计依据 | 不转为实体文件 |
| 默认禁用 | 成立 | 在 KG-06 中升级为硬性门槛 |
| 系统指令隔离 | 成立 | 继续默认隔离 |
| 青天评标 / 满分门控限制 | 成立 | 只能人工参考，不得评分 |

## 4. KG-05 Disabled Entity 字段设计复核摘要

KG-05 已将 KG-04 的草案口径扩展为 disabled entity 字段设计，核心补充包括：

1. `runtime_access=false` 作为运行链路总开关。
2. `rag_enabled=false` 作为 RAG 检索禁用开关。
3. `evidence_enabled=false` 作为 evidence 禁用开关。
4. `scoring_enabled=false` 作为评分依据禁用开关。
5. `source_text_copied=false` 作为不得复制原文的实体级约束。
6. `entity_status=disabled_draft` 作为禁用态草案标识。

KG-06 对 KG-05 的复核判断：

| 复核项 | 结论 | KG-06 处置 |
| --- | --- | --- |
| disabled entity 定位 | 成立 | 只允许表达候选、风险、冲突、审核和禁用状态 |
| 字段覆盖 | 基本完整 | KG-06 冻结字段清单 |
| 运行权限 | 必须全 false | KG-06 设置硬性门槛 |
| source file 引用 | 成立 | 只允许路径与摘要，不复制正文 |
| 审核状态机 | 成立 | 不定义批准运行状态 |
| KG-07 条件 | 需继续收紧 | KG-07 必须人工授权，不得自动进入 |

## 5. 试点方向冻结

KG-06 冻结以下试点方向：

| 类型 | 组合 | KG-06 结论 |
| --- | --- | --- |
| 首个试点 | `全能索引 + 市政桥梁 KG01` | 保持为唯一首个试点 |
| 备选试点 | `全能索引 + 医院装修改造 KG02` | 保持为备选，不进入首个试点 |
| 暂不推荐 | `全能` 单独试点 | 覆盖面过宽，易误用为全局系统指令 |
| 暂不推荐 | `全能 + 市政道路 KG01` | 专业边界与市政桥梁、管网、附属工程交叉 |
| 暂不推荐 | `全能 + 污水处理厂 KG01` | 厂站、设备、土建、电气自控耦合度高 |

## 6. Manifest 字段冻结清单

KG-06 将 KG-05 字段冻结为实体前清单。KG-07 如获授权创建 disabled manifest entity 草案，不得删除、重命名或弱化以下字段。

| 字段 | 必填 | 冻结要求 |
| --- | --- | --- |
| `entity_id` | 是 | 稳定 ID，不依赖文件名显示变化 |
| `entity_status` | 是 | 固定为 `disabled_draft` |
| `source_root` | 是 | 固定记录允许源根路径 |
| `source_path` | 是 | 记录原始绝对路径 |
| `source_path_hash` | 是 | 仅用于辅助稳定识别，不替代原始路径 |
| `source_text_copied` | 是 | 必须为 `false` |
| `source_summary` | 是 | 只允许人工短摘要，不得复制原文段落 |
| `normalized_name` | 是 | 保留版本标签和专业线索 |
| `file_type` | 是 | 记录扩展名或识别类型 |
| `file_size` | 是 | 只读记录大小 |
| `modified_time` | 是 | 只读记录修改时间 |
| `professional_domain` | 是 | 记录专业域 |
| `domain_tag` | 是 | 记录短标签，例如 `general`、`municipal_bridge`、`hospital_renovation` |
| `content_class` | 是 | 记录用途类别 |
| `recommended_target` | 是 | 仅为推荐层，不代表启用 |
| `risk_level` | 是 | R0 到 R4 |
| `risk_reasons` | 是 | 至少一项风险理由 |
| `conflict_group_id` | 是 | 没有冲突也需记录 `none` |
| `duplicate_group_id` | 否 | 没有重复可记录 `none` |
| `enabled` | 是 | 必须为 `false` |
| `runtime_access` | 是 | 必须为 `false` |
| `rag_enabled` | 是 | 必须为 `false` |
| `prompt_registry_enabled` | 是 | 必须为 `false` |
| `system_instruction_enabled` | 是 | 必须为 `false` |
| `generation_reference_enabled` | 是 | 必须为 `false` |
| `evidence_enabled` | 是 | 必须为 `false` |
| `scoring_enabled` | 是 | 必须为 `false` |
| `zbid_writeback_enabled` | 是 | 必须为 `false` |
| `docx_export_enabled` | 是 | 必须为 `false` |
| `human_only` | 是 | 必须为 `true` |
| `human_review_required` | 是 | 必须为 `true` |
| `review_status` | 是 | 默认 `pending` |
| `reviewer` | 否 | 未审核时为空 |
| `review_notes` | 否 | 记录人工审核说明 |
| `created_at` | 是 | 草案创建时间 |
| `updated_at` | 是 | 草案更新时间 |

## 7. 字段校验要求

KG-07 如获授权创建实体草案，必须先通过以下字段校验。

### 7.1 Source Path

`source_path` 必须满足：

1. 必须位于 `/Users/youfeini/Desktop/AI知识图谱大全` 下。
2. 必须是只读引用，不得复制到 ZDoc。
3. 必须保留原始绝对路径。
4. 不得使用相对路径替代。
5. 不得指向 ZDoc 仓库内部复制件。

### 7.2 Source Summary

`source_summary` 必须满足：

1. 只能是人工短摘要。
2. 不得复制源文件正文。
3. 不得大段摘录原文。
4. 不得包含敏感原文。
5. 不得把摘要写成可直接 prompt 或 system instruction。

### 7.3 Risk Level

`risk_level` 必须满足：

1. 必须使用 R0、R1、R2、R3、R4。
2. 系统指令类默认不低于 R3。
3. 写回、导出、提交、覆盖、自动评分、满分门控类默认不低于 R3。
4. `.git`、`.DS_Store`、`.sample`、`.gitignore` 等非知识内容为 R4。
5. 青天评标 / 满分门控类不得因“仅参考”而降级为可运行。

### 7.4 Domain Tag

`domain_tag` 必须满足：

1. `全能索引` 使用 `general_index`。
2. `市政桥梁 KG01` 使用 `municipal_bridge_kg01`。
3. `医院装修改造 KG02` 使用 `hospital_renovation_kg02`。
4. 不得把跨专业全能内容误标为单一专业运行知识包。
5. 后续新增专业必须先经人工确认专业域。

### 7.5 Enabled And Runtime Flags

以下字段必须硬性校验为禁用：

| 字段 | 必须值 |
| --- | --- |
| `enabled` | `false` |
| `runtime_access` | `false` |
| `rag_enabled` | `false` |
| `prompt_registry_enabled` | `false` |
| `system_instruction_enabled` | `false` |
| `generation_reference_enabled` | `false` |
| `evidence_enabled` | `false` |
| `scoring_enabled` | `false` |
| `zbid_writeback_enabled` | `false` |
| `docx_export_enabled` | `false` |

任何一项不是 `false`，KG-07 应立即停止。

## 8. 硬性门槛

KG-06 冻结以下硬性门槛：

1. `runtime_access=false`：禁止运行链路访问。
2. `rag_enabled=false`：禁止 RAG 检索。
3. `evidence_enabled=false`：禁止 evidence 化。
4. `scoring_enabled=false`：禁止作为评分依据。
5. `system_instruction_enabled=false`：禁止系统指令化。
6. `prompt_registry_enabled=false`：禁止进入 prompt registry。
7. `generation_reference_enabled=false`：禁止作为生成引用。
8. `source_text_copied=false`：禁止复制源文件正文。

这些字段不是说明性字段，而是 KG-07 前置验收门槛。

## 9. 系统指令类内容隔离规则

系统指令类内容继续隔离：

1. 不得作为 ZDoc system instruction。
2. 不得进入 system instruction registry。
3. 不得进入 prompt registry。
4. 不得进入首个试点启用项。
5. 不得作为生成链全局约束。
6. 不得通过改名或摘要方式绕过隔离。

隔离示例：

| source_path | KG-06 处置 |
| --- | --- |
| `/Users/youfeini/Desktop/AI知识图谱大全/全能/04-HCX8-FINAL-INSTRUCTIONS-安徽青天AI施组GPT系统指令.md` | 继续隔离，`system_instruction_enabled=false` |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/SYSTEM_市政桥梁工程青天施组系统指令_上传版.md` | 继续隔离，`system_instruction_enabled=false` |

## 10. 青天评标 / 满分门控参考边界

青天评标 / 满分门控类内容只能作为人工参考边界，不得作为自动评分依据。

允许：

1. 作为 `human_reference_only` 登记。
2. 作为 `reference_retrieval_candidate` 登记但保持 `rag_enabled=false`。
3. 帮助人工理解评标关注点。

禁止：

1. 不得作为 scoring basis。
2. 不得作为 evidence。
3. 不得作为满分优化目标。
4. 不得作为生成链强制规则。
5. 不得触发自动评分、复评或 ZBid 写回。

隔离示例：

| source_path | KG-06 处置 |
| --- | --- |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG03_青天AI类人评标门控知识图谱_上传版.md` | 仅人工参考，`evidence_enabled=false`、`scoring_enabled=false` |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG04_施组满分生成闭环知识图谱_上传版.md` | 仅人工参考，`evidence_enabled=false`、`scoring_enabled=false` |

## 11. KG-07 可进入条件

KG-07 不得自动进入。只有 ChatGPT 总控明确授权后，才可进入。

KG-07 进入条件：

1. KG-06 文档已提交到 `main`。
2. KG-06 tag 已创建并推送。
3. 工作区干净。
4. ChatGPT 总控明确给出 KG-07 指令。
5. ChatGPT 总控明确指定唯一输出文件。
6. ChatGPT 总控明确说明 KG-07 是否允许创建真实 disabled manifest entity 草案文件。
7. KG-07 若允许创建实体草案，也只能创建 disabled 草案。
8. KG-07 不得复制原始知识图谱文件。
9. KG-07 不得生成知识包实体文件。
10. KG-07 不得接入 RAG / prompt registry / system instruction registry。
11. KG-07 不得启用任何知识包。
12. KG-07 不得运行服务、Ollama、端口或 endpoint。
13. KG-07 不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
14. KG-07 不得写 output/job/export。
15. KG-07 不得进入真实使用阶段。

## 12. KG-07 授权请求草案

如 ChatGPT 总控决定进入 KG-07，建议授权请求限定为：

> 请求授权执行 KG-07：ZDoc controlled pilot disabled manifest entity draft only。
>
> KG-07 仅允许在 ZDoc 仓库中创建一个 disabled manifest entity 草案文件，用于登记 `全能索引 + 市政桥梁 KG01` 首个试点和 `全能索引 + 医院装修改造 KG02` 备选试点的路径、摘要、风险、专业域、冲突组和禁用权限字段。
>
> KG-07 不得复制 `/Users/youfeini/Desktop/AI知识图谱大全` 中任何源文件，不得生成知识包实体文件，不得接入 RAG、prompt registry 或 system instruction registry，不得启用任何条目，不得让生成链读取，不得 evidence 化，不得评分依据化，不得进入真实使用阶段。
>
> 所有实体条目必须保持：
>
> - `enabled=false`
> - `runtime_access=false`
> - `rag_enabled=false`
> - `prompt_registry_enabled=false`
> - `system_instruction_enabled=false`
> - `generation_reference_enabled=false`
> - `evidence_enabled=false`
> - `scoring_enabled=false`
> - `source_text_copied=false`
>
> KG-07 完成后必须停止，等待 ChatGPT 总控审核，不得自动进入 KG-08。

## 13. KG-06 结论

KG-06 结论如下：

1. KG-04 manifest 草案可作为试点方向依据。
2. KG-05 disabled entity 字段设计可作为实体前字段基线。
3. 首个试点继续为 `全能索引 + 市政桥梁 KG01`。
4. 备选试点继续为 `全能索引 + 医院装修改造 KG02`。
5. KG-06 冻结了 manifest 字段、校验规则和硬性禁用门槛。
6. KG-07 仍需人工授权，不得自动进入。
7. KG-06 完成后必须停止，等待 ChatGPT 总控审核。
