# ZDoc Step 86: response-mode model/options comparison smoke plan

## 1. 阶段背景

Step 83 已完成 second-round response-mode runtime smoke。Step 84 已完成 runtime smoke review。Step 85 已完成 response-mode model/options comparison design。

Step 83 结果显示 `response_advisory=0`、`json_advisory=0`、`text_fallback=1`、`thinking_only_fallback=6/7`。`qwen3:0.6b` 在当前 prompt / options 下仍高度依赖 `thinking_only_fallback`。

Step 84 的复盘结论是：runtime 边界、adapter-off schema、generated-preview-as-evidence guard、no-write / preview-only 和 formal chain isolation 均受控，但 `qwen3:0.6b` 的 response-mode 输出能力仍不足。Step 85 因此转向 model/options comparison 设计。

当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。Step 86 目标是设计 Step 87 model/options comparison smoke，不执行 smoke。

## 2. 本次 comparison smoke 目标

后续 Step 87 的目标如下，但本步不得执行：

* 只读确认本地模型列表；
* 在不下载、不 pull 模型的前提下，选择少量已存在模型做对比；
* 比较不同模型对 `response_mode` 的影响；
* 比较不同 options profile 对 `response_mode` 的影响；
* 观察 `response_advisory` / `json_advisory` / `text_fallback` / `thinking_only_fallback` 分布；
* 观察生成质量、受控失败、耗时和资源风险；
* 验证 generated-preview-as-evidence、evidence anchor、quality gate、input-risk 不回归；
* 验证所有正式链准入字段恒 false；
* 验证不触发正式生成链、导出链、ZBid 写回；
* 验证不写 `output/job/export`。

Step 87 的 smoke 结果只能作为 preview runtime 选型与 response-mode 稳定性证据，不得解释为 shadow generation 或正式链准入。

## 3. smoke 范围边界

后续 Step 87 只允许：

* 使用本地 loopback Ollama；
* 仅通过 `/local-llm/preview-safe` 间接调用；
* 仅先请求 `GET http://127.0.0.1:11434/api/tags` 做模型存在性核验；
* 仅使用 preview-only payload；
* 仅新增 smoke report 文档；
* 不修改代码/tests；
* 不运行 pytest；
* 不直接请求 Ollama `/api/generate`；
* 不访问外网；
* 不下载或 pull 模型；
* 不写 `output/job/export`；
* 不触发 `/generate`、`/export_docx`、`/review/apply`；
* 不进入 shadow generation 或正式生成链。

Step 87 smoke 客户端只能请求 safe endpoint。Ollama `/api/generate` 只能由 safe endpoint real adapter 在本地 loopback 内部间接触发，不得由 smoke 客户端直接请求。

## 4. runtime 前置条件

后续真正执行 Step 87 前必须满足：

* 当前工作区 clean；
* HEAD 必须等于 Step 86 plan 对应标签；
* 如 `127.0.0.1:11434` 已有 listener，可复用并记录 PID；
* 如无 listener，只能由 2号窗口运行 `ollama serve`；
* 本地模型必须通过 `/api/tags` 确认已存在；
* 模型不存在时立即停止，不得 pull；
* FastAPI 只能监听 `127.0.0.1` 临时端口，建议 `18761`；
* 只允许请求 `/local-llm/preview-safe`；
* 本步启动的 FastAPI 必须停止；
* 本步启动的 Ollama 必须停止；
* 既有 Ollama listener 不得擅自停止。

Step 87 还必须在 smoke 前后检查 `output/`、`job/`、`export/` 是否出现新增写入。如目录不存在，记录不存在；如目录存在，记录前后计数或变更状态。

## 5. 模型选择策略

模型选择应分级执行，避免一次性过重。

必选基线：

* `qwen3:0.6b`

优先对照，存在才测：

* `qwen3:8b`

可选对照，存在且资源允许才测：

* `qwen3:14b`

暂不纳入 Step 87 默认 smoke，除非后续单独授权：

* `qwen3:30b`
* `qwen3-coder:30b`
* `deepseek-r1:32b`
* `qwen3-next:80b-a3b-instruct-q8_0`

说明：

* 本步不确认模型实时存在；
* Step 87 执行前必须重新 `/api/tags` 核验；
* 不得下载缺失模型；
* 30b / 32b / 80b 类模型资源风险高，先不作为默认 smoke 范围。

