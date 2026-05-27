# KG-RUNTIME-112 route-layer preview-only response assertion-failure / response-shape diagnosis review

## 结论

KG-RUNTIME-112 已完成 no-server in-process route-layer assertion-failure / response-shape diagnosis。

诊断结论：KG-RUNTIME-110 的断言失败位置应在 route 返回后的根层 integration 字段断言阶段。route 返回值不是裸 `preview_only_response`，而是 route envelope `dict`；adapter 结果被包裹在 `detail`，同时 `preview_only_response` 作为 route 顶层 metadata 被透传。`preview_contract` / `preview_only_mapping` / `audit_only_mapping` / `prohibited_mapping` 四个字段存在于 `response["preview_only_response"]` 内，不存在于 route 根层。

因此，若 KG-RUNTIME-110 smoke 在 route 根层断言上述四个 integration 字段，会得到 assertion failure。建议 KG-RUNTIME-113 在单独授权后修复断言目标或明确 route response unwrapping 规则。

本阶段未修改代码，未进入 KG-RUNTIME-113，未进入 ZDoc 接入、真实使用或试用阶段。

## 基线

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`22a0352087f7a4e94fc0663bd09af0663954c755`
- 开始前基线 tag：`v0.1.494-zdoc-kg-route-layer-preview-only-response-no-go-gate`
- 本地基线 tag 查询结果：未发现本地 tag
- 远端基线 tag 查询结果：`git ls-remote --tags` 被 sandbox SSH 限制拒绝，未请求完全访问权限

## 诊断方式

本阶段只执行了一次 no-server in-process Python 诊断调用。

调用方式：

- 直接导入 route 模块
- 设置 route feature flag
- 直接调用 `kg_read_only_preview_route(...)`
- 使用 synthetic adapter stub 替代 adapter 返回
- 使用 synthetic / content-safe response 形态
- 使用 helper 构造 `preview_only_response` 结构
- 使用 `PYTHONDONTWRITEBYTECODE=1`
- 在诊断调用期间设置文件正文读取、JSON parse、socket / TCP guard

诊断期间 guard 结果：

- 文件正文读取尝试次数：`0`
- JSON parse 尝试次数：`0`
- socket / TCP 尝试次数：`0`

## response_shape

route 返回类型：

- `route_return_type`：`dict`

route 根层形态：

- root 字段数量：`69`
- root 包含 `detail`
- root 包含 `preview_only_response`
- root 不包含 `preview_contract`
- root 不包含 `preview_only_mapping`
- root 不包含 `audit_only_mapping`
- root 不包含 `prohibited_mapping`

`response["preview_only_response"]` 形态：

- `preview_contract`
- `preview_only_mapping`
- `audit_only_mapping`
- `prohibited_mapping`

`response["detail"]` 形态：

- `detail` 为 adapter result 包裹层
- `detail` 字段数量：`37`
- `detail` 包含 `preview_only_response`

## missing_fields

若断言目标是 route 根层，则缺失：

- `preview_contract`
- `preview_only_mapping`
- `audit_only_mapping`
- `prohibited_mapping`

若断言目标是 `response["preview_only_response"]`，则缺失：

- 无

## unexpected_fields

若断言目标误设为裸 `preview_only_response`，route 根层会出现 route envelope / safety metadata / adapter metadata 字段，因此这些字段对裸 preview-only assertion 来说属于 unexpected。

诊断观察到的 unexpected 字段类别：

- route envelope 字段
- request / route identity 字段
- safety guard 字段
- downstream prohibition 字段
- adapter metadata 字段
- structure / structural profile metadata 字段
- `detail`
- `preview_only_response`

## field_type

字段类型诊断：

- `root`：`dict`
- `root.detail`：`dict`
- `root.preview_only_response`：`dict`
- `root.preview_only_response.preview_contract`：`dict`
- `root.preview_only_response.preview_only_mapping`：`dict`
- `root.preview_only_response.audit_only_mapping`：`dict`
- `root.preview_only_response.prohibited_mapping`：`tuple`
- `root.detail.preview_only_response`：`dict`

## assertion_stage

诊断的 assertion stage：

- `root_integration_field_assertion_after_route_return`

解释：

- route call 已返回 `dict`
- `preview_only_response` 已在 route 顶层出现
- 四个 integration 字段未展开到 route 根层
- 四个 integration 字段完整存在于 `preview_only_response` 内
- 因此失败点不是 helper 未生成，也不是 adapter stub 未返回，而是 route-layer assertion target / response-shape 期望与实际 route envelope 不一致

## route 层结构判断

route 层发生了以下结构变化：

- 字段包裹：发生，adapter result 被包裹到 `detail`
- 字段命名变化：未观察到四个 integration 字段命名变化
- 层级变化：发生，四个 integration 字段位于 `preview_only_response` 内，而不是 route 根层
- 透传丢失：未观察到 `preview_only_response` 顶层透传丢失

## 安全边界

本阶段未执行以下事项：

- 未修改代码
- 未修改 adapter / route / helper / `main.py`
- 未修改 frontend / tests / config / JSON
- 未再次执行目录扫描命令
- 未读取真实 KG 文件正文内容
- 未解析真实 KG JSON
- 未运行服务
- 未访问端口
- 未调用 `/health`
- 未调用 `/kg/read-only-preview`
- 未调用 `/generate`
- 未调用 `/export_docx`
- 未调用 `/review/apply`
- 未触发 ZBid 写回
- 未写 output / job / export
- 未运行 Ollama
- 未接入 RAG / registry / CI
- 未作为 evidence
- 未作为 scoring
- 未输出 KG value
- 未输出业务正文 / 实体正文 / 知识条目正文
- 未输出 prompt
- 未输出 system instruction
- 未进入 ZDoc 接入阶段
- 未进入真实使用阶段
- 未进入试用阶段
- 未进入 KG-RUNTIME-113

## KG-RUNTIME-113 建议

建议 KG-RUNTIME-113 在单独授权后修复 route-layer smoke 断言目标：

- 若验证 route contract，应断言 `response["preview_only_response"]` 内的四个 integration 字段。
- 若验证 helper 裸输出，应在 route smoke 中显式 unwrap `preview_only_response` 后再断言。
- 不建议在 KG-RUNTIME-112 修改 route / adapter / helper 代码。
