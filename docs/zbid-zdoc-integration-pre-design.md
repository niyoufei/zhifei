# ZBid to ZDoc Integration Pre-design

## 1. 阶段定位

本文件用于在 ZBid / 技术标业务系统接入 ZDoc 之前，先明确职责边界、数据接口、风险控制和推进路线。

当前阶段只做接入前置设计，不修改业务代码，不新增 API，不接前端，不启动服务，不触发生成、导出或写盘链路。ZBid 接入 ZDoc 的第一目标不是直接生成正式成果，而是把业务数据、草稿预览、审核状态和交付边界拆清楚，避免业务系统一接入就进入 job/result bundle/export 等高风险路径。

## 2. 当前 ZDoc 稳定基线

- 当前 `main` 基线 commit: `103c950 docs: add ZDoc v0.1.30 stage review`.
- 当前稳定标签: `v0.1.31-zdoc-stage-review-archive`.
- 当前 ZDoc 已完成从 Ollama sidecar 到 draft-only section draft decision UI 的阶段归档。
- 当前 ZDoc 已有正式写回治理设计，但尚未开放正式写回正文。
- 当前 ZDoc 未开放 ZBid 业务系统到正式成果链路的直接接入。

## 3. ZBid 与 ZDoc 的职责边界

ZBid 侧职责:

- 维护技术标业务项目、投标资料、招标要求、评分点、章节任务、人员协作状态和业务审批状态。
- 决定哪些业务数据可以进入 ZDoc 的文档草稿链路。
- 负责业务权限、项目权限、招投标流程权限和用户身份。
- 负责业务侧项目生命周期，不直接写 ZDoc 的 result bundle。

ZDoc 侧职责:

- 接收经过整理的文档生成输入或草稿输入。
- 生成、展示或审查文档草稿。
- 保持 no-write / draft-only / formal apply 等边界清晰。
- 负责文档结构、章节草稿、审计信息和导出前版本状态。

不应混淆的职责:

- ZBid 不应直接写 ZDoc 的 job/result bundle/export 输出。
- ZDoc 不应直接决定 ZBid 的投标业务状态。
- ZBid 的业务审批不等于 ZDoc 的正式写回确认。
- ZDoc 的 draft-only preview 不等于 ZBid 的最终交付成果。

## 4. 技术标业务数据类型

接入前应先把 ZBid 数据分为以下类型:

- 项目基本信息: 项目名称、招标单位、项目地点、标段、工期、质量目标。
- 招标文件信息: 招标要求、技术规范、评分办法、格式要求、提交要求。
- 企业资质信息: 公司资质、人员资质、业绩、获奖、体系认证。
- 技术方案素材: 施工组织、进度计划、质量安全、环境保护、资源配置、重难点措施。
- 商务与合规约束: 不应直接进入技术标正文生成的敏感或非技术内容。
- 章节结构信息: 章节标题、章节顺序、章节要求、页数约束。
- 审核与决策信息: 审核人、审批状态、确认理由、更新时间。
- 草稿与版本信息: draft content、original hash、draft hash、audit trail、version status。

每类数据都需要标注来源、可信度、是否可用于生成、是否可用于导出、是否需要人工确认。

## 5. 接入前置条件

ZBid 接入 ZDoc 前至少需要满足:

- 明确项目 ID、文档 ID、章节 ID 的映射规则。
- 明确 ZBid 用户身份如何传递给 ZDoc 的 `confirmed_by` 或后续审计字段。
- 明确哪些字段允许进入 draft-only preview。
- 明确哪些字段禁止进入正式正文或导出。
- 明确数据快照机制，避免 ZBid 数据变更后 ZDoc 仍基于旧输入写回。
- 明确冲突检测规则，例如 original hash 与当前章节内容不一致时必须停止。
- 明确默认关闭的 feature flag 策略。
- 明确所有写盘、job 更新、result bundle 写入、export 触发都必须单独设计和验收。

## 6. 数据流设计

推荐先采用单向、只读、草稿级数据流:

1. ZBid 选择项目和章节。
2. ZBid 生成只读输入快照。
3. ZDoc 接收输入快照并构建 draft-only preview。
4. ZDoc 返回 draft、diff、audit、status。
5. ZBid 展示或保存业务侧审核意见，但不写 ZDoc 正式成果。
6. 人工确认后，后续阶段才允许进入 draft store 或 formal apply preview。

第一阶段不建议:

