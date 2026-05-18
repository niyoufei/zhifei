# ZDoc Step 84: second-round response-mode runtime smoke review + follow-up design

## 1. 阶段背景

Step 80 已完成 second-round response-mode prompt tuning fake-only implementation + deterministic tests。Step 81 已完成 fake-stage review。Step 82 已完成 second-round response-mode runtime smoke plan refresh。Step 83 已完成 second-round response-mode runtime smoke + smoke report。

Step 83 enabled payload 7/7 HTTP 200、7/7 `status=ok`、7/7 `calls_ollama=true`。adapter-off compatible payload 正常，adapter-off illegal field 仍为 controlled failure。generated-preview-as-evidence 回归仍有效，正式链准入字段全部恒 false。

但 Step 83 显示 `thinking_only_fallback` 仍为 6/7，`response_advisory=0`，`json_advisory=0`，`text_fallback=1`。当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

本步为 docs-only runtime smoke 复盘与 follow-up design，不实现代码，不运行测试，不启动服务，不运行 Ollama。

## 2. Step 83 已证明的事实

Step 83 已证明以下事实：

* 本地 Ollama 可达；
* `qwen3:0.6b` 存在；
* FastAPI loopback runtime smoke 受控；
* disabled 场景 stable disabled；
* adapter-off compatible payload 正常；
* adapter-off illegal field 为 controlled failure；
* enabled 7/7 HTTP 200；
* enabled 7/7 `status=ok`；
* enabled 7/7 `calls_ollama=true`；
* `text_fallback` 仍可出现 1 次；
* generated-preview-as-evidence 回归仍有效；
* `generated_content_evidence_blocked` 仍可追踪；
* `formal_generation_allowed` 恒 false；
* `shadow_candidate_allowed` 恒 false；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 恒 false；
* 未请求 `/generate`；
* 未请求 `/export_docx`；
* 未请求 `/review/apply`；
* 未直接请求 Ollama `/api/generate`；
* 未写 `output/job/export`；
* FastAPI 与 Ollama 进程均已停止；
* `18760` 与 `11434` 端口均无监听。

这些事实说明 Step 83 的 runtime smoke 执行边界受控，但不说明 response-mode 已达到 shadow generation 或正式生成链准入条件。

## 3. Step 83 结果复盘

Step 83 摘要如下：

* disabled：HTTP 200，`status=disabled`，`calls_ollama=false`，preview-only/no-write；
* adapter-off compatible：HTTP 200，`status=ok`，`calls_ollama=false`，未误触 illegal field；
* adapter-off illegal field：HTTP 200，`status=failure`，`error_type=illegal_field`，`reason=illegal_field:content`；
* enabled 7/7 HTTP 200，7/7 `status=ok`，7/7 `calls_ollama=true`；
* SRT-A：`thinking_only_fallback / response_first / review_required`；
* SRT-B：`thinking_only_fallback / json_first / review_required`；
* SRT-C：`text_fallback / text_fallback / review_required`；
* SRT-D：`thinking_only_fallback / response_first / review_required`；
* SRT-E：`thinking_only_fallback / response_first / review_required`，evidence `missing`；
* SRT-F：`thinking_only_fallback / response_first / blocked`，evidence `invalid_anchor`；
* SRT-G：`thinking_only_fallback / response_first / blocked`，evidence `invalid_anchor`；
* `response_advisory=0`；
* `json_advisory=0`；
* `text_fallback=1`；
* `thinking_only_fallback=6`；
* `empty_response=0`；
* `malformed_response=0`；
* `normalization_failure=0`；
* `system_error=0`；
* `generated_preview_as_evidence_detected` 次数 = 2；
* `generated_content_evidence_blocked` 次数 = 2；
* thinking fallback 出现次数 = 6；
* 正式链准入字段全 false。

Prompt metadata 在 enabled 场景稳定返回：7/7 enabled payload 均返回 `prompt_profile=second_round_response_mode_tuning`、`prompt_version=zdoc_response_mode_prompt_v2`、`prompt_tuning_applied=true`、`adapter_schema_mode=compatible`。

## 4. 关键进展判断

Step 83 已证明二轮 response-mode runtime smoke 受控。adapter-off schema follow-up 受控，generated-preview-as-evidence 防护未回归，no-write / preview-only / formal chain isolation 稳定。

Step 83 相比 Step 77 的一个正向变化是 `malformed_response` 从 Step 77 的 1 次降为 0。`text_fallback` 仍保持 1 次。

但 `response_advisory` 和 `json_advisory` 仍未出现。`thinking_only_fallback` 从 Step 77 的 4/6 变为 Step 83 的 6/7，未改善。该结果不支持进入 shadow generation 或正式生成链。

当前应将 Step 83 解释为：runtime 边界、metadata 和安全 guard 稳定，但 qwen3:0.6b 的 response-mode 输出能力仍不足。

## 5. 剩余缺口定义

缺口 1：`response_advisory` 仍未出现。

二轮 response-first prompt 后，SRT-A 仍为 `thinking_only_fallback`。`response_first` prompt 在真实 runtime 下仍未形成 ordinary `response_advisory`。后续需要考虑更强模型、runtime option、prompt profile 或模型能力边界。

缺口 2：`json_advisory` 仍未出现。

二轮 JSON-first prompt 后，SRT-B 仍为 `thinking_only_fallback`。虽然未再出现 `malformed_response`，但也未形成 `json_advisory`。JSON-first prompt 对 `qwen3:0.6b` 仍不稳定。

缺口 3：`thinking_only_fallback` 仍高依赖。

