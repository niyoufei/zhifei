# ZDoc KG-10 Controlled Pilot Manifest Candidate Manual Static Validation Report

## 1. KG-10 执行摘要

本文件是 KG-10 的 docs-only 人工静态校验报告，用于按 KG-09 静态校验规则复核 KG-08 disabled manifest candidate JSON。

KG-10 不创建真实 validator 脚本，不修改 KG-08 candidate JSON，不注册 manifest，不启用知识包，不接入 RAG / prompt registry / system instruction registry，不运行服务、Ollama、端口或 endpoint，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。

本报告只记录人工复核结论，完成后必须停止，等待 ChatGPT 总控审核，不得自动进入 KG-11。

## 2. 复核对象

本阶段只读复核以下文件：

- `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`
- `docs/zdoc-kg-controlled-pilot-manifest-candidate-static-validation-rules-kg09.md`
- `docs/zdoc-kg-controlled-pilot-disabled-manifest-candidate-kg08-review.md`

## 3. KG-08 Candidate JSON 基本信息

| 项目 | 结果 |
| --- | --- |
| 文件路径 | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` |
| 文件类型 | JSON candidate |
| 试点名称 | `ZDoc KG controlled pilot disabled manifest candidate` |
| 试点方向 | `全能索引 + 市政桥梁 KG01` |
| 备选方向 | `全能索引 + 医院装修改造 KG02` |
| `source_mode` | `path_and_summary_only` |
| `status` | `candidate_only` |
| `registration_status` | `not_registered` |
| `activation_requires` | `manual_authorization_after_KG08_review` |
| source 条目数 | 5 |
| JSON 语法校验 | 通过 `python3 -m json.tool` |

## 4. KG-09 静态校验规则引用摘要

KG-09 规定 candidate JSON 必须满足以下核心规则：

1. 必填字段必须存在。
2. 禁止字段不得出现。
3. disabled flags 必须全部为布尔值 `false`。
4. `source_mode` 必须为 `path_and_summary_only`。
5. `registration_status` 必须为 `not_registered`。
6. `status` 必须为 `candidate_only`。
7. `source_path` 只能引用 `/Users/youfeini/Desktop/AI知识图谱大全` 下的原始路径。
8. `source_summary` 只能为短摘要，不得搬运系统指令、prompt、青天评标或满分门控原文。
9. `risk_level` 必须使用 R0 到 R4。
10. `domain_tags` 必须使用经人工确认的静态标签。
11. `isolation_rules` 必须包含系统指令隔离、青天评标 / 满分门控隔离、非 evidence、非 scoring basis 和非运行链路规则。
12. KG-10 不得创建真实 validator，不得修改 candidate JSON，不得注册 manifest。

## 5. 必填字段校验结果

顶层必填字段人工校验结果：

| 字段 | 结果 |
| --- | --- |
| `pilot_name` | 通过 |
| `pilot_direction` | 通过 |
| `backup_direction` | 通过 |
| `source_mode` | 通过 |
| `status` | 通过 |
| `registration_status` | 通过 |
| `activation_requires` | 通过 |
| `disabled_flags` | 通过 |
| `domain_tags` | 通过 |
| `sources` | 通过 |
| `isolation_rules` | 通过 |
| `future_authorization_conditions` | 通过 |

`sources[]` 条目必填字段人工校验结果：

| 字段 | 结果 |
| --- | --- |
| `source_path` | 通过，5 个条目均存在 |
| `source_summary` | 通过，5 个条目均存在 |
| `risk_level` | 通过，5 个条目均为 `R2` |
| `domain_tags` | 通过，5 个条目均为非空数组 |
| `isolation_rules` | 通过，5 个条目均为非空数组 |

结论：必填字段校验通过。

## 6. 禁止字段校验结果

按 KG-09 禁止字段清单进行人工检查，candidate JSON 未发现以下字段：

| 禁止字段类别 | 结果 |
| --- | --- |
| `runtime_config` / `service_name` / `endpoint` | 未发现 |
| `rag_index` / `embedding_model` | 未发现 |
| `prompt_template` / `generation_prompt` | 未发现 |
| `system_instruction` 正文字段 | 未发现 |
| `evidence` 字段 | 未发现 |
| `scoring_basis` / `score_rules` | 未发现 |
| `writeback_target` / `export_target` | 未发现 |
| `active_registry` | 未发现 |

结论：禁止字段校验通过。

## 7. Disabled Flags 校验结果

`disabled_flags` 校验结果：

| 字段 | 期望值 | 实际结果 |
| --- | --- | --- |
| `enabled` | `false` | 通过 |
| `runtime_access` | `false` | 通过 |
| `rag_enabled` | `false` | 通过 |
| `evidence_enabled` | `false` | 通过 |
| `scoring_enabled` | `false` | 通过 |
| `prompt_registry_enabled` | `false` | 通过 |
| `system_instruction_registry_enabled` | `false` | 通过 |
| `writeback_enabled` | `false` | 通过 |
| `export_enabled` | `false` | 通过 |

结论：disabled flags 校验通过，未发现字符串 `"false"` 或 `true`。

## 8. Status 校验结果

| 字段 | 期望值 | 实际结果 |
| --- | --- | --- |
| `status` | `candidate_only` | 通过 |

未发现 `active`、`enabled`、`runtime`、`production`、`registered`、`approved_for_runtime` 等状态值。

结论：`status="candidate_only"` 校验通过。

## 9. Registration Status 校验结果

| 字段 | 期望值 | 实际结果 |
| --- | --- | --- |
| `registration_status` | `not_registered` | 通过 |

未发现 registry ID、runtime ID、endpoint ID，未发现 `registered`、`active`、`mounted`、`loaded`、`indexed` 等状态值。

结论：`registration_status="not_registered"` 校验通过。

## 10. Source Mode 校验结果

| 字段 | 期望值 | 实际结果 |
| --- | --- | --- |
| `source_mode` | `path_and_summary_only` | 通过 |

未发现 `source_text`、`source_content`、`full_text`、`raw_content` 等疑似正文承载字段。

结论：`source_mode="path_and_summary_only"` 校验通过。

## 11. Source Path 校验结果

人工复核的 5 个 `source_path` 均为 `/Users/youfeini/Desktop/AI知识图谱大全` 下的绝对路径：

| source_path 类型 | 结果 |
| --- | --- |
| 全能索引 | 通过 |
| 全能行业模块 | 通过 |
| 全能模板候选 | 通过 |
| 市政桥梁 KG01 | 通过 |
| 医院装修改造 KG02 备选 | 通过 |

未发现 source path 指向 ZDoc 仓库内部复制件，未发现指向 `output`、`job`、`export`、`backend`、`frontend`、`config` 或 `tests`。

结论：`source_path` 校验通过。

## 12. Source Summary 校验结果

人工复核的 5 个 `source_summary` 均为短摘要。

| 检查项 | 结果 |
| --- | --- |
| 是否搬运源文件长正文 | 未发现 |
| 是否搬运系统指令原文 | 未发现 |
| 是否搬运 prompt 原文 | 未发现 |
| 是否搬运青天评标 / 满分门控原文 | 未发现 |
| 是否含 endpoint、写回、导出、提交、覆盖、自动评分等动作指令 | 未发现 |
| 是否含疑似敏感原文 | 未发现 |

结论：`source_summary` 校验通过。

## 13. Risk Level 校验结果

candidate JSON 中 5 个 `sources[]` 条目的 `risk_level` 均为 `R2`。

| 检查项 | 结果 |
| --- | --- |
| 是否使用 R0 / R1 / R2 / R3 / R4 | 通过 |
| 是否出现未知风险等级 | 未发现 |
| 是否将 R2 解释为可运行 | 未发现 |
| 是否包含系统指令源文件并错误降级 | 未包含系统指令源文件 |
| 是否包含青天评标 / 满分门控源文件并错误降级 | 未包含青天评标 / 满分门控源文件 |

结论：`risk_level` 校验通过。R2 仅代表候选复核风险，不代表可运行。

## 14. Domain Tags 校验结果

candidate JSON 使用的 domain tags 为：

- `general_index`
- `municipal_bridge_kg01`
- `backup_hospital_renovation_kg02`

| 检查项 | 结果 |
| --- | --- |
| 是否为数组 | 通过 |
| 是否为空 | 否 |
| 是否包含 KG-09 允许标签 | 通过 |
| 是否出现未经人工确认标签 | 未发现 |
| 是否把 `general_index` 标为运行知识包 | 未发现 |

结论：`domain_tags` 校验通过。

## 15. Isolation Rules 校验结果

顶层 `isolation_rules` 包含以下关键隔离规则：

| 规则 | 结果 |
| --- | --- |
| `source_path_records_origin_path_only` | 通过 |
| `source_summary_records_summary_only` | 通过 |
| `source_text_not_copied` | 通过 |
| `system_instruction_sources_must_remain_quarantined` | 通过 |
| `qingtian_review_and_full_score_gate_sources_are_reference_candidates_only` | 通过 |
| `not_registered_in_zdoc_runtime` | 通过 |
| `not_loaded_by_generate_export_review_or_writeback` | 通过 |
| `not_evidence` | 通过 |
| `not_scoring_basis` | 通过 |

每个 `sources[]` 条目也包含非运行或人工复核类隔离规则。

结论：`isolation_rules` 校验通过。

## 16. System Instruction 隔离校验结果

系统指令隔离校验结果：

| 检查项 | 结果 |
| --- | --- |
| 是否包含 `system_instruction` 正文字段 | 未发现 |
| 是否包含系统指令原文 | 未发现 |
| `system_instruction_registry_enabled` 是否为 `false` | 通过 |
| 是否包含 `system_instruction_sources_must_remain_quarantined` | 通过 |
| `source_summary` 是否改写成隐性 system instruction | 未发现 |

结论：system instruction 隔离校验通过。

## 17. Evidence / Scoring 校验结果

| 检查项 | 结果 |
| --- | --- |
| `evidence_enabled=false` | 通过 |
| `scoring_enabled=false` | 通过 |
| 是否包含 `evidence` 字段 | 未发现 |
| 是否包含 `scoring_basis` 字段 | 未发现 |
| 是否包含青天评标 / 满分门控原文 | 未发现 |
| 是否包含自动评分、复评、满分优化、ZBid 写回规则 | 未发现 |
| 是否包含 `not_evidence` | 通过 |
| 是否包含 `not_scoring_basis` | 通过 |

结论：evidence / scoring 校验通过。

## 18. 问题清单

本次人工静态校验未发现阻塞问题。

| 问题级别 | 问题 | 处置 |
| --- | --- | --- |
| 阻塞 | 无 | 无需处理 |
| 非阻塞 | 当前仅为人工静态校验报告，尚无自动 validator | 符合 KG-10 边界，不创建脚本 |
| 后续关注 | 若 KG-11 继续推进，应保持 docs-only 或另行授权 validator 脚本 | 等待 ChatGPT 总控授权 |

## 19. 是否允许进入 KG-11 的建议

建议：可以考虑进入 KG-11，但必须再次人工授权，且 KG-11 不得自动进入。

KG-11 的建议边界：

1. 优先限定为 docs-only 校验清单复核或 validator 伪代码设计。
2. 不得默认创建真实 validator 脚本。
3. 不得修改 KG-08 candidate JSON。
4. 不得注册 manifest。
5. 不得启用知识包。
6. 不得接入 RAG / prompt registry / system instruction registry。
7. 不得运行服务、Ollama、端口或 endpoint。
8. 不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
9. 不得生成 DOCX。
10. 不得写 output/job/export。

KG-11 若要创建真实 validator，必须由 ChatGPT 总控明确授权，并单独指定目标文件、允许范围和禁止范围。

## 20. KG-10 结论

KG-10 结论如下：

1. KG-08 candidate JSON 语法有效。
2. 必填字段校验通过。
3. 禁止字段校验通过。
4. disabled flags 校验通过。
5. `status="candidate_only"` 校验通过。
6. `registration_status="not_registered"` 校验通过。
7. `source_mode="path_and_summary_only"` 校验通过。
8. `source_path` / `source_summary` 校验通过。
9. `risk_level` / `domain_tags` / `isolation_rules` 校验通过。
10. system instruction 隔离校验通过。
11. `evidence_enabled=false`、`scoring_enabled=false` 校验通过。
12. 未发现阻塞问题。
13. KG-11 仍需人工授权，不得自动进入。
