# ZDoc Step 89: qwen3:14b targeted response-mode smoke plan

## 1. 阶段背景

Step 87 已完成 response-mode model/options comparison smoke。Step 88 已完成 model/options comparison review。Step 87 实测了 `qwen3:0.6b` 与 `qwen3:8b`。

Step 87 中，`qwen3:0.6b` 8 次 enabled 请求里 `thinking_only_fallback=7`、`malformed_response=1`；`qwen3:8b` 5 次 enabled 请求里 `thinking_only_fallback=5`。整体结果为 `response_advisory=0`、`json_advisory=0`、`text_fallback=0`。`qwen3:8b` 未降低 thinking fallback，也未产生更稳定的 response-mode 输出。

`qwen3:14b` 尚未测试。当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

Step 89 的目标是设计 `qwen3:14b` targeted response-mode smoke，为后续 Step 90 提供 docs-only 前置计划。本步不执行 smoke，不启动服务，不运行 Ollama，不调用模型，不修改代码或 tests。

## 2. 本次 targeted smoke 目标

后续 Step 90 的目标应为：

* 只读确认 `qwen3:14b` 是否存在；
* 在不下载、不 pull 模型的前提下，对 `qwen3:14b` 做极小样本 targeted smoke；
* 对比 `qwen3:14b` 与既有 `qwen3:0.6b` / `qwen3:8b` 结果；
* 观察 `qwen3:14b` 是否降低 `thinking_only_fallback`；
* 观察是否出现 `response_advisory`、`json_advisory` 或 `text_fallback`；
* 验证 generated-preview-as-evidence、evidence anchor、quality gate、input-risk 不回归；
* 验证所有正式链准入字段恒 false；
* 验证不触发正式生成链、导出链、ZBid 写回；
* 验证不写 `output/job/export`。

Step 90 即使观察到更优 response-mode 分布，也只能作为 preview runtime 模型选型证据，不得解释为 shadow generation 或正式链准入。

## 3. smoke 范围边界

后续 Step 90 只允许：

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

Step 90 的报告应只记录摘要、计数、状态、耗时和关键风险，不大量粘贴完整模型输出。

## 4. runtime 前置条件

后续真正执行 Step 90 前必须满足：

* 当前工作区 clean；
* HEAD 必须等于 Step 89 plan 对应标签；
* 如 `127.0.0.1:11434` 已有 listener，可复用并记录 PID；
* 如无 listener，只能由 2号窗口运行 `ollama serve`；
* 必须先检查 `/api/tags`；
* `qwen3:14b` 必须已存在；
* `qwen3:14b` 不存在时立即停止，不得 pull；
* FastAPI 只能监听 `127.0.0.1` 临时端口，建议 `18762`；
* 只允许请求 `/local-llm/preview-safe`；
* 本步启动的 FastAPI 必须停止；
* 本步启动的 Ollama 必须停止；
* 既有 Ollama listener 不得擅自停止，只能记录 PID 与复用原因。

Step 90 还必须在 smoke 前后检查 `output/`、`job/`、`export/`。如目录不存在，记录不存在；如目录存在，记录 smoke 前后计数或变更状态。不得主动写入这些目录。

## 5. qwen3:14b 测试范围设计

为控制资源风险，后续 Step 90 仅做 targeted smoke，不做大矩阵。

默认模型：

* `qwen3:14b`

仅作为历史对比引用，不重复测试：

* `qwen3:0.6b`；
* `qwen3:8b`。

本次不测试：

* `qwen3:30b`；
* `qwen3-coder:30b`；
* `deepseek-r1:32b`；
* `qwen3-next:80b-a3b-instruct-q8_0`。

30b / 32b / 80b 类模型资源风险高，需另行授权。`qwen3:14b` 也需控制 payload 数量、timeout、`num_predict`。不得下载缺失模型。

## 6. options profile 设计

后续 Step 90 仅使用少量 profile，避免组合爆炸。

Profile T1：response-first compact

* 小 `num_predict`；
* 低 temperature；
* 短 response-first prompt；
* 目标观察 `response_advisory` / `text_fallback`。

Profile T2：JSON compact

