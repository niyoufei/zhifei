# ZDoc KG-16 Disabled Registry Candidate Static Validation Rules

## 1. KG-16 执行摘要

KG-16 是对 KG-15 disabled registry candidate JSON 的 docs-only 静态校验规则设计。本步骤只定义规则，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON，不创建真实 validator 脚本，不注册 manifest，不创建真实 registry 文件，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包。

KG-16 结论：KG-15 registry candidate 当前仍是 `registry_candidate_only`、`not_registered`、disabled 的 docs candidate。后续任何 KG-17 动作必须再次由 ChatGPT 总控人工授权，不得自动进入。

## 2. 复核对象

| 对象 | 路径 | KG-16 用途 |
| --- | --- | --- |
| KG-15 registry candidate JSON | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 设计静态校验规则的直接对象 |
| KG-15 review | `docs/zdoc-kg-disabled-registry-candidate-entity-creation-kg15-review.md` | 承接 docs-only、非 registry、不可自动读取结论 |
| KG-14 schema draft | `docs/zdoc-kg-frozen-candidate-registry-candidate-schema-and-disabled-pre-registration-draft-kg14.md` | 承接 schema 和 disabled pre-registration draft 约束 |
| KG-08 manifest candidate JSON | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 校验 registry candidate 的 linked path 指向 |

## 3. KG-15 Registry Candidate JSON 静态复核摘要

| 字段或规则 | 当前状态 | KG-16 复核结论 |
| --- | --- | --- |
| `registry_candidate_id` | 非空 | 可作为候选 ID |
| `manifest_candidate_path` | 指向 docs 下 KG-08 frozen manifest candidate | 符合溯源边界 |
| `linked_manifest_candidate_path` | 指向同一 docs 下 KG-08 frozen manifest candidate | 符合关联边界 |
| `pilot_direction` | `全能索引 + 市政桥梁 KG01` | 与试点方向一致 |
| `backup_direction` | `全能索引 + 医院装修改造 KG02` | 仅为备选记录 |
| `source_mode` | `path_and_summary_only` | 符合禁止正文承载规则 |
| `status` | `registry_candidate_only` | 符合候选态 |
| `registration_status` | `not_registered` | 未注册 |
| `activation_requires` | `manual_authorization_after_KG15_review` | 需要人工授权 |
| `disabled_flags` | 全部为 boolean `false` | 禁用状态成立 |
| `manual_authorization_required` | `true` | 人工授权必需 |
| `risk_level` | `R2` | 仅为候选风险，不代表可运行 |
| `domain_tags` | 非空数组 | 仅作静态标签 |

KG-16 不改变上述字段，只把当前可接受状态固化为后续静态校验规则。

## 4. 必填字段校验规则

未来静态校验应要求 KG-15 registry candidate JSON 至少包含以下顶层字段：

| 字段 | 校验规则 |
| --- | --- |
| `registry_candidate_id` | 必须存在，且为非空字符串 |
| `manifest_candidate_path` | 必须存在，且指向 docs 下 frozen manifest candidate |
| `linked_manifest_candidate_path` | 必须存在，且与 `manifest_candidate_path` 指向同一 frozen manifest candidate |
| `pilot_direction` | 必须存在，且等于 `全能索引 + 市政桥梁 KG01` |
| `backup_direction` | 必须存在，且等于 `全能索引 + 医院装修改造 KG02` |
| `source_mode` | 必须存在，且等于 `path_and_summary_only` |
| `status` | 必须存在，且等于 `registry_candidate_only` |
| `registration_status` | 必须存在，且等于 `not_registered` |
| `activation_requires` | 必须存在，且等于 `manual_authorization_after_KG15_review` |
| `disabled_flags` | 必须存在，且为对象 |
| `isolation_rules` | 必须存在，且为非空数组 |
| `pre_registration_rules` | 必须存在，且为对象 |
| `manual_authorization_required` | 必须存在，且为 boolean `true` |
| `risk_level` | 必须存在，且使用 R0 / R1 / R2 / R3 / R4 |
| `domain_tags` | 必须存在，且为非空数组 |
| `future_authorization_conditions` | 必须存在，且为非空数组 |

缺少任一必填字段时，应判定静态校验失败。

## 5. 禁止字段校验规则

registry candidate JSON 不得包含会被误解为运行、注册、检索、生成、评分、写回或导出的字段。

