# KG-RUNTIME-30: ZDoc KG Controlled Adapter Contract Mapping Implementation Draft Review

## 1. 步骤名称

- Step: KG-RUNTIME-30.
- Name: ZDoc KG controlled adapter contract mapping implementation draft.
- Repository: `/Users/youfeini/Desktop/文档生成系统`.
- Branch: `main`.

## 2. 开始前状态

- Start HEAD: `1b1bcf7b3608e506e636bd06aa7a84c5acb55148`.
- Start tag: `v0.1.410-zdoc-kg-adapter-contract-mapping-implementation-gate`.
- Start `git status --short`: clean.

## 3. KG-RUNTIME-29 授权门槛摘要

KG-RUNTIME-29 仅授权 KG-RUNTIME-30 在后续明确指令下执行 controlled adapter contract mapping implementation draft。

KG-RUNTIME-29 要求 KG-RUNTIME-30 保持最小范围，仅允许修改 `backend/kg_read_only_preview_adapter.py`，实现静态 adapter contract mapping 草案，并新增完成后的 review 文档。

KG-RUNTIME-29 明确禁止 route、`main.py`、frontend、tests、config、真实 KG 路径连接、服务运行、端口访问、endpoint 访问、RAG、prompt registry、system instruction registry、generation、export、evidence、scoring、ZBid writeback、Ollama 或模型路径接入。

## 4. KG-RUNTIME-28 Adapter Contract Mapping 设计摘要

KG-RUNTIME-28 冻结的设计边界为结构契约映射设计，不授权真实 KG 使用。

KG-RUNTIME-28 设计要求 adapter 仅输出结构契约元数据，保留 default-off、manual-trigger、read-only、no-write、no-evidence、no-scoring、no-RAG、no-generation、no-export、no-ZBid-writeback、no-Ollama、no-model-upgrade 边界。

KG-RUNTIME-28 设计要求禁止输出真实业务正文值、实体正文、知识条目正文、prompt 内容、system instruction 内容、evidence 内容、scoring 内容、生成正文、可直接进入 `/generate` 的内容、可直接进入 RAG 的文本块、prompt registry 内容和 system instruction registry 内容。

## 5. 本步骤实际修改文件

- `backend/kg_read_only_preview_adapter.py`

## 6. 本步骤实际新增文件

- `docs/zdoc-kg-controlled-adapter-contract-mapping-implementation-draft-kg-runtime-30-review.md`

## 7. Adapter Contract Mapping Draft 实现范围

本步骤仅在 adapter 内部新增静态常量和纯函数输出收口：

- 输出字段白名单；
- allowed structural path policy；
- blocked structural path policy；
- value output policy；
- runtime boundary flags；
- adapter mapping status summary。

本步骤未接入真实 KG 文件路径，未读取真实 KG 文件，未解析真实 KG JSON，未注册 route，未修改 `main.py`，未接入服务启动、RAG、prompt registry、system instruction registry、generation、export、evidence、scoring 或 ZBid writeback。

## 8. 输出字段白名单说明

adapter 当前 contract mapping draft 输出收口到以下白名单字段：

- `ok`
- `enabled`
- `status`
- `reason`
- `source`
- `contract_scope`
- `module_contract_count`
- `adapter_structural_path_whitelist_count`
- `allowed_path_count`
- `blocked_path_count`
- `value_output_policy`
- `no_write`
- `no_evidence`
- `no_scoring`
- `no_rag`
- `no_generation`
- `no_export`
- `no_zbid_writeback`

白名单外字段不作为 adapter 输出返回。

## 9. 禁止输出内容说明

adapter 代码中通过 blocked structural path policy 和 value output policy 明确禁止输出：

- 实体正文；
- 知识条目正文；
- prompt 内容；
- system instruction 内容；
- evidence 内容；
- scoring 内容；
- 生成正文；
- 可直接进入 `/generate` 的内容；
- 可直接进入 RAG 的文本块；
- prompt registry 内容；
- system instruction registry 内容；
- 真实业务正文值。

