# ZDoc Step 78: response-mode prompt tuning runtime smoke review + follow-up design

## 1. 阶段背景

Step 74 已完成 response-mode prompt tuning fake-only implementation + deterministic tests。Step 75 已完成 fake-stage review。Step 76 已完成 response-mode prompt tuning runtime smoke plan refresh。Step 77 已完成 response-mode prompt tuning runtime smoke + smoke report。

Step 77 结果为 6/6 HTTP 200，runtime smoke 受控。Step 77 首次观察到 `text_fallback=1`，`thinking_only_fallback` 从此前 Step 70 的 8/8 降为 Step 77 的 4/6。Step 77 JSON-first payload 结果为 `malformed_response`，仍未观察到 `response_advisory` / `json_advisory`。

正式链准入字段全部恒为 false。当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。本步目标是复盘 Step 77 并设计后续 response-mode follow-up，不执行代码或 runtime smoke。

## 2. Step 77 已证明的事实

Step 77 已证明以下事实：

* 本地 Ollama 可达；
* `qwen3:0.6b` 存在；
* FastAPI loopback runtime smoke 受控；
* disabled 场景 stable disabled；
* adapter-off compatible payload 正常；
* adapter-off illegal field 为 controlled failure；
* enabled 6/6 HTTP 200；
* enabled runtime 中出现 `text_fallback=1`；
* `thinking_only_fallback` 次数由 Step 70 的 8/8 改善为 Step 77 的 4/6；
* generated-preview-as-evidence 回归仍有效；
* `formal_generation_allowed` 恒 false；
* `shadow_candidate_allowed` 恒 false；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 恒 false；
* 未请求 `/generate`；
* 未请求 `/export_docx`；
* 未请求 `/review/apply`；
* 未直接请求 Ollama `/api/generate`；
* 未写 `output/job/export`；
* FastAPI 进程已停止；
* `18759` 端口已释放；
* 本步启动的 Ollama 已停止，`11434` 无监听。

## 3. Step 77 结果复盘

Step 77 摘要如下：

* disabled：HTTP 200，`status=disabled`，`calls_ollama=false`，`preview_only/no_write=true`；
* adapter-off compatible：HTTP 200，`status=ok`，`calls_ollama=false`，fake-only helper 正常；
* adapter-off illegal field：HTTP 200，`status=failure`，`error_type=illegal_field`，`reason=illegal_field:content`；
* enabled 6/6 HTTP 200；
* PT-A：`thinking_only_fallback / review_required / not_required`；
* PT-B：`malformed_response / blocked / not_required`；
* PT-C：`text_fallback / review_required / not_required`；
* PT-D：`thinking_only_fallback / review_required / not_required`；
* PT-E：`thinking_only_fallback / blocked / invalid_anchor`；
* PT-F：`thinking_only_fallback / review_required / missing`；
* response_mode 统计：`response_advisory=0`，`json_advisory=0`，`text_fallback=1`，`thinking_only_fallback=4`，`empty_response=0`，`malformed_response=1`，`normalization_failure=0`，`system_error=0`；
* generated_preview_as_evidence_detected 次数 = 1；
* generated_content_evidence_blocked 次数 = 1；
* thinking fallback 出现次数 = 4；
* 正式链准入字段全 false。

## 4. 关键进展判断

Step 77 已证明 prompt tuning 后 runtime 不再是 8/8 `thinking_only_fallback`。`text_fallback` 首次在真实 runtime 下出现，说明 response-mode prompt tuning 至少开始影响真实 runtime 的响应模式分布。

adapter-off schema follow-up 受控，compatible payload 正常，illegal field 仍为 controlled failure。generated-preview-as-evidence 防护未回归，no-write / preview-only / formal chain isolation 稳定。

该结果支持继续做 second-round response-mode tuning。但当前结果仍不支持进入 shadow generation 或正式生成链。

## 5. 剩余缺口定义

缺口 1：`response_advisory` 未出现。

response-first prompt 未在真实 runtime 下形成 `response_advisory`。PT-A 仍为 `thinking_only_fallback`，说明 response-first prompt 仍需强化。

缺口 2：`json_advisory` 未出现。

JSON-first payload PT-B 结果为 `malformed_response`。这说明 JSON prompt 可能诱导出不稳定或非规范 JSON，后续需要 JSON schema / bounded JSON / fallback 策略。

缺口 3：`thinking_only_fallback` 仍偏高。

6 个 enabled payload 中 4 个仍为 `thinking_only_fallback`。虽然较 Step 70 的 8/8 已改善，但仍不能进入 shadow generation。

缺口 4：`text_fallback` 初步有效但样本不足。

PT-C 形成 `text_fallback`，这是正向信号。但单个 payload 不能证明 text-fallback 在真实 runtime 下稳定，需要后续复测。

## 6. JSON-first malformed_response 专项复盘

