# ZDoc KG-41 Disabled Entity Pair Offline Static Validator Draft Creation Review

## 1. KG-41 执行摘要

KG-41 在 ChatGPT 总控单独授权后，仅创建 disabled entity pair 的离线静态 validator 草案。本步骤不运行 validator，不执行 `py_compile`，不接入 CI，不接入 ZDoc 系统，不注册、不启用、不加载任何知识包。

本次仅新增两个 docs 非运行目录文件：

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `docs/kg-controlled-validators/zdoc_kg_disabled_entity_pair_static_validator_draft.py` | docs-only 草案 | 仅包含纯函数式字段校验草案，不带 shebang、CLI 入口、文件 IO 或运行链路接入 |
| `docs/zdoc-kg-disabled-entity-pair-offline-static-validator-draft-creation-kg41-review.md` | docs-only review | 记录 KG-41 创建物、边界和 KG-42 授权门槛 |

## 2. 创建内容说明

`zdoc_kg_disabled_entity_pair_static_validator_draft.py` 仅表达未来离线静态 validator 的字段检查形态。该文件要求调用方显式传入已经加载的 `manifest_entity`、`registry_entity` 字典和 docs 路径字符串；文件本身不自动读取 KG-08、KG-15、KG-31、KG-33，不写任何文件，也不连接服务、端口、Ollama 或 endpoint。

草案覆盖的静态检查思路仅限：

1. KG-31 manifest entity 是否 `enabled=false`；
2. KG-33 registry entity 是否 `enabled=false`；
3. `registration_status` 是否为 `not_registered`；
4. `runtime_loadable`、`registry_loadable`、`rag_loadable`、`prompt_registry_loadable`、`system_instruction_loadable` 是否为 false；
5. `evidence_allowed`、`scoring_allowed` 是否为 false；
6. KG-33 registry entity 对 KG-31 manifest entity 的引用关系是否一致；
7. KG-31 / KG-33 文件路径是否仍位于 `docs/kg-controlled-entities/` 非运行目录。

## 3. 为什么仍不是运行态工具

KG-41 validator 草案仍不是运行态工具，原因如下：

1. 文件位于 `docs/kg-controlled-validators/`，属于 docs 非运行目录；
2. 文件不带 shebang；
3. 文件不设置可执行权限；
4. 文件不包含 CLI 入口；
5. 文件没有 `if __name__ == "__main__"`；
6. 文件不自动读取 JSON；
7. 文件不写文件；
8. 文件不注册到 ZDoc；
9. 文件不接入 CI；
10. 文件不接入 RAG / prompt registry / system instruction registry；
11. 文件不调用服务、端口、Ollama 或 endpoint；
12. 文件不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。

## 4. 不得运行、不接入的原因

KG-41 的授权范围是“离线静态 validator 草案创建”，不是 validator 执行或系统集成。直接运行或接入会突破 KG-40 no-execution gate，也会把当前 disabled entity pair 从 docs-only 草案推进到实际校验链路或运行链路，超出本阶段授权。

因此 KG-41 明确：

| 行为 | KG-41 结论 |
| --- | --- |
| 运行新增 validator | 不允许 |
| `py_compile` 新增 validator | 不允许 |
| 接入 CI | 不允许 |
| 接入 ZDoc 运行链 | 不允许 |
| 修改 KG-31 / KG-33 JSON | 不允许 |
| 注册 manifest / registry | 不允许 |
| 启用 knowledge pack | 不允许 |
| 写 output/job/export | 不允许 |

## 5. KG-31 / KG-33 / KG-40 状态承接

| 对象 | 当前状态 | KG-41 承接 |
| --- | --- | --- |
| KG-31 disabled manifest entity | docs 非运行目录下的 disabled static entity，`registration_status=not_registered`，`enabled=false` | 不修改、不注册、不加载，仅作为未来草案函数的静态字段模型 |
| KG-33 disabled registry entity | docs 非运行目录下的 disabled static registry entity，`registration_status=not_registered`，`enabled=false` | 不修改、不注册、不加载，仅作为未来草案函数的静态字段模型 |
| KG-40 no-execution gate | 已明确 KG-41 即使获准也只能最小化、离线、静态，不得注册、启用或接入运行链路 | KG-41 仅新增草案文件与 review 文档，未运行 validator |

KG-08 manifest candidate 与 KG-15 registry candidate 继续保持候选、冻结、禁用、未注册状态；KG-41 不修改这两个 candidate JSON。

## 6. 边界复核

KG-41 保持以下边界：

1. 不修改代码 / tests / frontend / backend / config；
2. 不修改既有 docs；
3. 不修改 KG-08 manifest candidate JSON；
4. 不修改 KG-15 registry candidate JSON；
5. 不修改 KG-31 manifest entity JSON；
6. 不修改 KG-33 registry entity JSON；
7. 不复制、移动、删除 `AI知识图谱大全` 文件；
8. 不创建真实 registry；
9. 不注册、启用、加载任何知识包；
10. 不接入 RAG / prompt registry / system instruction registry；
11. 不运行服务 / Ollama / 端口 / endpoint；
12. 不生成 DOCX；
13. 不写 `output/job/export`；
14. 不进入 KG-42。

## 7. KG-42 授权门槛

KG-42 不得自动进入。若 ChatGPT 总控希望继续推进，必须单独授权，并应优先限定为以下任一低风险范围：

1. 对 KG-41 validator 草案做 docs-only 人工复核；
2. 设计 validator 草案的静态校验规则文档；
3. 审核草案是否仍满足 no-runtime / no-registration / no-integration。

KG-42 即使获准，也不得默认执行 validator，不得接入 CI，不得接入 ZDoc 系统，不得注册 manifest 或 registry，不得启用知识包，不得读取 `AI知识图谱大全` 原文。

## 8. KG-41 最终结论

KG-41 已创建 disabled entity pair offline static validator draft 与本 review 文档。新增 validator 草案仍为 docs 非运行目录下的静态草案，不具备自动执行、文件读取、文件写入、CI 接入或系统接入能力。

KG-41 未运行新增 validator，未执行 `py_compile`，未接入测试，未进入 KG-42。