7 个 enabled payload 中 6 个仍为 `thinking_only_fallback`。二轮 prompt tuning 没有实现预期改善。真实 runtime 仍不具备进入 shadow generation 的 response-mode 条件。

缺口 4：`text_fallback` 样本仍不足。

`text_fallback` 继续出现 1 次。但样本量有限，不能证明稳定。`text_fallback` 也仍是 preview advisory 兜底，不是正式正文能力。

## 6. 与 Step 77 对比分析

Step 77：

* `response_advisory=0`；
* `json_advisory=0`；
* `text_fallback=1`；
* `thinking_only_fallback=4`；
* `malformed_response=1`。

Step 83：

* `response_advisory=0`；
* `json_advisory=0`；
* `text_fallback=1`；
* `thinking_only_fallback=6`；
* `malformed_response=0`。

结论：

* `malformed_response` 得到改善；
* `text_fallback` 未进一步提升；
* thinking fallback 反而占比仍高；
* `response_advisory` / `json_advisory` 均未出现；
* 二轮 prompt tuning 在 `qwen3:0.6b` 真实 runtime 下改善有限。

该对比说明继续只做同类 prompt 文本微调，可能收益递减。下一步更适合先设计模型与参数对比，而不是直接进入第三轮 runtime smoke。

## 7. 模型能力边界分析

当前使用模型为 `qwen3:0.6b`。该模型已证明可通过 safe endpoint 触发真实 runtime，但在 Step 70、Step 77、Step 83 连续 smoke 中仍高度依赖 thinking fallback。

小模型可能更容易输出 thinking 而非稳定 response 字段。prompt tuning 对小模型 response-mode 改善有限。Step 83 中 JSON-first 不再 malformed，但仍未形成 `json_advisory`，说明格式约束改善了失败类型，却没有解决 response 字段稳定性。

后续可能需要设计 model comparison plan。可考虑 `qwen3:8b` 或更强本地模型作为对照，但不得本步执行。模型切换必须单独计划、单独授权、保持 no-write 和 preview-only，并继续只通过 `/local-llm/preview-safe` 验证。

任何模型比较都必须先确认模型已本地存在。不得 pull、不得下载、不得访问外网。

## 8. 后续方向建议

后续可从 docs-only 角度提出以下方向：

* response-mode model comparison plan；
* `qwen3:0.6b` vs `qwen3:8b` 或其他已存在模型的 runtime smoke plan；
* response-mode option tuning plan；
* thinking fallback acceptability policy；
* `text_fallback` stabilization plan；
* JSON advisory 降级策略；
* 继续保持 evidence anchor / quality gate / input-risk gate；
* 不进入 shadow generation。

model comparison plan 应优先回答：更强本地模型是否能在同样 no-write / preview-only 边界下更稳定地产生 `response_advisory` 或 `json_advisory`。option tuning plan 应优先回答：`num_predict`、timeout、context 压缩或其他已存在选项是否会影响 response-mode 分布。

## 9. 是否继续 prompt tuning 的判断

单纯继续在 `qwen3:0.6b` 上做 prompt 文本微调，收益可能有限。Step 83 已显示二轮 prompt tuning 后 `response_advisory` / `json_advisory` 仍为 0，`thinking_only_fallback` 仍为 6/7。

继续 prompt tuning 前应先做 model/options 层面的设计。如果仍坚持 `qwen3:0.6b`，应接受 `thinking_only_fallback` 高频，并将其限定为 preview-only。

如果目标是 shadow generation 前置能力，应考虑更强模型或更稳定 response 输出路径。任何模型/参数变更都不得跳过 runtime smoke 与 quality gate。

即使后续出现 `response_advisory` 或 `json_advisory`，也不得自动进入 shadow generation。它们仍需 evidence anchor、quality gate、input-risk gate、candidate patch 设计、人工确认和 rollback 方案。

## 10. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 Step 83 说明当前 `qwen3:0.6b` response-mode 仍不满足 shadow generation 准入条件。正式链前仍需完成 response-mode 稳定性、模型/参数对比、evidence anchor、quality gate、input-risk gate、shadow generation、candidate patch、人工确认、diff、rollback、DOCX 导出一致性和 ZBid 写回隔离。

当前阶段不得进入 shadow generation、candidate patch、正式正文写回、DOCX 导出或 ZBid 写回。

## 11. 风险与回滚

当前风险如下：

* 风险 1：将 `thinking_only_fallback` 高频误判为可接受；
* 风险 2：将 `text_fallback=1` 误判为稳定；
* 风险 3：继续 prompt tuning 但收益递减；
* 风险 4：模型切换后破坏 no-write / preview-only 边界；
* 风险 5：更强模型输出更长内容，增加正式正文误用风险；
* 风险 6：runtime smoke 结果被误解为 shadow generation 准入。

回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路，不得进入 shadow generation、candidate patch、DOCX 导出或 ZBid 写回。

## 12. 当前阶段结论

Step 83 已证明 second-round response-mode runtime smoke 受控，adapter-off schema 与 generated-preview-as-evidence 回归稳定，formal flags 恒 false；但 `response_advisory` / `json_advisory` 仍为 0，`thinking_only_fallback` 仍为 6/7，因此不得进入 shadow generation 或正式生成链。

本阶段仅完成 docs-only runtime smoke 复盘与 follow-up design，未实现代码，未运行测试，未启动服务，未运行 Ollama，未进入 model comparison runtime smoke、shadow generation 或正式生成链。

## 13. 下一步建议

下一步建议为 ZDoc Step 85：response-mode model/options comparison design，docs-only；不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
