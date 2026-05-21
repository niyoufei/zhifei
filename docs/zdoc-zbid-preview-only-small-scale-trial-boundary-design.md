# ZDoc-ZBid preview-only small-scale trial boundary design

## 1. 阶段定位

当前已完成 ZDoc-ZBid preview-only / no-write / no-evidence 对接闭环。

当前仅具备进入小范围试用前置设计的条件。本步只定义试用前的边界、人员、入口、数据、禁止项、日志、失败回退和停止条件，不代表已经进入小范围试用。

本步不启动小范围试用。

本步不进入正式生成链。

本步不进入 50 人正式部署设计。

## 2. 小范围试用建议范围

- 试用对象：内部少量人员，建议 2～5 人。
- 试用数据：脱敏样例、测试文档、非正式投标成果。
- 试用目的：验证 preview-only 对接链路的可用性、稳定性、提示清晰度、失败提示和人工复核体验。
- 试用入口：仅限 preview-only 入口，不开放正式生成、正式导出、正式写回入口。
- 试用周期：仅作为后续授权建议，不得在本文档中认定已启动。

## 3. 允许验证内容

后续如经用户明确授权进入小范围试用，可验证的内容应限定为：

- ZDoc preview-only 数据构造。
- ZDoc outbound adapter preview-only 发送。
- ZBid receiver API preview-only 接收。
- `preview_packet`、`validator_result`、`blocked_reasons` 展示或记录。
- 五个 no-write / no-formal-chain false flags：
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- 错误提示、失败回退、人工确认流程。

## 4. 严格禁止内容

小范围试用设计与后续授权中必须继续禁止：

- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得触发 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。
- 不得将 preview-only 结果作为 evidence。
- 不得将 preview-only 结果作为评分依据。
- 不得写入正式业务数据。
- 不得进入 50 人正式部署设计。

## 5. 小范围试用前必须明确的授权点

真正进入小范围试用前，必须由用户另行明确授权以下事项：

- 试用人员名单或角色范围。
- 试用数据来源与脱敏要求。
- 允许启动的服务。
- 允许访问的端口。
- 允许调用的 endpoint。
- 允许记录的日志内容。
- 失败后的停止条件。
- 是否允许临时环境变量启用 preview-only network-send。
- 是否允许保存 smoke / trial report 文档。
- 禁止写回边界。

## 6. 日志与留痕要求

小范围试用的日志与留痕应满足：

- 记录时间。
- 记录操作入口。
- 记录请求类型。
- 记录 preview-only 状态。
- 记录是否触发五个 false flags。
- 记录 `blocked_reasons`。
- 记录失败原因。
- 不记录敏感业务数据。
- 不记录正式 evidence。
- 不写入正式评分依据。

## 7. 失败回退与停止条件

后续小范围试用如出现以下情况，必须立即停止并记录：

- 任一正式链 flag 非 false。
- 出现 `output/job/export` 写入。
- 出现 DOCX 生成。
- 出现 ZBid 写回。
- 出现 evidence 写入。
- 出现未知 endpoint 调用。

失败项不得现场修复。任何修复、代码变更、配置变更、服务重启策略调整或重新试用，均必须另行授权。

## 8. 后续建议

- Step 226 可起草小范围试用授权请求。
- Step 226 仍不得视为已授权启动试用。
- 真正进入小范围试用前，必须另行获得用户明确授权。
- 小范围试用和问题修正完成后，才可讨论 50 人正式部署设计。
