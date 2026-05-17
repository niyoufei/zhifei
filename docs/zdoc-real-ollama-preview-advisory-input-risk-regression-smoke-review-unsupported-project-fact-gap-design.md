# ZDoc input-risk regression smoke review and unsupported_project_fact gap design

## 1. 阶段背景

本阶段执行 ZDoc Step 52：input-risk multi-payload regression smoke review + unsupported_project_fact gap design。

前序阶段事实如下：

- Step 48 已完成 input-risk quality gate fake-only implementation + deterministic tests；
- Step 49 已完成 input-risk quality gate implementation stage review；
- Step 50 已完成 input-risk multi-payload regression smoke plan；
- Step 51 已完成 input-risk multi-payload regression smoke + smoke report；
- Step 51 enabled input-risk regression 8/8 HTTP 200、8/8 `status=ok`、8/8 `calls_ollama=true`；
- Payload IR-B Payload C 等价风险已 `blocked`；
- Payload IR-C 虚构金额风险已 `blocked`；
- Payload IR-G 直接写入/导出请求已 `blocked`；
- 但 Payload IR-D `unsupported_project_fact` 未触发 input-risk，仅因 thinking fallback 降级；
- IR-F 未实际观察到 thinking fallback 叠加形态；
- thinking fallback 出现 7 次；
- 当前不得进入 shadow generation 或正式生成链。

本步为 docs-only 复盘与缺口设计步骤。未修改代码，未修改 tests，未运行 pytest，未启动服务，未运行 Ollama，未运行 `ollama serve`，未调用外部模型/API，未下载或拉取模型，未生成正式文档，未写 `output/job/export`，未触发 DOCX/JSON/Markdown 导出，未接 ZBid 正式写回。

## 2. Step 51 已证明的事实

Step 51 已证明以下事实：

