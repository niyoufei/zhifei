# ZDoc preview advisory runtime smoke review and thinking fallback gap design

## 1. 阶段背景

本阶段执行 ZDoc Step 39：preview advisory normalization runtime smoke review + thinking fallback quality gap design。

前序阶段事实如下：

- Step 35 已完成 preview advisory normalization fake-only implementation + deterministic tests；
- Step 35 测试结果为 `140 passed in 3.72s`；
- Step 36 已完成 fake-stage review；
- Step 37 已完成 runtime smoke plan refresh；
- Step 38 已完成真实 runtime smoke；
- Step 38 enabled 场景已从 `missing_preview_advisory / invalid_response` 改善为 `status=ok`；
- Step 38 enabled 场景返回 `calls_ollama=true`；
- Step 38 enabled 场景返回 `real_transport_enabled=true`；
- Step 38 enabled 场景返回 advisory；
- Step 38 advisory 长度为 `386`；
- Step 38 suggestions 数量为 `1`；
- Step 38 risk_notes / warnings 数量为 `1`；
- Step 38 `preview_mode` 为 `thinking_only_fallback`；
- Step 38 `content_source` 为 `thinking`。

因此，Step 38 已经证明真实 runtime enabled 场景可以形成 bounded preview advisory，但当前不能把该结果等同于普通 `response` advisory、结构化 JSON advisory 或高质量 advisory 稳定。

本步为 docs-only runtime smoke 复盘与 thinking fallback 质量缺口设计步骤，不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型。

## 2. Step 38 已证明的事实

Step 38 已证明以下事实：

- Ollama listener 可达；
- `GET http://127.0.0.1:11434/api/tags` 返回 HTTP `200`；
- `/api/tags` 响应为有效 JSON；
- 本地模型列表包含 `qwen3:0.6b`；
- `/local-llm/preview-safe` enabled 场景已进入 real transport path；
- enabled 场景返回 `calls_ollama=true`；
- enabled 场景返回 `real_transport_enabled=true`；
- enabled 场景返回 `status=ok`；
- enabled 场景返回 advisory；
- enabled 场景 advisory 长度为 `386`；
- enabled 场景 suggestions 数量为 `1`；
- enabled 场景 risk_notes / warnings 数量为 `1`；
- enabled 场景 `missing_preview_advisory` 已消失；
- enabled 场景 `invalid_response` 已消失；
- thinking fallback 在真实 runtime 下可形成 bounded advisory；
- runtime 未请求 `/generate`；
- runtime 未请求 `/export_docx`；
- runtime 未请求 `/review/apply`；
- runtime 未直接请求 Ollama `/api/generate`；
- runtime 未写 `output/`、`job/`、`export/`；
- FastAPI 进程已停止；
- 端口 `18753` 已释放；
- 既有 Ollama listener PID `14236` 未被擅自停止。

Step 38 同时证明 safe endpoint 在真实 runtime 场景仍保持：

- `preview_only=true`；
- `no_write=true`；
- `affects_generation=false`；
- `affects_export=false`；
- `calls_generate_route=false`；
- `calls_export_docx_route=false`；
- `calls_review_apply_route=false`。

## 3. Step 38 尚未证明的事项

Step 38 尚未证明以下事项：

- 尚未证明普通 `response` 字段稳定返回 advisory；
- 尚未证明结构化 JSON 输出稳定；
- 尚未证明非 JSON 技术建议文本在真实 runtime 下稳定；
- 尚未证明 `message.content` 在真实 runtime 下稳定；
- 尚未证明不同 payload 下均能返回高质量 advisory；
- 尚未证明 `qwen3:0.6b` 输出质量可进入质量评测层；
- 尚未证明 thinking fallback 的内容质量足以支撑正式生成链；
- 尚未证明 thinking fallback 的专业价值、准确性、完整性或可采纳性；
- 尚未证明 suggestions 具备稳定专业价值；
- 尚未证明 risk_notes / warnings 的风险分类质量；
- 尚未进入质量评测层；
- 尚未进入 shadow generation；
- 尚未进入人工确认写回；
- 尚未进入 DOCX 导出；
- 尚未进入 ZBid 写回。

因此，Step 38 的 `status=ok` 只能证明 preview advisory runtime path 已有初步可用路径，不能证明正式链路可接入。

## 4. 新缺口定义

