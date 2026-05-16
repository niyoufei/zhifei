# ZDoc preview advisory quality gate design

## 1. 阶段背景

本阶段执行 ZDoc Step 40：preview advisory quality gate design。

前序阶段事实如下：

- Step 38 已证明真实 runtime enabled 场景可返回 `status=ok` 和 bounded advisory；
- Step 38 enabled 场景返回 `calls_ollama=true`；
- Step 38 enabled 场景返回 `real_transport_enabled=true`；
- Step 38 advisory 来源为 `thinking_only_fallback`；
- Step 38 advisory 长度为 `386`；
- Step 38 suggestions 数量为 `1`；
- Step 38 risk_notes / warnings 数量为 `1`；
- Step 39 已归档 thinking fallback 质量缺口；
- 当前尚未证明普通 `response`、结构化 JSON、高质量 advisory 稳定；
- 当前不能进入 shadow generation；
- 当前不能进入正式生成链；
- 当前不能进入 DOCX 导出；
- 当前不能进入 ZBid 写回。

Step 40 的目标是设计 preview advisory quality gate，作为后续正式生成链接入前的第一道质量门禁。

本步为 docs-only 质量门禁设计步骤，不实现质量评测器，不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型。

## 2. 当前已证明能力

当前已经证明的能力如下：

- default real transport runtime 可触发；
- enabled 场景可 `calls_ollama=true`；
- enabled 场景可 `real_transport_enabled=true`；
- normalization 可将真实 runtime thinking fallback 转为 bounded advisory；
- fake fixture 下普通文本 response 已受控；
- fake fixture 下 JSON 文本 response 已受控；
- fake fixture 下非 JSON 技术建议文本已受控；
- fake fixture 下 `message.content` 已受控；
- fake fixture 下 thinking fallback 已受控；
- fake fixture 下空 response、malformed JSON、normalization failure 均已受控；
- suggestions 数量上限已在 fake fixture 下验证；
- risk_notes 数量上限已在 fake fixture 下验证；
- no-write / preview-only 边界仍保持稳定；
- runtime 未写 `output/job/export`；
- runtime 未触发正式生成链；
- runtime 未触发导出链；
- runtime 未触发 ZBid 写回链。

这些能力只证明 preview advisory 层已有可控底座，不证明 advisory 质量已经合格。

## 3. 当前未证明事项

当前尚未证明以下事项：

- advisory 质量未评分；
- thinking fallback 不代表普通 response 稳定；
- 普通 response runtime 稳定性未证明；
- JSON response runtime 稳定性未证明；
- 非 JSON 技术建议文本 runtime 稳定性未证明；
- `message.content` runtime 稳定性未证明；
- 多 payload 稳定性未证明；
- 专业性未评分；
- 准确性未评分；
- 工程适配性未评分；
- 招标响应质量尚未纳入自动质量门禁；
- 参数一致性尚未纳入自动质量门禁；
- 风险闭环尚未纳入自动质量门禁；
- 施工组织逻辑尚未纳入自动质量门禁；
- 未进入 shadow generation；
- 未进入人工确认写回；
- 未进入 DOCX 导出一致性校核；
- 未进入 ZBid 写回隔离。

因此，`status=ok` 不能被解释为质量合格，也不能被解释为可进入正式生成链。

## 4. quality gate 总体目标

preview advisory quality gate 的总体目标如下：

- 防止低质 advisory 被包装为可用建议；
- 防止 thinking fallback 被误当正式正文；
- 防止 `status=ok` 被误判为质量合格；
- 防止 preview advisory 被误写入正式章节；
- 防止 preview advisory 直接触发 DOCX 导出；
- 防止 preview advisory 直接触发 ZBid 写回；
- 在进入 shadow generation 前建立可量化准入标准；
- 在进入正式生成链前建立质量评分基础；
- 在进入正式生成链前建立风险拦截基础；
- 在进入正式生成链前建立人工确认基础；
- 在进入正式生成链前建立回滚基础；
- 始终保持 preview-only / no-write，直到后续单独授权正式链写回。

quality gate 是正式链前置门禁，不是正式链本身。

## 5. quality gate 分层设计

### P0 安全与边界门禁

P0 是硬性安全门禁，任一项不满足都必须 blocked：

- 必须 `preview_only=true`；
- 必须 `no_write=true`；
- 必须 `affects_generation=false`；
- 必须 `affects_export=false`；
- 必须 `affects_zbid_writeback=false` 或等价字段；
- 不得触发 `/generate`；
- 不得触发 `/export_docx`；
- 不得触发 `/review/apply`；
- 不得写 `output/job/export`；
- 不得写正式章节；
- 不得生成 DOCX / JSON / Markdown 正式导出；
- 不得接 ZBid 写回；
- 不得下载或 pull 模型；
- 不得调用外部模型/API。

