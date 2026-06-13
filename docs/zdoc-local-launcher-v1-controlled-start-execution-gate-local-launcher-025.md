# LOCAL-LAUNCHER-025 ZDoc Local App V1 Controlled Start Execution Gate

## 1. 节点名称

`LOCAL-LAUNCHER-025-ZDOC-LOCAL-APP-V1-CONTROLLED-START-EXECUTION-GATE`

## 2. 用户授权摘要

用户明确授权 `LOCAL-LAUNCHER-025` 执行 controlled start execution。

授权范围仅限仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 023 runtime preflight PASS、复核 024 controlled start authorization、复核非敏感启动命令文本来源、使用 023 已识别的非敏感启动命令启动本地 ZDoc 服务、观察启动命令 stdout/stderr 中的非敏感启动状态、确认本地进程是否存在、确认端口是否处于监听状态，并记录 PID、端口、启动时间和命令来源。

本节点严格禁止访问 endpoint、执行 curl / HTTP request、运行 Ollama、执行 `ollama list`、读取真实 KG、读取真实项目资料、读取真实招标文件、读取 `.env` / secrets / tokens / credentials、读取 registration / metadata / proof / manifest / sample 实例、读取 output/job/export 正文、触发 generation/export/write-back、写 output/job/export、进入 trial、进入真实使用、进入 50 人正式使用、进入 endpoint health check 或进入 `LOCAL-LAUNCHER-026`。

## 3. 当前基线 HEAD/tag

- 开始前 HEAD：`08e6580dfad6a52b478a7b24843251cbea720454`
- 开始前 tag：`v0.1.660-local-launcher-zdoc-local-app-v1-controlled-start-authorization-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-024-ZDOC-LOCAL-APP-V1-CONTROLLED-START-AUTHORIZATION-GATE`

## 4. 023 runtime preflight PASS 复核结果

已只读复核 `docs/zdoc-local-launcher-v1-runtime-preflight-execution-gate-local-launcher-023.md`。

023 PASS 判定为：

`LOCAL-LAUNCHER-023 ZDOC LOCAL APP V1 RUNTIME PREFLIGHT EXECUTION GATE PASSED / RUNTIME PREFLIGHT COMPLETED / CONTROLLED START AUTHORIZATION MAY BE CONSIDERED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

复核结论：023 runtime preflight PASS 可复核。

## 5. 024 controlled start authorization 复核结果

已只读复核 `docs/zdoc-local-launcher-v1-controlled-start-authorization-gate-local-launcher-024.md`。

024 明确 controlled start execution 必须另设 025 执行门；用户已在本节点提供 025 授权。024 还确认 025 仍不得访问 endpoint、不得运行 Ollama、不得读取真实 KG / 真实项目资料、不得触发 trial / generation / export / write-back。

复核结论：024 controlled start authorization 已覆盖本节点边界。

## 6. 实际执行命令清单

本节点在仓库内执行的取证、启动和确认命令如下。同一命令可能因前置确认、后置确认或提交前检查被重复执行。

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
git tag --points-at HEAD
git log -1 --oneline
git diff --check
git diff --cached --check
sed -n '1,260p' docs/zdoc-local-launcher-v1-controlled-start-authorization-gate-local-launcher-024.md
sed -n '1,300p' docs/zdoc-local-launcher-v1-runtime-preflight-execution-gate-local-launcher-023.md
sed -n '301,460p' docs/zdoc-local-launcher-v1-runtime-preflight-execution-gate-local-launcher-023.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-runtime-preflight-authorization-gate-local-launcher-022.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-runtime-preflight-readiness-and-boundary-strategy-gate-local-launcher-021.md
sed -n '1,220p' README.md
sed -n '1,220p' local_launcher/v1/README.md
sed -n '1,160p' requirements.txt
pgrep -fl "zdoc|vite|node|uvicorn|fastapi|python|flask|django|electron|tauri"
lsof -nP -iTCP -sTCP:LISTEN
ps aux
export PYTHONPATH="$PWD:${PYTHONPATH:-}"; exec python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

未执行 `npm install`、`yarn`、`pnpm`、`pip`、测试、lint、build、curl、wget、http、httpie、nc、telnet、浏览器打开、endpoint 请求、Ollama 命令、generation、export 或 write-back。

## 7. 仓库路径确认结果

实际路径：

```text
/Users/youfeini/Desktop/文档生成系统
```

结论：符合预期仓库路径。

## 8. 当前分支确认结果

实际分支：

```text
main
```

结论：符合预期分支。

## 9. HEAD/tag 确认结果

实际开始前 HEAD：

```text
08e6580dfad6a52b478a7b24843251cbea720454
```

实际开始前 HEAD tag：

```text
v0.1.660-local-launcher-zdoc-local-app-v1-controlled-start-authorization-gate
```

实际最近提交：

```text
08e6580 LOCAL-LAUNCHER-024 controlled start authorization
```

结论：HEAD/tag 与 024 基线一致。

## 10. 工作区 clean 确认结果

开始前 `git status --short` 无输出。

服务启动后、写入 025 文档前，`git status --short` 仍无输出。

结论：controlled start 未造成仓库新增或修改。

## 11. 启动命令文本来源

启动命令文本来源为根目录 `README.md` 的“手动启动 / 启动后端服务”章节。

README 记录的启动步骤为：

```bash
cd /path/to/文档生成系统
export PYTHONPATH="$PWD:$PYTHONPATH"
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

