# ZBid Input Snapshot Schema Design

## 1. 阶段定位

本文件用于定义 ZBid / 技术标业务系统接入 ZDoc 前的输入快照 schema 边界。当前阶段只做字段设计和风险边界确认，为后续 mock-only mapper/helper 提供依据。

本文件不包含实现代码，不新增 API，不接前端，不触发生成链，不写 job/build/output/result bundle，不触发 DOCX/XLSX/PPTX/HTML 导出。

## 2. 当前基线

- 当前 `main` 基线 commit: `331b603 docs: design ZBid ZDoc integration pre-plan`.
- 当前稳定标签: `v0.1.32-zbid-zdoc-integration-pre-design`.
- 当前 ZDoc 稳定边界仍是 draft-only preview 和正式写回治理设计。
- 当前未开放 ZBid 到正式成果链路的直接接入。
- 当前未开放正式正文写回、job 更新、result bundle 写入或 export 联动。

## 3. schema 设计目标

ZBid 输入快照 schema 的目标是把业务输入整理成稳定、可审计、可 hash、可映射到 ZDoc draft-only input 的只读数据结构。

该 schema 应满足:

- 能表达项目、标段、招标要求、评分项、章节任务和技术素材。
- 能记录输入来源、版本、hash 和审核状态。
- 能支持后续 deterministic mock mapper/helper 测试。
- 能明确区分业务确认、草稿预览和正式写回。
- 默认不携带任何写盘、导出、正式 apply 或生成触发指令。

## 4. 输入快照总结构

建议总结构按以下逻辑分组:

- `snapshot_meta`: 快照 ID、来源系统、创建时间、创建人、schema 版本。
- `project`: 项目级字段。
- `lot`: 标段与工期字段。
- `tender`: 招标文件、技术要求和评分项字段。
- `section_tasks`: 章节任务字段。
- `technical_materials`: 技术素材字段。
- `review_context`: 审核与决策字段。
- `version_hashes`: 版本与 hash 字段。
- `safety_boundary`: 安全边界字段。

第一阶段不要求该结构直接成为 API 入参。它仅作为后续 mock-only mapper/helper 的设计输入。

## 5. 项目级字段

建议字段:

- `project_id`: ZBid 侧项目 ID。
- `project_name`: 项目名称。
- `project_code`: 项目编号或内部编号。
- `owner_name`: 招标人或建设单位名称。
- `agency_name`: 招标代理机构名称。
- `bidder_name`: 投标单位名称。
- `project_location`: 项目地点。
- `document_type`: 文档类型，例如技术标。
- `business_stage`: 业务阶段，例如素材整理、草稿预览、人工审核。
- `source_system`: 来源系统，固定为 ZBid 或业务侧系统标识。

项目级字段只用于生成上下文和审计，不应包含正式写回指令、导出触发指令或 job/result bundle 写入目标。

## 6. 标段与工期字段

建议字段:

- `lot_id`: 标段 ID。
- `lot_name`: 标段名称。
- `lot_number`: 标段编号。
- `scope_summary`: 标段范围摘要。
- `planned_duration_days`: 计划工期天数。
- `planned_start_date`: 计划开工日期，可为空。
- `planned_end_date`: 计划竣工日期，可为空。
- `quality_target`: 质量目标。
- `safety_target`: 安全目标。
- `milestone_constraints`: 关键节点约束。

工期字段应尽量采用结构化字段。无法确定的字段应保留为空或标记为 `unknown`，不应在 mapper 阶段臆造。

## 7. 招标文件与评分项字段

建议字段:

- `tender_doc_id`: 招标文件 ID 或来源引用。
- `tender_doc_version`: 招标文件版本。
- `technical_requirements`: 技术要求摘要或摘录列表。
- `format_requirements`: 格式、页数、目录或版式要求。
- `submission_requirements`: 提交要求。
- `evaluation_method`: 评标办法摘要。
- `scoring_items`: 评分项列表。

