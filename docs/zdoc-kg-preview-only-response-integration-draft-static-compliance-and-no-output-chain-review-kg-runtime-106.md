# KG-RUNTIME-106 ZDoc KG Preview-Only Response Integration Draft Static Compliance And No-Output-Chain Review

## 1. 审查边界

- 阶段：KG-RUNTIME-106。
- 审查对象：KG-RUNTIME-105 `preview_only_response` integration controlled implementation draft。
- 审查方式：静态审查，只读查看授权文件和 KG-RUNTIME-105 提交面。
- 本阶段仅新增本 docs-only review 文件。
- 本阶段不运行服务，不访问端口，不调用 endpoint，不运行 pytest，不运行 py_compile。
- 本阶段不读取真实 KG 文件正文，不解析真实 KG JSON，不再次执行目录扫描。
- 本阶段不触发生成、导出、写回、evidence、scoring、RAG、registry、CI。

## 2. 基线与只读证据

- 开始前分支：`main`。
- 开始前 HEAD：`0ad99ceea3f352a7ba0959e1e7d545b83004db95`。
- KG-RUNTIME-105 基线 tag：`v0.1.488-zdoc-kg-preview-only-response-integration-draft`。
- 本地 tag refs 未发现该 tag；远端 tag 查询因当前沙箱网络权限拒绝，未请求完全访问权限。
- `git show --name-only --format=oneline --no-renames HEAD` 显示 KG-RUNTIME-105 仅涉及：
  - `backend/app/routers/kg_read_only_preview.py`
  - `backend/kg_content_safe_output_contract.py`
  - `backend/kg_read_only_preview_adapter.py`
  - `docs/zdoc-kg-preview-only-response-integration-controlled-implementation-draft-kg-runtime-105-review.md`

## 3. 授权范围静态结论

- 是否仅修改 KG-RUNTIME-105 授权范围内 adapter / route / helper 文件：是。代码文件仅为 `backend/kg_content_safe_output_contract.py`、`backend/kg_read_only_preview_adapter.py`、`backend/app/routers/kg_read_only_preview.py`。
- 是否未修改 `main.py`：是。KG-RUNTIME-105 文件清单未包含 `backend/app/main.py` 或其他 `main.py`。
- 是否未修改 frontend / tests / config / JSON：是。KG-RUNTIME-105 文件清单未包含 frontend、tests、config 或 JSON 文件。
- 是否仅新增 KG-RUNTIME-105 review 文档：是。KG-RUNTIME-105 新增文档为 `docs/zdoc-kg-preview-only-response-integration-controlled-implementation-draft-kg-runtime-105-review.md`。

## 4. `preview_only_response` 草案字段结论

- 是否新增 `preview_only_response` 草案字段：是。
- route 层 `KG_READ_ONLY_PREVIEW_REAL_KG_METADATA_FIELDS` 仅新增 `preview_only_response`，通过既有字段循环从 adapter result 透传。
- adapter 层 `OUTPUT_FIELD_WHITELIST` 仅新增 `preview_only_response`，仍经 `_whitelisted_response` 输出。
- helper 层 `build_preview_only_response_integration_payload` 返回的 `preview_only_response` 仅包含以下 4 个顶层键：
  - `preview_contract`
  - `preview_only_mapping`
  - `audit_only_mapping`
  - `prohibited_mapping`

## 5. 既有 helper 复用确认

KG-RUNTIME-105 继续复用既有 preview-only / content-safe helper 链路：

- `classify_content_safe_fields`
- `filter_preview_only_fields`
- `filter_audit_only_fields`
- `build_preview_only_payload`
- `build_preview_only_adapter_mapping`

静态路径为：

- `build_preview_only_response_integration_payload(...)` 调用 `build_preview_only_payload(...)`。
- `build_preview_only_payload(...)` 调用 `filter_preview_only_fields(...)` 与 `filter_audit_only_fields(...)`。
- adapter 的 `_build_preview_only_response_integration(...)` 调用 `build_preview_only_adapter_mapping(...)` 形成 overlap check 输入，再调用 `build_preview_only_response_integration_payload(...)` 形成草案输出。

## 6. Route 透传结论

- route 是否仅透传 `preview_only_response` 草案字段：是。
- KG-RUNTIME-105 的 route diff 仅在 `KG_READ_ONLY_PREVIEW_REAL_KG_METADATA_FIELDS` 中增加 `"preview_only_response"`。
- route 未新增 `/generate`、`/export_docx`、`/review/apply` 调用。
- route 未新增 output/job/export 写入。
- route 未新增 ZBid 写回、evidence、scoring、RAG、prompt registry 或 system instruction registry 接入。
- route 未新增 frontend 接入、真实使用入口或试用入口。

## 7. `preview_only_mapping` 允许字段结论

`preview_only_mapping` 来自 `filter_preview_only_fields(...)`，仅允许以下 content-safe 字段：

