# ZDoc KG-15 Disabled Registry Candidate Entity Creation Review

## 1. KG-15 执行摘要

KG-15 在 docs 目录下新增 disabled registry candidate 候选实体，并同步新增本 review 文档。本步骤不修改 KG-08 manifest candidate，不创建真实 registry 文件，不注册 manifest，不创建 validator，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包，不进入 ZDoc 运行链路。

新增 registry candidate JSON 位于：

- `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json`

该 JSON 只记录 registry candidate ID、指向 docs 下 frozen manifest candidate 的路径、试点方向、禁用标志、隔离规则、预注册规则、人工授权要求、风险等级、专业标签和后续 KG-16 授权条件。

## 2. 前置复核承接

| 来源阶段 | 承接结论 |
| --- | --- |
| KG-14 | registry candidate schema 与 disabled pre-registration draft 只能作为 docs-only 设计层，不创建 registry 文件、不注册、不启用 |
| KG-13 | registry isolation 优先于 registration，frozen candidate 仍是 `candidate_only` / `not_registered` / disabled |
| KG-12 | KG-08 manifest candidate 已冻结为 docs-only disabled candidate，冻结不改变 JSON、不注册 manifest |
| KG-08 | manifest candidate 只记录路径、摘要、风险、标签、隔离规则、禁用标志和后续授权条件，不能被 ZDoc 自动读取 |

KG-15 只把 KG-14 的 schema 设计落为 docs 下 disabled registry candidate 候选文件，不进入运行注册。

## 3. Registry Candidate 当前状态

| 字段 | 当前值 | KG-15 结论 |
| --- | --- | --- |
| `status` | `registry_candidate_only` | 仅为 registry candidate 候选 |
| `registration_status` | `not_registered` | 未注册 |
| `source_mode` | `path_and_summary_only` | 只允许路径与摘要模式 |
| `activation_requires` | `manual_authorization_after_KG15_review` | 后续必须人工授权 |
| `manifest_candidate_path` | docs 下 KG-08 frozen candidate | 仅作溯源，不授权读取 |
| `linked_manifest_candidate_path` | docs 下 KG-08 frozen candidate | 仅作溯源，不授权读取 |
| `manual_authorization_required` | `true` | 必须人工授权 |
| `risk_level` | `R2` | 候选风险，不代表可运行 |

## 4. Disabled Flags 复核

| 字段 | 必须值 | KG-15 结论 |
| --- | --- | --- |
| `enabled` | `false` | 锁定禁用 |
| `runtime_access` | `false` | 运行链路不可访问 |
| `rag_enabled` | `false` | 不进入 RAG |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 不进入 system instruction registry |
| `writeback_enabled` | `false` | 不写回 |
| `export_enabled` | `false` | 不导出 |

上述字段均为 boolean `false`，不得在 KG-15 中改为 `true`。

## 5. 为什么仍属于 Docs-Only 候选实体

该 registry candidate 仍属于 docs-only 候选实体，原因如下：

1. 文件位于 `docs/kg-registry-candidates/`；
2. 文件不在 backend、frontend、config、tests 或任何运行配置目录；
3. `status="registry_candidate_only"`；
4. `registration_status="not_registered"`；
5. 全部 disabled flags 均为 `false`；
6. `manifest_candidate_path` 只指向 docs 下 frozen manifest candidate；
7. `source_mode="path_and_summary_only"`；
8. `activation_requires="manual_authorization_after_KG15_review"`；
9. `manual_authorization_required=true`；
10. isolation rules 明确禁止运行读取、注册、RAG、prompt registry、system instruction registry、evidence、scoring、writeback 和 export。

因此，该文件只能作为人工审核候选，不具备任何运行权限。

## 6. 为什么不是正式 Registry

该 registry candidate 不是正式 registry，原因如下：

