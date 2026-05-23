# ZDoc KG-32 Disabled Manifest Entity Static Compliance and No-Runtime Review

## 1. KG-32 执行摘要

KG-32 是对 KG-31 新增 disabled manifest entity JSON 的 docs-only 静态合规与 no-runtime 复核。本步骤不执行任何实体化新增动作，不修改 KG-31 entity JSON，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON。

KG-32 结论：KG-31 entity 当前仅为 `docs/kg-controlled-entities/` 下的静态 disabled entity 草案。它不可被 ZDoc 加载、注册、启用、检索、作为 evidence、作为 scoring basis 或作为任何运行链路输入。

## 2. 复核对象

KG-32 复核以下文件：

| 文件 | 复核用途 | KG-32 处置 |
| --- | --- | --- |
| `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | KG-31 disabled manifest entity | 只读复核 |
| `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | KG-08 manifest candidate | 只读复核，语法校验 |
| `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | KG-15 registry candidate | 只读复核，语法校验 |
| `docs/zdoc-kg-first-controlled-inert-manifest-entity-creation-kg31-review.md` | KG-31 创建说明与边界记录 | 只读复核 |

KG-32 不读取、复制、移动、删除或改写 `AI知识图谱大全` 原文件。

## 3. KG-31 Entity 字段完整性复核

KG-31 disabled manifest entity 已包含以下核心字段：

| 字段类别 | 字段 | 复核结论 |
| --- | --- | --- |
| identity | `manifest_entity_id` | 已包含 |
| identity | `entity_kind` | 已包含，值为 controlled inert manifest entity |
| identity | `entity_status` | 已包含，值为 disabled entity only |
| scope | `scope` | 已包含，值为 docs only |
| source linkage | `created_from` | 已包含，指向 KG-08 manifest candidate |
| source linkage | `created_from_path` | 已包含，指向 KG-08 candidate 路径 |
| source linkage | `linked_registry_candidate` | 已包含，指向 KG-15 registry candidate |
| source linkage | `linked_registry_candidate_path` | 已包含，指向 KG-15 candidate 路径 |
| source policy | `source_mode` | 已包含，值为 `path_and_summary_only` |
| registration | `registration_status` | 已包含，值为 `not_registered` |
| access controls | `enabled` / `runtime_loadable` / `rag_loadable` | 已包含并禁用 |
| registry controls | `prompt_registry_loadable` / `system_instruction_loadable` | 已包含并禁用 |
| evidence controls | `evidence_allowed` / `scoring_allowed` | 已包含并禁用 |
| source controls | `source_files_copied` / `raw_source_text_embedded` | 已包含并禁用 |
| isolation | `isolation_rules` | 已包含 |
| next boundary | `kg32_boundary` | 已包含 |

字段完整性结论：KG-31 entity 覆盖 KG-32 所需静态合规复核字段。

## 4. 禁用字段复核

KG-32 复核 KG-31 entity 的禁用字段如下：

| 字段 | 当前要求 | 复核结论 |
| --- | --- | --- |
| `enabled` | `false` | 通过 |
| `registration_status` | `not_registered` | 通过 |
| `runtime_loadable` | `false` | 通过 |
| `system_instruction_loadable` | `false` | 通过 |
| `rag_loadable` | `false` | 通过 |
| `prompt_registry_loadable` | `false` | 通过 |
| `evidence_allowed` | `false` | 通过 |
| `scoring_allowed` | `false` | 通过 |
| `source_files_copied` | `false` | 通过 |
| `raw_system_instruction_embedded` | `false` | 通过 |
| `raw_prompt_embedded` | `false` | 通过 |
| `raw_source_text_embedded` | `false` | 通过 |
| `writeback_allowed` | `false` | 通过 |
| `export_allowed` | `false` | 通过 |
| `loader_config_present` | `false` | 通过 |
| `endpoint_binding_present` | `false` | 通过 |
| `runtime_registry_entry_present` | `false` | 通过 |

禁用字段结论：KG-31 entity 不具备运行加载、注册、检索、提示词注册、系统指令注册、证据化、评分、写回或导出能力。

## 5. Disabled Flags 复核

KG-31 entity 的 `disabled_flags` 继续保持以下锁定：

| disabled flag | 要求 | 复核结论 |
| --- | --- | --- |
| `enabled` | `false` | 通过 |
| `runtime_access` | `false` | 通过 |
| `runtime_loadable` | `false` | 通过 |
| `rag_enabled` | `false` | 通过 |
| `rag_loadable` | `false` | 通过 |
| `evidence_enabled` | `false` | 通过 |
| `evidence_allowed` | `false` | 通过 |
| `scoring_enabled` | `false` | 通过 |
| `scoring_allowed` | `false` | 通过 |
| `prompt_registry_enabled` | `false` | 通过 |
| `prompt_registry_loadable` | `false` | 通过 |
| `system_instruction_registry_enabled` | `false` | 通过 |
| `system_instruction_loadable` | `false` | 通过 |
| `writeback_enabled` | `false` | 通过 |
| `writeback_allowed` | `false` | 通过 |
| `export_enabled` | `false` | 通过 |
| `export_allowed` | `false` | 通过 |

Disabled flags 结论：所有运行相关开关均保持 false。

## 6. No-Runtime / No-Registration 复核

KG-31 entity 当前位于：

`docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json`

该位置是 docs 非运行目录，不是 `backend`、`frontend`、`config`、运行 registry、任务目录、job、output 或 export 目录。

KG-32 复核结论：

1. KG-31 entity 不是 runtime manifest；
2. KG-31 entity 没有注册；
3. KG-31 entity 没有 runtime loader 配置；
4. KG-31 entity 没有 endpoint 绑定；
5. KG-31 entity 没有 activation id；
6. KG-31 entity 没有 registration id；
7. KG-31 entity 没有 ZBid writeback target；
8. KG-31 entity 没有 export path；
9. KG-31 entity 不应被 ZDoc 自动读取。

## 7. Evidence / Scoring / RAG / Registry 复核

KG-32 确认 KG-31 entity 不允许进入以下链路：

| 链路 | 字段证据 | 复核结论 |
| --- | --- | --- |
| evidence | `evidence_allowed=false` | 不得作为 evidence |
| scoring | `scoring_allowed=false` | 不得作为 scoring basis |
| RAG | `rag_loadable=false` | 不得 RAG 加载 |
| prompt registry | `prompt_registry_loadable=false` | 不得 prompt registry 加载 |
| system instruction registry | `system_instruction_loadable=false` | 不得 system instruction 加载 |
| writeback | `writeback_allowed=false` | 不得写回 |
| export | `export_allowed=false` | 不得导出 |

复核结论：KG-31 entity 不能作为检索、生成、证据、评分、写回或导出输入。

## 8. Source 内容边界复核

KG-31 entity 仅保留 source path、source summary、risk level、domain tags 和 isolation rules。

KG-32 继续确认：

1. `source_files_copied=false`；
2. `raw_source_text_embedded=false`；
3. `raw_system_instruction_embedded=false`；
4. `raw_prompt_embedded=false`；
5. source summary 只作为摘要，不应替代原文；
6. entity 文件未复制 `AI知识图谱大全` 原文件；
7. entity 文件未嵌入系统指令原文；
8. entity 文件未嵌入 prompt 原文；
9. entity 文件未嵌入青天评标或满分门控原文。

## 9. KG-08 / KG-15 状态复核

| 对象 | 当前状态 | KG-32 复核结论 |
| --- | --- | --- |
| KG-08 manifest candidate JSON | `candidate_only` / `not_registered` / disabled | 继续候选、冻结、禁用 |
| KG-15 registry candidate JSON | `registry_candidate_only` / `not_registered` / disabled | 继续候选、冻结、禁用 |
| KG-31 disabled manifest entity JSON | `disabled_entity_only` / `not_registered` / docs-only | 继续静态实体草案 |

KG-32 不修改 KG-08，不修改 KG-15，不修改 KG-31 entity。

## 10. System Instruction 与青天评标隔离复核

KG-32 继续确认：

1. `全能` 不得作为 system instruction；
2. `市政桥梁 KG01` 不得作为 system instruction；
3. `医院装修改造 KG02` 不得作为 system instruction；
4. KG-31 entity 不得进入 system instruction registry；
5. prompt registry 不得绕过 system instruction quarantine；
6. 青天评标 / 满分门控内容不得作为 evidence；
7. 青天评标 / 满分门控内容不得作为 scoring basis；
8. 相关内容不得进入 `/review/apply`；
9. 相关内容不得写回 ZBid；
10. 相关内容不得进入导出链或影响评分。

## 11. 问题分级

| 级别 | 是否存在 | 说明 | 处置 |
| --- | --- | --- | --- |
| Blocker | 否 | 未发现注册、启用、运行加载或系统接入字段 | 可保持静态草案 |
| Major | 否 | 未发现 evidence、scoring、RAG、prompt registry、system instruction registry 可用性 | 继续禁用 |
| Minor | 否 | 未发现需要修改 KG-31 entity 的静态字段缺口 | 不修改既有文件 |
| Note | 是 | KG-31 entity 是首次受控实体化文件，但仍是 docs-only disabled entity | 仅人工复核使用 |

## 12. KG-33 边界建议

KG-33 不得自动进入。若 ChatGPT 后续单独授权 KG-33，建议 KG-33 只能做以下范围之一：

1. registry entity 的隔离禁用草案；
2. KG-31 entity 的进一步人工审查与处置记录。

KG-33 默认仍不得：

1. 接入系统；
2. 注册 manifest；
3. 创建真实 registry；
4. 创建 validator 脚本；
5. 注册、启用、加载任何知识包；
6. 接入 RAG / prompt registry / system instruction registry；
7. 运行服务、Ollama、端口或 endpoint；
8. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
9. 生成 DOCX；
10. 写入 `output/job/export`；
11. 修改 KG-08、KG-15 或 KG-31 entity。

## 13. KG-32 No-Runtime 结论

KG-32 最终结论：

1. KG-31 disabled manifest entity 字段完整性通过静态复核；
2. `enabled=false`、`registration_status=not_registered`、`runtime_loadable=false` 等禁用字段保持有效；
3. KG-31 entity 不得作为 evidence；
4. KG-31 entity 不得作为 scoring basis；
5. KG-31 entity 不得 RAG 加载；
6. KG-31 entity 不得 prompt registry 加载；
7. KG-31 entity 不得 system instruction 加载；
8. KG-08 / KG-15 仍保持候选、冻结、禁用状态；
9. KG-31 entity 当前仅为 docs 非运行目录下的静态实体草案；
10. KG-32 不进入 KG-33。
