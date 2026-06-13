# LOCAL-LAUNCHER-046 ZDoc Local App V1 Ollama Output Control Smoke Test Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-046-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-AUTHORIZATION-GATE`

本节点性质：

`Ollama output control smoke test authorization boundary and user authorization request only`

本节点目标：

记录未来是否可以执行一次“模型输出控制 smoke test”的授权边界、禁止事项、阻断条件、用户授权文本模板和后续进入条件。

本节点明确：

1. 不执行任何 Ollama 命令。
2. 不运行模型。
3. 不输入 prompt。
4. 不执行 `ollama run`。
5. 不访问 endpoint。
6. 不触发 trial。
7. 不触发 ZDoc generation/export/write-back。
8. 不读取真实 KG、真实项目资料或真实招标文件。
9. 不进入 `LOCAL-LAUNCHER-047`。

## 2. 当前基线 HEAD/tag

- 开始前 HEAD：`beb9f8787fb8907cfaaa2a88892831eacc81cfc9`
- 开始前 tag：`v0.1.681-local-launcher-zdoc-local-app-v1-ollama-model-run-smoke-test-next-stage-strategy-gate`
- 当前分支基线：`main`
- 上一节点：`LOCAL-LAUNCHER-045-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-NEXT-STAGE-STRATEGY-GATE`

实际最近提交：

```text
beb9f87 LOCAL-LAUNCHER-045 ollama smoke test next stage strategy
```

