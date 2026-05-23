# ZDoc-ZBid 20-user local deployment and pilot-run authorization request

## 1. 当前推进口径

本文档用于起草 20 人本地化部署与试运行授权请求，只代表申请授权，不代表已启动部署或试运行。

当前推进口径如下：

- 当前阶段按约 20 人团队使用进行本地化部署与接入。
- 先完成 ZDoc 与 ZBid 的本地化部署与试运行。
- ChatGPT 作为系统顶级补充与总控。
- 试运行成功后，再扩大人员规模并开展更大规模部署设计。
- 更先进本地大模型升级属于后续阶段。

该推进口径优先解决“本地可用、流程闭环、试运行稳定”，而不是直接进入 50 人正式部署设计或模型升级实施。

## 2. 授权请求范围

本次拟申请的授权范围仅限 20 人场景本地部署与试运行实施。

该授权请求不代表：

- 不代表开放正式链。
- 不代表开放正式证据链、评分依据写入、DOCX 导出、review/apply、ZBid 写回。
- 不代表进入 50 人正式部署设计。
- 不代表开始升级顶级本地大模型。

即使后续获得 Step 245 授权，也必须保持 preview-only / no-write / no-evidence 边界，除非用户另行明确授权正式链开放。

## 3. 拟申请的实施范围

后续 Step 245 如获明确授权，拟申请实施范围包括：

- 本地必要服务启动。
- 本地端口访问。
- ZDoc / ZBid 在 preview-only / no-write / no-evidence 边界下的试运行。
- 试运行日志记录。
- 问题清单记录。
- 失败回退记录。
- ChatGPT 作为顶级补充与总控的使用边界验证。

实施范围必须限定为：

- 20 人场景。
- 本地化部署与试运行。
- preview-only / no-write / no-evidence。
- 脱敏样例、测试文档、非正式成果。
- 明确授权的服务、端口和 endpoint。

## 4. ChatGPT 总控与顶级补充边界

ChatGPT 在 20 人本地部署与试运行阶段的定位：

- 协助解释 preview-only 结果。
- 协助整理 blocked_reasons。
- 协助生成问题清单和复盘摘要。
- 协助提示人工复核流程。
- 协助整理后续授权边界。

ChatGPT 不得：

- 替代系统权限控制。
- 默认开放正式链。
- 替代人工审批。
- 将 preview-only 结果作为 evidence。
- 将 preview-only 结果作为评分依据。
- 直接触发生成、导出、review/apply 或 ZBid 写回。

## 5. 必须继续禁止

20 人本地部署与试运行期间必须继续禁止：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回。
- DOCX 生成。
- `output/job/export` 写入。
- preview-only 结果作为 evidence。
- preview-only 结果作为评分依据。

同时继续禁止：

- 未授权的服务启动。
- 未授权的端口访问。
- 未授权的 endpoint 调用。
- 未授权的真实业务联调。
- 未授权的 50 人正式部署设计。
- 未授权的顶级本地模型升级实施。

## 6. 授权后拟进入下一步

授权后拟进入的下一步为：

- Step 245 可作为 20-user local deployment and pilot-run controlled execution。
- Step 245 必须由用户明确授权。
- Step 245 才允许启动服务、访问端口和按试运行边界执行。

Step 245 不得默认修改代码，不得默认开放正式链，不得默认生成 DOCX，不得默认写 `output/job/export`，不得默认进入 50 人正式部署设计，不得默认启动顶级模型升级实施。

## 7. Step 245 授权语建议

用户如需授权 Step 245，可复制并补全以下授权语：

> 我授权执行 Step 245：ZDoc-ZBid 20-user local deployment and pilot-run controlled execution。ZDoc 仓库限定为 `/Users/youfeini/Desktop/文档生成系统`，分支限定为 `main`，开始前 HEAD 必须由本次授权明确填写并在执行前核验；ZBid 仓库限定为 `/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`，分支限定为 `local-llm-integration-clean`，开始前 HEAD 必须由本次授权明确填写并在执行前核验。本步限定为 20 人场景本地化部署与试运行，数据范围限定为脱敏样例、测试文档、非正式成果；允许启动明确列出的必要本地服务，访问明确列出的必要本地端口，调用明确列出的 preview-only endpoint；全程保持 preview-only / no-write / no-evidence；不得开放 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回；不得生成 DOCX；不得写 `output/job/export`；不得将 preview-only 结果作为 evidence 或评分依据；不得进入 50 人正式部署设计；不得启动顶级本地大模型升级实施。

执行 Step 245 前仍需用户给出完整授权信息，包括：

- ZDoc 开始前 HEAD。
- ZBid 开始前 HEAD。
- 允许启动的服务。
- 允许访问的端口。
- 允许调用的 endpoint。
- 20 人场景试运行角色范围。
- 试运行数据范围。
- 日志、问题清单和回退记录保存范围。
- 停止条件。

## 8. 结论

当前最合理的下一步是等待用户审阅本授权请求文档。

在用户明确授权前，不得启动 20 人本地部署与试运行，不得启动服务，不得访问端口，不得调用 endpoint，不得访问 ZBid 仓库，不得修改代码，不得开放正式链，不得生成 DOCX，不得写 `output/job/export`，不得进入 50 人正式部署设计，不得启动顶级本地模型升级实施。
