# ZDoc-ZBid preview-only expanded trial stage final consolidation

## 1. 阶段定位

本文件归档 ZDoc-ZBid preview-only 扩大试用阶段总成果，形成阶段闭环说明。

当前阶段定位如下：

- preview-only 对接闭环已完成。
- small-scale trial 已完成。
- expanded trial 已完成。
- 当前仅验证 preview-only / no-write / no-evidence 链路。
- 当前未开放正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply、ZBid 写回。
- 当前未进入 50 人正式部署设计。

本文档不代表进入正式生成链，不代表进入真实业务联调，不代表进入 50 人正式部署设计。

## 2. 当前 ZDoc 基线

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 当前 HEAD：`f2045c1cbba9fc9b05310a22d8c31b87df4f7fdc`

ZDoc 当前已完成：

- preview-only route。
- 前端同源 proxy。
- 前端动态展示。
- outbound adapter。
- preview-only network-send。
- cross-system smoke。
- small-scale trial。
- expanded trial。
- 观察项 docs 优化。
- 交付包整理。

## 3. 当前 ZBid 基线

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 扩大试用阶段 ZBid HEAD 保持：`378355755372e03ac4f4064af59b287054984c25`

ZBid 当前已完成：

- preview-only receiver/helper。
- receiver API 暴露。
- receiver API runtime smoke。

扩大试用阶段 ZBid 未 commit、未 tag、未 push。

## 4. expanded trial 结果

Step 238 已完成 5 个代表性角色 payload 验证。

执行结果：

- ZDoc outbound adapter 成功发送 preview-only payload。
- ZBid receiver endpoint 返回 HTTP 200。
- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `preview_packet` 可读。
- `validator_result` 可读。
- `blocked_reasons` 可读。
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`
- 错误提示、blocked_reasons 可读性、日志留痕完整性、人工复核流程体验已记录。
- 两侧 `output/job/export` 前后快照均为空。
- 未生成 DOCX。
- 未触发正式链。

5 个代表性角色 payload 覆盖：

- 技术标编制。
- 复核。
- 项目负责人。
- 质控审核。
- 备用综合角色。

## 5. 阶段问题与观察结论

当前阶段结论：

- 当前未发现阻断 preview-only 链路的问题。
- 当前未发现正式链误触发、写回、DOCX、evidence、评分依据写入。
- 观察项仍仅作为后续优化候选，不代表已授权代码修复。
- 任何后续优化都必须单独授权。

仍需持续观察的方向包括：

- 错误提示清晰度。
- `blocked_reasons` 可读性。
- preview-only / no-write / no-evidence 状态醒目性。
- 五个 false flags 对试用人员的可理解性。
- 日志留痕完整性。
- 人工复核检查表落地程度。

上述观察项不得被解释为当前已授权修复事项。

## 6. 严格未开放边界

当前仍严格未开放：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回。
- 正式 evidence。
- 评分依据写入。
- DOCX 生成。
- `output/job/export` 写入。
- 真实业务联调。
- 正式生成链。
- 50 人正式部署设计。

preview-only 结果、validator_result、blocked_reasons、日志摘要、人工复核记录和 trial report 均不得作为正式 evidence 或评分依据。

## 7. 进入正式部署前仍需满足的前置条件

进入正式部署设计前，仍需满足以下前置条件：

- preview-only 观察项如需优化，需完成单独授权、实施与复验。
- 如需扩大到更广范围使用，需先完成扩大试用总结与边界确认。
- 必须继续保持 no-write / no-evidence 边界校核。
- 必须明确正式链开放条件、回退条件、日志策略、失败停止条件。
- 正式部署设计必须在试用闭环、问题收敛和必要修正完成后再启动。

正式部署前置条件不得用 expanded trial 成功结果直接替代。expanded trial 只证明 preview-only / no-write / no-evidence 链路在本地受控范围内可用。

## 8. 后续建议

建议后续可选方向：

- Step 241 可做“进入正式部署前置条件矩阵”。
- 或做“扩大试用阶段总交付包补充索引”。

50 人正式部署设计仍不得直接启动。

任何后续代码优化、UI / 文案优化、日志增强、服务启动、端口访问、endpoint 调用、更大范围试用、真实业务联调或正式部署设计，均必须另行授权。
