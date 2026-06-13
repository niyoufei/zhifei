# LOCAL-LAUNCHER-045 ZDoc Local App V1 Ollama Model Run Smoke Test Next Stage Strategy Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-045-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-NEXT-STAGE-STRATEGY-GATE`

本节点性质：

`Ollama model run smoke test next-stage strategy only`

本节点目标：

在首次最小模型运行 smoke test 通过后，形成下一阶段路线策略、风险分级、授权门拆分和推荐推进顺序。

本节点明确：

1. 不执行任何 Ollama 命令。
2. 不运行模型。
3. 不输入 prompt。
4. 不访问 endpoint。
5. 不触发 trial。
6. 不触发 ZDoc generation/export/write-back。
7. 不读取真实 KG、真实项目资料或真实招标文件。
8. 不进入 `LOCAL-LAUNCHER-046`。

## 2. 当前基线 HEAD/tag

- 开始前 HEAD：`014b0a0ee10b121e03b55ba9558fc18c4209cca0`
- 开始前 tag：`v0.1.680-local-launcher-zdoc-local-app-v1-ollama-model-run-smoke-test-result-record-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-044-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-RESULT-RECORD-GATE`

实际最近提交：

```text
014b0a0 LOCAL-LAUNCHER-044 ollama smoke test result record
```

## 3. 上游节点通过状态

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-model-inventory-result-record-gate-local-launcher-038.md`
2. `docs/zdoc-local-launcher-v1-ollama-model-selection-execution-gate-local-launcher-040.md`
3. `docs/zdoc-local-launcher-v1-ollama-model-selection-result-record-gate-local-launcher-041.md`
4. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-authorization-gate-local-launcher-042.md`
5. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md`
6. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md`
7. `local_launcher/v1/README.md`

复核结果：

1. 038 inventory result closed。
2. 040 model selection 判定：`PASS`。
3. 041 model selection result closed。
4. 042 smoke test authorization boundary completed。
5. 043 smoke test 判定：`PASS`。
6. 044 smoke test result closed。
7. V1 professional static console only 状态已记录。

040 当前 decision：

```text
LOCAL-LAUNCHER-040 ZDOC LOCAL APP V1 OLLAMA MODEL SELECTION EXECUTION GATE PASSED / MODEL SELECTION RECOMMENDATION COMPLETED BASED ON RECORDED LOCAL INVENTORY / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

041 当前 decision：

```text
LOCAL-LAUNCHER-041 ZDOC LOCAL APP V1 OLLAMA MODEL SELECTION RESULT RECORD GATE COMPLETED / MODEL SELECTION RECOMMENDATION PASS RECORDED / MODEL SELECTION RESULT CLOSED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

042 当前 decision：

```text
LOCAL-LAUNCHER-042 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST AUTHORIZATION GATE COMPLETED / MODEL RUN SMOKE TEST EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

043 当前 decision：

```text
LOCAL-LAUNCHER-043 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST EXECUTION GATE PASSED / MINIMAL MODEL RUN SMOKE TEST COMPLETED WITH QWEN3 0.6B / NON-SENSITIVE RESPONSE SUMMARY RECORDED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

044 当前 decision：

