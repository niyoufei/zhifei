# ZDoc KG-40 Disabled Entity Pair Validator Implementation Authorization Request and No-Execution Gate

## 1. KG-40 执行摘要

KG-40 是 disabled entity pair validator implementation authorization request 与 no-execution gate 文档。本步骤仍为 docs-only，不创建 validator 脚本，不运行校验，不接入 CI，不接入系统，不修改 KG-31 manifest entity JSON，不修改 KG-33 registry entity JSON，不修改 KG-08 manifest candidate JSON，不修改 KG-15 registry candidate JSON。

KG-40 结论：KG-39 已完成 validator 设计说明与人工校验清单，但 KG-40 不执行实现。若后续进入 KG-41，必须由 ChatGPT 总控单独授权；即使获准，也应优先限制为最小化离线静态 validator 草案，不得注册、启用或接入运行链路。

## 2. KG-39 结论承接

KG-39 已形成以下设计结论：

| KG-39 内容 | 承接结论 |
| --- | --- |
| validator 目标 | 仅检查 disabled manifest entity 与 disabled registry entity 的静态字段、引用关系、禁用状态 |
| validator 输入 | 仅限 docs 下 KG-08、KG-15、KG-31、KG-33 静态文件路径 |
| validator 输出 | 静态报告，不得写运行目录，不得生成 DOCX，不得更新实体 JSON |
| 静态检查项 | 覆盖 `enabled=false`、`not_registered`、`runtime_loadable=false`、`evidence_allowed=false`、`scoring_allowed=false` 等 |
| pair 引用关系 | 检查 KG-31 来源 KG-08、KG-33 来源 KG-15、KG-33 指向 KG-31 |
| manual verification checklist | 覆盖禁用字段、候选来源、docs 非运行目录、不可加载状态 |
| KG-40 边界 | 只能做 implementation authorization request 或进一步 docs-only 审查 |

KG-40 承接 KG-39，但不把 KG-39 的设计说明转化为可执行脚本。

## 3. Validator 后续实施的限定目标

如后续单独授权进入 KG-41，validator 的目标必须被限定为离线静态检查：

1. 校验 KG-31 disabled manifest entity 的静态字段；
2. 校验 KG-33 disabled registry entity 的静态字段；
3. 校验 KG-31 / KG-33 的 pair 引用关系；
4. 校验 KG-08 / KG-15 候选来源路径；
5. 校验所有禁用字段继续为 false；
6. 校验 `registration_status=not_registered`；
7. 校验 `source_mode=path_and_summary_only`；
8. 校验 docs 非运行目录位置；
9. 校验未复制、未嵌入 `AI知识图谱大全` 原文；
10. 输出静态校验结果，不产生运行副作用。

不允许 validator 目标扩展为：

1. 注册 manifest；
2. 注册 registry；
3. 启用 knowledge pack；
4. 加载 RAG；
5. 加载 prompt registry；
6. 加载 system instruction registry；
7. 生成 evidence；
8. 生成 scoring basis；
9. 写回 ZBid；
10. 触发导出或 DOCX 生成。

## 4. Validator 后续输入限定

若 KG-41 获得单独授权，最小化离线静态 validator 草案只允许读取以下 docs 文件：

| 输入 | 路径 | 用途 |
| --- | --- | --- |
| KG-08 manifest candidate | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | 来源候选状态校验 |
| KG-15 registry candidate | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | registry 候选状态校验 |
| KG-31 manifest entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | manifest entity 静态字段校验 |
| KG-33 registry entity | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | registry entity 静态字段校验 |

禁止读取或扫描：

1. `AI知识图谱大全` 原文；
2. backend / frontend / config；
3. job / output / export；
4. 服务端口或 endpoint；
5. RAG index；
6. prompt registry；
7. system instruction registry；
8. ZBid 写回目标。

## 5. Validator 后续输出限定

若 KG-41 获得单独授权，输出应限定为静态校验报告。不得修改输入文件，不得写运行目录。

建议输出内容：

| 输出项 | 说明 |
| --- | --- |
| `validation_status` | `pass` / `fail` / `manual_review_required` |
| `checked_files` | 被检查 docs 文件路径 |
| `failed_checks` | 失败项 |
| `manual_review_required` | 是否需要人工复核 |
| `blocked_runtime_actions` | 确认仍阻断的运行行为 |
| `review_notes` | 人工审查备注 |

