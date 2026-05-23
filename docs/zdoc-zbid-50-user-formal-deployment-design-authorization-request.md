# ZDoc-ZBid 50-user formal deployment design authorization request

## 1. 授权请求来源

本文档用于起草“约 50 人同时使用场景”的正式部署设计授权请求，只代表申请授权，不代表已进入正式部署设计，不代表已开放正式链。

授权请求来源如下：

- preview-only 对接闭环已完成。
- small-scale trial 已完成。
- expanded trial 已完成。
- pre-formal-deployment prerequisite matrix 已完成。
- 当前仅具备进入“正式部署设计文档编制”的前置条件。
- 当前仍未开放正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply、ZBid 写回。

当前已验证能力边界仍是 preview-only / no-write / no-evidence。正式部署设计授权请求不得被理解为正式链开放授权。

## 2. 本次拟申请的范围

本次拟申请的范围仅限：

- “正式部署设计”文档编制。
- 面向约 50 人同时使用场景。
- 只做设计，不实施部署。
- 不修改代码。
- 不启动服务。
- 不访问端口。
- 不调用 endpoint。
- 不进入正式链。
- 不进入写回链。

本文档不授权实施部署、变更系统配置、扩容硬件、启动服务、访问端口、调用 endpoint、开放正式链或写回链。

## 3. 正式部署设计应覆盖的内容范围

如后续 Step 243 获得用户明确授权，正式部署设计文档可覆盖以下范围：

- 约 50 人同时使用场景的容量假设。
- ZDoc 与 ZBid 的部署拓扑建议。
- 服务拆分建议。
- 并发与队列设计建议。
- 硬件配置建议。
- 存储、备份、恢复建议。
- 日志、监控、告警建议。
- 权限与操作边界建议。
- 发布、回退、变更控制建议。
- 运维边界与巡检建议。
- preview-only / no-write / no-evidence 边界下的部署限制说明。

上述范围仅为未来设计文档编制范围，不代表已启动部署设计，不代表可以进入实施。

## 4. 必须明确的边界

未来如进入“正式部署设计”，必须明确：

- 本次“正式部署设计”是设计文档，不是实施。
- 设计对象基于当前已验证能力边界，即 preview-only / no-write / no-evidence。
- 不得因进入部署设计而默认开放 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回。
- 不得默认开放 DOCX 生成、`output/job/export` 写入、正式 evidence、评分依据写入。
- 如未来需要设计正式链开放方案，必须另行单独授权。

正式部署设计不得绕过 preview-only 阶段形成的 no-write / no-evidence 边界，也不得将 preview-only 结果作为正式 evidence 或评分依据。

## 5. 必须继续禁止

在用户明确授权正式部署设计文档编制前，以及在正式部署设计文档编制过程中，仍必须继续禁止：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回。
- DOCX 生成。
- `output/job/export` 写入。
- preview-only 结果作为 evidence。
- preview-only 结果作为评分依据。
- 未授权的服务启动、端口访问、endpoint 调用。
- 未授权的真实业务联调。

如后续需要讨论正式链开放方案、DOCX 生成方案、ZBid 写回方案、正式 evidence 方案或评分依据写入方案，必须另行单独授权，不能包含在本次授权请求中默认执行。

## 6. 授权后拟进入的下一步

授权后拟进入的下一步为：

- Step 243 可作为“ZDoc-ZBid 50-user formal deployment design”。
- Step 243 必须由用户明确授权。
- Step 243 仅限 docs-only 设计编制。
- Step 243 不得修改代码。
- Step 243 不得启动服务。
- Step 243 不得访问端口。
- Step 243 不得调用 endpoint。

Step 243 的目标应是形成正式部署设计文档，而不是执行部署、启动服务、调整配置、进行压测、开放正式链或进入真实业务联调。

## 7. Step 243 授权语建议

用户如需授权 Step 243，可复制并补全以下授权语：

> 我授权执行 Step 243：ZDoc-ZBid 50-user formal deployment design。ZDoc 仓库限定为 `/Users/youfeini/Desktop/文档生成系统`，分支限定为 `main`，开始前 HEAD 必须由本次授权明确填写并在执行前核验。本步仅限 docs-only 正式部署设计文档编制，面向约 50 人同时使用场景；允许新增指定的正式部署设计文档；不得修改代码、tests、frontend 或既有 docs；不得访问 ZBid 仓库；不得启动服务；不得访问端口；不得调用任何 endpoint；不得开放 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回；不得生成 DOCX；不得写 `output/job/export`；不得将 preview-only 结果作为 evidence 或评分依据；不得进入真实业务联调或执行部署。

执行 Step 243 前仍需用户给出完整授权信息，包括 ZDoc 开始前 HEAD、允许新增文件、是否允许只读引用既有阶段文档，以及明确不得实施部署、不得开放正式链。

## 8. 结论

当前最合理的下一步是等待用户审阅本授权请求文档。

在用户明确授权前，不得进入 Step 243，不得开始 50 人正式部署设计本体，不得修改代码，不得启动服务，不得访问端口，不得调用 endpoint，不得开放正式链，不得生成 DOCX，不得写 `output/job/export`。
