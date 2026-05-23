# ZDoc KG-14 Frozen Candidate Registry Candidate Schema and Disabled Pre-Registration Draft Design

## 1. KG-14 执行摘要

KG-14 是对 KG-08 frozen disabled manifest candidate 的 docs-only schema 与 disabled pre-registration draft 设计归档。本步骤只设计 registry candidate 草案层的字段结构和预注册门槛，不创建 registry 文件，不注册 manifest，不修改 KG-08 candidate JSON，不创建 validator，不接入 RAG / prompt registry / system instruction registry，不启用任何知识包。

KG-14 结论：frozen candidate 仍必须保持 `candidate_only`、`not_registered`、disabled。registry candidate 草案层只能作为未来人工审核前的设计层，不能被 ZDoc 自动读取，不能进入运行 registry，不能参与检索、生成、证据、评分、写回或导出。

## 2. 复核对象

| 对象 | 路径 | KG-14 用途 |
| --- | --- | --- |
| KG-13 registry isolation gate | `docs/zdoc-kg-frozen-manifest-candidate-registry-isolation-and-pre-registration-gate-kg13.md` | 承接 registry isolation 与 pre-registration gate |
| KG-12 freeze record | `docs/zdoc-kg-controlled-pilot-manifest-candidate-freeze-record-and-next-gate-kg12.md` | 承接 frozen candidate 状态和锁定项 |
| KG-08 candidate JSON | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 确认 frozen candidate 当前字段 |
| KG-08 review | `docs/zdoc-kg-controlled-pilot-disabled-manifest-candidate-kg08-review.md` | 确认非运行态候选实体边界 |

## 3. Frozen Candidate 当前状态确认

| 字段 | 当前状态 | KG-14 结论 |
| --- | --- | --- |
| `pilot_direction` | `全能索引 + 市政桥梁 KG01` | 首个试点方向保持不变 |
| `backup_direction` | `全能索引 + 医院装修改造 KG02` | 仅作备选方向记录 |
| `source_mode` | `path_and_summary_only` | 只允许路径与摘要 |
| `status` | `candidate_only` | 仍为候选 |
| `registration_status` | `not_registered` | 仍未注册 |
| `activation_requires` | `manual_authorization_after_KG08_review` | 仍需人工授权 |
| `enabled` | `false` | 仍未启用 |
| `runtime_access` | `false` | 运行链路不可访问 |
| `rag_enabled` | `false` | 未接入 RAG |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | `false` | 未接入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 未接入 system instruction registry |
| `writeback_enabled` | `false` | 未启用写回 |
| `export_enabled` | `false` | 未启用导出 |

KG-14 不改变 KG-08 candidate JSON。上述状态只作为 schema 设计输入，不代表任何运行授权。

## 4. KG-13 Registry Isolation 结论承接

KG-14 继承 KG-13 的以下结论：

1. registry isolation 优先于 registry registration；
2. frozen candidate 默认停留在 docs 层；
3. 不得从 `docs/kg-manifest-candidates/` 自动扫描并加载 candidate；
4. 不得将 candidate path 写入运行 registry；
5. 不得因 freeze record 通过而自动创建 registry 文件；
6. 不得因 pre-registration gate 通过而自动注册 manifest；
7. 所有 registry candidate 字段默认 disabled；
8. 所有 registry 变更必须经过人工授权、静态校验和单独提交；
9. registry isolation 失败时，后续注册流程必须停止；
10. KG-14 不创建 registry 文件，也不执行注册。

## 5. Registry Candidate 草案层定位

registry candidate 草案层是 future design layer，只用于描述未来可能的预注册草案结构。

定位如下：

1. 它不是运行 registry；
2. 它不是 manifest registry；
3. 它不是 RAG registry；
4. 它不是 prompt registry；
5. 它不是 system instruction registry；
6. 它不是知识包实体；
7. 它不允许被 ZDoc 自动读取；
8. 它不允许参与 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
9. 它只可在未来人工授权后作为 docs-only 或 disabled candidate draft 进一步设计；
10. KG-14 只定义草案字段，不生成草案实体。

## 6. Registry Candidate Schema 字段清单

未来若总控授权创建 registry candidate 草案，其 schema 至少应包含以下字段。KG-14 仅记录设计，不创建 JSON、YAML、CSV、DB 或其他实体文件。

