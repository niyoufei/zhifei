# ZDoc KG-17 Disabled Registry Candidate Manual Static Validation Report

## 1. KG-17 执行摘要

KG-17 是对 KG-15 disabled registry candidate JSON 的 docs-only 人工静态校验报告。本步骤依据 KG-16 静态校验规则进行人工复核，只记录校验结果，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON，不创建真实 validator 脚本，不注册 manifest，不创建真实 registry 文件，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包。

KG-17 结论：KG-15 registry candidate JSON 通过人工静态校验。未发现 blocker、major 或 minor 问题。建议可考虑进入 KG-18，但 KG-18 必须由 ChatGPT 总控再次人工授权，不得自动进入。

## 2. 复核对象

| 对象 | 路径 | KG-17 用途 |
| --- | --- | --- |
| KG-16 静态校验规则 | `docs/zdoc-kg-disabled-registry-candidate-static-validation-rules-kg16.md` | 本次人工校验依据 |
| KG-15 registry candidate JSON | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | 本次人工校验对象 |
| KG-15 review | `docs/zdoc-kg-disabled-registry-candidate-entity-creation-kg15-review.md` | 承接 docs-only、非正式 registry、不可自动读取结论 |
| KG-08 manifest candidate JSON | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 校验 linked path / manifest path 指向 |

## 3. KG-15 Registry Candidate JSON 基本信息

| 项目 | 结果 |
| --- | --- |
| 文件路径 | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` |
| 文件类型 | docs-only registry candidate JSON |
| `registry_candidate_id` | `zdoc-kg-pilot-qn-index-municipal-bridge-kg01-disabled-registry-candidate` |
| `manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` |
| `linked_manifest_candidate_path` | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` |
| 试点方向 | `全能索引 + 市政桥梁 KG01` |
| 备选方向 | `全能索引 + 医院装修改造 KG02` |
| `source_mode` | `path_and_summary_only` |
| `status` | `registry_candidate_only` |
| `registration_status` | `not_registered` |
| `activation_requires` | `manual_authorization_after_KG15_review` |
| `manual_authorization_required` | `true` |
| `risk_level` | `R2` |
| JSON 语法校验 | 通过 `python3 -m json.tool` |

## 4. KG-16 静态校验规则引用摘要

KG-16 规定 registry candidate JSON 必须满足以下核心规则：

1. 必填字段必须存在。
2. 禁止字段不得出现。
3. `manifest_candidate_path` 与 `linked_manifest_candidate_path` 必须指向 docs 下 KG-08 frozen manifest candidate。
4. `status` 必须为 `registry_candidate_only`。
5. `registration_status` 必须为 `not_registered`。
6. `source_mode` 必须为 `path_and_summary_only`。
7. 所有 disabled flags 必须为 boolean `false`。
8. `isolation_rules` 必须包含非运行、非 registry、非 evidence、非 scoring、三类 registry 隔离和 system instruction 隔离规则。
9. `pre_registration_rules` 必须保持 draft-only、not approved、registry forbidden、evidence forbidden、scoring forbidden、writeback forbidden 和 export forbidden。
10. `manual_authorization_required` 必须为 boolean `true`。
11. RAG registry、prompt registry、system instruction registry 必须保持隔离。
12. system instruction 类内容不得转为 system instruction。
13. 青天评标 / 满分门控类内容不得作为 evidence 或 scoring basis。

## 5. 必填字段校验结果

顶层必填字段人工校验结果：

| 字段 | 结果 |
| --- | --- |
| `registry_candidate_id` | 通过 |
| `manifest_candidate_path` | 通过 |
| `linked_manifest_candidate_path` | 通过 |
| `pilot_direction` | 通过 |
| `backup_direction` | 通过 |
| `source_mode` | 通过 |
| `status` | 通过 |
| `registration_status` | 通过 |
| `activation_requires` | 通过 |
| `disabled_flags` | 通过 |
| `isolation_rules` | 通过 |
| `pre_registration_rules` | 通过 |
| `manual_authorization_required` | 通过 |
| `risk_level` | 通过 |
| `domain_tags` | 通过 |
| `future_authorization_conditions` | 通过 |

结论：必填字段校验通过。

## 6. 禁止字段校验结果

按 KG-16 禁止字段清单进行人工检查，KG-15 registry candidate JSON 未发现以下字段：

| 禁止字段类别 | 结果 |
| --- | --- |
| `runtime_config` / `service_name` / `endpoint` | 未发现 |
| `registry_id` / `manifest_registry_id` / `active_registry` | 未发现 |
| `rag_index` / `embedding_model` / `corpus_path` | 未发现 |
| `prompt_template` / `generation_prompt` | 未发现 |
| `system_instruction` 正文字段 | 未发现 |
| `evidence` 字段 | 未发现 |
| `scoring_basis` / `score_rules` | 未发现 |
| `writeback_target` / `export_target` | 未发现 |

结论：禁止字段校验通过。

