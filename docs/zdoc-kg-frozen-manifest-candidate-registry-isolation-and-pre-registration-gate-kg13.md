# ZDoc KG-13 Frozen Manifest Candidate Registry Isolation and Pre-Registration Gate

## 1. KG-13 执行摘要

KG-13 是对 KG-08 frozen disabled manifest candidate 的 docs-only registry isolation 与 pre-registration gate 归档。本步骤只设计预注册隔离门槛，不修改 KG-08 candidate JSON，不创建 registry 文件，不注册 manifest，不创建 validator，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包。

KG-13 结论：KG-08 candidate 经 KG-11 freeze gate 和 KG-12 freeze record 后，仍只能作为 `candidate_only`、`not_registered`、disabled 的 docs candidate。任何进入 registry candidate 草案、运行 registry 或真实注册链路的动作，都必须等待 KG-14 或后续阶段的明确人工授权。

## 2. 复核对象

| 对象 | 路径 | KG-13 用途 |
| --- | --- | --- |
| KG-12 freeze record | `docs/zdoc-kg-controlled-pilot-manifest-candidate-freeze-record-and-next-gate-kg12.md` | 确认冻结对象和冻结后约束 |
| KG-11 disposition gate | `docs/zdoc-kg-controlled-pilot-manifest-candidate-validation-disposition-and-freeze-gate-kg11.md` | 确认 freeze gate 判定条件 |
| KG-08 candidate JSON | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 确认候选实体当前字段状态 |
| KG-08 review | `docs/zdoc-kg-controlled-pilot-disabled-manifest-candidate-kg08-review.md` | 确认非运行态候选实体定位 |

## 3. Frozen Candidate 当前状态确认

| 字段 | 当前状态 | KG-13 结论 |
| --- | --- | --- |
| `pilot_direction` | `全能索引 + 市政桥梁 KG01` | 与首个试点方向一致 |
| `backup_direction` | `全能索引 + 医院装修改造 KG02` | 仅作备选方向记录 |
| `source_mode` | `path_and_summary_only` | 只允许路径与摘要 |
| `status` | `candidate_only` | 仍为候选 |
| `registration_status` | `not_registered` | 未注册 |
| `activation_requires` | `manual_authorization_after_KG08_review` | 仍需人工授权 |
| `enabled` | `false` | 未启用 |
| `runtime_access` | `false` | 运行链路不可访问 |
| `rag_enabled` | `false` | 未接入 RAG |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | `false` | 未接入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 未接入 system instruction registry |
| `writeback_enabled` | `false` | 未启用写回 |
| `export_enabled` | `false` | 未启用导出 |

KG-13 不改变上述状态。上述字段只能作为预注册隔离门槛的输入事实，不代表允许进入 registry。

## 4. Candidate 状态结论

KG-13 继承并确认以下状态结论：

1. candidate 仍保持 `candidate_only`；
2. candidate 仍保持 `not_registered`；
3. candidate 仍保持 disabled；
4. candidate 仍位于 docs 候选区；
5. candidate 不属于运行配置；
6. candidate 不允许被 ZDoc 自动读取；
7. candidate 不允许作为 RAG、prompt registry 或 system instruction registry 的输入；
8. candidate 不允许作为 evidence；
9. candidate 不允许作为 scoring basis；
10. candidate 不允许触发写回、导出、审核应用或生成链路。

## 5. Registry Isolation 设计原则

registry isolation 用于防止 docs candidate 被误认为可注册、可运行或可检索的 manifest。

设计原则如下：

1. registry isolation 优先于 registry registration；
2. frozen candidate 默认停留在 docs 层；
3. 不得从 `docs/kg-manifest-candidates/` 自动扫描并加载 candidate；
4. 不得将 candidate path 写入运行 registry；
5. 不得用文件扩展名或 JSON 格式推断运行权限；
6. 不得因 freeze record 通过而自动创建 registry 文件；
7. 不得因 pre-registration gate 通过而自动注册 manifest；
8. 所有 registry 相关状态必须显式记录为 disabled / not registered；
9. 所有 registry 变更必须经过人工授权、静态校验和单独提交；
10. registry isolation 失败时，后续注册流程必须停止。

## 6. Pre-Registration Gate 字段清单