`scoring_items` 建议包含:

- `item_id`: 评分项 ID。
- `item_name`: 评分项名称。
- `max_score`: 分值。
- `requirement_text`: 要求原文或摘要。
- `evidence_needed`: 需要支撑的素材类型。
- `related_section_ids`: 关联章节任务 ID。

招标文件字段应保留来源引用和版本信息。用于生成的文本片段应标注是否为原文摘录、人工摘要或业务侧整理内容。

## 8. 章节任务字段

建议字段:

- `section_id`: ZBid 侧章节任务 ID。
- `section_title`: 章节标题。
- `section_order`: 章节顺序。
- `section_goal`: 章节目标。
- `section_requirements`: 章节要求。
- `original_text`: 当前章节原始正文，可为空。
- `original_source`: 原始正文来源。
- `target_length`: 目标长度或页数约束。
- `related_scoring_item_ids`: 关联评分项 ID。
- `related_material_ids`: 关联技术素材 ID。
- `draft_instruction`: 草稿生成或改写指令。

章节任务字段可映射到 ZDoc draft-only input，但不得包含直接覆盖正式正文、更新 `run_result`、写 result bundle 或触发 export 的指令。

## 9. 技术素材字段

建议字段:

- `material_id`: 素材 ID。
- `material_type`: 素材类型，例如业绩、人员、施工组织、设备、质量安全、环保、进度计划。
- `title`: 素材标题。
- `content_excerpt`: 可用于草稿的素材摘录。
- `source_ref`: 来源引用。
- `source_version`: 来源版本。
- `confidence`: 可信度标记。
- `usable_for_draft`: 是否允许用于 draft-only preview。
- `sensitive`: 是否包含敏感信息。
- `redaction_note`: 脱敏说明。

技术素材字段只应进入草稿输入和审计上下文。敏感字段默认不得进入模型输入，除非后续有单独脱敏设计和验收。

## 10. 审核与决策字段

建议字段:

- `requested_by`: 请求草稿预览的人。
- `requested_at`: 请求时间。
- `reviewer`: 业务审核人，可为空。
- `review_state`: 业务审核状态，例如 `pending_review`、`reviewed`、`rejected_for_revision`。
- `review_note`: 业务审核意见。
- `decision_reason`: 业务侧决策理由，可为空。

这些字段只代表 ZBid 业务侧状态，不等同于 ZDoc 正式写回确认。schema 不得包含绕过人工确认的 apply 字段，不得包含 `confirmed_apply=true`、`auto_apply=true` 或类似语义。

## 11. 版本与 hash 字段

建议字段:

- `snapshot_version`: 快照版本。
- `schema_version`: schema 版本。
- `snapshot_created_at`: 快照创建时间。
- `source_updated_at`: ZBid 源数据更新时间。
- `snapshot_hash`: 整体快照 hash。
- `project_hash`: 项目字段 hash。
- `tender_hash`: 招标文件字段 hash。
- `section_original_hash`: 章节原始正文 hash。
- `materials_hash`: 技术素材集合 hash。
- `prompt_input_hash`: 后续 mapper 生成 draft input 前的输入 hash。

hash 字段用于冲突检测、回溯和审计。后续如果进入写盘设计，必须先验证 original hash 与当前章节正文一致。

## 12. 安全边界字段

建议字段:

- `mode`: 固定为 `draft_only_snapshot`。
- `write_policy`: 固定为 `no_write`。
- `generation_policy`: 固定为 `no_real_generation` 或由后续 mock 阶段明确覆盖。
- `export_policy`: 固定为 `no_export`.
- `job_policy`: 固定为 `no_job_update`.
- `requires_human_review`: 固定为 `true`。
- `allowed_next_step`: 第一阶段建议仅为 `mock_mapping` 或 `draft_preview_input`.

安全边界字段只用于声明禁止能力，不应用作执行开关。所有后续写盘能力必须另行设计、实现和验收。