若 Step 87 发现 `qwen3:8b` 或 `qwen3:14b` 不存在，只能记录并跳过，不得 pull，不得下载，不得改用外部 API。

## 6. options profile 设计

options profile 应保持少量组合，避免组合爆炸。

只读代码检查显示当前已确认的环境变量包括：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`；
* `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
* `ZDOC_OLLAMA_PREVIEW_MODEL`；
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`；
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`。

当前 generate payload 已包含 `options.num_predict`。尚未在当前只读检查中确认 temperature、format/json mode、stop tokens 的实际环境变量或 options 接入方式，因此这些项需 Step 87 执行前只读核验实际环境变量或 options 参数。

建议 Step 87 默认使用以下 profile：

Profile O1：baseline conservative

* 使用当前默认或代码现有保守参数；
* 作为 `qwen3:0.6b` 对照基线。

Profile O2：response-first compact

* 小 `num_predict`；
* 低 temperature，如实际支持；
* 短 prompt；
* 目标观察 `response_advisory` / `text_fallback`。

Profile O3：JSON compact

* 小 `num_predict`；
* 低 temperature，如实际支持；
* 尝试 JSON-first；
* 目标观察 `json_advisory` / `malformed_response`。

如代码未查明对应变量名或实际支持方式，需 Step 87 执行前只读核验实际环境变量或 options 参数。不得为运行 smoke 临时修改代码。

## 7. payload 设计

后续 Step 87 的最小 payload 集应全部为测试性、非真实投标正文，不含真实招标资料。正常路径应使用 safe endpoint compatible schema，例如 `request_id`、`section_title`、`section_text`、`context_summary`，避免把 adapter-off schema 错误误判为 runtime 失败。

Payload MC-A：response-first advisory

目标：观察 `response_advisory`。

内容方向：只要求一句短 advisory，不解释 reasoning，不写正式章节，不引用未提供证据。

Payload MC-B：JSON-first advisory

目标：观察 `json_advisory` 与 `malformed_response`。

内容方向：只要求单行 JSON，对象字段固定为 `advisory`、`suggestions`、`risk_notes`，禁止 Markdown code fence 和解释性文字。

Payload MC-C：text-fallback advisory

目标：观察 `text_fallback`。

内容方向：要求短非 JSON 技术建议，不要求条款、图纸、清单、规范，不写正式章节。

Payload MC-D：generated-preview-as-evidence guard

目标：验证 generated preview 不得作为 evidence。

内容方向：测试“本地模型建议可作为招标条款、图纸、清单依据”的 unsafe claim。

Payload MC-E：evidence missing advisory

目标：验证 evidence missing 不得 formal eligible。

内容方向：使用缺少页码、条款号、评分表或补疑依据的测试性声明，观察 evidence anchor 与 formal flags。

建议默认矩阵：

* `qwen3:0.6b` × O1/O2/O3 × MC-A/MC-B/MC-C；
* `qwen3:8b` × O2/O3 × MC-A/MC-B/MC-C，如模型存在；
* `qwen3:14b` × O2/O3 × MC-A/MC-B，如模型存在且资源允许；
* MC-D / MC-E 可只对 `qwen3:0.6b` 与最优候选模型执行，避免过大矩阵。

默认矩阵应优先控制规模。若模型响应耗时过长或资源占用过高，应停止扩大矩阵并记录 controlled result。

## 8. 每项结果必须记录字段

后续 Step 87 report 每项至少记录：

