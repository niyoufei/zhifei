# LOCAL-LAUNCHER-024 ZDoc Local App V1 Controlled Start Authorization Gate

## 1. 节点基本信息

- 节点名称：`LOCAL-LAUNCHER-024-ZDOC-LOCAL-APP-V1-CONTROLLED-START-AUTHORIZATION-GATE`
- 本节点性质：`controlled start authorization boundary and user authorization request only`
- 本节点产物：`docs/zdoc-local-launcher-v1-controlled-start-authorization-gate-local-launcher-024.md`
- 当前分支：`main`
- 当前基线 HEAD：`25a18a8e746238d3d7c6748d0fe869cbec01540b`
- 当前基线 tag：`v0.1.659-local-launcher-zdoc-local-app-v1-runtime-preflight-execution-gate`
- 上游节点：`LOCAL-LAUNCHER-023-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-EXECUTION-GATE`
- 023 runtime preflight 判定：`PASS`

本节点不执行 controlled start，不启动服务，不停止服务，不访问 endpoint，不运行 Ollama，不进入 `LOCAL-LAUNCHER-025`。

## 2. 上游节点通过状态

1. `LOCAL-LAUNCHER-017-ZDOC-LOCAL-APP-V1-PROFESSIONAL-UI-STATIC-UPGRADE-IMPLEMENTATION-GATE`：completed。
2. `LOCAL-LAUNCHER-018-ZDOC-LOCAL-APP-V1-PROFESSIONAL-UI-STATIC-UPGRADE-AUDIT-GATE`：passed。
3. `LOCAL-LAUNCHER-019-ZDOC-LOCAL-APP-V1-PROFESSIONAL-UI-USER-HANDOFF-AND-MANUAL-VERIFICATION-GATE`：completed。
4. `LOCAL-LAUNCHER-020-ZDOC-LOCAL-APP-V1-PROFESSIONAL-UI-MANUAL-VERIFICATION-RESULT-RECORD-GATE`：completed and PASS recorded。
5. `LOCAL-LAUNCHER-021-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-READINESS-AND-BOUNDARY-STRATEGY-GATE`：completed。
6. `LOCAL-LAUNCHER-022-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-AUTHORIZATION-GATE`：completed。
7. `LOCAL-LAUNCHER-023-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-EXECUTION-GATE`：completed and PASS recorded。

023 decision：

