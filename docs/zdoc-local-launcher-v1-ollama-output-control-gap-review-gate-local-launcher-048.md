# LOCAL-LAUNCHER-048 ZDoc Local App V1 Ollama Output Control Gap Review Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-048-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-GAP-REVIEW-GATE`

本节点性质：

`Ollama output control gap review only`

本节点目标：

在 047 输出控制 smoke test 判定为 `CONTROL_GAP` 后，对输出控制差距进行只读复核，记录差距事实、性质判断、风险影响、后续可选路线和下一授权门建议。

本节点明确：

1. 不执行任何 Ollama 命令。
2. 不运行模型。
3. 不输入 prompt。
4. 不修改 prompt 后重试。
5. 不访问 endpoint。
6. 不触发 ZDoc generation/export/write-back。
7. 不读取真实 KG、真实项目资料或真实招标文件。
8. 不进入 `LOCAL-LAUNCHER-049`。

## 2. 当前基线 HEAD/tag

- 开始前 HEAD：`cdec9d6b23fb04d1ba7affa084d84c58e757bdc0`
- 开始前 tag：`v0.1.683-local-launcher-zdoc-local-app-v1-ollama-output-control-smoke-test-execution-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-047-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-EXECUTION-GATE`

实际最近提交：

```text
cdec9d6 (HEAD -> main, tag: v0.1.683-local-launcher-zdoc-local-app-v1-ollama-output-control-smoke-test-execution-gate, origin/main, origin/HEAD) LOCAL-LAUNCHER-047 ollama output control smoke test execution
```

开始前 `git status --short` 无输出。

## 3. 上游节点通过状态

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md`
2. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md`
3. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md`
4. `docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-authorization-gate-local-launcher-046.md`
5. `docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-execution-gate-local-launcher-047.md`

复核结果：

1. 043 smoke test 判定：`PASS`。
2. 044 smoke test result closed。
3. 045 next-stage strategy completed。
4. 046 output control authorization completed。
5. 047 output control 判定：`CONTROL_GAP`。

043 当前 decision：

```text
LOCAL-LAUNCHER-043 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST EXECUTION GATE PASSED / MINIMAL MODEL RUN SMOKE TEST COMPLETED WITH QWEN3 0.6B / NON-SENSITIVE RESPONSE SUMMARY RECORDED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

044 当前 decision：

```text
LOCAL-LAUNCHER-044 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST RESULT RECORD GATE COMPLETED / MODEL RUN SMOKE TEST PASS RECORDED / MINIMAL QWEN3 0.6B RESPONSE RESULT CLOSED / NO ADDITIONAL OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

045 当前 decision：

```text
LOCAL-LAUNCHER-045 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST NEXT STAGE STRATEGY GATE COMPLETED / NEXT STAGE STRATEGY DOCUMENTED AFTER MODEL RUN SMOKE TEST PASS / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

046 当前 decision：

```text
LOCAL-LAUNCHER-046 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL SMOKE TEST AUTHORIZATION GATE COMPLETED / OUTPUT CONTROL SMOKE TEST EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

047 当前 decision：

```text
LOCAL-LAUNCHER-047 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL SMOKE TEST EXECUTION GATE COMPLETED WITH OUTPUT CONTROL GAP / MODEL RESPONDED BUT STRICT ONE-LINE OK FORMAT NOT FULLY CONFIRMED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

## 4. 047 输出控制差距事实复核

047 已记录事实如下：

1. 047 使用模型：`qwen3:0.6b`。
2. 047 prompt：`只输出一行：OK。不要输出思考过程，不要解释，不要使用 Markdown。`
3. prompt 性质：无业务含义、无隐私、无真实数据。
4. `ollama run` 执行次数：1 次。
5. 是否返回响应：是。
6. 响应耗时：约 `1.1102 seconds`。
7. 非敏感响应摘要：`输出包含非敏感 thinking 文本，最终返回 OK；响应超过 100 字，未复制完整长输出。`
8. 是否出现 thinking 文本：是。
9. 是否严格满足“一行 OK”：否。
10. 判定：`CONTROL_GAP`。
11. 未触发真实 KG / 真实项目资料读取。
12. 未触发 ZDoc generation/export/write-back。
13. 未进入 trial。
14. 未进入真实使用或 50 人正式使用。

本节点复核结论：

1. 047 已返回响应，说明最小模型响应链路仍可用。
2. 047 输出包含 thinking 文本和解释性内容，说明输出格式控制未完全达成。
3. 047 最终包含 `OK`，但不是唯一输出。
4. 047 不满足严格一行 `OK`。
5. 047 的 `CONTROL_GAP` 判定成立。

