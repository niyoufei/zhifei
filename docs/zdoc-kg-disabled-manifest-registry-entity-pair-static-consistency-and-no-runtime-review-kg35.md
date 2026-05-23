# ZDoc KG-35 Disabled Manifest-Registry Entity Pair Static Consistency and No-Runtime Review

## 1. KG-35 执行摘要

KG-35 是对 KG-31 disabled manifest entity 与 KG-33 disabled registry entity 的 docs-only 静态配对一致性复核。本步骤不执行新的实体化动作，不修改 KG-31 manifest entity JSON，不修改 KG-33 registry entity JSON，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON。

KG-35 结论：KG-31 与 KG-33 当前可以作为一组受控静态草案 pair 归档，但仍只位于 `docs/` 非运行目录下。二者均未注册、未启用、不可运行加载、不可 registry 加载、不可 RAG 加载、不可 prompt registry 加载、不可 system instruction registry 加载、不可作为 evidence、不可作为 scoring basis。

## 2. 复核对象

| 对象 | 文件 | KG-35 处置 |
| --- | --- | --- |
| KG-08 manifest candidate | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 只读复核 |
| KG-15 registry candidate | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 只读复核 |
| KG-31 disabled manifest entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | 只读复核 |
| KG-33 disabled registry entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | 只读复核 |
| KG-34 no-runtime review | `docs/zdoc-kg-disabled-registry-entity-static-compliance-and-no-runtime-review-kg34.md` | 只读承接 |

KG-35 不读取、复制、移动、删除或改写 `AI知识图谱大全` 原文件。

## 3. Entity Pair 配对关系复核

KG-31 manifest entity 与 KG-33 registry entity 的配对关系如下：

| 维度 | KG-31 manifest entity | KG-33 registry entity | 一致性结论 |
| --- | --- | --- | --- |
| 试点方向 | `全能索引 + 市政桥梁 KG01` | `全能索引 + 市政桥梁 KG01` | 一致 |
| 备选方向 | `全能索引 + 医院装修改造 KG02` | `全能索引 + 医院装修改造 KG02` | 一致 |
| 来源模式 | `path_and_summary_only` | `path_and_summary_only` | 一致 |
| 风险等级 | `R2` | `R2` | 一致 |
| 专业标签 | `general_index` / `municipal_bridge_kg01` / `backup_hospital_renovation_kg02` | `general_index` / `municipal_bridge_kg01` / `backup_hospital_renovation_kg02` | 一致 |
| 注册状态 | `not_registered` | `not_registered` | 一致 |
| 启用状态 | `enabled=false` | `enabled=false` | 一致 |

配对结论：KG-31 与 KG-33 的试点方向、备选方向、来源模式、风险等级、专业标签、注册状态和启用状态一致，可以作为静态 pair 进行后续人工审查。

## 4. Registry Entity 对 Manifest Entity 引用一致性复核

KG-33 registry entity 对 KG-31 manifest entity 的引用字段如下：

| 字段 | KG-33 当前值 | 复核结论 |
| --- | --- | --- |
| `linked_manifest_entity` | `KG-31 disabled manifest entity` | 指向对象名称一致 |
| `linked_manifest_entity_path` | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | 指向 KG-31 entity 文件 |
| `manifest_entity_registered` | `false` | 未注册 KG-31 entity |
| `manifest_entity_loadable` | `false` | 未加载 KG-31 entity |

路径交叉复核：

| 关系 | 复核结论 |
| --- | --- |
| KG-33 `linked_manifest_entity_path` 指向 KG-31 manifest entity 文件 | 通过 |
| KG-33 `linked_manifest_candidate_path` 指向 KG-08 manifest candidate 文件 | 通过 |
| KG-31 `created_from_path` 指向 KG-08 manifest candidate 文件 | 通过 |
| KG-31 `linked_registry_candidate_path` 指向 KG-15 registry candidate 文件 | 通过 |
| KG-33 `created_from_path` 指向 KG-15 registry candidate 文件 | 通过 |

引用一致性结论：KG-33 仅以 docs-only 静态路径引用 KG-31，不构成 manifest 注册、registry 注册、运行加载或知识包启用。

## 5. 禁用字段一致性复核

| 控制项 | KG-31 manifest entity | KG-33 registry entity | KG-35 结论 |
| --- | --- | --- | --- |
| `enabled` | `false` | `false` | 一致禁用 |
| `registration_status` | `not_registered` | `not_registered` | 一致未注册 |
| `runtime_loadable` | `false` | `false` | 一致不可运行加载 |
| `system_instruction_loadable` | `false` | `false` | 一致不可系统指令加载 |
| `rag_loadable` | `false` | `false` | 一致不可 RAG 加载 |
| `prompt_registry_loadable` | `false` | `false` | 一致不可 prompt registry 加载 |
| `evidence_allowed` | `false` | `false` | 一致不可 evidence |
| `scoring_allowed` | `false` | `false` | 一致不可评分 |
| `source_files_copied` | `false` | `false` | 一致未复制源文件 |
| `raw_system_instruction_embedded` | `false` | `false` | 一致未嵌入系统指令原文 |
| `raw_prompt_embedded` | `false` | `false` | 一致未嵌入 prompt 原文 |
| `raw_source_text_embedded` | `false` | `false` | 一致未嵌入源文件原文 |
| `writeback_allowed` | `false` | `false` | 一致不可写回 |
| `export_allowed` | `false` | `false` | 一致不可导出 |
| `loader_config_present` | `false` | `false` | 一致无 loader 配置 |
| `endpoint_binding_present` | `false` | `false` | 一致无 endpoint 绑定 |
| `runtime_registry_entry_present` | `false` | `false` | 一致无运行 registry 条目 |

