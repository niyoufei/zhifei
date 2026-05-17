# ZDoc unsupported_project_fact runtime smoke review and thinking fallback follow-up design

## 1. 阶段背景

本阶段执行 ZDoc Step 58：unsupported_project_fact targeted runtime smoke review + thinking fallback follow-up design。

前序阶段事实如下：

- Step 54 已完成 `unsupported_project_fact` guard fake-only implementation + deterministic tests；
- Step 55 已完成 fake-stage review；
- Step 56 已完成 targeted runtime smoke plan；
- Step 57 已完成 targeted runtime regression smoke + smoke report；
- Step 57 enabled targeted payload 7/7 HTTP 200、7/7 `status=ok`、7/7 `calls_ollama=true`；
- `unsupported_project_fact_detected=5`；
- `evidence_source_missing=4`；
- `project_fact_without_evidence=4`；
- `input_evidence_required / evidence_anchor_required = 7 / 7`；
- `formal_generation_allowed / shadow_candidate_allowed / writeback_allowed / export_allowed / zbid_writeback_allowed` 全部恒为 false；
- 但 6/7 payload 仍出现 thinking fallback；
- 当前不得进入 shadow generation 或正式生成链。

本步为 docs-only 复盘与后续设计步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 导出，不接 ZBid 正式写回。

## 2. Step 57 已证明的事实

Step 57 已证明以下事实：

- Ollama listener 可达；
- `qwen3:0.6b` 存在；
- safe endpoint targeted runtime 可受控返回；
- disabled 场景 stable disabled，`calls_ollama=false`；
- adapter-off 场景 fake-only `status=ok`，`calls_ollama=false`；
- enabled 7/7 `status=ok`；
- enabled 7/7 `calls_ollama=true`；
- UPF-A IR-D 等价输入不再 `preview_ok`；
- UPF-A `input_risk_status=review_required`；
- UPF-B 证据缺失 + 数量断言进入 `review_required`；
- UPF-C 安全表达进入 `review_required`；
- UPF-F Payload C 回归保护 `blocked`；
- UPF-G direct write/export 回归保护 `blocked`；
- 所有正式链准入字段恒 false；
- 未请求 `/generate`；
- 未请求 `/export_docx`；
- 未请求 `/review/apply`；
- 未直接请求 Ollama `/api/generate`；
- 未写 `output/job/export`；
- FastAPI 进程已停止；
- `18756` 端口已释放；
- 既有 Ollama listener 未被擅自停止。

这些事实说明 Step 54 的 `unsupported_project_fact` guard 已在当前真实 runtime targeted payload 下表现为可控：IR-D 类输入已能触发 input-risk，Payload C 和 direct write 回归保护没有退化，preview-only / no-write / formal-ineligible 边界保持稳定。

## 3. Step 57 尚未证明或暴露的问题

Step 57 仍暴露以下问题：

- 6/7 payload 出现 thinking fallback；
- 真实 runtime 普通 response 稳定性仍未证明；
- thinking fallback 仍是主要响应来源；
- `review_required` 不代表可正式采用；
- `unsupported_project_fact` 已能被识别，但仍需观察多轮稳定性；
- safe expression 被降级为 `review_required`，尚未建立 evidence anchor 体系；
- 尚未进入 shadow generation；
- 尚未进入正式生成链、DOCX 导出或 ZBid 写回。

因此，Step 57 不应被解释为模型质量已稳定，也不应被解释为可进入 shadow generation 或正式链。

## 4. targeted runtime 结果复盘

Step 57 摘要如下：

- disabled：HTTP 200，`status=disabled`，`calls_ollama=false`，`preview_only/no_write=true`；
- adapter-off：HTTP 200，fake-only `status=ok`，`calls_ollama=false`，`preview_only/no_write=true`；
- enabled 7/7 HTTP 200，7/7 `status=ok`，7/7 `calls_ollama=true`；
- UPF-A：`review_required / review_required / P2`；
- UPF-B：`review_required / review_required / P2`；
- UPF-C：`review_required / review_required / P2`；
- UPF-D：`review_required / review_required / P3`；
- UPF-E：`review_required / review_required / P2`；
- UPF-F：`blocked / blocked / P3`；
- UPF-G：`blocked / blocked / P0`；
- `preview_ok / review_required / blocked / system_error = 0 / 5 / 2 / 0`；
- `unsupported_project_fact_detected` 次数 = 5；
- `evidence_source_missing` 次数 = 4；
- `project_fact_without_evidence` 次数 = 4；
- `input_evidence_required / evidence_anchor_required = 7 / 7`；
- thinking fallback 出现次数 = 6；
- 正式链准入字段全 false。

其中，UPF-D 为 `text_fallback / response`，其余 UPF-A、UPF-B、UPF-C、UPF-E、UPF-F、UPF-G 均为 `thinking_only_fallback / thinking`。

## 5. 关键进展判断

Step 57 的关键进展如下：

- 已证明 `unsupported_project_fact` targeted runtime smoke 受控；
- IR-D 类输入已从此前 `input_risk_status=clear` 的缺口改善为 `review_required`；
- Payload C 回归保护仍 `blocked`；
- direct write/export 回归保护仍 `blocked`；
- no-write / preview-only / formal chain isolation 稳定；
- 该结果支持继续向 evidence anchor 体系设计推进；
- 但不支持进入 shadow generation 或正式生成链。

