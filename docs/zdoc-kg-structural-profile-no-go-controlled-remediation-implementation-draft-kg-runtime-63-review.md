# ZDoc KG Structural Profile NO-GO Controlled Remediation Implementation Draft - KG-RUNTIME-63 Review

## Scope

- 本次实际修改文件：`backend/kg_read_only_preview_adapter.py`
- 本次实际新增文件：`docs/zdoc-kg-structural-profile-no-go-controlled-remediation-implementation-draft-kg-runtime-63-review.md`
- 是否仅修改授权 adapter / route 文件：是，仅修改授权 adapter 文件；未修改 route 文件。
- 是否未修改 `backend/app/main.py` / frontend / tests / config / JSON：是，未修改。

## Runtime Boundary

- 是否未实际读取真实 KG 正文：是，本阶段未读取真实 KG 文件正文。
- 是否未实际解析真实 KG JSON：是，本阶段未解析真实 KG JSON。
- 是否未运行服务 / endpoint / pytest / py_compile：是，未运行服务，未调用 endpoint，未运行 pytest，未运行 py_compile。
- 是否未接入生成、导出、写回、RAG、registry、CI：是，未接入。
- 本阶段只是修复草案，不能认定 structural-profile smoke 已通过。

## Remediation Points

1. 修复点 1：`structural_profile=true` 且受控 `structure_read=true` 时，adapter 的 structural profile 响应现在同时返回 `structure_summary` 与 `structure_contract`，并继续返回 `structure_read_only`、`structural_profile_only`、`structural_profile_summary`、`structural_profile_contract`。
2. 修复点 2：substring overlap 风险控制策略为不再从 scalar value、list item、dict value、字段名或路径名生成 `module_name_candidates`，该字段固定为空列表/元组语义；`redaction_policy` 改为固定策略字符串，不拼接 KG 内容。

## Whitelists And Read Path

- `structural_profile_summary` 字段白名单保持 14 个字段，未扩大。
- `structure_summary` 字段白名单保持 13 个字段，未扩大。
- scalar 仅输出类型 / 计数；list 仅输出长度桶 / 类型摘要；dict 仅输出 key 名 / key 数 / 类型集合，不输出 value 内容。
- 是否未新增第二套不受控读取路径：是，继续复用既有受控 structure-read 路径。

## Next Gate

- 仍需 KG-RUNTIME-64 做静态合规与 no-content-leak review。
- 本阶段只形成 controlled remediation implementation draft，不进入真实使用阶段。
