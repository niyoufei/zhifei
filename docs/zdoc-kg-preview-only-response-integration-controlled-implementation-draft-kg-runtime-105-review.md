# KG-RUNTIME-105 ZDoc KG Preview-Only Response Integration Controlled Implementation Draft Review

## 1. 本次实际修改文件

- `backend/kg_content_safe_output_contract.py`
- `backend/kg_read_only_preview_adapter.py`
- `backend/app/routers/kg_read_only_preview.py`

## 2. 本次实际新增文件

- `docs/zdoc-kg-preview-only-response-integration-controlled-implementation-draft-kg-runtime-105-review.md`

## 3. 授权范围确认

- 是否仅修改授权 adapter / route / helper 文件：是，仅修改 `backend/kg_content_safe_output_contract.py`、`backend/kg_read_only_preview_adapter.py`、`backend/app/routers/kg_read_only_preview.py`。
- 是否未修改 `backend/app/main.py`：是，未修改。
- 是否未修改 frontend / tests / config / JSON：是，未修改。

## 4. 禁止执行事项确认

- 是否未实际读取真实 KG 正文：是，本阶段未读取真实 KG 正文。
- 是否未实际解析真实 KG JSON：是，本阶段未解析真实 KG JSON。
- 是否未运行服务 / endpoint / pytest / py_compile：是，未运行服务，未访问 endpoint，未运行 pytest，未运行 py_compile。
- 是否未再次执行目录扫描：是，未执行 `find ..`、`find /`、`find AI知识图谱大全`。
- 是否未接入 `/generate`、`/export_docx`、`/review/apply`：是，未接入。
- 是否未写 output/job/export：是，未写入。
- 是否未接入 RAG / registry / CI：是，未接入。
- 是否未进入 ZDoc 前端接入、真实使用、试用阶段：是，未进入。

## 5. Preview-Only Response Integration 草案字段

本阶段新增或接入的 response integration 草案字段为：

- `preview_only_response`
- `preview_only_response.preview_contract`
- `preview_only_response.preview_only_mapping`
- `preview_only_response.audit_only_mapping`
- `preview_only_response.prohibited_mapping`

`backend/app/routers/kg_read_only_preview.py` 仅将 adapter 返回的 `preview_only_response` 草案字段透传到 KG read-only preview response 顶层；未接入前端，未写正文，未写 output。

## 6. KG-RUNTIME-100 Mapping Helper 复用确认

已复用 KG-RUNTIME-100 helper / adapter mapping：

- `classify_content_safe_fields`
- `filter_preview_only_fields`
- `filter_audit_only_fields`
- `build_preview_only_payload`
- `build_preview_only_adapter_mapping`

`build_preview_only_response_integration_payload` 通过 `build_preview_only_payload` 复用上述过滤链路；adapter 通过 `build_preview_only_adapter_mapping` 生成 overlap check 的输入。

## 7. Preview-Only 映射字段清单

`preview_only_mapping` 仅允许来自 content-safe response 形态的以下字段：

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

contract 字段继续由 `_is_safe_contract_code` 限制为安全枚举 / 数字码字段，不包含 bool、KG scalar value、正文、evidence、scoring。

## 8. Audit-Only 映射字段清单

`audit_only_mapping` 仅允许以下字段：

- `feature_flag_status`
- `manual_trigger_status`
- `real_kg_read_only_status`
- `authorized_target_hit_status`
- `allowlist_status`
- `route_contract_code`
- `adapter_contract_code`
- `validation_result`
- `overlap_check_result`

这些字段均为门禁状态或 contract / validation / overlap code，不包含 KG value。

## 9. Prohibited 禁止字段清单

`prohibited_mapping` 仅作为禁止类别清单返回：

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

## 10. Prohibited 与 Preview-Only 隔离确认

- 是否确认 `prohibited` 未进入 `preview_only`：是，adapter 增加 `overlap_check_result`，基于 KG-RUNTIME-100 mapping 输出检查 `preview_only_mapping` 字段名与 `prohibited_mapping` 禁止类别无交集。
- 是否确认 `preview_only` 未包含 KG value / 正文 / evidence / scoring：是，`preview_only_mapping` 仅由 content-safe response 的结构只读摘要、结构画像摘要和安全 contract 数字码字段组成。

## 11. 门禁确认

`preview_only_response` 只在 adapter 已进入完整 gated structural profile preview 草案分支时生成，仍受以下条件约束：

- feature flag 已启用。
- `manual_trigger = true`。
- `real_kg_read_only = true`。
- `structure_read = true`。
- `structural_profile = true`。
- `authorized_target` 严格等于 `知识图谱/ZF-KG-12-Municipal-Bridge.json`。

本阶段没有新增绕过门禁的入口。

## 12. 下阶段边界

- 是否仍需 KG-RUNTIME-106 做静态合规与 no-output-chain review：是，仍需 KG-RUNTIME-106 单独做静态合规与 no-output-chain review。
- 明确说明：本阶段只是 preview-only response integration 草案，不能认定 ZDoc 已接入，不能认定进入试用阶段。