`LOCAL-LAUNCHER-023 ZDOC LOCAL APP V1 RUNTIME PREFLIGHT EXECUTION GATE PASSED / RUNTIME PREFLIGHT COMPLETED / CONTROLLED START AUTHORIZATION MAY BE CONSIDERED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 3. 当前系统状态摘要

1. V1 专业静态控制台已完成。
2. V1 专业静态控制台已通过用户人工验收。
3. runtime preflight readiness strategy 已完成。
4. runtime preflight authorization boundary 已完成。
5. runtime preflight execution 已完成且 PASS。
6. 当前仅具备进入 controlled start 授权边界记录的条件。
7. 当前仍不具备直接启动服务条件。
8. 当前仍不具备 endpoint 访问条件。
9. 当前仍不具备 Ollama 运行条件。
10. 当前仍不具备 trial / generation / export / write-back 条件。

V1 当前仍为 professional static console only。`local_launcher/v1/launcher-state.json` 中 `service_start_allowed`、`service_stop_allowed`、`endpoint_access_allowed`、`health_check_allowed`、`ollama_allowed`、`trial_allowed`、`generation_allowed`、`export_allowed`、`write_back_allowed`、`real_kg_read_allowed`、`real_project_data_read_allowed`、`controlled_execution_allowed` 均为 `false`。

## 4. 当前授权状态

1. 当前仅授权执行 `LOCAL-LAUNCHER-024` docs-only 授权边界记录。
2. 当前未授权执行 `LOCAL-LAUNCHER-025`。
3. 当前未授权启动服务。
4. 当前未授权停止服务。
5. 当前未授权访问 endpoint。
6. 当前未授权执行 curl / HTTP request。
7. 当前未授权运行 Ollama。
8. 当前未授权执行 `ollama list` 或任何 Ollama 模型命令。
9. 当前未授权读取真实 KG。
10. 当前未授权读取真实项目资料。
11. 当前未授权读取真实招标文件。
12. 当前未授权读取 `.env` / secrets / tokens / credentials。
13. 当前未授权 trial。
14. 当前未授权 generation / export / write-back。
15. 当前未授权 ZBid 写回。
16. 当前未授权进入真实使用或 50 人正式使用。

## 5. controlled start 的定义边界

必须按以下层级拆分，不能跨级执行：

1. `controlled start authorization gate`：仅记录授权边界，不启动服务。
2. `controlled start execution gate`：未来如获用户明确授权，才可启动本地服务。
3. `post-start status record gate`：启动后仅记录状态，不访问 endpoint。
4. `endpoint health check authorization gate`：endpoint 健康检查授权。
5. `endpoint health check execution gate`：endpoint 健康检查执行。
6. `trial authorization gate`：小范围试用授权。
7. `trial execution gate`：小范围试用执行。
8. `50-user deployment readiness gate`：50 人正式部署准备，不得提前进入。

LOCAL-LAUNCHER-024 仅属于第 1 层：`controlled start authorization gate`。

## 6. 未来 025 可授权范围草案

以下仅为草案，不在 LOCAL-LAUNCHER-024 执行。

未来若用户明确授权 `LOCAL-LAUNCHER-025`，controlled start execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 023 runtime preflight PASS。
6. 复核启动命令文本来源。
7. 使用 023 已识别的非敏感启动命令启动本地 ZDoc 服务。
8. 仅观察启动命令 stdout/stderr 中的非敏感启动状态。
9. 启动后确认本地进程是否存在。
10. 启动后确认端口是否处于监听状态。
11. 记录 PID、端口、启动时间、命令来源。
12. 不访问 endpoint。
13. 不执行 curl / HTTP request。
14. 不运行 Ollama 命令。
15. 不读取真实 KG。
16. 不读取真实项目资料。
17. 不触发 generation/export/write-back。
18. 启动完成后停止推进，等待 ChatGPT 总控师审核。

未来 025 即使被授权，也仍不得访问 endpoint。endpoint 健康检查必须另设授权门和执行门。

## 7. 未来 025 禁止范围草案

未来 025 仍应禁止：

1. endpoint 访问。
2. curl / HTTP request。
3. Ollama 命令。
4. `ollama list`。
5. 读取真实 KG。
6. 读取真实项目资料。
7. 读取真实招标文件。
8. 读取用户隐私或业务数据。
9. 读取 `.env` / secrets / tokens / credentials。
10. 读取 registration / metadata / proof / manifest / sample 实例。
11. 读取 output/job/export 正文。
12. generation。
13. export。
14. write-back。
15. ZBid 写回。
16. trial。
17. 真实使用。
18. 50 人正式使用。
19. 修改 V0/V1/backend/frontend/config/dependency。
20. 创建脚本、App 包、Tauri/Electron 工程、runtime bridge。
21. 运行测试/lint/build。
22. 未授权停止服务。

## 8. controlled start 阻断条件

未来 025 如出现以下任一情况，应判定 BLOCKED，不得启动服务：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 启动命令来源不清晰。
4. 启动命令需要读取 `.env` / secrets / tokens / credentials。
5. 启动命令会自动访问 endpoint。
6. 启动命令会自动运行 Ollama。
7. 启动命令会自动读取真实 KG。
8. 启动命令会自动读取真实项目资料。
9. 启动命令会自动触发 generation/export/write-back。
10. 启动命令会写 output/job/export。
11. 端口已被疑似 ZDoc 服务占用。
12. 服务已经运行且状态不明确。
13. 无法在授权范围内确认边界。

## 9. 用户授权文本模板

用户后续如需进入 025，可直接复制以下授权文本：

`我明确授权 LOCAL-LAUNCHER-025 执行 controlled start execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 023 runtime preflight PASS、复核非敏感启动命令文本来源、使用 023 已识别的非敏感启动命令启动本地 ZDoc 服务、观察启动命令 stdout/stderr 中的非敏感启动状态、确认本地进程是否存在、确认端口是否处于监听状态、记录 PID、端口、启动时间、命令来源。严格禁止访问 endpoint、执行 curl/HTTP request、运行 Ollama、执行 ollama list、读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 .env/secrets/tokens/credentials、读取 registration/metadata/proof/manifest/sample 实例、读取 output/job/export 正文、触发 generation/export/write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用、进入 endpoint health check。若启动命令需要读取敏感配置、会自动访问 endpoint、会自动运行 Ollama、会自动读取真实数据或会自动触发生成/导出/写回，必须判定 BLOCKED 并停止。启动完成或阻断后必须回报并停止，不得进入下一节点。`

## 10. 进入 025 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-025-ZDOC-LOCAL-APP-V1-CONTROLLED-START-EXECUTION-GATE`

