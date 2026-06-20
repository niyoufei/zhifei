# LOCAL-LAUNCHER-025 Runtime Independent Boundary And Risk Authorization Gate

## 1. LOCAL-LAUNCHER-025 节点结论

`LOCAL-LAUNCHER-025-RETRY-1-RUNTIME-INDEPENDENT-BOUNDARY-AND-RISK-AUTHORIZATION-GATE` 是 LOCAL-LAUNCHER 真实 runtime 路线的独立前置 Gate。

本节点结论如下：

1. 本节点是 runtime 路线独立前置 Gate。
2. 本节点不是 runtime ready。
3. 本节点不是 release ready。
4. 本节点不是 trial ready。
5. 本节点不是真实使用 ready。
6. 本节点不是 50 人正式使用 ready。
7. 本节点不授权服务启动。
8. 本节点不授权 Web UI 启动。
9. 本节点不授权 endpoint。
10. 本节点不授权 Ollama。
11. 本节点不授权模型推理。
12. 本节点不授权真实 KG / 真实项目资料接入。
13. 本节点不授权 generation/export/write-back。

本节点仅形成 runtime 前置边界、风险分级和后续 Gate 拆分建议，供 ChatGPT 总控师审核。

## 2. 与 024 静态 UI 封版成果的关系

1. `LOCAL-LAUNCHER-024` 是 LOCAL-LAUNCHER V1 静态 UI 最终闭环。
2. 024 静态 UI 路线已关闭。
3. 025 不继承静态 UI 路线运行授权。
4. 025 不改变 024 的最终封版结论。
5. 025 仅用于建立 runtime 路线边界。
6. 025 完成后不得自动进入 runtime 执行。

024 的最终结论仍保持不变：当前成果仅为本地静态 UI 骨架与专业化静态 UI 封版资料，不得解释为 runtime ready、release ready、trial ready、真实使用 ready 或 50 人正式使用 ready。

## 3. runtime 路线总边界

