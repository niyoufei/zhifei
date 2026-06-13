# LOCAL-LAUNCHER-027 ZDoc Local App V1 Endpoint Health Check Authorization Gate

## 1. 节点基本信息

- 节点名称：`LOCAL-LAUNCHER-027-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-AUTHORIZATION-GATE`
- 本节点性质：`endpoint health check authorization boundary and user authorization request only`
- 本节点产物：`docs/zdoc-local-launcher-v1-endpoint-health-check-authorization-gate-local-launcher-027.md`
- 当前基线 HEAD：`bd3c52dbef0586976ceada8b22651cdd1e4f5802`
- 当前基线 tag：`v0.1.662-local-launcher-zdoc-local-app-v1-post-start-status-record-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-026-ZDOC-LOCAL-APP-V1-POST-START-STATUS-RECORD-GATE`

上游节点通过状态：

1. `LOCAL-LAUNCHER-023-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-EXECUTION-GATE`：PASS。
2. `LOCAL-LAUNCHER-024-ZDOC-LOCAL-APP-V1-CONTROLLED-START-AUTHORIZATION-GATE`：completed。
3. `LOCAL-LAUNCHER-025-ZDOC-LOCAL-APP-V1-CONTROLLED-START-EXECUTION-GATE`：STARTED。
4. `LOCAL-LAUNCHER-026-ZDOC-LOCAL-APP-V1-POST-START-STATUS-RECORD-GATE`：PASS。

025 controlled start 判定：

```text
STARTED
```

026 post-start status 判定：

```text
PASS
```

当前服务状态摘要基于 026 记录：

- PID：`21727`
- 监听端口：`127.0.0.1:8000`
- 服务仍在运行
- endpoint 尚未访问

本节点不执行 endpoint health check，不访问 endpoint，不执行 curl / HTTP request，不运行 Ollama，不读取真实数据。

## 2. 当前授权状态

当前授权状态：

1. 当前仅授权执行 `LOCAL-LAUNCHER-027` docs-only 授权边界记录。
2. 当前未授权执行 `LOCAL-LAUNCHER-028`。
3. 当前未授权访问 endpoint。
4. 当前未授权执行 curl / HTTP request。
5. 当前未授权运行 Ollama。
6. 当前未授权执行 `ollama list` 或任何 Ollama 模型命令。
7. 当前未授权读取真实 KG。
8. 当前未授权读取真实项目资料。
9. 当前未授权读取真实招标文件。
10. 当前未授权读取 `.env` / secrets / tokens / credentials。
11. 当前未授权 trial。
12. 当前未授权 generation / export / write-back。
13. 当前未授权 ZBid 写回。
14. 当前未授权进入真实使用或 50 人正式使用。

## 3. endpoint health check 的定义边界

endpoint health check 必须按以下层级拆分，不能跨级执行：

1. `endpoint health check authorization gate`：仅记录授权边界，不访问 endpoint。
2. `endpoint health check execution gate`：未来如获用户明确授权，才可访问最小健康检查 endpoint。
3. `endpoint response record gate`：记录健康检查响应，不触发业务动作。
4. `Ollama readiness authorization gate`：Ollama 状态检查授权。
5. `trial authorization gate`：小范围试用授权。
6. `trial execution gate`：小范围试用执行。
7. `generation/export/write-back authorization gate`：生成、导出、写回授权。
8. `50-user deployment readiness gate`：50 人正式部署准备，不得提前进入。

LOCAL-LAUNCHER-027 仅属于第 1 层：`endpoint health check authorization gate`。

## 4. 未来 028 可授权范围草案

以下仅为草案，不在 LOCAL-LAUNCHER-027 执行。

未来若用户明确授权 `LOCAL-LAUNCHER-028`，endpoint health check execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 025 controlled start STARTED。
6. 复核 026 post-start status PASS。
7. 复核服务 PID 与监听端口。
8. 仅访问最小健康检查 endpoint。
9. 仅允许访问本地地址 `127.0.0.1:8000`。
10. 仅允许访问 health / status / readiness 类 endpoint。
11. 仅记录 HTTP 状态码、非敏感响应摘要、响应时间。
12. 不发送真实项目数据。
13. 不发送真实 KG 数据。
14. 不发送用户隐私数据。
15. 不触发 generation/export/write-back。
16. 不运行 Ollama。
17. 检查完成后立即回报并停止。

未来 028 即使被授权，也仍不得进入 trial，不得读取真实 KG / 真实项目资料，不得触发 generation/export/write-back。

## 5. 未来 028 禁止范围草案

未来 028 仍应禁止：

1. 访问除 `127.0.0.1:8000` 之外的地址。
2. 访问任何业务生成 endpoint。
3. 访问任何 export endpoint。
4. 访问任何 write-back endpoint。
5. 访问任何 review/apply endpoint。
6. 访问任何真实 KG endpoint。
7. 访问任何真实项目资料 endpoint。
8. 发送真实项目数据。
9. 发送真实招标文件内容。
10. 发送用户隐私数据。
11. 运行 Ollama。
12. 执行 `ollama list`。
13. 读取 `.env` / secrets / tokens / credentials。
14. 读取 registration / metadata / proof / manifest / sample 实例。
15. 读取 output/job/export 正文。
16. generation。
17. export。
18. write-back。
19. ZBid 写回。
20. trial。
21. 真实使用。
22. 50 人正式使用。
23. 修改 V0/V1/backend/frontend/config/dependency。
24. 创建脚本、App 包、Tauri/Electron 工程、runtime bridge。
25. 运行测试/lint/build。
26. 停止或重启服务，除非后续另行授权。

