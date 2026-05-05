# ZBid to ZDoc Mock Mapper Helper Design

## 1. 阶段定位

本文件用于定义 ZBid 输入快照到 ZDoc draft-only input 的 mock-only mapper/helper 设计边界。当前阶段只做文档设计，为后续代码实现提供字段映射、禁止能力和验收约束。

本阶段不创建 mapper/helper 代码，不创建测试文件，不新增 API，不接前端，不启动服务，不连接 Ollama，不触发生成链、导出链、job/build/output/result bundle。

## 2. 当前基线

- 当前 `main` 基线 commit: `1817023 docs: design ZBid input snapshot schema`.
- 当前稳定标签: `v0.1.33-zbid-input-snapshot-schema-design`.
- 已完成 ZBid 输入快照 schema 设计。
- 已完成 ZBid / ZDoc 接入前置设计。
- ZDoc 当前稳定边界仍是 draft-only preview 和正式写回治理设计。
- 当前未开放 ZBid 到正式成果链路的直接接入。

## 3. mapper/helper 设计目标

mapper/helper 的目标是把 ZBid 输入快照转换为 ZDoc 可理解的 draft-only input 结构，并在转换前拒绝高风险字段或不完整输入。

设计目标:

- 只做结构映射，不做真实生成。
- 只返回内存中的 draft-only input 或结构化错误。
- 保留项目、章节、评分项、素材、hash 和 audit context。
- 明确拒绝正式写回、export、job/result bundle 写入和自动 apply 语义。
- 为后续 deterministic tests 提供稳定输入输出。

mapper/helper 不负责:

- 调用 Ollama。
- 调用 LLMClient。
- 调用 `/actions/generate_async`。
- 调用 `/actions/review/apply`。
- 创建或更新 job。
- 写 build/output/result bundle。
- 触发 DOCX/XLSX/PPTX/HTML export。
- 执行正式 apply 或绕过人工确认。

## 4. 输入来源

输入来源应为 `docs/zbid-input-snapshot-schema-design.md` 中定义的 ZBid 输入快照结构。

允许读取的逻辑字段:

- `snapshot_meta`
- `project`
- `lot`
- `tender`
- `section_tasks`
- `technical_materials`
- `review_context`
- `version_hashes`
- `safety_boundary`

输入必须是调用方传入的内存对象。mock-only helper 不应从 job、build、output、result bundle、导出目录或外部服务读取补充数据。

## 5. 输出目标

输出目标是 ZDoc draft-only input 的中间结构，用于后续 section draft build 或 mock-only tests。

建议输出逻辑字段:

- `draft_type`: 固定为 `section_draft_input`。
- `source_type`: 固定为 `zbid_snapshot`.
- `project_context`: 项目、标段和招标上下文摘要。
- `section_inputs`: 章节级 draft-only 输入列表。
- `material_context`: 与章节相关的素材摘录。
- `scoring_context`: 与章节相关的评分项上下文。
- `audit_context`: 快照 ID、来源、版本、hash、请求人和时间。
- `safety_boundary`: no-write、no-export、no-job-update 等边界声明。

输出不得包含正式写回目标、export 目标、job 更新目标、result bundle 写入目标或 apply 指令。

## 6. 字段映射规则

项目上下文映射:

- `project.project_id` -> `project_context.project_id`
- `project.project_name` -> `project_context.project_name`
- `project.project_code` -> `project_context.project_code`
- `project.owner_name` -> `project_context.owner_name`
- `project.bidder_name` -> `project_context.bidder_name`
- `lot.lot_id` -> `project_context.lot_id`
- `lot.lot_name` -> `project_context.lot_name`
- `lot.scope_summary` -> `project_context.scope_summary`
- `lot.planned_duration_days` -> `project_context.planned_duration_days`
- `lot.quality_target` -> `project_context.quality_target`
- `lot.safety_target` -> `project_context.safety_target`

章节输入映射:

- `section_tasks[].section_id` -> `section_inputs[].section_id`
- `section_tasks[].section_title` -> `section_inputs[].section_title`
- `section_tasks[].section_order` -> `section_inputs[].section_order`
- `section_tasks[].original_text` -> `section_inputs[].original`
- `section_tasks[].section_requirements` -> `section_inputs[].requirements`
- `section_tasks[].draft_instruction` -> `section_inputs[].draft_instruction`
- `section_tasks[].target_length` -> `section_inputs[].target_length`

