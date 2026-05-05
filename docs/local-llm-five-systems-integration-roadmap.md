# Local LLM Five Systems Integration Roadmap

## 1. 阶段定位

本文件是用户桌面 5 个 Codex 建设系统接入本地化大模型的总路线 docs-only 规划。

当前阶段只做总控设计，不访问其他桌面系统目录，不修改任何系统代码，不启动服务，不运行 Ollama，不接生产链。本文用于统一后续只读盘点、docs-only 设计、mock-only 接入、测试、guard 和阶段标签的推进顺序。

本路线图不代表任何系统已经完成生产接入，也不代表允许直接把本地模型接入正式成果链。

## 2. 当前 ZDoc 稳定基线

当前文档生成系统 ZDoc 稳定基线:

- 当前 `main` 最新 commit: `5b833d0 docs: add ZBid snapshot mock API bridge smoke checks review`
- 当前稳定标签: `v0.1.46-zbid-snapshot-mock-api-bridge-smoke-checks-review`
- 当前工作区状态: clean

ZDoc 当前已达到:

- ZBid snapshot mock API bridge 已实现。
- in-process HTTP smoke checks 已补强。
- guard task spec 已建立。
- 阶段复盘文档已归档。

ZDoc 当前仍未接入:

- 前端
- 正式生成链
- 导出链
- job/result bundle
- build/output
- 正式 apply / 正式写回链

## 3. 用户本地 5 个系统资产清单

用户桌面 5 个 Codex 建设系统:

| 系统 | 状态 | 当前定位 |
| --- | --- | --- |
| 智飞ERP20260202 | 已建成并试运行阶段 | 企业业务系统，后续适合在稳定数据边界内接入本地模型辅助 |
| 即时通讯 | 已建成，还在完善中 | 通讯协同系统，后续适合先做只读摘要、分类、辅助回复建议 |
| OpenClaw | 股票自动交易系统，正在建设中 | 最高风险系统，只允许先做只读分析和模拟输出 |
| ZhiFei_BizSystem | 评标系统，还在检验优化中 | 第一个接入本地化部署的系统 |
| 文档生成系统 | 当前正在运行的系统 | 已完成 ZBid mock API bridge 与 smoke checks 阶段 |

统一背景:

- 以上 5 个系统文件均在用户电脑桌面。
- 以上 5 个系统均通过 Codex 建设。
- 以上 5 个系统均有 GitHub 仓库。
- GitHub 仓库用户名: `niyoufei@gmail.com`。
- 最终目标: 全部接入本地化部署，实现最先进、最新的大模型能力。
- ChatGPT 订阅账号需要纳入协同体系，但不能被混同为本地模型运行时。

截图中可识别的系统入口包括:

- 智飞ERP20260202
- OpenClaw
- Matrix（即时通讯）
- 文档生成系统
- 智飞青天 / ZhiFei_BizSystem（评标系统）

这些系统不是空白系统，也不是未来才创建的系统。它们已经有对应本地文件、Codex 项目上下文和 GitHub 仓库。当前文档生成系统只作为本轮推进窗口，不能直接替其它系统改代码。

后续若接入其它系统，必须按“对应系统目录单独推进”的原则执行:

- 智飞ERP20260202: 进入 `/Users/youfeini/Desktop/智飞ERP20260202` 只读盘点。
- OpenClaw: 进入 `/Users/youfeini/Desktop/OpenClaw` 只读盘点。
- Matrix / 即时通讯: 进入对应桌面目录只读盘点。
- ZhiFei_BizSystem / 智飞青天评标系统: 进入对应桌面目录只读盘点。
- 文档生成系统: 继续在 `/Users/youfeini/Desktop/文档生成系统` 推进。

本路线图阶段不得访问其它桌面系统目录，也不得在当前文档生成系统仓库中直接修改其它系统代码。

## 4. 总体目标

总体目标是为 5 个系统建立统一、可审计、可回滚、default-off 的本地化大模型接入路线。