## 7. Path 指向校验结果

| 校验项 | 结果 |
| --- | --- |
| `manifest_candidate_path` 是否存在 | 通过 |
| `linked_manifest_candidate_path` 是否存在 | 通过 |
| 两个 path 是否一致 | 通过 |
| 是否指向 docs 下 frozen manifest candidate | 通过 |
| 是否指向 KG-08 manifest candidate JSON | 通过 |
| 是否指向 `AI知识图谱大全` 原文件 | 未发现 |
| 是否指向 backend / frontend / config / tests / output / job / export | 未发现 |
| 是否包含运行时读取授权 | 未发现 |
| 是否作为 RAG corpus path | 未发现 |
| 是否作为 prompt 或 system instruction source | 未发现 |

结论：`manifest_candidate_path` / `linked_manifest_candidate_path` 指向校验通过。

## 8. Status 校验结果

| 字段 | 期望值 | 实际结果 |
| --- | --- | --- |
| `status` | `registry_candidate_only` | 通过 |

未发现 `active`、`enabled`、`runtime`、`production`、`registered`、`approved_for_runtime` 等状态值。

结论：`status="registry_candidate_only"` 校验通过。

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

未发现 `source_text`、`source_content`、`full_text`、`raw_content` 等正文承载字段。未发现源文件原文、系统指令原文、prompt 原文、青天评标原文或满分门控原文。

结论：`source_mode="path_and_summary_only"` 校验通过。

## 11. Disabled Flags 校验结果

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

## 12. Isolation Rules 校验结果

顶层 `isolation_rules` 包含以下关键隔离规则：

| 规则 | 结果 |
| --- | --- |
| `docs_only_registry_candidate` | 通过 |
| `not_real_registry_file` | 通过 |
| `not_registered_manifest` | 通过 |
| `not_runtime_readable` | 通过 |
| `manifest_candidate_path_points_to_docs_frozen_candidate_only` | 通过 |
| `source_mode_path_and_summary_only` | 通过 |
| `rag_registry_disabled` | 通过 |
| `prompt_registry_disabled` | 通过 |
| `system_instruction_registry_disabled` | 通过 |
| `system_instruction_sources_must_remain_quarantined` | 通过 |
| `qingtian_review_and_full_score_gate_sources_are_reference_candidates_only` | 通过 |
| `not_evidence` | 通过 |
| `not_scoring_basis` | 通过 |
| `not_loaded_by_generate_export_review_or_writeback` | 通过 |

结论：`isolation_rules` 校验通过。

## 13. Pre-Registration Rules 校验结果

`pre_registration_rules` 校验结果：

| 字段 | 期望值 | 实际结果 |
| --- | --- | --- |
| `pre_registration_status` | `draft_only` | 通过 |
| `manual_review_required` | `true` | 通过 |
| `review_status` | `pending` | 通过 |
| `approval_status` | `not_approved` | 通过 |
| `registration_must_remain_not_registered` | `true` | 通过 |
| `runtime_registry_forbidden` | `true` | 通过 |
| `rag_registry_forbidden` | `true` | 通过 |
| `prompt_registry_forbidden` | `true` | 通过 |
| `system_instruction_registry_forbidden` | `true` | 通过 |
| `evidence_forbidden` | `true` | 通过 |
| `scoring_basis_forbidden` | `true` | 通过 |
| `writeback_forbidden` | `true` | 通过 |
| `export_forbidden` | `true` | 通过 |

结论：`pre_registration_rules` 校验通过。

## 14. Manual Authorization 校验结果

| 校验项 | 结果 |
| --- | --- |
| `manual_authorization_required` 是否为 boolean `true` | 通过 |
| `future_authorization_conditions` 是否存在 | 通过 |
| 是否要求 KG-16 单独授权 | 通过 |
| 是否要求不修改 KG-08 manifest candidate | 通过 |
| 是否要求不注册 manifest | 通过 |
| 是否要求不创建真实 registry 文件 | 通过 |
| 是否要求不启用 runtime access | 通过 |
| 是否要求不启用 RAG / prompt / system instruction registry | 通过 |
| 是否要求不启用 evidence / scoring / writeback / export | 通过 |
| 是否要求不运行服务、Ollama、端口或 endpoint | 通过 |

结论：manual authorization 校验通过。

## 15. RAG Registry 隔离校验结果

| 检查项 | 结果 |
| --- | --- |
| `rag_enabled=false` | 通过 |
| `rag_registry_forbidden=true` | 通过 |
| `rag_registry_disabled` | 通过 |
| 是否存在 `rag_index` | 未发现 |
| 是否存在 `embedding_model` | 未发现 |
| 是否存在 `corpus_path` | 未发现 |
| `manifest_candidate_path` 是否作为 RAG corpus path | 未发现 |
| 是否生成或引用向量索引 | 未发现 |

结论：RAG registry 隔离校验通过。

## 16. Prompt Registry 隔离校验结果

