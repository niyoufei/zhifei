# ZDoc Step 88: response-mode model/options comparison review

## 1. 阶段背景

Step 85 已完成 response-mode model/options comparison design。Step 86 已完成 model/options comparison smoke plan。Step 87 已完成 model/options comparison smoke + report。

Step 87 实测 `qwen3:0.6b` 与 `qwen3:8b`。Step 87 未测试 `qwen3:14b`、30b、32b、80b 类模型。

Step 87 的目标是验证不同本地模型 / options profile 对 `response_mode` 的影响，重点观察是否存在比 `qwen3:0.6b` 更低 `thinking_only_fallback` 的本地模型，以及 `response_advisory` / `json_advisory` / `text_fallback` 是否在更强模型或不同 options 下出现。

当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。本步为 docs-only review，不运行模型，不启动服务，不修改代码或 tests。

## 2. Step 87 已证明的事实

Step 87 已证明以下事实：

* Ollama `/api/tags` 可达，HTTP 200，valid JSON；
* 本地共有 7 个模型；
* 实际参与对比模型为 `qwen3:0.6b` 与 `qwen3:8b`；
* `qwen3:14b` 为控制矩阵规模跳过；
* 30b / 32b / 80b 类模型因资源风险未测试；
* disabled 场景受控；
* adapter-off compatible payload 正常；
* adapter-off illegal field controlled failure；
* 13 个 enabled 请求均受控；
* 未出现 `response_advisory`；
* 未出现 `json_advisory`；
* 未出现 `text_fallback`；
* `thinking_only_fallback=12`；
* `malformed_response=1`；
* generated-preview-as-evidence 防护有效；
* evidence missing 防护有效；
* `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 全部恒 false；
* 未写 `output/job/export`；
* 未触发正式链路。

这些事实说明 Step 87 的 runtime smoke 和隔离边界受控，但不说明当前模型已满足 shadow generation 或正式生成链准入条件。

## 3. Step 87 结果复盘

Step 87 的模型分布如下：

* `qwen3:0.6b`：8 次，`thinking_only_fallback=7`，`malformed_response=1`；
* `qwen3:8b`：5 次，`thinking_only_fallback=5`。

总统计如下：

```text
response_advisory=0
json_advisory=0
text_fallback=0
thinking_only_fallback=12
malformed_response=1
```

安全与 evidence 统计如下：

```text
generated-preview-as-evidence detected=2
generated content evidence blocked=2
evidence missing 2 次，均 review_required
正式链准入字段全 false
```

Step 87 未观察到 timeout。唯一 enabled controlled failure 是 `qwen3:0.6b / O1 / MC-B` 的 `malformed_response`，对应 JSON-first payload，`quality_status=blocked`，`fallback_reason=malformed_json`。

## 4. 关键结论

关键结论如下：

* `qwen3:8b` 未降低 thinking fallback；
* `qwen3:8b` 未产生 `response_advisory`；
* `qwen3:8b` 未产生 `json_advisory`；
* `qwen3:8b` 未产生 `text_fallback`；
* 当前 0.6b / 8b 对 response-mode 改善均不理想；
* 单纯继续在 0.6b / 8b 上微调 prompt 收益可能有限；
* 当前不具备 shadow generation 准入条件；
* 当前不得进入正式生成链。

与 Step 83 相比，Step 87 的结果更保守：Step 83 仍出现 `text_fallback=1`，而 Step 87 在 0.6b / 8b comparison matrix 中未出现 `text_fallback`。这说明 `text_fallback` 目前仍不能视为稳定路径。

## 5. 是否测试 qwen3:14b 的判断

从 docs-only 角度看，`qwen3:14b` 可能提供更强输出稳定性。Step 87 已通过 `/api/tags` 记录其存在，但为了控制矩阵规模和资源风险未测试。

是否测试 `qwen3:14b` 的判断如下：

* `qwen3:14b` 可能比 8b 更容易形成普通 response 或 JSON response；
* 但 `qwen3:14b` 资源占用高于 8b；
* 需单独设计轻量化 targeted smoke；
* 不应直接纳入大矩阵；
* 如测试，应限制 payload 数量、profile 数量、timeout、num_predict；
* 仍不得下载模型；
* 仍不得进入正式链。

建议后续若测试 `qwen3:14b`，仅做 targeted response-mode smoke，而不是继续扩大 model/options matrix。

## 6. 是否测试 30b / 32b / 80b 的判断

30b / 32b / 80b 类模型资源风险更高。它们可能输出更长内容，增加误用为正式正文风险。

当前判断如下：

* 30b / 32b / 80b 类模型需单独授权；
* 不应在当前阶段默认测试；
* 若后续考虑，应先做资源风险评估和极小样本 smoke plan；
* 高规格模型仍必须只走 `/local-llm/preview-safe`；
* 不得直接请求 Ollama `/api/generate`；
* 不得自动 pull / 下载；
* 不得把模型输出解释为正式链准入。

推理型模型尤其需要谨慎，因为它们可能进一步增强 thinking 输出倾向，而不是降低 `thinking_only_fallback`。

## 7. 当前推荐路线

当前推荐路线为保守路线：

* 先不进入 shadow generation；
* 先做 `qwen3:14b` targeted response-mode smoke plan；
* 仅验证少量 payload：
  * response-first；
  * JSON-first；
  * text-fallback；
  * generated-preview-as-evidence guard；
* 如果 14b 仍无法明显改善，则考虑接受 thinking fallback 仅作为 preview-only，或再评估更强模型；
* 所有情况下 formal flags 继续恒 false。

`qwen3:14b` targeted smoke 的目标不应是证明可进入正式链，而应是回答一个更窄的问题：在相同 no-write / preview-only / evidence guard 下，14b 是否能比 0.6b / 8b 更稳定地产生非-thinking response mode。

## 8. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 Step 87 结果说明当前 `qwen3:0.6b` 与 `qwen3:8b` 均不满足 shadow generation 前置 response-mode 稳定条件。正式链前仍需完成模型/参数进一步评估、shadow generation design、candidate patch、人工确认、diff、rollback、DOCX 导出一致性、ZBid 写回隔离和真实资料 evidence source 映射。

即使后续 `qwen3:14b` 或更强模型产生 `response_advisory` / `json_advisory` / `text_fallback`，也只能作为 shadow generation readiness 的前置证据，不得直接进入正式生成链。

## 9. 风险与回滚

当前风险如下：

* 风险 1：把 `qwen3:8b` 作为升级模型但实际无改善；
* 风险 2：继续扩大模型矩阵导致资源不可控；
* 风险 3：更强模型输出更长，增加误用风险；
* 风险 4：thinking fallback 高频被误读为可接受；
* 风险 5：模型比较结果被误解为正式链准入；
* 风险 6：后续模型切换破坏 preview-only / no-write。

回滚措施：保持 `qwen3:0.6b` preview-only 基线。

兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

同时必须保留 disabled / adapter-off / fake-only 路径。出现异常时不得扩大到正式链路，不得进入 shadow generation、candidate patch、DOCX 导出或 ZBid 写回。

## 10. 当前阶段结论

本阶段仅完成 model/options comparison smoke review，未证明 `qwen3:0.6b` 或 `qwen3:8b` 的 response-mode 满足 shadow generation 条件，也未进入正式生成链。

Step 87 已证明 model/options comparison runtime smoke 受控，generated-preview-as-evidence 与 evidence missing 防护有效，formal flags 恒 false；但 `response_advisory=0`、`json_advisory=0`、`text_fallback=0`，且 `qwen3:8b` 为 5/5 `thinking_only_fallback`。因此当前不能进入 shadow generation 或正式生成链。

## 11. 下一步建议

下一步建议为 ZDoc Step 89：qwen3:14b targeted response-mode smoke plan，docs-only。不得直接进入 qwen3:14b runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