核心目标:

- 用本地 Ollama、本地推理服务或后续统一模型网关作为本地化大模型运行主体。
- 用 Codex 执行链完成只读盘点、设计、实现、测试、guard、复盘和标签归档。
- 用 ChatGPT 订阅账号作为总控、审查、规划和交互协同入口。
- 所有系统先完成 mock-only / draft-only / no-write 接入，再评估是否进入更高风险阶段。
- 所有生产链路必须 default-off，并具备人工确认、回滚和可审计证据。

当前不直接接任何新系统代码。当前不直接启动任何系统服务。当前不直接把本地模型接入生产链。

## 5. 本地化大模型架构原则

本地化大模型运行主体应是本机或局域网部署模型，例如:

- Ollama
- 本地推理服务
- 后续统一模型网关

架构原则:

- 本地模型运行时与业务系统解耦。
- 业务系统通过 default-off API bridge 或 helper 调用模型能力。
- 所有写入链路必须独立于 preview / mock-only 链路。
- 所有生产链路必须有人工确认和回滚机制。
- 所有系统先做只读输出，再做草稿输出，最后才评估正式写回。
- 不同系统不得直接复用未经审计的模型调用链。

## 6. ChatGPT 订阅账号协同边界

ChatGPT 订阅账号属于云端账号，不能被迁移成本地模型本体，也不能被描述为本地私有化部署。

可行协同方式:

- ChatGPT 订阅账号作为总控入口。
- ChatGPT 订阅账号用于审查、规划、复盘和交互协同。
- ChatGPT 与 Codex 执行链协同，推动本地 5 个系统逐步接入。
- ChatGPT 可辅助评估设计文档、测试结果、风险边界和阶段标签。

明确边界:

- ChatGPT 订阅账号不是本地模型运行时。
- ChatGPT 订阅账号不能替代本机 / 局域网模型服务。
- ChatGPT 订阅账号不能直接进入业务系统生产写回链。
- ChatGPT 订阅账号不能直接控制资金、交易、导出、生成或正式 apply。

## 7. 五系统接入优先级

建议接入优先级:

1. ZhiFei_BizSystem 评标系统
2. 文档生成系统 ZDoc
3. 智飞ERP20260202
4. 即时通讯
5. OpenClaw 股票自动交易系统

排序依据:

- 优先选择业务价值高、已有 LLM 相关预览基础、风险可控的系统。
- 文档生成系统已完成 mock API bridge 和 smoke checks，可作为方法论沉淀来源。
- ERP 和即时通讯需先完成现状盘点，避免误触业务数据和协同消息。
- OpenClaw 涉及股票自动交易和资金风险，必须排在最后，并采用最高风险等级。

## 8. 第一优先级：ZhiFei_BizSystem 评标系统

ZhiFei_BizSystem 当前状态:

- 评标系统。
- 仍在检验优化中。
- 定位为第一个接入本地化部署的系统。
- 截图入口可识别为智飞青天 / ZhiFei_BizSystem（评标系统）。

优先原因:

- 评标业务天然适合模型辅助分析、摘要、对比和草稿建议。
- 可先限制在只读评审辅助、报告预览、材料摘要等低风险场景。
- 与正式业务写回可以保持清晰隔离。

第一阶段只允许:

- 只读现状盘点。
- docs-only 接入边界复盘。
- 现有 LLM / Ollama / preview 相关链路盘点。
- 数据输入、输出、写回、导出和人工确认边界梳理。

后续应优先进入对应桌面目录做独立只读盘点，但不能在当前文档生成系统仓库中直接修改 ZhiFei_BizSystem 代码。

不得直接:

- 修改生产链路。
- 默认开启本地模型。
- 接正式评标成果按钮。
- 写数据库、报告、导出文件或正式结果。

## 9. 第二优先级：文档生成系统 ZDoc

文档生成系统当前状态:

