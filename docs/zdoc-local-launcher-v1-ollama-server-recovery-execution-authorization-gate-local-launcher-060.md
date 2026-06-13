# LOCAL-LAUNCHER-060 ZDoc Local App V1 Ollama Server Recovery Execution Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-060-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-RECOVERY-EXECUTION-AUTHORIZATION-GATE`

本节点性质：

`Ollama server recovery execution authorization boundary only`

本节点目标：

在 059 已完成受控 diagnostics execution 后，仅新增本授权边界文档，记录后续是否可以执行一次受控 Ollama server recovery execution 的授权范围、禁止范围、阻断条件、完成后回报格式和用户授权文本模板。

本节点明确：

1. 不执行任何 recovery。
2. 不执行任何诊断命令。
3. 不执行任何 Ollama 命令。
4. 不执行 `ollama serve`。
5. 不执行 `ollama list`。
6. 不执行 `ollama run`。
7. 不执行 `ollama pull`。
8. 不执行 `ollama create`。
9. 不执行 `ollama rm`。
10. 不启动、重启或停止 ZDoc 服务。
11. 不启动、重启或停止 Ollama server。
12. 不访问 endpoint。
13. 不执行 curl / HTTP request。
14. 不运行模型。
15. 不向模型输入 prompt。
16. 不读取真实 KG、真实项目资料或真实招标文件。
17. 不读取 `.env` / secrets / tokens / credentials。
18. 不读取 registration / metadata / proof / manifest / sample 实例。
19. 不读取 output/job/export 正文。
20. 不读取日志正文。
21. 不读取 `/tmp` 临时 stdout/stderr 捕获文件正文。
22. 不触发 ZDoc generation/export/write-back。
23. 不进入 trial、真实使用或 50 人正式使用。
24. 不进入 `LOCAL-LAUNCHER-061`。

## 2. 开始前 HEAD/tag

开始前 HEAD：

```text
a6bda42417a3d7d70861ec4d03895b0ebfa98cdd
```

开始前 tag：

```text
v0.1.695-local-launcher-zdoc-local-app-v1-ollama-server-diagnostics-execution-gate
```

当前分支：

```text
main
```

仓库路径：

```text
/Users/youfeini/Desktop/文档生成系统
```

开始前 `git status --short` 无输出，工作区 clean。

## 3. 上一节点 059 审核通过结论

上一节点：

`LOCAL-LAUNCHER-059-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-DIAGNOSTICS-EXECUTION-GATE`

上一节点审核结论：

`LOCAL-LAUNCHER-059 可审核通过`

059 当前 decision：

```text
LOCAL-LAUNCHER-059 ZDOC LOCAL APP V1 OLLAMA SERVER DIAGNOSTICS EXECUTION GATE COMPLETED / OLLAMA SERVER DIAGNOSTICS EXECUTED WITH USER AUTHORIZATION / NO OLLAMA SERVE EXECUTED / NO OLLAMA LIST EXECUTED / NO OLLAMA RUN EXECUTED / NO OLLAMA PULL EXECUTED / NO SERVICE START STOP RESTART EXECUTED / NO ENDPOINT OR HTTP REQUEST EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED / DIAGNOSTIC RESULT RECORDED / STOPPED BEFORE 060
```

## 4. 上游文档复核范围

本节点仅复核以下 docs：

1. `docs/zdoc-local-launcher-v1-ollama-server-recovery-execution-gate-local-launcher-056.md`
2. `docs/zdoc-local-launcher-v1-ollama-server-recovery-blocker-review-gate-local-launcher-057.md`
3. `docs/zdoc-local-launcher-v1-ollama-server-diagnostics-authorization-gate-local-launcher-058.md`
4. `docs/zdoc-local-launcher-v1-ollama-server-diagnostics-execution-gate-local-launcher-059.md`

说明：

1. 附件中列出的 056 示例文件名在仓库中不存在。
2. 已按附件允许的 `find docs -maxdepth 1 -type f -name '*056*.md'` 定位 056 docs。
3. 仅读取 `LOCAL-LAUNCHER` 对应的 056 docs。
4. 未读取 `MODEL-FLEET-GOVERNANCE` 的 056 docs 正文。

## 5. 059 诊断摘要

