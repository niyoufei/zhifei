# LOCAL-LAUNCHER-047 ZDoc Local App V1 Ollama Output Control Smoke Test Execution Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-047-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-EXECUTION-GATE`

本节点性质：

`Ollama output control smoke test execution gate`

本节点目标：

在不读取真实数据、不触发 ZDoc generation/export/write-back、不进入 trial 的前提下，使用 `qwen3:0.6b` 执行 1 次输出控制 smoke test，验证模型是否能按最小格式控制要求输出。

## 2. 用户授权摘要

用户明确授权 `LOCAL-LAUNCHER-047` 执行 `Ollama output control smoke test execution`。

授权范围仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 043 smoke test `PASS`。
6. 复核 044 smoke test result closed。
7. 复核 045 next-stage strategy。
8. 复核 046 output control authorization boundary。
9. 复核 Ollama server PID 与监听端口。
10. 使用 `qwen3:0.6b` 执行一次输出控制 smoke test。
11. 仅输入无业务含义、无隐私、无真实数据的最小格式控制 prompt：

`只输出一行：OK。不要输出思考过程，不要解释，不要使用 Markdown。`

12. 仅记录是否返回响应。
13. 仅记录响应耗时。
14. 仅记录非敏感响应摘要。
15. 记录是否出现 thinking 文本。
16. 记录是否严格满足“一行 OK”。

本节点严格禁止读取真实 KG、真实项目资料、真实招标文件、隐私数据、`.env`、secrets、tokens、credentials、registration、metadata、proof、manifest、sample 实例、output/job/export 正文或日志正文；禁止触发 ZDoc generation、export、write-back；禁止写 output/job/export；禁止进入 trial、真实使用或 50 人正式使用；禁止使用真实业务 prompt、真实技术标内容、真实项目资料内容；禁止运行多个模型、执行 benchmark、执行长文本生成、下载模型、执行 `ollama pull/create/rm` 或修改 V0/V1/backend/frontend/config/dependency。

## 3. 当前基线 HEAD/tag

- 开始前 HEAD：`929577bb3599d13c242d7498d3ce2c80b1e25aec`
- 开始前 tag：`v0.1.682-local-launcher-zdoc-local-app-v1-ollama-output-control-smoke-test-authorization-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-046-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-SMOKE-TEST-AUTHORIZATION-GATE`

实际最近提交：

```text
929577b LOCAL-LAUNCHER-046 ollama output control authorization
```

## 4. 仓库路径确认结果

实际路径：

```text
/Users/youfeini/Desktop/文档生成系统
```

结论：符合预期仓库路径。

## 5. 当前分支确认结果

实际分支：

```text
main
```

结论：符合预期分支。

## 6. HEAD/tag 确认结果

实际开始前 HEAD：

```text
929577bb3599d13c242d7498d3ce2c80b1e25aec
```

实际开始前 HEAD tag：

```text
v0.1.682-local-launcher-zdoc-local-app-v1-ollama-output-control-smoke-test-authorization-gate
```

结论：HEAD/tag 与 046 基线一致。

## 7. 工作区 clean 确认结果

开始前 `git status --short` 无输出。

smoke test 执行后、写入 047 docs 前再次执行 `git status --short` 无输出。

结论：工作区在写入本文件前 clean，smoke test 未造成仓库文件变更。

## 8. 上游文档复核结果

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md`
2. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md`
3. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md`
4. `docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-authorization-gate-local-launcher-046.md`
5. `docs/zdoc-local-launcher-v1-ollama-model-selection-result-record-gate-local-launcher-041.md`

复核结果：

1. 043 smoke test 判定：`PASS`。
2. 044 smoke test result closed。
3. 045 next-stage strategy 已建议优先进入输出控制 smoke test 授权门。
4. 046 output control authorization boundary 已完成，并授权未来 047 在固定边界内执行一次输出控制 smoke test。
5. 041 已记录本地模型清单与模型选择结果，轻量快速候选包含 `qwen3:0.6b`。

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

## 9. Ollama server PID 与监听端口复核结果

实际执行：

```bash
pgrep -fl "ollama"
lsof -nP -iTCP -sTCP:LISTEN
```

`pgrep` 结果：

```text
83676 /opt/homebrew/bin/ollama serve
```

`lsof` 结果中 Ollama 监听项：

```text
ollama 83676 youfeini 4u IPv4 ... TCP 127.0.0.1:11434 (LISTEN)
```

结论：

1. Ollama server PID `83676` 仍存在。
2. `127.0.0.1:11434` 仍处于 LISTEN。
3. 未读取进程环境变量。
4. 未停止、重启或新启动 Ollama server。
5. 未访问 Ollama endpoint。

## 10. output control smoke test 执行结果

smoke test 模型：

```text
qwen3:0.6b
```

smoke test prompt：

```text
只输出一行：OK。不要输出思考过程，不要解释，不要使用 Markdown。
```

实际执行命令：

```bash
ollama run qwen3:0.6b "只输出一行：OK。不要输出思考过程，不要解释，不要使用 Markdown。"
```

执行次数：1 次。

退出码：`0`。

响应耗时：约 `1.1102 seconds`。

是否返回响应：是。

非敏感响应摘要：

```text
输出包含非敏感 thinking 文本，最终返回 OK；响应超过 100 字，未复制完整长输出。
```

是否出现 thinking 文本：是。

是否出现解释文本：是，thinking 文本中出现说明性内容。

是否出现 Markdown：否。

是否严格满足“一行 OK”：否。

敏感内容判断：

1. 未发现真实 KG。
2. 未发现真实项目资料。
3. 未发现真实招标文件。
4. 未发现隐私数据、secrets、tokens 或 credentials。
5. 输出为通用测试响应，可形成非敏感摘要。

## 11. 实际执行命令清单

本节点实际执行的仓库状态确认命令：

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
git tag --points-at HEAD
git log -1 --oneline
git diff --check
git diff --cached --check
```