未来若设计 registry candidate 草案，pre-registration gate 至少应检查以下字段，但 KG-13 不创建该实体文件。

| 字段 | 必须值或要求 | 说明 |
| --- | --- | --- |
| `candidate_id` | 非空、稳定、不可与运行 ID 混用 | 仅用于候选识别 |
| `source_candidate_path` | 指向 KG-08 candidate JSON | 只作溯源 |
| `source_mode` | `path_and_summary_only` | 不得承载正文 |
| `status` | `candidate_only` | 不得改为 active |
| `registration_status` | `not_registered` | 不得改为 registered |
| `registry_candidate_status` | `draft_only` 或等价禁用态 | 不得表示可运行 |
| `enabled` | `false` | 不启用 |
| `runtime_access` | `false` | 不允许运行访问 |
| `rag_enabled` | `false` | 不进入 RAG registry |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 不进入 system instruction registry |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `writeback_enabled` | `false` | 不写回 |
| `export_enabled` | `false` | 不导出 |
| `manual_review_required` | `true` | 必须人工复核 |
| `review_status` | `pending` | 未审核不得推进 |
| `risk_level` | 保持原候选风险或更高 | 不得自动降级 |
| `isolation_rules` | 包含非运行、非 evidence、非 scoring、系统指令隔离规则 | 隔离规则不得缺失 |
| `allowed_next_step` | 仅允许人工授权后的下一阶段 | 不得自动推进 |

该清单只是 KG-13 的设计门槛，不是 registry 文件内容，也不是注册授权。

## 7. 禁止进入运行 Registry 的条件

出现以下任一条件时，candidate 不得进入运行 registry：

1. `enabled` 不为 `false`；
2. `runtime_access` 不为 `false`；
3. `registration_status` 不为 `not_registered`；
4. `status` 不为 `candidate_only`；
5. `source_mode` 不为 `path_and_summary_only`；
6. 出现源文件正文、系统指令原文、prompt 原文、青天评标原文或满分门控原文；
7. 出现 `runtime_config`、`endpoint`、`service_name` 或运行入口；
8. 出现 `rag_index`、`embedding_model` 或检索索引配置；
9. 出现 `prompt_template` 或 generation prompt；
10. 出现 `system_instruction` 正文字段；
11. 出现 `evidence`、`scoring_basis` 或 `score_rules` 字段；
12. 出现 `writeback_target` 或 `export_target`；
13. 缺少 `not_evidence`；
14. 缺少 `not_scoring_basis`；
15. 缺少系统指令隔离规则；
16. 缺少人工复核状态；
17. 未取得 ChatGPT 总控明确人工授权。

任何一项触发时，后续流程必须停留在 docs 层，不得注册。

## 8. 允许进入后续 Registry Candidate 草案的人工授权条件

KG-13 不创建 registry candidate 草案。若 KG-14 或后续阶段希望推进，只能在以下条件全部满足后，进入新的人工授权任务：

1. ChatGPT 总控明确授权 KG-14；
2. 明确唯一输出文件路径；
3. 明确是否仍为 docs-only；
4. 明确禁止修改 KG-08 candidate JSON；
5. 明确禁止创建运行 registry；
6. 明确禁止接入 RAG / prompt registry / system instruction registry；
7. 明确禁止启用任何知识包；
8. 明确所有 registry candidate 字段默认 disabled；
9. 明确 registry candidate 不得被运行链路自动读取；
10. 明确不得 evidence 化或评分依据化；
11. 明确不得运行服务、Ollama、端口或 endpoint；
12. 明确不得触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
13. 明确不得写 `output/job/export`。

上述条件满足，也只意味着可以设计或归档 registry candidate 草案，不意味着可以注册 manifest。

## 9. RAG Registry 隔离边界

RAG registry 隔离边界如下：

1. `rag_enabled=false` 必须保持；
2. 不得创建 RAG index；
3. 不得创建 embedding 配置；
4. 不得将 source path 自动加入检索语料；
5. 不得把 source summary 当作可检索正文；
6. 不得将 candidate 注册为 retrieval corpus；
7. 不得生成向量；
8. 不得运行任何检索链路；
9. 后续即使创建 registry candidate 草案，也必须默认 `allow_retrieval=false` 或等价禁用态。

