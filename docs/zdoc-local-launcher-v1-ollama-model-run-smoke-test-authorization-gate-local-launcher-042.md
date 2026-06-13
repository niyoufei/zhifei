# LOCAL-LAUNCHER-042 ZDoc Local App V1 Ollama Model Run Smoke Test Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-042-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-AUTHORIZATION-GATE`

本节点性质：

`Ollama model run smoke test authorization boundary and user authorization request only`

本节点目标：

记录未来是否可以执行首次最小模型运行 smoke test 的授权边界、禁止事项、阻断条件、用户授权文本模板和后续进入条件。

本节点不执行 `ollama run`，不执行任何 Ollama 命令，不运行模型，不输入 prompt。

当前基线：

- 开始前 HEAD：`a8d83a85f5b35142a63618f0123c3f8c68fbbf90`
- 开始前 tag：`v0.1.677-local-launcher-zdoc-local-app-v1-ollama-model-selection-result-record-gate`
- 上一节点：`LOCAL-LAUNCHER-041-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-RESULT-RECORD-GATE`

实际最近提交：

```text
a8d83a8 LOCAL-LAUNCHER-041 ollama model selection result record
```

上游节点状态：

1. `LOCAL-LAUNCHER-037-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-INVENTORY-EXECUTION-GATE`：`PASS`。
2. `LOCAL-LAUNCHER-038-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-INVENTORY-RESULT-RECORD-GATE`：completed / inventory result closed。
3. `LOCAL-LAUNCHER-039-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-AUTHORIZATION-GATE`：completed / model selection authorization boundary documented。
4. `LOCAL-LAUNCHER-040-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-EXECUTION-GATE`：`PASS`。
5. `LOCAL-LAUNCHER-041-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-RESULT-RECORD-GATE`：completed / model selection result closed。

关键状态：

1. 037 Ollama model inventory 判定：`PASS`。
2. 038 inventory result closed。
3. 040 Ollama model selection 判定：`PASS`。
4. 041 model selection result closed。

## 2. 当前系统状态判断

当前系统状态如下：

1. ZDoc 本地服务 controlled start 已完成。
2. ZDoc post-start status 已 `PASS`。
3. ZDoc endpoint health check 已 `PASS`。
4. endpoint health check result 已闭环。
5. Ollama server 已启动。
6. Ollama server post-start status 已 `PASS`。
7. 本地模型清单已确认。
8. 模型清单非空。
9. 模型选择建议已完成。
10. 当前仍不具备 trial / generation / export / write-back 条件。
11. 当前仍不具备真实 KG / 真实项目资料读取条件。

说明：本节点未重新探测服务、进程、端口、endpoint 或 Ollama；上述状态来自 037、038、039、040、041 文档链的只读复核。