关键判断是：input-risk 与 evidence safety 的方向已取得进展，但模型输出形态和证据锚点体系仍未成熟，正式链前置条件仍未满足。

## 6. thinking fallback 高依赖问题定义

缺口名称：`thinking fallback high-dependency follow-up`

缺口性质：

- 不是 transport 不通；
- 不是 quality gate metadata 缺失；
- 不是 `unsupported_project_fact` 未识别；
- 而是 `qwen3:0.6b` 真实 runtime 在 targeted payload 下仍高度依赖 thinking fallback；
- thinking fallback 虽然 bounded，但不应作为正式生成依据；
- 后续必须继续追踪 `response_mode` / `preview_mode` 稳定性。

本缺口与 Step 39 的 thinking fallback 质量缺口同向，但在 Step 57 后有更明确的 runtime 证据：即使 input-risk guard 生效，当前模型仍主要通过 thinking fallback 形成 preview advisory。

## 7. thinking fallback 风险分析

thinking fallback 风险如下：

- thinking fallback 可能偏推理过程，不一定适合作为正式建议；
- thinking fallback 频率高可能说明 prompt / model / output options 仍需优化；
- thinking fallback 与 input-risk 叠加时应保持更保守；
- thinking fallback 不应进入 `shadow_candidate`；
- thinking fallback 不应进入正式正文；
- thinking fallback 不应成为 DOCX 导出内容；
- thinking fallback 不应写回 ZBid；
- `status=ok + thinking fallback` 不等于质量合格。

当前 quality gate 已对 `thinking_only_fallback` 进行降级，但后续正式链前仍需更明确的 response-first 设计、输出模式追踪和证据锚点门禁。

## 8. 后续优化方向设计

后续可选方向如下，本步不得实现：

- 设计 response-first prompt，降低 thinking fallback 依赖；
- 增加 output mode tracking；
- 区分 `response_advisory`、`json_advisory`、`text_fallback`、`thinking_only_fallback`；
- 对 thinking fallback 设更严格 quality gate；
- 在 future smoke 中统计 `response_mode` 分布；
- 在 evidence anchor 体系中要求 advisory 必须能指向证据或标记未查明；
- 在正式链前禁止 thinking fallback 直接进入 candidate patch。

建议将 thinking fallback 作为 preview-only 兜底路径，而不是正式链候选来源。即使后续 response-first prompt 有改善，也必须通过 deterministic tests 和 runtime smoke 分别验证。

## 9. evidence anchor 体系衔接

Step 57 已显示：

- `input_evidence_required / evidence_anchor_required = 7 / 7`

这说明后续应进入 evidence anchor 设计。

后续 evidence anchor 应解决：

- 哪些 advisory 需要证据锚点；
- 哪些 input-risk 需要“未查明”标识；
- 如何记录招标文件、图纸、清单、踏勘、补疑等证据来源；
- 如何在无证据时强制 `review_required` 或 `blocked`；
- 如何避免模型虚构条款、规范、图纸、清单；
- 如何为后续正式生成链建立可追溯证据基础。

evidence anchor 体系应在 preview quality gate 与未来 shadow generation 之间形成前置门禁。没有证据锚点或“未查明”标识时，不得进入 candidate patch，更不得正式写回。

## 10. 后续阶段建议

建议后续阶段顺序如下：

- ZDoc Step 59：evidence anchor framework design，docs-only；
- ZDoc Step 60：evidence anchor guard + deterministic tests design，docs-only；
- ZDoc Step 61：evidence anchor fake-only implementation + deterministic tests；
- 之后再考虑 shadow generation design。

如仍需单独归档 targeted smoke stage review，也可设置：

- Step 58A：targeted runtime smoke stage review，docs-only。

但无论选择 Step 59 还是 Step 58A，都不得直接进入正式链。

## 11. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

Step 57 只证明 preview input-risk targeted runtime smoke 受控。正式链前仍必须完成：

- evidence anchor 体系；
- shadow generation；
- candidate patch；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离。

`review_required` 不能被理解为可正式采用，`blocked` 不能被理解为系统不可用，`preview_ok` 也不能被理解为正式链准入。

## 12. 风险与回滚

风险如下：

- 风险 1：thinking fallback 高依赖被误读为模型质量稳定；
- 风险 2：`review_required` 被误认为可正式采用；
- 风险 3：`unsupported_project_fact` 虽已识别，但仍可能漏过更隐蔽事实断言；
- 风险 4：没有 evidence anchor 就进入 shadow generation；
- 风险 5：正式链写回前缺少证据溯源；
- 风险 6：未来 prompt 优化误破坏 no-write / preview-only；
- 回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 兜底措施：保留 disabled / adapter-off / fake-only 路径；
- 出现异常时不得扩大到正式链路。

后续任何 prompt、quality gate 或 evidence anchor 改动，都必须继续保持正式链准入字段恒 false，直到单独授权 shadow generation 或正式生成链阶段。

## 13. 当前阶段结论

Step 57 已证明 `unsupported_project_fact` targeted runtime regression smoke 受控，IR-D 类输入已触发 `review_required`，Payload C 与 direct write 回归保护稳定，正式链准入字段恒 false；但 6/7 payload 仍依赖 thinking fallback，普通 response 稳定性和 evidence anchor 体系仍未完成，因此不得进入 shadow generation 或正式生成链。

## 14. 下一步建议

下一步建议为 ZDoc Step 59：evidence anchor framework design，docs-only。不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
