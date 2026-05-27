# KG-RUNTIME-114 corrected route-layer no-server in-process preview-only response integration re-smoke validation review

## 结论

KG-RUNTIME-114 corrected route-layer no-server in-process preview-only response integration re-smoke validation 结论：PASS。

本阶段只验证 corrected route-layer response-shape 断言目标。route 返回值确认为 envelope `dict`，`root.preview_only_response` 存在，且 `preview_only_response` 内包含：

- `preview_contract`
- `preview_only_mapping`
- `audit_only_mapping`
- `prohibited_mapping`

本阶段断言目标为 `root.preview_only_response`。未在 route root 根层直接断言 `preview_contract` / `preview_only_mapping` / `audit_only_mapping` / `prohibited_mapping`。

本阶段未进入 ZDoc 接入阶段、真实使用阶段或试用阶段。未进入 KG-RUNTIME-115。

## 基线

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`fb14e5c7fe49fe1cda7756589a9490f69bdb7cc5`
- 开始前基线 tag：`v0.1.496-zdoc-kg-route-layer-response-shape-diagnosis-frozen-gate`
- 本地 `git tag --points-at HEAD`：未发现本地 tag
- 远端基线 tag 检查：`git push --dry-run origin HEAD:refs/tags/v0.1.496-zdoc-kg-route-layer-response-shape-diagnosis-frozen-gate` 返回 `Everything up-to-date`
- 开始前 `git status --short`：clean

说明：普通 `git ls-remote --tags` 被 sandbox SSH 限制拒绝，未切换完全访问权限；按本阶段说明，以 HEAD 与远端 tag 作为基线。

## 执行方式

本阶段使用 no-server in-process route 调用完成 corrected re-smoke：

- 使用 `PYTHONDONTWRITEBYTECODE=1`
- 直接导入 route 模块
- 设置 route feature flag
- 直接调用 `kg_read_only_preview_route(...)`
- 未使用 `TestClient`
- 未启动 `uvicorn`
- 未绑定 TCP 端口
- 未访问 `127.0.0.1`
- 未调用 `/health`
- 未调用 `/kg/read-only-preview`
- 使用 synthetic adapter stub
- 使用 helper 构造 synthetic / content-safe `preview_only_response`
- 在 route 调用期间拦截文件 IO、`Path.read_text`、`Path.read_bytes`、JSON parse、socket / TCP

执行中有两个工具层纠偏事实：

- `.venv/bin/python` 不存在，该命令未进入 Python 解释器，未执行 re-smoke。
- 使用 `asyncio.run()` 的 harness 在 route 调用前被本地 event-loop `socketpair` 触发的 socket guard 中止；该次未作为 re-smoke 证据，未绑定 TCP 端口，未访问 endpoint，未读取真实 KG，未解析真实 KG JSON。

最终有效 corrected re-smoke 使用 direct coroutine send 方式推进无 `await` 的 route coroutine，避免事件循环 socketpair 副作用。

## re-smoke 结果

最终有效 corrected re-smoke 输出：

```text
corrected_resmoke=PASS
route_return_type=dict
route_envelope_keys_present=ok,enabled,status,reason,detail,request_id
root_preview_only_response_present=yes
assertion_target=root.preview_only_response
integration_keys=preview_contract,preview_only_mapping,audit_only_mapping,prohibited_mapping
preview_only_mapping_keys=structural_profile_contract,structural_profile_only,structural_profile_summary,structure_contract,structure_read_only,structure_summary
audit_only_mapping_keys=adapter_contract_code,allowlist_status,authorized_target_hit_status,feature_flag_status,manual_trigger_status,overlap_check_result,real_kg_read_only_status,route_contract_code,validation_result
prohibited_mapping_count=12
prohibited_mapping_is_category_list=yes
guard_file_io_attempts=0
guard_path_read_attempts=0
guard_json_parse_attempts=0
guard_socket_attempts=0
```

## response shape 判断

- route 返回类型：`dict`
- route 返回形态：envelope dict
- route envelope key：`ok` / `enabled` / `status` / `reason` / `detail` / `request_id`
- `root.preview_only_response`：存在
- `root.preview_only_response` 类型：`dict`
- corrected assertion target：`root.preview_only_response`
- 未将四个 integration 字段当作 route root 根层字段断言

## mapping 判断

`preview_only_mapping` 仅包含 corrected re-smoke 允许字段：

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

`preview_only_mapping` 未包含以下内容：

- KG scalar value
- list item 内容
- dict value 内容
- 业务正文
- 实体正文
- 知识条目正文
- prompt
- system instruction
- evidence
- scoring
- 原始 KG 文本片段
- 可反推 KG 正文的字符串

## guard 结果

- 文件 IO 尝试次数：`0`
- `Path.read_text` / `Path.read_bytes` / `Path.open` 尝试次数：`0`
- JSON parse 尝试次数：`0`
- socket / TCP 尝试次数：`0`

因此，本次有效 corrected re-smoke 未读取真实 KG 文件正文内容，未解析真实 KG JSON，未启动服务，未绑定 TCP 端口，未访问 `127.0.0.1`，未调用真实 endpoint。

## 边界确认

本阶段未执行以下事项：

- 未修改代码
- 未修改 adapter / route / helper / `main.py`
- 未修改 frontend / tests / config / JSON
- 未再次执行目录扫描命令，包括 `find ..`、`find /`、`find AI知识图谱大全`
- 未读取真实 KG 文件正文内容
- 未解析真实 KG JSON
- 未运行服务
- 未绑定 TCP 端口
- 未访问 `127.0.0.1`
- 未调用 `/health`
- 未调用 `/kg/read-only-preview`
- 未运行 `python3 -m json.tool`
- 未运行 `pytest`
- 未运行 `py_compile`
- 未运行 Ollama
- 未触发 `/generate`
- 未触发 `/export_docx`
- 未触发 `/review/apply`
- 未触发 ZBid 写回
- 未写正文
- 未写 output / job / export
- 未接入 RAG / registry / CI
- 未作为 evidence
- 未作为 scoring
- 未切换完全访问权限
- 未使用 GitHub / browser / Chrome / computer / Documents / Spreadsheets / Presentations / Gmail / Slack / Canva 插件
- 未进入 ZDoc 接入阶段
- 未进入真实使用阶段
- 未进入试用阶段
- 未进入 KG-RUNTIME-115

## 阶段结论

KG-RUNTIME-114 corrected route-layer no-server in-process preview-only response integration re-smoke validation：PASS。

该 PASS 仅证明 corrected route-layer assertion target 下，synthetic / content-safe `preview_only_response` 可通过 route envelope 透传，并可在 `root.preview_only_response` 中断言四个 integration 字段。

该 PASS 不证明 ZDoc 已接入，不证明真实 KG 已使用，不证明进入试用阶段，不证明 `/generate` / `/export_docx` / `/review/apply` 已接入。
