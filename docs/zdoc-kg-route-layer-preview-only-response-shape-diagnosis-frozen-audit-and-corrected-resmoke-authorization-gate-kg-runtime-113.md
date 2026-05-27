# KG-RUNTIME-113 route-layer preview-only response shape diagnosis frozen audit and corrected re-smoke authorization gate

## 结论

KG-RUNTIME-113 仅冻结 KG-RUNTIME-112 的 route-layer preview-only response assertion-failure / response-shape diagnosis 结果，并设置后续 KG-RUNTIME-114 corrected route-layer no-server in-process preview-only response integration re-smoke 授权门槛。

KG-RUNTIME-113 本身不修改代码，不运行 smoke，不读取真实 KG，不解析真实 KG JSON，不进入 KG-RUNTIME-114。

当前不得认定 route-layer smoke 已通过；不得认定 ZDoc 已接入；不得认定已进入真实使用；不得认定已进入试用阶段；不得作为 evidence；不得作为 scoring。

## 基线

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- KG-RUNTIME-113 开始前 HEAD：`d5e2ae04b764bf059a4bf5505fba1360502dd9ee`
- KG-RUNTIME-113 开始前基线 tag：`v0.1.495-zdoc-kg-route-layer-preview-only-response-shape-diagnosis`
- 基线说明：KG-RUNTIME-112 本地 tag 写入被系统拒绝，但远端 tag 已通过 refspec 创建并指向上述 HEAD；KG-RUNTIME-113 以 HEAD 与远端 tag 作为基线。

## KG-RUNTIME-112 已冻结事实

KG-RUNTIME-112 已完成 route-layer preview-only response assertion-failure / response-shape diagnosis。

KG-RUNTIME-112 未修改代码。

KG-RUNTIME-112 未启动服务。

KG-RUNTIME-112 未访问 endpoint。

KG-RUNTIME-112 未读取真实 KG 文件正文内容。

KG-RUNTIME-112 未解析真实 KG JSON。

KG-RUNTIME-112 使用 synthetic / content-safe response 形态。

KG-RUNTIME-112 使用 no-server in-process route-layer 诊断方式，并使用 synthetic adapter stub 替代真实 KG 读取路径。

## response-shape 诊断冻结

KG-RUNTIME-112 诊断确认：

- route 返回 envelope `dict`
- route 根层存在 `preview_only_response`
- route 根层存在 `detail`
- `preview_contract` 位于 `root.preview_only_response` 内
- `preview_only_mapping` 位于 `root.preview_only_response` 内
- `audit_only_mapping` 位于 `root.preview_only_response` 内
- `prohibited_mapping` 位于 `root.preview_only_response` 内
- 四个 integration 字段不位于 root 根层
- 在 root 层断言四个 integration 字段会失败
- `preview_only_response` 内四个 integration 字段无缺失
- 断言失败阶段为 `root_integration_field_assertion_after_route_return`

字段类型冻结：

- `root`：`dict`
- `root.detail`：`dict`
- `root.preview_only_response`：`dict`
- `root.preview_only_response.preview_contract`：`dict`
- `root.preview_only_response.preview_only_mapping`：`dict`
- `root.preview_only_response.audit_only_mapping`：`dict`
- `root.preview_only_response.prohibited_mapping`：`tuple`

route 层结构冻结：

- adapter result 被包裹到 `detail`
- `preview_only_response` 作为 route 顶层 metadata 被透传
- 四个 integration 字段没有在 route 根层展开
- 四个 integration 字段没有观察到命名变化
- 未观察到 `preview_only_response` 顶层透传丢失

## KG-RUNTIME-110 NO-GO 直接原因冻结

KG-RUNTIME-110 NO-GO 的直接原因冻结为：

- smoke 断言目标使用 root 层字段
- 实际 route envelope 将四个 integration 字段包裹在 `root.preview_only_response` 内
- 因此 root 层断言 `preview_contract` / `preview_only_mapping` / `audit_only_mapping` / `prohibited_mapping` 会失败

该 NO-GO 不应直接解释为 `preview_only_response` 集成本身失败。更准确的结论是：需要修正 corrected re-smoke 的断言目标，或显式 unwrap `preview_only_response` 后再断言。

## 当前不得认定事项

当前不得认定：

- route-layer smoke 已通过
- ZDoc 已接入
- 已进入真实使用
- 已进入试用阶段
- 可作为 evidence
- 可作为 scoring

## KG-RUNTIME-114 授权门槛草案

KG-RUNTIME-114 只有在后续单独授权后，才允许执行 corrected route-layer no-server in-process preview-only response integration re-smoke。KG-RUNTIME-113 不执行 re-smoke。

KG-RUNTIME-114 授权边界草案如下：

- 不启动 uvicorn
- 不绑定 TCP 端口
- 不访问 `127.0.0.1`
- 不调用真实 endpoint
- 优先使用直接 route in-process 调用
- 使用 synthetic / 已验证 content-safe response 形态
- 不读取真实 KG
- 不解析真实 KG JSON
- 不再次执行目录扫描
- 断言目标必须为 `root.preview_only_response`
- 或显式 unwrap `preview_only_response` 后再断言
- 必须验证 `preview_only_response` 存在
- 必须验证 `preview_only_response` 内包含 `preview_contract`
- 必须验证 `preview_only_response` 内包含 `preview_only_mapping`
- 必须验证 `preview_only_response` 内包含 `audit_only_mapping`
- 必须验证 `preview_only_response` 内包含 `prohibited_mapping`
- 必须验证 `prohibited_mapping` 未进入 `preview_only_mapping`
- 必须验证 `preview_only_mapping` 不含 KG value / 正文 / evidence / scoring
- 禁止触发生成、导出、写回
- 禁止写 output / job / export
- 禁止运行 Ollama
- 禁止 pytest
- 禁止 py_compile
- 禁止接入 RAG / registry / CI
- 禁止进入 ZDoc 接入阶段
- 禁止进入真实使用阶段
- 禁止进入试用阶段

KG-RUNTIME-114 corrected re-smoke 如未满足上述边界，应停止并归档为 NO-GO，不得现场扩大权限或切换为服务 / endpoint / pytest / 真实 KG 方式。

## KG-RUNTIME-113 安全边界

KG-RUNTIME-113 未执行以下事项：

- 未修改 adapter / route / helper / `main.py`
- 未修改 frontend / tests / config / JSON
- 未再次执行目录扫描命令
- 未读取真实 KG 文件正文内容
- 未解析真实 KG JSON
- 未运行服务
- 未访问端口
- 未调用 `/health`
- 未调用 `/kg/read-only-preview`
- 未运行 `python3 -m json.tool`
- 未运行 pytest
- 未运行 py_compile
- 未运行 Ollama
- 未触发 `/generate`
- 未触发 `/export_docx`
- 未触发 `/review/apply`
- 未触发 ZBid 写回
- 未写业务正文、实体正文或知识条目正文
- 未写 output / job / export
- 未接入 RAG / registry / CI
- 未进入真实使用阶段
- 未进入试用阶段
- 未作为 evidence
- 未作为 scoring
- 未切换为完全访问权限
- 未使用任何插件

## 停止线

KG-RUNTIME-113 只冻结 KG-RUNTIME-112 response-shape 诊断结果，并设置 KG-RUNTIME-114 corrected no-server re-smoke 授权门槛。

KG-RUNTIME-113 未执行 corrected re-smoke。

KG-RUNTIME-113 未进入 KG-RUNTIME-114。