## 13. 不允许进入 schema 的字段

以下字段或语义不得进入 ZBid 输入快照 schema:

- 正文正式写回指令。
- export 触发字段。
- job/result bundle 写入字段。
- build/output 写入字段。
- 绕过人工确认的 apply 字段。
- `/actions/generate_async` 触发字段。
- `/actions/review/apply` 触发字段。
- DOCX/XLSX/PPTX/HTML 自动导出字段。
- 自动覆盖章节正文的字段。
- 自动更新 `run_result` 的字段。
- 自动创建或更新 job 的字段。
- 自动标记为正式交付成果的字段。
- 未经脱敏的敏感凭证、账号、密钥或私密资料。

schema 不得包含正文正式写回指令，不得包含 export 触发字段，不得包含 job/result bundle 写入字段，不得包含绕过人工确认的 apply 字段。所有后续写盘能力必须另行设计和验收。

## 14. 示例 JSON

以下示例仅用于说明文档中的字段结构，不代表新增 JSON 文件，不代表 API 入参已开放。

```json
{
  "snapshot_meta": {
    "snapshot_id": "zbid-snapshot-001",
    "source_system": "ZBid",
    "schema_version": "0.1",
    "snapshot_version": "1",
    "snapshot_created_at": "2026-05-05T10:00:00+08:00",
    "requested_by": "user@example.com"
  },
  "project": {
    "project_id": "project-001",
    "project_name": "Example Technical Bid Project",
    "project_code": "BID-2026-001",
    "owner_name": "Example Owner",
    "agency_name": "Example Agency",
    "bidder_name": "Example Bidder",
    "project_location": "Example City",
    "document_type": "technical_bid",
    "business_stage": "draft_preview"
  },
  "lot": {
    "lot_id": "lot-001",
    "lot_name": "Section A",
    "lot_number": "A",
    "scope_summary": "Example construction scope summary",
    "planned_duration_days": 180,
    "planned_start_date": null,
    "planned_end_date": null,
    "quality_target": "Qualified",
    "safety_target": "No major safety incidents",
    "milestone_constraints": []
  },
  "tender": {
    "tender_doc_id": "tender-doc-001",
    "tender_doc_version": "v1",
    "technical_requirements": [
      {
        "requirement_id": "req-001",
        "text": "Describe construction organization and schedule controls.",
        "source_type": "excerpt"
      }
    ],
    "format_requirements": [],
    "submission_requirements": [],
    "evaluation_method": "comprehensive_score",
    "scoring_items": [
      {
        "item_id": "score-001",
        "item_name": "Construction organization plan",
        "max_score": 10,
        "requirement_text": "Plan should be complete and feasible.",
        "evidence_needed": ["schedule", "resource_plan"],
        "related_section_ids": ["section-001"]
      }
    ]
  },
  "section_tasks": [
    {
      "section_id": "section-001",
      "section_title": "Construction Organization Plan",
      "section_order": 1,
      "section_goal": "Create a draft-only section preview.",
      "section_requirements": ["Cover schedule, resources, and key measures."],
      "original_text": "Existing section text for comparison.",
      "original_source": "zdoc_current_section",
      "target_length": "about 1200 Chinese characters",
      "related_scoring_item_ids": ["score-001"],
      "related_material_ids": ["mat-001"],
      "draft_instruction": "Improve completeness while preserving factual constraints."
    }
  ],
  "technical_materials": [
    {
      "material_id": "mat-001",
      "material_type": "schedule",
      "title": "Example schedule control material",
      "content_excerpt": "Use milestone tracking and weekly coordination.",
      "source_ref": "business-material-001",
      "source_version": "v1",
      "confidence": "reviewed",
      "usable_for_draft": true,
      "sensitive": false,
      "redaction_note": null
    }
  ],
  "review_context": {
    "reviewer": null,
    "review_state": "pending_review",
    "review_note": null,
    "decision_reason": null
  },
  "version_hashes": {
    "snapshot_hash": "sha256:example-snapshot-hash",
    "project_hash": "sha256:example-project-hash",
    "tender_hash": "sha256:example-tender-hash",
    "section_original_hash": "sha256:example-original-hash",
    "materials_hash": "sha256:example-materials-hash",
    "prompt_input_hash": "sha256:example-prompt-input-hash"
  },
  "safety_boundary": {
    "mode": "draft_only_snapshot",
    "write_policy": "no_write",
    "generation_policy": "no_real_generation",
    "export_policy": "no_export",
    "job_policy": "no_job_update",
    "requires_human_review": true,
    "allowed_next_step": "mock_mapping"
  }
}
```

