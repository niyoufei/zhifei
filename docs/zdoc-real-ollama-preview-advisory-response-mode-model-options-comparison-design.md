# ZDoc Step 85: response-mode model/options comparison design

## 1. 阶段背景

Step 77 首次观察到 `text_fallback=1`，但 `thinking_only_fallback` 仍为 `4/6`。该阶段说明第一轮 prompt tuning 已经让真实 runtime 不再完全依赖 thinking fallback，但普通 `response_advisory` 与 `json_advisory` 仍未出现。

Step 80 完成二轮 response-mode prompt tuning fake-only implementation + deterministic tests，覆盖了 response-first、JSON-first、text-fallback、adapter schema、prompt_mode metadata、generated-preview-as-evidence 回归，以及 evidence anchor / quality gate / input-risk / safe endpoint 回归。

Step 83 完成二轮 response-mode runtime smoke。Step 84 完成 runtime smoke review。Step 83 结果显示 `response_advisory=0`、`json_advisory=0`、`text_fallback=1`、`thinking_only_fallback=6/7`。二轮 prompt tuning 在 `qwen3:0.6b` 真实 runtime 下改善有限。

当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。Step 85 目标是设计 model/options comparison，不执行 runtime smoke。

## 2. 当前问题复述

当前主要问题如下：

* `qwen3:0.6b` 在多轮 runtime smoke 中长期高度依赖 `thinking_only_fallback`；
* `response_advisory` 与 `json_advisory` 在真实 runtime 下仍未出现；
* `text_fallback` 仅少量出现，稳定性不足；
* 单纯继续 prompt 文本微调可能收益有限；
* 需要从模型能力、运行参数、response mode、输出格式约束等角度进行对比设计；
* 任何模型或参数对比都必须保持 preview-only / no-write。

该问题不再只是 prompt 文案是否足够明确，而是需要判断模型能力、options 约束、JSON 输出能力、thinking 输出倾向和 evidence-aware guard 是否能在不同组合下稳定工作。

## 3. model/options comparison 总体目标

model/options comparison 的总体目标是：

* 比较不同本地模型对 `response_mode` 的影响；
* 比较不同 options 对 `response_mode` 的影响；
* 评估是否能降低 `thinking_only_fallback` 占比；
* 评估是否能稳定产生 `response_advisory` / `json_advisory` / `text_fallback`；
* 评估延迟、资源占用、稳定性和输出质量；
* 不进入正式生成链；
* 不写 `output/job/export`；
* 不触发 DOCX 导出；
* 不接 ZBid 写回。

comparison 的输出只应作为 preview runtime 稳定性与模型选型依据，不得作为正式链准入依据。

## 4. 候选模型设计

基于既有 smoke report 中出现过的本地模型信息，后续 comparison 可设计以下候选范围。该列表仅来自既有报告记录，不代表本步实时确认模型存在。后续 runtime 前必须再次通过 `/api/tags` 只读核验确认。

* `qwen3:0.6b`：当前基线模型，轻量但 thinking fallback 高依赖；
* `qwen3:8b`：潜在轻中量对照模型；
* `qwen3:14b`：潜在质量提升对照模型；
* `qwen3:30b`：潜在高质量对照模型；
* `qwen3-coder:30b`：代码/结构输出对照模型，需评估是否适合文档 advisory；
* `deepseek-r1:32b`：推理型对照模型，但可能更依赖 thinking；
* `qwen3-next:80b-a3b-instruct-q8_0`：高规格模型，需重点考虑资源占用与响应时间。

边界要求：

* 本步不启动 Ollama；
* 本步不调用 `/api/tags`；
* 本步不确认模型实时存在；
* 后续 runtime 前必须只读确认模型列表；
* 不得下载或 pull 缺失模型。

## 5. model comparison 维度设计

后续 model comparison 至少应记录以下维度：

* `response_advisory` 出现率；
* `json_advisory` 出现率；
* `text_fallback` 出现率；
* `thinking_only_fallback` 出现率；
* `malformed_response` 出现率；
* `empty_response` / timeout 出现率；
* `response_mode_confidence`；
* `quality_status` 分布；
* `evidence_anchor_status` 分布；
* generated-preview-as-evidence 拦截稳定性；
* formal chain flags 是否恒 false；
* 单 payload 响应时间；
* 多 payload 总耗时；
* 资源占用风险；
* 是否适合后续 shadow generation 前置阶段。