若用户未授权，则 hold。

任何推荐、上游 PASS、当前 024 完成或 Codex 连续对话上下文，都不构成进入 025 的授权。

## 11. 禁止项确认

LOCAL-LAUNCHER-024 确认：

1. 未修改 V1 页面产物。
2. 未修改 V0。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未运行 npm/yarn/pnpm/pip。
7. 未运行测试/lint/build。
8. 未打开 HTML 页面。
9. 未启动服务。
10. 未停止服务。
11. 未访问 endpoint。
12. 未执行 curl / HTTP request。
13. 未运行 Ollama。
14. 未执行 `ollama list`。
15. 未读取真实 KG。
16. 未读取真实项目资料。
17. 未读取真实招标文件。
18. 未读取 `.env` / secrets / tokens / credentials。
19. 未读取 registration / metadata / proof / manifest / sample 实例。
20. 未读取 output/job/export 正文。
21. 未触发 generation/export/write-back。
22. 未写 output/job/export。
23. 未进入 trial。
24. 未进入真实使用。
25. 未进入 50 人正式使用。
26. 未进入 endpoint health check。
27. 未进入 `LOCAL-LAUNCHER-025`。

## 12. 实际执行命令清单

LOCAL-LAUNCHER-024 只执行了授权范围内的 Git 状态确认和指定文件只读查看：

```bash
git status --short
git log -1 --format=%H
git log -1 --oneline --decorate
git tag --points-at HEAD
sed -n '1,260p' docs/zdoc-local-launcher-v1-runtime-preflight-execution-gate-local-launcher-023.md
sed -n '261,380p' docs/zdoc-local-launcher-v1-runtime-preflight-execution-gate-local-launcher-023.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-runtime-preflight-authorization-gate-local-launcher-022.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-runtime-preflight-readiness-and-boundary-strategy-gate-local-launcher-021.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-professional-ui-manual-verification-result-record-gate-local-launcher-020.md
sed -n '1,220p' local_launcher/v1/README.md
sed -n '1,220p' local_launcher/v1/launcher-state.json
```

未执行端口检查、进程检查、服务状态检查、endpoint 请求、curl/HTTP request、Ollama 命令、测试、lint、build 或启动/停止命令。

## 13. 当前 decision

`LOCAL-LAUNCHER-024 ZDOC LOCAL APP V1 CONTROLLED START AUTHORIZATION GATE COMPLETED / CONTROLLED START EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 14. 下一节点建议

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-025-ZDOC-LOCAL-APP-V1-CONTROLLED-START-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 025。
4. 025 即使后续被授权，也仍不得访问 endpoint。
5. endpoint health check 必须另设后续授权门。
6. trial / generation / export / write-back 必须另设后续授权门。
