# ZDoc KG-12 Controlled Pilot Manifest Candidate Freeze Record and Next Gate

## 1. KG-12 执行摘要

KG-12 是对 KG-08 disabled manifest candidate 的 docs-only freeze 记录。本步骤只记录冻结对象、冻结依据、冻结后约束和 KG-13 授权门槛，不修改 KG-08 candidate JSON，不创建 validator，不注册 manifest，不启用知识包，不接入 RAG / prompt registry / system instruction registry，也不进入 ZDoc 运行链路。

KG-12 结论：KG-08 candidate JSON 已通过 KG-09 静态规则设计、KG-10 人工静态校验和 KG-11 处置 freeze gate 复核，可冻结为非运行态候选实体。冻结后仍必须保持 `candidate_only`、`not_registered`、`enabled=false` 和全部运行开关关闭状态。

## 2. 冻结对象

| 项目 | 内容 |
| --- | --- |
| 冻结对象 | KG-08 disabled manifest candidate JSON |
| 文件路径 | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` |
| 试点方向 | `全能索引 + 市政桥梁 KG01` |
| 备选方向 | `全能索引 + 医院装修改造 KG02` |
| `source_mode` | `path_and_summary_only` |
| `status` | `candidate_only` |
| `registration_status` | `not_registered` |
| `activation_requires` | `manual_authorization_after_KG08_review` |
| source 条目数 | 5 |
| 当前用途 | docs candidate，路径与摘要索引，不参与运行 |

冻结对象只作为候选实体记录，不代表已注册 manifest，不代表可被 ZDoc 自动读取，不代表已获得检索、生成、证据、评分、写回或导出权限。

## 3. KG-09 / KG-10 / KG-11 承接结论

| 阶段 | 承接结论 | KG-12 处置 |
| --- | --- | --- |
| KG-09 | 已定义必填字段、禁止字段、disabled flags、`source_mode`、`status`、`registration_status`、source path / summary、risk、domain、isolation rules 的静态校验规则 | 作为 freeze 的规则依据 |
| KG-10 | 人工静态校验通过，JSON 语法有效，未发现 blocker，disabled flags 全部为 `false`，`status="candidate_only"`，`registration_status="not_registered"` | 作为 freeze 的校验证据 |
| KG-11 | 判定 candidate 满足 freeze gate，可冻结为 docs-only、disabled、not registered 的非运行态候选实体 | 作为 KG-12 freeze 记录的直接依据 |

KG-12 不重新扩大 KG-09/KG-10/KG-11 的授权范围。所有结论只用于 docs-only freeze 记录。

## 4. Freeze 判定结论

KG-12 freeze 判定如下：

1. candidate JSON 语法有效；
2. 必填字段满足 KG-09 规则；
3. 未发现 KG-09 禁止字段；
4. disabled flags 全部为布尔值 `false`；
5. `source_mode="path_and_summary_only"`；
6. `status="candidate_only"`；
7. `registration_status="not_registered"`；
8. source path 只引用原始资料路径；
9. source summary 只记录摘要；
10. 未发现系统指令原文搬运；
11. 未发现 prompt、青天评标、满分门控原文搬运；
12. 未发现 evidence 化字段；
13. 未发现 scoring basis 字段；
14. 未发现 RAG、prompt registry、system instruction registry 注册线索；
15. 未发现 endpoint、service、writeback、export 运行线索；
16. KG-10 未发现 blocker、major 或 minor 问题；
17. KG-11 已确认可进入 freeze gate。

结论：KG-08 candidate JSON 可冻结为非运行态、不可自动读取、不可注册、不可启用的 docs candidate。

## 5. Freeze 后状态

freeze 后必须继续保持以下状态：

| 字段 | 冻结后状态 | 说明 |
| --- | --- | --- |
| `status` | `candidate_only` | 只允许作为候选 |
| `registration_status` | `not_registered` | 未注册到任何运行 registry |
| `source_mode` | `path_and_summary_only` | 只记录路径与摘要 |
| `enabled` | `false` | 不启用 |
| `runtime_access` | `false` | 运行链路不可访问 |
| `rag_enabled` | `false` | 不进入 RAG |
| `evidence_enabled` | `false` | 不作为 evidence |
| `scoring_enabled` | `false` | 不作为评分依据 |
| `prompt_registry_enabled` | `false` | 不进入 prompt registry |
| `system_instruction_registry_enabled` | `false` | 不进入 system instruction registry |
| `writeback_enabled` | `false` | 不触发写回 |
| `export_enabled` | `false` | 不触发导出 |

freeze 是候选状态锁定，不是启用审批。

## 6. 禁止变更项

在 KG-13 获得新的明确人工授权前，以下内容不得变更：

| 禁止变更项 | 禁止原因 |
| --- | --- |
| KG-08 candidate JSON 文件 | KG-12 只做 freeze 记录，不做实体修改 |
| `source_path` | 防止改变溯源对象或引入复制件 |
| `source_summary` | 防止搬运原文或写入动作性指令 |
| disabled flags | 防止候选实体被误启用 |
| `registration_status` | 防止候选实体被误判为已注册 |
| `status` | 防止候选态被绕过 |
| `source_mode` | 防止从路径摘要模式扩展为正文承载 |
| `risk_level` | 风险等级调整必须重新复核 |
| `domain_tags` | 专业标签调整必须重新复核 |
| `isolation_rules` | 隔离规则调整必须重新复核 |
| `future_authorization_conditions` | 授权条件调整必须重新复核 |

如未来确需变更上述任一项，应先形成独立授权任务，并重新执行静态校验。

## 7. 锁定结论

KG-12 对以下锁定项作出冻结结论：

| 锁定项 | 冻结值 | KG-12 结论 |
| --- | --- | --- |
| `enabled` | `false` | 锁定 |
| `runtime_access` | `false` | 锁定 |
| `rag_enabled` | `false` | 锁定 |
| `evidence_enabled` | `false` | 锁定 |
| `scoring_enabled` | `false` | 锁定 |
| `prompt_registry_enabled` | `false` | 锁定 |
| `system_instruction_registry_enabled` | `false` | 锁定 |
| `writeback_enabled` | `false` | 锁定 |
| `export_enabled` | `false` | 锁定 |

任何将上述字段改为 `true` 的动作都不属于 KG-12 范围，也不得在未取得后续明确授权前执行。

## 8. System Instruction 隔离结论

KG-12 继续确认：系统指令类内容不得原样作为 ZDoc system instruction。

冻结后的约束为：

1. candidate JSON 不得包含系统指令原文；
2. candidate JSON 不得新增 `system_instruction` 正文字段；
3. `system_instruction_registry_enabled=false` 必须保持；
4. `system_instruction_sources_must_remain_quarantined` 必须保持；
5. 不得通过 prompt registry 绕道启用系统指令类内容；
6. 不得被 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回链路读取。

若未来希望使用系统指令类资料中的方法论，只能在另行授权后进行人工拆解、降权、改写和复核。

## 9. 青天评标 / 满分门控隔离结论

KG-12 继续确认：青天评标、满分门控、评分响应类内容不得作为 evidence 或 scoring basis。

冻结后的约束为：

1. `evidence_enabled=false` 必须保持；
2. `scoring_enabled=false` 必须保持；
3. `not_evidence` 必须保持；
4. `not_scoring_basis` 必须保持；
5. `qingtian_review_and_full_score_gate_sources_are_reference_candidates_only` 必须保持；
6. 不得把青天评标 / 满分门控内容作为自动评分、复评、满分优化或 ZBid 写回依据；
7. 不得把相关内容作为正式 evidence 引用。

## 10. KG-13 授权条件

KG-13 不得自动进入。若 ChatGPT 总控决定继续，建议 KG-13 只能在明确人工授权后执行，并优先限定为以下 docs-only / static-only 事项之一：

1. 设计 candidate freeze record 的人工签署字段；
2. 设计 candidate 变更审计规则；
3. 设计从 `candidate_only` 到未来注册态的门槛清单；
4. 设计真实 validator 的伪代码或规则映射，但不创建脚本；
5. 复核是否需要新增独立 validator 任务；
6. 复核是否需要新增 `frozen_at`、`frozen_by`、`freeze_reason`、`freeze_source_commit` 等字段，但不得直接修改 candidate JSON。

KG-13 如涉及以下动作，必须取得更高等级的明确授权：

1. 修改 KG-08 candidate JSON；
2. 创建真实 validator 脚本；
3. 创建运行态 manifest；
4. 注册 manifest；
5. 将 candidate 移入运行配置目录；
6. 启用 retrieval / generation / evidence / scoring / writeback / export；
7. 接入 RAG、prompt registry 或 system instruction registry；
8. 复制、移动、删除、重命名或改写 `AI知识图谱大全` 原文件；
9. 运行 ZDoc、ZBid、Ollama、端口或 endpoint；
10. 触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
11. 生成 DOCX；
12. 写入 `output/job/export`。

## 11. KG-12 最终记录

KG-12 最终记录如下：

1. KG-08 candidate JSON 被冻结为 docs-only disabled candidate；
2. freeze 不改变 candidate JSON；
3. freeze 不注册 manifest；
4. freeze 不启用知识包；
5. freeze 不接入 RAG、prompt registry、system instruction registry；
6. freeze 不允许 evidence 化或评分依据化；
7. freeze 后仍保持 `candidate_only`、`not_registered`、`path_and_summary_only`；
8. 所有 disabled flags 继续锁定为 `false`；
9. system instruction 类内容继续隔离；
10. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
11. KG-13 需要 ChatGPT 总控再次人工授权，不得自动进入。
