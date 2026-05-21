# ZDoc-ZBid preview-only small-scale trial authorization request

## 1. 授权请求来源

本授权请求基于以下阶段结果起草：

- Step 224 preview-only 对接阶段总归档。
- Step 225 小范围试用前置边界设计。

当前 ZDoc-ZBid preview-only / no-write / no-evidence 对接闭环已完成。

当前尚未进入小范围试用。

当前尚未进入正式生成链。

当前尚未进入 50 人正式部署设计。

本文档只代表申请授权，不代表已启动小范围试用。

## 2. 拟申请的小范围试用范围

- 试用对象：内部少量人员，建议 2～5 人；具体名单或角色须由用户后续明确。
- 试用数据：脱敏样例、测试文档、非正式投标成果。
- 试用目的：验证 preview-only 对接链路可用性、稳定性、失败提示、人工复核体验。
- 试用入口：仅限 preview-only 入口。
- 试用输出：仅允许生成 trial report / smoke report / 问题清单，不得生成正式 DOCX，不得写正式结果。

## 3. 试用允许验证内容

如后续获得用户明确授权，试用期间允许验证的内容仅限：

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

## 4. 试用期间必须禁止

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

## 5. 试用前必须由用户明确授权的事项

真正进入小范围试用前，必须由用户另行明确授权以下事项：

- 试用人员名单或角色范围。
- 试用数据来源与脱敏要求。
- 允许启动的服务。
- 允许访问的端口。
- 允许调用的 endpoint。
- 是否允许临时启用 preview-only network-send。
- 是否允许保存 trial report / smoke report / 问题清单。
- 日志留痕范围。
- 失败后的停止条件。
- 禁止写回边界。

## 6. 建议试用控制条件

- 仅使用临时环境变量启用 preview-only network-send。
- 不写入 `.env`、配置文件或持久配置。
- 每次试用前后检查 ZDoc 与 ZBid 的 `git status --short`。
- 每次试用前后检查 `output/job/export` 快照。
- 每次试用后关闭本步启动的服务。
- 每次试用必须形成 trial report。

## 7. 日志与留痕要求

- 记录时间、操作者角色、操作入口、请求类型、preview-only 状态。
- 记录是否保持五个 false flags。
- 记录 `blocked_reasons`。
- 记录失败原因。
- 不记录敏感业务数据。
- 不记录正式 evidence。
- 不写入正式评分依据。

## 8. 停止条件

后续小范围试用如出现以下情况，必须立即停止：

- 任一正式链 flag 非 false。
- 出现 `output/job/export` 写入。
- 出现 DOCX 生成。
- 出现 ZBid 写回。
- 出现 evidence 写入。
- 出现未知 endpoint 调用。
- 出现 fallback 到正式接口。

失败项不得现场修复。任何修复、代码变更、配置变更、服务重启策略调整或重新试用，均必须另行授权。

## 9. 授权后拟进入的下一步

- Step 227 可作为 ZDoc-ZBid preview-only small-scale trial controlled execution。
- Step 227 必须由用户明确授权。
- Step 227 不得修改代码。
- Step 227 不得进入正式生成链。
- Step 227 不得进入 50 人正式部署设计。

## 10. Step 227 用户授权语建议

以下授权语仅供用户后续复制并补全。本文档本身不代表用户已授权。

> 我授权执行 Step 227：ZDoc-ZBid preview-only small-scale trial controlled execution。授权范围仅限 preview-only / no-write / no-evidence 小范围试用。
>
> ZDoc 仓库路径：`/Users/youfeini/Desktop/文档生成系统`；ZDoc 分支：`main`；ZDoc 开始前 HEAD：`<由用户在 Step 227 授权时填写>`。
>
> ZBid 仓库路径：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`；ZBid 分支：`local-llm-integration-clean`；ZBid 开始前 HEAD：`<由用户在 Step 227 授权时填写>`。
>
> 试用人员或角色范围：`<由用户填写>`。
>
> 试用数据范围：仅限脱敏样例、测试文档、非正式投标成果；具体数据来源与脱敏要求为：`<由用户填写>`。
>
> 允许启动的服务、访问的端口、调用的 endpoint 边界为：`<由用户填写>`。
>
> 允许临时启用 preview-only network-send：`<是/否，由用户填写>`。
>
> 允许保存 trial report / smoke report / 问题清单：`<是/否，由用户填写>`。
>
> 禁止触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回；禁止生成 DOCX；禁止写 `output/job/export`；禁止将 preview-only 结果作为 evidence 或评分依据；禁止写入正式业务数据；禁止进入 50 人正式部署设计。试用失败时不得现场修复，必须停止并回报，修复另行授权。