评分项映射:

- `section_tasks[].related_scoring_item_ids` 用于从 `tender.scoring_items` 中选择相关评分项。
- 相关评分项进入 `section_inputs[].scoring_context`。
- 评分项中的 `requirement_text` 和 `evidence_needed` 只作为草稿上下文，不作为自动验收或正式成果状态。

素材映射:

- `section_tasks[].related_material_ids` 用于从 `technical_materials` 中选择相关素材。
- 仅当 `usable_for_draft=true` 且 `sensitive=false` 时，素材可进入 `section_inputs[].material_context`。
- `content_excerpt` 可作为 draft-only 上下文。
- `source_ref`、`source_version` 和 `confidence` 应进入 audit 或 material metadata。

审计与 hash 映射:

- `snapshot_meta.snapshot_id` -> `audit_context.snapshot_id`
- `snapshot_meta.source_system` -> `audit_context.source_system`
- `snapshot_meta.schema_version` -> `audit_context.schema_version`
- `snapshot_meta.snapshot_created_at` -> `audit_context.snapshot_created_at`
- `snapshot_meta.requested_by` -> `audit_context.requested_by`
- `version_hashes.snapshot_hash` -> `audit_context.snapshot_hash`
- `version_hashes.section_original_hash` -> `section_inputs[].original_hash`
- `version_hashes.prompt_input_hash` -> `audit_context.prompt_input_hash`

安全边界映射:

- `safety_boundary.mode` 必须保持为 draft-only 语义。
- `safety_boundary.write_policy=no_write` 必须进入输出。
- `safety_boundary.export_policy=no_export` 必须进入输出。
- `safety_boundary.job_policy=no_job_update` 必须进入输出。

## 7. 不映射字段清单

mapper/helper 不得映射以下字段或语义:

- 正文正式写回指令。
- export 触发字段。
- job/result bundle 写入字段。
- build/output 写入字段。
- 自动 apply 或 confirmed apply 字段。
- 绕过人工确认的字段。
- `/actions/generate_async` 触发字段。
- `/actions/review/apply` 触发字段。
- DOCX/XLSX/PPTX/HTML 自动导出字段。
- 自动覆盖章节正文的字段。
- 自动更新 `run_result` 的字段。
- 自动创建或更新 job 的字段。
- 自动标记为正式交付成果的字段。
- 敏感凭证、账号、密钥或未经脱敏的私密资料。

如果输入中出现上述字段或等价语义，后续实现应返回结构化错误，不应静默忽略后继续生成可用输出。

## 8. mock-only 约束

mapper/helper 只能 mock-only。

必须满足:

- 纯函数式输入输出优先。
- 不读取本地 job/build/output/result bundle。
- 不写任何本地文件。
- 不连接网络服务。
- 不调用 Ollama。
- 不调用 LLMClient。
- 不调用 run_autoplan。
- 不调用 create_job 或 update_job。
- 不调用 `_save_outputs` 或 `save_output_artifacts`。
- 不触发 export/docx/xlsx/pptx/html。
- 不执行正式 apply。
- 不绕过人工确认。

mock-only helper 的唯一副作用应为无副作用返回数据结构。任何写盘能力都必须在后续单独设计、单独 PR、单独验收。

## 9. deterministic test 设计思路

后续实现必须先从 deterministic tests 开始。

建议测试覆盖:

- 有效快照能映射为稳定 draft-only input。
- 缺少 `snapshot_id` 时返回结构化错误。
- 缺少 `project_id` 或 `project_name` 时返回结构化错误。
- 章节任务为空时返回结构化错误。
- 章节缺少 `section_id` 或 `section_title` 时返回结构化错误。
- 关联评分项 ID 不存在时返回结构化错误或明确 warning。
- 关联素材 ID 不存在时返回结构化错误或明确 warning。
- `usable_for_draft=false` 的素材不进入输出。
- `sensitive=true` 的素材不进入输出。
- 出现正式写回字段时拒绝。
- 出现 export 字段时拒绝。
- 出现 job/result bundle 写入字段时拒绝。
- 出现 auto apply 或绕过人工确认字段时拒绝。
- 输出不包含生成、写盘、导出或正式 apply 目标。

