# LOCAL-LAUNCHER-028 ZDoc Local App V1 Endpoint Health Check Execution Gate

## 1. 节点名称

`LOCAL-LAUNCHER-028-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-EXECUTION-GATE`

## 2. 用户授权摘要

用户明确授权 `LOCAL-LAUNCHER-028` 执行 endpoint health check execution。

授权范围仅限仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 025 controlled start STARTED、复核 026 post-start status PASS、复核服务 PID 与监听端口、仅访问本地 `127.0.0.1:8000` 的最小健康检查 endpoint，并仅记录 HTTP 状态码、非敏感响应摘要和响应时间。

本节点严格禁止访问除 `127.0.0.1:8000` 之外的地址，禁止访问业务生成、导出、写回、review/apply、真实 KG、真实项目资料相关 endpoint，禁止发送真实项目数据、真实招标文件内容或用户隐私数据，禁止运行 Ollama 或 `ollama list`，禁止读取 `.env` / secrets / tokens / credentials，禁止读取 registration / metadata / proof / manifest / sample 实例，禁止读取 output/job/export 正文，禁止触发 generation/export/write-back，禁止写 output/job/export，禁止进入 trial、真实使用或 50 人正式使用。

## 3. 当前基线 HEAD/tag

- 开始前 HEAD：`12192a74bafb2ce91506e93cf292195822d88310`
- 开始前 tag：`v0.1.663-local-launcher-zdoc-local-app-v1-endpoint-health-check-authorization-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-027-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-AUTHORIZATION-GATE`

## 4. 025 STARTED 复核结果

已只读复核 `docs/zdoc-local-launcher-v1-controlled-start-execution-gate-local-launcher-025.md`。

025 controlled start 判定为：

```text
STARTED / CONTROLLED START ESTABLISHED
```

025 记录 PID：

```text
21727
```

025 记录监听端口：

```text
127.0.0.1:8000
```

复核结论：025 STARTED 可复核。

## 5. 026 PASS 复核结果

已只读复核 `docs/zdoc-local-launcher-v1-post-start-status-record-gate-local-launcher-026.md`。

026 post-start status 判定为：

```text
PASS
```

026 记录 PID `21727` 仍存在，`127.0.0.1:8000` 仍处于 LISTEN。

复核结论：026 PASS 可复核。

## 6. 027 endpoint health check authorization 复核结果

已只读复核 `docs/zdoc-local-launcher-v1-endpoint-health-check-authorization-gate-local-launcher-027.md`。

027 明确：028 如获用户明确授权，仅允许访问本地 `127.0.0.1:8000` 的最小 health / status / readiness 类 endpoint，仅记录 HTTP 状态码、非敏感响应摘要和响应时间；不得访问业务生成、导出、写回、review/apply、真实 KG、真实项目资料相关 endpoint，不得运行 Ollama，不得读取真实数据，不得触发 trial / generation / export / write-back。

复核结论：027 endpoint health check authorization 已覆盖本节点边界。

## 7. 实际执行命令清单

本节点在仓库内执行的 Git、只读复核、服务状态复核和最小健康检查命令如下。同一命令可能因前置确认、状态复核或提交前检查被重复执行。

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
git tag --points-at HEAD
git log -1 --oneline
git diff --check
git diff --cached --check
sed -n '1,260p' docs/zdoc-local-launcher-v1-endpoint-health-check-authorization-gate-local-launcher-027.md
sed -n '1,320p' docs/zdoc-local-launcher-v1-post-start-status-record-gate-local-launcher-026.md
sed -n '1,340p' docs/zdoc-local-launcher-v1-controlled-start-execution-gate-local-launcher-025.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-controlled-start-authorization-gate-local-launcher-024.md
sed -n '1,120p' README.md
pgrep -fl "zdoc|vite|node|uvicorn|fastapi|python|flask|django|electron|tauri"
lsof -nP -iTCP -sTCP:LISTEN
curl -sS -i --max-time 5 -w "\nHTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}\n" "http://127.0.0.1:8000/health"
```

未执行新服务启动、服务重启、服务停止、测试、lint、build、安装命令、业务 endpoint 请求、导出 endpoint 请求、写回 endpoint 请求、review/apply endpoint 请求、真实 KG / 真实项目资料 endpoint 请求、Ollama 命令、`ollama list`、日志正文读取、真实数据读取、trial、generation、export 或 write-back。

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
12192a74bafb2ce91506e93cf292195822d88310
```

实际开始前 HEAD tag：

```text
v0.1.663-local-launcher-zdoc-local-app-v1-endpoint-health-check-authorization-gate
```

实际最近提交：

```text
12192a7 LOCAL-LAUNCHER-027 endpoint health check authorization
```

结论：HEAD/tag 与 027 基线一致。

## 11. 工作区 clean 确认结果

开始前 `git status --short` 无输出。

endpoint health check 执行后、写入 028 文档前，`git status --short` 仍无输出。

结论：endpoint health check 未造成仓库新增或修改。

## 12. 服务 PID 复核结果

执行：

```bash
pgrep -fl "zdoc|vite|node|uvicorn|fastapi|python|flask|django|electron|tauri"
```

服务进程摘要：