## 3. 上游节点通过状态

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-model-selection-result-record-gate-local-launcher-041.md`
2. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-authorization-gate-local-launcher-042.md`
3. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md`
4. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md`
5. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md`

复核结果：

1. 041 model selection result closed。
2. 042 smoke test authorization boundary completed。
3. 043 smoke test 判定：`PASS`。
4. 044 smoke test result closed。
5. 045 next-stage strategy completed。
6. 045 已推荐进入输出控制 smoke test 授权门。

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

## 4. 当前系统状态判断

当前系统状态如下：

1. ZDoc 本地服务 controlled start 已完成。
2. ZDoc post-start status 已 `PASS`。
3. ZDoc endpoint health check 已 `PASS`。
4. endpoint health check result 已闭环。
5. Ollama server 已启动。
6. Ollama server post-start status 已 `PASS`。
7. 本地模型清单已确认。
8. 模型选择建议已完成。
9. `qwen3:0.6b` 最小 smoke test 已 `PASS`。
10. 043 输出中出现非敏感 thinking 文本。
11. thinking 文本为非阻断观察项。
12. 当前仍不具备 trial / generation / export / write-back 条件。
13. 当前仍不具备真实 KG / 真实项目资料读取条件。
14. 当前仍不具备真实业务 prompt 条件。

说明：本节点未重新探测服务、进程、端口、endpoint 或 Ollama；上述状态来自 041、042、043、044、045 文档链的只读复核。

## 5. 043 / 044 smoke test 结果摘要

已记录的 smoke test 结果如下：

1. smoke test 模型：`qwen3:0.6b`。
2. smoke test prompt：`只回复 OK。`。
3. prompt 性质：无业务含义、无隐私、无真实数据。
4. `ollama run` 执行次数：1 次。
5. 是否返回响应：是。
6. 响应耗时：约 `1.2560` 秒。
7. 非敏感响应摘要：`输出包含非敏感 thinking 文本，最终返回 OK；响应超过 100 字，未复制完整长输出。`
8. smoke test 判定：`PASS`。
9. 044 已记录结果闭环。

本节点确认：

1. 未再次执行 `ollama run`。
2. 未再次执行任何 Ollama 命令。
3. 未再次运行模型。
4. 未输入 prompt。
5. 未复制完整长输出。

## 6. 输出控制问题定义

输出控制问题定义如下：

1. 首次 smoke test 的核心目的已达成：模型最小响应链路可用。
2. 但输出中出现 thinking 文本，提示后续需要输出控制验证。
3. 输出控制验证的目标不是测试业务质量。
4. 输出控制验证的目标是确认模型能否在无真实数据条件下按指定格式输出。
5. 输出控制 smoke test 仍不得接入 ZDoc generation。
6. 输出控制 smoke test 仍不得读取真实 KG / 真实项目资料。
7. 输出控制 smoke test 仍不得进入 trial。
8. 输出控制 smoke test 仍不得触发 export/write-back。

## 7. 未来 047 可授权范围草案

以下仅作为未来 `LOCAL-LAUNCHER-047` 可授权范围草案，本节点不执行。

未来若用户明确授权 `LOCAL-LAUNCHER-047`，输出控制 smoke test execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 043 smoke test `PASS`。
6. 复核 044 smoke test result closed。
7. 复核 045 next-stage strategy。
8. 复核 Ollama server PID 与监听端口。
9. 使用 `qwen3:0.6b` 执行一次输出控制 smoke test。
10. 仅输入无业务含义、无隐私、无真实数据的最小格式控制 prompt。
11. 建议 prompt 固定为：`只输出一行：OK。不要输出思考过程，不要解释，不要使用 Markdown。`
12. 仅记录是否返回响应。
13. 仅记录响应耗时。
14. 仅记录非敏感响应摘要。
15. 记录是否出现 thinking 文本。
16. 记录是否严格满足“一行 OK”。
17. 不接入 ZDoc generation。
18. 不接入真实 KG。
19. 不接入真实项目资料。
20. 不读取招标文件。
21. 不写 output/job/export。
22. 不进入 trial。
23. 执行完成或阻断后立即回报并停止。

## 8. 未来 047 禁止范围草案

未来 047 仍应禁止：

1. 读取真实 KG。
2. 读取真实项目资料。
3. 读取真实招标文件。
4. 读取用户隐私或业务数据。
5. 读取 `.env` / secrets / tokens / credentials。
6. 读取 registration / metadata / proof / manifest / sample 实例。
7. 读取 output/job/export 正文。
8. 触发 ZDoc generation。
9. 触发 export。
10. 触发 write-back。
11. 写 output/job/export。
12. ZBid 写回。
13. trial。
14. 真实使用。
15. 50 人正式使用。
16. 使用真实业务 prompt。
17. 使用真实技术标内容。
18. 使用真实项目资料内容。
19. 运行多个模型。
20. 使用非 `qwen3:0.6b` 模型。
21. 执行性能 benchmark。
22. 执行长文本生成。
23. 执行模型下载。
24. 执行 `ollama pull`。
25. 执行 `ollama create`。
26. 执行 `ollama rm`。
27. 修改 V0/V1/backend/frontend/config/dependency。
28. 创建脚本、App 包、Tauri/Electron 工程、runtime bridge。
29. 运行测试/lint/build。
30. 停止或重启当前 ZDoc 服务，除非后续另行授权。
31. 停止或重启 Ollama server，除非后续另行授权。

## 9. 输出控制 smoke test 阻断条件

未来 047 如出现以下任一情况，应判定 `BLOCKED`，不得继续：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 043 `PASS` 无法复核。
4. 044 result closed 无法复核。
5. 045 strategy 无法复核。
6. Ollama server PID 或端口无法复核。
7. `qwen3:0.6b` 不在已记录模型清单中。
8. 需要执行 `ollama list` 才能确认模型。
9. 需要执行 `ollama pull` 才能获取模型。
10. 需要读取真实 KG 才能构造 prompt。
11. 需要读取真实项目资料才可构造 prompt。
12. 需要触发 generation/export/write-back 才能判断。
13. 需要访问 ZDoc 业务 endpoint。
14. 需要写 output/job/export。
15. 需要运行多个模型才能判断。
16. 需要执行 benchmark 才能判断。
17. 需要长文本生成才能判断。
18. 无法在授权范围内完成最小输出控制验证。

## 10. 用户授权文本模板

后续如需进入 `LOCAL-LAUNCHER-047`，用户可直接复制以下授权文本：

`我明确授权 LOCAL-LAUNCHER-047 执行 Ollama output control smoke test execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 043 smoke test PASS、复核 044 smoke test result closed、复核 045 next-stage strategy、复核 Ollama server PID 与监听端口、使用 qwen3:0.6b 执行一次输出控制 smoke test、仅输入无业务含义/无隐私/无真实数据的最小格式控制 prompt：“只输出一行：OK。不要输出思考过程，不要解释，不要使用 Markdown。”、仅记录是否返回响应、响应耗时、非敏感响应摘要、是否出现 thinking 文本、是否严格满足“一行 OK”。严格禁止读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 .env/secrets/tokens/credentials、读取 registration/metadata/proof/manifest/sample 实例、读取 output/job/export 正文、触发 ZDoc generation、触发 export、触发 write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用、使用真实业务 prompt、使用真实技术标内容、使用真实项目资料内容、运行多个模型、使用非 qwen3:0.6b 模型、执行性能 benchmark、执行长文本生成、执行模型下载、执行 ollama pull/create/rm、修改 V0/V1/backend/frontend/config/dependency。若输出控制 smoke test 需要真实数据、业务 prompt、生成导出写回、下载模型、运行多个模型或访问业务 endpoint，必须判定 BLOCKED 并停止。执行完成或阻断后必须回报并停止，不得进入下一节点。`

## 11. 进入 047 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-047-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-EXECUTION-GATE`

若用户未授权，则 hold。

本节点不得进入 `LOCAL-LAUNCHER-047`。

047 即使后续被授权，也仅允许一次输出控制 smoke test。

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
50. 未进入 `LOCAL-LAUNCHER-047`。

## 13. 后续限制

后续必须保持以下限制：

1. trial / generation / export / write-back 必须另设授权门。
2. 真实 KG / 真实项目资料读取必须另设授权门。
3. 50 人正式使用必须另设 readiness 与 deployment gate。
4. ZBid 写回必须另设专门授权链路。
5. 当前 ZDoc 服务不得被停止或重启，除非另行授权。
6. 当前 Ollama server 不得被停止或重启，除非另行授权。

## 14. 当前 Decision

`LOCAL-LAUNCHER-046 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL SMOKE TEST AUTHORIZATION GATE COMPLETED / OUTPUT CONTROL SMOKE TEST EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED`

## 15. 下一节点建议

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-047-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 047。
4. 047 即使后续被授权，也仅允许一次输出控制 smoke test。
5. trial / generation / export / write-back 必须另设授权门。
6. 真实 KG / 真实项目资料读取必须另设授权门。
7. 50 人正式使用必须另设 readiness 与 deployment gate。

## 16. 明确说明未进入 `LOCAL-LAUNCHER-047`

本节点未进入 `LOCAL-LAUNCHER-047`。