禁止输出：

1. 修改后的 KG-08 / KG-15 / KG-31 / KG-33；
2. 真实 registry；
3. 运行配置；
4. RAG 索引；
5. prompt registry 条目；
6. system instruction 条目；
7. evidence；
8. scoring basis；
9. DOCX；
10. output/job/export 产物。

## 6. No-Execution Gate

KG-40 明确执行以下 no-execution gate：

| 项目 | KG-40 状态 |
| --- | --- |
| 创建 validator 脚本 | 不执行 |
| 运行校验 | 不执行 |
| 接入 CI | 不执行 |
| 接入系统 | 不执行 |
| 修改 KG-31 manifest entity JSON | 不执行 |
| 修改 KG-33 registry entity JSON | 不执行 |
| 修改 KG-08 manifest candidate JSON | 不执行 |
| 修改 KG-15 registry candidate JSON | 不执行 |
| 创建真实 registry | 不执行 |
| 注册 manifest | 不执行 |
| 注册 registry | 不执行 |
| 启用 knowledge pack | 不执行 |
| 接入 RAG / prompt registry / system instruction registry | 不执行 |
| 运行服务 / Ollama / 端口 / endpoint | 不执行 |
| 触发生成、导出、review apply 或 ZBid 写回 | 不执行 |
| 生成 DOCX | 不执行 |
| 写 output/job/export | 不执行 |

## 7. KG-41 授权请求草案

如 ChatGPT 总控希望继续进入 KG-41，建议授权文本限定为：

> 允许执行 KG-41：创建最小化离线静态 validator 草案。仅允许新增一个 docs 或 tools 下明确隔离的非运行脚本草案及一份 review 文档；validator 只能读取 KG-08、KG-15、KG-31、KG-33 docs 路径，输出静态校验报告；不得注册、不得启用、不得加载、不得接入 RAG / prompt registry / system instruction registry、不得运行服务、不得触发生成/导出/review apply/ZBid 写回。

KG-41 即使获准，也必须继续满足：

1. 最小化；
2. 离线；
3. 静态；
4. 默认不运行；
5. 不接入 CI；
6. 不接入系统；
7. 不修改实体 JSON；
8. 不读取 `AI知识图谱大全` 原文；
9. 不创建真实 registry；
10. 不注册、启用或加载知识包。

## 8. KG-41 禁止项冻结

KG-41 不得自动进入。若获单独授权，仍不得：

1. 注册 manifest；
2. 注册 registry；
3. 启用 knowledge pack；
4. 接入 RAG；
5. 接入 prompt registry；
6. 接入 system instruction registry；
7. 生成 evidence；
8. 生成 scoring basis；
9. 写回 ZBid；
10. 触发 `/generate`、`/export_docx`、`/review/apply`；
11. 运行 ZDoc 服务、ZBid 服务、Ollama、端口或 endpoint；
12. 生成 DOCX；
13. 写入 `output/job/export`；
14. 复制、移动、删除或改写 `AI知识图谱大全` 文件。

## 9. 人工审核要求

进入 KG-41 前，ChatGPT 总控应人工确认：

1. KG-39 设计说明是否足够清晰；
2. KG-40 是否仍未创建 validator 脚本；
3. KG-08 / KG-15 / KG-31 / KG-33 是否仍为 disabled / not_registered；
4. validator 是否确有必要进入实现草案；
5. KG-41 输出文件范围是否明确；
6. KG-41 是否仍保持 no-runtime、no-registration、no-integration；
7. 是否需要继续停留在 docs-only 审查，而不是进入脚本草案。

## 10. KG-40 最终结论

KG-40 最终结论：

1. 已汇总 KG-39 validator design note 与 manual verification checklist 结论；
2. 已明确 validator 后续若实施，仅能校验 disabled manifest entity 与 disabled registry entity 的静态字段、引用关系、禁用状态；
3. KG-40 不创建 validator 脚本；
4. KG-40 不运行校验；
5. KG-40 不接入 CI；
6. KG-40 不接入系统；
7. KG-41 如需继续，必须由 ChatGPT 单独授权；
8. KG-41 即使获准，也应优先限制为最小化离线静态 validator 草案；
9. KG-41 不得注册、启用或接入运行链路；
10. KG-40 不进入 KG-41，不执行任何真实创建、注册、接入、启用、校验器运行或运行动作。
