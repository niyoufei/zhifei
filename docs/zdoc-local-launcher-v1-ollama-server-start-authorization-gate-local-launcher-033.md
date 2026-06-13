# LOCAL-LAUNCHER-033 ZDoc Local App V1 Ollama Server Start Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-033-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-START-AUTHORIZATION-GATE`

本节点性质：

`Ollama server start authorization boundary and user authorization request only`

当前基线：

- 开始前 HEAD：`59bfe336d6b45f82ce26872b7899eaa2e3522fba`
- 开始前 tag：`v0.1.668-local-launcher-zdoc-local-app-v1-ollama-readiness-blocker-review-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-032-ZDOC-LOCAL-APP-V1-OLLAMA-READINESS-BLOCKER-REVIEW-GATE`

实际最近提交：

```text
59bfe33 LOCAL-LAUNCHER-032 ollama readiness blocker review
```

上游节点状态：

1. `LOCAL-LAUNCHER-028-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-EXECUTION-GATE`：`PASS`。
2. `LOCAL-LAUNCHER-029-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-RESULT-RECORD-GATE`：completed / endpoint health check result closed。
3. `LOCAL-LAUNCHER-030-ZDOC-LOCAL-APP-V1-OLLAMA-READINESS-AUTHORIZATION-GATE`：completed / Ollama readiness execution authorization boundary documented。
4. `LOCAL-LAUNCHER-031-ZDOC-LOCAL-APP-V1-OLLAMA-READINESS-EXECUTION-GATE`：`BLOCKED`。
5. `LOCAL-LAUNCHER-032-ZDOC-LOCAL-APP-V1-OLLAMA-READINESS-BLOCKER-REVIEW-GATE`：completed / Ollama readiness blocker recorded。

031 Ollama readiness 判定：

```text
BLOCKED
```

032 Ollama readiness blocker review 完成状态：

```text
COMPLETED
```

本节点明确不执行 `ollama serve`，不启动 Ollama server，不执行 `ollama list`，不执行 `ollama --version`，不执行 `command -v ollama` 或 `which ollama`，不运行模型，不输入 prompt。

## 2. 当前系统状态判断

当前系统状态如下：

1. ZDoc 本地服务 controlled start 已完成。
2. post-start status 已 `PASS`。
3. endpoint health check 已 `PASS`。
4. endpoint health check result 已闭环。
5. Ollama CLI 存在。
6. Ollama client version 已确认，为 `0.21.2`。
7. Ollama server 未连接。
8. 本地模型清单未确认。
9. 当前不具备模型运行授权条件。
10. 当前不具备 trial / generation / export / write-back 条件。

状态边界说明：

1. ZDoc endpoint health check 与 Ollama readiness 是两个独立边界。
2. 031 阻断不改变 028/029 已记录的 ZDoc 基础服务健康检查结果。
3. 031 阻断仅说明当前无法在未启动 Ollama server 的情况下确认本地模型清单。
4. 本节点只记录未来启动 Ollama server 的授权边界，不执行启动。

