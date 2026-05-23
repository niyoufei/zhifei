# ZDoc KG-11 Controlled Pilot Manifest Candidate Validation Disposition and Freeze Gate

## 1. KG-11 执行摘要

KG-11 是对 KG-08 disabled manifest candidate、KG-09 静态校验规则、KG-10 人工静态校验报告的处置结论与 freeze gate 归档。本步骤仅形成 docs-only 结论文件，不修改 candidate JSON，不创建 validator，不注册 manifest，不接入 ZDoc 运行链路。

KG-11 结论：KG-08 candidate JSON 目前满足 KG-09/KG-10 的静态约束，可作为非运行态候选实体进入 freeze gate。freeze 后仍必须保持 `candidate_only`、`not_registered`、`enabled=false` 和全部运行开关关闭状态。

## 2. 复核对象

| 对象 | 路径 | KG-11 用途 |
| --- | --- | --- |
| KG-10 人工静态校验报告 | `docs/zdoc-kg-controlled-pilot-manifest-candidate-manual-static-validation-report-kg10.md` | 提取校验结论和问题清单 |
| KG-09 静态校验规则 | `docs/zdoc-kg-controlled-pilot-manifest-candidate-static-validation-rules-kg09.md` | 复核 KG-10 所依据的规则边界 |
| KG-08 candidate JSON | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 确认候选实体当前状态 |
| KG-08 review | `docs/zdoc-kg-controlled-pilot-disabled-manifest-candidate-kg08-review.md` | 确认非运行态候选实体定位 |

## 3. KG-10 人工静态校验结论摘要

| 校验项 | KG-10 结论 | KG-11 处置 |
| --- | --- | --- |
| JSON 语法 | 通过 | 可作为 freeze 前置条件 |
| 必填字段 | 通过 | 无需补字段 |
| 禁止字段 | 通过 | 不需要清理字段 |
| disabled flags | 通过 | 继续锁定为禁用 |
| `status` | `candidate_only` | freeze 后保持不变 |
| `registration_status` | `not_registered` | freeze 后保持不变 |
| `source_mode` | `path_and_summary_only` | 继续禁止复制原文 |
| `source_path` / `source_summary` | 通过 | 继续仅保留路径与摘要 |
| `risk_level` / `domain_tags` / `isolation_rules` | 通过 | 可作为静态描述字段保留 |
| system instruction 隔离 | 通过 | 不得进入 system instruction registry |
| evidence / scoring | 通过 | 不得作为 evidence 或 scoring basis |

KG-10 未发现 blocker、major 或 minor 问题。KG-10 的非阻断说明是：当前没有真实 validator，这是 KG-09/KG-10 阶段的设计边界，不构成 KG-11 freeze gate blocker。

## 4. KG-08 Candidate JSON 当前状态确认

| 字段 | 当前状态 | KG-11 结论 |
| --- | --- | --- |
| candidate 文件位置 | `docs/kg-manifest-candidates/` | 位于 docs 候选区，不属于运行配置目录 |
| 试点方向 | `全能索引 + 市政桥梁 KG01` | 与总控试点结论一致 |
| 备选方向 | `全能索引 + 医院装修改造 KG02` | 仅作备选记录 |
| `source_mode` | `path_and_summary_only` | 符合不复制原文边界 |
| `status` | `candidate_only` | 非运行态候选 |
| `registration_status` | `not_registered` | 未注册 |
| `activation_requires` | `manual_authorization_after_KG08_review` | 后续启用必须人工授权 |
| source 条目 | 路径与摘要形式 | 未复制 AI 知识图谱原文 |

KG-11 不对 KG-08 candidate JSON 做任何修改。若未来需要调整字段、source 条目、风险等级或摘要，应另行授权，并重新执行静态校验。

## 5. 问题分级与处置

| 级别 | 是否存在 | 说明 | 处置 |
| --- | --- | --- | --- |
| Blocker | 否 | 未发现阻止 freeze 的结构性问题 | 允许进入 freeze gate 判断 |
| Major | 否 | 未发现注册、启用、运行链路或证据化风险 | 保持全部禁用 |
| Minor | 否 | 未发现需立即修正的文档或字段问题 | 不修改 candidate |
| Note | 是 | 尚无真实 validator，且 KG-11 不创建 validator | 作为后续 KG-12 授权条件之一 |

KG-11 的处置建议是保留 candidate 原样冻结为非运行态候选。不得在 KG-11 中直接修正、补写、重排或格式化 candidate JSON。

## 6. Candidate Freeze 判定条件

candidate 进入 freeze gate 至少满足以下条件：