- `structure_read_only`
- `structure_summary`
- `structural_profile_only`
- `structural_profile_summary`
- `structure_contract.contract_scope`
- `structure_contract.authorized_target`
- `structure_contract.allowlist_status`
- `structure_contract.target_policy`
- `structure_contract.summary_field_whitelist`
- `structure_contract.value_output_policy`
- `structure_contract.scalar_policy`
- `structure_contract.list_policy`
- `structure_contract.dict_policy`
- `structural_profile_contract.contract_scope`
- `structural_profile_contract.authorized_target`
- `structural_profile_contract.allowlist_status`
- `structural_profile_contract.target_policy`
- `structural_profile_contract.summary_field_whitelist`
- `structural_profile_contract.profile_scope`
- `structural_profile_contract.redaction_policy`
- `structural_profile_contract.scalar_policy`
- `structural_profile_contract.list_policy`
- `structural_profile_contract.dict_policy`
- `structural_profile_contract.module_name_policy`

contract 子字段继续由 `_is_safe_contract_code(...)` 限制为非 bool 的非负整数或非负整数序列。

结论：`preview_only_mapping` 未包含 KG scalar value、业务正文、实体正文、知识条目正文、prompt、system instruction、evidence 或 scoring。

## 8. `audit_only_mapping` 允许字段结论

`audit_only_mapping` 来自 `filter_audit_only_fields(...)`，仅允许以下 audit-only 状态码字段：

- `feature_flag_status`
- `manual_trigger_status`
- `real_kg_read_only_status`
- `authorized_target_hit_status`
- `allowlist_status`
- `route_contract_code`
- `adapter_contract_code`
- `validation_result`
- `overlap_check_result`

结论：`audit_only_mapping` 仅包含门禁、contract、validation、overlap code，不包含 KG value、正文、evidence 或 scoring。

## 9. `prohibited_mapping` 结论

`prohibited_mapping` 仅为禁止类别清单，来自 `PROHIBITED_FIELDS`：

- `KG scalar value`
- `list item 内容`
- `dict value 内容`
- `业务正文`
- `实体正文`
- `知识条目正文`
- `prompt`
- `system instruction`
- `evidence`
- `scoring`
- `原始 KG 文本片段`
- `可反推 KG 正文的字符串`

结论：

- `prohibited_mapping` 不承载 KG value 或正文内容。
- `prohibited_mapping` 未进入 `preview_only_mapping`。
- `_preview_only_overlap_check_result(...)` 对 `preview_only` 字段名与 prohibited 类别做交集检查，静态设计用于保持隔离。

## 10. No-Output-Chain / No-Runtime 静态矩阵

| 审查项 | 结论 |
| --- | --- |
| 是否未接入 `/generate` | 是，未接入 |
| 是否未接入 `/export_docx` | 是，未接入 |
| 是否未接入 `/review/apply` | 是，未接入 |
| 是否未写 output/job/export | 是，未写入 |
| 是否未触发 ZBid 写回 | 是，未触发 |
| 是否未作为 evidence | 是，未作为 evidence |
| 是否未作为 scoring | 是，未作为 scoring |
| 是否未接入 RAG | 是，未接入 |
| 是否未接入 prompt registry | 是，未接入 |
| 是否未接入 system instruction registry | 是，未接入 |
| 是否未运行服务、访问端口或调用 endpoint | 是，本阶段未运行、未访问、未调用 |
| 是否未读取真实 KG 文件正文 | 是，本阶段未读取 |
| 是否未解析真实 KG JSON | 是，本阶段未解析 |
| 是否未再次执行目录扫描 | 是，本阶段未执行目录扫描 |
| 是否未进入真实使用阶段 | 是，未进入 |
| 是否未进入试用阶段 | 是，未进入 |

说明：KG-RUNTIME-106 仅审查 KG-RUNTIME-105 response integration 草案的静态合规性。它不授权执行既有结构读取路径，不代表本阶段读取或解析真实 KG。

## 11. 需进入 KG-RUNTIME-107 的事项

- 是否仍需 KG-RUNTIME-107 做 preview-only response integration frozen audit and no-server smoke authorization gate：是。
- KG-RUNTIME-106 只完成静态合规审查与 no-output-chain review。
- KG-RUNTIME-106 不代表 ZDoc 已接入。
- KG-RUNTIME-106 不代表进入真实使用阶段。
- KG-RUNTIME-106 不代表进入试用阶段。
- KG-RUNTIME-106 不包含 no-server smoke 执行授权。

## 12. KG-RUNTIME-106 最终审查结论

KG-RUNTIME-105 的 `preview_only_response` integration controlled implementation draft 在静态审查范围内满足以下边界：

- preview-only：满足，草案字段仅透出 preview contract、preview-only mapping、audit-only mapping、prohibited mapping。
- content-safe：满足，继续复用既有 content-safe helper/filter 链路。
- no-runtime：满足本阶段静态审查边界，未运行服务、端口或 endpoint。
- no-output-chain：满足，未接入生成链、导出链、写回链。
- no-generation：满足，未接入 `/generate`。
- no-export：满足，未接入 `/export_docx`。
- no-writeback：满足，未接入 `/review/apply` 或 ZBid 写回。
- no-evidence：满足，未作为 evidence。
- no-scoring：满足，未作为 scoring。
- no-RAG：满足，未接入 RAG。
- no-registry：满足，未接入 prompt registry 或 system instruction registry。

KG-RUNTIME-106 到此停止，不进入 KG-RUNTIME-107。
