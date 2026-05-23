# ZDoc KG-36 Disabled Entity Pair Frozen Audit Package and Manual Authorization Gate

## 1. KG-36 执行摘要

KG-36 是对 KG-31 disabled manifest entity 与 KG-33 disabled registry entity 的 frozen audit package 与人工授权门槛归档。本步骤仍为 docs-only，不执行任何新的实体化动作，不修改 KG-31 manifest entity JSON，不修改 KG-33 registry entity JSON，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON。

KG-36 结论：KG-31 / KG-33 已形成一组受控 disabled entity pair，可作为冻结审计包进入人工审查链路；但该 pair 当前仅是 `docs/` 非运行目录下的禁用静态草案组合，不得注册、不得启用、不得加载、不得 evidence、不得 scoring，不得接入 RAG / prompt registry / system instruction registry。

## 2. Frozen Audit Package 范围

KG-36 frozen audit package 包含以下文件和审查节点：

| 类别 | 文件 | 状态 | KG-36 用途 |
| --- | --- | --- | --- |
| manifest candidate | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | KG-08 candidate only / not registered / disabled | 只读来源候选 |
| registry candidate | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | KG-15 registry candidate only / not registered / disabled | 只读 registry 候选 |
| manifest entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | KG-31 disabled entity only / not registered / disabled | 冻结 pair 的 manifest 侧 |
| registry entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | KG-33 disabled registry entity only / not registered / disabled | 冻结 pair 的 registry 侧 |
| manifest entity review | `docs/zdoc-kg-disabled-manifest-entity-static-compliance-and-no-runtime-review-kg32.md` | no-runtime review | KG-31 合规复核依据 |
| registry entity review | `docs/zdoc-kg-disabled-registry-entity-static-compliance-and-no-runtime-review-kg34.md` | no-runtime review | KG-33 合规复核依据 |
| entity pair review | `docs/zdoc-kg-disabled-manifest-registry-entity-pair-static-consistency-and-no-runtime-review-kg35.md` | pair consistency review | KG-31 / KG-33 配对一致性依据 |

本审计包仅用于人工审查和后续授权判断，不是运行输入，不是 registry 配置，不是 manifest 注册文件。

## 3. KG-31 Manifest Entity 结论汇总

KG-31 创建了首个受控 inert manifest entity：

`docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json`

KG-32 对 KG-31 的复核结论如下：

| 复核项 | KG-32 结论 | KG-36 承接 |
| --- | --- | --- |
| 文件位置 | `docs/kg-controlled-entities/` | docs 非运行目录 |
| `entity_status` | `disabled_entity_only` | 继续禁用 |
| `registration_status` | `not_registered` | 继续未注册 |
| `enabled` | `false` | 继续未启用 |
| `runtime_loadable` | `false` | 不可运行加载 |
| `rag_loadable` | `false` | 不可 RAG 加载 |
| `prompt_registry_loadable` | `false` | 不可 prompt registry 加载 |
| `system_instruction_loadable` | `false` | 不可 system instruction 加载 |
| `evidence_allowed` | `false` | 不可 evidence |
| `scoring_allowed` | `false` | 不可 scoring |
| `source_files_copied` | `false` | 未复制原文件 |
| `raw_source_text_embedded` | `false` | 未嵌入原文 |

KG-36 承接结论：KG-31 manifest entity 只能作为冻结审计包中的静态禁用对象，不得被 ZDoc 自动读取、注册、加载或启用。

## 4. KG-33 Registry Entity 结论汇总

KG-33 创建了首个受控 inert registry entity：

`docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json`

KG-34 对 KG-33 的复核结论如下：

| 复核项 | KG-34 结论 | KG-36 承接 |
| --- | --- | --- |
| 文件位置 | `docs/kg-controlled-entities/` | docs 非运行目录 |
| `entity_status` | `disabled_registry_entity_only` | 继续禁用 |
| `registration_status` | `not_registered` | 继续未注册 |
| `enabled` | `false` | 继续未启用 |
| `runtime_registered` | `false` | 不进入运行注册 |
| `registry_loadable` | `false` | 不可 registry 加载 |
| `runtime_loadable` | `false` | 不可运行加载 |
| `manifest_entity_registered` | `false` | 不注册 KG-31 manifest entity |
| `manifest_entity_loadable` | `false` | 不加载 KG-31 manifest entity |
| `rag_loadable` | `false` | 不可 RAG 加载 |
| `prompt_registry_loadable` | `false` | 不可 prompt registry 加载 |
| `system_instruction_loadable` | `false` | 不可 system instruction 加载 |
| `evidence_allowed` | `false` | 不可 evidence |
| `scoring_allowed` | `false` | 不可 scoring |

KG-36 承接结论：KG-33 registry entity 不是真实 registry，不得被 ZDoc 注册、加载、启用、检索、证据化、评分或写回。

## 5. KG-35 Pair 一致性结论汇总

KG-35 已复核 KG-31 / KG-33 的 pair 一致性：

| 维度 | KG-35 结论 | KG-36 冻结状态 |
| --- | --- | --- |
| 试点方向 | `全能索引 + 市政桥梁 KG01` 一致 | 冻结 |
| 备选方向 | `全能索引 + 医院装修改造 KG02` 一致 | 冻结 |
| source mode | `path_and_summary_only` 一致 | 冻结 |
| risk level | `R2` 一致 | 冻结 |
| domain tags | `general_index` / `municipal_bridge_kg01` / `backup_hospital_renovation_kg02` 一致 | 冻结 |
| KG-33 指向 KG-31 | `linked_manifest_entity_path` 指向 KG-31 manifest entity | 冻结 |
| KG-31 指向 KG-08 | `created_from_path` 指向 KG-08 manifest candidate | 冻结 |
| KG-33 指向 KG-15 | `created_from_path` 指向 KG-15 registry candidate | 冻结 |
| pair 状态 | docs-only / not registered / disabled / no-runtime | 冻结 |

