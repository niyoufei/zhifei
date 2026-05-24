# ZDoc KG Static Anchor Phase Master Archive Index KG-ARCHIVE-01

## 1. 执行摘要

KG-ARCHIVE-01 是 AI 知识图谱锚点静态阶段的 docs-only 阶段成果总索引。本文件只做归档索引，不修改任何 JSON，不修改 KG-41 validator 草案，不修改代码 / tests / frontend / backend / config，不修改既有 docs。

当前阶段结论：

1. AI 知识图谱锚点静态阶段已阶段性完成；
2. KG-08 manifest candidate、KG-15 registry candidate、KG-31 disabled manifest entity、KG-33 disabled registry entity、KG-41 validator draft 已完成受控静态归档；
3. 当前仍不进入 KG-48；
4. 当前不授权真实注册、真实启用、真实加载或真实系统接入；
5. 当前不授权运行 validator、不授权 `py_compile`、不授权接入测试或 CI；
6. 后续如需继续，必须由 ChatGPT 总控单独授权并重新设定目标、边界和回退要求。

## 2. 当前基线

| 项目 | 值 |
| --- | --- |
| 仓库 | `/Users/youfeini/Desktop/文档生成系统` |
| 分支 | `main` |
| KG-ARCHIVE-01 开始前 HEAD | `51c354f17c4d44fa9969735f749e60d4669a69c8` |
| KG-ARCHIVE-01 开始前 tag | `v0.1.379-zdoc-kg-final-no-execution-static-archive-closeout` |
| 当前阶段 | AI 知识图谱锚点静态阶段完成归档 |
| 当前运行状态 | no-runtime / no-registration / no-integration |
| 当前下一阶段 | 不进入 KG-48，等待 ChatGPT 单独授权 |

## 3. KG-01 至 KG-47 阶段成果索引