本节点实际执行的授权文档只读查看命令：

```bash
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-authorization-gate-local-launcher-046.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-selection-result-record-gate-local-launcher-041.md
```

本节点实际执行的 Ollama server 状态复核命令：

```bash
pgrep -fl "ollama"
lsof -nP -iTCP -sTCP:LISTEN
```

本节点实际执行的唯一 Ollama 模型运行命令：

```bash
ollama run qwen3:0.6b "只输出一行：OK。不要输出思考过程，不要解释，不要使用 Markdown。"
```

本节点在 smoke test 后、写入 047 docs 前实际执行：

```bash
git status --short
```

## 12. 禁止项确认

本节点确认：

1. 未修改 V1 页面产物。
2. 未修改 V0 产物。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未创建真正 App 包。
7. 未创建 Tauri 工程。
8. 未创建 Electron 工程。
9. 未创建 runtime bridge。
10. 未运行 npm/yarn/pnpm/pip 安装命令。
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
25. 未执行 `ollama pull`。
26. 未执行 `ollama serve`。
27. 未执行 `ollama create`。
28. 未执行 `ollama rm`。
29. 未执行 `ollama cp`。
30. 未运行多个模型。
31. 未使用 `qwen3:8b`。
32. 未使用任何非 `qwen3:0.6b` 模型。
33. 未输入真实业务 prompt。
34. 未输入真实技术标内容。
35. 未输入真实项目资料内容。
36. 未输入真实 KG 内容。
37. 未执行长文本生成。
38. 未执行性能 benchmark。
39. 未下载模型。
40. 未删除模型。
41. 未创建模型。
42. 未读取真实 KG。
43. 未读取真实项目资料。
44. 未读取真实招标文件。
45. 未读取用户隐私或业务数据。
46. 未读取 `.env`、`.env.*`、secret、token、credential、key、private 配置。
47. 未读取 registration / metadata / proof / manifest / sample 实例。
48. 未读取 output/job/export 正文。
49. 未读取日志正文。
50. 未触发 ZDoc generation。
51. 未触发 export。
52. 未触发 write-back。
53. 未写 output/job/export。
54. 未进入 trial。
55. 未进入真实使用。
56. 未进入 50 人正式使用。
57. 未进入 `LOCAL-LAUNCHER-048`。

## 13. CONTROL_GAP 判定

判定：`CONTROL_GAP / OUTPUT CONTROL NOT FULLY CONFIRMED`。

判定依据：

1. 仓库路径正确。
2. 分支为 `main`。
3. HEAD/tag 与 046 基线一致。
4. 工作区 clean。
5. 043 smoke test `PASS` 已复核。
6. 044 smoke test result closed 已复核。
7. 045 next-stage strategy 已复核。
8. 046 output control authorization boundary 已复核。
9. Ollama server PID 与监听端口已复核。
10. `qwen3:0.6b` 在 041 已记录模型选择结果中。
11. 仅执行 1 次指定 `ollama run` 命令。
12. 模型返回响应。
13. 已记录响应耗时。
14. 已记录非敏感响应摘要。
15. 输出出现 thinking 文本。
16. 输出出现解释文本。
17. 最终返回 `OK`，但不是唯一输出。
18. 输出不严格满足一行 `OK`。
19. 未执行 `ollama list`。
20. 未执行 `ollama pull`。
21. 未执行 `ollama serve`。
22. 未运行多个模型。
23. 未使用真实业务 prompt。
24. 未使用真实技术标内容。
25. 未使用真实项目资料内容。
26. 未读取真实 KG / 真实项目资料。
27. 未触发 ZDoc generation/export/write-back。
28. 未写 output/job/export。
29. 未进入 trial、真实使用、50 人正式使用。
30. 未进入下一节点。

`CONTROL_GAP` 不等于安全越界；该结果仅表示输出格式控制尚未完全达成。

## 14. 当前 Decision

`LOCAL-LAUNCHER-047 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL SMOKE TEST EXECUTION GATE COMPLETED WITH OUTPUT CONTROL GAP / MODEL RESPONDED BUT STRICT ONE-LINE OK FORMAT NOT FULLY CONFIRMED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED`

## 15. 后续限制

后续必须保持以下限制：

1. 不得为修正输出再次运行模型。
2. 不得修改 prompt 后重试。
3. 048 不得执行 `ollama run`。
4. 048 不得输入 prompt。
5. 048 不得再次执行模型推理。
6. trial / generation / export / write-back 必须另设授权门。
7. 真实 KG / 真实项目资料读取必须另设授权门。
8. 当前 ZDoc 服务不得被停止或重启，除非另行授权。
9. 当前 Ollama server 不得被停止或重启，除非另行授权。
10. 不得自行扩大授权。
11. 不得运行其他模型。
12. 不得 pull 模型。

## 16. 下一节点建议

因本节点判定为 `CONTROL_GAP`，下一节点建议为：

`LOCAL-LAUNCHER-048-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-GAP-REVIEW-GATE`

048 只能复核输出控制差距，不得再次运行模型，不得输入 prompt，不得修改 prompt 重试，不得进入 trial，不得触发 generation/export/write-back。

## 17. 明确说明未进入 `LOCAL-LAUNCHER-048`

本节点未进入 `LOCAL-LAUNCHER-048`。