| 边界类型 | 当前是否允许 | 后续允许前置条件 | 禁止行为 | 阻断条件 | 必须回报 ChatGPT 总控师的触发点 |
| --- | --- | --- | --- | --- | --- |
| 服务边界 | 不允许 | 独立服务启动前安全预检 Gate 通过，并获得服务启动明确授权 | 启动、停止、重启、探测服务 | 未授权服务命令、服务状态不明、出现残留进程或 PID 风险 | 发现服务已运行、需要启动服务、需要处理服务状态 |
| Web UI 启动边界 | 不允许 | Web UI 启动 Gate 明确授权启动方式、窗口、端口、停止条件 | 启动 Web UI、打开页面、预览 HTML | 需要执行启动脚本或打开 UI | 任何 Web UI 启动、预览、访问需求 |
| endpoint 边界 | 不允许 | endpoint 健康检查 Gate 明确授权 endpoint 清单和只读检查方法 | 访问 endpoint、curl、HTTP request、localhost 探测、端口探测 | 需要访问 `127.0.0.1:8010`、`127.0.0.1:8501` 或其他 endpoint | 任何 endpoint、HTTP、localhost、端口访问需求 |
| Ollama 边界 | 不允许 | Ollama inventory Gate 明确授权只读命令、目标字段和回报格式 | 执行 Ollama 命令、运行模型、拉取模型 | 需要读取 Ollama inventory 或触发 Ollama 进程 | 任何 Ollama 命令需求 |
| 模型推理边界 | 不允许 | 模型推理最小验证 Gate 明确模型、输入、输出、停止条件和无真实资料约束 | 模型推理、生成、试跑、真实 prompt 验证 | 需要向模型提交输入或读取模型输出 | 任何模型推理需求 |
| prompt 输入边界 | 不允许 | prompt Gate 明确 prompt 来源、内容、脱敏要求、模型和输出处置 | 向任何模型输入 prompt | prompt 涉及真实资料、未脱敏信息或未授权模型 | 任何 prompt 输入需求 |
| KG 读取边界 | 不允许 | KG 读取 Gate 明确 KG 范围、只读字段、脱敏策略和禁止写回 | 读取真实 KG、修改 KG、写回 KG | 需要打开真实 KG、抽取 KG、查询 KG | 任何 KG 读取或接入需求 |
| 真实项目资料边界 | 不允许 | 真实资料接入 Gate 明确资料类型、脱敏规则、读取路径和最小样本范围 | 读取招标文件、图纸、清单、项目样本、真实项目资料 | 需要接触真实项目内容或无法确认资料已脱敏 | 任何真实资料读取需求 |
| generation/export/write-back 边界 | 不允许 | generation/export/write-back Gate 明确输入、输出目录、写入对象、回滚方案和审计方式 | generation、export、write-back、覆盖产物、写入项目资料 | 需要生成、导出、写回或覆盖任何结果 | 任何生成、导出、写回需求 |
| 日志读取边界 | 不允许 | 日志读取 Gate 明确日志路径、允许字段、脱敏规则和禁止正文范围 | 读取日志正文、output/job/export、生成结果 | 需要查看日志正文、结果文件或运行输出 | 任何日志、output、job、export 读取需求 |
| secrets/tokens/credentials 边界 | 不允许 | secrets 审查 Gate 明确不读取敏感值，仅确认配置存在性或占位状态 | 读取 secrets、tokens、credentials、环境变量敏感信息 | 需要查看敏感值或环境变量内容 | 任何密钥、令牌、凭据、敏感环境变量需求 |
| 运行配置边界 | 不允许 | runtime 配置清点 Gate 明确只读配置文件清单和禁止字段 | 读取未授权 runtime 配置、修改配置、执行配置加载 | 配置包含敏感字段或会触发 runtime 行为 | 任何 runtime 配置清点需求 |
| mock 数据边界 | 不允许 runtime 使用 | mock 数据闭环 Gate 明确 mock 数据来源、范围、禁止真实资料混入 | 用 mock 驱动真实 runtime、混入真实资料 | mock 与真实资料边界不清或会触发生成 | 任何 mock runtime 闭环需求 |
| 脱敏样本边界 | 不允许 | 脱敏样本验证 Gate 明确脱敏证明、样本范围、读取方式和删除/保留规则 | 使用未审查样本、扩大样本范围、混入真实敏感信息 | 无法证明样本脱敏或样本来源不明 | 任何脱敏样本读取或验证需求 |
| trial / 多人试用边界 | 不允许 | trial Gate 和 50 人正式使用 Gate 分别独立通过，并明确用户范围、责任、回滚、支持和审计要求 | trial、真实使用、多人试用、50 人正式使用 | 功能未完成 runtime 分级 Gate 或责任边界不清 | 任何试用、真实使用、多人使用需求 |

统一边界结论：

1. 当前仍不允许启动 Web UI。
2. 当前仍不允许执行 `./scripts/run_web_ui.sh --background`。
3. 当前仍不允许访问 `127.0.0.1:8010`。
4. 当前仍不允许访问 `127.0.0.1:8501`。
5. 当前仍不允许将 024 静态 UI 封版视为 runtime 授权。

## 4. 风险分级