| 禁止字段 | 禁止原因 |
| --- | --- |
| `runtime_config` | 暗示进入运行配置 |
| `service_name` | 暗示服务接入 |
| `endpoint` | 暗示 endpoint 访问 |
| `registry_id` | 暗示已进入真实 registry |
| `manifest_registry_id` | 暗示已注册 manifest |
| `active_registry` | 暗示已激活 registry |
| `rag_index` | 暗示 RAG 索引 |
| `embedding_model` | 暗示向量化或检索链路 |
| `corpus_path` | 暗示语料注册 |
| `prompt_template` | 暗示 prompt registry |
| `generation_prompt` | 暗示参与生成 |
| `system_instruction` | 暗示 system instruction registry |
| `evidence` | 暗示证据化 |
| `scoring_basis` | 暗示评分依据 |
| `score_rules` | 暗示自动评分规则 |
| `writeback_target` | 暗示写回目标 |
| `export_target` | 暗示导出目标 |

出现任一禁止字段，应判定静态校验失败。

## 6. Path 指向校验规则

`manifest_candidate_path` 与 `linked_manifest_candidate_path` 必须同时满足：

1. 字段必须存在；
2. 字段必须为字符串；
3. 字段值必须相同；
4. 字段值必须等于 `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`；
5. 字段值必须指向 docs 下 frozen manifest candidate；
6. 字段值不得指向 `/Users/youfeini/Desktop/AI知识图谱大全` 原文件；
7. 字段值不得指向 backend、frontend、config、tests、output、job 或 export；
8. 字段值不得被解释为运行时读取授权；
9. 字段值不得被解释为 RAG corpus path；
10. 字段值不得被解释为 prompt 或 system instruction source。

如路径缺失、路径不一致、路径指向非 docs frozen candidate 或路径指向运行目录，应判定静态校验失败。

## 7. Status 校验规则

`status` 必须等于：

```text
registry_candidate_only
```

静态校验失败条件：

1. `status` 缺失；
2. `status` 不等于 `registry_candidate_only`；
3. 出现 `active`、`enabled`、`runtime`、`production`、`registered`、`approved_for_runtime` 等状态值；
4. 出现绕过候选态的同义字段。

## 8. Registration Status 校验规则

`registration_status` 必须等于：

```text
not_registered
```

静态校验失败条件：

1. `registration_status` 缺失；
2. `registration_status` 不等于 `not_registered`；
3. 出现 `registered`、`active`、`mounted`、`loaded`、`indexed` 等状态值；
4. 出现任何 registry ID、runtime ID 或 endpoint ID。

## 9. Source Mode 校验规则

`source_mode` 必须等于：

```text
path_and_summary_only
```

静态校验失败条件：

1. `source_mode` 缺失；
2. `source_mode` 不等于 `path_and_summary_only`；
3. 出现 `source_text`、`source_content`、`full_text`、`raw_content` 等正文承载字段；
4. 出现源文件原文、系统指令原文、prompt 原文、青天评标原文或满分门控原文。

## 10. Disabled Flags 校验规则

`disabled_flags` 必须包含以下字段，且全部为 boolean `false`：

| 字段 | 必须值 |
| --- | --- |
| `enabled` | `false` |
| `runtime_access` | `false` |
| `rag_enabled` | `false` |
| `evidence_enabled` | `false` |
| `scoring_enabled` | `false` |
| `prompt_registry_enabled` | `false` |
| `system_instruction_registry_enabled` | `false` |
| `writeback_enabled` | `false` |
| `export_enabled` | `false` |

静态校验失败条件：

1. 任一字段缺失；
2. 任一字段不是 boolean；
3. 任一字段为 `true`；
4. 任一字段使用字符串 `"false"` 代替 boolean `false`；
5. 存在同义启用字段或绕过字段。

## 11. Isolation Rules 校验规则

顶层 `isolation_rules` 必须为非空数组，并至少包含以下规则：