| 阶段 | 阶段目标 | 关键文件 / 输出 | commit | tag |
| --- | --- | --- | --- | --- |
| KG-01 | `AI知识图谱大全` 只读盘点与 ZDoc 适配性分析 | ChatGPT 回报；无仓库文件 | 无仓库提交 | 无 |
| KG-02 | 分类治理、风险分级与 manifest 草案分析 | ChatGPT 回报；无仓库文件 | 无仓库提交 | 无 |
| KG-02R | 分类治理复核与 manifest 草案校正 | ChatGPT 回报；无仓库文件 | 无仓库提交 | 无 |
| KG-03 | ZDoc 知识锚点架构与 manifest schema 设计 | `docs/zdoc-kg-anchor-architecture-and-manifest-schema-design.md` | `e0f8e05` | `v0.1.334-zdoc-kg-anchor-architecture-design` |
| KG-03R | 纳入 KG-02R 修正并确认 KG-04 readiness | `docs/zdoc-kg-anchor-architecture-kg02r-correction-and-kg04-readiness.md` | `b91b587` | `v0.1.335-zdoc-kg-architecture-kg02r-correction` |
| KG-04 | controlled knowledge pack pilot manifest draft 与 KG-05 授权请求 | `docs/zdoc-kg-controlled-knowledge-pack-pilot-manifest-draft-and-authorization-request.md` | `fbc2aff` | `v0.1.336-zdoc-kg-controlled-pilot-manifest-draft` |
| KG-05 | disabled entity 字段设计与 KG-06 授权条件 | `docs/zdoc-kg-controlled-pilot-manifest-disabled-entity-design-kg05.md` | `e5ee995` | `v0.1.337-zdoc-kg-controlled-pilot-disabled-entity-design` |
| KG-06 | pre-entity review 与 authorization gate | `docs/zdoc-kg-controlled-pilot-pre-entity-review-and-authorization-gate-kg06.md` | `2071db4` | `v0.1.338-zdoc-kg-controlled-pilot-pre-entity-review` |
| KG-07 | inert manifest entity scaffold 设计 | `docs/zdoc-kg-controlled-pilot-inert-manifest-entity-scaffold-kg07.md` | `829b21e` | `v0.1.339-zdoc-kg-controlled-pilot-inert-manifest-scaffold` |
| KG-08 | disabled manifest candidate entity 创建 | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json`；`docs/zdoc-kg-controlled-pilot-disabled-manifest-candidate-kg08-review.md` | `2f031a0` | `v0.1.340-zdoc-kg-controlled-pilot-disabled-manifest-candidate` |
| KG-09 | manifest candidate 静态校验规则设计 | `docs/zdoc-kg-controlled-pilot-manifest-candidate-static-validation-rules-kg09.md` | `012627d` | `v0.1.341-zdoc-kg-manifest-candidate-static-validation-rules` |
| KG-10 | manifest candidate 人工静态校验报告 | `docs/zdoc-kg-controlled-pilot-manifest-candidate-manual-static-validation-report-kg10.md` | `b977a13` | `v0.1.342-zdoc-kg-manifest-candidate-manual-validation-report` |
| KG-11 | manifest candidate validation disposition and freeze gate | `docs/zdoc-kg-controlled-pilot-manifest-candidate-validation-disposition-and-freeze-gate-kg11.md` | `a5c95d7` | `v0.1.343-zdoc-kg-manifest-candidate-validation-disposition-gate` |
| KG-12 | manifest candidate freeze record and next gate | `docs/zdoc-kg-controlled-pilot-manifest-candidate-freeze-record-and-next-gate-kg12.md` | `2d119b8` | `v0.1.344-zdoc-kg-manifest-candidate-freeze-record` |
| KG-13 | frozen manifest candidate registry isolation and pre-registration gate | `docs/zdoc-kg-frozen-manifest-candidate-registry-isolation-and-pre-registration-gate-kg13.md` | `1cedfa1` | `v0.1.345-zdoc-kg-frozen-candidate-registry-isolation-gate` |
| KG-14 | registry candidate schema and disabled pre-registration draft design | `docs/zdoc-kg-frozen-candidate-registry-candidate-schema-and-disabled-pre-registration-draft-kg14.md` | `a41355a` | `v0.1.346-zdoc-kg-frozen-candidate-registry-schema-draft` |
| KG-15 | disabled registry candidate entity 创建 | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json`；`docs/zdoc-kg-disabled-registry-candidate-entity-creation-kg15-review.md` | `4e6f8d8` | `v0.1.347-zdoc-kg-disabled-registry-candidate-entity` |
| KG-16 | registry candidate 静态校验规则设计 | `docs/zdoc-kg-disabled-registry-candidate-static-validation-rules-kg16.md` | `34eed67` | `v0.1.348-zdoc-kg-registry-candidate-static-validation-rules` |
| KG-17 | registry candidate 人工静态校验报告 | `docs/zdoc-kg-disabled-registry-candidate-manual-static-validation-report-kg17.md` | `c2ef28f` | `v0.1.349-zdoc-kg-registry-candidate-manual-validation-report` |
| KG-18 | registry candidate validation disposition and freeze gate | `docs/zdoc-kg-disabled-registry-candidate-validation-disposition-and-freeze-gate-kg18.md` | `f0981fe` | `v0.1.350-zdoc-kg-registry-candidate-validation-disposition-gate` |
| KG-19 | registry candidate freeze record and next gate | `docs/zdoc-kg-disabled-registry-candidate-freeze-record-and-next-gate-kg19.md` | `ae995b5` | `v0.1.351-zdoc-kg-registry-candidate-freeze-record` |
| KG-20 | frozen registry candidate pre-registration readiness review | `docs/zdoc-kg-frozen-registry-candidate-pre-registration-readiness-and-authorization-gate-kg20.md` | `93ae48f` | `v0.1.352-zdoc-kg-frozen-registry-candidate-readiness-gate` |
| KG-21 | pre-registration authorization disposition and no-registration boundary | `docs/zdoc-kg-frozen-registry-candidate-pre-registration-authorization-disposition-kg21.md` | `2724402` | `v0.1.353-zdoc-kg-registry-candidate-authorization-disposition` |
| KG-22 | pre-registration packet and controlled handoff index | `docs/zdoc-kg-frozen-registry-candidate-pre-registration-packet-and-handoff-index-kg22.md` | `7d33a7d` | `v0.1.354-zdoc-kg-registry-candidate-pre-registration-packet` |
| KG-23 | pre-registration packet completeness and manual acceptance review | `docs/zdoc-kg-pre-registration-packet-completeness-and-manual-acceptance-review-kg23.md` | `8e26ae5` | `v0.1.355-zdoc-kg-pre-registration-packet-acceptance-review` |
| KG-24 | final acceptance disposition and phase closeout gate | `docs/zdoc-kg-pre-registration-packet-final-acceptance-disposition-and-phase-closeout-kg24.md` | `a033025` | `v0.1.356-zdoc-kg-pre-registration-packet-phase-closeout` |
| KG-25 | pre-entity implementation plan and authorization gate | `docs/zdoc-kg-pre-entity-implementation-plan-and-authorization-gate-kg25.md` | `58e5cc5` | `v0.1.357-zdoc-kg-pre-entity-implementation-plan` |
| KG-26 | pre-entity implementation completeness and no-execution review | `docs/zdoc-kg-pre-entity-implementation-plan-completeness-and-no-execution-review-kg26.md` | `6d5c9fd` | `v0.1.358-zdoc-kg-pre-entity-no-execution-review` |
| KG-27 | final authorization disposition and execution package freeze gate | `docs/zdoc-kg-pre-entity-implementation-final-authorization-disposition-and-execution-package-freeze-gate-kg27.md` | `95cd9dd` | `v0.1.359-zdoc-kg-pre-entity-final-authorization-gate` |
| KG-28 | execution package frozen index and manual readiness checklist | `docs/zdoc-kg-pre-entity-execution-package-frozen-index-and-manual-readiness-checklist-kg28.md` | `a46e5a5` | `v0.1.360-zdoc-kg-pre-entity-execution-package-index` |
| KG-29 | final acceptance and entity-action authorization request | `docs/zdoc-kg-pre-entity-execution-package-final-acceptance-and-entity-action-authorization-request-kg29.md` | `925b6b6` | `v0.1.361-zdoc-kg-pre-entity-final-acceptance-request` |
| KG-30 | entity-action authorization disposition and controlled execution package freeze | `docs/zdoc-kg-entity-action-authorization-disposition-and-controlled-execution-package-freeze-kg30.md` | `8add458` | `v0.1.362-zdoc-kg-entity-action-authorization-freeze` |
| KG-31 | first controlled inert manifest entity creation | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json`；`docs/zdoc-kg-first-controlled-inert-manifest-entity-creation-kg31-review.md` | `e2a1ba4` | `v0.1.363-zdoc-kg-first-controlled-inert-manifest-entity` |
| KG-32 | disabled manifest entity static compliance and no-runtime review | `docs/zdoc-kg-disabled-manifest-entity-static-compliance-and-no-runtime-review-kg32.md` | `1c810c3` | `v0.1.364-zdoc-kg-disabled-manifest-entity-static-review` |
| KG-33 | first controlled inert registry entity creation | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json`；`docs/zdoc-kg-first-controlled-inert-registry-entity-creation-kg33-review.md` | `65d3b2f` | `v0.1.365-zdoc-kg-first-controlled-inert-registry-entity` |
| KG-34 | disabled registry entity static compliance and no-runtime review | `docs/zdoc-kg-disabled-registry-entity-static-compliance-and-no-runtime-review-kg34.md` | `48f984e` | `v0.1.366-zdoc-kg-disabled-registry-entity-static-review` |
| KG-35 | manifest-registry entity pair static consistency and no-runtime review | `docs/zdoc-kg-disabled-manifest-registry-entity-pair-static-consistency-and-no-runtime-review-kg35.md` | `b168576` | `v0.1.367-zdoc-kg-disabled-entity-pair-static-consistency-review` |
| KG-36 | disabled entity pair frozen audit package and manual authorization gate | `docs/zdoc-kg-disabled-entity-pair-frozen-audit-package-and-manual-authorization-gate-kg36.md` | `8ef7771` | `v0.1.368-zdoc-kg-disabled-entity-pair-frozen-audit-package` |
| KG-37 | final manual authorization request and static archive closeout | `docs/zdoc-kg-disabled-entity-pair-final-manual-authorization-request-and-static-archive-closeout-kg37.md` | `86e9ff9` | `v0.1.369-zdoc-kg-disabled-entity-pair-final-authorization-request` |
| KG-38 | final authorization disposition and next-stage freeze gate | `docs/zdoc-kg-disabled-entity-pair-final-authorization-disposition-and-next-stage-freeze-gate-kg38.md` | `d940c85` | `v0.1.370-zdoc-kg-disabled-entity-pair-authorization-disposition` |
| KG-39 | validator design note and manual verification checklist | `docs/zdoc-kg-disabled-entity-pair-validator-design-note-and-manual-verification-checklist-kg39.md` | `778c8b0` | `v0.1.371-zdoc-kg-disabled-entity-pair-validator-design` |
| KG-40 | validator implementation authorization request and no-execution gate | `docs/zdoc-kg-disabled-entity-pair-validator-implementation-authorization-request-and-no-execution-gate-kg40.md` | `2d9209d` | `v0.1.372-zdoc-kg-validator-implementation-authorization-request` |
| KG-41 | offline static validator draft creation | `docs/kg-controlled-validators/zdoc_kg_disabled_entity_pair_static_validator_draft.py`；`docs/zdoc-kg-disabled-entity-pair-offline-static-validator-draft-creation-kg41-review.md` | `2e2ba46` | `v0.1.373-zdoc-kg-disabled-entity-pair-validator-draft` |
| KG-42 | validator draft static compliance and no-execution review | `docs/zdoc-kg-disabled-entity-pair-validator-draft-static-compliance-and-no-execution-review-kg42.md` | `aafe280` | `v0.1.374-zdoc-kg-validator-draft-static-compliance-review` |
| KG-43 | validator draft frozen audit package and manual authorization gate | `docs/zdoc-kg-disabled-entity-pair-validator-draft-frozen-audit-package-and-manual-authorization-gate-kg43.md` | `0585cb2` | `v0.1.375-zdoc-kg-validator-draft-frozen-audit-package` |
| KG-44 | validator draft final authorization request and static archive closeout | `docs/zdoc-kg-disabled-entity-pair-validator-draft-final-authorization-request-and-static-archive-closeout-kg44.md` | `27602cd` | `v0.1.376-zdoc-kg-validator-draft-final-authorization-request` |
| KG-45 | validator draft authorization disposition and next-stage freeze gate | `docs/zdoc-kg-disabled-entity-pair-validator-draft-final-authorization-disposition-and-next-stage-freeze-gate-kg45.md` | `79512ef` | `v0.1.377-zdoc-kg-validator-draft-authorization-disposition` |
| KG-46 | validator draft static archive index and manual review checklist | `docs/zdoc-kg-disabled-entity-pair-validator-draft-static-archive-index-and-manual-review-checklist-kg46.md` | `63ecb57` | `v0.1.378-zdoc-kg-validator-draft-static-archive-index` |
| KG-47 | final no-execution closeout and static phase archive | `docs/zdoc-kg-disabled-entity-pair-validator-draft-final-no-execution-closeout-and-static-phase-archive-kg47.md` | `51c354f` | `v0.1.379-zdoc-kg-final-no-execution-static-archive-closeout` |

