# KG-RUNTIME-115 corrected route-layer preview-only response re-smoke PASS frozen audit package and ZDoc preview-only integration readiness authorization gate

## 结论

KG-RUNTIME-115 仅冻结 KG-RUNTIME-114 corrected route-layer no-server in-process preview-only response integration re-smoke validation 的 PASS 成果，并设置后续 KG-RUNTIME-116 ZDoc preview-only integration readiness review / authorization gate。

KG-RUNTIME-115 不执行 ZDoc 接入，不进入真实使用阶段，不进入试用阶段，不执行 KG-RUNTIME-116。

## 基线

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- KG-RUNTIME-115 开始前 HEAD：`2c5b2a4862021b5c19175c4d41f7f7fd3f56c686`
- KG-RUNTIME-115 开始前基线 tag：`v0.1.497-zdoc-kg-corrected-route-layer-preview-only-response-resmoke-validation`
- 说明：KG-RUNTIME-114 本地 tag 写入曾被系统拒绝，远端 tag 已按 refspec 创建并指向该 HEAD；KG-RUNTIME-115 以 HEAD 与远端 tag 作为基线。

## KG-RUNTIME-114 PASS 冻结

KG-RUNTIME-114 已完成 corrected route-layer no-server in-process preview-only response integration re-smoke validation。

KG-RUNTIME-114 corrected re-smoke 结论为：PASS。

KG-RUNTIME-114 最终有效调用为 direct coroutine route 调用。该调用验证 route 返回 envelope `dict`，并确认 `root.preview_only_response` 存在。

KG-RUNTIME-114 使用 synthetic / content-safe response 形态。adapter 使用 synthetic stub。helper 构造 content-safe payload。route 返回 envelope dict。

已按 `root.preview_only_response` 或 unwrap 后对象断言，`preview_only_response` 包含：

- `preview_contract`
- `preview_only_mapping`
- `audit_only_mapping`
- `prohibited_mapping`

`preview_only_mapping` 仅包含允许字段：

- `structure_read_only`
- `structure_summary`
- `structural_profile_only`
- `structural_profile_summary`
- `structure_contract`
- `structural_profile_contract`

`audit_only_mapping` 仅包含允许字段：

- `feature_flag_status`
- `manual_trigger_status`
- `real_kg_read_only_status`
- `authorized_target_hit_status`
- `allowlist_status`
- `route_contract_code`
- `adapter_contract_code`
- `validation_result`
- `overlap_check_result`

`prohibited_mapping` 仅保留禁止类别清单，数量为 `12`。`prohibited_mapping` 未进入 `preview_only_mapping`。

`preview_only_mapping` 未包含 KG value / 正文 / evidence / scoring。

## KG-RUNTIME-114 未执行事项冻结

KG-RUNTIME-114 未执行以下事项：

- 未启动 `uvicorn`
- 未绑定 TCP 端口
- 未访问 `127.0.0.1`
- 未调用真实 endpoint
- 未调用 `/health`
- 未调用 `/kg/read-only-preview`
- 未读取真实 KG 文件正文
- 未解析真实 KG JSON
- 未触发生成 / 导出 / 写回
- 未触发 `/generate`
- 未触发 `/export_docx`
- 未触发 `/review/apply`
- 未触发 ZBid 写回
- 未写 output / job / export
- 未运行 Ollama
- 未接入 RAG / registry / CI
- 未作为 evidence
- 未作为 scoring

## 当前可认定

- route-layer no-server in-process preview-only response integration re-smoke 已通过。
- route envelope 下 `root.preview_only_response` 结构断言已通过。
- `preview_only` / `audit_only` / `prohibited` 映射边界在 synthetic content-safe 形态下通过验证。

## 当前不得认定

- 不得认定 ZDoc 已接入。
- 不得认定已进入真实使用。
- 不得认定已进入试用阶段。
- 不得认定模型已升级。
- 不得认定少数人可试用。
- 不得作为 evidence。
- 不得作为 scoring。

## 工具层备注

- `.venv/bin/python` 不存在，未进入解释器。
- 一次 `asyncio.run()` harness 在 route 前被本地 event-loop `socketpair` guard 中止。
- 该中止不作为 PASS 证据。
- 最终 PASS 证据来自 direct coroutine no-server in-process route 调用。

## KG-RUNTIME-115 docs-only 边界

KG-RUNTIME-115 仅新增本 docs-only 文件。

KG-RUNTIME-115 不修改 adapter / route / helper / `main.py`，不修改 frontend / tests / config / JSON，不再次执行目录扫描，不读取真实 KG 文件正文，不解析真实 KG JSON，不运行服务，不访问端口，不调用 endpoint，不运行 smoke，不运行 Ollama，不接入 RAG / registry / CI，不触发生成 / 导出 / 写回，不写 output / job / export。

KG-RUNTIME-115 只冻结 PASS 成果并设置下一阶段 readiness 授权门槛，不执行 ZDoc 接入。

## KG-RUNTIME-116 授权门槛草案

KG-RUNTIME-116 只有在后续单独授权后，才允许进行 ZDoc preview-only integration readiness review / authorization gate。

如后续单独授权，KG-RUNTIME-116 授权边界必须限定为：

- docs-only 或 readiness review
- 不修改代码
- 不运行服务
- 不访问 endpoint
- 不读取真实 KG
- 不解析真实 KG JSON
- 不再次执行目录扫描
- 不接入 frontend
- 不接入 `/generate`
- 不接入 `/export_docx`
- 不接入 `/review/apply`
- 不写 output / job / export
- 不运行 Ollama
- 不运行 `pytest` / `py_compile`
- 不接入 RAG / registry / CI
- 不进入真实使用或试用阶段
- 仅评估 ZDoc preview-only integration readiness 的范围、边界、依赖、风险、下一步最小接入条件

KG-RUNTIME-116 不得在 KG-RUNTIME-115 中执行。
