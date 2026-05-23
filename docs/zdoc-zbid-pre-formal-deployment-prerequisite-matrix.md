# ZDoc-ZBid pre-formal-deployment prerequisite matrix

## 1. 当前阶段结论

截至本矩阵整理时：

- preview-only 对接闭环已完成。
- small-scale trial 已完成。
- expanded trial 已完成。
- observation docs-only 优化已完成。
- 当前未开放正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply、ZBid 写回。
- 当前未进入 50 人正式部署设计。

本文档只归纳进入正式部署设计前必须满足的前置条件，不代表已经进入 50 人正式部署设计，也不代表正式链开放。

## 2. 前置条件矩阵字段

后续维护正式部署前置条件时，建议统一使用以下字段：

- 序号
- 前置条件
- 所属类别
- 当前状态：已完成 / 部分完成 / 未开始
- 依据文档
- 是否需要单独授权
- 是否涉及代码修改
- 是否涉及服务启动/端口访问
- 是否涉及双仓联动
- 风险点
- 进入正式部署设计前是否必须完成

## 3. 前置条件矩阵

| 序号 | 前置条件 | 所属类别 | 当前状态 | 依据文档 | 是否需要单独授权 | 是否涉及代码修改 | 是否涉及服务启动/端口访问 | 是否涉及双仓联动 | 风险点 | 进入正式部署设计前是否必须完成 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ZDoc preview-only route、前端同源 proxy、动态展示闭环完成 | A. preview-only 功能闭环 | 已完成 | `zdoc-zbid-preview-only-integration-stage-final-consolidation.md`、`zdoc-zbid-preview-only-cross-system-controlled-smoke-stage-review.md` | 否 | 否 | 否 | 否 | 不能误认为正式生成入口已开放 | 是 |
| 2 | ZDoc outbound adapter default-off + network-send 完成 | A. preview-only 功能闭环 | 已完成 | `zdoc-outbound-adapter-preview-only-network-send-code-implementation-stage-review.md` | 否 | 否 | 否 | 否 | network-send 只能显式启用且仅限 preview-only receiver | 是 |
| 3 | ZBid preview-only receiver/helper 与 receiver API 完成 | A. preview-only 功能闭环 | 已完成 | `zdoc-zbid-preview-only-cross-repository-status-consolidation.md`、ZBid receiver stage review 记录 | 否 | 否 | 否 | 是 | 不得接入评分链、证据链、导出链、存储链、写回链 | 是 |
| 4 | cross-system controlled smoke 通过 | A. preview-only 功能闭环 | 已完成 | `zdoc-zbid-preview-only-cross-system-controlled-smoke-report.md`、`zdoc-zbid-preview-only-cross-system-controlled-smoke-stage-review.md` | 否 | 否 | 否 | 是 | 只能证明受控 preview-only 链路成立 | 是 |
| 5 | small-scale trial 通过 | B. 小范围试用与扩大试用验证 | 已完成 | `zdoc-zbid-preview-only-small-scale-trial-controlled-execution-report.md`、`zdoc-zbid-preview-only-small-scale-trial-controlled-execution-stage-review.md` | 否 | 否 | 否 | 是 | 不能作为正式业务联调完成证明 | 是 |
| 6 | expanded trial 通过 | B. 小范围试用与扩大试用验证 | 已完成 | `zdoc-zbid-preview-only-expanded-trial-controlled-execution-report.md`、`zdoc-zbid-preview-only-expanded-trial-controlled-execution-stage-review.md` | 否 | 否 | 否 | 是 | 仍不代表真实业务联调或正式部署准备完成 | 是 |
| 7 | 五个 false flags 稳定为 false | D. 安全边界与禁止链校核 | 已完成 | small-scale trial、expanded trial、cross-system smoke 报告 | 否 | 否 | 否 | 是 | 任一 flag 非 false 都必须停止并复查 | 是 |
| 8 | 未发现正式链误触发 | D. 安全边界与禁止链校核 | 已完成 | small-scale trial final consolidation、expanded trial final consolidation | 否 | 否 | 否 | 是 | 不能据此开放正式链；只是当前试用未发现误触发 | 是 |
| 9 | 未发现 `output/job/export` 写入 | D. 安全边界与禁止链校核 | 已完成 | cross-system smoke、small-scale trial、expanded trial 报告 | 否 | 否 | 否 | 是 | 后续任何服务或 endpoint 调用仍需重新做前后快照 | 是 |
| 10 | 未生成 DOCX | D. 安全边界与禁止链校核 | 已完成 | cross-system smoke、small-scale trial、expanded trial 报告 | 否 | 否 | 否 | 是 | DOCX 导出仍未开放 | 是 |
| 11 | 未触发 ZBid 写回 | D. 安全边界与禁止链校核 | 已完成 | cross-system smoke、small-scale trial、expanded trial 报告 | 否 | 否 | 否 | 是 | ZBid 写回仍未授权、未开放 | 是 |
| 12 | 观察项是否仅为 docs-only 优化，还是仍需代码优化 | C. 观察项与必要优化闭环 | 部分完成 | `zdoc-zbid-preview-only-observation-optimization-implementation-stage-review.md`、`zdoc-zbid-preview-only-expanded-trial-stage-final-consolidation.md` | 是，若进入代码或 UI 优化 | 可能涉及 | 视验证方式而定 | 可能涉及 | 观察项未闭环时不宜进入正式部署设计 | 是 |
| 13 | trial report / smoke report / stage review / final consolidation 交付链形成 | C. 观察项与必要优化闭环 | 已完成 | preview-only integration、small-scale trial、expanded trial 各阶段报告与总归档 | 否 | 否 | 否 | 否 | 交付链是审查资料，不等于正式部署方案 | 是 |
| 14 | 正式部署前是否还需做扩大试用问题修正复验 | C. 观察项与必要优化闭环 | 部分完成 | `zdoc-zbid-preview-only-expanded-trial-stage-final-consolidation.md` | 是 | 可能涉及 | 可能涉及 | 可能涉及 | 必要优化如未复验，会把观察项带入正式部署设计 | 是 |
| 15 | 运维日志策略定义 | E. 运维/日志/回退机制前置要求 | 未开始 | 当前仅有试用报告和日志留痕观察 | 是 | 可能涉及 | 可能涉及 | 可能涉及 | 日志过宽可能记录敏感数据，过窄可能无法排查问题 | 是 |
| 16 | 失败回退机制定义 | E. 运维/日志/回退机制前置要求 | 未开始 | Step 236、Step 237、Step 238 的停止条件记录 | 是 | 可能涉及 | 可能涉及 | 可能涉及 | 未定义回退机制会放大正式部署风险 | 是 |
| 17 | 权限边界定义 | E. 运维/日志/回退机制前置要求 | 未开始 | 扩大试用边界设计与授权请求 | 是 | 可能涉及 | 否 | 可能涉及 | 未定义角色权限会导致正式链误用风险 | 是 |
| 18 | 试用停止条件固化为正式部署前置规则 | E. 运维/日志/回退机制前置要求 | 部分完成 | small-scale trial、expanded trial 的边界设计与报告 | 是，若进入流程或系统约束 | 可能涉及 | 可能涉及 | 可能涉及 | 停止条件只在文档中存在时，执行一致性不足 | 是 |
| 19 | 正式链开放条件定义 | F. 正式部署设计启动条件 | 未开始 | 当前所有阶段均声明正式链未开放 | 是 | 可能涉及 | 可能涉及 | 可能涉及 | 未定义开放条件时不得设计正式部署 | 是 |
| 20 | 正式部署设计授权请求 | F. 正式部署设计启动条件 | 未开始 | 本矩阵之后可另行起草 | 是 | 否 | 否 | 可能涉及 | 授权请求不得被误认为正式部署设计已启动 | 是 |