PT-B 是 JSON-first advisory payload，runtime 结果为 `malformed_response / blocked / not_required`。该结果受控，没有触发正式链，也没有写入正文、导出文件或写回外部系统。

该结果说明 JSON-first prompt 尚未形成稳定 `json_advisory`。后续应设计更严格的短 JSON 模板，例如固定单层对象、固定字段、短字符串值和禁止 Markdown 包裹。后续也应评估是否需要 format/options 支持，但不得为追求 `json_advisory` 而放宽 evidence safety。

后续仍应保留 malformed JSON 的 controlled failure 或 text_fallback 兜底。JSON-first 的目标是提升 preview metadata 可解析性，不是绕过 quality gate、input-risk gate 或 evidence anchor。

## 7. text_fallback 专项复盘

PT-C 成功形成 `text_fallback / review_required / not_required`。这是 Step 77 的正向进展，表明真实 runtime 已经出现非 `thinking_only_fallback` 的响应模式。

`text_fallback` 可作为短技术建议 preview，但不得进入正式链。`text_fallback` 仍需经过 quality gate / evidence anchor / input-risk，不得被解释为正式正文或 candidate patch。

后续应通过多 payload 验证 `text_fallback` 稳定性，重点观察不同输入长度、不同 advisory 请求和 evidence-aware 请求下是否仍能稳定形成可控短文本。

## 8. response-first 专项复盘

PT-A 仍为 `thinking_only_fallback`。这说明 response-first prompt 可能仍未足够约束模型输出路径，或者当前 qwen3:0.6b 在该 prompt / options 下仍倾向输出 thinking 内容。

后续 response-first prompt 应更短、更明确、更少推理诱因。应避免要求“分析”“判断”“解释”类长思考，改为明确“只返回一句用户可见建议”。同时仍必须明确不写正式章节正文、不导出、不写回、不应用、不虚构条款、图纸、清单、规范或工程量。

response-first 的优化目标是提高 preview advisory 的可见输出稳定性，不是让 `response_advisory` 获得正式链准入。

## 9. adapter-off schema 复盘

adapter-off compatible payload 已正常，adapter-off illegal field 返回 controlled `illegal_field:content`。schema follow-up 达成初步目标。

后续 smoke payload 应统一使用 compatible schema，避免 adapter-off 因测试字段不兼容造成解释偏差。illegal field 测试应保留为 controlled failure 回归，用于证明字段校验仍受控。

adapter-off schema 失败不得被误判为 real runtime failure。adapter-off 的用途是验证非 real adapter 路径和 schema guard，而不是证明 Ollama transport。

## 10. 后续设计方向

后续可从 docs-only 角度继续设计以下方向：

* 第二轮 response-first prompt tuning；
* 第二轮 JSON-first prompt tuning；
* text-fallback 稳定性测试；
* response-mode runtime smoke plan refresh；
* 可能的 model comparison plan；
* 可能的 qwen3:0.6b options 调整；
* 继续保持 evidence anchor、quality gate、input-risk gate 不可绕过；
* 继续禁止 shadow generation 与正式链准入。

第二轮 response-first tuning 应优先减少推理诱因，固定输出一句短 advisory。第二轮 JSON-first tuning 应优先短模板和严格字段，而不是扩大输出长度。text-fallback 方向应关注稳定、短、可审查，而不是正文生成能力。

## 11. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。但 Step 77 仍属于 preview runtime 稳定性验证。

即使出现 `text_fallback`，也不得进入正式链。正式链前仍需完成 response-mode 稳定、evidence anchor、quality gate、input-risk gate、shadow generation、candidate patch、人工确认、diff、rollback、DOCX 导出一致性和 ZBid 写回隔离。

`response_mode` 只是 preview metadata，不是正式链准入字段。`quality_status=review_required` 或 `blocked` 更不能被解释为可写回。`evidence_anchor_status=not_required` 也不等于无需审核或可进入正式链。

## 12. 风险与回滚

当前风险如下：

* 风险 1：`text_fallback` 被误认为正式正文能力成熟；
* 风险 2：thinking fallback 仍偏高，被误读为可接受；
* 风险 3：JSON prompt 为追求格式而削弱 evidence safety；
* 风险 4：response-first prompt 诱导过短导致质量不足；
* 风险 5：adapter-off schema failure 被误判；
* 风险 6：`response_mode` 被误用为正式链准入；
* 风险 7：后续 tuning 破坏 no-write / preview-only。

回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路，不得进入 shadow generation、candidate patch、DOCX 导出或 ZBid 写回。

## 13. 当前阶段结论

Step 77 已证明 response-mode prompt tuning runtime smoke 受控，并首次观察到 text_fallback；thinking_only_fallback 由此前 8/8 改善为 4/6，但 response_advisory / json_advisory 仍未出现，JSON-first 仍 malformed，因此不得进入 shadow generation 或正式生成链。

## 14. 下一步建议

下一步建议为 ZDoc Step 79：response-mode second-round prompt tuning design，docs-only；不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