## 15. 校验规则

建议后续 mock-only mapper/helper 至少校验:

- `snapshot_meta.snapshot_id` 必填。
- `snapshot_meta.schema_version` 必填。
- `project.project_id` 和 `project.project_name` 必填。
- `section_tasks` 至少包含一个章节任务。
- 每个章节任务必须包含 `section_id` 和 `section_title`。
- `related_scoring_item_ids` 必须能在 `tender.scoring_items` 中找到对应项，允许为空。
- `related_material_ids` 必须能在 `technical_materials` 中找到对应项，允许为空。
- `version_hashes.snapshot_hash` 必填。
- `safety_boundary.mode` 必须为 `draft_only_snapshot`。
- `safety_boundary.write_policy` 必须为 `no_write`。
- `safety_boundary.export_policy` 必须为 `no_export`。
- 不允许出现正式写回、导出、job/result bundle 写入或绕过人工确认的字段。

校验失败时，后续 helper 应返回结构化错误，不应尝试补写默认正文，不应触发生成或写盘。

## 16. 与 ZDoc draft-only input 的映射关系

建议映射关系:

- `section_tasks[].section_title` -> ZDoc section draft `section_title`。
- `section_tasks[].original_text` -> ZDoc section draft `original`。
- `section_tasks[].draft_instruction`、`section_requirements`、`related_scoring_item_ids` 和 `related_material_ids` -> ZDoc draft-only input 的上下文字段。
- `technical_materials[].content_excerpt` -> 草稿上下文素材。
- `tender.scoring_items` -> 章节约束和评分点上下文。
- `version_hashes.section_original_hash` -> original hash 校验。
- `snapshot_meta` 和 `version_hashes` -> audit context。
- `safety_boundary` -> 后续 mapper 的拒绝条件和审计提示。

该映射只允许进入 draft-only build 或 mock-only helper。不得映射为 `/actions/generate_async` 入参，不得映射为 `/actions/review/apply` 入参，不得映射为 export 参数。

## 17. 后续 mock-only mapper/helper 前置条件

进入 mock-only mapper/helper 前建议满足:

- schema 字段范围已被文档确认。
- 至少准备一个纯内存测试样例。
- helper 只接受输入快照并返回 ZDoc draft-only input。
- helper 不读取 job/build/output。
- helper 不写 job/build/output/result bundle。
- helper 不调用 LLMClient。
- helper 不连接 Ollama。
- helper 不触发 run_autoplan。
- helper 不触发 export/docx/xlsx/pptx/html。
- helper 对禁止字段有拒绝测试。

mock-only 阶段的验收目标应是字段映射正确、冲突和禁止字段能被拒绝、文件数量前后一致。

## 18. 结论

ZBid 输入快照 schema 应作为 ZBid 接入 ZDoc 前的只读、可审计、可校验边界。它的职责是描述业务输入和草稿上下文，不负责生成正式成果，不负责写回正文，不负责更新 job/result bundle，不负责触发导出。

建议下一步仍保持低风险路线: 先基于本 schema 设计 mock-only mapper/helper，并通过纯内存测试确认字段映射和禁止字段拒绝逻辑。正式写回、持久化、job/result bundle 和 export 必须继续拆分为单独设计、单独实现、单独验收。