## 4. 尚未完成且阻止直接进入 50 人正式部署设计的事项

以下事项尚未完成，因而不能直接进入 50 人正式部署设计：

- 正式链仍未开放。
- 正式 evidence 仍未开放。
- 评分依据写入仍未开放。
- DOCX 导出仍未开放。
- review/apply 仍未开放。
- ZBid 写回仍未开放。
- 任何必要优化如需代码变更，仍需单独授权与复验。
- 正式部署前的运维、回退、日志、权限边界尚未形成正式方案。

expanded trial 通过只能说明 preview-only / no-write / no-evidence 链路在受控范围内完成验证，不得替代正式部署设计前置条件。

## 5. 继续禁止事项

在后续获得明确授权前，继续禁止：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回。
- DOCX 生成。
- `output/job/export` 写入。
- preview-only 结果作为 evidence。
- preview-only 结果作为评分依据。
- 未授权的服务启动、端口访问、endpoint 调用。
- 未授权的正式部署设计启动。

## 6. 结论建议

当前最合理的后续工作不是直接做 50 人正式部署设计。

建议先根据本矩阵补齐仍需完成的前置条件：

- 明确观察项是否需要代码、UI、日志或流程优化。
- 对任何必要优化进行单独授权、实施与复验。
- 定义正式部署前的运维日志、失败回退、权限边界和停止条件。
- 明确正式链开放条件、回退条件、审计策略和责任边界。

前置条件补齐、必要优化完成并复验后，才应单独申请正式部署设计授权。

本文档不授权正式部署设计，不授权正式链开放，不授权服务启动、端口访问、endpoint 调用、代码修改、ZBid 写回或 DOCX 生成。