P0 的职责是保护系统边界。P0 不评价内容质量，只判断是否允许进入任何后续 preview 质量判断。

### P1 响应完整性门禁

P1 判断 preview advisory 是否具备可评估的结构：

- advisory 非空；
- advisory 长度在上限内；
- suggestions 数量在上限内；
- risk_notes / warnings 数量在上限内；
- `source` 可追踪；
- `model` 可追踪；
- `calls_ollama` 可追踪；
- `preview_mode` 可追踪；
- `content_source` 或 `response_source` 可追踪；
- `failure_reason` / `error_type` 可追踪；
- `request_id` 可追踪，如调用方提供；
- `status` 与 `ok` 字段含义一致。

P1 不保证 advisory 质量，只保证后续质量评估有足够元数据。

### P2 输出模式门禁

P2 判断输出来源和 fallback 级别：

- 普通 response 优先级高于 thinking fallback；
- `message.content` 优先级高于 thinking fallback；
- JSON response 优先解析结构化字段；
- 非 JSON 技术建议文本可作为 fallback；
- `thinking_only_fallback` 必须标记为 `review_required` 或等价状态；
- `thinking_only_fallback` 不得直接作为正式生成依据；
- `thinking_only_fallback` 不得直接作为章节改写依据；
- `thinking_only_fallback` 不得进入 DOCX 导出；
- `thinking_only_fallback` 不得进入 ZBid 写回；
- missing `preview_mode` 时不得高于 `review_required`。

P2 的核心原则是：response / structured output 优先，thinking fallback 只是 preview-only 兜底。

### P3 技术质量门禁

P3 判断 advisory 是否具备施工组织设计 / 技术标场景下的可用性：

- advisory 必须与输入章节或标题相关；
- advisory 不得出现空泛模板话；
- advisory 不得只写“加强管理、严格控制、落实责任”等泛化表达；
- advisory 不得出现无依据的工程量；
- advisory 不得出现无依据的工期；
- advisory 不得出现无依据的规范编号；
- advisory 不得出现无依据的金额；
- advisory 不得出现无依据的项目名称；
- advisory 不得虚构招标条款；
- advisory 不得虚构评分项；
- advisory 不得虚构图纸内容；
- advisory 不得虚构清单内容；
- advisory 不得输出正式正文替换段落；
- advisory 不得生成 DOCX / Markdown / JSON 文件内容；
- 对施工组织设计内容，应优先检查量化指标；
- 对施工组织设计内容，应优先检查风险闭环；
- 对施工组织设计内容，应优先检查工序逻辑；
- 对施工组织设计内容，应优先检查资源合理性。

P3 的目标是防止低质、空泛、臆断或越界的内容进入后续候选层。

### P4 正式链准入门禁

P4 判断 preview advisory 是否具备进入更深阶段的资格。当前阶段 P4 一律不放行正式写入：

- preview advisory 通过质量评分后，也只能进入 shadow / candidate 区；
- 不得直接写正式章节；
- 不得直接触发 DOCX 导出；
- 不得直接写回 ZBid；
- 必须经过人工确认；
- 必须有 diff 展示；
- 必须有版本记录；
- 必须有回滚机制；
- 必须有低质拦截；
- 必须有导出一致性校核；
- 必须有 ZBid 写回隔离。

在 Step 40 阶段，所有 preview advisory 均为 `formal_ineligible`。

## 6. quality gate 判定状态设计

后续 quality gate 至少应设计以下状态：

- `blocked`：必须拦截，不得进入后续链路；
- `review_required`：可展示给用户，但不得进入 shadow generation；
- `preview_ok`：可作为 preview advisory 展示；
- `shadow_candidate`：未来质量层成熟后才允许进入候选改写；
- `formal_ineligible`：当前阶段一律不得进入正式正文；
- `system_error`：异常或不可解析时受控失败。

状态语义如下：

- `blocked`：P0 安全边界失败、结构不可评估、内容明显低质或存在臆断；
- `review_required`：可读但质量不足、依赖 thinking fallback、缺少部分证据或需要人工判断；
- `preview_ok`：仅表示可作为 preview advisory 展示；
- `shadow_candidate`：只在后续质量层成熟、人工确认链路明确后才允许；
- `formal_ineligible`：当前阶段所有输出均应附带或等价体现；
- `system_error`：异常或不可解析时必须受控失败，不得自动放行。