| 字段 | 类型 | 默认值或要求 | 说明 |
| --- | --- | --- | --- |
| `registry_candidate_id` | string | 非空、稳定、不得与运行 registry ID 混用 | 草案层候选 ID |
| `schema_version` | string | 非空 | 只标识草案 schema 版本 |
| `manifest_candidate_path` | string | 只能指向 docs 下 frozen candidate | 仅作溯源，不授权自动读取 |
| `source_candidate_commit` | string | 可为空或记录冻结 commit | 用于人工追踪 |
| `pilot_direction` | string | `全能索引 + 市政桥梁 KG01` | 首个试点方向 |
| `backup_direction` | string | `全能索引 + 医院装修改造 KG02` | 备选试点方向 |
| `source_mode` | string | `path_and_summary_only` | 禁止正文承载 |
| `candidate_status` | string | `candidate_only` | 保持候选态 |
| `registration_status` | string | `not_registered` | 保持未注册 |
| `registry_candidate_status` | string | `draft_only` | 不得表示 active |
| `enabled` | boolean | `false` | 不启用 |
| `runtime_access` | boolean | `false` | 不允许运行访问 |
| `rag_enabled` | boolean | `false` | 不进入 RAG |
| `evidence_enabled` | boolean | `false` | 不作为 evidence |
| `scoring_enabled` | boolean | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | boolean | `false` | 不进入 prompt registry |
| `system_instruction_registry_enabled` | boolean | `false` | 不进入 system instruction registry |
| `writeback_enabled` | boolean | `false` | 不写回 |
| `export_enabled` | boolean | `false` | 不导出 |
| `manual_review_required` | boolean | `true` | 必须人工复核 |
| `review_status` | string | `pending` | 未审核不得推进 |
| `risk_level` | string | 不低于来源候选风险 | 不得自动降级 |
| `risk_reasons` | array | 非空 | 记录隔离原因 |
| `domain_tags` | array | 非空 | 静态专业标签 |
| `isolation_rules` | array | 必须包含非运行、非 evidence、非 scoring、系统指令隔离规则 | 隔离规则 |
| `allowed_next_step` | string | `manual_authorization_required` | 不得自动推进 |
| `created_for_stage` | string | `KG-14` 或后续授权阶段 | 记录来源阶段 |
| `notes` | string | 可为空 | 人工说明 |

## 7. `manifest_candidate_path` 约束

`manifest_candidate_path` 是 registry candidate schema 中的关键隔离字段。

约束如下：

1. 只能指向 docs 下 frozen candidate；
2. 当前唯一允许目标为 `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`；
3. 不得指向 `/Users/youfeini/Desktop/AI知识图谱大全` 原文件；
4. 不得指向 ZDoc 运行配置目录；
5. 不得指向 backend、frontend、config、tests、output、job 或 export；
6. 不得被解释为运行时读取授权；
7. 不得被自动扫描器使用；
8. 不得作为 RAG corpus path；
9. 不得作为 prompt 或 system instruction 来源路径；
10. 仅用于人工溯源和静态复核。

## 8. Disabled Pre-Registration Draft 字段清单

未来若总控授权进入 disabled pre-registration draft，草案字段至少应包括：

| 字段 | 必须值或默认值 | 预注册含义 |
| --- | --- | --- |
| `pre_registration_id` | 非空、草案层唯一 | 预注册草案 ID |
| `registry_candidate_id` | 引用草案候选 ID | 关联 registry candidate |
| `manifest_candidate_path` | 指向 docs frozen candidate | 溯源路径 |
| `pre_registration_status` | `draft_only` | 仅草案 |
| `registration_status` | `not_registered` | 未注册 |
| `enabled` | `false` | 禁用 |
| `runtime_access` | `false` | 运行不可访问 |
| `rag_enabled` | `false` | RAG 禁用 |
| `prompt_registry_enabled` | `false` | prompt registry 禁用 |
| `system_instruction_registry_enabled` | `false` | system instruction registry 禁用 |
| `evidence_enabled` | `false` | evidence 禁用 |
| `scoring_enabled` | `false` | scoring 禁用 |
| `writeback_enabled` | `false` | writeback 禁用 |
| `export_enabled` | `false` | export 禁用 |
| `manual_review_required` | `true` | 必须人工审核 |
| `review_status` | `pending` | 未审核 |
| `reviewer` | 空值或人工填写 | 不得自动填充为通过 |
| `approval_status` | `not_approved` | 未批准 |
| `activation_requires` | `future_manual_authorization` | 后续人工授权 |
| `blocked_registries` | 包含 RAG、prompt、system instruction、runtime | 阻断 registry |
| `blocked_runtime_actions` | 包含 generate、export_docx、review_apply、zbid_writeback | 阻断运行动作 |
| `audit_notes` | 可为空 | 人工说明 |

disabled pre-registration draft 不等同于 registration request，不得被系统解释为注册申请已通过。

## 9. Candidate 状态保持要求

无论未来是否设计 registry candidate 草案，KG-08 candidate 都必须保持：

1. `candidate_only`；
2. `not_registered`；
3. disabled；
4. `path_and_summary_only`；
5. 不进入运行目录；
6. 不被 ZDoc 自动读取；
7. 不被 RAG registry 读取；
8. 不被 prompt registry 读取；
9. 不被 system instruction registry 读取；
10. 不作为 evidence；
11. 不作为 scoring basis；
12. 不作为写回、导出、审核应用或生成链路输入。

