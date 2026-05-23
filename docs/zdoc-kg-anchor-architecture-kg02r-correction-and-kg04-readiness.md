# KG-02R 修正纳入 ZDoc KG 架构基线与 KG-04 准入边界

## 1. 文档定位

本文是 KG-03R docs-only 补正归档，用于将 KG-02R 的复核结论纳入 KG-03 已归档的 ZDoc 知识锚点架构基线。

本文不进入 KG-04，不生成 manifest 实体文件，不生成知识包实体文件，不复制 `/Users/youfeini/Desktop/AI知识图谱大全` 中的任何原始资料，不接入 RAG、prompt registry 或 system instruction registry，不改变 ZDoc 代码、测试、前端、后端、配置、运行链、评分链、导出链或写回链。

## 2. KG-02R 复核摘要

KG-02R 复核确认 KG-01 的基础统计仍成立：

- 总文件数：170。
- 总目录数：49，含根目录；子目录 48。
- 总大小：5,261,921 bytes。
- 扩展名统计：`md=130`、无扩展名 26、`sample=14`。
- 排除 `.git`、`.DS_Store`、`.sample` 后，业务侧文件为 131 个。
- 其中知识 markdown 为 130 个。
- `河道整治工程/.gitignore` 属业务侧可见文件，但应按非知识内容处理。

KG-02R 对 KG-02 的主要校正：

- 系统指令候选仍为 24 个。
- prompt pack 候选仍为 4 个。
- 知识图谱 / schema 候选仍为 86 个。
- 青天评标 / 评分响应候选仍为 59 个。
- 模板 / 案例库候选仍为 22 个。
- 施工组织设计 / RAG 候选应由 43 校正为 61。
- 风险统计应从笼统 Medium 口径改为 R0-R4 口径。
- “其他”专业下的 22 个文件需要进一步拆为独立专业域。
- manifest 需要同时记录“结构风险”和“正文上下文风险”。

## 3. KG-03 原架构结论是否仍成立

KG-03 的总体架构结论仍成立：

- AI知识图谱大全应作为 ZDoc 内容输出的知识锚点，而不是直接驱动生成、评分或写回的运行时指令。
- 系统指令类文件不得原样作为 ZDoc system instruction。
- 青天评标 / 满分门控类不得直接参与评分。
- 任何内容不得直接作为 evidence。
- source archive、manifest registry、knowledge pack、prompt pack、system instruction quarantine、rag corpus candidate、template library candidate、human reference only 的分层仍适用。
- KG-04 前必须先建立 manifest、风险分级、冲突组、隔离层和人工审核流程。

需要补正的是统计口径、风险口径、专业域拆分、RAG 候选数量和 KG-04 准入边界。

## 4. 纳入 KG-03 基线的修正项

KG-03 基线应补充以下修正：

1. RAG 候选数量采用 KG-02R 复核后的 61。
2. 风险分级采用 R0-R4，不再使用单一 Medium 表述。
3. 业务侧风险统计采用：R0=0、R1=1、R2=67、R3=62、R4=1。
4. 全量文件口径下 R4=40，包含 `.git`、`.DS_Store`、`.sample`、`.gitignore` 等非知识内容。
5. “其他”专业中的 22 个文件不得长期合并统计，应拆分为独立专业域。
6. manifest 必须区分结构风险与正文上下文风险。
7. RAG 候选默认 `allow_retrieval=false`。
8. 所有 manifest 条目默认 `enabled=false`。
9. 所有系统指令类继续默认 R3 隔离。
10. 青天评标 / 满分门控类继续不得直接参与评分。

## 5. RAG 候选数量校正

KG-02 首次回报中，施工组织设计 / RAG 候选记录为 43。KG-02R 按更完整的文件名与用途维度复核后，确认该数量应校正为 61。

校正原因：

