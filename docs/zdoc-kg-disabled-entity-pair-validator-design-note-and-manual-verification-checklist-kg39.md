# ZDoc KG-39 Disabled Entity Pair Validator Design Note and Manual Verification Checklist

## 1. KG-39 执行摘要

KG-39 是 disabled entity pair 的 docs-only validator 设计说明与人工校验清单。本步骤只形成设计文档，不创建 validator 脚本，不运行校验器，不接入 CI，不接入 ZDoc 运行链路，不修改 KG-31 manifest entity JSON，不修改 KG-33 registry entity JSON，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON。

KG-39 设计结论：后续若需要 validator，应先以静态字段一致性、禁用字段锁定、候选来源链路、docs 非运行目录位置、不可加载状态为核心校验目标。KG-39 仅定义目标、输入、输出、检查项、失败判定和人工复核要求，不授予脚本创建或系统接入权限。

## 2. 复核依据

KG-39 复核并承接以下对象：

| 对象 | 文件 | 当前状态 |
| --- | --- | --- |
| KG-08 manifest candidate | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | `candidate_only` / `not_registered` / disabled |
| KG-15 registry candidate | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | `registry_candidate_only` / `not_registered` / disabled |
| KG-31 disabled manifest entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | `disabled_entity_only` / `not_registered` / disabled |
| KG-33 disabled registry entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | `disabled_registry_entity_only` / `not_registered` / disabled |
| KG-35 static consistency review | `docs/zdoc-kg-disabled-manifest-registry-entity-pair-static-consistency-and-no-runtime-review-kg35.md` | pair 一致性复核依据 |
| KG-38 authorization disposition | `docs/zdoc-kg-disabled-entity-pair-final-authorization-disposition-and-next-stage-freeze-gate-kg38.md` | 不授权真实接入，冻结 KG-39 范围 |

KG-39 不读取、复制、移动、删除或改写 `AI知识图谱大全` 原文件。

## 3. KG-31 / KG-33 / KG-38 结论汇总

| 来源 | 关键结论 | KG-39 承接 |
| --- | --- | --- |
| KG-31 disabled manifest entity | manifest entity 位于 docs 非运行目录，`enabled=false`、`registration_status=not_registered`、`runtime_loadable=false` | 作为 validator 设计的 manifest 侧输入 |
| KG-33 disabled registry entity | registry entity 位于 docs 非运行目录，`runtime_registered=false`、`registry_loadable=false`、`manifest_entity_loadable=false` | 作为 validator 设计的 registry 侧输入 |
| KG-38 authorization disposition | 当前不授权真实注册、真实启用、真实加载或真实系统接入；KG-39 只能做 validator 设计说明或人工校验清单 | KG-39 不创建脚本、不运行校验、不接入系统 |

## 4. Validator 目标设计

后续 validator 若获单独授权，其目标应限定为静态、只读、非运行态检查。KG-39 仅设计目标，不实现 validator。

建议目标：

1. 验证 KG-31 manifest entity 与 KG-33 registry entity 均在 docs 非运行目录；
2. 验证 KG-31 / KG-33 均保持 `enabled=false`；
3. 验证 KG-31 / KG-33 均保持 `registration_status=not_registered`；
4. 验证 KG-31 / KG-33 均保持不可运行加载；
5. 验证 KG-31 / KG-33 均不得 evidence、不得 scoring；
6. 验证 KG-31 / KG-33 均不得 RAG 加载、prompt registry 加载、system instruction registry 加载；
7. 验证 KG-33 对 KG-31 的引用路径一致；
8. 验证 KG-31 来源于 KG-08，KG-33 来源于 KG-15；
9. 验证 source mode 仍为 `path_and_summary_only`；
10. 验证未复制、未嵌入 `AI知识图谱大全` 原文、系统指令原文或 prompt 原文。

## 5. Validator 输入设计

后续 validator 的输入只应为已冻结的 docs 下静态文件路径，不应扫描运行目录，不应读取原始知识图谱正文。

建议输入：

| 输入 | 路径 | 用途 |
| --- | --- | --- |
| manifest candidate | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 校验 KG-08 来源状态 |
| registry candidate | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 校验 KG-15 来源状态 |
| manifest entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | 校验 KG-31 manifest 侧字段 |
| registry entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | 校验 KG-33 registry 侧字段 |

禁止输入：

1. `AI知识图谱大全` 原文件正文；
2. backend / frontend / config 运行配置；
3. job / output / export 目录；
4. 端口、endpoint 或服务响应；
5. RAG index；
6. prompt registry；
7. system instruction registry；
8. ZBid 写回目标。

## 6. Validator 输出设计

后续 validator 若获授权，输出应是静态报告，不得写入运行目录，不得生成 DOCX，不得更新 JSON 实体文件。

建议输出字段：