## 5. CONTROL_GAP 性质判断

本节点明确：

1. `CONTROL_GAP` 不等于安全越界。
2. `CONTROL_GAP` 不等于模型运行失败。
3. `CONTROL_GAP` 表示模型响应链路可用，但格式控制未完全达成。
4. 当前问题集中在输出格式控制，而不是服务连通性。
5. 当前问题不影响 043 最小 smoke test 已通过结论。
6. 当前问题会影响后续正式文档生成的可控性。
7. 在进入 ZDoc + Ollama 业务集成前，应优先解决或明确输出控制策略。

## 6. 风险影响分析

风险影响如下：

1. 对安全边界影响：未发现越界；047 未读取真实 KG、真实项目资料、真实招标文件、隐私数据或 secrets。
2. 对输出质量影响：输出未完全按指定格式，仅最终返回 `OK`，但包含 thinking 文本和解释性内容。
3. 对后续文档生成影响：可能干扰结构化解析、结果校验、JSON/Markdown 格式控制。
4. 对技术标文本生成影响：若 thinking 文本混入正式输出，可能影响成稿质量、格式纯度和交付可读性。
5. 对自动化流水线影响：可能影响后续解析器、导出流程、质量检查和自动校验。
6. 对当前系统状态影响：ZDoc 服务、Ollama server、健康检查和 smoke test 基础链路仍成立；本节点未重新探测服务、端口或 endpoint。

## 7. 后续可选路线

### 路线 A：Prompt 控制策略授权门

建议节点：

`LOCAL-LAUNCHER-049-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-AUTHORIZATION-GATE`

性质：

1. 仅记录 prompt 控制策略授权边界。
2. 不运行模型。
3. 不输入 prompt。
4. 不执行 Ollama 命令。
5. 目标是设计更强的输出控制 prompt、停止条件、格式要求、长度限制。

### 路线 B：模型参数 / 输出模式治理授权门

建议节点：

`LOCAL-LAUNCHER-049-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-MODE-GOVERNANCE-AUTHORIZATION-GATE`

性质：

1. 仅记录是否需要研究模型输出模式、thinking 控制、system prompt 约束等。
2. 不运行模型。
3. 不修改配置。
4. 不读取真实数据。

### 路线 C：更换轻量模型输出控制授权门

建议节点：

`LOCAL-LAUNCHER-049-ZDOC-LOCAL-APP-V1-OLLAMA-ALTERNATIVE-LIGHTWEIGHT-OUTPUT-CONTROL-AUTHORIZATION-GATE`

性质：

1. 仅记录是否允许后续使用 `qwen3:8b` 做一次输出控制对比。
2. 不运行模型。
3. 不输入 prompt。
4. 不执行 benchmark。
5. 不读取真实数据。

### 路线 D：暂缓输出控制，进入 ZDoc + Ollama 集成 readiness 授权门

建议节点：

`LOCAL-LAUNCHER-049-ZDOC-LOCAL-APP-V1-ZDOC-OLLAMA-INTEGRATION-READINESS-AUTHORIZATION-GATE`

性质：

1. 仅记录集成 readiness 边界。
2. 不访问业务 endpoint。
3. 不触发 generation。
4. 不读取真实 KG / 真实项目资料。
5. 需明确带着 output control gap 风险进入后续阶段。

## 8. 推荐路线

推荐进入：

`LOCAL-LAUNCHER-049-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-AUTHORIZATION-GATE`

推荐理由：

1. 当前问题是输出控制策略不足，而不是模型不可用。
2. 继续直接运行模型可能重复得到 thinking 文本。
3. 在再次执行模型前，应先设计更严密的 prompt 控制策略。
4. 路线 A 仍为 docs-only 授权门，风险低。
5. 有利于后续正式文档生成、结构化输出、质量校核。

必须明确：

1. 049 只能是 authorization gate。
2. 049 不得运行模型。
3. 049 不得输入 prompt。
4. 049 不得执行任何 Ollama 命令。
5. 049 不得读取真实 KG / 真实项目资料。
6. 真正执行新的 prompt 控制 smoke test 必须另设 execution gate。
7. 若用户选择其他路线，应由 ChatGPT 总控师另行下发对应节点。

## 9. 后续授权门拆分原则

后续必须遵守：

1. prompt 控制策略必须先 authorization，再 execution。
2. 任何再次模型运行必须另设 execution gate。
3. 使用 `qwen3:8b` 或其他模型必须另设授权门。
4. 多模型对比必须另设授权门。
5. ZDoc 调用 Ollama 必须另设授权门。
6. 真实 KG / 真实项目资料读取必须另设授权门。
7. generation/export/write-back 必须另设授权门。
8. trial 必须另设授权门。
9. 50 人正式使用必须另设 readiness 与 deployment gate。

