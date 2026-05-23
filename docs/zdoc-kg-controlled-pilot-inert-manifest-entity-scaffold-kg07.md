# ZDoc KG-07 Controlled Pilot Inert Manifest Entity Scaffold Design

## 1. KG-07 执行摘要

本文件是 KG-07 的 docs-only 设计归档，用于在不生成真实 manifest 文件的前提下，设计受控试点 inert manifest entity 的目录位置建议、命名规则、字段清单、伪结构和 KG-08 授权门槛。

KG-07 不创建真实 manifest 实体文件，不创建知识包实体文件，不复制 `AI知识图谱大全` 中任何文件，不接入 RAG、prompt registry 或 system instruction registry，不启用任何知识包，不进入 ZDoc 运行链路。

本文件中的示例结构只作为文档内伪结构，不得被视为可执行配置、JSON、YAML、CSV、DB 或真实 manifest 文件。

## 2. KG-04 / KG-05 / KG-06 复核承接结论

KG-07 继承以下结论：

| 来源阶段 | 复核结论 | KG-07 承接方式 |
| --- | --- | --- |
| KG-04 | manifest 草案方向成立，首个试点为 `全能索引 + 市政桥梁 KG01`，备选为 `全能索引 + 医院装修改造 KG02` | 仅作为 inert scaffold 的试点对象，不落地实体 |
| KG-05 | disabled entity 字段设计成立，必须增加 `runtime_access=false`、`rag_enabled=false`、`evidence_enabled=false`、`scoring_enabled=false` 等硬字段 | 作为字段清单基础 |
| KG-06 | 字段冻结、校验规则和硬性禁用门槛成立，KG-07 不得自动进入 KG-08 | KG-07 只做文档内 scaffold 设计 |

KG-07 不改变 KG-04、KG-05、KG-06 的任何禁用结论。

## 3. 试点方向

首个试点方向：

- `全能索引 + 市政桥梁 KG01`

首个试点边界：

1. `全能` 仅作为索引、术语、模板候选。
2. `全能` 不得作为 system instruction。
3. `全能` 不得直接参与生成。
4. `市政桥梁 KG01` 仅作为 knowledge pack candidate。
5. `市政桥梁 KG01` 默认 `enabled=false`、`runtime_access=false`、`rag_enabled=false`。

备选试点方向：

- `全能索引 + 医院装修改造 KG02`

备选试点边界：

1. 只作为 KG-08 以后可能登记的备选对象。
2. 不进入首个试点启用范围。
3. 不进入运行链路。
4. 不进入 evidence 或 scoring。

## 4. Inert Manifest Entity 定位

`inert manifest entity` 是一种惰性、不可运行、不可检索、不可生成、不可评分的登记单元。

它可以表达：

1. 源文件路径和短摘要。
2. 专业域、用途类别、风险等级和冲突组。
3. 默认禁用状态。
4. 人工审核状态。
5. 后续是否允许进入下一阶段设计。

它不能表达：

1. 可运行配置。
2. 可检索语料。
3. 可生成引用。
4. 可评分依据。
5. 可审计 evidence。
6. 可用 system instruction。
7. 源文件正文。

## 5. 目录位置建议

KG-07 仅提出目录位置建议，不创建目录、不创建 manifest 文件。

如 KG-08 获得人工授权，建议 future inert manifest entity 草案可放在以下位置之一：

| 候选位置 | 用途 | KG-07 结论 |
| --- | --- | --- |
| `docs/kg-manifest-drafts/` | docs-only 草案归档 | 推荐作为首选，因为仍属于文档归档层 |
| `docs/kg-manifest-drafts/pilot/` | 试点条目草案 | 可作为首个试点子目录 |
| `docs/kg-manifest-drafts/quarantine/` | 系统指令、青天评标、满分门控隔离草案 | 可作为隔离条目草案目录 |
| `knowledge/` | 知识包运行目录 | KG-07 不推荐，容易被误解为接入运行链路 |
| `backend/`、`config/`、`frontend/`、`tests/` | 代码或配置目录 | KG-07 禁止 |

推荐目录原则：

