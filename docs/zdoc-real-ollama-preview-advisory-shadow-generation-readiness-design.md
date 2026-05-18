# ZDoc Shadow Generation Readiness Design

## 1. 阶段背景

Step 92 已将 response-mode 后续策略确定为 B + D 为主，C 后续预研，A 暂缓：

* B：接受 `thinking_only_fallback` 仅作为 preview-only / review_required 的人工参考建议，不进入 shadow candidate，不进入正式链；
* D：优先推进 evidence source mapping、human approval、diff / rollback 与 shadow readiness 设计；
* C：adapter / normalization 抽取策略仅作为后续预研，必须先设计 guard；
* A：暂缓默认继续扩大到 30b / 32b / 80b 等更大模型。

当前 runtime 事实仍然保守：

* `qwen3:0.6b`、`qwen3:8b`、`qwen3:14b` 均未证明 response-mode 满足 shadow generation 条件；
* `qwen3:14b` targeted smoke 中 5/5 仍为 `thinking_only_fallback`；
* `response_advisory` / `json_advisory` 未稳定出现；
* `text_fallback` 仅曾出现少量样本，稳定性不足；
* `thinking_only_fallback` 仍只能作为 preview-only / review_required。

同时，evidence anchor、quality gate、input-risk、generated-preview-as-evidence 已具备 fake-only 初步门禁，且正式链准入字段持续保持 false。

当前不得进入 shadow generation implementation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。Step 93 的目标是设计 shadow generation readiness，不执行任何生成或写回。

## 2. readiness 与 implementation 的边界

readiness design 允许：

* 定义准入条件；
* 定义数据契约；
* 定义候选内容结构；
* 定义 evidence trace；
* 定义人工确认；
* 定义 diff / rollback；
* 定义 no-write boundary；
* 定义日志与审计字段；
* 定义后续 deterministic tests。

readiness design 禁止：

* 生成 candidate patch；
* 生成正式正文；
* 修改章节正文；
* 写 DOCX；
* 写 `output/job/export`；
* 写回 ZBid；
* 调用模型；
* 启动服务；
* 进入 shadow generation implementation。

## 3. shadow generation 的目标定义

未来 shadow generation 的目标是生成可审查、可拒绝、可回滚的候选建议或候选 patch，而不是直接生成正式成果。

目标边界：

* 只生成候选建议或候选 patch；
* 不直接写正式章节；
* 不直接进入 DOCX；
* 不直接写回 ZBid；
* 候选内容必须携带 evidence anchors；
* 候选内容必须通过 quality gate、input-risk gate、evidence anchor、response-mode policy；
* 候选内容必须经人工确认；
* 候选内容必须可 diff、可拒绝、可回滚。

shadow generation 的产物应始终被视为待审候选，不是正式正文，也不是证据来源。

## 4. shadow generation 前置准入条件

后续任何候选内容进入 shadow generation 之前，至少必须满足以下准入条件：

* `quality_status` 不得为 `blocked` / `system_error`；
* `input_risk_status` 不得为 `blocked`；
* `evidence_anchor_status` 不得为 `missing` / `invalid_anchor` / `conflicting` / `system_error`；
* `generated_preview_as_evidence_detected` 不得为 true；
* `thinking_only_fallback` 不得直接进入 `shadow_candidate`；
* `response_mode` 必须符合后续单独授权策略；
* `no_write=true`；
* `preview_only=true`；
* `affects_generation=false`；
* `affects_export=false`；
* `formal_generation_allowed=false`；
* `export_allowed=false`；
* `zbid_writeback_allowed=false`；
* 必须具备 human approval 流程；
* 必须具备 rollback 机制。

以上条件不满足时应 fail-closed，返回 blocked、review_required 或 controlled failure，不得自动放行。

## 5. shadow_candidate_allowed 的未来设计边界

当前 `shadow_candidate_allowed` 必须保持 false。

后续只有在 readiness guard、deterministic tests、runtime smoke、human approval design 完成后，才可讨论某些 preview candidate 是否允许进入 shadow candidate。该讨论必须单独授权，且不得与正式写回、DOCX 导出或 ZBid 写回混在同一步。

未来即使出现 `shadow_candidate_allowed=true`：