缺口名称：`thinking_only_fallback quality gap`

缺口性质：

- 不是 transport wiring 问题；
- 不是 Ollama 不可达；
- 不是模型不存在；
- 不是 `fake_transport_required`；
- 不是 `missing_preview_advisory`；
- 不是 `invalid_response`；
- 不是 endpoint 路由未通；
- 而是真实 runtime advisory 当前依赖 thinking fallback，尚未证明普通 response、结构化输出或高质量 advisory 稳定。

换言之，当前核心问题已经从“能否形成 advisory”转为“advisory 的来源、质量、稳定性、可解释性和正式链路隔离是否足够可靠”。

## 5. 质量风险分析

thinking fallback 的主要质量风险如下：

- thinking 内容可能偏推理过程，不一定适合作为用户可见 advisory；
- thinking fallback 可能不稳定，不同 prompt、不同上下文或不同运行时可能出现不同摘要；
- thinking fallback 不应被误当正式正文；
- thinking fallback 不应进入正式生成链；
- thinking fallback 不应作为正式章节改写依据；
- thinking fallback 应始终 bounded，不得保存完整 thinking；
- advisory 长度虽受控，但质量未评分；
- suggestions 数量虽受控，但专业价值未验证；
- risk_notes / warnings 虽存在，但风险分类未评分；
- `status=ok` 不能等价于“质量合格”；
- `status=ok` 不能等价于“可写入正式方案”；
- `status=ok` 不能等价于“可进入 DOCX 导出或 ZBid 写回”；
- 用户可能误以为 preview advisory 已写入正式方案；
- 后续实现者可能误把 thinking fallback 当成正式生成链候选输出。

当前 thinking fallback 的价值是：在真实模型未形成普通 response advisory 时，提供一个可见、截断、可追踪、preview-only 的受控兜底。它不是质量合格证明。

## 6. 后续设计目标

后续应达到的目标状态如下：

- preview advisory 可来自普通 `response`；
- preview advisory 可来自结构化 JSON；
- preview advisory 可来自非 JSON 技术建议文本；
- preview advisory 可来自受控 fallback；
- response 优先级应高于 thinking fallback；
- thinking fallback 只能作为 preview-only 兜底；
- thinking fallback 不得作为正式生成依据；
- thinking fallback 不得作为正式章节改写依据；
- smoke report 应区分 `response_mode` / `preview_mode`；
- smoke report 应区分 `content_source` / `response_source`；
- advisory 应进入质量评测前置校核；
- 低质 advisory 应可被识别；
- 低质 advisory 应可被降级；
- 低质 advisory 应可被标记；
- 所有路径保持 `preview_only=true`；
- 所有路径保持 `no_write=true`；
- 所有路径保持 `affects_generation=false`；
- 所有路径保持 `affects_export=false`；
- 不触发正式生成链；
- 不触发正式导出链；
- 不接 ZBid 写回。

目标不是把 thinking fallback 强化为正式输出，而是把它严格限制在 preview-only、quality-pending、human-review-required 的安全边界内。

## 7. 后续需要补充的 guard 设计

后续应设计或强化以下 guard：

- `preview_mode` 字段或等价字段稳定返回；
- `response_source` 字段或等价字段稳定标记；
- `content_source` 字段继续稳定标记；
- `thinking_only_fallback` 必须显式标记；
- thinking fallback 不得保存完整 thinking；
- thinking fallback 不得写入正式正文；
- thinking fallback 不得作为正式章节改写依据；
- thinking fallback 不得进入 DOCX 导出；
- thinking fallback 不得进入 ZBid 写回；
- `status=ok` 仍需附带 `quality_pending` 或 equivalent 标记，直到质量评测层建立；
- `status=ok` 仍需保留 `requires_human_review` 或 equivalent 标记；
- advisory 质量未评测前，不得进入 shadow generation；
- advisory 质量未评测前，不得进入 formal generation；
- low-quality advisory 必须能被标记为不可采纳；
- response 优先级必须高于 thinking fallback；
- empty advisory 不得被误判为 `status=ok`。

后续如需要新增 `quality_pending`、`response_mode`、`quality_gate` 等字段，应先进入 docs-only 设计，再进入 deterministic tests，不得直接修改正式链路。

## 8. 后续 deterministic tests 设计

后续实现或质量层前应补充 deterministic tests，至少包括：

