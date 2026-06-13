# LOCAL-LAUNCHER-030 ZDoc Local App V1 Ollama Readiness Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-030-ZDOC-LOCAL-APP-V1-OLLAMA-READINESS-AUTHORIZATION-GATE`

本节点性质：

`Ollama readiness authorization boundary and user authorization request only`

当前基线：

- 开始前 HEAD：`eb98f6e939fae81aaea3192c4286a5fdcdd3cd69`
- 开始前 tag：`v0.1.665-local-launcher-zdoc-local-app-v1-endpoint-health-check-result-record-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-029-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-RESULT-RECORD-GATE`

上游节点 025、026、027、028、029 状态：

1. `LOCAL-LAUNCHER-025-ZDOC-LOCAL-APP-V1-CONTROLLED-START-EXECUTION-GATE`：`STARTED`。
2. `LOCAL-LAUNCHER-026-ZDOC-LOCAL-APP-V1-POST-START-STATUS-RECORD-GATE`：`PASS`。
3. `LOCAL-LAUNCHER-027-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-AUTHORIZATION-GATE`：completed。
4. `LOCAL-LAUNCHER-028-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-EXECUTION-GATE`：`PASS`。
5. `LOCAL-LAUNCHER-029-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-RESULT-RECORD-GATE`：completed / endpoint health check result closed。

关键状态摘要：

- 025 controlled start 判定：`STARTED`。
- 026 post-start status 判定：`PASS`。
- 028 endpoint health check 判定：`PASS`。
- 029 endpoint health check result record：已闭环。
- 服务 PID：`21727`。
- 监听端口：`127.0.0.1:8000`。
- endpoint health check 已通过：`GET http://127.0.0.1:8000/health`，HTTP `200`。
- 当前未授权 Ollama。

本节点明确不运行 Ollama，不执行 `ollama list`，不执行任何 Ollama 模型命令。

## 2. 当前授权状态

当前授权状态如下：

1. 当前仅授权执行 `LOCAL-LAUNCHER-030` docs-only 授权边界记录。
2. 当前未授权执行 `LOCAL-LAUNCHER-031`。
3. 当前未授权运行 Ollama。
4. 当前未授权执行 `ollama list`。
5. 当前未授权执行 `ollama --version`。
6. 当前未授权执行 `which ollama`。
7. 当前未授权执行任何 Ollama 模型命令。
8. 当前未授权模型加载。
9. 当前未授权模型推理。
10. 当前未授权模型下载 / pull。
11. 当前未授权模型删除 / rm。
12. 当前未授权 `ollama serve`。
13. 当前未授权读取真实 KG。
14. 当前未授权读取真实项目资料。
15. 当前未授权读取真实招标文件。
16. 当前未授权 trial。
17. 当前未授权 generation / export / write-back。
18. 当前未授权 ZBid 写回。
19. 当前未授权进入真实使用或 50 人正式使用。

## 3. Ollama Readiness 定义边界

Ollama readiness 必须按以下层级分离：

1. `Ollama readiness authorization gate`：仅记录授权边界，不运行 Ollama。
2. `Ollama readiness execution gate`：未来如获用户明确授权，才可执行最小 Ollama readiness 检查。
3. `Ollama model inventory result record gate`：记录模型清单检查结果，不运行模型推理。
4. `Ollama model run authorization gate`：模型运行授权。
5. `Ollama model run execution gate`：模型运行执行。
6. `trial authorization gate`：小范围试用授权。
7. `trial execution gate`：小范围试用执行。
8. `generation/export/write-back authorization gate`：生成、导出、写回授权。
9. `50-user deployment readiness gate`：50 人正式部署准备，不得提前进入。

本节点只处于第 1 层：`Ollama readiness authorization gate`。

## 4. 未来 031 可授权范围草案

以下仅为未来 `LOCAL-LAUNCHER-031` 的可授权范围草案，本节点不执行。

未来若用户明确授权 `LOCAL-LAUNCHER-031`，Ollama readiness execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 028 endpoint health check `PASS`。
6. 复核 029 endpoint result closed。
7. 检查本机是否存在 `ollama` 可执行程序。
8. 检查 Ollama 版本。
9. 执行 `ollama list` 仅用于确认本地模型清单。
10. 仅记录模型名称、大小、修改时间等非推理信息。
11. 不执行 `ollama run`。
12. 不执行模型推理。
13. 不发送 prompt。
14. 不加载真实 KG。
15. 不读取真实项目资料。
16. 不触发 generation/export/write-back。
17. 检查完成后立即回报并停止。

未来 031 即使被授权，也仍不得运行模型推理，不得进行 trial，不得读取真实 KG / 真实项目资料，不得触发 generation/export/write-back。

## 5. 未来 031 禁止范围草案

未来 `LOCAL-LAUNCHER-031` 仍应禁止：

