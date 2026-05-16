# ZDoc preview advisory quality gate guard and deterministic tests design

## 1. 阶段背景

本阶段执行 ZDoc Step 41：preview advisory quality gate guard + deterministic tests design。

前序阶段事实如下：

- Step 38 已证明真实 runtime enabled 场景可返回 `status=ok` 和 bounded advisory；
- Step 38 enabled 场景返回 `calls_ollama=true`；
- Step 38 enabled 场景返回 `real_transport_enabled=true`；
- Step 38 advisory 来源为 `thinking_only_fallback`；
- Step 39 已归档 thinking fallback 质量缺口；
- Step 40 已完成 preview advisory quality gate design；
- 当前尚未实现质量评测器；
- 当前尚未证明 advisory 质量合格；
- 当前不得进入 shadow generation；
- 当前不得进入正式生成链；
- 当前不得进入 DOCX 导出；
- 当前不得进入 ZBid 写回。

Step 41 的目标是锁定后续 quality gate 实现前的 guard、测试、允许修改文件、数据契约和失败回滚边界。

本步不得实现代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`。

## 2. quality gate 设计目标复述

preview advisory quality gate 的目标如下：

- 防止低质 advisory 被包装成可用建议；
- 防止 thinking fallback 被误当正式正文；
- 防止 `status=ok` 被误判为质量合格；
- 防止 preview advisory 被误写入正式章节；
- 防止 preview advisory 直接触发导出或写回；
- 在进入 shadow generation 前建立可量化门禁；
- 在进入正式生成链前建立质量评分基础；
- 在进入正式生成链前建立风险拦截基础；
- 在进入正式生成链前建立人工确认基础；
- 在进入正式生成链前建立回滚基础；
- 当前所有输出仍必须 `formal_ineligible`；
- 当前所有输出不得写正式正文；
- 当前所有输出不得导出；
- 当前所有输出不得写回 ZBid。

quality gate 是 preview 阶段的质量门禁，不是正式链授权机制。高质量 preview advisory 也不能自动升级为正式正文。

## 3. guard 分层设计

后续实现必须至少包含以下 guard。

### P0 安全边界 guard

P0 是硬性安全边界。任一安全字段缺失、异常或出现正式链调用痕迹，`quality_status` 必须为 `blocked`。

P0 guard 要求：

- 必须 `preview_only=true`；
- 必须 `no_write=true`；
- 必须 `affects_generation=false`；
- 必须 `affects_export=false`；
- 必须 `affects_zbid_writeback=false` 或等价字段；
- 不触发 `/generate`；
- 不触发 `/export_docx`；
- 不触发 `/review/apply`；
- 不写 `output/job/export`；
- 不接 ZBid 写回；
- 不写正式章节；
- 不生成 DOCX / JSON / Markdown 正式导出；
- 不调用外部模型/API；
- 不下载或 pull 模型。

P0 失败时不得继续评估 P1-P4，不得展示为可用建议，不得进入 shadow candidate。

### P1 响应完整性 guard

P1 判断 response 是否具备可评估结构：

- advisory 必须存在且非空；
- advisory 长度必须在上限内；
- suggestions 数量必须在上限内；
- risk_notes / warnings 数量必须在上限内；
- `source` 必须可追踪；
- `model` 必须可追踪；
- `calls_ollama` 必须可追踪；
- `preview_mode` 必须可追踪；
- `content_source` 或 `response_source` 必须可追踪；
- `error_type` / `failure_reason` 必须可追踪；
- `status` 与 `ok` 字段不得自相矛盾。

缺少关键追踪字段时不得进入 `shadow_candidate`。如果 advisory 不可评估，必须 `blocked` 或 `review_required`。

### P2 输出模式 guard

P2 判断输出来源和 fallback 等级：

- 普通 response 优先级高于 thinking fallback；
- `message.content` 优先级高于 thinking fallback；
- JSON response 优先解析结构化字段；
- 非 JSON 技术建议文本只能作为 preview fallback；
- `thinking_only_fallback` 必须显式降级；
- `thinking_only_fallback` 不得作为正式生成依据；
- `thinking_only_fallback` 不得作为章节改写依据；
- `thinking_only_fallback` 不得进入 shadow candidate；
- `status=ok` 不能跳过质量评分；
- `status=ok` 不能直接变成 formal eligibility。

P2 的核心是把 response quality 与 transport success 分离。`calls_ollama=true` 只说明触达 real transport，不说明内容质量合格。

### P3 技术质量 guard

P3 判断 advisory 的技术标 / 施工组织设计质量：

- advisory 必须与输入章节 / 标题相关；
- 不得输出空泛模板话；
- 不得只输出“加强管理、严格控制、落实责任”等泛化表述；
- 不得虚构工程量；
- 不得虚构工期；
- 不得虚构规范编号；
- 不得虚构金额；
- 不得虚构项目名称；
- 不得虚构招标条款；
- 不得虚构评分项；
- 不得虚构图纸内容；
- 不得输出正式正文替换段落；
- 不得生成 DOCX / Markdown / JSON 文件内容；
- 施工组织设计场景应检查量化指标；
- 施工组织设计场景应检查风险闭环；
- 施工组织设计场景应检查工序逻辑；
- 施工组织设计场景应检查资源合理性。

P3 不能依赖真实模型再次判断。后续实现应先用 deterministic fake fixtures 固化启发式规则、字段检查和 fail-closed 行为。

### P4 正式链准入 guard

当前阶段 P4 必须固定为不放行正式链：

- 当前阶段 `formal_generation_allowed=false`；
- 当前阶段 `shadow_candidate_allowed=false`；
- 当前阶段 `writeback_allowed=false`；
- 当前阶段 `export_allowed=false`；
- 当前阶段 `zbid_writeback_allowed=false`；
- 后续即使 `quality_score` 达标，也只能进入后续单独授权的 shadow / candidate 阶段；
- 后续 shadow / candidate 阶段必须单独设计、单独测试、单独授权。

P4 的职责是防止 quality gate 被误用成正式链开关。

## 4. quality status 状态机设计

后续实现应设计以下状态，但本步不得实现：

- `blocked`：必须拦截，不得展示为可用建议；
- `review_required`：可展示给用户审核，但不得进入 shadow generation；
- `preview_ok`：可作为 preview advisory 展示；
- `shadow_candidate`：未来 shadow generation 阶段才允许；
- `formal_ineligible`：当前阶段所有输出必须带该限制；
- `system_error`：异常或不可解析时受控失败。

状态规则：

- 当前阶段所有输出均不得高于 `preview_ok`；
- 当前阶段所有输出都必须保持 `formal_ineligible`；
- `thinking_only_fallback` 默认不得高于 `review_required`，除非后续质量实现明确验证；
- `status=ok` 与 `quality_status` 必须分离；
- `quality_status` 不得影响正式生成链；
- `quality_status=preview_ok` 不得把 `formal_generation_allowed` 置为 true；
- `quality_status=blocked` 时不得展示为可用建议；
- `system_error` 必须 fail closed，不得自动放行。

建议状态流：

```text
raw_preview_response
-> P0 safety guard
-> P1 completeness guard
-> P2 output mode guard
-> P3 technical quality guard
-> P4 formal-chain eligibility guard
-> quality_status + formal_ineligible flags
```

## 5. quality score 设计

后续实现应设计以下评分维度，但本步不得实现：

- `relevance_score`：与输入内容相关性；
- `specificity_score`：是否具体、非模板化；
- `engineering_score`：施工组织 / 技术标专业性；
- `quantification_score`：是否具备量化指标；
- `risk_closure_score`：风险、措施、验证闭环；
- `evidence_safety_score`：是否避免虚构条款 / 数据；
- `format_score`：字段完整、长度受控、结构清晰；
- `write_safety_score`：是否保持 no-write；
- `fallback_penalty`：thinking fallback 或弱输出降级；
- `overall_quality_status`：综合状态。

评分约束：

- 分数只用于 preview 阶段门禁；
- 分数不允许触发正式写回；
- 高分不等于正式生成链准入；
- 高分不等于 DOCX 导出准入；
- 高分不等于 ZBid 写回准入；
- 低于阈值必须 `blocked` 或 `review_required`；
- scoring threshold 后续实现前需单独设计；
- threshold 不得硬编码成绕过 P0/P4 的快捷路径。

建议后续先采用可解释的规则型评分，避免在 deterministic tests 中依赖真实模型或外部评审器。

## 6. 低质输出拦截规则

后续实现时，以下情况必须 `blocked` 或 `review_required`：

- advisory 为空；
- advisory 只是泛泛表述；
- advisory 与输入无关；
- 输出虚构工程参数；
- 输出虚构招标条款；
- 输出虚构规范编号；
- 输出虚构清单内容；
- 输出虚构图纸内容；
- 输出过长；
- 输出疑似正文替换；
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
- 出现写回链调用痕迹；
- suggestions 超上限且未截断；
- risk_notes 超上限且未截断。

拦截规则必须 fail closed：无法判断时不得自动放行到 shadow candidate 或 formal chain。

## 7. 技术标专项 guard

结合施工组织设计 / 技术标场景，后续实现应检查：

- 是否使用央企技术标表达风格；
- 是否指向章节、工序、风险、质量、安全、进度、环保、资源或评分项；
- 是否避免“加强管理、严格控制、落实责任”等空话；
- 是否包含控制点；
- 是否包含量化指标；
- 是否包含检查频次；
- 是否包含责任岗位；
- 是否包含验证资料；
- 是否避免无依据的规范编号；
- 是否避免无依据的招标条款；
- 是否避免无依据的图纸内容；
- 是否对未查明资料标记“需资料核验”或“未查明”；
- 是否避免把 advisory 写成正式正文；
- 是否保留 `evidence_safety` 或等价标识；
- 是否在缺少证据时主动降级为 review_required。

技术标专项 guard 的目标是让 advisory 有工程价值，但仍保持 preview-only，不替代人工复核。

## 8. data contract 设计

后续 quality gate 输出字段建议包括：

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

当前阶段固定值：

- `formal_generation_allowed=false`
- `shadow_candidate_allowed=false`
- `writeback_allowed=false`
- `export_allowed=false`
- `zbid_writeback_allowed=false`

数据契约要求：

- `blockers` 必须可解释；
- `warnings` 必须可展示；
- `review_reasons` 必须说明为什么需要人工审核；
- `passed_checks` / `failed_checks` 应便于 deterministic tests 断言；
- 缺少必需字段时必须 fail closed。

## 9. deterministic tests 设计

后续实现必须覆盖以下 deterministic tests，但本步不得运行 pytest：

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
- `/generate` 调用痕迹 -> `blocked`；
- `/export_docx` 调用痕迹 -> `blocked`；
- `/review/apply` 调用痕迹 -> `blocked`；
- `status=ok` 但 `quality_status=blocked` 时不得放行；
- `quality_status=preview_ok` 时 `formal_generation_allowed` 仍必须 false；
- `quality_status=preview_ok` 时 `writeback_allowed` 仍必须 false；
- `quality_status=preview_ok` 时 `export_allowed` 仍必须 false；
- thinking fallback 不得进入 `shadow_candidate`；
- quality gate exception -> `system_error` 或 `blocked`；
- malformed quality input -> `system_error` 或 `blocked`。

所有 tests 必须可在无 Ollama、无服务、无外网的 deterministic 环境中运行。

## 10. fake fixture 设计

后续 tests 应使用 fake fixture，不依赖真实 Ollama。

建议 fixture：

- `good_advisory_fixture`：具体、相关、结构完整、preview-only；
- `vague_advisory_fixture`：空泛模板话；
- `hallucinated_clause_fixture`：虚构招标条款、规范编号或工程量；
- `long_advisory_fixture`：超出 advisory 长度上限；
- `thinking_fallback_fixture`：`preview_mode=thinking_only_fallback`；
- `unsafe_write_flags_fixture`：`no_write=false` 或 `preview_only=false`；
- `route_trigger_attempt_fixture`：包含 `/generate`、`/export_docx`、`/review/apply` 调用痕迹；
- `missing_trace_fields_fixture`：缺少 `source`、`model` 或 `preview_mode`；
- `construction_bid_quality_fixture`：包含章节、工序、风险、控制点、验证资料等技术标要素；
- `empty_advisory_fixture`：advisory 为空；
- `suggestions_over_limit_fixture`：suggestions 超上限；
- `risk_notes_over_limit_fixture`：risk_notes 超上限。

fixture 约束：

- deterministic tests 不得真实访问 `127.0.0.1:11434`；
- 不得运行 Ollama；
- 不得运行 `ollama serve`；
- 不得下载模型；
- 不得调用外部 API；
- 不得写 `output/job/export`；
- 不得触发正式生成链；
- 不得触发导出链；
- 不得触发 ZBid 写回链。

## 11. 后续实现边界设计

后续 Step 42 如进入 quality gate fake-only implementation，应先明确允许修改文件。

建议原则如下：

可考虑新增或修改：

- `backend/zhifei_autoplan/preview_advisory_quality_gate.py` 或同类 helper；
- `backend/tests/test_preview_advisory_quality_gate.py` 或扩展现有 tests；
- `backend/zhifei_autoplan/ollama_preview.py` 中仅做调用点接入；
- `backend/tests/test_ollama_preview.py` 中仅做集成回归；
- `backend/tests/test_local_llm_preview_safe_endpoint.py` 中仅做 endpoint schema 回归。

但是否新增文件、是否调整 endpoint response schema、是否扩展测试范围，必须在 Step 42 前由 ChatGPT 单独授权。本步不得实现。

后续实现必须保持：

- preview-only；
- no-write；
- no-export；
- no-ZBid-writeback；
- default-off；
- fake fixture / monkeypatch / dependency injection 先行。

## 12. 禁止触碰范围

后续仍不得修改或触碰：

- 正式生成链；
- 正式导出链；
- ZBid 写回链；
- `output/`；
- `job/`；
- `export/`；
- 正式模板文件；
- 正式生成结果文件；
- 与 preview 无关的 UI 主流程；
- 任何会改变正式文档生成结果的代码。

质量门禁实现不得创建正式文档，不得写正式章节，不得触发 DOCX / JSON / Markdown 导出。

## 13. 后续阶段准入设计

下一阶段顺序不得跳步：

1. Step 41：quality gate guard + deterministic tests design；
2. Step 42：quality gate fake-only implementation + deterministic tests；
3. Step 43：quality gate implementation stage review；
4. Step 44：multi-payload preview quality smoke plan；
5. Step 45：multi-payload preview quality smoke；
6. 再讨论 shadow generation 设计；
7. 不得直接进入正式生成链。

每个阶段都必须单独授权。即使 Step 42 fake-only tests 通过，也不能自动进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。

## 14. 与正式生成链接入目标的关系

最终目标是让本地模型稳定、高质量参与正式生成链，包括：

- 正文生成；
- 章节改写；
- DOCX 导出；
- ZBid 写回。

但 quality gate 是正式链前置门禁，不是正式链本身。正式链仍需后续完成：

- shadow generation；
- candidate patch；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- 生成质量评分；
- 低质拦截。

quality gate 只能决定 preview advisory 是否可展示、是否需要人工复核、是否有资格进入未来 shadow candidate。它不能直接授权正式正文写回。

## 15. 风险与回滚

主要风险如下：

- 风险 1：quality gate 规则过宽，低质 advisory 被放行；
- 风险 2：quality gate 规则过严，可用建议被误拦截；
- 风险 3：`status=ok` 被误认为质量合格；
- 风险 4：thinking fallback 被误认为正式正文；
- 风险 5：后续实现误写正式正文或 `output/job/export`；
- 风险 6：正式链准入字段被错误置为 true；
- 风险 7：quality gate 被误用为 shadow generation 开关；
- 风险 8：quality gate 异常时未 fail closed。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

- 保留 disabled 路径；
- 保留 adapter-off 路径；
- 保留 fake-only 路径；
- 保留 preview-only guard；
- 保留 no-write guard；
- quality gate 异常时必须 `blocked`，不得自动放行。

## 16. 当前阶段结论

本阶段仅完成 preview advisory quality gate guard + deterministic tests 的 docs-only 设计，未实现 quality gate，未运行测试，未启动服务，未进入 shadow generation 或正式生成链。

当前可以确认的是：

- Step 40 已给出 quality gate 总体设计；
- Step 41 已将该设计细化为实现前 guard、状态机、评分维度、data contract、fake fixtures 和 deterministic tests；
- 后续实现必须先走 fake-only tests；
- 后续实现不得修改正式生成链、导出链或 ZBid 写回链；
- 后续任何正式链准入都必须另行设计、另行授权。

## 17. 下一步建议

下一步建议为 ZDoc Step 42：preview advisory quality gate fake-only implementation + deterministic tests。

不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