本节点实际执行的 controlled start 命令为：

```bash
export PYTHONPATH="$PWD:${PYTHONPATH:-}"; exec python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`local_launcher/v1/README.md` 同时确认 V1 professional static console 本身不包含可执行启动入口、不访问 endpoint、不运行 Ollama、不触发 generation/export/write-back。

## 12. 启动命令安全边界判断

启动命令安全边界判断：

1. 命令来源明确，为 023 已识别的根 README 非敏感启动命令。
2. 命令不包含 install / build / test / lint。
3. 命令不包含 curl / HTTP request。
4. 命令不包含 Ollama 命令。
5. 命令未读取 `.env` / secrets / tokens / credentials。
6. 命令未访问 endpoint。
7. 命令未触发 generation/export/write-back。
8. 命令未写 output/job/export。
9. 启动 stdout/stderr 未出现 token、密钥、连接串、真实项目资料、真实 KG 或用户隐私内容。
10. 启动后工作区仍 clean，未出现非授权新增或修改文件。

结论：可在本节点授权范围内执行 controlled start。

## 13. 是否实际执行 controlled start

是。已执行 controlled start。

服务由本节点启动，不是启动前已存在的服务。

启动前 `pgrep -fl "zdoc|vite|node|uvicorn|fastapi|python|flask|django|electron|tauri"` 未发现 `uvicorn`、`fastapi`、`flask`、`django` 或 ZDoc 服务进程；仅发现 macOS `centaurid`/`AppleCentauri*` 的 `tauri` 子串误命中，以及 Codex MCP / `node_repl` 相关 `node` 进程。

启动前 `lsof -nP -iTCP -sTCP:LISTEN` 未发现 `127.0.0.1:8000` 监听。

## 14. 启动时间

启动时间记录为：

```text
2026-06-13 10:04 Asia/Shanghai
```

依据：`ps aux` 中本节点启动的 Python / Uvicorn 进程 `STARTED` 字段为 `10:04AM`。

## 15. stdout/stderr 非敏感启动状态摘要

启动命令输出仅包含非敏感 Uvicorn 状态：

```text
Started server process [21727]
Waiting for application startup.
Application startup complete.
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

未复制或记录任何 token、密钥、连接串、真实项目资料、真实 KG、隐私数据或业务数据。

## 16. PID 记录

本节点启动的服务 PID：

```text
21727
```

`pgrep` 摘要：