## 6. endpoint health check 阻断条件

未来 028 如出现以下任一情况，应判定 BLOCKED，不得访问 endpoint：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 025 STARTED 无法复核。
4. 026 PASS 无法复核。
5. 服务进程不存在。
6. 端口未处于 LISTEN。
7. 无法确认最小健康检查 endpoint。
8. 健康检查 endpoint 与业务生成、导出、写回、KG、项目资料有关。
9. endpoint 需要 token、secret、credential。
10. endpoint 会触发 Ollama。
11. endpoint 会读取真实 KG。
12. endpoint 会读取真实项目资料。
13. endpoint 会写 output/job/export。
14. endpoint 会触发 generation/export/write-back。
15. 访问 endpoint 需要读取 `.env` / secrets。
16. 无法在授权范围内确认边界。

## 7. 用户授权文本模板

用户后续如需进入 028，可直接复制以下授权文本：

`我明确授权 LOCAL-LAUNCHER-028 执行 endpoint health check execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 025 controlled start STARTED、复核 026 post-start status PASS、复核服务 PID 与监听端口、仅访问本地 127.0.0.1:8000 的最小健康检查 endpoint、仅记录 HTTP 状态码、非敏感响应摘要和响应时间。严格禁止访问除 127.0.0.1:8000 之外的地址，禁止访问业务生成、导出、写回、review/apply、真实 KG、真实项目资料相关 endpoint，禁止发送真实项目数据、真实招标文件内容或用户隐私数据，禁止运行 Ollama 或 ollama list，禁止读取 .env/secrets/tokens/credentials，禁止读取 registration/metadata/proof/manifest/sample 实例，禁止读取 output/job/export 正文，禁止触发 generation/export/write-back，禁止写 output/job/export，禁止进入 trial、真实使用或 50 人正式使用。若无法确认 endpoint 为最小健康检查 endpoint，或健康检查会触发 Ollama、真实数据读取、生成、导出、写回，必须判定 BLOCKED 并停止。健康检查完成或阻断后必须回报并停止，不得进入下一节点。`

## 8. 进入 028 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-028-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-EXECUTION-GATE`

若用户未授权，则 hold。

任何推荐、上游 PASS、当前 027 完成或 Codex 连续对话上下文，都不构成进入 028 的授权。

## 9. 禁止项确认

LOCAL-LAUNCHER-027 确认：

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
14. 未运行 Ollama。
15. 未执行 `ollama list`。
16. 未读取真实 KG。
17. 未读取真实项目资料。
18. 未读取真实招标文件。
19. 未读取 `.env` / secrets / tokens / credentials。
20. 未读取 registration / metadata / proof / manifest / sample 实例。
21. 未读取 output/job/export 正文。
22. 未读取日志正文。
23. 未触发 generation/export/write-back。
24. 未写 output/job/export。
25. 未进入 trial。
26. 未进入真实使用。
27. 未进入 50 人正式使用。
28. 未进入 `LOCAL-LAUNCHER-028`。

## 10. 实际执行命令清单

LOCAL-LAUNCHER-027 只执行 Git 状态确认和指定文档只读查看：

```bash
git status --short
git log -1 --format=%H
git tag --points-at HEAD
git log -1 --oneline
git diff --check
git diff --cached --check
sed -n '1,360p' docs/zdoc-local-launcher-v1-post-start-status-record-gate-local-launcher-026.md
sed -n '1,360p' docs/zdoc-local-launcher-v1-controlled-start-execution-gate-local-launcher-025.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-controlled-start-authorization-gate-local-launcher-024.md
sed -n '1,360p' docs/zdoc-local-launcher-v1-runtime-preflight-execution-gate-local-launcher-023.md
```

未执行进程检查、端口检查、服务状态检查、endpoint 请求、curl/HTTP request、Ollama 命令、测试、lint、build、启动、重启或停止命令。

## 11. 当前 decision

`LOCAL-LAUNCHER-027 ZDOC LOCAL APP V1 ENDPOINT HEALTH CHECK AUTHORIZATION GATE COMPLETED / ENDPOINT HEALTH CHECK EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO ENDPOINT ACCESSED / NO CURL OR HTTP REQUEST EXECUTED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 12. 下一节点建议

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-028-ZDOC-LOCAL-APP-V1-ENDPOINT-HEALTH-CHECK-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 028。
4. 028 即使后续被授权，也仅允许最小健康检查。
5. Ollama 运行必须另设授权门。
6. trial / generation / export / write-back 必须另设授权门。
7. 真实 KG / 真实项目资料读取必须另设授权门。
8. 50 人正式使用必须另设 readiness 与 deployment gate。