1. 只能在 docs 层表达 inert 草案。
2. 不得放入运行链路会读取的位置。
3. 不得放入配置目录。
4. 不得放入 backend、frontend、tests。
5. 不得创建真实知识包目录。

## 6. 命名规则建议

KG-08 如获授权创建真实 disabled manifest 文件，应使用清晰的禁用态命名。

建议命名格式：

- `kg-pilot-disabled-manifest-draft-v1.md`
- `kg-pilot-disabled-manifest-draft-v1.json.sample.md`
- `kg-pilot-inert-entity-draft-v1.md`

命名规则：

1. 必须包含 `disabled` 或 `inert`。
2. 必须包含 `draft`。
3. 不得使用 `active`、`enabled`、`runtime`、`production`。
4. 不得使用容易被程序自动识别为真实配置的扩展名，除非 KG-08 明确授权。
5. 若展示 JSON/YAML 伪结构，应放在 Markdown 文档代码块中，不得创建 `.json`、`.yaml`、`.yml`、`.csv` 或 DB 文件。

## 7. 字段清单

inert manifest entity 字段应沿用 KG-06 冻结清单。

| 字段 | 必填 | 默认值 / 规则 |
| --- | --- | --- |
| `entity_id` | 是 | 稳定 ID |
| `entity_status` | 是 | `disabled_draft` |
| `source_root` | 是 | `/Users/youfeini/Desktop/AI知识图谱大全` |
| `source_path` | 是 | 只记录来源路径 |
| `source_path_hash` | 是 | 路径稳定识别辅助值 |
| `source_text_copied` | 是 | `false` |
| `source_summary` | 是 | 只写摘要，不搬运原文件内容 |
| `normalized_name` | 是 | 规范名称 |
| `file_type` | 是 | 文件类型 |
| `file_size` | 是 | 只读记录 |
| `modified_time` | 是 | 只读记录 |
| `professional_domain` | 是 | 专业域 |
| `domain_tag` | 是 | 短标签 |
| `content_class` | 是 | 内容类别 |
| `recommended_target` | 是 | 仅为推荐层 |
| `risk_level` | 是 | R0 到 R4 |
| `risk_reasons` | 是 | 风险原因 |
| `conflict_group_id` | 是 | 冲突组 |
| `duplicate_group_id` | 否 | 无重复时为 `none` |
| `enabled` | 是 | `false` |
| `runtime_access` | 是 | `false` |
| `rag_enabled` | 是 | `false` |
| `prompt_registry_enabled` | 是 | `false` |
| `system_instruction_enabled` | 是 | `false` |
| `generation_reference_enabled` | 是 | `false` |
| `evidence_enabled` | 是 | `false` |
| `scoring_enabled` | 是 | `false` |
| `zbid_writeback_enabled` | 是 | `false` |
| `docx_export_enabled` | 是 | `false` |
| `human_only` | 是 | `true` |
| `human_review_required` | 是 | `true` |
| `review_status` | 是 | `pending` |
| `reviewer` | 否 | 空 |
| `review_notes` | 否 | 空 |
| `created_at` | 是 | 草案创建时间 |
| `updated_at` | 是 | 草案更新时间 |

## 8. 文档内伪结构示例

以下示例只是 Markdown 文档内的伪结构，不是 manifest 文件，不得复制为 JSON / YAML / CSV / DB 实体。

```text
inert_manifest_entity:
  entity_id: kg07-pilot-0001
  entity_status: disabled_draft
  source_root: /Users/youfeini/Desktop/AI知识图谱大全
  source_path: /Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG01_市政桥梁工程核心知识图谱_上传版.md
  source_text_copied: false
  source_summary: 市政桥梁核心知识图谱候选，仅用于人工理解专业锚点
  professional_domain: 市政桥梁
  domain_tag: municipal_bridge_kg01
  content_class: knowledge_pack_candidate
  recommended_target: source_archive_only
  risk_level: R2
  enabled: false
  runtime_access: false
  rag_enabled: false
  prompt_registry_enabled: false
  system_instruction_enabled: false
  generation_reference_enabled: false
  evidence_enabled: false
  scoring_enabled: false
  human_only: true
  human_review_required: true
  review_status: pending
```