- 从 ZBid 直接创建 ZDoc job。
- 从 ZBid 直接触发 ZDoc generation。
- 从 ZBid 直接触发 DOCX/XLSX/PPTX/HTML export。
- 从 ZBid 直接写 ZDoc result bundle。

## 7. draft-only 接入边界

ZBid 第一阶段只应接入 draft-only 能力:

- 可以请求 ZDoc 构建草稿预览。
- 可以查看 diff preview。
- 可以查看 audit record。
- 可以查看 apply/reject/rollback preview 状态。
- 可以把 ZDoc 返回数据作为业务侧参考。

ZBid 第一阶段不应:

- 触发正式正文写回。
- 修改 ZDoc `run_result`。
- 修改 ZDoc job。
- 写 build/output/result bundle。
- 触发 export。
- 把 preview 结果标记为正式投标成果。

## 8. 禁止接入正式成果链的能力

在没有单独设计、实现和验收前，ZBid 不得接入:

- `/actions/generate_async`.
- `/actions/review/apply`.
- result bundle 写入。
- job 创建或更新。
- build/output 写入。
- DOCX/XLSX/PPTX/HTML 自动导出。
- 无 audit 的正文写回。
- 无人工确认的正文写回。
- 自动覆盖章节正文。
- 自动将 draft 标记为正式交付稿。

## 9. 风险清单与控制措施

风险: ZBid 业务确认被误认为 ZDoc 正式写回确认。

- 控制: 两类确认必须分离，ZDoc formal apply 必须有独立二次确认和 audit。

风险: ZBid 输入变更后，ZDoc 基于旧 original hash 写回。

- 控制: 引入 original hash / draft hash / current hash 冲突检查。

风险: ZBid 直接触发生成或导出，绕过 ZDoc no-write 边界。

- 控制: 第一阶段禁止接入 generate/export/action apply，所有能力 default-off。

风险: 草稿预览被当作正式成果。

- 控制: UI 和 API status 必须明确 draft-only / preview-only。

风险: 审计链断裂。

- 控制: 所有 draft decision 和 future apply 都必须携带 audit trail、confirmed_by、confirmed_at 和 reason。

风险: 一次 PR 同时接入业务、生成、写回和导出。

- 控制: 按 helper、API、UI、persist、job/result、export 拆分阶段和 PR。

## 10. 分阶段推进路线

Phase 1: docs-only 接入前置设计。

- 只记录职责边界、数据类型、风险和路线。
- 不改代码。

Phase 2: ZBid 输入快照 schema 设计。

- 定义项目、章节、评分点、素材和审计字段。
- 不接生成链。

Phase 3: mock-only mapper/helper。

- 将 ZBid 输入快照转换为 ZDoc draft input。
- 使用 deterministic tests。
- 不写 job/build/output。

Phase 4: draft-only API bridge，默认关闭。

- 仅允许 draft preview。
- 不接 `/actions/generate_async`。
- 不接 export。

Phase 5: ZBid 侧展示草稿状态。

- 只展示 ZDoc draft/diff/audit/status。
- 不允许标记为正式交付成果。

Phase 6: draft store 或正式写回前治理专项。

- 仅在正式治理设计被拆解并验证后推进。
- 不与 export 同 PR。

Phase 7: export 前版本选择。

- 用户必须选择正式正文或草稿正文。
- export 仍由用户单独触发。

## 11. Codex 后续执行约束

- 未经明确授权，不启动服务。
- 未经明确授权，不连接 Ollama。
- 未经明确授权，不运行真实生成。
- 未经明确授权，不触发 `/actions/generate_async`。
- 未经明确授权，不触发 DOCX/XLSX/PPTX/HTML 导出。
- 未经明确授权，不写 job/build/output/result bundle。
- 未经明确授权，不执行 `git clean/reset/delete/move`。
- docs-only 任务只修改 docs 文件。
- ZBid 接入任务默认先做 schema 或设计，不直接接正式成果链。
- 每个 PR 必须先确认实际变更文件范围。
- 涉及写盘能力时必须先证明 job/build/output 文件数不变。

## 12. 结论

ZBid 接入 ZDoc 前应先完成业务数据边界、输入快照、draft-only 接入和审计语义设计。当前 ZDoc 的稳定边界是 draft-only preview 和 formal write-back governance design，尚未开放正式正文写回、job/result bundle 写入或 export 联动。

建议下一步只推进 ZBid 输入快照 schema 设计或 mock-only mapper/helper，不接前端、不接生成链、不写正式成果、不触发导出。