- 当前正在运行。
- 已完成 ZBid snapshot mock API bridge。
- 已完成 in-process HTTP smoke checks。
- 已完成 guard spec 与阶段复盘。

当前稳定结论:

- endpoint: `POST /actions/zbid/snapshot_draft_input/preview`
- feature flag: `ZDOC_ZBID_MOCK_API_ENABLED=1`
- 仅 mock-only / draft-only / no-write。
- 仍未接前端、正式生成链、导出链、job/result bundle 或正式 apply。

ZDoc 后续只允许先做:

- docs-only 生产切换前置设计。
- local LLM 接入边界设计。
- mock-only helper 扩展设计。
- default-off API bridge 设计。
- smoke checks 与 guard 复用策略设计。

不得直接接正式成果链。

## 10. 第三优先级：智飞ERP20260202

智飞ERP20260202 当前状态:

- 已建成并试运行阶段。

适合接入方向:

- 只读经营数据摘要。
- 流程异常提醒建议。
- 表单字段草稿建议。
- 业务规则解释。
- 管理报表草稿辅助。

前置要求:

- 只读盘点数据模型、权限模型、写入链路和导出链路。
- docs-only 接入设计。
- 严格区分建议输出和正式业务写入。
- 所有写入动作必须人工确认。

不得直接:

- 修改业务数据。
- 自动审批。
- 自动流转。
- 自动导出正式报表。

## 11. 第四优先级：即时通讯

即时通讯当前状态:

- 已建成，还在完善中。
- 截图入口可识别为 Matrix（即时通讯）。

适合接入方向:

- 只读消息摘要。
- 会话分类。
- 待办提取。
- 辅助回复草稿。
- 知识检索建议。

前置要求:

- 只读盘点消息存储、权限、发送链路和通知链路。
- docs-only 设计隐私边界和敏感信息处理策略。
- mock-only 回复草稿 helper。
- default-off API bridge。
- deterministic tests 和 smoke checks。

不得直接:

- 自动发送消息。
- 自动删除消息。
- 自动转发敏感内容。
- 绕过用户确认进行群发或外发。

## 12. 第五优先级：OpenClaw 股票自动交易系统

OpenClaw 当前状态:

- 股票自动交易系统。
- 正在建设中。

OpenClaw 必须采用最高风险等级。

明确禁止:

- 不允许模型直接下单。
- 不允许模型直接控制资金。
- 不允许模型绕过人工确认。
- 不允许模型直接连接生产交易执行链。
- 不允许接入实盘交易链。
- 不允许模型自动改变交易策略并立即执行。

第一阶段只允许:

- 只读市场数据分析。
- 只读策略解释。
- 模拟输出。
- 回测报告草稿。
- 风险提示草稿。
- 风控解释。
- 人工确认流程设计。

任何自动交易相关能力都必须先经过单独的风控设计、模拟验证、人工确认、资金隔离、审计日志和回滚策略评审。

## 13. 统一模型网关设想

后续可设计统一模型网关，但当前不实现。

统一模型网关职责设想:

- 管理本地模型列表。
- 管理模型版本。
- 管理系统级 feature flag。
- 提供统一 prompt / request / response 审计。
- 提供调用限流和权限控制。
- 提供 no-write / draft-only / mock-only 模式标记。
- 提供统一错误处理和模型降级策略。

统一模型网关不应承担:

- 直接业务写回。
- 直接导出成果。
- 直接创建 job/result bundle。
- 直接控制资金或交易。

## 14. 数据安全与权限边界

数据安全原则:

- 默认只读。
- 默认本地处理。
- 默认不写盘。
- 默认不外发。
- 默认不进入生产链。
- 敏感数据必须有最小必要输入。

权限边界:

- 本地模型只能接收被明确允许的数据。
- Codex 执行链只能在任务授权范围内修改文件。
- ChatGPT 订阅账号只作为云端协同和审查入口。
- 生产写回必须由业务系统自身的权限和人工确认控制。