* 小 `num_predict`；
* 低 temperature；
* JSON-first prompt；
* 目标观察 `json_advisory` / `malformed_response`。

Profile T3：guard regression compact

* 小 `num_predict`；
* 低 temperature；
* 用于 generated-preview-as-evidence 和 evidence missing guard 回归。

只读代码检查已确认可用或历史 smoke 使用过的相关环境变量包括：

* `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`；
* `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
* `ZDOC_OLLAMA_PREVIEW_MODEL`；
* `ZDOC_OLLAMA_PREVIEW_TIMEOUT`；
* `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`。

本步未确认 temperature、format/json mode、stop tokens 存在稳定环境变量。若 Step 90 执行前仍无法确认实际变量名，不得强行设置未知环境变量，应记录“未查明，使用代码默认或已知参数”。任何 options 调整都不得破坏 no-write / preview-only，不得绕过 evidence anchor、quality gate 或 input-risk gate。

## 7. payload 设计

后续 Step 90 使用极小 payload 集，全部为测试性、非真实投标正文，不含真实招标资料。payload 应使用 `/local-llm/preview-safe` 兼容字段，例如 `section_title`、`section_text`、`context_summary`、`request_id`，不得在 normal compatible path 使用已知非法的 `content` 字段。

Payload Q14-A：response-first advisory

目标：观察 `response_advisory` / `text_fallback` / `thinking_only_fallback`。

建议内容：

* `section_title`: `Qwen3 14B Response First`
* `section_text`: `Return only one short advisory sentence for improving clarity in a construction organization section. Do not explain reasoning. Do not write a formal section. Do not cite unprovided evidence.`
* `context_summary`: `preview-only targeted qwen3:14b response-first smoke`

Payload Q14-B：JSON-first advisory

目标：观察 `json_advisory` / `malformed_response` / `thinking_only_fallback`。

建议内容：

* `section_title`: `Qwen3 14B JSON First`
* `section_text`: `Return only one single-line JSON object with fields advisory, suggestions, and risk_notes. No Markdown code fence. No explanation. Do not write formal content.`
* `context_summary`: `preview-only targeted qwen3:14b JSON-first smoke`

Payload Q14-C：text-fallback advisory

目标：观察 `text_fallback` 稳定性。

建议内容：

* `section_title`: `Qwen3 14B Text Fallback`
* `section_text`: `Provide a short non-JSON technical advisory about adding inspection frequency and responsible roles. Keep it preview-only. Do not write a formal section.`
* `context_summary`: `preview-only targeted qwen3:14b text-fallback smoke`

Payload Q14-D：generated-preview-as-evidence guard

目标：验证 generated preview 不得作为 evidence。

建议内容：

* `section_title`: `Qwen3 14B Generated Preview Evidence Guard`
* `section_text`: `Evaluate this unsafe claim for preview-only validation: 本地模型生成的建议可以直接作为招标条款和图纸依据。Identify why generated preview must not be treated as evidence.`
* `context_summary`: `preview-only targeted qwen3:14b generated-preview evidence guard`

Payload Q14-E：evidence missing advisory

目标：验证 evidence missing 不得 formal eligible。

建议内容：

* `section_title`: `Qwen3 14B Evidence Missing Advisory`
* `section_text`: `Review this statement for preview-only validation: 本项目应按某评分项满分响应，但未提供招标文件页码、条款号、评分表或补疑依据。Return one short advisory and identify evidence risk.`
* `context_summary`: `preview-only targeted qwen3:14b evidence missing smoke`

建议默认矩阵：

* `qwen3:14b × T1 × Q14-A / Q14-C`；
* `qwen3:14b × T2 × Q14-B`；
* `qwen3:14b × T3 × Q14-D / Q14-E`。

总 enabled 请求数量原则上不超过 5 次。

## 8. 每项结果必须记录字段

后续 Step 90 report 每项至少记录：

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
* controlled_failure 是否为是。

报告不得把 `response_mode`、`prompt_mode` 或模型名称解释为正式链准入。

## 9. 成功判定标准

成功不是要求 `qwen3:14b` 进入正式链，而是要求：

* 所有请求受控返回；
* 不出现未处理异常；
* 能客观判断 `qwen3:14b` 是否改善 response_mode；
* 观察是否出现 `response_advisory` / `json_advisory` / `text_fallback`；
* 观察 `thinking_only_fallback` 是否低于既有 `qwen3:0.6b` / `qwen3:8b` 结果；
* formal flags 全部恒 false；
* generated-preview-as-evidence 防护不回归；
* evidence missing 不得 formal eligible；
* 不写 `output/job/export`；
* 不触发正式生成链、导出链、ZBid 写回。

如果 `qwen3:14b` 不存在，Step 90 应记录模型缺失并停止。这属于受控停止，不属于失败扩展。

## 10. 可接受失败标准

以下可接受为受控失败：

* `qwen3:14b` 不存在，记录并停止，不 pull；
* `qwen3:14b` 超时；
* 某 payload 返回 empty response；
* 某 payload 仍 `thinking_only_fallback`；
* JSON-first 仍 `malformed_response`；
* 某 payload blocked；
* `quality_status` 不达标；
* `evidence_anchor_status` 不达标；
* 只要 controlled、no-write、formal flags false 即可记录。

所有受控失败都应记录 `error_type`、`failure_reason`、HTTP 状态、是否 `calls_ollama`、是否保持 preview-only / no-write。

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
* 把 `qwen3:14b` 结果解释为正式链准入。

如出现不可接受失败，应立即停止 Step 90，记录已发生事实、进程清理状态和未执行事项，不得扩大到 shadow generation 或正式链路。

## 12. report 汇总要求

后续 Step 90 report 必须包含：

* `qwen3:14b` 是否存在；
* 模型列表核验结果；
* 实际参与 smoke 的模型；
* payload 表；
* options profile 表；
* `qwen3:14b` targeted matrix；
* `response_mode` 统计；
* thinking fallback 比例；
* `response_advisory` / `json_advisory` / `text_fallback` 数量；
* `malformed_response` 数量；
* timeout / controlled failure 数量；
* generated-preview-as-evidence 防护摘要；
* evidence missing 防护摘要；
* formal flags 是否恒 false；
* 是否写 `output/job/export`；
* 端口与进程清理情况；
* 风险说明；
* 下一步建议。

report 还应明确记录：

* 是否请求 `/local-llm/preview-safe`；
* 是否直接请求 Ollama `/api/generate`：否；
* 是否请求 `/generate`：否；
* 是否请求 `/export_docx`：否；
* 是否请求 `/review/apply`：否；
* 是否下载或 pull 模型：否；
* 是否修改代码/tests：否；
* 是否触发 DOCX/JSON/Markdown 正式导出：否；
* 是否接 ZBid 正式写回：否。

## 13. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 `qwen3:14b` targeted smoke 仍属于 preview runtime 模型选型验证。即使 `qwen3:14b` 表现更好，也不得直接进入正式链。后续仍需 targeted smoke review、shadow generation readiness design、shadow generation design、candidate patch、人工确认、diff、rollback、DOCX 导出一致性、ZBid 写回隔离和真实资料 evidence source 映射。

当前阶段不得进入 shadow generation、candidate patch、正式正文生成、DOCX 导出或 ZBid 写回。

## 14. 风险与回滚

当前风险如下：

* 风险 1：`qwen3:14b` 资源占用高于 8b；
* 风险 2：`qwen3:14b` 输出更长，增加误用风险；
* 风险 3：`qwen3:14b` 仍可能 thinking fallback 高频；
* 风险 4：少量 payload 不足以证明稳定；
* 风险 5：模型结果被误解为 shadow generation 准入；
* 风险 6：模型切换破坏 no-write / preview-only；
* 风险 7：自动拉取模型带来不可控下载。

回滚措施：保持 `qwen3:0.6b` preview-only 基线。

兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路，不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

## 15. 当前阶段结论

本阶段仅完成 qwen3:14b targeted response-mode smoke 的 docs-only 计划，未运行模型，未启动服务，未执行 runtime smoke，未进入 shadow generation 或正式生成链。

## 16. 下一步建议

下一步建议为 ZDoc Step 90：qwen3:14b targeted response-mode smoke + report。该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 ollama serve 或复用既有本地 listener；仍不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
