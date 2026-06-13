# LOCAL-LAUNCHER-043 ZDoc Local App V1 Ollama Model Run Smoke Test Execution Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-043-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-EXECUTION-GATE`

本节点性质：

`Ollama model run smoke test execution gate`

本节点目标：

在不读取真实数据、不触发 ZDoc generation/export/write-back、不进入 trial 的前提下，使用 `qwen3:0.6b` 执行 1 次最小模型运行 smoke test，确认 Ollama server 与轻量模型最小响应链路可用。

## 2. 用户授权摘要

用户明确授权 `LOCAL-LAUNCHER-043` 执行 `Ollama model run smoke test execution`。

授权范围仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 040 model selection `PASS`。
6. 复核 041 model selection result closed。
7. 复核 042 smoke test authorization boundary。
8. 复核 Ollama server PID 与监听端口。
9. 使用 `qwen3:0.6b` 执行一次最小 smoke test。
10. 仅输入无业务含义、无隐私、无真实数据的最小测试 prompt。
11. 仅记录是否返回响应。
12. 仅记录响应耗时。
13. 仅记录非敏感响应摘要。

本节点严格禁止读取真实 KG、真实项目资料、真实招标文件、隐私数据、`.env`、secrets、tokens、credentials、registration、metadata、proof、manifest、sample 实例、output/job/export 正文或日志正文；禁止触发 ZDoc generation、export、write-back；禁止写 output/job/export；禁止进入 trial、真实使用或 50 人正式使用；禁止使用真实业务 prompt、真实技术标内容、真实项目资料内容；禁止运行多个模型、执行 benchmark、执行长文本生成、下载模型、执行 `ollama pull/create/rm` 或修改 V0/V1/backend/frontend/config/dependency。

## 3. 当前基线 HEAD/tag

- 开始前 HEAD：`2d94226f51c772bc838de1e0c65259cfaf710f85`
- 开始前 tag：`v0.1.678-local-launcher-zdoc-local-app-v1-ollama-model-run-smoke-test-authorization-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-042-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-AUTHORIZATION-GATE`

实际最近提交：

```text
2d94226 LOCAL-LAUNCHER-042 ollama smoke test authorization
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
2d94226f51c772bc838de1e0c65259cfaf710f85
```

实际开始前 HEAD tag：

```text
v0.1.678-local-launcher-zdoc-local-app-v1-ollama-model-run-smoke-test-authorization-gate
```

结论：HEAD/tag 与 042 基线一致。

## 7. 工作区 clean 确认结果

开始前 `git status --short` 无输出。

smoke test 执行后、写入 043 docs 前再次执行 `git status --short` 无输出。

结论：工作区在写入本文件前 clean，smoke test 未造成仓库文件变更。

## 8. 040 model selection PASS 复核结果

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-selection-execution-gate-local-launcher-040.md`

复核结果：

1. 040 节点性质为 `Ollama model selection execution gate based only on recorded local inventory`。
2. 040 未执行任何 Ollama 命令。
3. 040 未运行模型。
4. 040 未输入 prompt。
5. 040 仅基于 038 已记录的 8 个本地模型名称提出模型选择建议。
6. 040 记录轻量快速验证候选包含 `qwen3:0.6b`。
7. 040 模型选择判定为 `PASS`。

040 当前 decision 可复核：

```text
LOCAL-LAUNCHER-040 ZDOC LOCAL APP V1 OLLAMA MODEL SELECTION EXECUTION GATE PASSED / MODEL SELECTION RECOMMENDATION COMPLETED BASED ON RECORDED LOCAL INVENTORY / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

## 9. 041 model selection result closed 复核结果

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-selection-result-record-gate-local-launcher-041.md`

复核结果：

1. 041 节点性质为 `Ollama model selection result record only`。
2. 041 已记录 040 Ollama model selection recommendation。
3. 041 已记录 040 模型选择判定 `PASS`。
4. 041 已记录轻量快速候选包含 `qwen3:0.6b` 与 `qwen3:8b`。
5. 041 model selection result closed。
6. 041 未执行 Ollama 命令、未运行模型、未输入 prompt。

041 当前 decision 可复核：

```text
LOCAL-LAUNCHER-041 ZDOC LOCAL APP V1 OLLAMA MODEL SELECTION RESULT RECORD GATE COMPLETED / MODEL SELECTION RECOMMENDATION PASS RECORDED / MODEL SELECTION RESULT CLOSED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

## 10. 042 smoke test authorization 复核结果

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-authorization-gate-local-launcher-042.md`

复核结果：

1. 042 节点性质为 `Ollama model run smoke test authorization boundary and user authorization request only`。
2. 042 明确未来 043 可使用 `qwen3:0.6b` 执行一次最小 smoke test。
3. 042 明确 smoke test prompt 必须无业务含义、无隐私、无真实数据。
4. 042 明确不得读取真实 KG、真实项目资料或真实招标文件。
5. 042 明确不得触发 ZDoc generation/export/write-back。
6. 042 明确不得进入 trial、真实使用或 50 人正式使用。
7. 042 明确 043 执行完成或阻断后必须回报并停止。

042 当前 decision 可复核：

```text
LOCAL-LAUNCHER-042 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST AUTHORIZATION GATE COMPLETED / MODEL RUN SMOKE TEST EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

