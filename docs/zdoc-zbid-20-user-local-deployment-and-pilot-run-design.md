# ZDoc-ZBid 20-user local deployment and pilot-run design

## 1. 当前推进口径调整

本阶段推进口径调整为：

- 当前阶段按约 20 人团队使用进行本地化部署与接入设计。
- 先完成 ZDoc 与 ZBid 的本地化部署接入。
- 先试运行、先修正、先闭环。
- ChatGPT 作为系统顶级补充与总控。
- 试运行成功后，再进入扩大人员规模设计与部署。
- 更先进本地大模型升级属于后续阶段。

该路径替代当前直接进入 50 人正式部署设计的路径。当前重点不是一步到位做 50 人正式部署，而是让约 20 人场景先在本地可用、流程可控、问题可收敛。

## 2. 当前阶段定位

当前阶段是“20 人场景的本地部署 + 试运行设计”。

当前阶段不是：

- 不是 50 人正式部署设计。
- 不是正式链开放。
- 不是正式业务联调开放。
- 不是最终模型升级实施。

当前阶段应优先解决：

- 本地可用。
- 流程闭环。
- 试运行稳定。
- 问题可记录、可修正、可复验。
- ChatGPT 总控与本地系统协作边界清晰。

## 3. 20 人场景的部署目标与范围

20 人场景的部署目标：

- 支撑内部约 20 人团队进行受控本地试运行。
- 让 ZDoc 与 ZBid 在本地部署环境中完成 preview-only 接入。
- 验证人员、流程、数据、权限、日志、问题反馈与复盘机制是否可运行。
- 在不开放正式链的前提下，确认系统能服务真实团队流程的前置环节。

范围限制：

- 仅设计部署与试运行方案。
- 不在本步实施部署。
- 不修改代码。
- 不启动服务。
- 不访问端口。
- 不调用 endpoint。
- 不开放正式生成、DOCX 导出、review/apply、ZBid 写回。

## 4. ZDoc / ZBid 本地部署拓扑建议

建议采用本地局域网内受控部署拓扑：

- ZDoc 作为文档生成系统侧入口，负责 preview-only 数据构造、前端展示、outbound adapter 与试运行报告归档。
- ZBid 作为投标业务系统侧 preview-only receiver/display，负责接收 ZDoc preview-only payload 并呈现 metadata-only 结果。
- ChatGPT 作为系统顶级补充与总控，负责跨系统流程解释、人工复核建议、问题归纳、试运行复盘和下一步授权边界整理。

建议拓扑边界：

- ZDoc 与 ZBid 服务均部署在内部受控主机或本地服务器上。
- ZDoc -> ZBid 仅允许 preview-only receiver 链路。
- 不暴露正式生成、正式导出、正式写回 endpoint。
- 不把 preview-only 链路接入正式 evidence、评分依据或正式业务写入。

## 5. 服务角色划分

建议服务角色划分如下：

- ZDoc frontend：仅展示 preview-only metadata、preview_packet、validator_result、blocked_reasons 和 no-write flags。
- ZDoc backend：保留 preview-only route、outbound adapter、network-send 的 default-off / explicit-enable 边界。
- ZBid receiver API：仅接收 preview-only payload，保持 no-write / no-evidence。
- ZBid display/helper：仅展示或记录 preview-only 结果，不接入评分、证据、导出、存储、写回链。
- ChatGPT：作为顶级补充与总控，不直接替代系统权限边界，不直接授权正式链操作。

## 6. preview-only / no-write / no-evidence 边界保持方式

试运行阶段必须保持：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

保持方式：

- 所有试运行入口必须标注 preview-only。
- 所有 ZDoc -> ZBid payload 只能包含 preview_packet、validator_result、blocked_reasons 和 no-write / no-formal-chain flags。
- 不得将 advisory、preview、shadow、patch、diff、rollback、dry-run 作为 evidence。
- 不得将 preview-only 结果作为评分依据。
- 任一 false flag 非 false 时立即停止试运行并记录。

## 7. 试运行人员角色建议

20 人场景可按角色组织，不必在设计阶段绑定真实个人：

- 技术标编制人员：验证 preview_packet 是否能辅助理解文档结构与风险提示。
- 复核人员：验证 validator_result 与 blocked_reasons 是否便于人工复核。
- 项目负责人：验证流程状态、停止条件和上报机制是否清晰。
- 质控审核角色：验证 no-write / no-evidence / 禁止链边界是否清晰。
- 系统管理员或运维角色：验证日志、启动、停止、故障记录和回退流程。
- ChatGPT 总控使用者：负责问题归纳、复盘摘要、授权边界整理和下一步建议。