```text
21727 /Library/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

补充说明：`pgrep` 还返回 macOS `centaurid` / `AppleCentauri*` 的 `tauri` 子串误命中，以及 Codex MCP / `node_repl` 相关 `node` 进程；这些不是 ZDoc 服务进程。

结论：PID `21727` 仍存在。

## 13. 端口监听复核结果

执行：

```bash
lsof -nP -iTCP -sTCP:LISTEN
```

端口监听摘要：

```text
Python 21727 ... TCP 127.0.0.1:8000 (LISTEN)
```

结论：`127.0.0.1:8000` 仍处于 LISTEN。

## 14. 最小健康检查 endpoint 来源

最小健康检查 endpoint 来源为根目录 `README.md` 的“验证服务”章节。

README 明确记录：

```bash
curl http://127.0.0.1:8000/health
```

并给出预期返回为短 JSON：

```text
{"ok": true, "version": "autoplan-0.1.0", "service": "...", ...}
```

结论：最小健康检查 endpoint 已明确确认为 `/health`，未猜测或扫描多个 endpoint。

## 15. 实际访问 URL

```text
http://127.0.0.1:8000/health
```

## 16. HTTP 方法

```text
GET
```

未发送请求体，未携带 token、secret 或 credential。

## 17. HTTP 状态码

```text
200
```

## 18. 响应时间

```text
0.003453s
```

## 19. 非敏感响应摘要

响应 `content-type`：

```text
application/json
```

非敏感响应摘要：

```text
ok=true; version=autoplan-0.1.0; service=文档生成系统; audit_ready=true
```

响应为短 JSON，未包含 token、secret、credential、真实项目数据、真实招标文件内容、真实 KG 内容或用户隐私数据。

## 20. 是否访问除 `127.0.0.1:8000` 外地址

否。

仅访问：

```text
http://127.0.0.1:8000/health
```

## 21. 是否访问业务生成 endpoint

否。

未访问 `/compose` 或任何业务生成 endpoint。

## 22. 是否访问导出 endpoint

否。

未访问 `/export` 或任何导出 endpoint。

## 23. 是否访问写回 endpoint

否。

未访问任何写回 endpoint。

## 24. 是否访问 review/apply endpoint

否。

未访问任何 review/apply endpoint。

## 25. 是否访问真实 KG / 真实项目资料 endpoint

否。

未访问真实 KG endpoint，未访问真实项目资料 endpoint。

## 26. 是否发送真实项目数据 / 招标文件内容 / 隐私数据

否。

本节点执行 GET 请求，未发送请求体，未发送真实项目数据、真实招标文件内容或用户隐私数据。

## 27. 是否运行 Ollama

否。

## 28. 是否执行 `ollama list`

否。

## 29. 是否读取 `.env` / secrets / tokens / credentials

否。

未读取 `.env`、`.env.*`、secret、token、credential、key 或 private 配置。

## 30. 是否读取 registration / metadata / proof / manifest / sample 实例

否。

## 31. 是否读取 output/job/export 正文

否。

未读取 output/job/export 正文。

## 32. 是否触发 trial / generation / export / write-back

否。

未进入 trial，未触发 generation，未触发 export，未触发 write-back。

## 33. PASS 或 BLOCKED 判定

`PASS`

判定依据：

1. 仓库路径正确。
2. 分支为 `main`。
3. HEAD/tag 与 027 基线一致。
4. 工作区 clean。
5. 025 STARTED 已复核。
6. 026 PASS 已复核。
7. PID `21727` 仍存在。
8. `127.0.0.1:8000` 仍处于 LISTEN。
9. 最小健康检查 endpoint 已明确确认为 `/health`。
10. 仅访问了 `127.0.0.1:8000` 的该最小健康检查 endpoint。
11. HTTP 状态码为 `200`。
12. 响应摘要非敏感。
13. 未访问业务生成、导出、写回、review/apply、KG、项目资料 endpoint。
14. 未发送真实项目数据、真实招标文件内容、用户隐私数据。
15. 未运行 Ollama。
16. 未读取真实 KG / 真实项目资料。
17. 未读取 `.env` / secrets / tokens / credentials。
18. 未读取 output/job/export 正文。
19. 未触发 generation/export/write-back。
20. 未进入 trial、真实使用、50 人正式使用。
21. 未进入下一节点。

## 34. 后续限制

后续必须保持以下限制：

1. `LOCAL-LAUNCHER-029` 只能记录和复核 endpoint health check 结果，不得再次访问 endpoint。
2. Ollama 运行必须另设授权门。
3. trial / generation / export / write-back 必须另设授权门。
4. 真实 KG / 真实项目资料读取必须另设授权门。
5. 50 人正式使用必须另设 readiness 与 deployment gate。
6. 不得停止或重启服务，除非后续另行授权。

## 35. 下一节点建议

若继续推进，下一节点建议为：

`LOCAL-LAUNCHER-029-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-RESULT-RECORD-GATE`

029 只能记录和复核 endpoint health check 结果，不得再次访问 endpoint。

## 36. 明确说明未进入 `LOCAL-LAUNCHER-029`

本节点未进入 `LOCAL-LAUNCHER-029`。

## 37. 当前 decision

`LOCAL-LAUNCHER-028 ZDOC LOCAL APP V1 ENDPOINT HEALTH CHECK EXECUTION GATE PASSED / MINIMAL LOCAL HEALTH CHECK COMPLETED / HTTP STATUS AND NON-SENSITIVE RESPONSE SUMMARY RECORDED / NO BUSINESS ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`
