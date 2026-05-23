# ZDoc-ZBid preview-only expanded trial authorization request

## 1. 授权请求来源

本文档用于起草 ZDoc-ZBid preview-only 扩大试用授权请求，只代表申请授权，不代表已授权启动扩大试用。

授权请求来源如下：

- 基于 preview-only 对接闭环已完成。
- 基于 small-scale trial 已完成。
- 基于 Step 236 扩大试用前置边界设计。
- 当前尚未启动扩大试用。
- 当前尚未进入正式生成链。
- 当前尚未进入 50 人正式部署设计。

当前阶段仍必须保持 preview-only / no-write / no-evidence，不得把扩大试用理解为正式上线或正式业务联调。

## 2. 拟申请的扩大试用范围

后续如进入扩大试用，拟申请范围应限定为：

- 试用对象：内部受控角色扩大范围，建议候选为 5～10 人或等效角色组。
- 试用角色建议分组：技术标编制、复核、项目负责人、质控审核等。
- 试用数据：脱敏样例、测试文档、非正式投标成果。
- 试用入口：仅限 preview-only 入口。
- 试用输出：仅限 report / issue list / observation note，不得形成正式成果。

扩大试用不得生成正式 DOCX，不得写入正式业务数据，不得产生正式 evidence，不得产生评分依据，不得触发 ZBid 写回。

## 3. 扩大试用允许验证内容

后续经用户明确授权后，扩大试用只允许验证：

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
- blocked_reasons 阅读与人工复核。
- 人工复核流程。
- 日志留痕完整性。

上述验证不得延伸为正式生成链、正式证据链、正式评分链、正式导出链或正式写回链验证。

## 4. 扩大试用期间必须禁止

扩大试用期间必须继续禁止：

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

任何 fallback 到正式接口、正式链路或正式写入路径的行为都必须立即停止并记录。

## 5. 扩大试用前必须明确授权的事项

进入扩大试用前，必须由用户明确授权以下事项：

- 试用人员名单或角色范围。
- 试用数据来源与脱敏要求。
- 允许启动的服务。
- 允许访问的端口。
- 允许调用的 endpoint。
- 是否允许临时启用 preview-only network-send。
- 是否允许保存试用报告、问题清单、日志摘要。
- 失败停止条件。
- 禁止写回边界。

未在授权中明确列出的服务、端口、endpoint、数据范围、角色范围和报告保存方式，均不得默认执行。

## 6. 建议控制条件

扩大试用建议采用以下控制条件：

- 仅使用临时环境变量启用 preview-only network-send。
- 不写入 `.env`、配置文件或持久配置。
- 每次试用前后检查 ZDoc 与 ZBid 的 `git status --short`。
- 每次试用前后检查 `output/job/export` 快照。
- 每次试用后关闭本步启动的服务。
- 每次试用必须形成 expanded-trial report。
- 试用 payload 必须为脱敏样例、测试文档或非正式投标成果，不得包含真实业务文件、正式 evidence、正式评分结果、DOCX 或 writeback 数据。

## 7. 停止条件

扩大试用期间如出现以下任一情况，必须立即停止：

- 任一正式链 flag 非 false。
- 出现 `output/job/export` 写入。
- 出现 DOCX 生成。
- 出现 ZBid 写回。
- 出现 evidence 写入。
- 出现评分依据写入。
- 出现未知 endpoint 调用。
- 出现 fallback 到正式接口。

停止后不得现场修复失败项。修复、UI 调整、日志增强、接口变更、服务重启或复验均必须另行授权。

## 8. 授权后拟进入的下一步

授权后拟进入的下一步为：

- Step 238 可作为 ZDoc-ZBid preview-only expanded trial controlled execution。
- Step 238 必须由用户明确授权。
- Step 238 不得修改代码。
- Step 238 不得进入正式生成链。
- Step 238 不得进入 50 人正式部署设计。

本文档不授权 Step 238，不授权启动服务，不授权访问端口，不授权调用 endpoint，不授权扩大试用执行。

## 9. Step 238 授权语建议

用户如需授权 Step 238，可复制并补全以下授权语：

> 我授权执行 Step 238：ZDoc-ZBid preview-only expanded trial controlled execution。ZDoc 仓库限定为 `/Users/youfeini/Desktop/文档生成系统`，分支限定为 `main`，开始前 HEAD 必须由本次授权明确填写并在执行前核验；ZBid 仓库限定为 `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`，分支限定为 `local-llm-integration-clean`，开始前 HEAD 必须由本次授权明确填写并在执行前核验。试用人员或角色范围限定为内部受控 5～10 人或等效角色组；试用数据限定为脱敏样例、测试文档、非正式投标成果；允许启动明确列出的 preview-only 必要本地服务、访问明确列出的本地端口、调用明确列出的 preview-only endpoint；允许临时启用 preview-only network-send，但不得写入持久配置。全程仅限 preview-only / no-write / no-evidence；不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回；不得生成 DOCX；不得写 `output/job/export`；不得将 preview-only 结果作为 evidence 或评分依据；不得进入正式生成链、真实业务联调或 50 人正式部署设计。

执行 Step 238 前仍需用户给出完整授权信息，包括两仓开始前 HEAD、允许服务、允许端口、允许 endpoint、试用角色范围、试用数据范围、报告保存范围和停止条件。

## 10. 结论

当前最合理的下一步是等待用户审阅本授权请求文档。

在用户明确授权前，不得启动扩大试用，不得启动服务，不得访问端口，不得调用任何 endpoint，不得修改代码，不得进入正式链，不得进入 50 人正式部署设计。