KG-36 承接结论：KG-31 / KG-33 pair 可以作为 frozen audit package 的核心对象，但不能由 frozen 状态推导出任何运行授权。

## 6. Disabled Entity Pair 当前状态

KG-36 确认当前 disabled entity pair 的状态如下：

| 控制项 | KG-31 manifest entity | KG-33 registry entity | KG-36 结论 |
| --- | --- | --- | --- |
| docs-only | 是 | 是 | 仅 docs 归档 |
| `enabled` | `false` | `false` | 不启用 |
| `registration_status` | `not_registered` | `not_registered` | 不注册 |
| runtime loadable | `false` | `false` | 不运行加载 |
| registry loadable | 不适用 | `false` | 不 registry 加载 |
| RAG loadable | `false` | `false` | 不 RAG 加载 |
| prompt registry loadable | `false` | `false` | 不 prompt registry 加载 |
| system instruction loadable | `false` | `false` | 不 system instruction registry 加载 |
| evidence allowed | `false` | `false` | 不作为 evidence |
| scoring allowed | `false` | `false` | 不作为 scoring basis |
| writeback allowed | `false` | `false` | 不写回 |
| export allowed | `false` | `false` | 不导出 |
| source files copied | `false` | `false` | 未复制源文件 |
| raw source text embedded | `false` | `false` | 未嵌入原文 |

状态结论：该 pair 是禁用、未注册、不可加载的静态草案组合，不是可运行知识包。

## 7. 不得注册 / 启用 / 加载规则

KG-36 将以下规则冻结为后续人工授权前的硬边界：

1. 不得注册 KG-31 manifest entity；
2. 不得注册 KG-33 registry entity；
3. 不得创建真实 registry；
4. 不得创建 runtime loader；
5. 不得创建 endpoint binding；
6. 不得启用任何 knowledge pack；
7. 不得让 ZDoc 自动读取 `docs/kg-controlled-entities/` 下的 entity 文件；
8. 不得将 KG-31 / KG-33 写入 backend、frontend、config 或运行 registry；
9. 不得作为 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回链路输入；
10. 不得写入 `output/job/export`。

## 8. Evidence / Scoring / Registry 隔离规则

KG-36 继续冻结以下隔离规则：

| 链路 | 冻结规则 |
| --- | --- |
| evidence | KG-31 / KG-33 均不得作为 evidence |
| scoring | KG-31 / KG-33 均不得作为 scoring basis |
| RAG | KG-31 / KG-33 均不得被 RAG 加载 |
| prompt registry | KG-31 / KG-33 均不得进入 prompt registry |
| system instruction registry | KG-31 / KG-33 均不得进入 system instruction registry |
| 青天评标 / 满分门控 | 只能作为隔离参考候选，不得进入评分逻辑 |
| system instruction 类内容 | 必须继续隔离，不得转为 system instruction |
| writeback | 不得写回 ZBid |
| export | 不得进入导出链 |

## 9. Manual Authorization Gate

KG-36 后，如需继续推进 KG-37，必须由 ChatGPT 总控单独授权。KG-37 不得自动进入。

KG-37 若获授权，只能选择以下方向之一：

1. 人工授权请求文档；
2. 静态归档审查文档；
3. frozen audit package 的只读索引或人工验收记录。

KG-37 仍不得：

1. 接入系统；
2. 注册 manifest；
3. 注册 registry；
4. 创建真实 registry；
5. 创建 validator 脚本；
6. 注册、启用、加载任何知识包；
7. 接入 RAG / prompt registry / system instruction registry；
8. 运行服务、Ollama、端口或 endpoint；
9. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
10. 生成 DOCX；
11. 写入 `output/job/export`；
12. 修改 KG-08、KG-15、KG-31 或 KG-33；
13. 复制、移动、删除或改写 `AI知识图谱大全` 文件。

## 10. 问题分级

| 级别 | 是否存在 | 说明 | KG-36 处置 |
| --- | --- | --- | --- |
| Blocker | 否 | 未发现 KG-31 / KG-33 pair 引用断裂、启用、注册或运行加载迹象 | 可冻结为审计包 |
| Major | 否 | 未发现 evidence、scoring、RAG、prompt registry、system instruction registry 可用性 | 继续隔离 |
| Minor | 否 | 未发现需要修改 KG-31 / KG-33 JSON 的静态字段问题 | 不修改既有 JSON |
| Note | 是 | pair 已进入 frozen audit package，但仍不是运行资产 | 仅人工复核 |

## 11. KG-36 最终结论

KG-36 最终结论：

1. KG-31 manifest entity、KG-33 registry entity、KG-32、KG-34、KG-35 的结论一致；
2. disabled entity pair frozen audit package 已形成；
3. entity pair 当前仅为 docs 非运行目录下的禁用静态草案组合；
4. entity pair 不得注册、不得启用、不得加载、不得 evidence、不得 scoring；
5. entity pair 不得接入 RAG / prompt registry / system instruction registry；
6. KG-37 如需继续，只能做人工授权请求或静态归档审查；
7. KG-36 不进入 KG-37，不执行任何真实创建、注册、接入、启用或运行动作。