059 diagnostics execution 已在用户授权范围内完成，摘要如下：

1. `ollama` client 存在。
2. `ollama` client version 为 `0.21.2`。
3. 059 当前未发现 `ollama` PID。
4. 059 当前未发现 `127.0.0.1:11434 LISTEN`。
5. Homebrew services 摘要为 `ollama none`。
6. launchctl 未发现 `ollama` 匹配项。
7. 056 `/tmp` 捕获文件只说明 056 当时曾进入短暂监听状态。
8. 056 `/tmp` 捕获文件不能证明 059 当前 Ollama server 正在运行。
9. 059 未执行 `ollama serve`。
10. 059 未执行 `ollama list`。
11. 059 未执行 `ollama run`。
12. 059 未执行 `ollama pull`。
13. 059 未启动、停止或重启任何服务。
14. 059 未访问 endpoint。
15. 059 未执行 curl / HTTP request。
16. 059 未运行模型。
17. 059 未向模型输入 prompt。
18. 059 未读取真实 KG / 真实项目资料。
19. 059 未触发 ZDoc generation/export/write-back。
20. 059 未进入 trial。

059 当前 blocker：

```text
Ollama server is not currently running or listening on 127.0.0.1:11434; no managed service entry is active in the checked Homebrew/launchctl summaries.
```

## 6. 当前 blocker

当前 blocker：

```text
Ollama server 当前未运行/未监听。
```

具体含义：

1. 当前无法确认存在可用 Ollama server PID。
2. 当前无法确认 `127.0.0.1:11434` 存在 LISTEN。
3. 当前不能继续 Prompt control smoke test。
4. 当前不能继续模型运行、prompt 输入、endpoint 访问或 ZDoc + Ollama 集成验证。
5. 当前不能进入 trial、真实使用或 50 人正式使用。

## 7. 需要 recovery execution 的原因

后续 recovery execution 的必要性如下：

1. 056 曾按授权执行一次 `ollama serve`，但未能持续确认 PID 与 LISTEN。
2. 057 已确认核心 blocker 是 `ollama serve` 启动后未能持续确认 PID 与 LISTEN。
3. 058 已建立 diagnostics execution 授权边界。
4. 059 已完成 diagnostics execution，并确认当前仍未运行、未监听。
5. 不恢复或确认 Ollama server 持续运行，就不能进入任何模型测试。
6. 不能跳过 recovery 直接进入 `ollama list`、`ollama run`、prompt 输入、endpoint 访问或 smoke test。
7. recovery execution 必须单独由用户明确授权。

本节点只记录上述必要性，不执行 recovery。

## 8. 下一节点 061 可授权范围草案

以下内容仅作为未来 `LOCAL-LAUNCHER-061` 授权草案记录，本节点不执行。

未来若用户明确授权，`LOCAL-LAUNCHER-061` 可授权范围建议仅限：

1. 仓库路径、分支、HEAD/tag、clean 状态确认。
2. 复核 059 诊断结论。
3. 复核 060 授权边界。
4. 执行一次受控 `ollama serve`。
5. 将 stdout/stderr 重定向至新的 `/tmp` 临时捕获文件。
6. 记录启动命令 PID。
7. 等待短时间后复核 PID 是否存活。
8. 复核 `127.0.0.1:11434 LISTEN` 是否存在。
9. 仅读取新捕获文件前 40 行并记录非敏感摘要。
10. 不执行 `ollama list`。
11. 不执行 `ollama run`。
12. 不执行 `ollama pull`。
13. 不访问 endpoint。
14. 不执行 curl / HTTP request。
15. 不输入 prompt。
16. 不运行模型。
17. 不读取真实 KG/项目资料。
18. 不触发 generation/export/write-back。
19. 不进入 trial 或真实使用。

## 9. 下一节点 061 禁止范围草案

未来 `LOCAL-LAUNCHER-061` 即使获授权，仍禁止：

1. `ollama list/run/pull/create/rm`。
2. 访问 endpoint。
3. curl / HTTP request。
4. 模型推理。
5. prompt 输入。
6. 真实 KG、项目资料、招标文件、secrets、output/job/export 正文、日志正文读取。
7. generation/export/write-back。
8. trial、真实使用、50 人正式使用。
9. 修改 V0/V1/backend/frontend/config/dependency。
10. 启动、停止、重启 ZDoc 服务。
11. 下载、删除、创建模型。
12. 运行测试/lint/build。
13. npm/yarn/pnpm/pip 安装。
14. 打开 HTML 页面。
15. 自动进入 `LOCAL-LAUNCHER-062`。

