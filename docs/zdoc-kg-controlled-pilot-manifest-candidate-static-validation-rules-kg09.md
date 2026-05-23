# ZDoc KG-09 Controlled Pilot Manifest Candidate Static Validation Rules Design

## 1. KG-09 执行摘要

本文件是 KG-09 的 docs-only 静态校验规则设计归档，用于定义 KG-08 disabled manifest candidate JSON 在未来被进一步处理前必须满足的静态校验规则。

KG-09 不创建真实 validator 脚本，不修改 KG-08 candidate JSON，不注册 manifest，不启用知识包，不接入 RAG / prompt registry / system instruction registry，不进入运行链路。

KG-09 只做规则设计，完成后必须停止，等待 ChatGPT 总控审核，不得自动进入 KG-10。

## 2. 复核对象

本阶段只读复核以下文件：

- `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`
- `docs/zdoc-kg-controlled-pilot-disabled-manifest-candidate-kg08-review.md`
- `docs/zdoc-kg-controlled-pilot-inert-manifest-entity-scaffold-kg07.md`
- `docs/zdoc-kg-controlled-pilot-pre-entity-review-and-authorization-gate-kg06.md`

复核用途仅限静态规则设计，不代表运行注册或系统接入。

## 3. KG-08 Candidate JSON 静态复核摘要

KG-08 candidate JSON 当前符合以下非运行态特征：

| 字段 | 当前要求 | KG-09 复核结论 |
| --- | --- | --- |
| `source_mode` | `path_and_summary_only` | 只能记录路径与摘要 |
| `status` | `candidate_only` | 只能作为候选 |
| `registration_status` | `not_registered` | 不得被视为已注册 |
| `activation_requires` | `manual_authorization_after_KG08_review` | 后续激活需人工授权 |
| `enabled` | `false` | 不启用 |
| `runtime_access` | `false` | 运行链路不可访问 |
| `rag_enabled` | `false` | 不进入 RAG |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 不进入 system instruction registry |
| `writeback_enabled` | `false` | 不触发写回 |
| `export_enabled` | `false` | 不触发导出 |

KG-09 的目标是把上述特征固化为未来静态校验规则，而不是执行校验器实现。

## 4. 必填字段校验规则

未来静态校验应要求 candidate JSON 至少包含以下顶层字段：

| 字段 | 校验规则 |
| --- | --- |
| `pilot_name` | 必须存在，且为非空字符串 |
| `pilot_direction` | 必须存在，且包含 `全能索引 + 市政桥梁 KG01` |
| `backup_direction` | 必须存在，且包含 `全能索引 + 医院装修改造 KG02` |
| `source_mode` | 必须存在，且等于 `path_and_summary_only` |
| `status` | 必须存在，且等于 `candidate_only` |
| `registration_status` | 必须存在，且等于 `not_registered` |
| `activation_requires` | 必须存在，且等于 `manual_authorization_after_KG08_review` |
| `disabled_flags` | 必须存在，且为对象 |
| `domain_tags` | 必须存在，且为数组 |
| `sources` | 必须存在，且为非空数组 |
| `isolation_rules` | 必须存在，且为数组 |
| `future_authorization_conditions` | 必须存在，且为数组 |

每个 `sources[]` 条目至少应包含：

| 字段 | 校验规则 |
| --- | --- |
| `source_path` | 必须存在，且为 `/Users/youfeini/Desktop/AI知识图谱大全` 下的绝对路径 |
| `source_summary` | 必须存在，且为短摘要 |
| `risk_level` | 必须存在，且为 R0 / R1 / R2 / R3 / R4 之一 |
| `domain_tags` | 必须存在，且为非空数组 |
| `isolation_rules` | 必须存在，且为非空数组 |

## 5. 禁止字段校验规则

candidate JSON 不得包含会被误解为运行、注册、检索、生成、评分或写回的字段。

禁止字段包括：

| 禁止字段 | 禁止原因 |
| --- | --- |
| `runtime_config` | 容易被误认为运行配置 |
| `rag_index` | 容易被误认为 RAG 索引 |
| `embedding_model` | 暗示进入向量化或检索链路 |
| `prompt_template` | 暗示进入 prompt registry |
| `system_instruction` | 暗示进入 system instruction registry |
| `generation_prompt` | 暗示参与生成 |
| `evidence` | 暗示作为证据 |
| `scoring_basis` | 暗示作为评分依据 |
| `score_rules` | 暗示自动评分规则 |
| `writeback_target` | 暗示写回目标 |
| `export_target` | 暗示导出目标 |
| `endpoint` | 暗示 endpoint 访问 |
| `service_name` | 暗示服务接入 |
| `active_registry` | 暗示已注册 |

如果未来 candidate JSON 出现上述字段，应判定静态校验失败。

## 6. Disabled Flags 校验规则

`disabled_flags` 必须包含以下字段，且全部为布尔值 `false`：

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

校验失败条件：

1. 任一字段缺失。
2. 任一字段不是布尔值。
3. 任一字段为 `true`。
4. 任一字段使用字符串 `"false"` 代替布尔值 `false`。

