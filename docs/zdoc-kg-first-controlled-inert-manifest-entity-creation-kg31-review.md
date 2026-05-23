# ZDoc KG-31 First Controlled Inert Manifest Entity Creation Review

## 1. KG-31 执行摘要

KG-31 是 ZDoc KG 管线中的首次受控实体化动作。本步骤只在 docs 下创建一个 inert / disabled manifest entity JSON，并新增一份 review 文档。

KG-31 仍然是 no-runtime、no-registration、no-integration。它不创建真实 registry，不创建 validator 脚本，不接入 RAG / prompt registry / system instruction registry，不启用知识包，不运行服务，不访问端口或 endpoint，不触发生成、导出、review apply 或 ZBid 写回。

## 2. 本次新增文件

KG-31 仅新增以下两个文件：

| 文件 | 作用 | 运行状态 |
| --- | --- | --- |
| `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | 首个受控 inert manifest entity | 不可运行、不可注册、不可加载 |
| `docs/zdoc-kg-first-controlled-inert-manifest-entity-creation-kg31-review.md` | KG-31 review 与边界记录 | docs-only |

除上述两个文件外，KG-31 不新增、修改、移动、删除任何其他文件。

## 3. Entity 来源与冻结承接

本次 manifest entity 来源于 KG-08 manifest candidate JSON 的冻结信息：

`docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`

本次 entity 关联 KG-15 registry candidate：

`docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json`

KG-31 不修改 KG-08 文件本体，不修改 KG-15 文件本体。KG-08 继续保持 `candidate_only`、`not_registered`、disabled；KG-15 继续保持 `registry_candidate_only`、`not_registered`、disabled。

## 4. 为什么仍不属于运行态接入

KG-31 创建的 JSON 文件位于 `docs/kg-controlled-entities/`，不是 ZDoc 运行配置目录，不是 runtime manifest，不是 registry 文件，也没有 loader、endpoint、activation id、registration id、writeback target 或 export path。

该 entity 明确锁定：

| 字段 | 值 | 结论 |
| --- | --- | --- |
| `enabled` | `false` | 不启用 |
| `registration_status` | `not_registered` | 不注册 |
| `runtime_loadable` | `false` | 不允许运行加载 |
| `system_instruction_loadable` | `false` | 不允许进入系统指令 |
| `rag_loadable` | `false` | 不允许进入 RAG |
| `prompt_registry_loadable` | `false` | 不允许进入 prompt registry |
| `evidence_allowed` | `false` | 不允许作为 evidence |
| `scoring_allowed` | `false` | 不允许作为 scoring basis |
| `source_files_copied` | `false` | 未复制源文件 |
| `raw_system_instruction_embedded` | `false` | 未嵌入系统指令原文 |

因此，KG-31 的 entity 只是 docs 下的 inert disabled entity，不会被 ZDoc 自动读取或使用。

## 5. Source 边界

KG-31 entity 只记录 KG-08 冻结的路径、摘要、风险等级、专业标签和隔离规则。

KG-31 不复制 `AI知识图谱大全` 原始文件，不复制系统指令原文，不复制 prompt 原文，不写入施工知识图谱正文，不写入青天评标或满分门控原文。

允许进入 entity 的信息只包括：

1. source path；
2. source summary；
3. risk level；
4. domain tags；
5. isolation rules；
6. disabled flags；
7. KG-08 / KG-15 链接关系。

## 6. KG-08 / KG-15 状态确认

| 对象 | KG-31 后状态 | 是否修改 |
| --- | --- | --- |
| KG-08 manifest candidate JSON | `candidate_only` / `not_registered` / disabled | 否 |
| KG-15 registry candidate JSON | `registry_candidate_only` / `not_registered` / disabled | 否 |
| KG-31 manifest entity JSON | `disabled_entity_only` / `not_registered` / inert | 新增 |

KG-31 不把 KG-08 转换为真实 manifest，不把 KG-15 转换为真实 registry。

## 7. 禁止使用规则

KG-31 entity 文件不得被 ZDoc 加载、注册、启用、检索或作为 evidence。

具体禁止：

1. 不得作为 runtime manifest；
2. 不得注册到 runtime registry；
3. 不得进入 RAG；
4. 不得进入 prompt registry；
5. 不得进入 system instruction registry；
6. 不得作为生成引用；
7. 不得作为 evidence；
8. 不得作为 scoring basis；
9. 不得写回 ZBid；
10. 不得触发导出；
11. 不得被 `/generate`、`/export_docx`、`/review/apply` 使用。

## 8. System Instruction 与青天评标隔离

KG-31 继续确认：

1. `全能` 不作为 system instruction；
2. `市政桥梁 KG01` 不作为 system instruction；
3. `医院装修改造 KG02` 不作为 system instruction；
4. source summary 不得变成隐性系统指令；
5. system instruction 类内容继续 quarantine；
6. 青天评标 / 满分门控类内容不得作为 evidence；
7. 青天评标 / 满分门控类内容不得作为 scoring basis；
8. 相关内容不得进入 review apply、ZBid 写回或 export 链路。

## 9. KG-32 边界建议

KG-32 不得自动进入。若 ChatGPT 后续授权 KG-32，建议 KG-32 只能做以下二选一：

1. entity 静态校验规则设计；
2. entity 人工审查与处置记录。

KG-32 默认仍不得：

1. 接入系统；
2. 注册 manifest；
3. 创建真实 registry；
4. 创建 validator 脚本；
5. 启用 RAG / prompt registry / system instruction registry；
6. 启用知识包；
7. 运行服务、Ollama、端口或 endpoint；
8. 触发生成、导出、review apply 或 ZBid 写回；
9. 生成 DOCX；
10. 写入 `output/job/export`。

## 10. KG-31 最终记录

KG-31 已创建首个受控 inert manifest entity，并确认该 entity 仍为 docs-only、disabled、not_registered、not_runtime_loadable。

KG-31 不进入 KG-32。
