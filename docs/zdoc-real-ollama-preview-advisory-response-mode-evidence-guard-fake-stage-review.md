# ZDoc response-mode evidence guard fake stage review

## 1. 阶段目标回顾

本阶段复盘 ZDoc Step 67：response-mode / generated-preview-as-evidence guard fake-only implementation + deterministic tests。

Step 67 的目标是实现 response-mode / generated-preview-as-evidence guard 的 fake-only 第一版，通过 deterministic tests 验证 response mode 分类、thinking fallback 降级、generated preview 不得作为 evidence、formal chain 防护，以及 existing evidence anchor / quality gate / input-risk / safe endpoint 回归。

该阶段仍属于 preview-only evidence safety 工作，不是 runtime smoke，不是 shadow generation，不是 candidate patch，也不是正式生成链接入。

## 2. 实际完成情况

本阶段实际修改文件如下：

* `backend/zhifei_autoplan/ollama_preview.py`；
* `backend/zhifei_autoplan/evidence_anchor.py`；
* `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
* `backend/tests/test_ollama_preview.py`；
* `backend/tests/test_evidence_anchor.py`；
* `backend/tests/test_preview_advisory_quality_gate.py`；
* `backend/tests/test_local_llm_preview_safe_endpoint.py`。

边界情况如下：

* 未新增文件；
* 未修改 docs；
* 未修改正式生成链；
* 未修改正式导出链；
* 未修改 ZBid 写回链；
* 未写 `output/job/export`；
* 未触发 DOCX/JSON/Markdown 正式导出；
* 未启动服务；
* 未运行 Ollama；
* 未运行 `ollama serve`；
* 未真实访问 `127.0.0.1:11434`。

## 3. 测试结果复盘

测试命令：

```bash
python3 -m pytest backend/tests/test_evidence_anchor.py backend/tests/test_preview_advisory_quality_gate.py backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

测试结果：

```text
237 passed in 3.87s
```

覆盖场景摘要：

* evidence anchor；
* quality gate；
* Ollama preview normalization；
* safe endpoint metadata 回归；
* `response_advisory`；
* `json_advisory`；
* `text_fallback`；
* `thinking_only_fallback`；
* `empty_response`；
* `malformed_response`；
* `normalization_failure`；
* `generated_preview_as_evidence`；
* `system_generated_preview as evidence`；
* generated preview + direct write；
* generated preview + DOCX export；
* generated preview + ZBid writeback；
* generated preview + candidate patch；
* existing `unsupported_project_fact` / input-risk / direct write / safe endpoint 回归。

## 4. response_mode 字段复盘

本阶段新增或稳定以下 response-mode metadata 字段：

* `response_mode`；
* `response_source`；
* `preview_mode`；
* `fallback_reason`；
* `response_mode_confidence`；
* `response_mode_warnings`；
* `response_mode_review_required`；
* `thinking_fallback_detected`。

字段语义与边界如下：

* `response_mode` 仅作为 preview metadata；
* `response_mode` 不触发正式链；
* `response_mode` 不得覆盖 evidence anchor；
* `response_mode` 不得覆盖 input-risk；
* `status=ok` 不等于 response_mode 合格；
* response_mode 合格也不代表 `formal_generation_allowed=true`。

`response_mode` 的作用是说明 preview advisory 来自普通 response、JSON response、文本 fallback、thinking fallback，还是 empty / malformed / normalization failure 等受控失败路径。它不负责判断事实证据是否成立，也不负责打开正式链准入。

## 5. response-mode 分类复盘

`response_advisory`：

* 普通 response 字段形成 advisory；
* 可作为 preview advisory；
* 正式链准入字段仍 false。

`json_advisory`：

* JSON response 可提取 advisory / suggestions / risk_notes；
* 正式链准入字段仍 false。

`text_fallback`：

* 非 JSON 技术建议文本可 fallback；
* 仍需 quality gate / evidence anchor；
* 正式链准入字段仍 false。

`thinking_only_fallback`：

* 已验证 `review_required`；
* `thinking_fallback_detected=true`；
* `shadow_candidate_allowed=false`；
* 不得进入正式链。

`empty_response`：

* controlled failure 或 review_required metadata；
* 不穿透异常。

`malformed_response`：

* controlled failure；
* 不穿透异常。

`normalization_failure`：

* controlled failure；
* 不穿透异常。

## 6. generated-preview-as-evidence 复盘

本阶段新增或稳定以下 generated-preview evidence 字段：

* `generated_preview_as_evidence_detected`；
* `generated_content_must_not_be_evidence`；
* `generated_content_evidence_blocked`；
* `invalid_anchor_reason`。

已覆盖场景如下：

* generated preview used as tender evidence；
* generated preview used as drawing evidence；
* `system_generated_preview as evidence_source_type`；
* generated preview + direct write request；
* generated preview + DOCX export request；
* generated preview + ZBid writeback request；
* generated preview + candidate patch request。

关键结论：

* `system_generated_preview` 不得作为事实 evidence；
* generated preview 可作为 suggestion source，但不得作为 evidence source；
* `evidence_anchor_status` 不得因 generated preview 变为 `anchored`；
* generated preview + formal chain request 必须 blocked；
* `generated_content_must_not_be_evidence` 必须可追踪。

## 7. evidence anchor / quality gate / input-risk 集成复盘

