# LOCAL-LAUNCHER-039 ZDoc Local App V1 Ollama Model Selection Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-039-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-AUTHORIZATION-GATE`

本节点性质：

`Ollama model selection authorization boundary and user authorization request only`

本节点目标：

记录未来是否可以执行本地模型选择的授权边界、禁止事项、阻断条件、用户授权文本模板和后续进入条件。

本节点不执行模型选择，不运行模型，不输入 prompt。

当前基线：

- 开始前 HEAD：`f2eb353ba1688e1b5791a981da75169ca12d9169`
- 开始前 tag：`v0.1.674-local-launcher-zdoc-local-app-v1-ollama-model-inventory-result-record-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-038-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-INVENTORY-RESULT-RECORD-GATE`

实际最近提交：

```text
f2eb353 LOCAL-LAUNCHER-038 ollama inventory result record
```

上游节点状态：

1. `LOCAL-LAUNCHER-034-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-START-EXECUTION-GATE`：`STARTED`。
2. `LOCAL-LAUNCHER-035-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-POST-START-STATUS-RECORD-GATE`：`PASS`。
3. `LOCAL-LAUNCHER-036-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-INVENTORY-AUTHORIZATION-GATE`：completed / model inventory execution authorization boundary documented。
4. `LOCAL-LAUNCHER-037-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-INVENTORY-EXECUTION-GATE`：`PASS`。
5. `LOCAL-LAUNCHER-038-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-INVENTORY-RESULT-RECORD-GATE`：completed / inventory result closed。

关键状态：

1. 034 Ollama server start 判定：`STARTED`。
2. 035 Ollama server post-start status 判定：`PASS`。
3. 037 Ollama model inventory 判定：`PASS`。
4. 038 Ollama model inventory result record 完成状态：completed / closed。

## 2. 当前系统状态判断

当前系统状态如下：

1. ZDoc 本地服务 controlled start 已完成。
2. ZDoc post-start status 已 `PASS`。
3. ZDoc endpoint health check 已 `PASS`。
4. endpoint health check result 已闭环。
5. Ollama server 已启动。
6. Ollama server post-start status 已 `PASS`。
7. Ollama server PID：`83676`。
8. Ollama server 监听端口：`127.0.0.1:11434`。
9. 本地模型清单已确认。
10. 模型清单非空。
11. 当前仍不具备模型运行授权条件。
12. 当前仍不具备 trial / generation / export / write-back 条件。
13. 当前仍不具备真实 KG / 真实项目资料读取条件。

说明：本节点未重新探测服务、进程、端口或 endpoint；上述状态来自 034、035、036、037、038 文档链的只读复核。

## 3. 038 模型清单摘要

已只读复核：

`docs/zdoc-local-launcher-v1-ollama-model-inventory-result-record-gate-local-launcher-038.md`

模型清单摘要如下：

1. 本地模型数量：8 个。
2. 本地模型清单：
   - `qwen3:30b`
   - `qwen3.6:35b`
   - `qwen3-next:80b-a3b-instruct-q8_0`
   - `qwen3-coder:30b`
   - `deepseek-r1:32b`
   - `qwen3:14b`
   - `qwen3:8b`
   - `qwen3:0.6b`
3. 038 仅记录模型清单结果。
4. 038 未运行模型。
5. 038 未输入 prompt。
6. 038 未触发 generation/export/write-back。

## 4. Ollama model selection 的定义边界

Ollama model selection 必须按以下层级分离：

1. `Ollama model selection authorization gate`：仅记录授权边界，不选择模型。
2. `Ollama model selection execution gate`：未来如获用户明确授权，才可基于已确认清单提出模型选择建议。
3. `Ollama model selection result record gate`：记录模型选择结果。
4. `Ollama model run authorization gate`：模型运行授权。
5. `Ollama model run execution gate`：模型运行执行。
6. `trial authorization gate`：小范围试用授权。
7. `generation/export/write-back authorization gate`：生成、导出、写回授权。
8. `real KG / real project data authorization gate`：真实 KG / 真实项目资料读取授权。
9. `50-user deployment readiness gate`：50 人正式部署准备，不得提前进入。