| 输出字段 | 含义 |
| --- | --- |
| `validation_status` | `pass` / `fail` / `manual_review_required` |
| `checked_files` | 被检查的 docs 文件路径 |
| `failed_checks` | 失败检查项列表 |
| `warning_checks` | 需人工注意的非阻断项 |
| `blocked_runtime_actions` | 确认仍被阻断的运行行为 |
| `manual_review_required` | 是否必须人工复核 |
| `review_notes` | 人工复核备注 |

输出边界：

1. 不修改 KG-08 / KG-15 / KG-31 / KG-33；
2. 不写 backend / frontend / config；
3. 不写 job / output / export；
4. 不生成真实 registry；
5. 不生成 DOCX；
6. 不注册、不启用、不加载任何知识包。

## 7. 静态检查项设计

| 检查项 | 期望值 | 失败判定 |
| --- | --- | --- |
| KG-31 `scope` | `docs_only` | 非 `docs_only` 即失败 |
| KG-33 `scope` | `docs_only` | 非 `docs_only` 即失败 |
| KG-31 `entity_status` | `disabled_entity_only` | 不匹配即失败 |
| KG-33 `entity_status` | `disabled_registry_entity_only` | 不匹配即失败 |
| KG-31 `registration_status` | `not_registered` | 不匹配即失败 |
| KG-33 `registration_status` | `not_registered` | 不匹配即失败 |
| KG-31 `enabled` | `false` | 不是 false 即失败 |
| KG-33 `enabled` | `false` | 不是 false 即失败 |
| KG-31 `runtime_loadable` | `false` | 不是 false 即失败 |
| KG-33 `runtime_loadable` | `false` | 不是 false 即失败 |
| KG-33 `runtime_registered` | `false` | 不是 false 即失败 |
| KG-33 `registry_loadable` | `false` | 不是 false 即失败 |
| KG-33 `manifest_entity_registered` | `false` | 不是 false 即失败 |
| KG-33 `manifest_entity_loadable` | `false` | 不是 false 即失败 |
| KG-31 / KG-33 `rag_loadable` | `false` | 任一不是 false 即失败 |
| KG-31 / KG-33 `prompt_registry_loadable` | `false` | 任一不是 false 即失败 |
| KG-31 / KG-33 `system_instruction_loadable` | `false` | 任一不是 false 即失败 |
| KG-31 / KG-33 `evidence_allowed` | `false` | 任一不是 false 即失败 |
| KG-31 / KG-33 `scoring_allowed` | `false` | 任一不是 false 即失败 |
| KG-31 / KG-33 `source_files_copied` | `false` | 任一不是 false 即失败 |
| KG-31 / KG-33 `raw_source_text_embedded` | `false` | 任一不是 false 即失败 |
| KG-31 / KG-33 `raw_system_instruction_embedded` | `false` | 任一不是 false 即失败 |
| KG-31 / KG-33 `raw_prompt_embedded` | `false` | 任一不是 false 即失败 |

## 8. Pair 引用关系检查设计

| 引用关系 | 期望 | 失败判定 |
| --- | --- | --- |
| KG-31 `created_from_path` | 指向 KG-08 manifest candidate | 不匹配即失败 |
| KG-31 `linked_registry_candidate_path` | 指向 KG-15 registry candidate | 不匹配即失败 |
| KG-33 `created_from_path` | 指向 KG-15 registry candidate | 不匹配即失败 |
| KG-33 `linked_manifest_candidate_path` | 指向 KG-08 manifest candidate | 不匹配即失败 |
| KG-33 `linked_manifest_entity_path` | 指向 KG-31 manifest entity | 不匹配即失败 |
| KG-31 / KG-33 `source_mode` | `path_and_summary_only` | 任一不匹配即失败 |
| KG-31 / KG-33 `risk_level` | `R2` | 任一不匹配需人工复核 |
| KG-31 / KG-33 `domain_tags` | 包含 `general_index`、`municipal_bridge_kg01`、`backup_hospital_renovation_kg02` | 缺失任一标签需人工复核 |

## 9. Manual Verification Checklist

人工复核时应逐项确认：