## 10. 服务状态策略

服务状态策略如下：

1. 当前 ZDoc 服务仍应视为运行状态。
2. 当前 Ollama server 仍应视为运行状态。
3. 本节点不授权停止或重启任何服务。
4. 本节点不授权启动任何新服务。
5. 本节点不访问 endpoint 重新探测服务状态。
6. 若后续继续验证，应保持状态记录连续。
7. 若用户计划暂停，应另设 service lifecycle authorization gate。
8. controlled stop 必须另设 execution gate。

## 11. 实际执行命令清单

本节点实际执行的 git 状态确认命令：

```bash
git status --short
git log -1 --format=%H
git log -1 --oneline --decorate=short
git tag --points-at HEAD
```

本节点实际执行的只读文档查看命令：

```bash
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-execution-gate-local-launcher-047.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-authorization-gate-local-launcher-046.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md
```

本节点未执行任何 Ollama 命令、HTTP request、endpoint 访问、测试、lint 或 build。

## 12. 禁止项确认

本节点确认：

1. 未修改 V1 页面产物。
2. 未修改 V0。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未创建真正 App 包。
7. 未创建 Tauri 工程。
8. 未创建 Electron 工程。
9. 未创建 runtime bridge。
10. 未运行 npm/yarn/pnpm/pip。
11. 未运行测试/lint/build。
12. 未打开 HTML 页面。
13. 未启动新 ZDoc 服务。
14. 未重启 ZDoc 服务。
15. 未停止 ZDoc 服务。
16. 未启动新的 Ollama server。
17. 未重启 Ollama server。
18. 未停止 Ollama server。
19. 未访问 endpoint。
20. 未访问 ZDoc endpoint。
21. 未访问 Ollama endpoint。
22. 未执行 curl / HTTP request。
23. 未再次访问 `/health`。
24. 未执行 `ollama list`。
25. 未执行 `ollama run`。
26. 未执行 `ollama pull`。
27. 未执行 `ollama serve`。
28. 未执行 `ollama create`。
29. 未执行 `ollama rm`。
30. 未执行 `ollama cp`。
31. 未执行任何 Ollama 模型命令。
32. 未执行模型推理。
33. 未输入 prompt。
34. 未修改 prompt 后重试。
35. 未下载模型。
36. 未删除模型。
37. 未创建模型。
38. 未运行多个模型。
39. 未使用非 `qwen3:0.6b` 模型。
40. 未执行性能 benchmark。
41. 未执行长文本生成。
42. 未使用真实业务 prompt。
43. 未使用真实技术标内容。
44. 未使用真实项目资料内容。
45. 未读取真实 KG。
46. 未读取真实项目资料。
47. 未读取真实招标文件。
48. 未读取用户隐私或业务数据。
49. 未读取 `.env`、`.env.*`、secret、token、credential、key、private 配置。
50. 未读取 registration / metadata / proof / manifest / sample 实例。
51. 未读取 output/job/export 正文。
52. 未读取日志正文。
53. 未触发 ZDoc generation。
54. 未触发 export。
55. 未触发 write-back。
56. 未写 output/job/export。
57. 未进入 trial。
58. 未进入真实使用。
59. 未进入 50 人正式使用。
60. 未进入 `LOCAL-LAUNCHER-049`。

## 13. 当前 Decision

`LOCAL-LAUNCHER-048 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL GAP REVIEW GATE COMPLETED / OUTPUT CONTROL GAP RECORDED / MODEL RESPONDED BUT STRICT ONE-LINE OK FORMAT NOT FULLY CONFIRMED / NO ADDITIONAL OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED`

## 14. 下一节点建议

推荐进入：

`LOCAL-LAUNCHER-049-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-AUTHORIZATION-GATE`

但必须明确：

1. 049 只能是 authorization gate。
2. 049 不授权 `ollama run`。
3. 049 不授权 prompt 输入。
4. 049 不授权模型推理。
5. 049 不授权再次执行输出控制 smoke test。
6. 049 不授权访问 endpoint。
7. 049 不授权真实 KG / 真实项目资料读取。
8. 049 不授权 trial。
9. 049 不授权 generation/export/write-back。
10. 若用户选择其他路线，应由 ChatGPT 总控师另行下发对应节点。

## 15. 明确说明未进入 `LOCAL-LAUNCHER-049`

本节点未进入 `LOCAL-LAUNCHER-049`。