伪结构限制：

1. 只能保留在 docs 文档内。
2. 不得保存为 `.json`、`.yaml`、`.yml`、`.csv` 或数据库文件。
3. 不得被程序读取。
4. 不得进入运行配置。
5. 不得触发生成、检索、评分或导出。

## 9. 默认锁定规则

以下字段必须默认锁定：

| 字段 | 锁定值 | 说明 |
| --- | --- | --- |
| `enabled` | `false` | 不启用任何知识包 |
| `runtime_access` | `false` | 运行链路不可访问 |
| `rag_enabled` | `false` | 不进入 RAG |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_enabled` | `false` | 不进入 system instruction registry |
| `generation_reference_enabled` | `false` | 不作为生成引用 |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `zbid_writeback_enabled` | `false` | 不触发 ZBid 写回 |
| `docx_export_enabled` | `false` | 不触发 DOCX 导出 |
| `source_text_copied` | `false` | 不复制源文件正文 |

任何字段从 `false` 改为 `true` 都不属于 KG-07 权限范围。

## 10. Source Path 规则

`source_path` 只记录来源路径，不复制原文。

规则：

1. 必须记录 `/Users/youfeini/Desktop/AI知识图谱大全` 下的原始路径。
2. 不得复制源文件到 ZDoc。
3. 不得移动、删除、重命名源文件。
4. 不得指向 ZDoc 内部复制件。
5. 不得把路径登记解释为授权读取运行时正文。
6. 不得把路径登记解释为 RAG 接入。

## 11. Source Summary 规则

`source_summary` 只写摘要，不搬运原文件内容。

规则：

1. 只能写人工短摘要。
2. 不得大段摘录源文件。
3. 不得复制系统指令原文。
4. 不得复制 prompt 原文。
5. 不得复制青天评标或满分门控规则原文。
6. 不得把摘要写成可直接执行的 prompt 或 system instruction。
7. 如疑似敏感信息，只记录风险类型，不记录敏感原文。

## 12. 试点条目建议

KG-07 不生成真实条目，只建议 KG-08 如获授权可从以下 inert 条目开始。

| inert_id | source_path | role | KG-07 建议 |
| --- | --- | --- | --- |
| `kg07-pilot-general-index-001` | `/Users/youfeini/Desktop/AI知识图谱大全/全能/00-HCX8-FINAL-KG-总索引版本说明.md` | 全能索引 | 可作为 source archive 索引候选，全部运行权限 false |
| `kg07-pilot-general-domain-002` | `/Users/youfeini/Desktop/AI知识图谱大全/全能/06-HCX8-FINAL-KG-行业模块库.md` | 行业模块 | 可作为术语和专业入口候选，全部运行权限 false |
| `kg07-pilot-general-template-003` | `/Users/youfeini/Desktop/AI知识图谱大全/全能/09-HCX8-FINAL-KG-标准产物模板库.md` | 模板候选 | 可作为 template library candidate，全部运行权限 false |
| `kg07-pilot-bridge-kg01-004` | `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG01_市政桥梁工程核心知识图谱_上传版.md` | 首个专业 KG 候选 | 可作为 knowledge anchor candidate，`rag_enabled=false` |
| `kg07-backup-hospital-renovation-kg02-001` | `/Users/youfeini/Desktop/AI知识图谱大全/医院装修改造/02_医院装修改造接口与医疗专项知识图谱.md` | 备选专业 KG 候选 | 仅作为备选登记候选，全部运行权限 false |

## 13. System Instruction 隔离规则

system instruction 类内容必须隔离，不得进入 system instruction registry。

规则：

1. `system_instruction_enabled=false` 必须保持。
2. 不得将源文件原文转为 ZDoc system instruction。
3. 不得将摘要改写成隐性 system instruction。
4. 不得进入 prompt registry。
5. 不得进入生成链全局约束。
6. 不得通过命名为 knowledge pack 绕过隔离。

隔离示例：

| source_path | KG-07 处置 |
| --- | --- |
| `/Users/youfeini/Desktop/AI知识图谱大全/全能/04-HCX8-FINAL-INSTRUCTIONS-安徽青天AI施组GPT系统指令.md` | 仅允许记录隔离风险，不得进入首批 inert 试点条目 |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/SYSTEM_市政桥梁工程青天施组系统指令_上传版.md` | 仅允许记录隔离风险，不得进入 system instruction registry |