* `shadow_candidate_allowed=true` 不等于 `writeback_allowed=true`；
* `shadow_candidate_allowed=true` 不等于 `formal_generation_allowed=true`；
* `shadow_candidate_allowed=true` 不等于 `export_allowed=true`；
* `shadow_candidate_allowed=true` 不等于 `zbid_writeback_allowed=true`；
* 只能生成候选，不写正式文档；
* 候选仍必须经过 human approval、diff、rollback 和 evidence trace 检查。

## 6. candidate patch 数据结构设计

未来 candidate patch 的最小数据契约建议如下，本步不得实现：

* `candidate_id`：候选补丁唯一标识；
* `source_section_id`：来源章节标识；
* `source_section_title`：来源章节标题；
* `original_text_excerpt`：原文摘要或原文片段；
* `proposed_text`：候选文本；
* `patch_type`：新增、替换、删除、重写、补充说明等类型；
* `patch_scope`：章节级、段落级、句子级或局部字段级范围；
* `patch_reason`：候选变更原因；
* `quality_gate_metadata`：quality gate 结果、score、warnings、blockers；
* `input_risk_metadata`：input-risk 状态、flags、blockers、warnings；
* `evidence_anchor_metadata`：evidence anchor 状态、required、invalid reason、missing reason；
* `response_mode_metadata`：response_mode、prompt_mode、fallback_reason、review_required 等；
* `evidence_sources`：证据来源列表与定位；
* `unsupported_claims`：未证实 claim 列表；
* `human_review_required`：是否必须人工复核；
* `approval_status`：pending、accepted、rejected、revised、hold；
* `diff_summary`：候选相对原文的差异摘要；
* `rollback_token`：回滚令牌；
* `created_at`：候选创建时间；
* `generated_by_model`：是否由模型产生；
* `model_name`：模型名；
* `prompt_profile`：prompt profile；
* `trace_id`：审计追踪标识。

该数据契约只描述候选结构，不代表候选可以写入正式正文。

## 7. evidence trace 设计

evidence trace 是 shadow generation readiness 的核心门禁：

* 每条事实性 candidate 必须携带 evidence anchor；
* model-generated preview 不得作为 evidence；
* `unknown_or_unverified` 不得进入 candidate patch；
* `missing` / `invalid_anchor` / `conflicting` 必须 blocked；
* safe expression 可 `review_required`，但不得自动写入；
* evidence trace 必须在人工确认界面可见；
* evidence trace 必须可被 DOCX / ZBid 后续链路继承。

事实性 candidate 的 evidence source 应区分招标文件、答疑补遗、评分办法、图纸、工程量清单、踏勘资料、照片、合同或建设单位要求、规范标准、用户提供上下文等来源。generated suggestion 只能作为建议来源，不得升级为 source evidence。

## 8. human approval 设计

human approval 是正式链前的硬边界：

* 没有人工确认，不得写正式正文；
* 人工确认前必须展示 original / candidate / diff / evidence anchors；
* 人工确认必须记录确认人、确认时间、确认范围；
* 人工可选择 accept / reject / revise / hold；
* accept 也不等于立即 DOCX 导出；
* revise 需要生成新 candidate；
* reject 必须保留审计记录；
* `approval_status` 未确认时 `writeback_allowed=false`。

人工确认记录不得被模型输出替代，也不得被 response_mode、quality_status 或 evidence_anchor_status 自动推导。

## 9. diff 与 rollback 设计

candidate patch 必须支持可审计的 diff 与可执行的 rollback：

* candidate patch 必须能展示修改前后差异；
* patch 应支持章节级、段落级、句子级范围；
* 每次写回前必须生成 rollback token；
* rollback 应能恢复原章节文本；
* rollback 不得依赖模型；
* rollback 记录应保留 `trace_id`；
* diff / rollback 未完成前，不得进入正式写回。

diff 应显示原文、候选文本、变更范围、证据引用、风险提示和人工确认状态。rollback 应面向已确认写回后的恢复需求，而不是依赖重新生成。

## 10. no-write boundary 设计

no-write boundary 必须贯穿 readiness、shadow candidate 和正式写回前的全部阶段：

* shadow generation readiness 阶段 `no_write=true`；
* shadow candidate 阶段也不得直接写正式正文；
* formal writeback 必须单独授权；
* DOCX export 必须单独授权；
* ZBid writeback 必须单独授权；
* `output/job/export` 不得在 readiness 阶段写入；
* 所有自动写回默认 fail-closed。

任何试图在 readiness 阶段生成正式章节、导出 DOCX、写 JSON / Markdown 正式成果、写 `output/job/export` 或写回 ZBid 的行为，都应被视为越界。

