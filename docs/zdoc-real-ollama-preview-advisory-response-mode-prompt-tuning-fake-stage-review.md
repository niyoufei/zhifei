# ZDoc response-mode prompt tuning fake-stage review

## 1. 阶段目标回顾

本阶段为 ZDoc Step 75：response-mode prompt tuning implementation stage review。

Step 74 的目标是：实现 response-mode prompt tuning 的 fake-only 第一版，通过 deterministic tests 验证 response-first、JSON-first、text-fallback、evidence-aware prompt、adapter-off schema follow-up 等逻辑，并继续保持 preview-only、no-write、正式链准入字段恒 false。

Step 74 的定位仍是 preview adapter 前置能力建设。它不是 runtime smoke，不启动真实 Ollama，不证明真实 runtime 下 response mode 已稳定，也不进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

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

Step 74 的代码改动集中在 Ollama preview prompt 构造与 fake-only deterministic tests。未修改 endpoint schema，未新增 helper 文件，未扩大到正式链路。

## 3. 测试结果复盘

Step 74 执行的测试命令为：

```bash
python3 -m pytest backend/tests/test_ollama_preview.py backend/tests/test_evidence_anchor.py backend/tests/test_preview_advisory_quality_gate.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

测试过程：

* 首次 3 个新增断言失败；
* 失败原因均为新增测试断言与现有 prompt 文案大小写、现有 input-risk 字段命名不匹配；
* 修复后重跑同一条授权测试命令；
* 最终通过。

最终结果：

```text
244 passed in 3.70s
```

覆盖场景总结：

* response-mode prompt tuning；
* Ollama preview normalization；
* evidence anchor；
* quality gate；
* input-risk；
* safe endpoint 回归；
* response-first prompt；
* JSON-first prompt；
* text-fallback prompt；
* evidence-aware prompt；
* adapter-off compatible payload；
* adapter-off illegal field controlled failure；
* generated-preview-as-evidence 回归；
* formal chain attempt 回归。

## 4. response-first prompt 复盘

Step 74 新增 fake transport 捕获 prompt，用于验证 response-first prompt 构造。

已验证内容如下：

* 已验证 `response_first` 构造；
* 已验证 `response_advisory` 分类；
* prompt 明确只输出用户可见短 advisory；
* prompt 明确不要输出推理过程；
* prompt 明确不写正式正文；
* prompt 明确不导出、不写回、不 apply；
* prompt 明确不得虚构招标条款、图纸、清单、规范、工程量。

response-first prompt 仅用于 preview advisory。它不写正式正文，不触发导出或写回，不绕过 quality gate、input-risk gate、evidence anchor，也不改变 formal chain flags。

## 5. JSON-first prompt 复盘

Step 74 新增 fake JSON 响应，用于验证 JSON-first prompt 和 JSON advisory 解析路径。

已验证内容如下：

* 已验证 JSON-first prompt；
* 已验证 `json_advisory`；
* JSON-first prompt 要求输出短 JSON object；
* 建议字段包括 `advisory`、`suggestions`、`risk_notes`；
* JSON 输出仅作为 preview metadata / advisory 解析来源；
* 不生成 Markdown 文档；
* 不生成正式章节；
* 不写入任何系统。

JSON-first prompt 仍属于 preview-only 输出模式。即使 JSON advisory 能被解析，也不代表正式链准入。

## 6. text-fallback prompt 复盘

Step 74 新增非 JSON 短文本 fake 响应，用于验证 text fallback prompt。

已验证内容如下：

* 已验证 `text_fallback`；
* 非 JSON 技术建议可受控进入 preview advisory；
* text fallback prompt 明确 preview-only；
* text fallback prompt 明确不得写正式正文；
* text fallback prompt 不得绕过 evidence anchor；
* text fallback 仍需 quality gate / evidence anchor；
* text fallback 不得进入正式链。

该路径用于在 JSON 不适用或普通 response 较自然时保留短 advisory 兜底，不用于正文生成、DOCX 导出或 ZBid 写回。

## 7. evidence-aware prompt 复盘

Step 74 已验证缺证据项目事实触发 `review_required` / `missing`。

evidence-aware prompt 的边界如下：

* 不得臆断招标条款；
* 不得臆断图纸；
* 不得臆断清单；
* 不得臆断规范；
* 不得臆断工程量；
* 涉及条款、图纸、清单、规范、工程量时，应提示需资料核验 / 未查明；
* generated preview 仍不得作为 evidence；
* evidence missing 仍不得 formal eligible；
* all formal chain flags remain false。

该结果说明 prompt tuning 没有绕过 evidence anchor。prompt 可以让 advisory 更短、更清晰，但证据准入仍由 evidence anchor、input-risk gate 和 quality gate 控制。

## 8. adapter-off schema follow-up 复盘

Step 74 对 adapter-off schema follow-up 做了 deterministic tests 覆盖。

已验证内容如下：

* adapter-off compatible payload 继续通过 fake-only helper；
* adapter-off illegal field fixture 已返回 controlled `illegal_field:content`；
* adapter-off schema 差异得到测试覆盖；
* illegal field 不会调用 safe helper；
* illegal field 不会调用 real adapter；
* illegal field 不会写盘；
* illegal field 不会触发正式链路。

该能力只证明 controlled behavior，不代表 runtime smoke 已验证。后续 smoke payload 仍需统一 schema，优先使用 endpoint-compatible 字段，例如 `request_id`、`section_title`、`section_text`、`context_summary`。

## 9. generated-preview-as-evidence / formal chain 回归复盘

Step 74 回归验证 generated-preview-as-evidence 与 formal chain attempt。

已验证内容如下：

* generated preview as evidence 仍为 `invalid_anchor` / blocked；
* generated preview + formal chain request 仍 blocked；
* DOCX / ZBid / apply request 仍不得执行；
* model-generated advisory 仍不得作为 evidence source；
* `formal_generation_allowed=false`；
* `shadow_candidate_allowed=false`；
* `writeback_allowed=false`；
* `export_allowed=false`；
* `zbid_writeback_allowed=false`。

该结果说明 prompt tuning 没有放宽 generated-preview-as-evidence guard，也没有打开正式链准入。

## 10. 已证明的事实

本阶段已证明：

* fake-only deterministic tests 下 response-mode prompt tuning guard 可控；
* response-first、JSON-first、text-fallback 三类 prompt 路径已有受控测试基础；
* evidence-aware prompt 遇到 missing source 仍进入 review_required / missing；
* adapter-off schema compatible / illegal field 均已受控；
* generated-preview-as-evidence 回归仍 blocked / invalid_anchor；
* formal chain attempt 回归仍 blocked；
* existing evidence anchor 回归通过；
* existing quality gate 回归通过；
* existing input-risk 回归通过；
* existing safe endpoint 回归通过；
* 未触发正式链路；
* 未写 `output/job/export`。

## 11. 尚未证明的事项

本阶段尚未证明：

* 未启动真实 Ollama；
* 未启动 FastAPI；
* 未做 runtime smoke；
* 未证明真实 runtime 下 `thinking_only_fallback` 频率下降；
* 未证明真实 runtime 下 `response_advisory` 稳定；
* 未证明真实 runtime 下 `json_advisory` 稳定；
* 未证明真实 runtime 下 `text_fallback` 稳定；
* 未证明 `qwen3:0.6b` 在 prompt tuning 后可稳定输出普通 response；
* 未进入 shadow generation；
* 未进入 candidate patch；
* 未进入人工确认写回；
* 未进入 DOCX 导出一致性校核；
* 未进入 ZBid 写回隔离。

因此，Step 74 的通过结果只能说明 fake-only 规则与测试基础已就绪，不能说明真实 runtime response-mode 问题已经解决。

## 12. 当前风险

当前风险如下：

* fake-only tests 不代表真实 runtime response-mode 稳定；
* `thinking_only_fallback` 可能仍高频；
* response-first prompt 可能在真实 runtime 下无效；
* JSON-first prompt 可能出现伪 JSON 或格式不稳定；
* adapter-off schema 差异仍需 runtime 复查；
* `response_advisory` / `json_advisory` 可能被误解为正式链准入；
* prompt tuning 可能在后续实现中弱化 evidence safety，需继续 guard。

这些风险在进入 runtime smoke 前仍需通过 docs-only plan refresh 明确边界；在进入 shadow generation 或正式链前，还需更多 runtime evidence 与人工确认流程设计。

## 13. 回滚边界

回滚与兜底边界如下：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
* 保留 disabled / adapter-off / fake-only 路径；
* response-mode 异常时应 controlled failure 或 `review_required`，不得自动放行；
* generated-preview-as-evidence 异常时应 `invalid_anchor` / blocked；
* evidence anchor 异常时应 blocked 或 `system_error`；
* 不得删除 fake fixture deterministic tests；
* 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

如后续 runtime smoke 发现 prompt tuning 无法降低 thinking fallback 频率，应保持 preview-only、no-write、formal-ineligible，不得用 status=ok 或 response_mode 改善作为正式链准入依据。

## 14. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 Step 74 只是 response-mode prompt tuning 的 fake-only 第一版。

正式链前仍需完成：

* prompt tuning stage review；
* response-mode runtime smoke plan refresh；
* response-mode runtime smoke；
* runtime smoke review；
* shadow generation 设计；
* candidate patch 设计；
* 人工确认写回；
* diff 展示；
* 版本回滚；
* DOCX 导出一致性校核；
* ZBid 写回隔离。

在以上阶段完成前，response-mode prompt tuning 只能作为 preview runtime 稳定性改进，不能作为正式生成链准入凭据。

## 15. 当前阶段结论

本阶段仅证明 response-mode prompt tuning 在 fake-only deterministic tests 下可控，不代表真实 runtime 下 `thinking_only_fallback` 频率已下降，不代表可进入 runtime smoke以外的下一阶段，更不代表可进入 shadow generation 或正式生成链。

## 16. 下一步建议

下一步建议为 ZDoc Step 76：response-mode runtime smoke plan refresh，先做 docs-only 计划。不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