| 等级 | 风险定义 | 当前是否授权 | 进入该等级前必须满足的 Gate | 禁止越级行为 | 阻断条件 | 回滚或停止要求 |
| --- | --- | --- | --- | --- | --- | --- |
| R0 | 静态只读资料审查，仅阅读明确授权 docs | 已授权本节点范围内的 024 closure docs | docs-only 审查授权 | 借静态审查读取 runtime、真实资料或敏感信息 | 发现资料超出授权清单 | 停止并回报 |
| R1 | 静态文件与说明微调 | 未授权 | 静态 UI 微调 Gate | 修改 `local-launcher-v1` 静态文件或既有 docs | 需要触碰静态 UI 文件 | 停止并等待授权 |
| R2 | runtime 配置只读审查 | 未授权 | runtime 配置清点 Gate | 读取未授权 runtime 配置、敏感配置、脚本正文 | 配置清单不明确或含敏感字段 | 停止并回报配置边界 |
| R3 | 服务启动前预检 | 未授权 | 服务启动前安全预检 Gate | 探测端口、读取 PID、检查 runtime 状态 | 需要服务、端口、PID 或 localhost 状态 | 停止并回报预检需求 |
| R4 | 受控服务启动 | 未授权 | 受控服务启动 Gate | 启动、停止、重启服务或执行启动脚本 | 未定义启动命令、端口、退出和回滚条件 | 停止，不启动服务 |
| R5 | endpoint 只读健康检查 | 未授权 | endpoint 健康检查 Gate | curl、HTTP request、localhost、端口探测 | endpoint 清单、方法或超时未授权 | 停止，不访问 endpoint |
| R6 | Ollama 只读 inventory | 未授权 | Ollama inventory Gate | 执行 Ollama 命令或启动模型 | Ollama 命令、字段、模型范围未授权 | 停止，不运行 Ollama |
| R7 | 模型推理最小空载验证 | 未授权 | 模型推理最小验证 Gate | 输入 prompt、触发推理、读取生成输出 | prompt、模型、输出处置不明确 | 停止，不推理 |
| R8 | mock 数据闭环验证 | 未授权 | mock 数据闭环 Gate | 将 mock 当作真实使用、触发 export/write-back | mock 来源或闭环步骤不清 | 停止，不执行闭环 |
| R9 | 脱敏样本验证 | 未授权 | 脱敏样本验证 Gate | 使用未证明脱敏的样本或扩大样本范围 | 脱敏证明不足或样本来源不明 | 停止并回报样本风险 |
| R10 | 真实 KG / 真实项目资料验证 | 未授权 | 真实资料接入 Gate | 读取真实 KG、招标文件、图纸、清单、项目样本 | 真实资料边界、权限、脱敏、审计不明确 | 停止，不接触真实资料 |
| R11 | generation/export/write-back | 未授权 | generation/export/write-back Gate | 生成、导出、写回、覆盖结果 | 输出路径、写回对象、回滚方案不明确 | 停止，不写入任何结果 |
| R12 | trial / 多人试用 / 正式使用 | 未授权 | trial Gate；50 人正式使用 Gate | trial、真实使用、多人试用、正式使用 | runtime 能力、责任边界、支持和回滚未闭环 | 停止，不进入使用阶段 |

风险分级统一结论：

1. 当前 025 仅处于 R0 docs-only 边界审查范围。
2. R1 至 R12 均未授权。
3. 任一等级完成后均不得自动进入下一等级。
4. 任一越级需求均必须停止并回报 ChatGPT 总控师。

## 5. 后续 Gate 拆分建议

