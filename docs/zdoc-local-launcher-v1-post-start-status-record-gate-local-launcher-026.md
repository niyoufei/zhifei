# LOCAL-LAUNCHER-026 ZDoc Local App V1 Post-Start Status Record Gate

## 1. 节点名称

`LOCAL-LAUNCHER-026-ZDOC-LOCAL-APP-V1-POST-START-STATUS-RECORD-GATE`

## 2. 当前基线 HEAD/tag

- 开始前 HEAD：`b89a6acef8ec2ea2c13493f7c3bc62288250733f`
- 开始前 tag：`v0.1.661-local-launcher-zdoc-local-app-v1-controlled-start-execution-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-025-ZDOC-LOCAL-APP-V1-CONTROLLED-START-EXECUTION-GATE`

## 3. 上游节点 023、024、025 通过状态

上游节点状态：

1. `LOCAL-LAUNCHER-023-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-EXECUTION-GATE`：PASS。
2. `LOCAL-LAUNCHER-024-ZDOC-LOCAL-APP-V1-CONTROLLED-START-AUTHORIZATION-GATE`：completed。
3. `LOCAL-LAUNCHER-025-ZDOC-LOCAL-APP-V1-CONTROLLED-START-EXECUTION-GATE`：STARTED / controlled start established。

023 decision：

`LOCAL-LAUNCHER-023 ZDOC LOCAL APP V1 RUNTIME PREFLIGHT EXECUTION GATE PASSED / RUNTIME PREFLIGHT COMPLETED / CONTROLLED START AUTHORIZATION MAY BE CONSIDERED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

024 decision：

`LOCAL-LAUNCHER-024 ZDOC LOCAL APP V1 CONTROLLED START AUTHORIZATION GATE COMPLETED / CONTROLLED START EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

025 decision：

`LOCAL-LAUNCHER-025 ZDOC LOCAL APP V1 CONTROLLED START EXECUTION GATE PASSED / CONTROLLED START ESTABLISHED / LOCAL SERVICE PROCESS AND LISTENING PORT CONFIRMED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 4. 025 controlled start 判定

025 controlled start 判定：`STARTED`。

已只读复核 `docs/zdoc-local-launcher-v1-controlled-start-execution-gate-local-launcher-025.md`，确认 025 记录为 `STARTED / CONTROLLED START ESTABLISHED`。

## 5. 025 已记录 PID

025 已记录 PID：

```text
21727
```

## 6. 025 已记录监听端口

025 已记录监听端口：

```text
127.0.0.1:8000
```

## 7. 本节点实际执行命令清单

本节点在仓库内执行的 Git、只读复核、进程与端口状态确认命令如下。同一命令可能因前置确认、状态复核或提交前检查被重复执行。

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
git tag --points-at HEAD
git log -1 --oneline
git diff --check
git diff --cached --check
sed -n '1,380p' docs/zdoc-local-launcher-v1-controlled-start-execution-gate-local-launcher-025.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-controlled-start-authorization-gate-local-launcher-024.md
sed -n '1,360p' docs/zdoc-local-launcher-v1-runtime-preflight-execution-gate-local-launcher-023.md
pgrep -fl "zdoc|vite|node|uvicorn|fastapi|python|flask|django|electron|tauri"
lsof -nP -iTCP -sTCP:LISTEN
ps aux
```

未执行新服务启动、服务重启、服务停止、curl、HTTP request、endpoint health check、Ollama 命令、`ollama list`、测试、lint、build、安装命令、日志正文读取、真实数据读取、trial、generation、export 或 write-back。

## 8. 仓库路径确认结果

实际路径：

```text
/Users/youfeini/Desktop/文档生成系统
```

结论：符合预期仓库路径。

## 9. 当前分支确认结果

实际分支：

```text
main
```

结论：符合预期分支。

## 10. HEAD/tag 确认结果

实际开始前 HEAD：

```text
b89a6acef8ec2ea2c13493f7c3bc62288250733f
```

实际开始前 HEAD tag：

```text
v0.1.661-local-launcher-zdoc-local-app-v1-controlled-start-execution-gate
```

实际最近提交：

```text
b89a6ac LOCAL-LAUNCHER-025 controlled start execution
```

结论：HEAD/tag 与 025 基线一致。

## 11. 工作区 clean 确认结果

开始前 `git status --short` 无输出。

post-start 进程与端口状态复核后、写入 026 文档前，`git status --short` 仍无输出。

结论：本节点状态复核未造成仓库新增或修改。

## 12. post-start 进程状态复核结果

执行：

```bash
pgrep -fl "zdoc|vite|node|uvicorn|fastapi|python|flask|django|electron|tauri"
ps aux
```

进程状态摘要：