KG-13 不授权任何 RAG 接入。

## 10. Prompt Registry 隔离边界

prompt registry 隔离边界如下：

1. `prompt_registry_enabled=false` 必须保持；
2. 不得把 source summary 转成 prompt template；
3. 不得把系统指令类内容改写后绕道进入 prompt registry；
4. 不得创建 generation prompt；
5. 不得创建 prompt pack；
6. 不得让 candidate 参与 `/generate`；
7. 不得把全能索引或市政桥梁 KG01 作为 prompt 启用项；
8. 后续即使创建 registry candidate 草案，也必须默认 prompt registry 禁用。

KG-13 不授权任何 prompt registry 接入。

## 11. System Instruction Registry 隔离边界

system instruction registry 隔离边界如下：

1. `system_instruction_registry_enabled=false` 必须保持；
2. 系统指令类内容不得原样转为 ZDoc system instruction；
3. candidate JSON 不得新增 `system_instruction` 正文字段；
4. source summary 不得改写成隐性 system instruction；
5. 不得创建 system instruction pack；
6. 不得将全能索引或任何 KG 文件作为系统指令启用；
7. 不得通过 prompt registry 绕过 system instruction 隔离；
8. 后续若需要提取约束思想，必须人工拆解、降权、改写并重新评审。

KG-13 不授权任何 system instruction registry 接入。

## 12. System Instruction 隔离结论

KG-13 结论：系统指令类内容继续隔离，不得转为 ZDoc system instruction。

本结论适用于：

1. KG-08 candidate 中的顶层隔离规则；
2. 后续可能出现的 registry candidate 草案；
3. 全能索引相关资料；
4. 市政桥梁 KG01 试点资料；
5. 医院装修改造 KG02 备选资料；
6. 任何被识别为系统指令、执行命令、写回、导出、提交、覆盖或自动评分的内容。

## 13. 青天评标 / 满分门控隔离结论

KG-13 结论：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

强制边界如下：

1. `evidence_enabled=false` 必须保持；
2. `scoring_enabled=false` 必须保持；
3. `not_evidence` 必须保持；
4. `not_scoring_basis` 必须保持；
5. 不得作为自动评分依据；
6. 不得作为满分门控依据；
7. 不得作为复评优化依据；
8. 不得作为 ZBid 写回依据；
9. 不得进入 `/review/apply`；
10. 不得生成正式证据引用。

## 14. KG-14 授权条件

KG-14 不得自动进入。若 ChatGPT 总控决定继续，建议 KG-14 只允许在明确人工授权后执行，并优先限定为以下事项之一：

1. 设计 docs-only registry candidate 草案文件；
2. 设计 registry candidate 字段映射，但不注册；
3. 设计 pre-registration checklist，但不创建 validator；
4. 设计人工审核签署字段；
5. 设计 registry isolation 审计规则；
6. 复核是否需要真实 validator，但不创建脚本；
7. 复核是否需要将 freeze record 与 registry candidate 关联，但不修改 KG-08 candidate JSON。

KG-14 如涉及以下动作，必须取得更高等级明确授权：

1. 修改 KG-08 candidate JSON；
2. 创建 registry 文件；
3. 注册 manifest；
4. 创建真实 validator 脚本；
5. 接入 RAG / prompt registry / system instruction registry；
6. 启用任何知识包；
7. 运行 ZDoc、ZBid、Ollama、端口或 endpoint；
8. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
9. 生成 DOCX；
10. 写入 `output/job/export`；
11. 复制、移动、删除、重命名或改写 `AI知识图谱大全` 原文件。

## 15. KG-13 最终结论

KG-13 最终结论如下：

1. frozen candidate 当前仍是 `candidate_only`；
2. frozen candidate 当前仍是 `not_registered`；
3. frozen candidate 当前仍是 disabled；
4. registry isolation 必须优先于任何 registration；
5. pre-registration gate 只能作为后续人工授权前的设计门槛；
6. KG-13 不创建 registry 文件；
7. KG-13 不注册 manifest；
8. KG-13 不接入 RAG、prompt registry 或 system instruction registry；
9. system instruction 类内容继续不得转为 system instruction；
10. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
11. KG-14 必须再次由 ChatGPT 总控人工授权，不得自动进入。