本节点只处于第 1 层：`Ollama model selection authorization gate`。

## 5. 未来 040 可授权范围草案

以下仅为未来 `LOCAL-LAUNCHER-040` 的可授权范围草案，本节点不执行。

未来若用户明确授权 `LOCAL-LAUNCHER-040`，Ollama model selection execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 037 Ollama model inventory `PASS`。
6. 复核 038 inventory result closed。
7. 基于 038 已记录的 8 个本地模型名称进行模型选择分析。
8. 按用途提出模型分层建议，例如默认通用模型、编码/工程辅助模型、大模型高质量候选、轻量快速候选、备选模型。
9. 说明每个候选模型适合的 ZDoc 场景。
10. 说明后续模型运行前仍需单独授权。
11. 不执行任何 Ollama 命令。
12. 不执行 `ollama list`。
13. 不执行 `ollama run`。
14. 不输入 prompt。
15. 不运行模型。
16. 不读取真实 KG / 真实项目资料。
17. 不触发 generation/export/write-back。
18. 完成后立即回报并停止。

未来 040 即使被授权，也只是模型选择建议，不等于授权模型运行，不等于授权 trial，不等于授权 generation/export/write-back。

## 6. 未来 040 禁止范围草案

未来 040 仍应禁止：

1. `ollama list`。
2. `ollama run`。
3. `ollama pull`。
4. `ollama serve`。
5. `ollama create`。
6. `ollama rm`。
7. `ollama cp`。
8. 任何 Ollama 模型命令。
9. 任何模型推理。
10. 任何 prompt 输入。
11. 任何模型下载。
12. 任何模型删除。
13. 任何模型创建。
14. 读取真实 KG。
15. 读取真实项目资料。
16. 读取真实招标文件。
17. 读取用户隐私或业务数据。
18. 读取 `.env` / secrets / tokens / credentials。
19. 读取 registration / metadata / proof / manifest / sample 实例。
20. 读取 output/job/export 正文。
21. generation。
22. export。
23. write-back。
24. ZBid 写回。
25. trial。
26. 真实使用。
27. 50 人正式使用。
28. 修改 V0/V1/backend/frontend/config/dependency。
29. 创建脚本、App 包、Tauri/Electron 工程、runtime bridge。
30. 运行测试/lint/build。
31. 停止或重启当前 ZDoc 服务，除非后续另行授权。
32. 停止或重启 Ollama server，除非后续另行授权。

## 7. 模型选择阻断条件

未来 040 如出现以下任一情况，应判定 `BLOCKED`，不得继续：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 037 `PASS` 无法复核。
4. 038 result closed 无法复核。
5. 模型清单信息不足以形成选择建议。
6. 需要重新执行 `ollama list` 才能判断。
7. 需要执行 `ollama run` 才能判断。
8. 需要模型推理或 benchmark 才能判断。
9. 需要输入 prompt 才能判断。
10. 需要读取真实 KG 才能判断。
11. 需要读取真实项目资料才可判断。
12. 需要触发 generation/export/write-back 才能判断。
13. 需要读取 `.env` / secrets 才能判断。
14. 无法在授权范围内确认边界。

## 8. 用户授权文本模板

后续如需进入 `LOCAL-LAUNCHER-040`，用户可直接复制以下授权文本：