## 10. 下一节点 061 阻断条件

未来 `LOCAL-LAUNCHER-061` 如出现以下任一情况，应判定 `BLOCKED`，不得继续：

1. 开始前 HEAD/tag 不符合预期。
2. 工作区不 clean。
3. 059 docs 缺失或诊断结论无法复核。
4. 060 docs 缺失或授权边界无法复核。
5. 用户未明确授权 061。
6. `ollama serve` 启动后 PID 不可确认。
7. `127.0.0.1:11434` 未形成 LISTEN。
8. 捕获文件出现疑似敏感内容，不得复制正文，只记录阻断。
9. 出现需要 endpoint 访问才能判断的事项。
10. 出现需要模型推理或 prompt 输入才能判断的事项。
11. 出现需要读取真实 KG/项目资料/secrets/output/job/export/log 正文的事项。
12. 任一禁止项被触发或存在触发风险。

## 11. 下一节点 061 完成后回报格式

未来 `LOCAL-LAUNCHER-061` 完成后必须逐项回报：

1. 是否完成 `LOCAL-LAUNCHER-061-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-RECOVERY-EXECUTION-GATE`。
2. 开始前 HEAD / tag。
3. 结束后 HEAD。
4. `git status --short` 是否 clean。
5. 实际修改文件。
6. 实际新增文件。
7. 是否仅新增 061 docs。
8. 是否修改 V1 产物。
9. 是否修改 V0 产物。
10. 是否修改 backend/frontend/config/dependency。
11. 是否新增 JS 文件。
12. 是否创建脚本或真正 App 包。
13. 是否运行 npm/yarn/pnpm/pip 安装命令。
14. 是否运行测试/lint/build。
15. 是否打开 HTML 页面。
16. 是否启动新 ZDoc 服务。
17. 是否重启 ZDoc 服务。
18. 是否停止 ZDoc 服务。
19. 是否启动新的 Ollama server。
20. 是否重启 Ollama server。
21. 是否停止 Ollama server。
22. 是否执行 `ollama serve`。
23. 是否执行 `ollama list`。
24. 是否执行 `ollama run`。
25. 是否执行 `ollama pull`。
26. 是否执行任何未授权 Ollama 命令。
27. 是否执行模型推理。
28. 是否向模型输入 prompt。
29. 是否下载/删除/创建模型。
30. 是否运行多个模型。
31. 是否访问 endpoint。
32. 是否执行 curl / HTTP request。
33. 是否读取真实 KG。
34. 是否读取真实项目资料。
35. 是否读取真实招标文件。
36. 是否读取 `.env` / secrets / tokens / credentials。
37. 是否读取 registration / metadata / proof / manifest / sample 实例。
38. 是否读取 output/job/export 正文。
39. 是否读取日志正文。
40. 是否读取 `/tmp` 临时 stdout/stderr 捕获文件正文。
41. 是否触发 ZDoc generation/export/write-back。
42. 是否写 output/job/export。
43. 是否进入 trial。
44. 是否进入真实使用或 50 人正式使用。
45. 是否记录 059 诊断结论。
46. 是否复核 060 授权边界。
47. 是否记录受控 `ollama serve` PID。
48. 是否记录 `127.0.0.1:11434 LISTEN` 状态。
49. 是否仅记录新捕获文件前 40 行非敏感摘要。
50. 当前 decision。
51. 下一节点建议。
52. `git diff --check` 是否通过。
53. `git diff --cached --check` 是否通过。
54. commit hash。
55. 远端 tag 是否已创建并 push。
56. 是否进入下一节点。

## 12. 用户授权文本模板

后续如需进入 061，用户可直接复制以下授权文本：