| 检查项 | 结果 |
| --- | --- |
| `prompt_registry_enabled=false` | 通过 |
| `prompt_registry_forbidden=true` | 通过 |
| `prompt_registry_disabled` | 通过 |
| 是否存在 `prompt_template` | 未发现 |
| 是否存在 `generation_prompt` | 未发现 |
| 是否把 path 或 summary 改写成 prompt | 未发现 |
| 是否通过 prompt registry 绕过 system instruction 隔离 | 未发现 |

结论：prompt registry 隔离校验通过。

## 17. System Instruction Registry 隔离校验结果

| 检查项 | 结果 |
| --- | --- |
| `system_instruction_registry_enabled=false` | 通过 |
| `system_instruction_registry_forbidden=true` | 通过 |
| `system_instruction_registry_disabled` | 通过 |
| `system_instruction_sources_must_remain_quarantined` | 通过 |
| 是否存在 `system_instruction` 正文字段 | 未发现 |
| 是否存在系统指令原文 | 未发现 |
| 是否把 source summary 改写成隐性 system instruction | 未发现 |
| 是否通过 prompt registry 绕过隔离 | 未发现 |

结论：system instruction registry 隔离校验通过。

## 18. System Instruction 类内容校验结论

系统指令类内容不得转为 ZDoc system instruction。本次人工静态校验确认：

1. KG-15 registry candidate 未包含系统指令原文；
2. 未包含可执行系统约束；
3. 未包含写回、导出、提交、覆盖或自动评分命令；
4. `system_instruction_registry_enabled=false`；
5. `system_instruction_registry_forbidden=true`；
6. system instruction 隔离规则存在。

结论：system instruction 类内容隔离校验通过，不得转为 system instruction 的边界继续有效。

## 19. 青天评标 / 满分门控校验结论

青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。本次人工静态校验确认：

1. `evidence_enabled=false`；
2. `scoring_enabled=false`；
3. `evidence_forbidden=true`；
4. `scoring_basis_forbidden=true`；
5. `not_evidence` 存在；
6. `not_scoring_basis` 存在；
7. 未发现 `evidence` 字段；
8. 未发现 `scoring_basis` 字段；
9. 未发现 `score_rules` 字段；
10. 未发现青天评标 / 满分门控原文；
11. 未发现自动评分、复评、满分优化或 ZBid 写回规则。

结论：青天评标 / 满分门控隔离校验通过，不得作为 evidence 或 scoring basis 的边界继续有效。

## 20. 问题清单

| 问题级别 | 问题 | 处置建议 |
| --- | --- | --- |
| Blocker | 无 | 无需处置 |
| Major | 无 | 无需处置 |
| Minor | 无 | 无需处置 |
| Note | 当前仅为人工静态校验报告，尚无真实 validator | 符合 KG-17 边界，不创建脚本 |

KG-17 不修改 KG-15 registry candidate JSON。若未来要调整 registry candidate 字段，应单独授权并重新执行静态校验。

## 21. 是否允许进入 KG-18 的建议

建议：可以考虑进入 KG-18，但必须再次人工授权，且 KG-18 不得自动进入。

KG-18 建议优先限定为 docs-only 处置结论或 freeze gate 复核，例如：

1. registry candidate validation disposition；
2. registry candidate freeze gate；
3. registry candidate 问题处置建议，但不得修改 JSON；
4. 是否允许进入下一阶段的人工授权请求草案。

KG-18 仍不得：

1. 修改 KG-08 manifest candidate JSON；
2. 修改 KG-15 registry candidate JSON；
3. 创建真实 validator 脚本；
4. 注册 manifest；
5. 创建真实 registry 文件；
6. 把 registry candidate 放入任何运行配置目录；
7. 接入 RAG / prompt registry / system instruction registry；
8. 启用任何知识包；
9. 运行服务、Ollama、端口或 endpoint；
10. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
11. 生成 DOCX；
12. 写入 `output/job/export`；
13. 复制、移动、删除、重命名或改写 `AI知识图谱大全` 原文件。

## 22. KG-17 最终结论

KG-17 最终结论如下：

1. KG-15 registry candidate JSON 语法有效；
2. 必填字段校验通过；
3. 禁止字段校验通过；
4. linked / manifest path 指向校验通过；
5. `status="registry_candidate_only"` 校验通过；
6. `registration_status="not_registered"` 校验通过；
7. `source_mode="path_and_summary_only"` 校验通过；
8. disabled flags 校验通过；
9. isolation rules 校验通过；
10. pre-registration rules 校验通过；
11. manual authorization 校验通过；
12. RAG / prompt registry / system instruction registry 隔离校验通过；
13. system instruction 类内容不得转为 system instruction 的边界继续有效；
14. 青天评标 / 满分门控类内容不得作为 evidence 或 scoring basis 的边界继续有效；
15. 未发现 blocker、major 或 minor 问题；
16. KG-18 仍需 ChatGPT 总控人工授权，不得自动进入。