Step 40 只设计状态，不实现状态机。

当前阶段所有输出均应 `formal_ineligible`。

`thinking_only_fallback` 默认不得高于 `review_required` 或 `preview_ok`，具体准入需后续质量实现验证。

## 7. quality score 设计

后续质量评分可按以下维度设计，但本步不得实现：

- `relevance_score`：与输入章节、标题、上下文的相关性；
- `specificity_score`：是否具体、非模板化；
- `engineering_score`：施工组织 / 技术标专业性；
- `quantification_score`：是否具备量化指标或可核验控制点；
- `risk_closure_score`：风险、措施、验证之间是否形成闭环；
- `evidence_safety_score`：是否避免虚构条款、数据、规范编号、图纸或清单；
- `format_score`：字段完整、长度受控、结构清晰；
- `write_safety_score`：是否保持 no-write、no-export、no-ZBid-writeback；
- `fallback_penalty`：thinking fallback、弱输出、空泛输出或非结构化输出降级；
- `overall_quality_status`：综合状态。

评分原则：

- 分数不用于正式生成链；
- 分数仅作为 preview 阶段门禁参考；
- 低于阈值必须 `blocked` 或 `review_required`；
- 高于阈值也不得直接写正式正文；
- 高于阈值也不得直接触发 DOCX 导出；
- 高于阈值也不得直接写回 ZBid；
- 评分必须可解释，至少返回 blockers / warnings / review_reasons。

建议初期将 `thinking_only_fallback` 自动施加 `fallback_penalty`，并默认进入 `review_required` 或受限的 `preview_ok`。

## 8. 低质输出拦截规则

以下情况必须 `blocked` 或 `review_required`：

- advisory 为空；
- advisory 只是泛泛表述；
- advisory 与输入无关；
- advisory 虚构工程参数；
- advisory 虚构招标条款；
- advisory 虚构规范编号；
- advisory 虚构清单内容；
- advisory 虚构图纸内容；
- advisory 过长；
- advisory 疑似正文替换；
- 出现“已写入”；
- 出现“已生成正式文档”；
- 出现“已导出 DOCX”；
- 出现“已写回 ZBid”；
- thinking fallback 未标记；
- missing `source`；
- missing `model`；
- missing `preview_mode`；
- `no_write` 字段缺失或为 false；
- `preview_only` 字段缺失或为 false；
- `affects_generation` 非 false；
- `affects_export` 非 false；
- 出现生成链调用痕迹；
- 出现导出链调用痕迹；
- 出现写回链调用痕迹。

拦截规则必须 fail closed：无法判断时不得自动放行到后续链路。

## 9. 技术标场景专项质量要求

结合后续正式生成链目标，施工组织设计 / 技术标场景下的 advisory 质量要求如下：

- 语言应符合央企技术标表达；
- 建议应指向具体章节、工序、风险、质量、安全、进度、环保、资源或评分项；
- 不得只写“加强管理、严格控制、落实责任、优化方案”等空话；
- 涉及施工措施时，应优先包含控制点；
- 涉及施工措施时，应优先包含量化指标；
- 涉及施工措施时，应优先包含检查频次；
- 涉及施工措施时，应优先包含责任岗位；
- 涉及施工措施时，应优先包含验证资料；
- 涉及招标条款时必须要求证据锚点；
- 涉及评分项时必须要求证据锚点；
- 未查明的招标条款不得臆断；
- 未查明的评分项不得臆断；
- 涉及图纸、清单、规范时必须标记为“需资料核验”或“未查明”；
- 不得把 preview advisory 当作正式正文；
- 不得把 preview advisory 当作已采纳方案；
- 不得把 preview advisory 当作已写入结果。

专项质量要求应服务于后续 shadow generation 与人工确认，而不是绕过人工确认。

## 10. data contract 设计

后续 quality gate 输出字段建议如下，但本步不得实现：

- `quality_status`
- `quality_score`
- `gate_level`
- `blockers`
- `warnings`
- `review_reasons`
- `passed_checks`
- `failed_checks`
- `preview_mode`
- `response_source`
- `content_source`
- `model`
- `calls_ollama`
- `advisory_length`
- `suggestions_count`
- `risk_notes_count`
- `formal_generation_allowed`
- `shadow_candidate_allowed`
- `writeback_allowed`
- `export_allowed`
- `zbid_writeback_allowed`

当前阶段字段默认语义应为：

- `formal_generation_allowed=false`
- `shadow_candidate_allowed=false`
- `writeback_allowed=false`
- `export_allowed=false`
- `zbid_writeback_allowed=false`