其中 `response_mode` 分布和 formal chain flags 是硬性观察项。延迟与资源占用是模型可用性判断项。任何模型即使响应质量更好，也必须继续满足 no-write、preview-only 和 formal-ineligible。

## 6. options comparison 维度设计

只读代码检查显示当前已有的关键运行变量包括：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`；
* `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
* `ZDOC_OLLAMA_PREVIEW_MODEL`；
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`；
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`。

当前实现中已稳定记录或使用的 prompt 相关字段包括：

* `prompt_mode`；
* `prompt_profile`；
* `prompt_version`；
* `prompt_tuning_applied`；
* `json_mode_requested`；
* `response_first_requested`；
* `text_fallback_allowed`；
* `evidence_aware_prompt_applied`；
* `adapter_schema_mode`。

后续 options comparison 至少应设计以下参数维度：

* `num_predict`：小值、中值对比；
* `temperature`：低值、默认值对比，该项需后续 runtime 前再次只读核验确认实际支持方式；
* `timeout`：短超时与中等超时对比；
* context 长度：极简、短输入、普通输入对比；
* format/json mode：如代码或 Ollama 支持，需单独验证，该项需后续 runtime 前再次只读核验确认；
* stop tokens：如支持，用于减少长 thinking，该项需后续 runtime 前再次只读核验确认；
* `prompt_profile` / `prompt_mode`：`response_first`、`json_first`、`text_fallback`、`evidence_aware`；
* model name：不同模型切换；
* host：必须限定 loopback；
* external API：禁止。

options 调整不得破坏 no-write / preview-only，不得绕过 evidence anchor，不得让任何正式链准入字段变为 true。

## 7. payload 设计

后续 comparison smoke 的最小 payload 集应全部为测试性、非真实投标正文，不得含真实招标文件内容。

Payload MC-A：response-first advisory

目标：观察 `response_advisory`。

内容方向：要求只返回一句短 advisory，不解释 reasoning，不写正式章节，不引用未提供证据。

Payload MC-B：JSON-first advisory

目标：观察 `json_advisory` 与 `malformed_response`。

内容方向：要求只返回单行 JSON，对象字段固定为 `advisory`、`suggestions`、`risk_notes`，禁止 Markdown code fence 和解释性文字。

Payload MC-C：text-fallback advisory

目标：观察 `text_fallback`。

内容方向：要求短非 JSON 技术建议，不要求条款、图纸、清单、规范，不写正式章节。

Payload MC-D：thinking fallback observation

目标：统计 `thinking_only_fallback`。

内容方向：要求简短 advisory 与 risk note，继续观察模型是否仍偏向 thinking 输出。

Payload MC-E：evidence missing advisory

目标：验证 evidence missing 不得 formal eligible。

内容方向：使用缺少页码、条款号、评分表或补疑依据的测试性声明，观察 `evidence_anchor_status` 与 formal flags。

Payload MC-F：generated-preview-as-evidence guard

目标：验证 generated preview 不得作为 evidence。

内容方向：测试“本地模型建议可作为招标条款、图纸、清单依据”的 unsafe claim。

Payload MC-G：formal chain request guard

目标：验证 DOCX / ZBid / candidate patch 请求 blocked。

内容方向：测试“将模型建议作为证据、生成候选补丁、导出 DOCX、写回 ZBid”的 unsafe request。

统一说明：

* 不使用真实招标资料；
* 不要求正式章节正文；
* 不生成文件；
* 不写回。

## 8. comparison matrix 设计

后续 report 应输出 comparison matrix，建议每一行对应一个 model + options profile + payload 组合。矩阵字段建议包括：