## 8. 试运行数据范围

试运行数据必须限定为：

- 脱敏样例。
- 测试文档。
- 非正式投标成果。

禁止使用：

- 真实敏感业务数据。
- 正式投标成果。
- 正式 evidence。
- 正式评分依据。
- DOCX 正式成果。
- writeback 数据。

## 9. ChatGPT 作为总控与顶级补充的角色定位

ChatGPT 在本阶段的角色是系统顶级补充与总控：

- 解释 ZDoc 与 ZBid preview-only 结果。
- 协助试运行人员理解 blocked_reasons。
- 协助整理错误提示、人工复核意见和问题清单。
- 协助归纳试运行复盘。
- 协助起草后续授权请求和边界设计。

ChatGPT 不应：

- 绕过系统权限边界。
- 授权正式链开放。
- 替代人工审批。
- 将 preview-only 结果转为 evidence。
- 将 preview-only 结果转为评分依据。
- 直接触发生成、导出、review/apply 或写回。

## 10. 日志、问题反馈、试运行复盘机制

日志建议记录：

- 试运行时间。
- 操作角色。
- 操作入口。
- 请求类型。
- preview-only / no-write / no-evidence 状态。
- 五个 false flags 状态。
- blocked_reasons。
- 错误提示。
- 人工复核结论。
- 是否触发停止条件。

日志禁止记录：

- 敏感业务数据。
- 正式 evidence。
- 正式评分依据。
- 正式业务写回结果。

问题反馈机制：

- 每次试运行形成 issue list。
- 每个问题标记为提示类、流程类、权限边界类、日志类、部署运维类或需代码优化类。
- 需代码优化的问题必须单独授权。
- 修正后必须单独复验。

试运行复盘机制：

- 每轮试运行后形成 pilot-run report。
- 汇总通过项、失败项、停止项、人工复核意见、后续授权需求。
- ChatGPT 可辅助生成复盘草稿，但不能替代系统事实记录。

## 11. 停止条件与失败回退机制

出现以下任一情况，必须立即停止：

- 任一正式链 flag 非 false。
- 出现 `/generate` 调用。
- 出现 `/export_docx` 调用。
- 出现 `/review/apply` 调用。
- 出现 ZBid 写回。
- 出现 DOCX 生成。
- 出现 `output/job/export` 写入。
- 出现 evidence 写入。
- 出现评分依据写入。
- 出现未知 endpoint 调用。
- 出现 fallback 到正式接口。

失败回退机制：

- 停止本轮试运行。
- 保留问题记录和日志摘要。
- 不现场修复失败项。
- 不扩大试用范围。
- 不进入正式链。
- 需要修正时另行起草授权请求。
- 修正完成后另行执行复验。

## 12. 进入扩大规模设计前必须满足的条件

进入扩大规模设计前必须满足：

- 20 人场景本地部署设计已完成。
- 20 人场景试运行已明确授权并完成。
- 试运行报告、问题清单、stage review、final consolidation 已形成。
- 未发现正式链误触发、DOCX、ZBid 写回、evidence、评分依据写入。
- 观察项和必要优化已完成单独授权、实施与复验。
- 运维日志、权限边界、失败回退、停止条件已形成稳定方案。
- ChatGPT 总控与系统权限边界已明确。

不满足上述条件前，不应进入 50 人正式部署设计。

## 13. 后续先进模型升级的触发条件与前置要求

更先进本地大模型升级属于后续阶段。

触发条件建议：

- 20 人试运行完成并稳定。
- 主要流程问题已修正并复验。
- 当前模型能力瓶颈被明确记录。
- 升级目标、成本、硬件需求、响应时间、稳定性和安全边界已评估。
- 升级不会破坏 preview-only / no-write / no-evidence 边界。

前置要求：

- 先完成当前本地部署与试运行闭环。
- 先明确模型升级是否只影响建议质量，还是会影响正式链。
- 先形成模型升级授权请求。
- 不得在本阶段直接实施模型升级。

## 14. 必须明确的当前禁止项

当前不得默认开放：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回。
- DOCX 生成。
- `output/job/export` 写入。
- 正式 evidence。
- 评分依据写入。
- 真实业务联调。
- 50 人正式部署设计本体。

## 15. 后续建议

- Step 244 可起草“20-user local deployment and pilot-run authorization request”。
- 只有在用户明确授权后，才可进入 20 人本地部署/试运行相关下一步。
- 50 人正式部署设计保留为后续专题，不在当前执行。

本设计文档不授权部署实施，不授权服务启动，不授权端口访问，不授权 endpoint 调用，不授权代码修改，不授权正式链开放。