## 14. 青天评标 / 满分门控边界

青天评标 / 满分门控类内容只作为参考候选，不得作为评分依据。

允许边界：

1. 可作为 `human_reference_only` 的风险登记对象。
2. 可作为未来人工复核的参考候选。
3. 可用于人工理解评标关注点。

禁止边界：

1. 不得作为 `scoring_basis`。
2. 不得作为 `evidence`。
3. 不得作为自动评分规则。
4. 不得作为满分优化目标。
5. 不得作为生成链强制规则。
6. 不得触发 `/review/apply` 或 ZBid 写回。

隔离示例：

| source_path | KG-07 处置 |
| --- | --- |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG03_青天AI类人评标门控知识图谱_上传版.md` | 仅参考候选，`evidence_enabled=false`、`scoring_enabled=false` |
| `/Users/youfeini/Desktop/AI知识图谱大全/市政桥梁工程/KG04_施组满分生成闭环知识图谱_上传版.md` | 仅参考候选，`evidence_enabled=false`、`scoring_enabled=false` |

## 15. KG-08 进入条件

KG-08 若要进入真实 disabled manifest 文件创建，必须再次人工授权。

进入 KG-08 前必须满足：

1. KG-07 文档已提交到 `main`。
2. KG-07 tag 已创建并推送。
3. 工作区干净。
4. ChatGPT 总控明确授权 KG-08。
5. ChatGPT 总控明确指定唯一输出文件。
6. ChatGPT 总控明确说明是否允许创建真实 disabled manifest 文件。
7. KG-08 即使获授权，也必须保持全部运行权限为 false。
8. KG-08 不得复制源文件。
9. KG-08 不得生成知识包实体。
10. KG-08 不得接入 RAG / prompt registry / system instruction registry。
11. KG-08 不得启用任何知识包。
12. KG-08 不得运行服务、Ollama、端口或 endpoint。
13. KG-08 不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
14. KG-08 不得写 output/job/export。
15. KG-08 不得进入真实使用阶段。

## 16. KG-08 授权请求草案

如 ChatGPT 总控决定进入 KG-08，建议授权请求限定为：

> 请求授权执行 KG-08：ZDoc controlled pilot disabled manifest file creation only。
>
> KG-08 仅允许创建一个真实 disabled manifest 草案文件，用于登记 `全能索引 + 市政桥梁 KG01` 首个试点和 `全能索引 + 医院装修改造 KG02` 备选试点的 inert 条目。所有条目必须保持 `enabled=false`、`runtime_access=false`、`rag_enabled=false`、`prompt_registry_enabled=false`、`system_instruction_enabled=false`、`generation_reference_enabled=false`、`evidence_enabled=false`、`scoring_enabled=false`、`source_text_copied=false`。
>
> KG-08 不得复制 `/Users/youfeini/Desktop/AI知识图谱大全` 中任何源文件，不得生成知识包实体文件，不得接入 RAG、prompt registry 或 system instruction registry，不得启用任何条目，不得让生成链读取，不得 evidence 化，不得评分依据化，不得进入真实使用阶段。
>
> KG-08 完成后必须停止，等待 ChatGPT 总控审核，不得自动进入 KG-09。

## 17. KG-07 结论

KG-07 结论如下：

1. KG-04、KG-05、KG-06 的试点与禁用结论继续成立。
2. 首个试点继续为 `全能索引 + 市政桥梁 KG01`。
3. 备选试点继续为 `全能索引 + 医院装修改造 KG02`。
4. inert manifest entity 应优先放在 docs-only 草案层，不得进入运行链路。
5. 本文件中的示例只能作为文档内伪结构，不得生成真实 manifest 文件。
6. KG-08 若要创建真实 disabled manifest 文件，必须再次人工授权。
7. KG-07 完成后必须停止，等待 ChatGPT 总控审核。
