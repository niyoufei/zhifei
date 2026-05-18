# ZDoc Step 92: response-mode strategy decision design

## 1. 阶段背景

`qwen3:0.6b` 已完成多轮 runtime smoke。`qwen3:8b` 已完成 model/options comparison smoke。`qwen3:14b` 已完成 targeted response-mode smoke。

`qwen3:0.6b`、`qwen3:8b`、`qwen3:14b` 均未稳定产生 `response_advisory` / `json_advisory`。`qwen3:14b` 在 Step 90 targeted smoke 中 5/5 仍为 `thinking_only_fallback`。

当前 response-mode 仍不满足 shadow generation 前置条件。当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

Step 92 的目标是形成 response-mode 后续策略决策框架，而不是继续盲目测试模型或直接写代码。本步为 docs-only 设计，不运行模型，不启动服务，不执行 runtime smoke，不修改代码或 tests。

## 2. 已完成验证事实汇总

已完成验证事实如下：

* `qwen3:0.6b` 历史表现：8 次中 `thinking_only_fallback=7`，`malformed_response=1`；
* `qwen3:8b` 历史表现：5 次中 `thinking_only_fallback=5`；
* `qwen3:14b` 本次表现：5 次中 `thinking_only_fallback=5`；
* `response_advisory` 在上述 runtime 中均未稳定出现；
* `json_advisory` 在上述 runtime 中均未稳定出现；
* `text_fallback` 仅曾出现少量样本，稳定性不足；
* generated-preview-as-evidence 防护有效；
* evidence missing 防护有效；
* quality gate / input-risk / evidence anchor / no-write / preview-only 边界稳定；
* `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 全部恒 false。

这些事实说明，系统已经具备可控的 preview runtime 与安全 guard 基础，但真实 runtime 下的 response-mode 输出仍未达到 shadow generation 前置要求。

## 3. 当前核心问题判断

当前瓶颈不是单纯“模型是否能调用”。Step 83、Step 87、Step 90 均证明本地 runtime 可通过 safe endpoint 受控触发。

当前瓶颈不是 safe endpoint 是否受控。disabled、adapter-off、enabled real adapter、generated-preview-as-evidence、evidence missing 等路径均已在多轮 smoke 中保持受控。

当前瓶颈不是 no-write 边界。现有 smoke 均未写 `output/job/export`，未触发 `/generate`、`/export_docx`、`/review/apply`，formal flags 均保持 false。

当前瓶颈是：真实 runtime 下模型输出长期依赖 `thinking_only_fallback`，无法稳定形成可追踪的 `response_advisory` / `json_advisory`。

该问题影响 shadow generation 前置条件。该问题解决前，不能进入正式正文生成、章节改写、DOCX 导出或 ZBid 写回。

## 4. 策略选项 A：继续测试更大模型

可选对象包括：

* `qwen3:30b`；
* `qwen3-coder:30b`；
* `deepseek-r1:32b`；
* `qwen3-next:80b-a3b-instruct-q8_0`。

潜在优点：

* 更大模型可能改善 `response_mode`；
* 可能更容易输出普通 response 或结构化 JSON；
* 可为长期模型选型提供更多对照证据。

主要风险：

* 资源占用高；
* 输出更长；
* thinking fallback 未必下降；
* 误用为正式正文风险更高；
* 推理型模型可能进一步强化 thinking 输出；
* 大模型 smoke 更容易拉长执行时间和进程清理风险。

该路径需要单独 smoke plan，不得默认进入。不得自动 pull / 下载模型。不得作为正式链准入依据。

结论建议：

* 不建议立即扩大到 30b / 32b / 80b；
* 如后续确需测试，应先做极小样本、单模型、单目的 smoke plan。

## 5. 策略选项 B：接受 thinking_only_fallback 仅作为 preview-only advisory

该策略保留当前模型链路，不强行把 `thinking_only_fallback` 解释为稳定 response-mode。

约束如下：

* `thinking_only_fallback` 继续 `review_required`；
* 不进入 `shadow_candidate`；
* 不进入 candidate patch；
* 不进入正式正文；
* 不触发 DOCX 导出；
* 不写回 ZBid；
* 适合作为人工参考建议；
* 不适合作为正式生成链候选内容来源。

优点是保守、可控、与当前多轮 smoke 事实一致。缺点是不能支撑最终正式生成链目标。

结论建议：

* 可作为短期稳定策略；
* 但不能支撑最终正式生成链目标。

## 6. 策略选项 C：改造 adapter / normalization 抽取策略

该策略尝试从模型输出中提取 user-facing advisory，或尝试把 thinking 中的可用建议转为 bounded advisory。

必要约束如下：

* 必须防止把低质量 reasoning 包装为正式建议；
* 必须继续受 quality gate / input-risk / evidence anchor 控制；
* 必须保持 no-write；
* 必须保持 formal flags false；
* 必须继续阻止 generated preview 被当作 evidence；
* 必须保留 disabled / adapter-off / fake-only 路径；
* 必须通过严格 fake-only tests 与 runtime smoke。

潜在优点：

* 可能改善 `response_mode`；
* 可能让模型输出中的用户可见建议更可追踪；
* 可能降低 `thinking_only_fallback` 对人工阅读的负担。

主要风险：

* 可能把低质量 thinking 包装成 advisory；
* 可能掩盖模型未稳定输出 response 的事实；
* 可能弱化 review_required 的边界；
* 如果 guard 不足，可能被误解为 shadow candidate 或正式正文。

结论建议：

* 可作为中期探索方向；
* 但必须先设计 guard，不能直接实现。

## 7. 策略选项 D：暂停 response-mode 深挖，转向 evidence source mapping / shadow readiness

现有 preview 安全底座较完整。evidence anchor、quality gate、input-risk、generated-preview-as-evidence 已具备初步框架。

该策略先推进真实资料 evidence source mapping、人工确认、diff/rollback、shadow readiness 设计。shadow generation 仍不得开启，只做 readiness。

优点：

* 降低正式链污染风险；
* 先完善正式链前的安全闭环；
* 避免在 response-mode 尚未稳定时盲目追求模型输出；
* 为后续 candidate patch 与正式写回提供更清晰的数据契约。

缺点：

* response-mode 问题仍未解决；
* 正式生成链推进速度更慢；
* 后续仍需要回到模型输出或 adapter 策略问题。

结论建议：

* 可作为保守推进路线；
* 适合继续围绕正式链安全闭环建设。

## 8. 推荐策略

推荐采用“B + D 为主，C 为后续预研，A 暂缓”的策略。

短期：

* 接受 `thinking_only_fallback` 仅作为 preview-only / `review_required`；
* 不进入 shadow；
* 不进入 candidate patch；
* 不进入正式正文；
* 不触发 DOCX 导出或 ZBid 写回。

中期：

* 推进 evidence source mapping；
* 推进 human approval；
* 推进 diff/rollback；
* 推进 shadow readiness 设计；
* 继续保持 formal flags 全 false。

后续：

* 如必须提升 response-mode，再单独设计 adapter/normalization guard 或更大模型极小样本测试；
* adapter / normalization 只能在 guard 设计和 fake-only tests 之后进入实现；
* 更大模型测试只能在单独 smoke plan 授权后执行。

暂缓：

* 不继续默认测试 30b / 32b / 80b。

严禁：

* 不得因 runtime smoke 受控而进入正式链；
* 不得把 `thinking_only_fallback` 解释为正式正文能力；
* 不得把 model-generated preview 当作 evidence。

## 9. shadow generation readiness 边界

当前不得进入 shadow generation implementation。

可以进入 shadow generation readiness design。readiness design 只能定义：

* 条件；
* 数据契约；
* 人工确认；
* diff/rollback；
* evidence trace；
* no-write boundary；
* 禁止正式写回。

readiness design 不得生成 candidate patch，不得写正文，不得导出 DOCX，不得写回 ZBid。

readiness design 应明确：即使将来允许 shadow generation，也只能生成候选，不能直接写正式正文；候选必须可 diff、可撤销、可人工确认，并带 evidence trace。

## 10. 正式链准入条件草案

后续进入正式链前至少需要满足：

* quality gate 稳定；
* input-risk gate 稳定；
* evidence anchor 稳定；
* generated-preview-as-evidence 防护稳定；
* response-mode 策略明确；
* shadow generation 仅生成候选，不写正式正文；
* candidate patch 可 diff；
* 人工确认写回；
* 可 rollback；
* DOCX 导出一致性校核；
* ZBid 写回隔离；
* 全链路审计日志；
* 仍需独立授权，不得自动进入。

这些条件不是 Step 92 的执行目标，而是后续正式链准入前的最低草案。任何一个条件未满足，都不得进入正式正文生成、章节改写、DOCX 导出或 ZBid 写回。

## 11. 后续阶段建议

建议下一步为 ZDoc Step 93：shadow generation readiness design，docs-only。

该步骤只设计：

* shadow generation 前置条件；
* candidate patch 数据结构；
* evidence trace；
* human approval；
* diff/rollback；
* no-write boundary；
* 禁止正式写回。

不得执行 shadow generation。

Step 93 仍应只新增计划文档，不修改代码，不运行模型，不启动服务，不生成 candidate patch，不写正文，不导出 DOCX，不写回 ZBid。

## 12. 与最终目标关系

最终目标仍是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但当前 response-mode 策略决策应优先保障安全边界，不应为了追求生成链速度而跳过 evidence anchor、human approval、diff/rollback 和 writeback isolation。

当前阶段的合理推进方向不是直接提升生成权限，而是先明确 response-mode 可接受边界、完善 evidence trace 与人工确认链路，并将任何模型输出继续限制在 preview-only / no-write 范围内。

## 13. 风险与回滚

当前风险如下：

* 风险 1：误把 `thinking_only_fallback` 当作正式生成能力；
* 风险 2：盲目扩大模型测试导致资源不可控；
* 风险 3：adapter 抽取策略把低质 reasoning 包装为 advisory；
* 风险 4：跳过 evidence source mapping 进入 shadow generation；
* 风险 5：没有 human approval 就写正文；
* 风险 6：DOCX / ZBid 写回缺少 rollback。

回滚措施：保持 `qwen3:0.6b` preview-only 基线。

兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路，不得进入 shadow generation implementation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

## 14. 当前阶段结论

本阶段仅完成 response-mode strategy decision 的 docs-only 设计，未运行模型，未启动服务，未执行 runtime smoke，未进入 shadow generation 或正式生成链。

## 15. 下一步建议

下一步建议为 ZDoc Step 93：shadow generation readiness design，docs-only。不得直接进入 shadow generation implementation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。