KG-33 额外 registry 控制项复核：

| 字段 | KG-33 当前值 | 复核结论 |
| --- | --- | --- |
| `runtime_registered` | `false` | 不进入运行注册 |
| `registry_loadable` | `false` | 不可 registry 加载 |
| `manifest_entity_registered` | `false` | 不注册 KG-31 manifest entity |
| `manifest_entity_loadable` | `false` | 不加载 KG-31 manifest entity |

禁用字段结论：KG-31 / KG-33 pair 没有打开任何运行、注册、检索、生成引用、证据化、评分、写回或导出入口。

## 6. RAG / Prompt Registry / System Instruction Registry 隔离复核

KG-31 与 KG-33 均保持以下隔离边界：

| 隔离项 | KG-35 结论 |
| --- | --- |
| RAG | `rag_loadable=false`，不得被 RAG 加载 |
| prompt registry | `prompt_registry_loadable=false`，不得进入 prompt registry |
| system instruction registry | `system_instruction_loadable=false`，不得进入 system instruction registry |
| evidence | `evidence_allowed=false`，不得作为 evidence |
| scoring | `scoring_allowed=false`，不得作为 scoring basis |
| ZBid writeback | `writeback_allowed=false`，不得写回 |
| export | `export_allowed=false`，不得导出 |

隔离结论：KG-31 / KG-33 pair 只能作为人工审查对象，不得被任何运行链路读取或使用。

## 7. KG-08 / KG-15 / KG-31 / KG-33 状态复核

| 对象 | 当前状态 | KG-35 复核结论 |
| --- | --- | --- |
| KG-08 manifest candidate JSON | `candidate_only` / `not_registered` / disabled | 继续候选、冻结、禁用 |
| KG-15 registry candidate JSON | `registry_candidate_only` / `not_registered` / disabled | 继续候选、冻结、禁用 |
| KG-31 disabled manifest entity JSON | `disabled_entity_only` / `not_registered` / `runtime_loadable=false` | 继续静态 disabled manifest entity 草案 |
| KG-33 disabled registry entity JSON | `disabled_registry_entity_only` / `not_registered` / `runtime_registered=false` / `registry_loadable=false` / `runtime_loadable=false` | 继续静态 disabled registry entity 草案 |

状态结论：KG-08、KG-15、KG-31、KG-33 均未进入运行态，均未注册，均未启用，均不得自动加载。

## 8. Docs 非运行目录结论

KG-31 与 KG-33 当前均位于：

`docs/kg-controlled-entities/`

该目录仅用于文档化、审查和受控归档，不属于 ZDoc 运行配置目录、backend、frontend、config、job、output 或 export 目录。

KG-35 确认：

1. 当前 pair 仅为 docs 非运行目录下的静态实体草案组合；
2. 当前 pair 不是真实 manifest registry 绑定；
3. 当前 pair 不是真实 registry；
4. 当前 pair 没有运行 loader；
5. 当前 pair 没有 endpoint 绑定；
6. 当前 pair 没有 registration id；
7. 当前 pair 没有 activation id；
8. 当前 pair 不应被 ZDoc 自动读取。

## 9. Source 内容与原文隔离复核

KG-31 / KG-33 pair 仅记录路径、摘要、风险等级、专业标签、disabled flags、isolation rules 和候选关系。

KG-35 继续确认：

1. 未复制 `AI知识图谱大全` 原文件；
2. 未嵌入 `AI知识图谱大全` 原文；
3. 未嵌入系统指令原文；
4. 未嵌入 prompt 原文；
5. 未嵌入青天评标或满分门控原文；
6. `全能` 不得作为 system instruction；
7. `市政桥梁 KG01` 不得作为 system instruction；
8. `医院装修改造 KG02` 仍仅为备选方向；
9. 青天评标 / 满分门控内容不得作为 evidence；
10. 青天评标 / 满分门控内容不得作为 scoring basis。

## 10. 问题分级

| 级别 | 是否存在 | 说明 | 处置 |
| --- | --- | --- | --- |
| Blocker | 否 | 未发现 pair 引用断裂、注册、启用、运行加载或系统接入字段 | 可保持静态 pair |
| Major | 否 | 未发现 evidence、scoring、RAG、prompt registry、system instruction registry 可用性 | 继续禁用 |
| Minor | 否 | 未发现需要修改 KG-31 或 KG-33 的静态一致性问题 | 不修改既有 JSON |
| Note | 是 | 当前 pair 已形成 docs-only 静态草案组合，但仍不具备运行资格 | 仅人工复核使用 |

## 11. KG-36 边界建议

KG-36 不得自动进入。若 ChatGPT 后续单独授权 KG-36，建议 KG-36 只能做以下范围之一：

1. entity pair frozen audit package；
2. entity pair 人工授权审查；
3. 对 KG-31 / KG-33 pair 的静态审查资料索引。

KG-36 仍不得：

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

## 12. KG-35 最终结论

KG-35 最终结论：

1. KG-31 disabled manifest entity 与 KG-33 disabled registry entity 的配对关系一致；
2. KG-33 对 KG-31 的引用路径一致，且仅为 docs-only 静态引用；
3. KG-31 / KG-33 均保持 `enabled=false`、`not_registered`、`runtime_loadable=false`、不可 evidence、不可 scoring；
4. KG-31 / KG-33 均不得被 RAG、prompt registry、system instruction registry 加载；
5. KG-08 / KG-15 / KG-31 / KG-33 继续保持候选、冻结、禁用、不可运行状态；
6. 当前 pair 仅为 docs 非运行目录下的静态实体草案组合；
7. KG-35 不进入 KG-36，不执行任何真实创建、注册、接入、启用或运行动作。
