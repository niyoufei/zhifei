# ZDoc-ZBid preview-only expanded trial boundary design

## 1. 当前阶段基础

基于 Step 224 至 Step 235 的阶段成果：

- preview-only 对接闭环已完成。
- small-scale trial 已完成。
- observation docs-only 优化已完成。
- 当前仍未开放正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply、ZBid 写回。
- 当前仍未进入 50 人正式部署设计。

本文档只定义扩大试用前置边界、角色范围、数据范围、服务/端口/endpoint 范围、停止条件和授权点，不代表已启动扩大试用。

## 2. 扩大试用定位

扩大试用仅作为 small-scale trial 之后的中间阶段。

扩大试用仍必须保持：

- preview-only
- no-write
- no-evidence

扩大试用目标是验证更稳定的内部使用流程，包括操作入口、错误提示、blocked_reasons 可读性、人工复核流程、日志留痕和问题上报闭环。扩大试用不是正式上线，不开放正式生成链、正式证据链、正式评分链、DOCX 导出、review/apply 或 ZBid 写回。

## 3. 扩大试用建议范围

建议范围如下：

- 试用对象：内部受控角色扩大范围，建议候选为 5～10 人或等效角色组。
- 试用角色分组：技术标编制、复核、项目负责人、质控审核等。
- 试用数据：脱敏样例、测试文档、非正式投标成果。
- 试用入口：仅限 preview-only 入口。
- 试用输出：仅限 report、issue list、observation note。

扩大试用不得形成正式成果，不得生成正式 DOCX，不得写入正式业务数据，不得把 preview-only 结果作为 evidence 或评分依据。

## 4. 允许验证内容

在用户后续明确授权扩大试用后，允许验证内容应限定为：

- ZDoc preview-only 数据构造。
- ZDoc outbound adapter preview-only 发送。
- ZBid receiver API preview-only 接收。
- preview_packet、validator_result、blocked_reasons 展示或记录。
- 五个 no-write / no-formal-chain false flags：
  - generate_called=false
  - export_docx_called=false
  - review_apply_called=false
  - zbid_writeback_called=false
  - output_job_export_written=false
- 错误提示。
- blocked_reasons 阅读和人工复核。
- 人工复核流程。
- 日志留痕完整性。

上述验证仍只服务 preview-only / no-write / no-evidence 试用，不得延伸为正式链路验证。

## 5. 服务 / 端口 / endpoint 边界建议

扩大试用前必须重新明确服务、端口和 endpoint 边界：

- 仅允许启动 preview-only 相关必要本地服务。
- 仅允许访问经授权的本地端口。
- 仅允许调用 preview-only endpoint。
- 不得调用 `/generate`。
- 不得调用 `/export_docx`。
- 不得调用 `/review/apply`。
- 不得调用 ZBid 写回相关 endpoint。
- 不得扩展到未知 endpoint。

如扩大试用需要临时启用 preview-only network-send，只能使用临时环境变量，不得写入 `.env`、配置文件或持久配置。

## 6. 严格禁止

扩大试用阶段必须继续禁止：

- 不得触发正式生成链。
- 不得触发正式证据链。
- 不得触发正式评分链。
- 不得触发正式导出链。
- 不得触发 ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。
- 不得将 preview-only 结果作为 evidence。
- 不得将 preview-only 结果作为评分依据。
- 不得写入正式业务数据。
- 不得进入 50 人正式部署设计。

任何 fallback 到正式接口、正式链路或正式写入路径的行为都必须视为停止条件。

## 7. 扩大试用前必须明确的授权点

进入扩大试用前，必须由用户明确授权并写清：

- 试用人员名单或角色范围。
- 试用数据来源与脱敏要求。
- 允许启动的服务。
- 允许访问的端口。
- 允许调用的 endpoint。
- 是否允许临时启用 preview-only network-send。
- 是否允许保存试用报告、问题清单、日志摘要。
- 失败停止条件。
- 禁止写回边界。

授权请求不得默认包含正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply、ZBid 写回或 50 人正式部署设计。

## 8. 停止条件

扩大试用期间如出现以下任一情况，必须立即停止并记录：

- 任一正式链 flag 非 false。
- 出现 `output/job/export` 写入。
- 出现 DOCX 生成。
- 出现 ZBid 写回。
- 出现 evidence 写入。
- 出现评分依据写入。
- 出现未知 endpoint 调用。
- 出现 fallback 到正式接口。

停止后不得现场修复失败项。任何修复、UI 调整、日志增强、接口变更、服务重启或复验都必须另行授权。

## 9. 后续建议

- Step 237 可起草“扩大试用授权请求”。
- Step 237 不得视为已授权启动扩大试用。
- 扩大试用与问题修正完成后，才可考虑更大范围试用或正式部署前置设计。
- 50 人正式部署设计不得提前进入。

当前最合理的后续顺序仍是：先完成 preview-only / no-write / no-evidence 范围内的扩大试用授权请求，再在明确授权后执行受控扩大试用；扩大试用和问题修正闭环后，才讨论更大范围或正式部署前置事项。