1. candidate JSON 语法有效；
2. KG-09 必填字段均存在；
3. KG-09 禁止字段均不存在；
4. `enabled=false`；
5. `runtime_access=false`；
6. `rag_enabled=false`；
7. `evidence_enabled=false`；
8. `scoring_enabled=false`；
9. `prompt_registry_enabled=false`；
10. `system_instruction_registry_enabled=false`；
11. `writeback_enabled=false`；
12. `export_enabled=false`；
13. `status="candidate_only"`；
14. `registration_status="not_registered"`；
15. `source_mode="path_and_summary_only"`；
16. `source_path` 只记录来源路径；
17. `source_summary` 只记录摘要；
18. system instruction 类内容继续隔离；
19. 青天评标 / 满分门控类内容不得作为 evidence 或 scoring basis；
20. 未发现 blocker、major、minor 问题。

KG-11 判定：当前 KG-08 candidate 满足上述 freeze gate 条件，可冻结为 docs-only、disabled、not registered 的候选实体。

## 7. Freeze 后保持约束

freeze 后 candidate 仍必须保持以下约束：

| 约束 | 必须状态 |
| --- | --- |
| `status` | `candidate_only` |
| `registration_status` | `not_registered` |
| `enabled` | `false` |
| `runtime_access` | `false` |
| `rag_enabled` | `false` |
| `evidence_enabled` | `false` |
| `scoring_enabled` | `false` |
| `prompt_registry_enabled` | `false` |
| `system_instruction_registry_enabled` | `false` |
| `writeback_enabled` | `false` |
| `export_enabled` | `false` |
| `source_mode` | `path_and_summary_only` |

freeze 不等同于注册、启用、接入检索、接入生成、进入 system instruction registry 或进入评分链路。

## 8. 锁定项复核结论

KG-11 复核认为以下锁定项应作为后续阶段的硬性前置条件：

| 锁定项 | KG-11 结论 |
| --- | --- |
| `enabled=false` | 必须保持 |
| `runtime_access=false` | 必须保持 |
| `rag_enabled=false` | 必须保持 |
| `evidence_enabled=false` | 必须保持 |
| `scoring_enabled=false` | 必须保持 |
| `prompt_registry_enabled=false` | 必须保持 |
| `system_instruction_registry_enabled=false` | 必须保持 |
| `writeback_enabled=false` | 必须保持 |
| `export_enabled=false` | 必须保持 |

任何将上述字段改为 `true` 的动作，都不得由 KG-11 执行，也不得在未取得后续明确人工授权前执行。

## 9. System Instruction 隔离结论

KG-11 继承 KG-03R、KG-04、KG-05、KG-06、KG-07、KG-08、KG-09、KG-10 的一致边界：系统指令类内容不得原样作为 ZDoc system instruction。

KG-08 candidate 中与 system instruction 风险相关的隔离规则应继续保留：

1. 系统指令来源仅可作为隔离参考候选；
2. 不得注册到 system instruction registry；
3. 不得在 prompt registry 中绕道启用；
4. 不得被 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回链路读取；
5. 若后续需要使用其中的约束思想，必须先人工拆解、改写、降权，并重新评审。

## 10. 青天评标 / 满分门控结论

青天评标、满分门控、评分响应类内容只可作为人工参考或受控候选资料，不得直接作为：

1. evidence；
2. scoring basis；
3. 自动评分依据；
4. 满分判定依据；
5. 写回建议依据；
6. 运行时强制门控。

KG-08 candidate 的 `evidence_enabled=false` 与 `scoring_enabled=false` 必须继续作为冻结条件保留。

## 11. KG-12 授权条件

KG-12 不得自动进入。若 ChatGPT 总控决定进入 KG-12，建议授权范围仍应被限定为以下一种或多种 docs-only / static-only 事项：

1. 形成 candidate freeze record 文档；
2. 设计真实 validator 的字段校验规格，但不创建脚本；
3. 设计候选 manifest 的变更审计规则；
4. 设计人工复核签署字段；
5. 设计从 candidate 到 registered manifest 的未来门槛，但不执行注册；
6. 复核是否需要补充 `frozen_at`、`freeze_reason`、`freeze_reviewer` 等字段，但不得在 KG-12 未授权时修改 candidate JSON。

KG-12 若涉及以下动作，必须重新取得更高等级的明确授权：

1. 修改 KG-08 candidate JSON；
2. 创建真实 validator 脚本；
3. 创建运行态 manifest；
4. 将 candidate 放入运行配置目录；
5. 注册 manifest；
6. 启用 retrieval / generation / evidence / scoring / writeback / export；
7. 接入 RAG、prompt registry 或 system instruction registry；
8. 复制、移动、删除或改写 AI 知识图谱原文件。

## 12. KG-11 最终结论

KG-11 结论如下：

1. KG-10 人工静态校验未发现 blocker、major 或 minor 问题；
2. KG-08 candidate JSON 当前仍为 `candidate_only`、`not_registered`、disabled 状态；
3. candidate 可冻结为非运行态、不可自动读取、不可注册、不可启用的 docs candidate；
4. freeze 后仍不得进入 RAG、prompt registry、system instruction registry、生成链、证据链、评分链或写回链；
5. system instruction 类内容继续隔离；
6. 青天评标 / 满分门控类内容继续不得作为 evidence 或 scoring basis；
7. KG-12 需要 ChatGPT 总控再次人工授权，不得自动进入。