1. 它没有放入运行 registry 目录；
2. 它没有任何 registry loader 引用；
3. 它没有注册到 manifest registry；
4. 它没有注册到 RAG registry；
5. 它没有注册到 prompt registry；
6. 它没有注册到 system instruction registry；
7. 它没有 endpoint、service、runtime config、writeback target 或 export target；
8. 它没有 registry ID 可供运行链路加载；
9. 它的 `registration_status` 明确为 `not_registered`；
10. 它的 `pre_registration_rules.pre_registration_status` 仅为 `draft_only`。

文件名中的 `registry.candidate` 只表示候选类型，不表示真实 registry。

## 7. 为什么不能被 ZDoc 自动读取

该 registry candidate 不能被 ZDoc 自动读取，原因如下：

1. 它位于 docs 下；
2. 它没有进入任何运行配置目录；
3. 它没有被任何代码、配置、router、service 或 registry 引用；
4. `runtime_access=false`；
5. `registration_status=not_registered`；
6. `enabled=false`；
7. `rag_enabled=false`；
8. `prompt_registry_enabled=false`；
9. `system_instruction_registry_enabled=false`；
10. isolation rules 包含 `not_loaded_by_generate_export_review_or_writeback`。

即使该文件是 JSON，也不得被自动扫描器、运行时加载器或生成链路读取。

## 8. Manifest Candidate Path 边界

`manifest_candidate_path` 和 `linked_manifest_candidate_path` 仅允许指向 docs 下 frozen manifest candidate：

```text
docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json
```

该路径只用于人工溯源和静态校验，不得用于：

1. 运行时读取；
2. RAG corpus path；
3. prompt template source；
4. system instruction source；
5. evidence source；
6. scoring basis source；
7. writeback source；
8. export source。

## 9. System Instruction 隔离结论

KG-15 继续确认：系统指令类内容不得转为 ZDoc system instruction。

强制边界如下：

1. `system_instruction_registry_enabled=false` 必须保持；
2. registry candidate 不得包含 `system_instruction` 正文字段；
3. registry candidate 不得包含系统指令原文；
4. 不得通过 prompt registry 绕过 system instruction 隔离；
5. 后续若需要提取约束思想，必须人工拆解、降权、改写并重新评审。

## 10. 青天评标 / 满分门控隔离结论

KG-15 继续确认：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

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

## 11. KG-16 建议方向

KG-16 若继续推进，应先做 registry candidate 静态校验规则设计。

建议 KG-16 只允许设计：

1. registry candidate JSON 必填字段校验规则；
2. disabled flags 必须为 boolean `false` 的校验规则；
3. `status="registry_candidate_only"` 的校验规则；
4. `registration_status="not_registered"` 的校验规则；
5. `activation_requires="manual_authorization_after_KG15_review"` 的校验规则；
6. `manifest_candidate_path` 只能指向 docs 下 frozen candidate 的校验规则；
7. `source_mode="path_and_summary_only"` 的校验规则；
8. RAG / prompt registry / system instruction registry 隔离规则；
9. evidence / scoring / writeback / export 禁用规则；
10. system instruction 与青天评标 / 满分门控隔离规则。

KG-16 不得自动进入。

## 12. KG-16 禁止边界

KG-16 仍不得：

1. 修改 KG-08 candidate JSON；
2. 修改 KG-15 registry candidate JSON，除非总控明确授权；
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

## 13. KG-15 最终结论

KG-15 最终结论如下：

1. 已新增 docs-only disabled registry candidate 候选实体；
2. 已新增 KG-15 review 文档；
3. registry candidate 不是正式 registry；
4. registry candidate 不得被 ZDoc 自动读取；
5. registry candidate 未注册 manifest；
6. registry candidate 未接入 RAG、prompt registry 或 system instruction registry；
7. registry candidate 未启用任何知识包；
8. system instruction 类内容继续不得转为 system instruction；
9. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
10. KG-16 需要 ChatGPT 总控再次人工授权，不得自动进入。