## 11. 与 DOCX 导出的关系

DOCX 导出不是 shadow generation 的一部分。

DOCX 导出前必须满足：

* 已完成正式章节写回确认；
* 已继承 candidate patch 的 evidence trace；
* 已保留 human approval 与 diff / rollback 记录；
* 已完成标题层级、表格、图片、图文一致性校核；
* 已完成导出前的独立授权。

当前阶段 `export_allowed=false`。shadow candidate 不能直接触发 DOCX 导出。

## 12. 与 ZBid 写回的关系

ZBid 写回必须严格隔离 source evidence、generated suggestion 与 human approval：

* ZBid 写回不得使用 model-generated advisory 作为原始证据；
* ZBid 写回必须区分 source evidence、generated suggestion、human approval；
* 不得覆盖原始招标解析数据；
* 不得污染 scoring basis；
* 当前阶段 `zbid_writeback_allowed=false`。

未来即使进入 ZBid 写回设计，也必须保留原始数据、候选 patch、人工确认、diff、rollback 与 trace_id 的隔离关系。

## 13. deterministic tests 设计

后续 Step 94 或后续实现前必须覆盖以下 deterministic tests，本步不得运行 pytest：

* candidate patch without evidence -> blocked；
* candidate patch with missing evidence -> blocked；
* candidate patch from `thinking_only_fallback` -> blocked 或 review_required；
* candidate patch with `generated_preview_as_evidence` -> blocked；
* candidate patch with anchored evidence but no human approval -> not writeback allowed；
* candidate patch accepted by human -> still not export allowed without export step；
* reject candidate -> no writeback；
* rollback token missing -> blocked；
* diff missing -> blocked；
* formal flags remain false；
* DOCX export attempted from shadow candidate -> blocked；
* ZBid writeback attempted from shadow candidate -> blocked。

测试还应覆盖 safe endpoint metadata 不回归、quality gate 不回归、input-risk 不回归、evidence anchor 不回归，以及 `generated_content_must_not_be_evidence` 可追踪。

## 14. 后续实现边界设计

后续如进入实现，必须单独授权。可能涉及：

* 新增 shadow_candidate helper；
* 新增 tests；
* 可能扩展 quality gate metadata；
* 可能扩展 evidence anchor metadata；
* 可能扩展 UI preview，但不得写正式正文；
* 不得修改正式生成链；
* 不得修改 DOCX 导出链；
* 不得修改 ZBid 写回链；
* 不得写 `output/job/export`。

实现顺序应先 fake-only helper 与 deterministic tests，再进入 docs-only stage review，再设计 runtime 或 UI 验证边界。不得从 readiness design 直接跳到 shadow generation implementation。

## 15. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 shadow generation readiness 只是正式链前的安全设计层。未完成 candidate patch、human approval、diff、rollback、DOCX 导出一致性校核和 ZBid 写回隔离前，不得进入正式生成链。

当前 response-mode 仍不满足 shadow generation 条件，因此 readiness design 的主要价值是定义准入、证据、人工确认和回滚边界，而不是放开生成链。

## 16. 风险与回滚

当前风险：

* 风险 1：把 shadow candidate 误认为正式正文；
* 风险 2：`thinking_only_fallback` 被误用为 candidate patch；
* 风险 3：缺 evidence trace 的内容进入候选；
* 风险 4：没有 human approval 就写正文；
* 风险 5：diff / rollback 不完整；
* 风险 6：DOCX / ZBid 写回缺少隔离；
* 风险 7：future implementation 意外写 `output/job/export`。

回滚与兜底：

* 回滚措施：保持 `shadow_candidate_allowed=false`；
* 兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
* 保留 disabled / adapter-off / fake-only 路径；
* 任一 guard 异常时应 blocked、review_required 或 system_error，不得自动放行；
* 不得把模型输出、response_mode 或 prompt_mode 当作正式链准入依据。

## 17. 当前阶段结论

本阶段仅完成 shadow generation readiness 的 docs-only 设计，未实现 shadow generation，未生成 candidate patch，未写正式正文，未启动服务，未运行模型，未进入 DOCX 导出或 ZBid 写回。

## 18. 下一步建议

下一步建议为 ZDoc Step 94：shadow generation readiness guard + deterministic tests design，docs-only。不得直接进入 shadow generation implementation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。
