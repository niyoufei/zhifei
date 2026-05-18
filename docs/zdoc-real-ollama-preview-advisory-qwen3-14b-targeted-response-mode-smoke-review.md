# ZDoc Step 91: qwen3:14b targeted response-mode smoke review

## 1. 阶段背景

Step 87 已完成 `qwen3:0.6b` / `qwen3:8b` model/options comparison smoke。Step 88 已完成 model/options comparison review。Step 89 已完成 `qwen3:14b` targeted response-mode smoke plan。Step 90 已完成 `qwen3:14b` targeted response-mode smoke + report。

Step 90 已确认 `qwen3:14b` 存在。Step 90 enabled `qwen3:14b` 5/5 HTTP 200、5/5 `status=ok`、5/5 `calls_ollama=true`。

Step 90 结果为 5/5 `thinking_only_fallback`，未出现 `response_advisory` / `json_advisory` / `text_fallback`。正式链准入字段全部恒 false。

当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。本步为 docs-only 复盘步骤，不运行测试，不启动服务，不运行 Ollama，不修改代码或 tests。

## 2. Step 90 已证明的事实

Step 90 已证明以下事实：

* `qwen3:14b` 已存在；
* Ollama `/api/tags` 可达，HTTP 200，valid JSON；
* 本地共有 7 个模型；
* FastAPI loopback runtime smoke 受控；
* disabled 场景受控；
* adapter-off compatible payload 受控；
* enabled `qwen3:14b` 5/5 HTTP 200；
* enabled `qwen3:14b` 5/5 `status=ok`；
* enabled `qwen3:14b` 5/5 `calls_ollama=true`；
* generated-preview-as-evidence 防护有效；
* evidence missing 防护有效；
* `formal_generation_allowed` 恒 false；
* `shadow_candidate_allowed` 恒 false；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 恒 false；
* 未请求 `/generate`；
* 未请求 `/export_docx`；
* 未请求 `/review/apply`；
* 未直接请求 Ollama `/api/generate`；
* 未写 `output/job/export`；
* FastAPI 与 Ollama 进程均已停止；
* `18762` 与 `11434` 端口均无监听。

这些事实说明 Step 90 的 runtime smoke 执行边界受控，但不说明 `qwen3:14b` 已满足 shadow generation 或正式生成链准入条件。

## 3. Step 90 结果复盘

Step 90 摘要如下：

* `qwen3:14b` 是否存在：存在；
* disabled：HTTP 200，`status=disabled`，`calls_ollama=false`；
* adapter-off compatible：HTTP 200，`status=ok`，`calls_ollama=false`；
* enabled `qwen3:14b`：5/5 HTTP 200，5/5 `status=ok`，5/5 `calls_ollama=true`；
* Q14-A：`thinking_only_fallback / review_required / not_required`；
* Q14-B：`thinking_only_fallback / review_required / not_required`；
* Q14-C：`thinking_only_fallback / review_required / not_required`；
* Q14-D：`thinking_only_fallback / blocked / invalid_anchor`；
* Q14-E：`thinking_only_fallback / review_required / missing`；
* generated-preview-as-evidence detected=1，blocked=1；
* evidence missing 为 `missing`，formal 不放行；
* 正式链准入字段全 false。

`qwen3:14b` `response_mode` 统计：

* `response_advisory=0`；
* `json_advisory=0`；
* `text_fallback=0`；
* `thinking_only_fallback=5`；
* `malformed_response=0`；
* `timeout=0`。

Step 90 的正向事实是 runtime、adapter-off、generated-preview-as-evidence、evidence missing 与 formal flags 防线均受控。负向事实是 `qwen3:14b` 没有带来 response-mode 改善。

## 4. 与历史模型结果对比

`qwen3:0.6b` 历史表现：

* 8 次中 `thinking_only_fallback=7`；
* `malformed_response=1`。

`qwen3:8b` 历史表现：

* 5 次中 `thinking_only_fallback=5`。

`qwen3:14b` 本次表现：

* 5 次中 `thinking_only_fallback=5`；
* `response_advisory=0`；
* `json_advisory=0`；
* `text_fallback=0`。

结论：

* `qwen3:14b` 未改善 response-mode；
* `qwen3:14b` 未降低 thinking fallback；
* `qwen3:14b` 未产生 `response_advisory` / `json_advisory` / `text_fallback`；
* 0.6b、8b、14b 均未满足 shadow generation 前置 response-mode 条件。

从 Step 87 到 Step 90，模型从 0.6b 扩展到 8b，再 targeted 到 14b，response-mode 分布仍未出现非-thinking advisory 模式。该结果应被视为模型/输出路径层面的阶段性边界，而不是继续扩大矩阵的直接理由。

## 5. 关键结论

`qwen3:14b` 虽为更大模型，但在本项目 safe endpoint / prompt profile / options 下仍高度依赖 `thinking_only_fallback`。