* 模型名；
* options profile；
* `payload_id`；
* HTTP 状态；
* `status`；
* `calls_ollama`；
* `response_mode`；
* `prompt_mode`；
* `quality_status`；
* `evidence_anchor_status`；
* `advisory_length`；
* `suggestions_count`；
* `risk_notes_count`；
* `thinking_fallback_detected`；
* `generated_preview_as_evidence_detected`；
* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`；
* `elapsed_ms` 或耗时；
* `controlled_failure_reason`。

矩阵不得大量粘贴模型完整输出。报告只记录摘要、长度、数量、状态和关键风险。

## 9. 成功判定标准设计

成功不是要求某模型直接进入正式链，而是要求：

* 所有请求受控返回；
* 不出现未处理异常；
* 能客观比较不同模型/options 的 `response_mode` 分布；
* 至少发现比 `qwen3:0.6b` 更低 thinking fallback 的候选路径，或明确当前模型能力边界；
* 所有正式链准入字段恒 false；
* 不写 `output/job/export`；
* 不触发正式生成链、导出链、ZBid 写回；
* 可为后续 shadow generation design 提供模型选择依据。

comparison 结论只能说明“哪个模型/options 更适合作为后续 preview runtime 候选”，不能说明“可以进入正式生成链”。

## 10. 可接受失败标准设计

以下情况可接受为受控失败：

* 某模型超时；
* 某模型返回 empty response；
* 某模型仍为 `thinking_only_fallback`；
* JSON-first 仍 `malformed_response`；
* 模型不可用但未自动 pull；
* 某 payload blocked；
* `quality_status` 不达标；
* `evidence_anchor_status` 不达标；
* 只要 controlled、no-write、no formal chain 即可记录。

可接受失败必须在 report 中明确标注模型、options profile、payload、失败类型和 no-write 状态。

## 11. 不可接受失败标准设计

以下结果不可接受：

* 自动 pull / 下载模型；
* 访问外网；
* 修改代码/tests；
* 写 `output/job/export`；
* 触发 `/generate`、`/export_docx`、`/review/apply`；
* 直接请求 Ollama `/api/generate`，除非后续单独授权；
* `formal_generation_allowed` 变 true；
* `shadow_candidate_allowed` 变 true；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 变 true；
* 把模型比较结果解释为正式链准入。

如果出现不可接受失败，应停止 comparison，清理本步启动的服务进程，并记录失败边界。

## 12. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。但 model/options comparison 仍属于 preview runtime 稳定性和模型选型阶段。

即使发现更优模型，也不得直接进入正式链。后续仍需 shadow generation design、candidate patch design、human approval、diff、rollback、DOCX export consistency、ZBid writeback isolation。

model/options comparison 只能为后续 shadow generation readiness 提供证据，不得替代 evidence anchor、quality gate、input-risk gate、人工确认或回滚设计。

## 13. 后续阶段建议

建议后续顺序为：

* Step 86：response-mode model/options comparison smoke plan，docs-only；
* Step 87：model/options comparison smoke + report；
* Step 88：model/options comparison review；
* Step 89：shadow generation readiness design；
* 后续再进入 shadow generation design。

在 Step 86 前，不得直接执行 model comparison runtime smoke。Step 87 如需启动 Ollama，只能复用既有本地 listener 或由 2 号窗口按授权运行 `ollama serve`，且不得下载或 pull 模型。

## 14. 风险与回滚

风险如下：

* 风险 1：更强模型资源占用过高；
* 风险 2：更强模型输出更长，增加误用为正式正文风险；
* 风险 3：推理型模型 thinking fallback 更高；
* 风险 4：JSON 输出仍不稳定；
* 风险 5：模型比较被误解为正式链准入；
* 风险 6：模型切换破坏 no-write / preview-only；
* 风险 7：自动拉取模型带来不可控下载。

回滚措施：保持当前 `qwen3:0.6b` preview-only 路径。

兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

同时必须保留 disabled / adapter-off / fake-only 路径。任何异常不得扩大到正式链路，不得触发 DOCX 导出，不得进入 ZBid 写回。

## 15. 当前阶段结论

本阶段仅完成 response-mode model/options comparison 的 docs-only 设计，未运行模型，未启动服务，未执行 runtime smoke，未进入 shadow generation 或正式生成链。

Step 83 已说明 `qwen3:0.6b` 在二轮 prompt tuning 后仍高度依赖 `thinking_only_fallback`。因此，后续更合理的方向是先设计 model/options comparison，而不是继续直接推进 shadow generation 或正式生成链。

## 16. 下一步建议

下一步建议为 ZDoc Step 86：response-mode model/options comparison smoke plan，docs-only。不得直接进入 model comparison runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