| 序号 | 检查项 | 期望结论 | 人工勾选 |
| --- | --- | --- | --- |
| 1 | KG-31 文件仍位于 `docs/kg-controlled-entities/` | 是 | 待勾选 |
| 2 | KG-33 文件仍位于 `docs/kg-controlled-entities/` | 是 | 待勾选 |
| 3 | KG-31 `enabled=false` | 是 | 待勾选 |
| 4 | KG-33 `enabled=false` | 是 | 待勾选 |
| 5 | KG-31 `registration_status=not_registered` | 是 | 待勾选 |
| 6 | KG-33 `registration_status=not_registered` | 是 | 待勾选 |
| 7 | KG-31 `runtime_loadable=false` | 是 | 待勾选 |
| 8 | KG-33 `runtime_loadable=false` | 是 | 待勾选 |
| 9 | KG-33 `runtime_registered=false` | 是 | 待勾选 |
| 10 | KG-33 `registry_loadable=false` | 是 | 待勾选 |
| 11 | KG-31 `evidence_allowed=false` | 是 | 待勾选 |
| 12 | KG-33 `evidence_allowed=false` | 是 | 待勾选 |
| 13 | KG-31 `scoring_allowed=false` | 是 | 待勾选 |
| 14 | KG-33 `scoring_allowed=false` | 是 | 待勾选 |
| 15 | KG-31 `rag_loadable=false` | 是 | 待勾选 |
| 16 | KG-33 `rag_loadable=false` | 是 | 待勾选 |
| 17 | KG-31 `prompt_registry_loadable=false` | 是 | 待勾选 |
| 18 | KG-33 `prompt_registry_loadable=false` | 是 | 待勾选 |
| 19 | KG-31 `system_instruction_loadable=false` | 是 | 待勾选 |
| 20 | KG-33 `system_instruction_loadable=false` | 是 | 待勾选 |
| 21 | KG-33 指向 KG-31 manifest entity | 是 | 待勾选 |
| 22 | KG-31 来源指向 KG-08 manifest candidate | 是 | 待勾选 |
| 23 | KG-33 来源指向 KG-15 registry candidate | 是 | 待勾选 |
| 24 | 未复制 `AI知识图谱大全` 原文件 | 是 | 待勾选 |
| 25 | 未创建 validator 脚本 | 是 | 待勾选 |
| 26 | 未接入 CI | 是 | 待勾选 |
| 27 | 未接入系统运行链路 | 是 | 待勾选 |

## 10. 失败判定规则

以下任一情况应判定为 fail：

1. 任何 entity 的 `enabled` 不是 false；
2. 任何 entity 的 `registration_status` 不是 `not_registered`；
3. 任何运行加载字段为 true；
4. 任何 RAG / prompt registry / system instruction registry 加载字段为 true；
5. 任何 evidence 或 scoring 字段为 true；
6. KG-33 不再指向 KG-31 manifest entity；
7. KG-31 / KG-33 不再位于 docs 非运行目录；
8. 出现 backend / frontend / config 写入；
9. 出现 validator 脚本；
10. 出现真实 registry；
11. 出现服务、端口、endpoint、生成、导出、review apply 或 ZBid 写回痕迹；
12. 出现 `AI知识图谱大全` 原文复制或嵌入。

以下情况应判定为 `manual_review_required`：

1. `risk_level` 非 `R2`；
2. `domain_tags` 缺失；
3. `review_status` 发生变化；
4. 新增隔离规则但未有人工说明；
5. source summary 变得过长或疑似搬运原文；
6. KG-08 / KG-15 状态发生变化。

## 11. 人工复核要求

人工复核应满足以下要求：

1. 复核者应先确认本步骤没有创建 validator 脚本；
2. 复核者应确认本步骤没有运行任何校验器；
3. 复核者应确认本步骤没有接入 CI；
4. 复核者应逐项检查 KG-31 / KG-33 禁用字段；
5. 复核者应检查 KG-31 / KG-33 pair 引用关系；
6. 复核者应确认 KG-08 / KG-15 仍为候选、未注册、禁用；
7. 复核者应确认未读取或复制 `AI知识图谱大全` 原文；
8. 复核者应确认当前文档仅为设计说明和人工校验清单。

## 12. KG-40 边界

KG-40 不得自动进入，必须由 ChatGPT 总控单独审核授权。

KG-40 若继续，只能选择以下范围之一：

1. validator implementation authorization request；
2. 进一步 docs-only 审查；
3. validator 设计说明的人工验收记录。

KG-40 默认仍不得：

1. 创建 validator 脚本；
2. 创建真实 registry；
3. 注册 manifest；
4. 注册 registry；
5. 启用 knowledge pack；
6. 接入 RAG / prompt registry / system instruction registry；
7. 运行服务、Ollama、端口或 endpoint；
8. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
9. 生成 DOCX；
10. 写入 `output/job/export`；
11. 修改 KG-08、KG-15、KG-31 或 KG-33；
12. 复制、移动、删除或改写 `AI知识图谱大全` 文件。

## 13. KG-39 最终结论

KG-39 最终结论：

1. 已汇总 KG-31 disabled manifest entity、KG-33 disabled registry entity 与 KG-38 授权处置结论；
2. 已设计 validator 的目标、输入、输出、检查项、失败判定和人工复核要求；
3. 已建立 manual verification checklist；
4. 已覆盖 `enabled=false`、`not_registered`、`runtime_loadable=false`、`evidence_allowed=false`、`scoring_allowed=false` 等禁用字段；
5. 已覆盖 pair 引用关系、候选来源、docs 非运行目录位置和不可加载状态；
6. 本步骤只形成设计说明，不生成脚本、不运行校验、不接入 CI、不接入系统；
7. KG-40 如需继续，只能做 validator implementation authorization request 或进一步 docs-only 审查；
8. KG-39 不进入 KG-40，不执行任何真实创建、注册、接入、启用、校验器运行或运行动作。
