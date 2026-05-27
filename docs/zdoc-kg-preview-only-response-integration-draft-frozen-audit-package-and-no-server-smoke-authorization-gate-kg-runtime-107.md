# KG-RUNTIME-107 ZDoc KG Preview-Only Response Integration Draft Frozen Audit Package And No-Server Smoke Authorization Gate

## 1. 阶段边界

- 阶段：KG-RUNTIME-107。
- 目标：仅冻结 KG-RUNTIME-105 / KG-RUNTIME-106 的 `preview_only_response` integration 草案成果，并设置 KG-RUNTIME-108 是否允许执行 no-server preview-only response integration smoke validation 的授权门槛。
- 本阶段仅新增本 docs-only 文件。
- 本阶段不修改 adapter / route / helper / `main.py`。
- 本阶段不修改 frontend / tests / config / JSON。
- 本阶段不运行 smoke。
- 本阶段不读取真实 KG 文件正文。
- 本阶段不解析真实 KG JSON。
- 本阶段不运行服务，不访问端口，不调用 endpoint。
- 本阶段不触发生成、导出、写回。
- 本阶段不写 output/job/export。
- 本阶段不运行 Ollama。
- 本阶段不接入 RAG / registry / CI。
- 本阶段不进入 KG-RUNTIME-108。

## 2. 已冻结的上游阶段成果

- KG-RUNTIME-105 已完成 `preview_only_response` integration controlled implementation draft。
- KG-RUNTIME-106 已完成 `preview_only_response` integration draft static compliance and no-output-chain review。
- 当前 `preview_only_response` integration 仍为草案，不代表 ZDoc 已接入。
- 当前草案只允许作为 frozen audit package 与后续 no-server smoke 授权门槛依据，不代表真实使用、试用或模型升级。

## 3. 当前草案字段

当前 `preview_only_response` integration 草案字段包括：

- `preview_only_response`
- `preview_contract`
- `preview_only_mapping`
- `audit_only_mapping`
- `prohibited_mapping`

字段边界：

- `preview_only_response` 为 route 透传的草案顶层字段。
- `preview_contract` 仅描述草案 contract 元信息。
- `preview_only_mapping` 仅承载允许进入 preview-only 的 content-safe 字段映射。
- `audit_only_mapping` 仅承载允许进入 audit-only 的门禁、contract、validation、overlap code。
- `prohibited_mapping` 仅承载禁止类别清单。

## 4. 当前草案复用链路

当前草案复用以下 helper / adapter 链路：

- `classify_content_safe_fields`
- `filter_preview_only_fields`
- `filter_audit_only_fields`
- `build_preview_only_payload`
- `build_preview_only_adapter_mapping`

复用结论：

- `preview_only_mapping` 继续来自 content-safe preview-only filter 链路。
- `audit_only_mapping` 继续来自 content-safe audit-only filter 链路。
- `prohibited_mapping` 继续作为禁止类别清单参与隔离检查。
- adapter 继续基于既有 mapping helper 形成 overlap check 输入。

## 5. Route 透传边界

- route 仅透传 `preview_only_response` 草案字段。
- route 未新增生成、导出、写回、evidence、scoring、RAG、prompt registry 或 system instruction registry 链路。
- route 未新增 frontend 接入、真实使用入口或试用入口。
- route 透传不代表 ZDoc 已接入。

## 6. 已确认的静态合规结论

- `preview_only` 仍仅包含允许字段。
- `audit_only` 仍仅包含允许字段。
- `prohibited` 仍仅为禁止类别清单。
- `prohibited` 未进入 `preview_only`。
- `preview_only` 未包含 KG value / 正文 / evidence / scoring。
- 未接入 `/generate`。
- 未接入 `/export_docx`。
- 未接入 `/review/apply`。
- 未写 output/job/export。
- 未触发 ZBid 写回。
- 未作为 evidence。
- 未作为 scoring。
- 未接入 RAG / prompt registry / system instruction registry。

## 7. 当前不得认定事项

当前不得认定：

- ZDoc 已接入。
- 已进入真实使用。
- 已进入试用阶段。
- 模型已升级。
- 少数人可试用。

上述事项均不由 KG-RUNTIME-105、KG-RUNTIME-106 或 KG-RUNTIME-107 授权。

## 8. KG-RUNTIME-108 授权前置条件

KG-RUNTIME-108 如后续单独授权，才允许执行 no-server preview-only response integration smoke validation。

KG-RUNTIME-107 只设置 no-server integration smoke 授权门槛，不执行 smoke。

## 9. KG-RUNTIME-108 授权边界草案

如后续单独进入 KG-RUNTIME-108，授权边界必须限定为：

- 不启动 uvicorn。
- 不绑定 TCP 端口。
- 不访问 `127.0.0.1`。
- 优先使用直接 adapter / helper in-process 调用。
- 如必须验证 route 透传，可使用直接 route in-process 调用。
- 使用 synthetic / 已验证 content-safe response 形态。
- 不读取真实 KG。
- 不解析真实 KG JSON。
- 不再次执行目录扫描。
- 仅验证 `preview_only_response` / `preview_contract` / `preview_only_mapping` / `audit_only_mapping` / `prohibited_mapping` 是否正确。
- 必须验证 `prohibited` 未进入 `preview_only`。
- 必须验证 `preview_only` 不含 KG value、正文、evidence、scoring。
- 禁止触发生成、导出、写回。
- 禁止写 output/job/export。
- 禁止运行 Ollama。
- 禁止 pytest / py_compile。
- 禁止接入 RAG / registry / CI。
- 禁止进入 ZDoc 接入、真实使用或试用阶段。

## 10. KG-RUNTIME-107 最终结论

KG-RUNTIME-107 完成的事项仅为：

- 冻结 KG-RUNTIME-105 `preview_only_response` integration controlled implementation draft 成果。
- 冻结 KG-RUNTIME-106 `preview_only_response` integration draft static compliance and no-output-chain review 成果。
- 设置 KG-RUNTIME-108 no-server preview-only response integration smoke validation 的未来授权门槛。

KG-RUNTIME-107 未执行 no-server smoke，未进入 KG-RUNTIME-108，未进入 ZDoc 接入 / 真实使用 / 试用阶段。