| 规则 | 含义 |
| --- | --- |
| `docs_only_registry_candidate` | 只属于 docs 候选实体 |
| `not_real_registry_file` | 不是真实 registry 文件 |
| `not_registered_manifest` | 未注册 manifest |
| `not_runtime_readable` | 运行链路不可读取 |
| `manifest_candidate_path_points_to_docs_frozen_candidate_only` | 只指向 docs frozen candidate |
| `source_mode_path_and_summary_only` | 只允许路径与摘要模式 |
| `rag_registry_disabled` | RAG registry 禁用 |
| `prompt_registry_disabled` | prompt registry 禁用 |
| `system_instruction_registry_disabled` | system instruction registry 禁用 |
| `system_instruction_sources_must_remain_quarantined` | 系统指令继续隔离 |
| `qingtian_review_and_full_score_gate_sources_are_reference_candidates_only` | 青天评标 / 满分门控仅作参考候选 |
| `not_evidence` | 不作为 evidence |
| `not_scoring_basis` | 不作为评分依据 |
| `not_loaded_by_generate_export_review_or_writeback` | 不被生成、导出、审核或写回链路读取 |

缺少上述关键规则时，应判定静态校验失败。

## 12. Pre-Registration Rules 校验规则

`pre_registration_rules` 必须为对象，并满足以下要求：

| 字段 | 必须值 |
| --- | --- |
| `pre_registration_status` | `draft_only` |
| `manual_review_required` | `true` |
| `review_status` | `pending` |
| `approval_status` | `not_approved` |
| `registration_must_remain_not_registered` | `true` |
| `runtime_registry_forbidden` | `true` |
| `rag_registry_forbidden` | `true` |
| `prompt_registry_forbidden` | `true` |
| `system_instruction_registry_forbidden` | `true` |
| `evidence_forbidden` | `true` |
| `scoring_basis_forbidden` | `true` |
| `writeback_forbidden` | `true` |
| `export_forbidden` | `true` |

静态校验失败条件：

1. `pre_registration_rules` 缺失；
2. `pre_registration_rules` 不是对象；
3. 任一禁止字段不为 `true`；
4. `pre_registration_status` 不为 `draft_only`；
5. `approval_status` 表示已批准；
6. `review_status` 表示已通过或已启用。

## 13. Manual Authorization 校验规则

`manual_authorization_required` 必须为 boolean `true`。

`future_authorization_conditions` 必须为非空数组，并至少表达以下含义：

1. KG-17 或后续阶段必须单独授权；
2. 不得修改 KG-08 manifest candidate；
3. 不得注册 manifest；
4. 不得创建真实 registry 文件；
5. 不得启用 runtime access；
6. 不得启用 RAG、prompt registry 或 system instruction registry；
7. 不得启用 evidence、scoring、writeback 或 export；
8. 不得运行服务、Ollama、端口或 endpoint。

缺少人工授权要求，应判定静态校验失败。

## 14. RAG Registry 隔离校验规则

RAG registry 隔离必须满足：

1. `disabled_flags.rag_enabled=false`；
2. `pre_registration_rules.rag_registry_forbidden=true`；
3. `isolation_rules` 包含 `rag_registry_disabled`；
4. 不存在 `rag_index`；
5. 不存在 `embedding_model`；
6. 不存在 `corpus_path`；
7. 不得将 `manifest_candidate_path` 解释为 RAG corpus path；
8. 不得生成或引用向量索引。

任一条件不满足，应判定静态校验失败。

## 15. Prompt Registry 隔离校验规则

prompt registry 隔离必须满足：

1. `disabled_flags.prompt_registry_enabled=false`；
2. `pre_registration_rules.prompt_registry_forbidden=true`；
3. `isolation_rules` 包含 `prompt_registry_disabled`；
4. 不存在 `prompt_template`；
5. 不存在 `generation_prompt`；
6. 不得把 source summary 或 path 改写成 prompt；
7. 不得通过 prompt registry 绕过 system instruction 隔离。

任一条件不满足，应判定静态校验失败。

## 16. System Instruction Registry 隔离校验规则

system instruction registry 隔离必须满足：

1. `disabled_flags.system_instruction_registry_enabled=false`；
2. `pre_registration_rules.system_instruction_registry_forbidden=true`；
3. `isolation_rules` 包含 `system_instruction_registry_disabled`；
4. `isolation_rules` 包含 `system_instruction_sources_must_remain_quarantined`；
5. 不存在 `system_instruction` 正文字段；
6. 不存在系统指令原文；
7. 不得把 source summary 改写成隐性 system instruction；
8. 不得通过 prompt registry 绕过隔离。

任一条件不满足，应判定静态校验失败。

## 17. System Instruction 类内容校验结论

系统指令类内容不得转为 ZDoc system instruction。

静态校验应确认：