## 3. 041 模型选择结果摘要

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-selection-result-record-gate-local-launcher-041.md`

041 已记录的模型选择结果如下：

1. 默认通用模型建议：`qwen3:30b`。
2. 编码 / 工程辅助模型建议：`qwen3-coder:30b`。
3. 大模型高质量候选：
   - `qwen3-next:80b-a3b-instruct-q8_0`
   - `qwen3.6:35b`
4. 轻量快速候选：
   - `qwen3:0.6b`
   - `qwen3:8b`
5. 备选模型：
   - `qwen3:14b`
   - `deepseek-r1:32b`

重要限制：

1. 上述建议不是 benchmark 结果。
2. 上述建议不是模型运行结果。
3. 上述建议不是 prompt 测试结果。
4. 后续模型运行前必须另设授权门和执行门。

041 当前 decision 可复核：

```text
LOCAL-LAUNCHER-041 ZDOC LOCAL APP V1 OLLAMA MODEL SELECTION RESULT RECORD GATE COMPLETED / MODEL SELECTION RECOMMENDATION PASS RECORDED / MODEL SELECTION RESULT CLOSED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED
```

## 4. 首次 smoke test 推荐策略

首次模型运行 smoke test 建议优先使用轻量快速候选。

首次 smoke test 建议候选模型：

`qwen3:0.6b`

备选 smoke test 模型：

`qwen3:8b`

原因：

1. 降低首次运行资源占用。
2. 降低超时风险。
3. 便于验证 Ollama server、模型加载、最小响应链路。
4. 不接入真实 KG。
5. 不接入真实项目资料。
6. 不触发 ZDoc generation/export/write-back。

边界说明：

1. 上述内容仅为授权边界建议。
2. 上述内容不构成执行授权。
3. 本节点不运行 `qwen3:0.6b`。
4. 本节点不运行 `qwen3:8b`。
5. 本节点不输入任何 prompt。

## 5. 未来 043 可授权范围草案

以下仅为未来 `LOCAL-LAUNCHER-043` 的可授权范围草案，本节点不执行。

未来若用户明确授权 `LOCAL-LAUNCHER-043`，首次模型运行 smoke test execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 040 model selection `PASS`。
6. 复核 041 model selection result closed。
7. 复核 Ollama server PID 与监听端口。
8. 使用 `qwen3:0.6b` 执行一次最小 smoke test。
9. 仅输入无业务含义、无隐私、无真实数据的最小测试 prompt。
10. 仅记录是否返回响应。
11. 仅记录响应耗时。
12. 仅记录非敏感响应摘要。
13. 不接入 ZDoc generation。
14. 不接入真实 KG。
15. 不接入真实项目资料。
16. 不读取招标文件。
17. 不写 output/job/export。
18. 不进入 trial。
19. 执行完成或阻断后立即回报并停止。

未来 043 即使被授权，也只是一次最小 smoke test，不等于授权 trial，不等于授权 generation/export/write-back，不等于授权真实 KG / 真实项目资料读取。

## 6. 未来 043 禁止范围草案

未来 043 仍应禁止：

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
11. ZBid 写回。
12. trial。
13. 真实使用。
14. 50 人正式使用。
15. 使用真实业务 prompt。
16. 使用真实技术标内容。
17. 使用真实项目资料内容。
18. 运行多个模型。
19. 执行性能 benchmark。
20. 执行长文本生成。
21. 执行模型下载。
22. 执行 `ollama pull`。
23. 执行 `ollama create`。
24. 执行 `ollama rm`。
25. 修改 V0/V1/backend/frontend/config/dependency。
26. 创建脚本、App 包、Tauri/Electron 工程、runtime bridge。
27. 运行测试/lint/build。
28. 停止或重启当前 ZDoc 服务，除非后续另行授权。
29. 停止或重启 Ollama server，除非后续另行授权。

## 7. smoke test 阻断条件

未来 043 如出现以下任一情况，应判定 `BLOCKED`，不得继续：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 040 `PASS` 无法复核。
4. 041 result closed 无法复核。
5. Ollama server PID 或端口无法复核。
6. `qwen3:0.6b` 不在已记录模型清单中。
7. 需要执行 `ollama list` 才能确认模型。
8. 需要执行 `ollama pull` 才能获取模型。
9. 需要读取真实 KG 才能构造 prompt。
10. 需要读取真实项目资料才可构造 prompt。
11. 需要触发 generation/export/write-back 才能判断。
12. smoke test 输出疑似包含敏感内容且无法形成安全摘要。
13. smoke test 需要访问 ZDoc 业务 endpoint。
14. smoke test 需要写 output/job/export。
15. 无法在授权范围内完成最小模型运行。

## 8. 用户授权文本模板

后续如需进入 `LOCAL-LAUNCHER-043`，用户可直接复制以下授权文本：

`我明确授权 LOCAL-LAUNCHER-043 执行 Ollama model run smoke test execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 040 model selection PASS、复核 041 model selection result closed、复核 Ollama server PID 与监听端口、使用 qwen3:0.6b 执行一次最小 smoke test、仅输入无业务含义/无隐私/无真实数据的最小测试 prompt、仅记录是否返回响应、响应耗时、非敏感响应摘要。严格禁止读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 .env/secrets/tokens/credentials、读取 registration/metadata/proof/manifest/sample 实例、读取 output/job/export 正文、触发 ZDoc generation、触发 export、触发 write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用、使用真实业务 prompt、使用真实技术标内容、使用真实项目资料内容、运行多个模型、执行性能 benchmark、执行长文本生成、执行模型下载、执行 ollama pull/create/rm、修改 V0/V1/backend/frontend/config/dependency。若 smoke test 需要真实数据、业务 prompt、生成导出写回、下载模型、运行多个模型或访问业务 endpoint，必须判定 BLOCKED 并停止。执行完成或阻断后必须回报并停止，不得进入下一节点。`

## 9. 进入 043 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-043-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-EXECUTION-GATE`

若用户未授权，则 hold。

本节点不得进入 `LOCAL-LAUNCHER-043`。

## 10. 禁止项确认

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
24. 未执行 `command -v ollama`。
25. 未执行 `which ollama`。
26. 未执行 `ollama --version`。
27. 未再次执行 `ollama list`。
28. 未执行 `ollama run`。
29. 未执行 `ollama pull`。
30. 未执行 `ollama serve`。
31. 未执行 `ollama create`。
32. 未执行 `ollama rm`。
33. 未执行 `ollama cp`。
34. 未执行任何 Ollama 模型命令。
35. 未执行模型推理。
36. 未输入 prompt。
37. 未下载/删除/创建模型。
38. 未读取真实 KG。
39. 未读取真实项目资料。
40. 未读取真实招标文件。
41. 未读取用户隐私或业务数据。
42. 未读取 `.env` / `.env.*` / secrets / tokens / credentials / keys / private 配置。
43. 未读取 registration / metadata / proof / manifest / sample 实例。
44. 未读取 output/job/export 正文。
45. 未读取日志正文。
46. 未触发 generation/export/write-back。
47. 未写 output/job/export。
48. 未进入 trial。
49. 未进入真实使用。
50. 未进入 50 人正式使用。
51. 未进入 `LOCAL-LAUNCHER-043`。

## 11. 当前 Decision

`LOCAL-LAUNCHER-042 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST AUTHORIZATION GATE COMPLETED / MODEL RUN SMOKE TEST EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 12. 下一节点建议

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-043-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-RUN-SMOKE-TEST-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 043。
4. 043 即使后续被授权，也仅允许一次最小 smoke test。
5. trial / generation / export / write-back 必须另设授权门。
6. 真实 KG / 真实项目资料读取必须另设授权门。
7. 50 人正式使用必须另设 readiness 与 deployment gate。

## 13. 明确说明未进入 `LOCAL-LAUNCHER-043`

本节点未进入 `LOCAL-LAUNCHER-043`。