## 10. no-write / no-evidence / no-scoring 约束说明

adapter contract mapping draft 输出中显式包含：

- `no_write=true`
- `no_evidence=true`
- `no_scoring=true`

该 draft 不写正文，不写 `output/job/export`，不生成 DOCX，不写 registry，不写知识包，不写 ZBid 数据，不产生 evidence，不作为 evidence，不产生 scoring，不作为 scoring。

## 11. no-RAG / no-generation / no-export / no-ZBid-writeback 约束说明

adapter contract mapping draft 输出中显式包含：

- `no_rag=true`
- `no_generation=true`
- `no_export=true`
- `no_zbid_writeback=true`

该 draft 不产生 RAG chunks，不产生 retrieval input，不连接 `/generate`，不产生 generation-ready text，不连接 `/export_docx`，不产生 export-ready content，不连接 `/review/apply`，不触发 ZBid 写回。

## 12. no-Ollama / no-model-upgrade 约束说明

adapter 内部 runtime boundary flags 显式包含：

- `no_ollama=true`
- `no_model_upgrade=true`

本步骤未运行 Ollama，未调用本地模型，未调用远程模型，未升级、拉取、删除、替换或配置任何模型。

## 13. Negative Execution Confirmation

- 是否读取真实 KG 文件正文内容：否。
- 是否打开 `知识图谱/ZF-KG-12-Municipal-Bridge.json` 内容：否。
- 是否解析真实 KG JSON：否。
- 是否运行 `python3 -m json.tool`：否。
- 是否运行 Python 脚本读取真实 KG JSON：否。
- 是否读取 `AI知识图谱大全` 内容：否。
- 是否复制、移动、删除 `AI知识图谱大全`：否。
- 是否加载真实知识包：否。
- 是否创建真实 registry：否。
- 是否注册、启用或加载知识包：否。
- 是否运行服务：否。
- 是否访问端口：否。
- 是否调用 `/health`：否。
- 是否调用 `/kg/read-only-preview`：否。
- 是否触发 `/generate`、`/export_docx`、`/review/apply`：否。
- 是否触发 ZBid 写回：否。
- 是否写正文：否。
- 是否写 `output/job/export`：否。
- 是否生成 DOCX：否。
- 是否运行 Ollama：否。
- 是否升级或拉取模型：否。
- 是否删除、替换或配置模型：否。
- 是否修改 JSON、tests、frontend、config：否。
- 是否修改 route / `main.py`：否。
- 是否接入 RAG / prompt registry / system instruction registry：否。
- 是否接入测试或 CI：否。
- 是否新增 `.pyc` / `__pycache__`：否。

## 14. Evidence and Scoring Boundary

adapter contract mapping draft 不得作为 evidence。

adapter contract mapping draft 不得作为 scoring。

本步骤没有将任何 mapping draft 结果接入 evidence、scoring、RAG、generation、export 或 ZBid writeback。

## 15. 下一阶段建议

KG-RUNTIME-31 如需推进，必须由后续单独明确授权。KG-RUNTIME-30 完成后停止，不自动进入 KG-RUNTIME-31。

## 16. Validation Results

- `git diff --check`: passed with exit code 0.
- `git diff --cached --check`: passed with exit code 0 after staging only the target adapter file and this target review document.

## 17. 最终边界结论

KG-RUNTIME-30 仅完成 controlled adapter contract mapping implementation draft。

本步骤只修改 `backend/kg_read_only_preview_adapter.py`，只新增目标 review 文档。

本步骤没有读取真实 KG 文件正文内容，没有解析真实 KG JSON，没有运行服务，没有访问端口，没有调用 endpoint，没有运行 Ollama，没有升级或拉取模型，没有修改 JSON、tests、frontend、config、route 或 `main.py`，没有接入 RAG、prompt registry、system instruction registry、测试或 CI，没有新增 `.pyc` 或 `__pycache__`。

本步骤未进入 KG-RUNTIME-31。