- 普通 `response` 优先于 thinking fallback；
- 结构化 JSON advisory 优先于 thinking fallback；
- `message.content` 优先于 thinking fallback；
- thinking fallback 显式标记 `preview_mode`；
- thinking fallback 显式标记 `content_source` 或 `response_source`；
- thinking fallback 不保存完整 thinking；
- thinking fallback advisory 长度受控；
- suggestions 数量上限不回归；
- risk_notes 数量上限不回归；
- `response_mode` / source 字段稳定；
- `status=ok` 但 `quality_pending` 标记存在；
- low-quality advisory 可被标记；
- empty advisory 不被误判为 `ok`；
- empty thinking fallback 不被误判为 `ok`；
- no-write / preview-only 恒定；
- `affects_generation=false` 恒定；
- `affects_export=false` 恒定；
- 不触发 `/generate`；
- 不触发 `/export_docx`；
- 不触发 `/review/apply`；
- 不写 `output/job/export`。

这些 tests 必须继续使用 fake fixture / monkeypatch / dependency injection，不得依赖真实 Ollama runtime，不得启动服务，不得访问 `127.0.0.1:11434`。

## 9. 后续 runtime 验证建议

后续不应立刻进入正式链，而应继续设计：

- 多 payload preview smoke；
- 模型输出模式对比；
- 普通 response 优先 prompt 调整；
- 结构化 JSON 输出 prompt 调整；
- thinking fallback 降级策略；
- thinking fallback 标识策略；
- advisory 质量评分设计；
- low-quality advisory 拦截策略；
- shadow generation 准入门槛；
- 人工确认写回前置条件；
- DOCX 导出一致性校核前置条件；
- ZBid 写回隔离前置条件。

建议后续 runtime 验证先区分三类输出：

1. 普通 response advisory；
2. 结构化 JSON advisory；
3. thinking-only fallback advisory。

只有在多 payload、质量评分、人工确认与回滚机制明确后，才可讨论是否进入 shadow generation。

## 10. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括：

- 正文生成；
- 章节改写；
- DOCX 导出；
- ZBid 写回。

但当前 Step 38 只证明 preview advisory runtime 可用的初步路径，且该路径依赖 thinking fallback。正式链前仍必须完成：

- preview advisory 质量评测层；
- 多 payload 稳定性验证；
- shadow generation；
- 人工确认写回；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- 回滚机制；
- 生成结果质量评分；
- 低质拦截；
- thinking fallback 降级策略。

preview advisory runtime smoke 成功不能替代质量门禁，thinking fallback 成功不能替代正式正文生成能力证明。

## 11. 风险与回滚

主要风险如下：

- 风险 1：thinking fallback 被误认为正式正文；
- 风险 2：`status=ok` 被误认为质量合格；
- 风险 3：低质 advisory 被包装成可用建议；
- 风险 4：后续跳过质量评测层直接进入正式生成链；
- 风险 5：不同 payload 下 runtime 表现不稳定；
- 风险 6：用户误以为 preview advisory 已写入正式方案；
- 风险 7：thinking fallback 被用于 shadow generation 或 formal generation；
- 风险 8：未来质量门禁缺失导致低质输出进入 DOCX 或 ZBid。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

- 保留 disabled 路径；
- 保留 adapter-off 路径；
- 保留 fake-only 路径；
- 保留 preview-only guard；
- 保留 no-write guard；
- 出现异常时不得扩大到正式链路。

## 12. 当前阶段结论

Step 38 已证明真实 runtime enabled 场景可返回 `status=ok` 和 bounded advisory，但当前 advisory 来源为 `thinking_only_fallback`，尚未证明普通 response、结构化 JSON 或高质量 advisory 稳定，因此不得进入质量评测层或正式生成链。

当前可以确认的是：

- default real transport runtime path 仍可触发；
- Step 35 normalization 修复已消除 Step 32 的 `missing_preview_advisory / invalid_response` 表现；
- thinking fallback 已在真实 runtime 下形成 bounded advisory；
- no-write / preview-only / no-export / no-ZBid 边界保持稳定；
- 下一阶段应先设计 preview advisory quality gate，而不是进入正式生成链。

## 13. 下一步建议

下一步建议为 ZDoc Step 40：preview advisory quality gate design，先设计质量评测门禁。

不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