## 15. mock-only / draft-only / no-write 统一原则

所有系统必须先遵循统一三原则:

- `mock-only`: 只做模拟或预览，不代表正式业务动作。
- `draft-only`: 只生成草稿，不写正式成果。
- `no-write`: 不写业务数据、不写成果文件、不写 job/result bundle。

所有 API bridge 默认关闭:

- feature flag 未开启时必须拒绝请求。
- disabled 场景不得调用模型或 mapper。
- enabled 场景也只允许最小 helper 调用。
- response 必须显式标记模式和安全边界。

## 16. 各系统接入前置盘点清单

每个系统必须先完成:

- 当前仓库状态确认。
- GitHub 远端确认。
- 现有功能清单。
- 已接入 AI / Ollama / 本地模型能力盘点。
- 高风险链路识别。
- 只读盘点。
- docs-only 接入设计。
- mock-only helper。
- default-off API bridge。
- deterministic tests。
- guard task spec。
- smoke checks。
- 阶段复盘。
- 稳定标签。

只读盘点至少包括:

- 当前仓库状态。
- GitHub 远端。
- 现有功能清单。
- 当前服务启动方式。
- 当前模型 / LLM / Ollama 相关代码。
- 当前已接入 AI / Ollama / 本地模型能力。
- 当前高风险链路。
- 当前写入链路。
- 当前导出链路。
- 当前 job / task / result bundle 链路。
- 当前权限和人工确认链路。
- 当前测试和 guard 能力。

对应系统目录单独推进原则:

- 不得在文档生成系统仓库中替其它系统改代码。
- 不得跨系统复用未经盘点的实现链路。
- 不得把当前 ZDoc 的 mock API bridge 直接复制到其它系统生产链。
- 每个系统必须在自己的本地目录中完成独立只读盘点、独立 docs-only 接入设计、独立测试和独立标签归档。

## 17. 新模型升级验证路线

新模型升级必须先走 sandbox / mock-only 验证。

建议顺序:

1. 记录当前稳定 commit 和标签。
2. 只读盘点当前模型调用链。
3. 新模型在 sandbox 环境加载。
4. 使用固定输入跑 deterministic 输出对比。
5. 记录 hash / diff。
6. 记录性能数据。
7. 验证 no-write 边界。
8. 生成复盘文档。
9. 创建稳定标签。

任何新模型不得直接进入生产链。性能变好不等于可以绕过安全验证。

## 18. 质量稳定性保障机制

质量稳定性保障应包括:

- deterministic tests。
- in-process smoke checks。
- artifact counts 前后对比。
- forbidden key 检查。
- no-write patch。
- guard scope / verify。
- docs-only 复盘。
- 稳定标签归档。
- 人工审查。

每个阶段必须能回答:

- 改了哪些文件。
- 为什么改。
- 测试覆盖什么。
- 是否写盘。
- 是否启动服务。
- 是否触发模型。
- 是否进入生产链。
- 如何回滚。

## 19. 风险清单与控制措施

风险: ChatGPT 订阅账号被误认为本地模型运行时。

- 控制: 明确 ChatGPT 是云端协同入口，不能被迁移成本地模型本体。

风险: 本地模型被直接接入生产链。

- 控制: 所有系统必须先 mock-only / draft-only / no-write，并 default-off。

风险: 多系统接入导致边界混乱。

- 控制: 每个系统单独盘点、单独设计、单独 guard、单独标签归档。

风险: ZhiFei_BizSystem 评标结果被模型直接改写。

- 控制: 第一阶段只读盘点和接入边界复盘，不接正式成果按钮。

风险: ZDoc mock bridge 被误接到正式生成链。

- 控制: 继续保持未接前端、未接生成链、未接导出链、未接 job/result bundle、未接正式 apply。

风险: ERP 业务数据被模型自动修改。

- 控制: 只读摘要和草稿建议优先，写入必须人工确认。