## 3. 031/032 阻断事实摘要

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-readiness-execution-gate-local-launcher-031.md`
2. `docs/zdoc-local-launcher-v1-ollama-readiness-blocker-review-gate-local-launcher-032.md`

031/032 阻断事实如下：

1. `ollama` CLI 路径：`/opt/homebrew/bin/ollama`。
2. Ollama client version：`0.21.2`。
3. `ollama list` 在 031 授权范围内执行。
4. `ollama list` 未能获取模型清单。
5. 阻断原因：无法连接运行中的 Ollama server。
6. `ollama serve` 在 031/032 均未授权。
7. `ollama serve` 未执行。
8. 模型清单为空/非空无法判断。

031 记录的 `ollama list` 阻断摘要：

```text
Error: could not connect to ollama server, run 'ollama serve' to start it
```

032 记录的 blocker review 结论：

```text
Ollama CLI exists but server connection not confirmed
```

复核结论：未来若要继续确认 Ollama readiness，应先通过独立授权门决定是否允许启动 Ollama server；不得在本节点直接执行 `ollama serve`。

## 4. 当前授权状态

当前授权状态如下：

1. 当前仅授权执行 `LOCAL-LAUNCHER-033` docs-only 授权边界记录。
2. 当前未授权执行 `LOCAL-LAUNCHER-034`。
3. 当前未授权执行 `ollama serve`。
4. 当前未授权启动 Ollama server。
5. 当前未授权执行 `ollama list`。
6. 当前未授权执行 `ollama run`。
7. 当前未授权执行 `ollama pull`。
8. 当前未授权执行任何 Ollama 模型命令。
9. 当前未授权模型加载。
10. 当前未授权模型推理。
11. 当前未授权 prompt 输入。
12. 当前未授权模型下载、删除、创建。
13. 当前未授权读取真实 KG。
14. 当前未授权读取真实项目资料。
15. 当前未授权读取真实招标文件。
16. 当前未授权读取 `.env` / secrets / tokens / credentials。
17. 当前未授权 trial。
18. 当前未授权 generation / export / write-back。
19. 当前未授权 ZBid 写回。
20. 当前未授权进入真实使用或 50 人正式使用。

## 5. Ollama server start 的定义边界

Ollama server start 必须按以下层级分离：

1. `Ollama server start authorization gate`：仅记录授权边界，不执行 `ollama serve`。
2. `Ollama server start execution gate`：未来如获用户明确授权，才可执行 `ollama serve`。
3. `Ollama server post-start status record gate`：记录 Ollama server 启动后状态。
4. `Ollama model inventory authorization gate`：授权重新执行 `ollama list`。
5. `Ollama model inventory execution gate`：执行模型清单确认。
6. `Ollama model selection authorization gate`：模型选择授权。
7. `Ollama model run authorization gate`：模型运行授权。
8. `Ollama model run execution gate`：模型运行执行。
9. `trial authorization gate`：小范围试用授权。
10. `generation/export/write-back authorization gate`：生成、导出、写回授权。
11. `50-user deployment readiness gate`：50 人正式部署准备，不得提前进入。

本节点只处于第 1 层：`Ollama server start authorization gate`。

## 6. 未来 034 可授权范围草案

以下仅为未来 `LOCAL-LAUNCHER-034` 的可授权范围草案，本节点不执行。

未来若用户明确授权 `LOCAL-LAUNCHER-034`，Ollama server start execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 031 `BLOCKED`。
6. 复核 032 blocker review。
7. 复核 `ollama` CLI 路径与 client version。
8. 执行 `ollama serve` 启动 Ollama server。
9. 观察 `ollama serve` stdout/stderr 中的非敏感启动状态。
10. 确认 Ollama server 进程是否存在。
11. 确认 Ollama server 本地监听端口是否存在。
12. 记录 PID、端口、启动时间、命令来源。
13. 不执行 `ollama list`，除非后续另设授权。
14. 不执行 `ollama run`。
15. 不输入 prompt。
16. 不下载模型。
17. 不读取真实 KG / 真实项目资料。
18. 不触发 generation/export/write-back。
19. 启动完成或阻断后立即回报并停止。

未来 034 即使被授权，也只是启动 Ollama server，不等于授权模型清单检查，更不等于授权模型运行。

## 7. 未来 034 禁止范围草案

未来 034 仍应禁止：

1. `ollama list`，除非后续另设授权。
2. `ollama run`。
3. `ollama pull`。
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
30. 停止 Ollama server，除非后续另行授权。

## 8. Ollama server start 阻断条件

未来 034 如出现以下任一情况，应判定 `BLOCKED`，不得启动 Ollama server 或不得继续：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 031 `BLOCKED` 无法复核。
4. 032 blocker review 无法复核。
5. `ollama` CLI 路径无法复核。
6. Ollama client version 无法复核。
7. `ollama serve` 命令需要安装、下载、pull 或更新模型。
8. `ollama serve` 触发模型加载或推理。
9. `ollama serve` 要求输入 prompt。
10. `ollama serve` 输出疑似包含敏感内容且无法形成安全摘要。
11. `ollama serve` 需要读取 `.env` / secrets。
12. `ollama serve` 需要读取真实 KG。
13. `ollama serve` 需要读取真实项目资料。
14. `ollama serve` 会触发 generation/export/write-back。
15. 启动需要修改系统配置。
16. 启动需要安装、下载、pull 或更新模型。
17. 端口被未知进程占用且无法在授权范围内确认。
18. 无法在授权范围内确认边界。

## 9. 用户授权文本模板

后续如需进入 `LOCAL-LAUNCHER-034`，用户可直接复制以下授权文本：

`我明确授权 LOCAL-LAUNCHER-034 执行 Ollama server start execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 031 BLOCKED、复核 032 blocker review、复核 ollama CLI 路径与 client version、执行 ollama serve 启动 Ollama server、观察 ollama serve stdout/stderr 中的非敏感启动状态、确认 Ollama server 进程是否存在、确认 Ollama server 本地监听端口是否存在、记录 PID/端口/启动时间/命令来源。严格禁止 ollama list、ollama run、ollama pull、ollama create、ollama rm、任何模型推理、任何 prompt 输入、模型下载、模型删除、模型创建、读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 .env/secrets/tokens/credentials、读取 registration/metadata/proof/manifest/sample 实例、读取 output/job/export 正文、触发 generation/export/write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用。若 ollama serve 需要安装、下载、pull、运行模型、输入 prompt、读取真实数据或触发生成/导出/写回，必须判定 BLOCKED 并停止。启动完成或阻断后必须回报并停止，不得进入下一节点。`

## 10. 进入 034 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-034-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-START-EXECUTION-GATE`

