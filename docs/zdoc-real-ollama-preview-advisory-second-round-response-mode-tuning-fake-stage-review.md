# ZDoc Step 81: second-round response-mode prompt tuning implementation stage review

## 1. 阶段目标回顾

Step 80 的目标是实现二轮 response-mode prompt tuning 的 fake-only 第一版，通过 deterministic tests 验证 response-first、JSON-first、text-fallback、thinking fallback 降级、adapter-off schema、prompt_mode metadata、generated-preview-as-evidence 回归、evidence anchor / quality gate / input-risk / safe endpoint 回归，并继续保持 preview-only、no-write、正式链准入字段恒 false。

本阶段仍属于 preview adapter 前置能力建设。它不启动真实 Ollama，不证明真实 runtime 下 response mode 已稳定，也不进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

## 2. 实际完成情况

本阶段实际修改文件如下：

* `backend/zhifei_autoplan/ollama_preview.py`；
* `backend/tests/test_ollama_preview.py`；
* `backend/tests/test_local_llm_preview_safe_endpoint.py`。

实际完成情况如下：

* 未新增文件；
* 未修改 docs；
* 未修改正式生成链；
* 未修改正式导出链；
* 未修改 ZBid 写回链；
* 未写 `output/job/export`；
* 未触发 DOCX/JSON/Markdown 正式导出；
* 未启动服务；
* 未运行 Ollama；
* 未真实访问 `127.0.0.1:11434`。

Step 80 的代码改动集中在 Ollama preview prompt 构造、prompt metadata 输出、JSON-first 受控失败/兜底，以及 fake-only deterministic tests。未修改 endpoint schema，未新增 helper 文件，未扩大到正式链路。

## 3. 测试结果复盘

Step 80 执行的测试命令为：

```bash
python3 -m pytest backend/tests/test_ollama_preview.py backend/tests/test_evidence_anchor.py backend/tests/test_preview_advisory_quality_gate.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

测试结果：

```text
246 passed in 3.56s
```

覆盖场景总结：

* Ollama preview normalization；
* response-mode prompt tuning；
* evidence anchor；
* quality gate；
* input-risk；
* safe endpoint 回归；
* second-round response-first prompt；
* second-round JSON-first prompt；
* text-fallback stabilized；
* thinking fallback 降级；
* adapter-off compatible payload；
* adapter-off illegal field；
* prompt_mode metadata；
* generated-preview-as-evidence 回归。

## 4. second-round response-first prompt 复盘

Step 80 已验证 second-round response-first prompt 的以下能力：

* 已验证短句 advisory；
* 已验证禁止 reasoning / chain-of-thought；
* 已验证禁止正式正文 / 导出 / 写回；
* 已验证缺证据提示 verification；
* fake response 可归类为 `response_advisory`；
* `response_advisory` 仅为 preview advisory；
* 不进入 `shadow_candidate`；
* 不进入正式生成链。

该路径的目标是提高普通 response 中用户可见短 advisory 的出现概率。即使 fake-only tests 中可归类为 `response_advisory`，也不能解释为真实 runtime 已稳定，更不能解释为正式链准入。

## 5. second-round JSON-first prompt 复盘

Step 80 已验证 second-round JSON-first prompt 的以下能力：

* 已验证单行 JSON；
* 已验证禁止 code fence / 解释性文字；
* valid JSON 可归类为 `json_advisory`；
* fenced JSON 可进入 controlled malformed；
* JSON plus explanation 可进入 `text_fallback`；
* `json_advisory` 仅为 preview advisory；
* 不生成正式章节；
* 不写入任何系统。

JSON-first 的目标是提升 preview metadata 和 advisory 解析稳定性。它不得生成 JSON 文件，不得生成 Markdown 文档，不得成为正式章节，也不得绕过 evidence safety。

## 6. text-fallback stabilized 复盘

Step 80 已验证短非 JSON 技术建议可稳定归类为 `text_fallback`。

`text_fallback` 保持 preview-only。`text_fallback` 仍需 evidence anchor / quality gate / input-risk。`text_fallback` 不进入 `shadow_candidate`，不进入正式链。

该路径用于在 JSON 不适用、JSON 输出不稳定或普通 response 不符合结构化预期时保留短 advisory 兜底。它不是正式正文生成能力，也不代表可进入 candidate patch、DOCX 导出或 ZBid 写回。

## 7. thinking fallback 降级复盘

Step 80 继续验证 thinking fallback 降级：

* `thinking_only_fallback` 仍为 bounded preview；
* `thinking_only_fallback` 仍 `review_required`；
* `thinking_fallback_detected` 可追踪；
* `shadow_candidate_allowed=false`；
* `thinking_only_fallback` 不得进入 candidate patch；
* 不得进入正式正文；
* 不得触发 DOCX 导出；
* 不得写回 ZBid。

即使 thinking fallback 的内容看起来可读，它仍是 preview-only fallback，不得作为正式建议来源或正式链准入依据。

## 8. adapter-off schema 复盘

Step 80 保持 adapter-off schema 双路径受控：

* adapter-off compatible payload 保持通过；
* `content` illegal field 继续 controlled `illegal_field:content`；
* adapter-off schema 差异已纳入 deterministic tests；
* adapter-off schema failure 不得误判为 real runtime failure；
* 不得为了 smoke 兼容放松安全字段校验。

该结果说明 adapter-off schema guard 继续可控。后续 runtime smoke 正常路径仍应使用 compatible schema，并保留 illegal field fixture 作为 controlled failure 回归。

## 9. prompt_mode metadata 复盘

Step 80 新增或稳定以下字段：

* `prompt_mode`；
* `prompt_profile`；
* `prompt_version`；
* `prompt_tuning_applied`；
* `prompt_tuning_warnings`；
* `json_mode_requested`；
* `response_first_requested`；
* `text_fallback_allowed`；
* `evidence_aware_prompt_applied`；
* `adapter_schema_mode`。

字段语义如下：

* `prompt_mode` 仅为 preview metadata；
* `prompt_mode` 不触发正式链；
* `prompt_mode` 不得覆盖 `response_mode`；
* `prompt_mode` 不得覆盖 evidence anchor；
* `prompt_mode` 不得覆盖 quality gate / input-risk。

这些字段用于后续 runtime smoke 统计与回归排查，不是正式链准入条件。

## 10. generated-preview-as-evidence 回归复盘

Step 80 验证 generated-preview-as-evidence 回归未破坏：

* generated preview 作为 evidence 仍触发 `invalid_anchor` / blocked；
* generated preview 不得作为 evidence source；
* generated preview + formal chain request 仍 blocked；
* `generated_content_must_not_be_evidence` 仍可追踪；
* 不允许将 model-generated advisory 当作 tender / drawing / boq / scoring evidence。

该结果说明二轮 prompt tuning 没有放松 generated-preview-as-evidence guard，也没有把 model-generated advisory 转化为证据来源。

## 11. evidence anchor / quality gate / input-risk / safe endpoint 回归复盘

Step 80 的 deterministic tests 继续覆盖并通过以下回归：

* existing evidence anchor guard 未回归；
* quality gate 未回归；
* input-risk gate 未回归；
* unsupported_project_fact guard 未回归；
* direct write guard 未回归；
* safe endpoint metadata 回归通过；
* no-write / preview-only 边界保持稳定。

prompt tuning 只改变 preview adapter 的 prompt 与 metadata 可观测性，不改变 evidence anchor、quality gate、input-risk 或 safe endpoint 的安全边界。

## 12. P0 / P4 正式链准入复盘

所有状态下以下字段恒为 false：

* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`。