```text
21727 /Library/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`ps aux` 同步确认 PID `21727` 存在，状态为 `Ss+`，启动时间为 `10:04AM`，命令为：

```text
/Library/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

补充说明：`pgrep` 还返回 macOS `centaurid` / `AppleCentauri*` 的 `tauri` 子串误命中，以及 Codex MCP / `node_repl` 相关 `node` 进程；这些不是 ZDoc 服务进程。

结论：025 记录的 PID `21727` 仍存在。

## 13. post-start 端口监听状态复核结果

执行：

```bash
lsof -nP -iTCP -sTCP:LISTEN
```

端口监听摘要：

```text
Python 21727 ... TCP 127.0.0.1:8000 (LISTEN)
```

结论：025 记录的 `127.0.0.1:8000` 仍处于 LISTEN。

## 14. 服务是否仍在运行

是。

依据：

1. PID `21727` 仍存在。
2. `127.0.0.1:8000` 仍处于 LISTEN。

## 15. 服务是否由 025 启动

是。

025 文档记录：启动前未发现 `127.0.0.1:8000` 监听，也未发现疑似 ZDoc / Uvicorn 服务进程；启动后发现 PID `21727` 和 `127.0.0.1:8000` 监听，且该 PID 与 025 controlled start 会话一致。

026 本节点仅复核该服务状态，未启动新服务，未重启服务，未停止服务。

## 16. 是否访问 endpoint

否。

本节点未访问任何 endpoint，未进入 endpoint health check。

## 17. 是否执行 curl / HTTP request

否。

未执行 curl、wget、http、httpie、nc、telnet、浏览器打开或任何 HTTP request。

## 18. 是否运行 Ollama

否。

## 19. 是否执行 `ollama list`

否。

## 20. 是否读取真实 KG / 真实项目资料

否。

未读取真实 KG、真实项目资料或真实招标文件正文。

## 21. 是否读取 `.env` / secrets / tokens / credentials

否。

未读取 `.env`、`.env.*`、secret、token、credential、key 或 private 配置。

## 22. 是否读取 output/job/export 正文

否。

未读取 output/job/export 正文。

## 23. 是否读取日志正文

否。

未读取任何日志正文。

## 24. 是否触发 trial / generation / export / write-back

否。

未进入 trial，未触发 generation，未触发 export，未触发 write-back。

## 25. PASS 或 BLOCKED 判定

`PASS`

判定依据：

1. 仓库路径正确。
2. 分支为 `main`。
3. HEAD/tag 与 025 基线一致。
4. 工作区 clean。
5. 025 controlled start STARTED 已复核。
6. 服务进程 PID `21727` 仍存在。
7. `127.0.0.1:8000` 仍处于 LISTEN。
8. 未访问 endpoint。
9. 未执行 curl / HTTP request。
10. 未运行 Ollama。
11. 未读取真实 KG / 真实项目资料。
12. 未读取 `.env` / secrets / tokens / credentials。
13. 未读取 output/job/export 正文。
14. 未读取日志正文。
15. 未触发 generation/export/write-back。
16. 未进入 endpoint health check。
17. 未进入下一节点。

## 26. endpoint health check 前置限制

endpoint health check 尚未授权。

后续必须保持以下限制：

1. endpoint health check 必须先有授权门。
2. endpoint health check execution 必须另设执行门。
3. 027 若被授权，只能记录 endpoint health check 授权边界，不得访问 endpoint。
4. 不得执行 curl / HTTP request。
5. 不得打开浏览器访问本地端口。
6. 不得运行 Ollama 或执行 `ollama list`。
7. 不得读取真实 KG / 真实项目资料 / 真实招标文件。
8. 不得读取 `.env` / secrets / tokens / credentials。
9. 不得读取 output/job/export 正文。
10. 不得读取日志正文，除非后续单独授权。
11. 不得触发 trial / generation / export / write-back。
12. 不得停止或重启服务，除非后续单独授权。

## 27. 下一节点建议

若继续推进，下一节点建议为：

`LOCAL-LAUNCHER-027-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-AUTHORIZATION-GATE`

027 只能记录 endpoint health check 授权边界，不得访问 endpoint。

endpoint health check execution、Ollama 运行、trial、generation、export、write-back、真实 KG / 真实项目资料读取、50 人正式使用均必须另设授权门和执行门。

## 28. 明确说明未进入 `LOCAL-LAUNCHER-027`

本节点未进入 `LOCAL-LAUNCHER-027`。

## 29. 当前 decision

`LOCAL-LAUNCHER-026 ZDOC LOCAL APP V1 POST-START STATUS RECORD GATE PASSED / POST-START LOCAL SERVICE STATUS RECORDED / SERVICE PROCESS AND LISTENING PORT STILL CONFIRMED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`