```text
21727 /Library/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## 17. 端口监听记录

`lsof -nP -iTCP -sTCP:LISTEN` 确认：

```text
Python 21727 ... TCP 127.0.0.1:8000 (LISTEN)
```

监听端口：

```text
127.0.0.1:8000
```

## 18. 服务是否由本节点启动

是。

启动前未发现 `127.0.0.1:8000` 监听，也未发现疑似 ZDoc / Uvicorn 服务进程。启动后发现 PID `21727` 和 `127.0.0.1:8000` 监听，且该 PID 与本节点 controlled start 会话一致。

## 19. 服务是否仍在运行

是。

本节点未停止服务。附件明确禁止未授权停止服务；因此服务保持运行。

## 20. 是否访问 endpoint

否。

未访问 endpoint，未进入 endpoint health check。

## 21. 是否执行 curl / HTTP request

否。

未执行 curl、wget、http、httpie、nc、telnet、浏览器打开或任何 HTTP request。

## 22. 是否运行 Ollama

否。

## 23. 是否执行 `ollama list`

否。

## 24. 是否读取真实 KG / 真实项目资料

否。

未读取真实 KG、真实项目资料或真实招标文件正文。

## 25. 是否读取 `.env` / secrets / tokens / credentials

否。

未读取 `.env`、`.env.*`、secret、token、credential、key 或 private 配置。

## 26. 是否读取 output/job/export 正文

否。

未读取 output/job/export 正文。

## 27. 是否触发 trial / generation / export / write-back

否。

未进入 trial，未触发 generation，未触发 export，未触发 write-back。

## 28. STARTED 或 BLOCKED 判定

`STARTED / CONTROLLED START ESTABLISHED`

判定依据：

1. 仓库路径正确。
2. 分支为 `main`。
3. HEAD/tag 与 024 基线一致。
4. 开始前工作区 clean。
5. 023 runtime preflight PASS 已复核。
6. 024 controlled start authorization 已复核。
7. 启动命令来源明确且非敏感。
8. 本节点实际启动了本地 ZDoc 服务。
9. 启动后进程存在。
10. 启动后端口处于 LISTEN。
11. 未访问 endpoint。
12. 未执行 curl / HTTP request。
13. 未运行 Ollama。
14. 未读取真实 KG / 真实项目资料。
15. 未读取 `.env` / secrets / tokens / credentials。
16. 未读取 output/job/export 正文。
17. 未触发 generation/export/write-back。
18. 未进入 trial、真实使用或 50 人正式使用。
19. 未进入 endpoint health check。
20. 未进入下一节点。

## 29. controlled start 后续限制

controlled start 后仍必须保持以下限制：

1. 不得访问 endpoint。
2. 不得执行 curl / HTTP request。
3. 不得运行 Ollama。
4. 不得执行 `ollama list`。
5. 不得读取真实 KG。
6. 不得读取真实项目资料。
7. 不得读取真实招标文件。
8. 不得读取 `.env` / secrets / tokens / credentials。
9. 不得读取 registration / metadata / proof / manifest / sample 实例。
10. 不得读取 output/job/export 正文。
11. 不得触发 trial / generation / export / write-back。
12. 不得写 output/job/export。
13. 不得进入真实使用或 50 人正式使用。
14. 不得进入 endpoint health check。
15. 不得停止服务，除非后续单独授权。

## 30. 下一节点建议

若继续推进，下一节点建议为：

`LOCAL-LAUNCHER-026-ZDOC-LOCAL-APP-V1-POST-START-STATUS-RECORD-GATE`

026 只能做 post-start status record，不得访问 endpoint。

endpoint health check、Ollama 运行、trial、generation、export、write-back、真实 KG / 真实项目资料读取、50 人正式使用均必须另设授权门和执行门。

## 31. 明确说明未进入 `LOCAL-LAUNCHER-026`

本节点未进入 `LOCAL-LAUNCHER-026`。

## 32. 当前 decision

`LOCAL-LAUNCHER-025 ZDOC LOCAL APP V1 CONTROLLED START EXECUTION GATE PASSED / CONTROLLED START ESTABLISHED / LOCAL SERVICE PROCESS AND LISTENING PORT CONFIRMED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`