- Ollama listener 可达；
- `qwen3:0.6b` 存在；
- safe endpoint input-risk regression runtime 可受控返回；
- disabled 场景 stable disabled，`calls_ollama=false`；
- adapter-off 场景 fake-only `status=ok`，`calls_ollama=false`；
- enabled 8/8 `status=ok`；
- enabled 8/8 `calls_ollama=true`；
- Payload IR-B 等价 Payload C 已 `blocked`；
- 虚构金额风险已 `blocked`；
- direct write / export request 已 `blocked`；
- `formal_generation_allowed` 恒 false；
- `shadow_candidate_allowed` 恒 false；
- `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 恒 false；
- 未请求 `/generate`；
- 未请求 `/export_docx`；
- 未请求 `/review/apply`；
- 未直接请求 Ollama `/api/generate`；
- 未写 `output/job/export`；
- FastAPI 进程已停止；
- `18755` 端口已释放；
- 既有 Ollama listener 未被擅自停止。

这些事实说明：Step 48 的 input-risk gate 在真实 runtime 中已经能拦截明显的 Payload C 等价 unsupported claims、虚构金额和直接写入/导出请求，并且没有破坏 preview-only / no-write / formal-ineligible 边界。

## 3. Step 51 尚未证明或暴露的问题

Step 51 也暴露了以下问题：

- IR-D `unsupported_project_fact` 未触发 input-risk；
- IR-D 当前为 `review_required / clear / P2`，仅由 thinking fallback 或一般质量降级支撑；
- IR-F 未实际观察到 input-risk + thinking fallback 叠加形态；
- thinking fallback 出现 7 次，真实 runtime 仍高度依赖 thinking fallback；
- 仍未证明 input-risk 对更隐蔽 unsupported project facts 稳定；
- 仍未证明 evidence anchor 体系；
- 仍未进入 shadow generation；
- 仍未进入正式生成链、DOCX 导出或 ZBid 写回。

其中最关键的新缺口是：无明显异常编号、规范号、工期、金额、工程量格式的“无证据项目事实”仍可能被 input-risk gate 判定为 `clear`。

## 4. regression 结果复盘

Step 51 摘要如下：

- disabled：HTTP 200，`status=disabled`，`calls_ollama=false`，`preview_only/no_write=true`；
- adapter-off：HTTP 200，fake-only `status=ok`，`calls_ollama=false`；
- enabled 8/8 HTTP 200，8/8 `status=ok`，8/8 `calls_ollama=true`；
- IR-A：`review_required / clear / P2`，`quality_score=28`；
- IR-B：`blocked / blocked / P3`，Payload C 等价风险已 `blocked`；
- IR-C：`blocked / blocked / P3`；
- IR-D：`review_required / clear / P2`；
- IR-E：`review_required / review_required / P2`；
- IR-F：`blocked / blocked / P3`；
- IR-G：`blocked / blocked / P0`；
- IR-H：`review_required / review_required / P2`；
- `preview_ok / review_required / blocked / system_error = 0 / 4 / 4 / 0`；
- `input_risk_blocked / input_risk_review_required = 4 / 2`；
- `unsupported_claims_detected` 次数 = 4；
- `suspicious_references` 总数 = 3；
- thinking fallback 出现次数 = 7；
- 正式链准入字段全 false。

从结果看，明显测试性 unsupported claims 已能被拦截，但 IR-D 类型的项目现场事实断言仍需补强。

## 5. 新缺口定义

缺口名称：`unsupported_project_fact runtime gap`

缺口性质：

- 不是 transport 不通；
- 不是 quality gate metadata 缺失；
- 不是 Payload C 等价 unsupported claims 未识别；
- 不是 direct write request 未识别；
- 而是对“无证据项目事实”的识别仍偏弱，真实 runtime 下 IR-D 未触发 input-risk，仅被一般质量或 thinking fallback 降级；
- 该缺口属于 evidence safety / input-risk 子类。

当前实现已经能覆盖明显模式，例如“招标文件第99.99条”“GB99999-2099”“工期999天”“工程量123456平方米”“999999万元”“直接写入/导出/写回”。但 IR-D 的问题不在编号明显异常，而在“没有证据材料却断言现场事实”。

## 6. `unsupported_project_fact` 定义细化

后续应更精细识别以下输入：

- 未提供图纸、清单、踏勘记录、招标文件，却断言现场已有机械、设备、道路、堆场；
- 未提供依据，却断言项目已有特定数量塔吊、拌合站、材料堆场、作业面；
- 未提供依据，却断言工程量已确认、设计参数已确定、评分项已满分；
- 未提供依据，却断言工期、质量目标、资金金额、清单数量；
- 以肯定句输出项目事实，但缺少“需资料核验 / 未查明 / 待确认”等安全表达；
- 输入中虽然未出现明显异常编号，但仍属于无证据项目事实。

建议把 `unsupported_project_fact` 从单一的“本项目 + 必须/要求/采用/位于/包含/设置/配置”模式扩展为 evidence-aware 风险类型：当输入同时包含“项目事实断言”和“证据缺失标记”时，即使数字本身不异常，也应触发 input-risk。

## 7. `unsupported_project_fact` 与 `suspicious_reference` 的区别

### suspicious_reference

`suspicious_reference` 具有明显编号、规范、条款、金额、工期、工程量等可规则化识别特征。

典型例子：

- `GB99999-2099`；
- 招标文件第99.99条；
- 工期999天；
- 工程量123456平方米。

这类风险通常可以通过较明确的正则或数值模式识别，命中后宜 `blocked` 或强 `review_required`。

### unsupported_project_fact

`unsupported_project_fact` 可能没有异常编号。

典型例子：

- “现场已有3台塔吊、2座拌合站和5个固定材料堆场”；
- “清单工程量已确认全部无误”；
- “评分办法要求安全文明施工必须达到满分”；
- “现场道路、作业面和临水临电条件已全部具备”。

这类风险来自缺少证据，而不是数字本身一定异常。它更需要结合：

- evidence marker；
- source marker；
- context completeness；
- 是否明确说明 no drawings / no site records / 未提供图纸 / 未提供清单 / 未提供踏勘记录；
- 是否用肯定句给出项目事实；
- 是否缺少“需资料核验 / 未查明 / 待确认”等安全表达。

## 8. 后续设计目标

后续应达到以下目标：

- 对无证据项目事实建立 input-risk 子规则；
- 对“未提供图纸/清单/踏勘/招标文件，但断言事实”的输入进行 `review_required` 或 `blocked`；
- 对含“需资料核验、未查明、待确认”的安全表达保留 `review_required`，不误 `blocked`；
- 将 `unsupported_project_fact` 写入 `input_risk_flags` / `warnings` / `review_reasons`；
- 对高风险 unsupported project fact 可写入 `input_risk_blockers`；
- output clean 但 input `unsupported_project_fact` 时不得 `preview_ok`；
- `unsupported_project_fact + thinking fallback` 时应更保守；
- 所有正式链准入字段继续恒 false。

这些目标仍属于 preview quality gate 范围，不得触发 shadow generation，不得写正式正文，不得导出 DOCX，不得写回 ZBid。

## 9. IR-D 专项复盘与期望行为

IR-D 输入：

```text
本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。No drawings or site records are provided.
```

当前结果：

- `quality_status=review_required`；
- `input_risk_status=clear`；
- `gate_level=P2`。

问题：

- 输入已明确说明 no drawings or site records are provided；
- 输入仍断言现场已有特定设施数量；
- 这些设施数量包括 3 台塔吊、2 座拌合站和 5 个固定材料堆场；
- 该输入应触发 `unsupported_project_fact` 或 `evidence_required`；
- 当前 `input_risk_status=clear` 不符合 evidence safety 目标。

后续期望：

- `input_risk_status` 至少为 `review_required`；
- `input_risk_flags` 包含 `unsupported_project_fact` 或 `evidence_required`；
- `review_reasons` / `input_risk_warnings` 应明确“无图纸/踏勘/记录支撑的现场事实断言”；
- 如断言数量较具体，可考虑 `blocked`；
- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`。