## 11. 已记录模型清单复核结果

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-inventory-result-record-gate-local-launcher-038.md`

复核结果：

1. 038 记录本地模型清单非空。
2. 038 记录本地模型数量为 8 个。
3. 038 已记录 `qwen3:0.6b`。
4. 038 未额外执行 `ollama list`。
5. 本节点未执行 `ollama list`。

038 已记录的 `qwen3:0.6b` 信息：

```text
qwen3:0.6b / 7df6b6e09427 / 522 MB / 7 weeks ago
```

## 12. Ollama server PID 与监听端口复核结果

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

## 13. smoke test 执行结果

smoke test 模型：

```text
qwen3:0.6b
```

smoke test prompt：

```text
只回复 OK。
```

实际执行命令：

```bash
ollama run qwen3:0.6b "只回复 OK。"
```

执行次数：1 次。

退出码：`0`。

响应耗时：约 `1.2560 seconds`。

是否返回响应：是。

非敏感响应摘要：

```text
输出包含非敏感 thinking 文本，最终返回 OK；响应超过 100 字，未复制完整长输出。
```

敏感内容判断：

1. 未发现真实 KG。
2. 未发现真实项目资料。
3. 未发现真实招标文件。
4. 未发现隐私数据、secrets、tokens 或 credentials。
5. 输出为通用测试响应摘要，可形成安全摘要。

## 14. 实际执行命令清单

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
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-authorization-gate-local-launcher-042.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-model-selection-result-record-gate-local-launcher-041.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-model-selection-execution-gate-local-launcher-040.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-model-inventory-result-record-gate-local-launcher-038.md
sed -n '261,520p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-authorization-gate-local-launcher-042.md
sed -n '261,520p' docs/zdoc-local-launcher-v1-ollama-model-selection-execution-gate-local-launcher-040.md
```

本节点实际执行的 Ollama server 状态复核命令：

```bash
pgrep -fl "ollama"
lsof -nP -iTCP -sTCP:LISTEN
```

本节点实际执行的唯一 Ollama 模型运行命令：

```bash
ollama run qwen3:0.6b "只回复 OK。"
```

本节点在 smoke test 后、写入 043 docs 前实际执行：

```bash
git status --short
```

## 15. 禁止项确认

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
57. 未进入 `LOCAL-LAUNCHER-044`。

## 16. PASS 判定

判定：`PASS / MODEL RUN SMOKE TEST COMPLETED`。

判定依据：

1. 仓库路径正确。
2. 分支为 `main`。
3. HEAD/tag 与 042 基线一致。
4. 工作区 clean。
5. 040 model selection `PASS` 已复核。
6. 041 model selection result closed 已复核。
7. 042 smoke test authorization boundary 已复核。
8. Ollama server PID 与监听端口已复核。
9. `qwen3:0.6b` 在 038 已记录模型清单中。
10. 仅执行 1 次 `ollama run qwen3:0.6b "只回复 OK。"`。
11. 模型返回响应。
12. 已记录响应耗时。
13. 已记录非敏感响应摘要。
14. 未执行 `ollama list`。
15. 未执行 `ollama pull`。
16. 未执行 `ollama serve`。
17. 未运行多个模型。
18. 未使用真实业务 prompt。
19. 未使用真实技术标内容。
20. 未使用真实项目资料内容。
21. 未读取真实 KG / 真实项目资料。
22. 未触发 ZDoc generation/export/write-back。
23. 未写 output/job/export。
24. 未进入 trial、真实使用、50 人正式使用。
25. 未进入下一节点。

## 17. 当前 Decision

`LOCAL-LAUNCHER-043 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST EXECUTION GATE PASSED / MINIMAL MODEL RUN SMOKE TEST COMPLETED WITH QWEN3 0.6B / NON-SENSITIVE RESPONSE SUMMARY RECORDED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED`

## 18. 后续限制

后续必须保持以下限制：

1. 044 不得执行 `ollama run`。
2. 044 不得输入 prompt。
3. 044 不得再次执行模型推理。
4. 044 只能记录 043 smoke test 结果。
5. trial / generation / export / write-back 必须另设授权门。
6. 真实 KG / 真实项目资料读取必须另设授权门。
7. 当前 ZDoc 服务不得被停止或重启，除非另行授权。
8. 当前 Ollama server 不得被停止或重启，除非另行授权。
9. 不得自行扩大授权。
10. 不得运行其他模型。
11. 不得 pull 模型。

## 19. 下一节点建议

若 ChatGPT 总控师审核通过，下一节点建议为：

`LOCAL-LAUNCHER-044-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-RESULT-RECORD-GATE`

044 只能记录 smoke test 结果，不得再次运行模型。

## 20. 明确说明未进入 `LOCAL-LAUNCHER-044`

本节点未进入 `LOCAL-LAUNCHER-044`。