若用户未授权，则 hold。

本节点不得进入 `LOCAL-LAUNCHER-034`。

## 11. 禁止项确认

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
12. 未访问 endpoint。
13. 未执行 curl / HTTP request。
14. 未再次访问 `/health`。
15. 未执行 `command -v ollama`。
16. 未执行 `which ollama`。
17. 未执行 `ollama --version`。
18. 未执行 `ollama list`。
19. 未执行 `ollama serve`。
20. 未启动 Ollama server。
21. 未执行 `ollama run`。
22. 未执行 `ollama pull`。
23. 未执行任何 Ollama 模型命令。
24. 未执行模型推理。
25. 未输入 prompt。
26. 未下载/删除/创建模型。
27. 未读取真实 KG。
28. 未读取真实项目资料。
29. 未读取真实招标文件。
30. 未读取 `.env` / secrets / tokens / credentials。
31. 未读取 registration / metadata / proof / manifest / sample 实例。
32. 未读取 output/job/export 正文。
33. 未读取日志正文。
34. 未触发 generation/export/write-back。
35. 未写 output/job/export。
36. 未进入 trial。
37. 未进入真实使用。
38. 未进入 50 人正式使用。
39. 未进入 `LOCAL-LAUNCHER-034`。

## 12. 实际执行命令清单

LOCAL-LAUNCHER-033 只执行 Git 状态确认和指定文档只读查看：

```bash
git status --short
git log -1 --format=%H
git log -1 --oneline
git tag --points-at HEAD
git diff --check
git diff --cached --check
sed -n '1,320p' docs/zdoc-local-launcher-v1-ollama-readiness-blocker-review-gate-local-launcher-032.md
sed -n '1,320p' docs/zdoc-local-launcher-v1-ollama-readiness-execution-gate-local-launcher-031.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-readiness-authorization-gate-local-launcher-030.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-endpoint-health-check-result-record-gate-local-launcher-029.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-endpoint-health-check-execution-gate-local-launcher-028.md
```

未执行任何 Ollama 命令、服务命令、endpoint 请求、HTTP request、安装命令、测试、lint、build、真实数据读取、trial、generation、export 或 write-back。

## 13. 当前 Decision

`LOCAL-LAUNCHER-033 ZDOC LOCAL APP V1 OLLAMA SERVER START AUTHORIZATION GATE COMPLETED / OLLAMA SERVER START EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA SERVE EXECUTED / NO OLLAMA LIST EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO MODEL DOWNLOAD / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 14. 下一节点建议

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-034-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-START-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 034。
4. 034 即使后续被授权，也仅允许启动 Ollama server。
5. `ollama list` 必须另设后续授权门。
6. 模型运行必须另设授权门。
7. trial / generation / export / write-back 必须另设授权门。
8. 真实 KG / 真实项目资料读取必须另设授权门。
9. 50 人正式使用必须另设 readiness 与 deployment gate。

## 15. 明确说明未进入 `LOCAL-LAUNCHER-034`

本节点未进入 `LOCAL-LAUNCHER-034`。