```text
LOCAL-LAUNCHER-044 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST RESULT RECORD GATE COMPLETED / MODEL RUN SMOKE TEST PASS RECORDED / MINIMAL QWEN3 0.6B RESPONSE RESULT CLOSED / NO ADDITIONAL OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

## 4. 当前已证明事项

当前已证明事项如下：

1. V1 专业静态控制台已完成并通过人工验收。
2. ZDoc 服务 controlled start 已完成。
3. ZDoc post-start status 已 `PASS`。
4. ZDoc `/health` 最小 endpoint health check 已 `PASS`。
5. endpoint health check result 已闭环。
6. Ollama server 已启动并通过 post-start status。
7. Ollama 本地模型清单已确认且非空。
8. 模型选择建议已完成。
9. `qwen3:0.6b` 已完成一次最小 smoke test。
10. 最小模型响应链路已验证。
11. smoke test 未接入真实 KG / 真实项目资料。
12. smoke test 未触发 ZDoc generation/export/write-back。
13. smoke test 未进入 trial。

说明：本节点未重新探测服务、进程、端口、endpoint 或 Ollama；上述事项来自当前基线和上游文档链只读复核。

## 5. 当前未证明事项

当前未证明事项如下：

1. 尚未证明 ZDoc 业务链路可调用 Ollama。
2. 尚未证明模型输出格式可严格受控。
3. 尚未证明模型对技术标 / 施工组织设计任务的质量。
4. 尚未证明真实 KG 接入。
5. 尚未证明真实项目资料接入。
6. 尚未证明 generation/export/write-back。
7. 尚未证明 trial 可用。
8. 尚未证明并发、稳定性、长文本、超时、失败恢复能力。
9. 尚未证明 50 人正式使用 readiness。
10. 尚未证明 ZBid 写回。

## 6. 非阻断观察项

043 模型输出中出现非敏感 thinking 文本。

观察结论：

1. 该现象不影响 043 smoke test `PASS`。
2. 该现象不改变 044 result closed。
3. 该现象提示后续需要输出格式控制策略。
4. 后续如进入模型运行验证，应在授权门中明确是否允许 thinking 文本。
5. 后续如进入模型运行验证，应在授权门中明确是否要求仅输出最终答案。
6. 后续如进入模型运行验证，应在授权门中明确是否要求 JSON / plain text / markdown 格式。
7. 后续如进入模型运行验证，应在授权门中明确最大响应长度。
8. 后续如进入模型运行验证，应在授权门中明确超时边界。
9. 本节点不得为此再次运行模型。
10. 本节点不得为此修改 prompt。

## 7. 下一阶段可选路线

### 路线 A：模型输出控制 smoke test 授权门

建议节点：

`LOCAL-LAUNCHER-046-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-AUTHORIZATION-GATE`

性质：

1. 仅记录授权边界。
2. 不运行模型。
3. 不输入 prompt。
4. 不执行 Ollama 命令。
5. 目标是为后续验证“仅输出最终答案 / 不输出 thinking / 限制格式”建立边界。

### 路线 B：ZDoc + Ollama 集成 readiness 授权门

建议节点：

`LOCAL-LAUNCHER-046-ZDOC-LOCAL-APP-V1-ZDOC-OLLAMA-INTEGRATION-READINESS-AUTHORIZATION-GATE`

性质：

1. 仅记录授权边界。
2. 不访问业务 endpoint。
3. 不触发 generation。
4. 不读取真实 KG / 真实项目资料。
5. 目标是规划 ZDoc 如何在无真实数据条件下调用本地 Ollama。

### 路线 C：无真实数据的模拟任务授权门

建议节点：

`LOCAL-LAUNCHER-046-ZDOC-LOCAL-APP-V1-SYNTHETIC-NO-DATA-MODEL-TASK-AUTHORIZATION-GATE`

性质：

1. 仅记录授权边界。
2. 后续可使用合成、无业务、无隐私 prompt。
3. 不读取真实 KG。
4. 不读取真实项目资料。
5. 不触发 export/write-back。

### 路线 D：服务生命周期管理授权门

建议节点：

`LOCAL-LAUNCHER-046-ZDOC-LOCAL-APP-V1-RUNTIME-SERVICE-LIFECYCLE-AUTHORIZATION-GATE`

性质：

1. 仅记录是否需要继续保持 ZDoc / Ollama server 运行。
2. 不停止服务。
3. 不重启服务。
4. 不访问 endpoint。
5. 若用户计划暂停，应另设 controlled stop execution gate。

## 8. 推荐路线

推荐进入：

`LOCAL-LAUNCHER-046-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-AUTHORIZATION-GATE`

推荐理由：

1. 043 已出现 thinking 文本非阻断观察项。
2. 在进入 ZDoc + Ollama 集成前，应先明确输出格式控制。
3. 输出控制是后续文档生成质量控制的基础。
4. 该路线仍可保持无真实数据、无业务 prompt、无 generation/export/write-back。
5. 风险低于直接进入 ZDoc 业务集成或真实资料验证。

必须明确：

1. 046 仍只能是 authorization gate。
2. 046 不得运行模型。
3. 046 不得输入 prompt。
4. 046 不得访问 endpoint。
5. 046 不得读取真实 KG / 真实项目资料。
6. 046 不得停止或重启服务。
7. 真正执行输出控制 smoke test 必须另设 execution gate。

若用户选择其他路线，应由 ChatGPT 总控师另行下发对应节点。

## 9. 风险分级

低风险：

1. docs-only。
2. 策略文档。
3. 结果记录。
4. 授权边界记录。

中风险：

1. 无真实数据的单模型最小 smoke test。
2. 单次、短 prompt、非业务响应确认。
3. 不接入 ZDoc generation/export/write-back 的模型连通性验证。

高风险：

1. ZDoc 调用 Ollama。
2. 模型输出控制验证。
3. 多轮模型运行。
4. 格式约束、超时、失败恢复等行为验证。

极高风险：

1. 真实 KG / 真实项目资料读取。
2. generation/export/write-back。
3. trial。
4. 50 人正式使用。
5. ZBid 写回。

## 10. 服务状态策略

服务状态策略如下：

1. 当前 ZDoc 服务仍在运行。
2. 当前 Ollama server 仍在运行。
3. 本节点不授权停止任何服务。
4. 本节点不授权重启任何服务。
5. 本节点不授权启动新的服务。
6. 本节点不访问 endpoint 重新探测服务状态。
7. 若后续继续验证，应保持状态记录连续。
8. 若用户计划暂停，应先进入 service lifecycle authorization gate。
9. controlled stop 必须另设 execution gate。

## 11. 后续授权门拆分原则

后续必须遵守以下授权门拆分原则：

1. 模型再次运行必须另设 authorization gate 和 execution gate。
2. ZDoc 调用 Ollama 必须另设 authorization gate 和 execution gate。
3. 真实 KG / 真实项目资料读取必须另设 authorization gate 和 execution gate。
4. generation/export/write-back 必须另设 authorization gate 和 execution gate。
5. trial 必须另设 authorization gate 和 execution gate。
6. 50 人正式使用必须另设 readiness gate 与 deployment gate。
7. ZBid 写回必须另设专门授权链路。
8. 服务停止、重启或新启动必须另设 service lifecycle authorization gate 和 execution gate。
9. 任一授权门不得自动进入对应 execution gate。

## 12. 禁止项确认

本节点确认：

1. 未修改 V1 页面产物。
2. 未修改 V0。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未运行 npm/yarn/pnpm/pip。
7. 未运行测试/lint/build。
8. 未打开 HTML 页面。
9. 未启动新 ZDoc 服务。
10. 未重启 ZDoc 服务。
11. 未停止 ZDoc 服务。
12. 未启动新的 Ollama server。
13. 未重启 Ollama server。
14. 未停止 Ollama server。
15. 未访问 endpoint。
16. 未访问 ZDoc endpoint。
17. 未访问 Ollama endpoint。
18. 未执行 curl / HTTP request。
19. 未再次访问 `/health`。
20. 未执行 `ollama list`。
21. 未执行 `ollama run`。
22. 未执行 `ollama pull`。
23. 未执行 `ollama serve`。
24. 未执行 `ollama create`。
25. 未执行 `ollama rm`。
26. 未执行 `ollama cp`。
27. 未执行任何 Ollama 模型命令。
28. 未执行模型推理。
29. 未输入 prompt。
30. 未下载/删除/创建模型。
31. 未运行多个模型。
32. 未执行性能 benchmark。
33. 未执行长文本生成。
34. 未使用真实业务 prompt。
35. 未使用真实技术标内容。
36. 未使用真实项目资料内容。
37. 未读取真实 KG。
38. 未读取真实项目资料。
39. 未读取真实招标文件。
40. 未读取用户隐私或业务数据。
41. 未读取 `.env` / secrets / tokens / credentials。
42. 未读取 registration / metadata / proof / manifest / sample 实例。
43. 未读取 output/job/export 正文。
44. 未读取日志正文。
45. 未触发 ZDoc generation/export/write-back。
46. 未写 output/job/export。
47. 未进入 trial。
48. 未进入真实使用。
49. 未进入 50 人正式使用。
50. 未进入 `LOCAL-LAUNCHER-046`。

## 13. 当前 Decision

`LOCAL-LAUNCHER-045 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST NEXT STAGE STRATEGY GATE COMPLETED / NEXT STAGE STRATEGY DOCUMENTED AFTER MODEL RUN SMOKE TEST PASS / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED`

## 14. 下一节点建议

推荐进入：

`LOCAL-LAUNCHER-046-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-AUTHORIZATION-GATE`

但必须明确：

1. 046 只能是 authorization gate。
2. 046 不授权执行 `ollama run`。
3. 046 不授权输入 prompt。
4. 046 不授权模型推理。
5. 046 不授权访问 endpoint。
6. 046 不授权真实 KG / 真实项目资料读取。
7. 046 不授权 trial。
8. 046 不授权 generation/export/write-back。
9. 046 不授权停止或重启服务。
10. 若用户选择其他路线，应由 ChatGPT 总控师另行下发对应节点。

## 15. 明确说明未进入 `LOCAL-LAUNCHER-046`

本节点未进入 `LOCAL-LAUNCHER-046`。