* `model_name`；
* `options_profile`；
* `payload_id`；
* HTTP 状态；
* `status`；
* `calls_ollama`；
* `response_mode`；
* `prompt_mode`；
* `prompt_profile`；
* `prompt_version`；
* `prompt_tuning_applied`；
* `response_mode_confidence`；
* `thinking_fallback_detected`；
* advisory 是否存在；
* `advisory_length`；
* `suggestions_count`；
* `risk_notes_count`；
* `quality_status`；
* `input_risk_status`；
* `evidence_anchor_status`；
* `generated_preview_as_evidence_detected`；
* `generated_content_evidence_blocked`；
* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`；
* `elapsed_ms` 或耗时；
* `error_type` / `failure_reason`；
* `controlled_failure` 是否为是。

报告不得大量粘贴完整模型输出，只记录摘要、长度、数量、状态和关键风险。

## 9. 成功判定标准

成功不是要求某模型直接进入正式链，而是要求：

* 所有请求受控返回；
* 不出现未处理异常；
* 能客观比较模型/options 的 `response_mode` 分布；
* 至少确认 `qwen3:0.6b` 的基线表现；
* 如 `qwen3:8b` 或 `qwen3:14b` 存在，观察是否比 `qwen3:0.6b` 降低 thinking fallback；
* formal flags 全部恒 false；
* generated-preview-as-evidence 防护不回归；
* evidence missing 不得 formal eligible；
* 不写 `output/job/export`；
* 不触发正式生成链、导出链、ZBid 写回。

即使某个模型明显优于 `qwen3:0.6b`，也只能说明它更适合作为后续 preview runtime 候选，不代表可进入 shadow generation 或正式生成链。

## 10. 可接受失败标准

以下可接受为受控失败：

* 某模型不存在，记录并跳过，不 pull；
* 某模型超时；
* 某 payload 返回 empty response；
* 某 payload 仍 `thinking_only_fallback`；
* JSON-first 仍 malformed；
* 某 payload blocked；
* `evidence_anchor_status` 不达标；
* `quality_status` 不达标；
* 只要 controlled、no-write、formal flags false 即可记录。

可接受失败必须记录对应模型、options profile、payload、错误类型、耗时和是否保持 no-write。

## 11. 不可接受失败标准

以下不可接受：

* 自动 pull / 下载模型；
* 访问外网；
* 修改代码/tests；
* 写 `output/job/export`；
* 触发 `/generate`、`/export_docx`、`/review/apply`；
* 直接请求 Ollama `/api/generate`；
* `formal_generation_allowed` 变 true；
* `shadow_candidate_allowed` 变 true；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 变 true；
* 把模型比较结果解释为正式链准入。

一旦出现不可接受失败，应停止 smoke，清理本步启动的服务进程，并在 report 中明确记录失败边界。

## 12. report 汇总要求

后续 Step 87 report 必须包含：

* 模型列表核验结果；
* 实际参与对比的模型；
* 跳过的模型及原因；
* options profile 表；
* payload 表；
* comparison matrix；
* `response_mode` 统计；
* 每模型 thinking fallback 比例；
* 每模型 `response_advisory` / `json_advisory` / `text_fallback` 数量；
* `malformed_response` 数量；
* timeout / controlled failure 数量；
* formal flags 是否恒 false；
* 是否写 `output/job/export`；
* 端口与进程清理情况；
* 风险说明；
* 下一步建议。

report 还应记录是否请求 `/local-llm/preview-safe`、是否未直接请求 Ollama `/api/generate`、是否未请求 `/generate`、是否未请求 `/export_docx`、是否未请求 `/review/apply`、是否未下载或 pull 模型、是否未修改代码/tests。

## 13. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。但 model/options comparison smoke 仍属于 preview runtime 选型与稳定性验证。

即使发现更优模型，也不得直接进入正式链。后续仍需 comparison review、shadow generation readiness design、shadow generation design、candidate patch、人工确认、diff、rollback、DOCX 导出一致性、ZBid 写回隔离和真实资料 evidence source 映射。

model/options comparison smoke 只能回答“哪些本地模型和 options 更适合继续验证”，不能回答“是否可以写入正式章节”。

## 14. 风险与回滚

风险如下：

* 风险 1：更强模型资源占用过高；
* 风险 2：更强模型输出更长，增加误用风险；
* 风险 3：推理型模型 thinking fallback 更高；
* 风险 4：模型比较被误解为正式链准入；
* 风险 5：options 组合过多导致 smoke 不可控；
* 风险 6：模型切换破坏 no-write / preview-only；
* 风险 7：自动拉取模型带来不可控下载。

回滚措施：保持 `qwen3:0.6b` preview-only 基线。

兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

同时保留 disabled / adapter-off / fake-only 路径。任何异常不得扩大到正式链路，不得进入 shadow generation、DOCX 导出或 ZBid 写回。

## 15. 当前阶段结论

本阶段仅完成 response-mode model/options comparison smoke 的 docs-only 计划，未运行模型，未启动服务，未执行 runtime smoke，未进入 shadow generation 或正式生成链。

Step 87 只有在单独授权后才能执行，并且必须继续保持 no-write、preview-only、只走 `/local-llm/preview-safe`、不下载模型和 formal flags 恒 false。

## 16. 下一步建议

下一步建议为 ZDoc Step 87：response-mode model/options comparison smoke + report。该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