| Gate 名称 | Gate 性质 | 允许范围 | 禁止范围 | 完成后是否允许自动进入下一阶段 |
| --- | --- | --- | --- | --- |
| runtime 配置清点 Gate | R2 只读配置边界审查 | 仅按授权清单读取 runtime 配置结构和非敏感字段 | 读取脚本正文、secrets、tokens、credentials、启动服务 | 否 |
| 服务启动前安全预检 Gate | R3 启动前条件审查 | 仅审查启动前 checklist、端口规划、回滚条件和停止条件 | 启动服务、端口探测、PID 操作、localhost 访问 | 否 |
| 受控服务启动 Gate | R4 服务启动授权 | 在明确命令、端口、日志、停止和回滚条件后受控启动 | 未授权脚本、后台常驻、真实资料接入、endpoint 扩展访问 | 否 |
| endpoint 健康检查 Gate | R5 只读健康检查 | 仅访问授权 endpoint，按授权方法记录健康结果 | curl 未授权地址、HTTP 扩展请求、业务调用、写操作 | 否 |
| Ollama inventory Gate | R6 模型环境只读清点 | 仅执行授权的 Ollama inventory 命令并记录模型清单 | 模型推理、pull、run、prompt、真实资料输入 | 否 |
| 模型推理最小验证 Gate | R7 空载推理验证 | 仅使用明确授权的无真实资料 prompt 与模型 | 真实 prompt、真实 KG、真实项目资料、生成业务结果 | 否 |
| mock 数据闭环 Gate | R8 mock 闭环验证 | 仅使用 mock 数据完成受控闭环验证 | 真实资料、脱敏样本、export/write-back、trial | 否 |
| 脱敏样本验证 Gate | R9 脱敏样本验证 | 仅读取已授权、已证明脱敏的最小样本 | 未脱敏资料、扩大样本、写回、真实使用 | 否 |
| 真实资料接入 Gate | R10 真实 KG / 真实项目资料验证 | 仅在明确权限、范围、审计、脱敏和停止条件后验证 | 未授权招标文件、图纸、清单、项目样本、敏感信息 | 否 |
| generation/export/write-back Gate | R11 输出写入能力验证 | 仅在明确输出目录、写回对象和回滚方案后执行 | 覆盖真实资料、无审计写入、无回滚写入、扩大输出 | 否 |
| trial Gate | R12 试用授权 | 仅在功能、数据、支持、责任和回滚闭环后小范围试用 | 真实使用泛化、多人扩展、50 人正式使用 | 否 |
| 50 人正式使用 Gate | R12 正式使用授权 | 仅在 trial 审核通过后评估 50 人使用准备度 | 未经 trial 直接正式使用、无支持与回滚机制 | 否 |

统一结论：任何 Gate 完成后均不得自动进入下一阶段，必须回报 ChatGPT 总控师审核。

## 6. 当前仍然禁止事项

当前仍严格禁止：

1. 服务启动。
2. Web UI 启动。
3. 执行 `./scripts/run_web_ui.sh --background`。
4. endpoint。
5. Ollama。
6. 模型推理。
7. prompt。
8. 真实 KG。
9. 真实项目资料。
10. 招标文件。
11. 图纸。
12. 清单。
13. 项目样本。
14. secrets。
15. tokens。
16. credentials。
17. output。
18. job。
19. export。
20. 日志正文。
21. generation。
22. export。
23. write-back。
24. trial。
25. 真实使用。
26. 50 人正式使用。

补充确认：

1. 当前仍禁止执行 `scripts/run_web_ui.sh`。
2. 当前仍禁止执行 `scripts/start_web_ui_background.sh`。
3. 当前仍禁止执行 `scripts/create_desktop_launcher.sh`。
4. 当前仍禁止打开、预览或运行任何 HTML 页面。
5. 当前仍禁止访问 `127.0.0.1:8010` 或 `127.0.0.1:8501`。
6. 当前仍禁止 curl、HTTP request、localhost 探测、端口探测。
7. 当前仍禁止读取、清理、删除 `.runtime/docgen/` PID 文件。
8. 当前仍禁止读取 output/job/export/生成结果/日志正文。
9. 当前仍禁止修改 `local-launcher-v1` 任何静态文件。
10. 当前仍禁止修改 014 至 024 既有 docs。
11. 当前仍禁止创建 runtime 代码、server 代码、endpoint 代码、API 代码、模型接入代码或 KG 接入代码。

## 7. 是否允许进入下一阶段的建议

1. 本节点完成后，不得自动进入 runtime 执行。
2. 本节点完成后，不得自动进入 026。
3. 本节点只能向 ChatGPT 总控师回报。
4. 是否进入下一阶段由 ChatGPT 总控师审核后另行授权。
5. 如发现任何越界风险，必须建议停止，而不是建议继续执行。

本节点建议结论：

`LOCAL-LAUNCHER-025-RETRY-1 COMPLETED / RUNTIME BOUNDARY ONLY / NO RUNTIME EXECUTION AUTHORIZED / STOPPED`
