# ZDoc KG-08 Controlled Pilot Disabled Manifest Candidate Review

## 1. KG-08 执行摘要

本文件复核 KG-08 新增的 disabled manifest candidate JSON，并说明它为什么仍属于非运行态候选实体。

KG-08 新增的 candidate JSON 位于：

- `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`

该文件只登记试点方向、来源路径、短摘要、风险等级、专业标签、隔离规则、禁用标志和后续授权条件。它不复制 `AI知识图谱大全` 原文件正文，不生成知识包实体，不接入 RAG、prompt registry 或 system instruction registry，不启用任何知识包。

## 2. 前置复核承接

KG-08 继承以下结论：

| 来源阶段 | 承接结论 |
| --- | --- |
| KG-04 | 首个试点为 `全能索引 + 市政桥梁 KG01`，备选为 `全能索引 + 医院装修改造 KG02` |
| KG-05 | disabled entity 必须保持 `enabled=false`、`runtime_access=false`、`rag_enabled=false`、`evidence_enabled=false`、`scoring_enabled=false` |
| KG-06 | source path / source summary / risk level / domain tag / enabled=false 等字段必须静态校验 |
| KG-07 | inert manifest entity 应优先放在 docs-only 草案层，KG-08 创建真实 disabled candidate 仍不得进入运行链路 |

## 3. 为什么仍是非运行态候选实体

该 candidate JSON 仍属于非运行态候选实体，原因如下：

1. 文件位于 `docs/kg-manifest-candidates/`，不是 backend、frontend、config、tests 或知识包运行目录。
2. 顶层 `status` 为 `candidate_only`。
3. 顶层 `registration_status` 为 `not_registered`。
4. 顶层 `source_mode` 为 `path_and_summary_only`。
5. 顶层 `activation_requires` 为 `manual_authorization_after_KG08_review`。
6. `enabled=false`。
7. `runtime_access=false`。
8. `rag_enabled=false`。
9. `evidence_enabled=false`。
10. `scoring_enabled=false`。
11. `prompt_registry_enabled=false`。
12. `system_instruction_registry_enabled=false`。
13. `writeback_enabled=false`。
14. `export_enabled=false`。

这些字段共同限定该文件只能作为人工审核候选，不具备运行、检索、生成、评分、证据、写回或导出权限。

## 4. 为什么不能被 ZDoc 自动读取

该 candidate JSON 不能被 ZDoc 自动读取，原因如下：

1. 它没有放入任何运行配置目录。
2. 它没有注册到 ZDoc manifest registry。
3. 它没有注册到 RAG corpus。
4. 它没有注册到 prompt registry。
5. 它没有注册到 system instruction registry。
6. 它没有任何运行入口引用。
7. 它不属于 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回链路的输入。
8. `runtime_access=false` 是最高层禁用标志。
9. `registration_status=not_registered` 明确表示尚未登记到系统。
10. `activation_requires=manual_authorization_after_KG08_review` 明确要求 KG-08 后人工授权。

因此，该文件即使是 JSON 格式，也只能视为 docs 下的候选清单，不得被任何 ZDoc 运行逻辑自动加载。

## 5. Candidate JSON 内容边界

candidate JSON 仅允许写入：

1. 试点名称。
2. 试点方向：`全能索引 + 市政桥梁 KG01`。
3. 备选方向：`全能索引 + 医院装修改造 KG02`。
4. `source_path`。
5. `source_summary`。
6. `risk_level`。
7. `domain_tags`。
8. `isolation_rules`。
9. disabled flags。
10. 后续授权条件。

candidate JSON 不允许写入：

1. 原始知识图谱正文。
2. 系统指令原文。
3. prompt 原文。
4. 青天评标 / 满分门控规则原文。
5. 可执行配置。
6. 运行入口。
7. RAG 索引内容。
8. 评分规则。
9. evidence。

## 6. System Instruction 隔离继续有效

系统指令类内容必须继续隔离，不得进入 system instruction registry。

KG-08 candidate JSON 只允许记录以下规则：

1. `system_instruction_sources_must_remain_quarantined`。
2. `system_instruction_registry_enabled=false`。
3. 不得将系统指令源文件原文写入 candidate JSON。
4. 不得将摘要改写为隐性 system instruction。
5. 不得进入首个试点启用项。

## 7. 青天评标 / 满分门控参考边界继续有效

青天评标 / 满分门控类内容只能作为参考候选，不得作为评分依据。

KG-08 candidate JSON 只允许记录以下规则：

1. `qingtian_review_and_full_score_gate_sources_are_reference_candidates_only`。
2. `evidence_enabled=false`。
3. `scoring_enabled=false`。
4. 不得写入青天评标 / 满分门控原文。
5. 不得注册为 scoring basis。
6. 不得触发 `/review/apply` 或 ZBid 写回。

## 8. KG-09 建议方向

KG-09 若继续推进，应先做候选 manifest 的静态校验规则设计，而不是接入运行链路。

KG-09 建议只允许设计：

1. candidate JSON schema 静态校验规则。
2. 禁用字段必须为 false 的校验规则。
3. `source_mode=path_and_summary_only` 的校验规则。
4. `status=candidate_only` 的校验规则。
5. `registration_status=not_registered` 的校验规则。
6. `activation_requires=manual_authorization_after_KG08_review` 的校验规则。
7. source path 必须位于 `/Users/youfeini/Desktop/AI知识图谱大全` 的校验规则。
8. source summary 不得包含原文大段摘录的人工检查规则。

KG-09 仍不得：

1. 接入 RAG。
2. 接入 prompt registry。
3. 接入 system instruction registry。
4. 启用任何知识包。
5. 运行服务、Ollama、端口或 endpoint。
6. 触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
7. 写 output/job/export。
8. 进入真实使用阶段。

## 9. KG-09 授权门槛

KG-09 不得自动进入。进入 KG-09 前必须由 ChatGPT 总控再次人工授权，并明确：

1. 唯一输出文件。
2. 是否只允许 docs-only 静态校验规则设计。
3. 是否禁止创建校验脚本。
4. 是否禁止修改代码、tests、frontend、backend、config。
5. 是否继续禁止运行服务和 endpoint。

如未取得上述授权，KG-08 完成后必须停止。

## 10. KG-08 结论

KG-08 结论如下：

1. candidate JSON 已限定为 docs 下的非运行态候选实体。
2. candidate JSON 只记录路径、摘要、风险、专业标签、隔离规则、禁用标志和后续授权条件。
3. candidate JSON 不复制原始知识图谱正文。
4. candidate JSON 不被 ZDoc 自动读取。
5. candidate JSON 不接入 RAG、prompt registry 或 system instruction registry。
6. candidate JSON 不作为 evidence 或评分依据。
7. KG-09 若继续推进，应先做静态校验规则设计。
8. KG-09 不得自动进入。