如果后续引入 `shadow_candidate_allowed=true`，必须先有单独设计、deterministic tests、人工确认链路和回滚机制。

## 11. deterministic tests 设计

后续 Step 41 或后续实现必须覆盖以下 deterministic tests，但本步不得运行 pytest：

- 高质量 advisory -> `preview_ok`；
- 空 advisory -> `blocked`；
- 泛泛模板话 advisory -> `review_required` 或 `blocked`；
- `thinking_only_fallback` -> `review_required` 或降级；
- 虚构工程量 -> `blocked`；
- 虚构规范编号 -> `blocked`；
- 虚构招标条款 -> `blocked`；
- 过长 advisory -> 截断或 `blocked`；
- `no_write=false` -> `blocked`；
- `preview_only=false` -> `blocked`；
- `affects_generation=true` -> `blocked`；
- `affects_export=true` -> `blocked`；
- missing `source` / `model` / `preview_mode` -> `review_required`；
- suggestions 超上限 -> 截断并 warning；
- risk_notes 超上限 -> 截断并 warning；
- `output/job/export` 写入尝试 -> `blocked`；
- `/generate` 调用尝试 -> `blocked`；
- `/export_docx` 调用尝试 -> `blocked`；
- `/review/apply` 调用尝试 -> `blocked`。

测试边界：

- 必须使用 fake fixture / monkeypatch / dependency injection；
- 不得依赖真实 Ollama；
- 不得启动服务；
- 不得运行 `ollama serve`；
- 不得访问外网；
- 不得下载或拉取模型；
- 不得写 `output/job/export`。

## 12. 后续实现边界

后续实现 quality gate 时，原则上应先做 docs-only 实现前设计，不得本步实现。

建议下一步先做：

```text
ZDoc Step 41：preview advisory quality gate guard + deterministic tests design
```

后续实现前必须明确：

- 是否新增 quality_gate helper；
- 是否放在 `backend/zhifei_autoplan/`；
- 是否调整 endpoint response schema；
- 是否扩展 tests；
- 是否需要新增测试文件；
- 如何保持 preview-only / no-write 不变；
- 如何证明不触发正式生成链；
- 如何证明不触发导出链；
- 如何证明不接 ZBid 写回；
- 如何证明不写 `output/job/export`。

如需新增文件、调整 schema、扩展测试范围或引入评分阈值，必须先经 ChatGPT 审核。

## 13. 与正式生成链接入目标的关系

最终目标是让本地模型稳定、高质量参与正式生成链，包括：

- 正文生成；
- 章节改写；
- DOCX 导出；
- ZBid 写回。

但 quality gate 是正式链前置门禁，不是正式链本身。正式链仍需后续完成：

- preview advisory quality gate；
- 多 payload 稳定性验证；
- shadow generation；
- candidate patch；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- 生成质量评分；
- 低质拦截。

quality gate 的存在不能被解释为正式写回授权。它只决定 preview advisory 是否可展示、是否需人工复核、是否可在未来进入 shadow candidate。

## 14. 风险与回滚

主要风险如下：

- 风险 1：`status=ok` 被误认为质量合格；
- 风险 2：thinking fallback 被误认为正式正文；
- 风险 3：低质 advisory 被放行；
- 风险 4：质量评分过宽导致后续正式链污染；
- 风险 5：质量评分过严导致可用建议被误拦截；
- 风险 6：后续实现误写正式正文或 `output/job/export`；
- 风险 7：质量门禁字段被误用为正式写回许可；
- 风险 8：shadow candidate 与 formal writeback 边界混淆。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

- 保留 disabled 路径；
- 保留 adapter-off 路径；
- 保留 fake-only 路径；
- 保留 preview-only guard；
- 保留 no-write guard；
- 质量门禁异常时必须 `blocked`，不得自动放行。

## 15. 当前阶段结论

本阶段仅完成 preview advisory quality gate 的 docs-only 设计，未实现质量评测器，未运行测试，未启动服务，未进入 shadow generation 或正式生成链。

当前可以确认的是：

- Step 38 已证明真实 runtime enabled 场景可返回 `status=ok` 和 bounded advisory；
- Step 39 已明确该 advisory 来源为 `thinking_only_fallback`，质量仍未证明；
- Step 40 将后续工作收敛到 preview advisory quality gate；
- 在质量门禁、稳定性验证、shadow generation、人工确认、导出校核和 ZBid 隔离成熟前，不得进入正式生成链。

## 16. 下一步建议

下一步建议为 ZDoc Step 41：preview advisory quality gate guard + deterministic tests design。

不得直接进入 quality gate implementation，不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
