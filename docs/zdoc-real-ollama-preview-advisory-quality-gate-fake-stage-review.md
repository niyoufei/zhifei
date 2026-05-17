# ZDoc preview advisory quality gate fake stage review

## 1. 阶段目标回顾

本阶段复盘 ZDoc Step 42：preview advisory quality gate fake-only implementation + deterministic tests。

Step 42 的目标是在不启动真实 Ollama、不访问 `127.0.0.1:11434`、不进入 shadow generation、不触发正式生成链的前提下，实现 preview advisory quality gate 的 fake-only 第一版，并通过 deterministic tests 验证：

- P0-P4 质量门禁；
- 正式链准入字段恒为 false；
- 低质输出拦截；
- thinking fallback 降级；
- no-write / preview-only 边界；
- existing `ollama_preview` 与 safe endpoint 回归。

该阶段只允许使用 fake fixture / monkeypatch / dependency injection，不依赖真实 Ollama runtime，不调用外部模型/API，不下载或拉取模型。

## 2. 实际完成情况

本阶段已经完成以下工作：

- 新增 `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
- 新增 `backend/tests/test_preview_advisory_quality_gate.py`；
- 修改 `backend/zhifei_autoplan/ollama_preview.py`；
- 修改 `backend/tests/test_ollama_preview.py`；
- 新增 `evaluate_preview_advisory_quality_gate`；
- 新增 `attach_preview_advisory_quality_gate`；
- quality gate 仅附加 preview metadata；
- `run_zdoc_ollama_preview` 的返回结果附带 `quality_gate`、`quality_status`、`quality_score`、`blockers`、`warnings`、`review_reasons`、`passed_checks`、`failed_checks` 等 metadata；
- 所有正式链准入字段仍保持 false；
- 未触发正式正文写回；
- 未触发 DOCX 导出；
- 未接 ZBid 写回。

本阶段未修改 `backend/app/routers/local_llm_preview_safe.py`。safe endpoint 仍通过既有 bridge 接收 preview result，并未新增写回、导出或正式生成能力。

## 3. 测试结果复盘

Step 42 运行的测试命令为：

```bash
python3 -m pytest backend/tests/test_preview_advisory_quality_gate.py backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

测试结果：

```text
171 passed in 4.09s
```

测试覆盖场景包括：

- 高质量 advisory；
- 低质 / 泛泛 advisory；
- `thinking_only_fallback`；
- 虚构条款 / 工程参数 / 规范编号；
- `no_write` 异常；
- `affects_generation` 异常；
- `affects_export` 异常；
- route trigger 痕迹；
- `output/job/export` 写入痕迹；
- `system_error`；
- existing `ollama_preview` no-write 回归；
- safe endpoint 回归。

该测试命令只覆盖授权的 deterministic tests，未运行全量测试，未启动服务，未运行 Ollama。

## 4. quality gate helper 复盘

新增 helper `backend/zhifei_autoplan/preview_advisory_quality_gate.py` 的定位如下：

- 只作为 preview advisory metadata gate；
- 不生成正式正文；
- 不触发生成链；
- 不触发导出链；
- 不触发 ZBid 写回；
- 不调用模型；
- 不访问 Ollama；
- 不访问外部 API；
- 不写 `output/job/export`。

`evaluate_preview_advisory_quality_gate` 负责接收 preview response 并返回 quality gate 判定结果。

`attach_preview_advisory_quality_gate` 负责把 quality gate 结果附加到 preview response 上。该函数只附加 metadata，不改变 preview-only / no-write 边界，不引入正式链行为。

## 5. quality_status 状态复盘

本阶段已覆盖以下 `quality_status`：

- `preview_ok`；
- `review_required`；
- `blocked`；
- `system_error`。

`formal_ineligible` 通过以下准入字段恒为 false 体现：

- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`。

状态语义复盘如下：

- `preview_ok` 只代表 preview 阶段可展示；
- `review_required` 只代表需要人工审核；
- `blocked` 必须拦截；
- `system_error` 必须受控；
- 当前所有状态均不得进入 shadow generation；
- 当前所有状态均不得进入正式生成链。

`status=ok` 与 `quality_status` 已分离。`status=ok` 不能被解释为质量合格，也不能被解释为正式链准入。

## 6. P0-P4 guard 复盘

### P0 安全边界 guard

P0 已覆盖以下安全边界：

- `preview_only` 异常；
- `no_write` 异常；
- `affects_generation` 异常；
- `affects_export` 异常；
- `/generate` 触发痕迹；
- `/export_docx` 触发痕迹；
- `/review/apply` 触发痕迹；
- `output/job/export` 写入痕迹；
- 正式结果字段拦截。

任一 P0 异常均返回 `quality_status=blocked`，不得进入 shadow candidate 或正式链。

### P1 响应完整性 guard

P1 已覆盖以下响应完整性要求：

- 空 advisory；
- advisory 长度；
- suggestions 数量；
- risk_notes / warnings 数量；
- `source` 追踪字段；
- `model` 追踪字段；
- `preview_mode` 追踪字段；
- `response_source` / `content_source` 追踪字段。

缺少关键追踪字段时，结果不得进入 shadow candidate。当前阶段只能进入 `review_required` 或更低状态。

### P2 输出模式 guard

P2 已覆盖以下输出模式要求：

- `thinking_only_fallback` 降级；
- `thinking_only_fallback` 不得进入 shadow_candidate；
- 普通 response 可到 `preview_ok`；
- `status=ok` 不等于 `quality_status=preview_ok`。

本阶段明确：thinking fallback 只能作为 preview-only 兜底，不得作为正式生成依据。

### P3 技术质量 guard

P3 已覆盖以下技术质量启发式：

- 泛泛模板话；
- 疑似虚构工程量；
- 疑似虚构规范编号；
- 疑似虚构招标条款；
- 疑似正式正文替换；
- 施工组织设计具体性检查；
- 量化指标、验收频次、责任岗位、整改闭环、资料归档等高质量要素识别。

本阶段采用 conservative heuristic 第一版，宁可把不确定内容降级或拦截，也不把低质 advisory 误放行到更深链路。

### P4 正式链准入 guard

P4 已证明以下字段所有状态下恒为 false：

- `formal_generation_allowed`；
- `shadow_candidate_allowed`；
- `writeback_allowed`；
- `export_allowed`；
- `zbid_writeback_allowed`。

即使 `quality_status=preview_ok`，当前阶段也不得进入 shadow generation、正式正文写回、DOCX 导出或 ZBid 写回。

## 7. 已证明的事实

本阶段已经证明：

- fake-only deterministic tests 下 quality gate 行为可控；
- conservative heuristic 第一版可拦截明显低质和高风险 advisory；
- thinking fallback 已被降级；
- 虚构条款、工程量、规范编号可被 `blocked`；
- `no_write` / preview-only 边界未破坏；
- existing `ollama_preview` 回归通过；
- safe endpoint 回归通过；
- 未触发正式链路；
- 未写 `output/job/export`。

这些事实只证明 fake-only 质量门禁的第一版可控，不证明真实 runtime 多 payload 的质量稳定。

## 8. 尚未证明的事项

当前尚未证明以下事项：

- 未启动真实 Ollama；
- 未启动 FastAPI；
- 未做 runtime quality smoke；
- 未验证真实 runtime advisory 通过 quality gate 的结果；
- 未验证多 payload 下 quality gate 稳定性；
- 未验证真实技术标内容的质量评分；
- 未进入 shadow generation；
- 未进入 candidate patch；
- 未进入人工确认写回；
- 未进入 DOCX 导出一致性校核；
- 未进入 ZBid 写回隔离。

因此，当前阶段不能被解释为正式生成链已具备接入条件。

## 9. 当前风险

当前主要风险如下：

- conservative heuristic 可能误拦截可用建议；
- heuristic 可能漏过部分低质 advisory；
- `preview_ok` 被误解为正式链准入；
- thinking fallback 虽被降级但仍可能被用户误读；
- 后续接入 shadow generation 时准入字段被误置为 true；
- 正式链写回前若缺少人工确认和 rollback，可能污染正式正文。

这些风险要求后续继续保持单步授权、docs-first、fake-only deterministic tests 优先的节奏。

## 10. 回滚边界

回滚边界如下：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
- 保留 disabled / adapter-off / fake-only 路径；
- quality gate 异常时应 `blocked` 或 `system_error`，不得自动放行；
- 不得删除 fake fixture deterministic tests；
- 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

如果后续 runtime 或多 payload smoke 出现异常，不得扩大到正式生成链，不得修改正式正文，不得触发导出链或 ZBid 写回链。

## 11. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 Step 42 只是 preview advisory quality gate 的 fake-only 第一版。正式链前仍需完成：

- quality gate stage review；
- multi-payload preview quality smoke plan；
- multi-payload preview quality smoke；
- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离。

quality gate 是正式链前置门禁，不是正式链本身。当前所有输出仍必须保持 `formal_ineligible`。

## 12. 当前阶段结论

本阶段仅证明 preview advisory quality gate 在 fake-only deterministic tests 下可控，不代表真实 runtime 多 payload 质量稳定，不代表可进入 shadow generation，不代表可进入正式生成链。

Step 42 的价值在于建立了第一版可测试、可追踪、fail-closed 的 preview advisory quality gate metadata 层，并继续保持 preview-only / no-write / formal-chain-ineligible 边界。

## 13. 下一步建议

下一步建议为 ZDoc Step 44：multi-payload preview quality smoke plan，先做 docs-only 计划。不得直接进入 multi-payload smoke，不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