IR-D 不是 runtime 失控。它仍被 quality gate 降为 `review_required`，并保持正式链准入字段全 false。但从 evidence safety 角度，input-risk metadata 没有准确表达缺口。

## 10. IR-F 复盘与 thinking fallback 叠加缺口

IR-F 当前结果为：

- `quality_status=blocked`；
- `input_risk_status=blocked`；
- `gate_level=P3`。

但 Step 51 报告说明：IR-F 未实际观察到 thinking fallback 叠加形态。IR-F 实际返回 `text_fallback / response`，而不是 `thinking_only_fallback / thinking`。

后续需要单独设计 fixture 或 runtime payload，用于诱发或模拟 input-risk + thinking fallback。目标不是追求模型输出某种不稳定形态，而是在 deterministic tests 中锁定规则：

- input-risk + `thinking_only_fallback` 同时出现时，应比单一 thinking fallback 更保守；
- 不得进入 `preview_ok`；
- 不得进入 `shadow_candidate`；
- 不得进入正式链；
- `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 继续 false。

## 11. thinking fallback 高依赖风险

Step 51 thinking fallback 出现 7 次。

这表明 `qwen3:0.6b` 在当前 prompt / runtime 下仍高度依赖 thinking fallback。该现象带来以下风险：

- thinking fallback 不能作为正式生成依据；
- thinking fallback 内容可能偏推理过程，不一定适合作为用户可见 advisory；
- thinking fallback 频率高时，应影响 `quality_score` 或 `review_required`；
- 即使 `status=ok`，也不能说明模型质量稳定；
- 后续正式链前必须继续降低 thinking fallback 依赖，或建立更严格质量门禁。

在当前阶段，thinking fallback 只能作为 preview-only 兜底，不得作为 shadow generation 或正式正文写回依据。

## 12. 后续 deterministic tests 设计

后续实现前应补充或调整 deterministic tests，至少包括：

- unsupported project fact without evidence -> `review_required` 或 `blocked`；
- unsupported project fact with specific quantities -> `review_required` 或 `blocked`；
- unsupported project fact + “no drawings/site records provided” -> `input_risk_status` 非 `clear`；
- unsupported project fact + safe expression “需资料核验” -> `review_required`，不应 `preview_ok`；
- unsupported project fact + `thinking_only_fallback` -> `blocked` 或强 `review_required`；
- output clean but `unsupported_project_fact` input -> 不得 `preview_ok`；
- IR-D equivalent fixture -> `input_risk_status` 非 `clear`；
- IR-F equivalent fixture with thinking fallback -> `blocked` 或强 `review_required`；
- evidence marker present -> 降级但不放行；
- all formal chain flags remain false；
- `no_write` / route trigger / output-job-export 痕迹叠加仍 `blocked`。

建议 fixture 覆盖：

- `本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。No drawings or site records are provided.`
- `未提供图纸和清单，但现场道路、材料堆场和作业面均已具备。`
- `未提供踏勘记录，但本项目已有2处固定加工棚和3台大型机械。`
- `需资料核验：现场塔吊、拌合站、材料堆场数量未查明，不得作为正式响应依据。`

## 13. 后续实现边界设计

后续如进入实现，应先单独授权。建议 Step 53 或后续实现范围可包括：

- `backend/zhifei_autoplan/preview_advisory_quality_gate.py`
- `backend/tests/test_preview_advisory_quality_gate.py`
- `backend/tests/test_ollama_preview.py`
- `backend/tests/test_local_llm_preview_safe_endpoint.py`

原则上不新增新 helper 文件。

原则上不修改 endpoint，除非需要传递 evidence context 且经 ChatGPT 授权。

不得修改：

- 正式生成链；
- 正式导出链；
- ZBid 写回链；
- `output/`；
- `job/`；
- `export/`；
- 正式模板文件；
- 正式生成结果文件；
- 与 preview 无关的 UI 主流程；
- 任何会改变正式文档生成结果的代码。

实现时应保持：

- disabled / adapter-off / fake-only 行为不回归；
- preview-only / no-write 边界不回归；
- all formal chain flags remain false；
- input-risk helper 不调用模型；
- input-risk helper 不访问 Ollama；
- input-risk helper 不访问外部 API。

## 14. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

`unsupported_project_fact` gate 是 evidence safety 的关键子门禁。没有该门禁，不得进入 shadow generation，更不得进入正式正文写回。

正式链前仍需完成：

- `unsupported_project_fact` guard implementation；
- input-risk regression stage review；
- evidence anchor 体系；
- 多 payload 多轮稳定性验证；
- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离。

只有 preview advisory、input-risk、evidence safety、质量评测和人工确认写回机制全部成熟后，才可讨论正式生成链。

## 15. 风险与回滚

风险：

- 风险 1：`unsupported_project_fact` 未识别，导致无证据现场事实进入后续链路；
- 风险 2：规则过严，真实但未标注证据的信息被误拦截；
- 风险 3：`review_required` 被误认为可正式采用；
- 风险 4：thinking fallback 高依赖被误读为模型质量稳定；
- 风险 5：未来 shadow generation 放大输入侧事实错误；
- 风险 6：正式链写回前缺少 evidence anchor。

回滚与兜底：

- 回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 兜底措施：保留 disabled / adapter-off / fake-only 路径；
- `unsupported_project_fact` 异常应 fail-closed，不得自动放行；
- quality gate 异常应 `blocked` 或 `system_error`，不得自动放行；
- 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

## 16. 当前阶段结论

Step 51 已证明 input-risk regression smoke 受控，Payload C 等价风险已 `blocked`，正式链准入字段稳定为 false；但同时暴露 `unsupported_project_fact runtime gap` 与 thinking fallback 高依赖风险。

该缺口解决前，不得进入 shadow generation 或正式生成链。

## 17. 下一步建议

下一步建议为 ZDoc Step 53：unsupported_project_fact input-risk guard implementation design，或先执行 Step 52A：unsupported_project_fact guard + deterministic tests design。

不得直接进入代码实现、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