## 7. Source Mode 校验规则

`source_mode` 必须等于：

```text
path_and_summary_only
```

该字段用于保证 candidate JSON 只记录源路径和摘要。

静态校验失败条件：

1. `source_mode` 缺失。
2. `source_mode` 不等于 `path_and_summary_only`。
3. 存在 `source_text`、`source_content`、`full_text`、`raw_content` 等疑似正文承载字段。
4. `source_summary` 出现大段原文搬运迹象。

## 8. Registration Status 校验规则

`registration_status` 必须等于：

```text
not_registered
```

静态校验失败条件：

1. `registration_status` 缺失。
2. `registration_status` 不等于 `not_registered`。
3. 出现 `registered`、`active`、`mounted`、`loaded`、`indexed` 等状态值。
4. 出现任何 registry ID、runtime ID 或 endpoint ID。

## 9. Status 校验规则

`status` 必须等于：

```text
candidate_only
```

静态校验失败条件：

1. `status` 缺失。
2. `status` 不等于 `candidate_only`。
3. 出现 `active`、`enabled`、`runtime`、`production`、`registered`、`approved_for_runtime` 等状态值。
4. 出现绕过候选态的同义字段。

## 10. Source Path 校验规则

`source_path` 只允许路径引用，不允许复制原文。

规则：

1. 每个 `source_path` 必须是绝对路径。
2. 每个 `source_path` 必须位于 `/Users/youfeini/Desktop/AI知识图谱大全` 下。
3. 每个 `source_path` 不得指向 ZDoc 仓库内部复制件。
4. 每个 `source_path` 不得指向 `output`、`job`、`export`、`backend`、`frontend`、`config` 或 `tests`。
5. `source_path` 只表示人工溯源路径，不表示运行时读取授权。

静态校验失败条件：

1. `source_path` 为空。
2. `source_path` 不是绝对路径。
3. `source_path` 不在允许 source root 下。
4. `source_path` 指向 ZDoc 仓库内文件。
5. candidate JSON 中出现源文件正文承载字段。

## 11. Source Summary 校验规则

`source_summary` 只允许摘要，不允许搬运系统指令原文、prompt 原文、青天评标原文或满分门控原文。

规则：

1. `source_summary` 必须是短摘要。
2. `source_summary` 不得包含系统指令原文。
3. `source_summary` 不得包含 prompt 原文。
4. `source_summary` 不得包含青天评标 / 满分门控规则原文。
5. `source_summary` 不得写成可执行指令。
6. `source_summary` 不得包含 endpoint、写回、导出、提交、覆盖、自动评分等动作指令。

静态校验失败条件：

1. `source_summary` 缺失或为空。
2. `source_summary` 明显为长正文搬运。
3. `source_summary` 含有“你必须”“立即执行”“写回”“导出”“提交”“覆盖”“自动评分”“满分门控”等动作性指令。
4. `source_summary` 含有疑似敏感原文。

## 12. Risk Level 校验要求

`risk_level` 必须为：

- `R0`
- `R1`
- `R2`
- `R3`
- `R4`

静态校验规则：

1. 普通知识锚点候选可为 R2，但不得因此启用。
2. 系统指令类内容默认不低于 R3。
3. 青天评标 / 满分门控 / 自动评分 / 写回 / 导出 / 提交 / 覆盖类内容默认不低于 R3。
4. 非知识内容、`.git`、`.DS_Store`、`.sample`、`.gitignore` 应为 R4。
5. candidate JSON 中的 R2 不得被解释为可运行。

## 13. Domain Tags 校验要求

`domain_tags` 必须是数组，且只允许使用经人工确认的静态标签。

当前 KG-09 允许的标签：

| 标签 | 含义 |
| --- | --- |
| `general_index` | 全能索引 |
| `municipal_bridge_kg01` | 市政桥梁 KG01 首个试点 |
| `backup_hospital_renovation_kg02` | 医院装修改造 KG02 备选试点 |

静态校验失败条件：

1. `domain_tags` 缺失。
2. `domain_tags` 不是数组。
3. `domain_tags` 为空。
4. 出现未经人工确认的专业域标签。
5. 把 `general_index` 误标为单一专业运行知识包。

## 14. Isolation Rules 校验要求

`isolation_rules` 必须包含能证明候选文件仍处于隔离状态的规则。

顶层 `isolation_rules` 建议至少包含：

| 规则 | 含义 |
| --- | --- |
| `source_path_records_origin_path_only` | 只记录原始路径 |
| `source_summary_records_summary_only` | 只记录摘要 |
| `source_text_not_copied` | 不复制正文 |
| `system_instruction_sources_must_remain_quarantined` | 系统指令源必须隔离 |
| `qingtian_review_and_full_score_gate_sources_are_reference_candidates_only` | 青天评标 / 满分门控仅参考候选 |
| `not_registered_in_zdoc_runtime` | 未注册到运行链路 |
| `not_loaded_by_generate_export_review_or_writeback` | 不被生成、导出、审核、写回读取 |
| `not_evidence` | 不作为 evidence |
| `not_scoring_basis` | 不作为评分依据 |