- 仅统计“工程知识图谱”会漏掉接口专项、证据边界、条款证据、模板索引、专业施工、规范验收、安全环保、工艺治理类文件。
- RAG 候选不等于可立即检索。它表示“未来可作为检索语料候选”，仍需 manifest、人工审核和默认禁用。
- 61 个候选中包含 R2 与 R3 文件。R3 文件即使属于 RAG 候选，也不得在 KG-04 启用检索。

基线修正：

- KG-04 如需设计 manifest 实体草案，应记录 `content_class` 可含 `rag_corpus_candidate`。
- 所有此类条目默认 `allow_retrieval=false`。
- 任何 RAG 候选不得直接作为 evidence。

## 6. 风险分级口径切换

KG-02 中“Medium 风险”是粗粒度描述，适合盘点阶段，但不适合 manifest 落地。KG-02R 将其切换为 R0-R4：

- R0：可进入候选池，但仍需审核。
- R1：需轻度清洗。
- R2：需人工复核。
- R3：隔离，不得自动进入生成链。
- R4：禁止整合。

业务侧风险统计：

| 风险等级 | 数量 | 说明 |
| --- | ---: | --- |
| R0 | 0 | 无可直接进入候选池且无清洗要求的文件 |
| R1 | 1 | 低风险候选，但仍需审核 |
| R2 | 67 | 版本、上传版、正文上下文风险，需人工复核 |
| R3 | 62 | 系统指令、评分门控、满分、写回/导出语义，隔离 |
| R4 | 1 | 业务侧 `.gitignore`，禁止整合 |

全量口径：

- R4=40。
- 包含 `.git/**`、`.DS_Store`、`.sample`、`.gitignore` 等非知识内容。

## 7. 专业域拆分修正

KG-02R 发现“其他”专业下有 22 个业务侧文件。该口径只适合临时统计，不适合 KG-04 manifest。

建议拆分为以下独立专业域：

- 装修改造与室外附属同步工程。
- 市政给排水厂站工程。
- 养老院房建。
- 养老院装修改造。
- 其他待确认专业。

拆分规则：

- 以一级目录为优先专业域。
- 不因文件名含“青天”“满分”“系统指令”而覆盖专业域。
- 专业域与内容用途分开记录。
- `professional_domain` 记录专业，`content_class` 记录用途。

## 8. manifest schema 调整

KG-03 中定义的 manifest 字段总体可用，但 KG-02R 要求补充风险细分能力。

建议保持既有字段：

- `file_id`
- `original_path`
- `source_root`
- `normalized_name`
- `file_type`
- `file_size`
- `modified_time`
- `professional_domain`
- `content_class`
- `source_category`
- `version_label`
- `risk_level`
- `risk_reasons`
- `conflict_group_id`
- `duplicate_group_id`
- `recommended_target`
- `enabled`
- `allow_retrieval`
- `allow_generation_reference`
- `allow_system_instruction`
- `human_only`
- `human_review_required`
- `review_status`
- `reviewer`
- `review_notes`
- `created_at`
- `updated_at`

建议在 KG-04 manifest 实体草案中新增或细化以下字段：

- `structural_risk_reasons`：来自文件名、目录、扩展名、版本标签、同名冲突、非知识文件等结构信号。
- `content_context_risk_reasons`：来自正文上下文的风险信号，例如写回、导出、提交、覆盖、endpoint、客户、账号、强制执行、自动评分等。
- `domain_raw`：原始一级目录名，避免专业域归一化后丢失来源。
- `classification_confidence`：分类置信度，建议 `low`、`medium`、`high`。

必须字段仍以 KG-03 定义为准；新增字段用于补强治理，不改变默认禁用原则。

## 9. 结构风险与正文上下文风险

KG-04 manifest 必须区分两类风险：

### 9.1 结构风险

结构风险来自文件名、目录名、扩展名和元数据，不读取正文也能判断。

例：