`我明确授权 LOCAL-LAUNCHER-040 执行 Ollama model selection execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 037 Ollama model inventory PASS、复核 038 inventory result closed、基于 038 已记录的 8 个本地模型名称进行模型选择分析、按用途提出默认通用模型/编码工程辅助模型/大模型高质量候选/轻量快速候选/备选模型建议、说明每个候选模型适合的 ZDoc 场景、说明后续模型运行前仍需单独授权。严格禁止执行 ollama list、ollama run、ollama pull、ollama serve、ollama create、ollama rm、任何 Ollama 模型命令、任何模型推理、任何 prompt 输入、模型下载、模型删除、模型创建、读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 .env/secrets/tokens/credentials、读取 registration/metadata/proof/manifest/sample 实例、读取 output/job/export 正文、触发 generation/export/write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用。若模型选择需要重新执行模型命令、运行模型、输入 prompt、读取真实数据或触发生成/导出/写回，必须判定 BLOCKED 并停止。选择建议完成或阻断后必须回报并停止，不得进入下一节点。`

## 9. 进入 040 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-040-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-EXECUTION-GATE`

若用户未授权，则 hold。

本节点不得进入 `LOCAL-LAUNCHER-040`。

## 10. 禁止项确认

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
16. 未执行 curl / HTTP request。
17. 未再次访问 `/health`。
18. 未执行 `command -v ollama`。
19. 未执行 `which ollama`。
20. 未执行 `ollama --version`。
21. 未再次执行 `ollama list`。
22. 未执行 `ollama run`。
23. 未执行 `ollama pull`。
24. 未执行 `ollama serve`。
25. 未执行任何 Ollama 模型命令。
26. 未执行模型推理。
27. 未输入 prompt。
28. 未下载/删除/创建模型。
29. 未读取真实 KG。
30. 未读取真实项目资料。
31. 未读取真实招标文件。
32. 未读取 `.env` / secrets / tokens / credentials。
33. 未读取 registration / metadata / proof / manifest / sample 实例。
34. 未读取 output/job/export 正文。
35. 未读取日志正文。
36. 未触发 generation/export/write-back。
37. 未写 output/job/export。
38. 未进入 trial。
39. 未进入真实使用。
40. 未进入 50 人正式使用。
41. 未进入 `LOCAL-LAUNCHER-040`。

## 11. 实际执行命令清单

LOCAL-LAUNCHER-039 只执行 Git 状态确认和指定文档只读查看：

```bash
git status --short
git log -1 --format=%H
git tag --points-at HEAD
git log -1 --oneline
git diff --check
git diff --cached --check
sed -n '1,500p' docs/zdoc-local-launcher-v1-ollama-model-inventory-result-record-gate-local-launcher-038.md
sed -n '1,500p' docs/zdoc-local-launcher-v1-ollama-model-inventory-execution-gate-local-launcher-037.md
sed -n '1,500p' docs/zdoc-local-launcher-v1-ollama-model-inventory-authorization-gate-local-launcher-036.md
sed -n '1,500p' docs/zdoc-local-launcher-v1-ollama-server-post-start-status-record-gate-local-launcher-035.md
sed -n '1,500p' docs/zdoc-local-launcher-v1-ollama-server-start-execution-gate-local-launcher-034.md
```

未执行任何 Ollama 命令、服务命令、endpoint 请求、HTTP request、安装命令、测试、lint、build、真实数据读取、日志正文读取、trial、generation、export 或 write-back。

## 12. 当前 Decision

`LOCAL-LAUNCHER-039 ZDOC LOCAL APP V1 OLLAMA MODEL SELECTION AUTHORIZATION GATE COMPLETED / OLLAMA MODEL SELECTION EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO MODEL DOWNLOAD / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 13. 下一节点建议

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-040-ZDOC-LOCAL-APP-V1-OLLAMA-MODEL-SELECTION-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 040。
4. 040 即使后续被授权，也仅允许基于 038 已记录模型清单做模型选择建议。
5. 模型运行必须另设授权门和执行门。
6. trial / generation / export / write-back 必须另设授权门。
7. 真实 KG / 真实项目资料读取必须另设授权门。
8. 50 人正式使用必须另设 readiness 与 deployment gate。

## 14. 明确说明未进入 `LOCAL-LAUNCHER-040`

本节点未进入 `LOCAL-LAUNCHER-040`。