静态校验失败条件：

1. `isolation_rules` 缺失。
2. `isolation_rules` 为空。
3. 缺少 `not_evidence`。
4. 缺少 `not_scoring_basis`。
5. 缺少系统指令隔离规则。
6. 缺少运行链路隔离规则。

## 15. System Instruction 隔离校验

system instruction 类内容必须继续隔离。

静态校验规则：

1. candidate JSON 不得包含 `system_instruction` 正文字段。
2. candidate JSON 不得包含系统指令原文。
3. `disabled_flags.system_instruction_registry_enabled` 必须为 `false`。
4. 顶层 `isolation_rules` 必须包含 `system_instruction_sources_must_remain_quarantined`。
5. `source_summary` 不得改写成隐性 system instruction。

静态校验失败条件：

1. 出现 `system_instruction` 字段。
2. 出现系统指令原文或可执行系统约束。
3. `system_instruction_registry_enabled` 缺失或不是 `false`。
4. 缺少系统指令隔离规则。

## 16. 青天评标 / 满分门控校验

青天评标 / 满分门控类内容不得作为 evidence 或 scoring basis。

静态校验规则：

1. candidate JSON 不得包含青天评标 / 满分门控原文。
2. candidate JSON 不得包含 `scoring_basis` 字段。
3. candidate JSON 不得包含 `evidence` 字段。
4. `disabled_flags.evidence_enabled` 必须为 `false`。
5. `disabled_flags.scoring_enabled` 必须为 `false`。
6. 顶层 `isolation_rules` 必须包含 `qingtian_review_and_full_score_gate_sources_are_reference_candidates_only`。
7. 顶层 `isolation_rules` 必须包含 `not_evidence`。
8. 顶层 `isolation_rules` 必须包含 `not_scoring_basis`。

静态校验失败条件：

1. 出现 evidence 化字段。
2. 出现 scoring basis 字段。
3. `evidence_enabled` 或 `scoring_enabled` 不为 `false`。
4. 出现自动评分、复评、满分优化、ZBid 写回等动作性规则。

## 17. 静态校验失败条件总表

未来静态校验如发现以下任一情况，应判定失败：

| 失败条件 | 处置 |
| --- | --- |
| candidate JSON 语法无效 | 停止 |
| 必填字段缺失 | 停止 |
| 出现禁止字段 | 停止 |
| 任一 disabled flag 不为 `false` | 停止 |
| `source_mode` 不为 `path_and_summary_only` | 停止 |
| `status` 不为 `candidate_only` | 停止 |
| `registration_status` 不为 `not_registered` | 停止 |
| `activation_requires` 不为 `manual_authorization_after_KG08_review` | 停止 |
| `source_path` 不在允许 source root 下 | 停止 |
| `source_summary` 搬运原文或含动作性指令 | 停止 |
| 系统指令内容未隔离 | 停止 |
| 青天评标 / 满分门控内容被 evidence 化或评分依据化 | 停止 |
| 出现 RAG、prompt registry、system instruction registry 注册线索 | 停止 |
| 出现运行服务、endpoint、写回、导出线索 | 停止 |

## 18. KG-10 授权条件

KG-10 不得自动进入。

如 ChatGPT 总控决定继续，KG-10 只能在明确人工授权后进入，并且应优先限定为：

1. docs-only 静态校验规则审阅或伪代码设计。
2. 不创建真实 validator 脚本，除非总控明确授权。
3. 不修改 KG-08 candidate JSON。
4. 不注册 manifest。
5. 不启用知识包。
6. 不接入 RAG / prompt registry / system instruction registry。
7. 不运行服务、Ollama、端口或 endpoint。
8. 不触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
9. 不写 output/job/export。
10. 不进入真实使用阶段。

KG-10 授权请求建议写法：

> 请求授权执行 KG-10：ZDoc KG manifest candidate static validation pseudo-code review only。
>
> KG-10 仅允许在 docs 中设计候选 manifest 静态校验伪代码或审核清单，不得创建真实 validator 脚本，不得修改 candidate JSON，不得注册 manifest，不得接入 RAG / prompt registry / system instruction registry，不得启用任何知识包，不得进入运行链路。

## 19. KG-09 结论

KG-09 结论如下：

1. KG-08 candidate JSON 当前仍是非运行态候选。
2. KG-09 已定义必填字段、禁止字段、disabled flags、source_mode、status、registration_status 等静态校验规则。
3. KG-09 已定义 source_path、source_summary、risk_level、domain_tags、isolation_rules 的静态校验要求。
4. KG-09 已定义系统指令、青天评标 / 满分门控的隔离校验。
5. KG-09 不创建真实 validator。
6. KG-09 不修改 candidate JSON。
7. KG-09 不注册 manifest，不启用知识包，不接入任何运行链路。
8. KG-10 不得自动进入。