说明：

* `response_advisory` 不等于正式链准入；
* `json_advisory` 不等于正式链准入；
* `text_fallback` 不等于正式链准入；
* prompt tuning 成功不等于正式链准入；
* 当前阶段仍 `formal_ineligible`。

## 13. 已证明的事实

本阶段已证明：

* fake-only deterministic tests 下二轮 prompt tuning guard 可控；
* response-first / JSON-first / text-fallback 三类路径已有测试基础；
* adapter-off compatible / illegal field 均受控；
* generated-preview-as-evidence 回归稳定；
* evidence anchor / quality gate / input-risk / safe endpoint 回归通过；
* 未触发正式链路；
* 未写 `output/job/export`。

这些事实只适用于 fake-only deterministic tests，不等于真实 runtime response-mode 已稳定。

## 14. 尚未证明的事项

本阶段尚未证明：

* 未启动真实 Ollama；
* 未启动 FastAPI；
* 未做二轮 runtime smoke；
* 未证明真实 runtime 下 `thinking_only_fallback` 频率下降；
* 未证明真实 runtime 下 `response_advisory` 稳定；
* 未证明真实 runtime 下 `json_advisory` 稳定；
* 未证明真实 runtime 下 `text_fallback` 稳定提升；
* 未进入 shadow generation；
* 未进入 candidate patch；
* 未进入人工确认写回；
* 未进入 DOCX 导出一致性校核；
* 未进入 ZBid 写回隔离。

因此，Step 80 的通过结果只能说明 fake-only 规则与测试基础已就绪，不能说明真实 runtime response-mode 问题已经解决。

## 15. 当前风险

当前风险如下：

* fake-only tests 不代表真实 runtime response-mode 稳定；
* `thinking_only_fallback` 可能仍高频；
* response-first prompt 在真实模型下可能仍无效；
* JSON-first prompt 真实输出可能仍 malformed；
* `text_fallback` 可能被误认为正式正文能力成熟；
* prompt_mode metadata 可能被误解为正式链准入；
* 后续 runtime smoke 仍需严格隔离正式链。

这些风险需要在 Step 82 runtime smoke plan refresh 中继续收口，并在 Step 83 runtime smoke 中用真实 runtime 结果复核。

## 16. 回滚边界

回滚与兜底边界如下：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
* 保留 disabled / adapter-off / fake-only 路径；
* response-mode 异常时应 controlled failure 或 `review_required`，不得自动放行；
* prompt tuning 异常不得影响正式生成链；
* evidence anchor 异常时应 blocked 或 `system_error`；
* 不得删除 fake fixture deterministic tests；
* 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

如后续 runtime smoke 发现二轮 prompt tuning 仍无法稳定产生非 thinking response mode，应保持 preview-only、no-write、formal-ineligible，不得以 fake-only 通过结果扩大到正式链。

## 17. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 Step 80 只是二轮 response-mode prompt tuning 的 fake-only 第一版。

正式链前仍需完成：

* implementation stage review；
* second-round runtime smoke plan refresh；
* second-round runtime smoke；
* runtime smoke review；
* shadow generation design；
* candidate patch design；
* human approval / diff / rollback design；
* DOCX export consistency design；
* ZBid writeback isolation design。

在这些阶段完成前，不得进入正式正文写回、DOCX 导出或 ZBid 写回。

## 18. 当前阶段结论

本阶段仅证明 second-round response-mode prompt tuning 在 fake-only deterministic tests 下可控，不代表真实 runtime 下 response_advisory / json_advisory / text_fallback 已稳定，不代表可进入 shadow generation 或正式生成链。

## 19. 下一步建议

下一步建议为 ZDoc Step 82：second-round response-mode runtime smoke plan refresh，docs-only。不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