继续简单扩大到 14b 并未解决 response-mode 问题。当前问题可能不是单纯模型大小问题，也可能与 Ollama 响应结构、模型输出习惯、prompt profile、options 或 adapter normalization 有关。

当前不具备 shadow generation 准入条件，当前不得进入正式生成链。

本阶段应把 `qwen3:14b` 的结果解释为：更大本地模型在当前约束下仍可受控运行，但没有证明可稳定输出 `response_advisory`、`json_advisory` 或 `text_fallback`。

## 6. 是否继续测试 30b / 32b / 80b 的判断

从 docs-only 角度看，30b / 32b / 80b 类模型资源占用明显更高。更大模型可能输出更长，更容易被误用为正式正文。推理型模型可能仍高度依赖 thinking。

如果继续测试，应单独设计极小样本 smoke，不建议自动扩大矩阵。不得直接进入 30b / 32b / 80b runtime smoke。

继续更大模型测试前，需要先做更高层的 response-mode strategy decision，明确是否仍追求 `response_advisory` / `json_advisory`，是否接受 `thinking_only_fallback` 作为 preview-only advisory，是否需要 adapter / normalization 调整，以及是否需要把 shadow generation 继续后移。

## 7. 当前推荐路线

当前推荐路线如下：

* 不进入 shadow generation；
* 不继续无控制扩大模型矩阵；
* 先做 response-mode strategy decision；
* 分析是否继续追求 `response_advisory` / `json_advisory`；
* 分析是否接受 `thinking_only_fallback` 仅作为 preview-only advisory；
* 分析是否需要调整 adapter normalization 或 prompt/output options；
* 分析是否需要把 shadow generation 推迟到更稳定模型或更强证据锚点之后；
* 保持 formal flags 全 false。

该路线比继续直接测试更大模型更保守，也更符合 Step 90 暴露出的核心问题：模型规模提升没有自然转化为 response-mode 改善。

## 8. 后续策略选项

以下为可选路径，本步不执行。

路径 A：继续模型对比

* 单独设计 `qwen3:30b` 或 `qwen3-coder:30b` 极小样本 smoke；
* 优点：可能改善 response mode；
* 风险：资源高、输出长、仍可能 thinking fallback。

路径 B：接受 `thinking_only_fallback` 仅作为 preview-only

* 将 `thinking_only_fallback` 固定为 `review_required`；
* 不允许进入 `shadow_candidate`；
* 用于人工参考，不作为候选正文；
* 优点：保守、可控；
* 风险：无法推进正式生成链。

路径 C：改造 adapter / normalization 策略

* 更强地从模型输出中抽取 user-facing advisory；
* 保持 bounded、no-write、evidence-aware；
* 优点：可能改善 `response_mode`；
* 风险：可能把低质量 thinking 包装成 advisory，必须强门禁。

路径 D：推迟 shadow generation，先完善 evidence source mapping

* 继续建设证据源映射、人工确认、diff/rollback；
* 优点：降低正式链风险；
* 风险：正式生成链推进速度更慢。

以上路径都不得绕过 evidence anchor、quality gate、input-risk gate、preview-only / no-write 边界，也不得把模型输出直接作为 evidence。

## 9. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 Step 90 结果说明 `qwen3:14b` 仍不满足 response-mode 稳定条件。正式链前仍需解决 response-mode strategy、evidence anchor、quality gate、input-risk gate、shadow generation、candidate patch、人工确认、diff、rollback、DOCX 导出一致性和 ZBid 写回隔离。

即使后续选择继续更大模型、adapter normalization 或 thinking fallback policy，也必须先经过 docs-only design、fake-only tests、runtime smoke、smoke review 与人工确认，不得直接进入正式链。

## 10. 风险与回滚

当前风险如下：

* 风险 1：将 `qwen3:14b` 作为升级模型但实际无 response-mode 改善；
* 风险 2：继续扩大模型测试导致资源不可控；
* 风险 3：更强模型输出更长，增加误用风险；
* 风险 4：thinking fallback 高频被误读为可接受；
* 风险 5：模型测试结果被误解为 shadow generation 准入；
* 风险 6：后续 adapter 抽取策略把低质量 thinking 包装为 advisory。

回滚措施：保持 `qwen3:0.6b` preview-only 基线。

兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路，不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

## 11. 当前阶段结论

Step 90 已证明 qwen3:14b targeted runtime smoke 受控，但 qwen3:14b 5/5 仍为 thinking_only_fallback，未出现 response_advisory / json_advisory / text_fallback，因此不得进入 shadow generation 或正式生成链。

本阶段仅完成 docs-only smoke review，不实现代码，不运行测试，不启动服务，不运行 Ollama，不进入更大模型 runtime smoke、shadow generation 或正式生成链。

## 12. 下一步建议

下一步建议为 ZDoc Step 92：response-mode strategy decision design，docs-only。不得直接进入更大模型 runtime smoke、adapter implementation、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
