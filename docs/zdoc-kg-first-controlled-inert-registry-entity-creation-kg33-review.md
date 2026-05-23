# ZDoc KG-33 First Controlled Inert Registry Entity Creation Review

## 1. KG-33 执行摘要

KG-33 是 ZDoc KG 管线中的首次受控 registry entity 草案创建。本步骤只在 docs 下创建一个 inert / disabled registry entity JSON，并新增一份 review 文档。

KG-33 仍为 no-runtime、no-registration、no-integration。它不创建真实 registry，不创建 validator 脚本，不注册、不启用、不加载任何知识包，不接入 RAG / prompt registry / system instruction registry，不运行服务，不访问端口或 endpoint，不触发生成、导出、review apply 或 ZBid 写回。

## 2. 本次新增文件

KG-33 仅新增以下两个文件：

| 文件 | 作用 | 运行状态 |
| --- | --- | --- |
| `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | 首个受控 inert registry entity 草案 | 不可运行、不可注册、不可加载 |
| `docs/zdoc-kg-first-controlled-inert-registry-entity-creation-kg33-review.md` | KG-33 review 与边界记录 | docs-only |

除上述两个文件外，KG-33 不新增、修改、移动、删除任何其他文件。

## 3. Entity 来源与链接关系

本次 registry entity 来源于 KG-15 registry candidate 的冻结信息：

`docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json`

本次 registry entity 引用 KG-08 manifest candidate：

`docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`

本次 registry entity 引用 KG-31 disabled manifest entity：

`docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json`

KG-33 不修改 KG-15 文件本体，不修改 KG-08 文件本体，不修改 KG-31 manifest entity 文件本体。

## 4. 为什么仍不属于真实 Registry

KG-33 创建的 registry entity 位于 `docs/kg-controlled-entities/`，不是 ZDoc 运行 registry 目录，不是 runtime config，不是 loader 配置，也没有 endpoint、activation id、registration id、writeback target 或 export path。

该 registry entity 明确锁定：

| 字段 | 值 | 结论 |
| --- | --- | --- |
| `enabled` | `false` | 不启用 |
| `registration_status` | `not_registered` | 不注册 |
| `runtime_registered` | `false` | 不进入运行注册 |
| `registry_loadable` | `false` | 不允许 registry 加载 |
| `runtime_loadable` | `false` | 不允许运行加载 |
| `manifest_entity_registered` | `false` | 不注册 KG-31 manifest entity |
| `manifest_entity_loadable` | `false` | 不加载 KG-31 manifest entity |

因此，KG-33 registry entity 是 docs-only disabled 草案，不是真实 registry。

## 5. 为什么仍不属于运行态接入

KG-33 registry entity 明确锁定：

| 字段 | 值 | 结论 |
| --- | --- | --- |
| `system_instruction_loadable` | `false` | 不允许进入系统指令 |
| `rag_loadable` | `false` | 不允许进入 RAG |
| `prompt_registry_loadable` | `false` | 不允许进入 prompt registry |
| `evidence_allowed` | `false` | 不允许作为 evidence |
| `scoring_allowed` | `false` | 不允许作为 scoring basis |
| `source_files_copied` | `false` | 未复制源文件 |
| `raw_system_instruction_embedded` | `false` | 未嵌入系统指令原文 |
| `writeback_allowed` | `false` | 不允许写回 |
| `export_allowed` | `false` | 不允许导出 |

因此，KG-33 不会让 KG-31 manifest entity 被 ZDoc 注册、加载、启用、检索或参与生成链路。

## 6. KG-08 / KG-15 / KG-31 状态确认

| 对象 | KG-33 后状态 | 是否修改 |
| --- | --- | --- |
| KG-08 manifest candidate JSON | `candidate_only` / `not_registered` / disabled | 否 |
| KG-15 registry candidate JSON | `registry_candidate_only` / `not_registered` / disabled | 否 |
| KG-31 manifest entity JSON | `disabled_entity_only` / `not_registered` / not runtime loadable | 否 |
| KG-33 registry entity JSON | `disabled_registry_entity_only` / `not_registered` / not runtime loadable | 新增 |

KG-33 不把 KG-15 转换为真实 registry，不把 KG-31 manifest entity 注册为运行 manifest。

## 7. Source 边界

KG-33 registry entity 只记录 KG-15、KG-08 与 KG-31 的路径链接、状态、风险等级、专业标签、禁用 flags 和隔离规则。

KG-33 不复制 `AI知识图谱大全` 原始文件，不复制系统指令原文，不复制 prompt 原文，不写入施工知识图谱正文，不写入青天评标或满分门控原文。

允许进入 registry entity 的信息仅包括：

1. linked candidate path；
2. linked entity path；
3. source mode；
4. status / registration status；
5. risk level；
6. domain tags；
7. disabled flags；
8. isolation rules；
9. pre-registration rules。

## 8. 禁止使用规则

KG-33 registry entity 文件不得被 ZDoc 注册、加载、启用、检索或作为 evidence。

具体禁止：

1. 不得作为真实 registry；
2. 不得注册到 runtime registry；
3. 不得加载 KG-31 manifest entity；
4. 不得进入 RAG；
5. 不得进入 prompt registry；
6. 不得进入 system instruction registry；
7. 不得作为生成引用；
8. 不得作为 evidence；
9. 不得作为 scoring basis；
10. 不得写回 ZBid；
11. 不得触发导出；
12. 不得被 `/generate`、`/export_docx`、`/review/apply` 使用。

## 9. System Instruction 与青天评标隔离

KG-33 继续确认：

1. `全能` 不作为 system instruction；
2. `市政桥梁 KG01` 不作为 system instruction；
3. `医院装修改造 KG02` 不作为 system instruction；
4. source summary 不得变成隐性系统指令；
5. system instruction 类内容继续 quarantine；
6. 青天评标 / 满分门控类内容不得作为 evidence；
7. 青天评标 / 满分门控类内容不得作为 scoring basis；
8. 相关内容不得进入 review apply、ZBid 写回或 export 链路。

## 10. KG-34 边界建议

KG-34 不得自动进入。若 ChatGPT 后续授权 KG-34，建议 KG-34 只能做以下二选一：

1. registry entity 静态合规复核；
2. registry entity 人工审查与处置记录。

KG-34 默认仍不得：

1. 接入系统；
2. 注册 manifest；
3. 创建真实 registry；
4. 创建 validator 脚本；
5. 注册、启用、加载任何知识包；
6. 接入 RAG / prompt registry / system instruction registry；
7. 运行服务、Ollama、端口或 endpoint；
8. 触发生成、导出、review apply 或 ZBid 写回；
9. 生成 DOCX；
10. 写入 `output/job/export`；
11. 修改 KG-08、KG-15、KG-31 manifest entity 或 KG-33 registry entity。

## 11. KG-33 最终记录

KG-33 已创建首个受控 inert registry entity，并确认该 entity 仍为 docs-only、disabled、not_registered、not_runtime_registered、not_registry_loadable、not_runtime_loadable。

KG-33 不进入 KG-34。