测试应只使用内存样例，不启动服务，不连接 Ollama，不运行真实生成，不写 job/build/output/result bundle。

## 10. 与 ZDoc section draft build 的关系

mapper/helper 的输出可以作为后续 ZDoc section draft build 的输入来源之一，但不能直接接入 API 或前端。

建议关系:

- mapper/helper 负责 ZBid snapshot -> ZDoc draft-only input。
- section draft build 负责 draft-only preview 结构构建。
- decision API 负责 apply_preview / reject / rollback preview 状态。
- formal write-back 仍必须由独立治理机制控制。

第一阶段不得把 mapper/helper 直接接到:

- `/actions/generate_async`
- `/actions/review/apply`
- job 创建或更新链路
- result bundle 写入链路
- build/output 写入链路
- export/docx/xlsx/pptx/html 链路

## 11. 不接入 API / 前端 / Ollama 的边界

本阶段只设计 mock-only helper，不接入 API、前端或 Ollama。

明确禁止:

- 新增 ZBid API bridge。
- 修改现有 ZDoc API。
- 修改 Streamlit 前端。
- 新增按钮、页面或 session state。
- 调用 Ollama。
- 调用 `/actions/generate_async`。
- 调用 `/actions/review/apply`。
- 触发正式 apply。
- 写 job/result bundle。
- 触发 export。

后续如果需要接 API 或前端，必须先完成 helper-only PR 和 deterministic tests，再单独设计默认关闭的 API bridge。

## 12. 风险清单与控制措施

风险: mapper/helper 被误用为正式生成入口。

- 控制: 输出必须标记 draft-only，且不得包含生成或 apply 触发字段。

风险: ZBid 业务审核被误认为 ZDoc 正式写回确认。

- 控制: `review_context` 只作为业务上下文，不映射为 confirmed apply。

风险: 敏感素材进入模型上下文。

- 控制: `sensitive=true` 或未脱敏素材不得进入 `material_context`。

风险: 输入快照与当前章节正文冲突。

- 控制: 保留 `section_original_hash`，后续接写盘前必须做冲突检测。

风险: 一次实现同时接 mapper、API、UI、生成和 export。

- 控制: 后续 PR 必须按 helper、tests、API、UI、persist、export 拆分。

风险: 禁止字段被静默忽略。

- 控制: 后续 helper 应对禁止字段返回结构化错误，测试必须覆盖。

## 13. 后续实现拆分建议

建议拆分顺序:

1. docs-only mock mapper/helper 设计。
2. helper-only 实现，默认不接 API。
3. deterministic tests，覆盖正常映射和禁止字段拒绝。
4. 只读验收，确认 job/build/output 文件数不变。
5. 默认关闭的 draft-only API bridge 设计。
6. API bridge 实现与测试。
7. 前端只读展示设计。
8. formal apply / persist / result bundle / export 专项设计。

不建议在同一 PR 内同时实现 helper、API、前端、正式写回和导出。

## 14. Codex 后续执行约束

后续 Codex 执行 ZBid / ZDoc mapper/helper 任务时应遵守:

- helper-only 任务只修改 helper 和对应测试。
- docs-only 任务只修改 docs。
- 未经明确授权，不启动服务。
- 未经明确授权，不连接 Ollama。
- 未经明确授权，不运行真实生成。
- 未经明确授权，不触发 `/actions/generate_async`。
- 未经明确授权，不触发 `/actions/review/apply`。
- 未经明确授权，不触发 DOCX/XLSX/PPTX/HTML 导出。
- 未经明确授权，不写 job/build/output/result bundle。
- 未经明确授权，不执行 `git clean/reset/delete/move`。
- 涉及写盘能力时必须先证明文件数量前后一致。
- 涉及 PR 时必须先确认实际变更文件范围。

## 15. 结论

ZBid -> ZDoc mapper/helper 的第一阶段应保持 mock-only、纯内存、无副作用。它只负责把 ZBid 输入快照转换为 ZDoc draft-only input，并拒绝正式写回、导出、job/result bundle、自动 apply 和绕过人工确认等高风险字段。

建议下一步仍先做 helper-only + deterministic tests，不接 API、不接前端、不接 Ollama、不写正式成果链。任何持久化、正式写回、job/result bundle 或 export 能力都必须另行设计和验收。