```text
我明确授权 LOCAL-LAUNCHER-061-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-RECOVERY-EXECUTION-GATE 执行一次受控 Ollama server recovery。

授权范围仅限：仓库/分支/HEAD/tag/clean 状态确认，复核 059 诊断结论与 060 授权边界，执行一次受控 ollama serve，将 stdout/stderr 重定向至新的 /tmp 临时捕获文件，记录启动 PID，短时间后复核 PID 是否存活，复核 127.0.0.1:11434 LISTEN 状态，仅读取新捕获文件前 40 行并记录非敏感摘要。

禁止执行 ollama list/run/pull/create/rm，禁止访问 endpoint/curl/HTTP request，禁止模型推理，禁止向模型输入 prompt，禁止读取真实 KG/真实项目资料/招标文件/secrets/output/job/export 正文/日志正文，禁止触发 generation/export/write-back，禁止进入 trial、真实使用或 50 人正式使用，禁止进入 062。

完成后必须回报并停止，不得继续推进。
```

## 13. 未经用户授权不得进入 061

本节点明确：

1. 未经用户明确授权，不得进入 `LOCAL-LAUNCHER-061`。
2. 060 完成后必须停止等待用户审核。
3. 本节点不授权 `ollama serve`。
4. 本节点不授权任何 recovery。
5. 本节点不授权任何模型、endpoint、prompt、真实数据、generation/export/write-back 或 trial 操作。

## 14. 本节点禁止项确认

本节点确认：

1. 未执行任何诊断命令。
2. 未执行任何系统诊断命令。
3. 未执行任何 Ollama 命令。
4. 未执行 `ollama serve`。
5. 未执行 `ollama list`。
6. 未执行 `ollama run`。
7. 未执行 `ollama pull`。
8. 未执行 `ollama create`。
9. 未执行 `ollama rm`。
10. 未启动、停止、重启任何服务。
11. 未启动新的 Ollama server。
12. 未重启 Ollama server。
13. 未停止 Ollama server。
14. 未启动、重启或停止 ZDoc 服务。
15. 未访问 endpoint。
16. 未执行 curl / HTTP request。
17. 未执行模型推理。
18. 未向模型输入 prompt。
19. 未下载、删除或创建模型。
20. 未运行多个模型。
21. 未读取真实 KG。
22. 未读取真实项目资料。
23. 未读取真实招标文件。
24. 未读取 `.env` / secrets / tokens / credentials。
25. 未读取 registration / metadata / proof / manifest / sample 实例。
26. 未读取 output/job/export 正文。
27. 未读取日志正文。
28. 未读取 `/tmp` 临时 stdout/stderr 捕获文件正文。
29. 未触发 ZDoc generation/export/write-back。
30. 未写 output/job/export。
31. 未进入 trial。
32. 未进入真实使用或 50 人正式使用。
33. 未修改 V1 产物。
34. 未修改 V0 产物。
35. 未修改 backend/frontend/config/dependency。
36. 未新增 JS 文件。
37. 未创建脚本或真正 App 包。
38. 未运行 npm/yarn/pnpm/pip 安装命令。
39. 未运行测试/lint/build。
40. 未打开 HTML 页面。
41. 未进入 `LOCAL-LAUNCHER-061`。

## 15. 当前 Decision

```text
LOCAL-LAUNCHER-060 ZDOC LOCAL APP V1 OLLAMA SERVER RECOVERY EXECUTION AUTHORIZATION GATE COMPLETED / OLLAMA SERVER RECOVERY EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO DIAGNOSTIC COMMAND EXECUTED / NO OLLAMA COMMAND EXECUTED / NO OLLAMA SERVE EXECUTED / NO OLLAMA LIST EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED / STOPPED BEFORE 061
```

## 16. 下一节点建议

下一节点建议：

1. 停止并等待用户审核本 060 授权边界文档。
2. 若用户明确发送授权文本，可进入 `LOCAL-LAUNCHER-061-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-RECOVERY-EXECUTION-GATE`。
3. 若用户未授权，则 hold。
4. 本节点不得进入 061。
5. 061 即使被授权，也只能执行一次受控 Ollama server recovery。
6. 061 不授权 `ollama list`。
7. 061 不授权 `ollama run`。
8. 061 不授权 `ollama pull`。
9. 061 不授权 endpoint / curl / HTTP request。
10. 061 不授权模型推理或 prompt 输入。
11. 061 不授权真实 KG / 真实项目资料读取。
12. 061 不授权 generation/export/write-back。
13. 061 不授权 trial、真实使用或 50 人正式使用。