## 10. 默认锁定项

registry candidate schema 与 disabled pre-registration draft 必须默认锁定以下字段：

| 字段 | 默认锁定值 | 说明 |
| --- | --- | --- |
| `enabled` | `false` | 不启用 |
| `runtime_access` | `false` | 不允许运行读取 |
| `rag_enabled` | `false` | 不进入 RAG |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 不进入 system instruction registry |
| `writeback_enabled` | `false` | 不写回 |
| `export_enabled` | `false` | 不导出 |

任何默认锁定项为 `true`，都应判定为草案不合格。

## 11. RAG Registry 隔离边界

RAG registry 隔离边界如下：

1. `rag_enabled=false` 必须保持；
2. 不得创建 RAG index；
3. 不得创建 embedding 配置；
4. 不得创建 corpus entry；
5. 不得将 source path 自动加入检索语料；
6. 不得将 source summary 当作可检索正文；
7. 不得生成向量；
8. 不得运行检索链路；
9. 不得把 registry candidate 草案放入 RAG 配置目录；
10. 未来若允许进入 RAG 设计，必须另行授权，并且默认仍为 disabled。

## 12. Prompt Registry 隔离边界

prompt registry 隔离边界如下：

1. `prompt_registry_enabled=false` 必须保持；
2. 不得创建 prompt pack；
3. 不得创建 prompt template；
4. 不得创建 generation prompt；
5. 不得把 source summary 改写成 prompt；
6. 不得把系统指令类内容通过 prompt registry 绕道启用；
7. 不得让全能索引、市政桥梁 KG01 或医院装修改造 KG02 备选内容参与 `/generate`；
8. 未来若允许 prompt 相关设计，必须另行授权，并且默认仍为 disabled。

## 13. System Instruction Registry 隔离边界

system instruction registry 隔离边界如下：

1. `system_instruction_registry_enabled=false` 必须保持；
2. 不得创建 system instruction pack；
3. 不得创建 system instruction 正文字段；
4. 不得把系统指令类内容原样转为 ZDoc system instruction；
5. 不得把 source summary 改写为隐性 system instruction；
6. 不得将全能索引或任何 KG 文件作为系统指令启用；
7. 不得通过 prompt registry 绕过隔离；
8. 未来若需要提取约束思想，必须人工拆解、降权、改写并重新评审。

## 14. System Instruction 隔离结论

KG-14 结论：系统指令类内容不得转为 ZDoc system instruction。

该结论适用于：

1. KG-08 candidate JSON；
2. 未来 registry candidate 草案；
3. 未来 disabled pre-registration draft；
4. 全能索引相关资料；
5. 市政桥梁 KG01 试点资料；
6. 医院装修改造 KG02 备选资料；
7. 任何被识别为系统指令、执行命令、写回、导出、提交、覆盖或自动评分的内容。

## 15. 青天评标 / 满分门控隔离结论

KG-14 结论：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

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
10. 不得生成正式证据引用；
11. 不得在 registry candidate 草案层改变上述边界。

## 16. KG-15 授权条件

KG-15 不得自动进入。若 ChatGPT 总控决定继续，建议 KG-15 只能在明确人工授权后执行，并优先限定为以下事项之一：

1. 设计 docs-only registry candidate 草案审查清单；
2. 设计 disabled pre-registration draft 的静态校验规则；
3. 设计 registry candidate 与 frozen candidate 的人工关联检查；
4. 设计 `manifest_candidate_path` 的路径校验规则；
5. 设计 disabled flags 的静态校验规则；
6. 设计人工审核签署字段；
7. 复核是否需要真实 validator，但不创建脚本；
8. 复核是否需要创建草案实体，但 KG-15 不得在未授权时创建 registry 文件。

KG-15 如涉及以下动作，必须取得更高等级明确授权：

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

## 17. KG-14 最终结论

KG-14 最终结论如下：

1. frozen candidate 当前仍是 `candidate_only`；
2. frozen candidate 当前仍是 `not_registered`；
3. frozen candidate 当前仍是 disabled；
4. registry candidate 草案层只作为未来人工审核前的设计层；
5. `manifest_candidate_path` 仅允许指向 docs 下 frozen candidate；
6. registry candidate schema 与 disabled pre-registration draft 必须默认全部禁用；
7. KG-14 不创建 registry 文件；
8. KG-14 不注册 manifest；
9. KG-14 不接入 RAG、prompt registry 或 system instruction registry；
10. system instruction 类内容继续不得转为 system instruction；
11. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
12. KG-15 必须再次由 ChatGPT 总控人工授权，不得自动进入。