本阶段集成关系如下：

* `generated_preview_as_evidence` 是 evidence anchor 的 `invalid_anchor` 子类；
* `response_mode` 与 `evidence_anchor_status` 分离；
* `quality_status=preview_ok` 不代表 `evidence_anchor_status=anchored`；
* `evidence_anchor_status=anchored` 不代表 `formal_generation_allowed=true`；
* `response_mode` 不得覆盖 input-risk；
* generated-preview-as-evidence 不得被 `quality_status=ok` 覆盖；
* existing evidence anchor tests 不回归；
* existing input-risk / `unsupported_project_fact` tests 不回归；
* existing quality gate tests 不回归。

该集成保持了四类门禁的职责边界：response-mode 说明输出来源，quality gate 判断 preview 输出质量，input-risk 判断输入侧风险，evidence anchor 判断事实证据状态。

## 8. DOCX / ZBid / candidate patch 防护复盘

本阶段已覆盖以下防护：

* generated preview + direct write request -> blocked；
* generated preview + DOCX export request -> blocked；
* generated preview + ZBid writeback request -> blocked；
* generated preview + candidate patch request -> blocked；
* candidate patch without valid evidence -> blocked；
* DOCX export without valid evidence -> blocked；
* ZBid writeback without valid evidence -> blocked。

执行边界如下：

* 当前未进入 DOCX 导出链；
* 当前未进入 ZBid 写回链；
* 当前未进入 candidate patch；
* 当前未进入 shadow generation。

## 9. P0 / P4 正式链准入复盘

所有状态下以下字段恒为 false：

* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`。

解释如下：

* response_mode 合格不等于正式链准入；
* evidence anchor 不等于正式链准入；
* `preview_ok` 不等于正式链准入；
* generated preview 不得作为 evidence；
* 当前阶段仍 `formal_ineligible`。

## 10. 已证明的事实

Step 67 已证明：

* response-mode guard 在 fake-only deterministic tests 下可控；
* generated-preview-as-evidence guard 在 fake-only deterministic tests 下可控；
* `thinking_only_fallback` 已可被识别并降级；
* `response_advisory` / `json_advisory` / `text_fallback` 已可被分类；
* generated preview 作为 evidence 可被 blocked / `invalid_anchor`；
* direct write / DOCX / ZBid / candidate patch 与 generated preview 叠加可被 blocked；
* no-write / preview-only 边界未破坏；
* existing evidence anchor / quality gate / input-risk / safe endpoint 回归通过；
* 未触发正式链路；
* 未写 `output/job/export`。

## 11. 尚未证明的事项

当前仍未证明：

* 未启动真实 Ollama；
* 未启动 FastAPI；
* 未做 response-mode runtime smoke；
* 未验证真实 runtime 下 `response_mode` 是否稳定；
* 未验证真实 runtime 下 generated-preview-as-evidence 是否按预期拦截；
* 未验证真实 runtime 下普通 response / JSON response 占比是否改善；
* 未验证真实 runtime 下 `thinking_only_fallback` 频率是否下降；
* 未进入 shadow generation；
* 未进入 candidate patch；
* 未进入人工确认写回；
* 未进入 DOCX 导出一致性校核；
* 未进入 ZBid 写回隔离。

## 12. 当前风险

当前风险如下：

* fake-only tests 不代表真实 runtime response-mode 稳定；
* thinking fallback 高依赖仍可能存在；
* response-mode 分类可能需要 runtime 继续校准；
* generated preview as evidence 已收紧，但需 runtime 验证；
* `generated_content_must_not_be_evidence` 字段可能被用户误解为完全禁止展示建议；
* 后续 shadow generation 若忽略 response_mode，可能误用 fallback 内容；
* 正式链写回前仍缺少 human approval / diff / rollback。

## 13. 回滚边界

回滚与兜底边界如下：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
* 保留 disabled / adapter-off / fake-only 路径；
* response-mode 异常时应 controlled failure 或 `review_required`，不得自动放行；
* generated-preview-as-evidence 异常时应 `invalid_anchor` / blocked；
* evidence anchor 异常时应 blocked 或 `system_error`；
* 不得删除 fake fixture deterministic tests；
* 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

## 14. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 Step 67 只是 response-mode / generated-preview-as-evidence guard 的 fake-only 第一版。

正式链前仍需完成：

* response-mode stage review；
* response-mode / evidence-aware runtime smoke plan；
* response-mode / evidence-aware runtime smoke；
* shadow generation 设计；
* candidate patch 设计；
* 人工确认写回；
* diff 展示；
* 版本回滚；
* DOCX 导出一致性校核；
* ZBid 写回隔离；
* 真实资料 evidence source 映射。

## 15. 当前阶段结论

本阶段仅证明 response-mode / generated-preview-as-evidence guard 在 fake-only deterministic tests 下可控，不代表真实 runtime response-mode 稳定，不代表可进入 shadow generation，不代表可进入正式生成链。

Step 67 的价值在于补齐了 response-mode 可追踪性和 generated-preview-as-evidence fail-closed 边界；但它仍只是正式链前的 preview safety 子门禁。

## 16. 下一步建议

下一步建议为 ZDoc Step 69：response-mode / evidence-aware runtime smoke plan refresh，先做 docs-only 计划。

不得直接进入 runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