1. registry candidate 未包含系统指令原文；
2. registry candidate 未包含可执行系统约束；
3. registry candidate 未包含写回、导出、提交、覆盖或自动评分命令；
4. `system_instruction_registry_enabled=false`；
5. `system_instruction_registry_forbidden=true`；
6. system instruction 隔离规则存在。

任何系统指令化迹象都应判定失败。

## 18. 青天评标 / 满分门控校验规则

青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

静态校验应确认：

1. `disabled_flags.evidence_enabled=false`；
2. `disabled_flags.scoring_enabled=false`；
3. `pre_registration_rules.evidence_forbidden=true`；
4. `pre_registration_rules.scoring_basis_forbidden=true`；
5. `isolation_rules` 包含 `not_evidence`；
6. `isolation_rules` 包含 `not_scoring_basis`；
7. 不存在 `evidence` 字段；
8. 不存在 `scoring_basis` 字段；
9. 不存在 `score_rules` 字段；
10. 不存在青天评标 / 满分门控原文；
11. 不存在自动评分、复评、满分优化或 ZBid 写回规则。

任一条件不满足，应判定静态校验失败。

## 19. 静态校验失败条件总表

未来静态校验如发现以下任一情况，应判定失败：

| 失败条件 | 处置 |
| --- | --- |
| registry candidate JSON 语法无效 | 停止 |
| 必填字段缺失 | 停止 |
| 出现禁止字段 | 停止 |
| `manifest_candidate_path` 与 `linked_manifest_candidate_path` 缺失或不一致 | 停止 |
| path 未指向 docs 下 frozen manifest candidate | 停止 |
| `status` 不为 `registry_candidate_only` | 停止 |
| `registration_status` 不为 `not_registered` | 停止 |
| `source_mode` 不为 `path_and_summary_only` | 停止 |
| 任一 disabled flag 不为 boolean `false` | 停止 |
| `manual_authorization_required` 不为 boolean `true` | 停止 |
| `pre_registration_status` 不为 `draft_only` | 停止 |
| `approval_status` 表示已批准 | 停止 |
| 缺少 isolation rules | 停止 |
| RAG / prompt / system instruction registry 隔离失败 | 停止 |
| 系统指令内容未隔离 | 停止 |
| 青天评标 / 满分门控内容被 evidence 化或评分依据化 | 停止 |
| 出现运行服务、endpoint、写回、导出线索 | 停止 |

## 20. KG-17 授权条件

KG-17 不得自动进入。若 ChatGPT 总控决定继续，建议 KG-17 只能在明确人工授权后执行，并优先限定为以下事项之一：

1. 对 KG-15 registry candidate JSON 执行人工静态校验报告；
2. 设计真实 validator 的伪代码，但不创建脚本；
3. 设计 registry candidate 变更审计规则；
4. 设计 registry candidate 与 manifest candidate 的路径一致性人工复核清单；
5. 设计 disabled flags 和 isolation rules 的人工复核清单；
6. 复核是否需要创建真实 validator 脚本，但不执行创建。

KG-17 如涉及以下动作，必须取得更高等级明确授权：

1. 修改 KG-08 manifest candidate JSON；
2. 修改 KG-15 registry candidate JSON；
3. 创建真实 validator 脚本；
4. 注册 manifest；
5. 创建真实 registry 文件；
6. 把 registry candidate 放入任何运行配置目录；
7. 接入 RAG / prompt registry / system instruction registry；
8. 启用任何知识包；
9. 运行 ZDoc、ZBid、Ollama、端口或 endpoint；
10. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
11. 生成 DOCX；
12. 写入 `output/job/export`；
13. 复制、移动、删除、重命名或改写 `AI知识图谱大全` 原文件。

## 21. KG-16 最终结论

KG-16 最终结论如下：

1. KG-15 registry candidate JSON 当前仍是 docs-only disabled candidate；
2. KG-16 已定义必填字段、禁止字段、path 指向、状态、注册状态、source mode、disabled flags、isolation rules 和 pre-registration rules 的静态校验规则；
3. KG-16 已定义 RAG / prompt registry / system instruction registry 隔离校验规则；
4. KG-16 已定义 system instruction 与青天评标 / 满分门控隔离校验规则；
5. KG-16 不创建真实 validator；
6. KG-16 不修改 KG-08 或 KG-15 JSON；
7. KG-16 不注册 manifest，不创建真实 registry 文件，不接入任何运行链路；
8. KG-17 需要 ChatGPT 总控再次人工授权，不得自动进入。