1. `ollama run`。
2. `ollama pull`。
3. `ollama serve`。
4. `ollama create`。
5. `ollama rm`。
6. `ollama cp`。
7. 任何模型推理。
8. 任何 prompt 输入。
9. 任何模型下载。
10. 任何模型删除。
11. 任何模型创建。
12. 读取真实 KG。
13. 读取真实项目资料。
14. 读取真实招标文件。
15. 读取用户隐私或业务数据。
16. 读取 `.env` / secrets / tokens / credentials。
17. 读取 registration / metadata / proof / manifest / sample 实例。
18. 读取 output/job/export 正文。
19. generation。
20. export。
21. write-back。
22. ZBid 写回。
23. trial。
24. 真实使用。
25. 50 人正式使用。
26. 修改 V0/V1/backend/frontend/config/dependency。
27. 创建脚本、App 包、Tauri/Electron 工程、runtime bridge。
28. 运行测试/lint/build。
29. 停止或重启当前 ZDoc 服务，除非后续另行授权。

## 6. Ollama Readiness 阻断条件

未来 `LOCAL-LAUNCHER-031` 如出现以下任一情况，应判定 `BLOCKED`，不得继续：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 028 `PASS` 无法复核。
4. 029 result closed 无法复核。
5. `ollama` 命令不可用。
6. `ollama list` 需要启动或安装额外组件。
7. `ollama list` 触发模型加载或推理。
8. `ollama list` 输出疑似包含敏感内容且无法形成安全摘要。
9. Ollama 检查需要读取 `.env` / secrets。
10. Ollama 检查需要读取真实 KG。
11. Ollama 检查需要读取真实项目资料。
12. Ollama 检查会触发 generation/export/write-back。
13. 检查需要修改系统配置。
14. 检查需要安装、下载、pull 或更新模型。
15. 无法在授权范围内确认边界。

## 7. 用户授权文本模板

后续如需进入 `LOCAL-LAUNCHER-031`，用户可直接复制以下授权文本：

`我明确授权 LOCAL-LAUNCHER-031 执行 Ollama readiness execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 028 endpoint health check PASS、复核 029 endpoint result closed、检查本机是否存在 ollama 可执行程序、检查 Ollama 版本、执行 ollama list 仅用于确认本地模型清单、仅记录模型名称/大小/修改时间等非推理信息。严格禁止 ollama run、ollama pull、ollama serve、ollama create、ollama rm、任何模型推理、任何 prompt 输入、模型下载、模型删除、模型创建、读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 .env/secrets/tokens/credentials、读取 registration/metadata/proof/manifest/sample 实例、读取 output/job/export 正文、触发 generation/export/write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用。若 Ollama 检查需要安装、下载、pull、运行模型、输入 prompt、读取真实数据或触发生成/导出/写回，必须判定 BLOCKED 并停止。检查完成或阻断后必须回报并停止，不得进入下一节点。`

## 8. 进入 031 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-031-ZDOC-LOCAL-APP-V1-OLLAMA-READINESS-EXECUTION-GATE`

若用户未授权，则 hold。

本节点不得进入 `LOCAL-LAUNCHER-031`。

## 9. 禁止项确认

本节点确认：

1. 未修改 V1 页面产物。
2. 未修改 V0。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未运行 npm/yarn/pnpm/pip。
7. 未运行测试/lint/build。
8. 未打开 HTML 页面。
9. 未启动新服务。
10. 未重启服务。
11. 未停止服务。
12. 未访问 endpoint。
13. 未执行 curl / HTTP request。
14. 未再次访问 `/health`。
15. 未运行 Ollama。
16. 未执行 `which ollama`。
17. 未执行 `ollama --version`。
18. 未执行 `ollama list`。
19. 未执行任何 Ollama 模型命令。
20. 未读取真实 KG。
21. 未读取真实项目资料。
22. 未读取真实招标文件。
23. 未读取 `.env` / secrets / tokens / credentials。
24. 未读取 registration / metadata / proof / manifest / sample 实例。
25. 未读取 output/job/export 正文。
26. 未读取日志正文。
27. 未触发 generation/export/write-back。
28. 未写 output/job/export。
29. 未进入 trial。
30. 未进入真实使用。
31. 未进入 50 人正式使用。
32. 未进入 `LOCAL-LAUNCHER-031`。

## 10. 当前 Decision

`LOCAL-LAUNCHER-030 ZDOC LOCAL APP V1 OLLAMA READINESS AUTHORIZATION GATE COMPLETED / OLLAMA READINESS EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO OLLAMA LIST EXECUTED / NO MODEL RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 11. 下一节点建议

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-031-ZDOC-LOCAL-APP-V1-OLLAMA-READINESS-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 031。
4. 031 即使后续被授权，也仅允许 Ollama readiness 检查。
5. 模型运行必须另设授权门。
6. trial / generation / export / write-back 必须另设授权门。
7. 真实 KG / 真实项目资料读取必须另设授权门。
8. 50 人正式使用必须另设 readiness 与 deployment gate。