## 4. 核心文件状态索引

| 阶段 | 核心文件 | git mode / blob | 当前状态 | 运行结论 |
| --- | --- | --- | --- | --- |
| KG-08 | `docs/kg-manifest-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.candidate.json` | `100644` / `41502c9e34d6297a538fd023f729df02e25ff7dd` | `candidate_only` / `not_registered` / disabled | 不作为运行输入 |
| KG-15 | `docs/kg-registry-candidates/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.candidate.json` | `100644` / `0439a0f1a607dbe79f1cf12d15b7f1b5e3f3c526` | `registry_candidate_only` / `not_registered` / disabled | 不是真实 registry |
| KG-31 | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json` | `100644` / `0f488c2a04dd29129e5d0eefd80fd30494bcdb6e` | `disabled_entity_only` / `not_registered` / disabled | 不加载、不启用 |
| KG-33 | `docs/kg-controlled-entities/zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json` | `100644` / `7ee5cc8d93dc2b53a48977c9555a4a51f65b53bc` | `disabled_registry_entity_only` / `not_registered` / disabled | 不注册、不加载 |
| KG-41 | `docs/kg-controlled-validators/zdoc_kg_disabled_entity_pair_static_validator_draft.py` | `100644` / `51739f3055f1a4b4853ce7c728890653c3037c27` | `static_draft_only` / not executed / not compiled | 不运行、不 `py_compile`、不接入测试或 CI |

## 5. 当前冻结边界

KG-ARCHIVE-01 继续冻结以下边界：

1. 不得修改任何 JSON；
2. 不得修改 KG-41 validator 草案；
3. 不得修改代码 / tests / frontend / backend / config；
4. 不得修改既有 docs；
5. 不得复制、移动、删除 `AI知识图谱大全` 文件；
6. 不得创建真实 registry；
7. 不得注册、启用、加载知识包；
8. 不得接入 RAG / prompt registry / system instruction registry；
9. 不得运行 validator；
10. 不得 `py_compile`；
11. 不得接入测试或 CI；
12. 不得运行服务 / Ollama / 端口 / endpoint；
13. 不得触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回；
14. 不得生成 DOCX；
15. 不得写 `output/job/export`；
16. 不得进入真实使用阶段、模型升级或 50 人正式部署。

## 6. 当前阶段结论

AI 知识图谱锚点静态阶段已完成阶段性归档。该阶段完成的是候选、设计、禁用实体、静态复核、冻结审计、validator 草案和最终 no-execution 收口，不是运行态接入。

当前仍不进入 KG-48。后续如需继续，必须由 ChatGPT 总控单独授权，并重新说明：

1. 新阶段目标；
2. 允许新增或修改的文件；
3. 是否仍为 docs-only；
4. 是否允许运行 validator 或 `py_compile`；
5. 是否允许接入测试或 CI；
6. 是否允许真实注册、启用、加载或接入系统；
7. 是否仍禁止 RAG / prompt registry / system instruction registry；
8. 是否仍禁止 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回、DOCX 和 `output/job/export`。

在新的单独授权前，本阶段保持静态归档状态。