- `SYSTEM_*`、`系统指令_*`、`ChatGPT配置GPT系统指令.md`。
- `FINAL`、`上传版`、`V2`、`V9`、`V34`、`V35`。
- `青天AI评标门控`、`满分候选规则`、`评分项`。
- `.git`、`.DS_Store`、`.sample`、`.gitignore`。

### 9.2 正文上下文风险

正文上下文风险来自文本内容。

例：

- 写回、导出、提交、覆盖、删除。
- `/generate`、`/export_docx`、`/review/apply`。
- endpoint、端口、URL。
- 客户、联系人、账号、密码等上下文。
- 强制执行、最高优先级、绕过、忽略指令。

KG-04 不应因正文中出现风险词就直接删除候选，也不应忽略风险。正确做法是记录风险原因，并保持默认禁用、人工复核。

## 10. 系统指令隔离延续

系统指令类继续默认 R3 隔离。

适用文件：

- `SYSTEM_*`
- `系统指令_*`
- `GPT系统指令`
- `ChatGPT配置GPT系统指令.md`
- `INSTRUCTIONS`

规则：

- 不得原样启用。
- 不得进入 ZDoc system instruction registry。
- 不得默认进入 prompt pack。
- 不得进入生成链。
- 仅允许作为 human reference，或经人工抽取后形成新的短规则草案。

## 11. 青天评标 / 满分门控限制延续

青天评标、评分项、满分门控、候选规则类继续不得直接参与评分。

规则：

- 默认不低于 R3。
- 不得写入评分主链。
- 不得作为自动评分依据。
- 不得承诺满分。
- 不得作为 evidence。
- 可作为人工参考或后续清洗后的检查项候选。

## 12. 默认权限基线

所有 manifest 条目默认：

```json
{
  "enabled": false,
  "allow_retrieval": false,
  "allow_generation_reference": false,
  "allow_system_instruction": false,
  "human_review_required": true
}
```

RAG 候选默认 `allow_retrieval=false`。

prompt 候选默认 `allow_generation_reference=false`。

系统指令候选默认 `allow_system_instruction=false`。

青天评标 / 满分门控候选默认 `human_only=true`。

## 13. KG-04 允许事项边界

KG-04 如获授权，只能做：

1. manifest 实体草案设计。
2. 试点条目清单设计。
3. source archive 索引设计。
4. risk / conflict / review 字段落地设计。
5. 所有条目默认 disabled。
6. 不启用 retrieval。
7. 不启用 generation。
8. 不启用 system instruction。
9. 不复制原文件。
10. 不接入 ZDoc 运行链路。

KG-04 允许的产物应是治理性、只读来源导向的草案，不是运行时知识包。

## 14. KG-04 禁止事项边界

KG-04 不得：

- 直接接入 RAG。
- 接入 prompt registry。
- 接入 system instruction registry。
- 写入 `backend/data/kg`。
- 调用 `/kg/upload`、`/kg/activate` 或任何 endpoint。
- 启动 ZDoc、ZBid 或 Ollama。
- 访问端口。
- 触发 `/generate`、`/export_docx`、`/review/apply`。
- 触发 ZBid 写回。
- 生成 DOCX。
- 写 output/job/export。
- 复制 AI知识图谱大全原文件进入 ZDoc。
- 启用任何 manifest 条目。
- 将任何内容作为 evidence。

## 15. 首个试点组合最终建议

推荐试点：

```text
全能索引 + 市政桥梁 KG01
```

原因：

- 市政桥梁 KG01 是专业核心知识图谱，范围相对清晰。
- 文件体量适中，适合验证 manifest、专业域、冲突组和风险字段。
- `全能` 仅作为索引、术语、模板候选，不作为 system instruction。

风险点：

- `市政桥梁 KG01` 文件名含 `上传版`，应按 R2 人工复核。
- `全能` 目录含系统指令、评标门控、关键词强化、模板等混合语义，必须分层记录。

KG-04 使用边界：

- 仅允许登记元数据和治理字段。
- 不复制正文。
- 不启用检索。
- 不参与生成。
- 不进入 system instruction。