风险: 即时通讯消息被模型自动发送。

- 控制: 只允许辅助回复草稿，不允许自动发送、删除、转发。

风险: OpenClaw 模型直接下单或控制资金。

- 控制: OpenClaw 最高风险等级，第一阶段只允许只读分析和模拟输出。

## 20. 分阶段实施路线

建议阶段:

### Phase 0: 总路线归档

- 新增本路线图。
- 不接任何系统代码。
- 不启动服务。
- 不运行模型。

### Phase 1: ZhiFei_BizSystem 只读盘点

- 只读检查仓库状态、模型相关链路、写入链路和测试能力。
- 输出 docs-only 接入边界复盘。
- 不修改代码。
- 进入对应桌面目录独立执行，不在当前文档生成系统仓库中修改 ZhiFei_BizSystem 代码。

### Phase 2: ZhiFei_BizSystem mock-only 设计

- 设计 helper、default-off API bridge、tests、guard spec。
- 不接正式评标成果链。

### Phase 3: ZDoc 生产切换前置设计

- 复用 v0.1.46 已沉淀的 mock API bridge / smoke checks 经验。
- 只做 docs-only 设计。
- 不接正式生成链。

### Phase 4: ERP 和即时通讯只读盘点

- 分别只读盘点。
- 分别输出 docs-only 接入设计。
- 不共享未经审查的实现链路。
- 智飞ERP20260202 进入 `/Users/youfeini/Desktop/智飞ERP20260202` 只读盘点。
- Matrix / 即时通讯进入对应桌面目录只读盘点。

### Phase 5: OpenClaw 高风险只读盘点

- 只读盘点交易链路和资金边界。
- 只允许模拟输出设计。
- 不允许模型下单。
- 进入 `/Users/youfeini/Desktop/OpenClaw` 只读盘点。
- 不接入实盘交易链。

### Phase 6: 统一模型网关设计

- 在多个系统前置盘点完成后再设计。
- 先 docs-only。
- 不直接替换各系统模型调用链。

## 21. Codex 后续执行约束

后续 Codex 执行相关任务时:

- 一次只处理一个系统。
- 先只读盘点，再 docs-only 设计。
- 未经明确授权，不访问其他桌面系统目录。
- 未经明确授权，不修改业务代码、API、前端、测试、guard 或 task spec。
- 未经明确授权，不启动服务。
- 未经明确授权，不运行 Ollama。
- 未经明确授权，不运行 pytest。
- 未经明确授权，不触发生成链、导出链、job/build/output/result bundle。
- 未经明确授权，不执行正式 apply。
- 未经明确授权，不 git add、commit、tag 或 push。
- OpenClaw 相关任务默认最高风险等级，只允许只读盘点和模拟输出设计。

## 22. 结论

五系统本地化大模型接入应按“只读盘点 -> docs-only 设计 -> mock-only helper -> default-off API bridge -> deterministic tests -> guard task spec -> smoke checks -> 阶段复盘 -> 稳定标签”的顺序推进。

当前路线结论:

- ZhiFei_BizSystem 是第一个本地化部署接入系统，应优先完成现状盘点和接入边界复盘。
- 文档生成系统 ZDoc 已达到 ZBid snapshot mock API bridge + smoke checks 阶段，但仍未接前端、正式生成链、导出链、job/result bundle 或正式 apply。
- 智飞ERP20260202 和即时通讯应在 ZhiFei_BizSystem 与 ZDoc 边界稳定后进入只读盘点。
- OpenClaw 属于股票自动交易系统，必须采用最高风险等级，只允许先做只读分析和模拟输出。
- ChatGPT 订阅账号属于云端账号，只能作为总控、审查、规划和交互协同入口，不能被描述为本地私有化模型本体。
- 本地化大模型运行主体仍应是本机 / 局域网部署模型，例如 Ollama、本地推理服务或后续统一模型网关。

本路线图只作为总控规划，不代表任何系统已经完成生产接入。