## 16. 备选试点组合

备选试点：

```text
全能索引 + 医院装修改造 KG02
```

原因：

- 医院装修改造 KG02 偏接口与医疗专项，适合验证专业工艺和接口专项锚点。
- 有助于检验专业域、内容类和风险字段能否表达复杂专业边界。

风险点：

- 医疗专项边界更强，不能把参考资料误作项目事实。
- 必须避免将行业知识直接转写为 evidence。

KG-04 使用边界与推荐试点相同：只登记、只设计、默认禁用。

## 17. 暂不推荐路线

### 17.1 全能单独试点

暂不推荐。

原因：

- `全能` 同时包含索引、术语、模板、系统指令、评标门控、关键词强化。
- 不适合验证单一专业知识包边界。
- 容易误把系统指令或评分门控带入运行链。

### 17.2 全能 + 市政道路 KG01

暂不推荐首轮。

原因：

- 市政道路目录含 `V34.1`、`V35` 等版本标签。
- 版本冲突治理成本高于市政桥梁 KG01。

### 17.3 全能 + 污水处理厂 KG01

暂不推荐首轮。

原因：

- 污水处理厂 KG01 体量最大。
- 专业内容复杂，治理和抽样成本高。
- 更适合 manifest 规则稳定后进入第二批或第三批。

## 18. 是否建议进入 KG-04

建议可以进入 KG-04，但前提是 KG-04 明确限制为 manifest 实体草案与试点清单设计，不得接入任何运行链。

KG-04 的合理目标不是“使用知识图谱”，而是把 KG-02R 与 KG-03R 的治理规则落成可审计、默认禁用、可回滚的 manifest 草案。

如果 ChatGPT 总控无法确认试点组合，应暂缓 KG-04。

## 19. KG-04 授权请求草案

```text
执行 KG-04：ZDoc KG anchor manifest 实体草案与试点条目清单设计

试点组合：
- 推荐：全能索引 + 市政桥梁 KG01
- 备选：全能索引 + 医院装修改造 KG02

允许：
1. 新增 manifest 草案实体文件；
2. 新增试点条目清单；
3. 仅登记 source archive 元数据、风险等级、冲突组、人工审核字段；
4. 所有条目默认 enabled=false；
5. allow_retrieval=false；
6. allow_generation_reference=false；
7. allow_system_instruction=false；
8. human_review_required=true；
9. 区分 structural_risk_reasons 与 content_context_risk_reasons；
10. 不复制 AI知识图谱大全原文件正文。

禁止：
1. 不得接入 RAG；
2. 不得接入 prompt registry；
3. 不得接入 system instruction registry；
4. 不得写入 backend/data/kg；
5. 不得启用任何条目；
6. 不得运行 ZDoc、ZBid、Ollama；
7. 不得访问端口；
8. 不得调用 endpoint；
9. 不得触发 /generate、/export_docx、/review/apply；
10. 不得触发 ZBid 写回；
11. 不得生成 DOCX；
12. 不得写 output/job/export；
13. 不得将任何内容作为 evidence；
14. 不得自动进入真实使用阶段。

验收：
- 只新增授权范围内的 manifest 草案和必要说明；
- git diff --check 通过；
- git status 可解释；
- 回报明确未接入运行链。
```

## 20. 结论

KG-03 架构方向继续成立。KG-03R 将 KG-02R 的修正纳入最新基线：

- RAG 候选为 61。
- 风险分级采用 R0-R4。
- 业务侧风险统计为 R0=0、R1=1、R2=67、R3=62、R4=1。
- 全量 R4=40。
- “其他”专业 22 个需拆分。
- manifest 必须区分结构风险与正文上下文风险。
- KG-04 只能做 manifest 草案与试点清单设计，不能接入系统。

完成 KG-03R 后应停止，等待 ChatGPT 总控是否授权 KG-04。
