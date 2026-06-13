# LOCAL-LAUNCHER-022 ZDOC Local App V1 Runtime Preflight Authorization Gate

## 1. Node Basic Information

- Node: `LOCAL-LAUNCHER-022-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-AUTHORIZATION-GATE`
- Scope: runtime preflight authorization boundary and user authorization request only.
- Target artifact: `docs/zdoc-local-launcher-v1-runtime-preflight-authorization-gate-local-launcher-022.md`
- Current branch: `main`
- Starting HEAD: `cba33e40551b3a02ce96f3af9fe3e1f9ce725d0a`
- Starting tag: `v0.1.657-local-launcher-zdoc-local-app-v1-runtime-preflight-readiness-and-boundary-strategy-gate`
- Starting worktree status: clean

Upstream status:

1. `LOCAL-LAUNCHER-017-ZDOC-LOCAL-APP-V1-PROFESSIONAL-UI-STATIC-UPGRADE-IMPLEMENTATION-GATE`: completed.
2. `LOCAL-LAUNCHER-018-ZDOC-LOCAL-APP-V1-PROFESSIONAL-UI-STATIC-UPGRADE-AUDIT-GATE`: passed.
3. `LOCAL-LAUNCHER-019-ZDOC-LOCAL-APP-V1-PROFESSIONAL-UI-USER-HANDOFF-AND-MANUAL-VERIFICATION-GATE`: completed.
4. `LOCAL-LAUNCHER-020-ZDOC-LOCAL-APP-V1-PROFESSIONAL-UI-MANUAL-VERIFICATION-RESULT-RECORD-GATE`: completed and PASS recorded.
5. `LOCAL-LAUNCHER-021-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-READINESS-AND-BOUNDARY-STRATEGY-GATE`: completed.

This node does not execute runtime preflight.

## 2. Current Authorization Status

Current authorization status:

1. LOCAL-LAUNCHER-022 authorizes only docs-only authorization boundary recording.
2. LOCAL-LAUNCHER-023 runtime preflight execution is not authorized.
3. Runtime preflight execution is not authorized.
4. Service startup is not authorized.
5. Service stop is not authorized.
6. Endpoint access is not authorized.
7. curl / HTTP request execution is not authorized.
8. Ollama command execution is not authorized.
9. `ollama list` and any Ollama model command are not authorized.
10. Real KG reading is not authorized.
11. Real project material reading is not authorized.
12. Real bidding-file reading is not authorized.
13. `.env`, secrets, tokens, credentials, keys, and private configuration reading is not authorized.
14. trial is not authorized.
15. generation/export/write-back is not authorized.
16. ZBid write-back is not authorized.
17. Real use and 50-user formal use are not authorized.

## 3. Future LOCAL-LAUNCHER-023 Allowed Scope Draft

This section is only a future authorization draft. It is not executed in LOCAL-LAUNCHER-022.

If the user later explicitly authorizes `LOCAL-LAUNCHER-023`, runtime preflight execution should be limited to:

1. Repository path confirmation.
2. Current branch confirmation.
3. HEAD/tag confirmation.
4. Worktree clean confirmation.
5. Non-sensitive directory structure confirmation.
6. Non-sensitive startup instruction file identification.
7. Non-sensitive package / dependency manifest file identification.
8. Non-sensitive startup command text identification.
9. Local port occupancy check.
10. Local process status check.
11. Service-not-running state check.
12. Log directory path identification, without reading real log bodies.
13. Configuration template identification, without reading `.env`, secrets, tokens, or credentials.
14. output/job/export directory existence identification, without reading bodies.
15. Preflight failure stop-condition confirmation.
16. Required conditions for a later controlled start authorization gate.

Even if LOCAL-LAUNCHER-023 is later authorized, it must still not start service, access endpoint, run Ollama, read real KG, read real project materials, or trigger generation/export/write-back.

## 4. Future LOCAL-LAUNCHER-023 Prohibited Scope Draft

Future LOCAL-LAUNCHER-023 should still prohibit:

1. Service startup.
2. Service stop, unless separately authorized later.
3. Endpoint access.
4. curl / HTTP request execution.
5. Ollama commands.
6. `ollama list`.
7. Real KG reads.
8. Real project material reads.
9. Real bidding-file reads.
10. User private-data reads.
11. `.env`, secrets, tokens, credentials, keys, and private configuration reads.
12. registration / metadata / proof / manifest / sample instance reads.
13. output/job/export body reads.
14. generation.
15. export.
16. write-back.
17. ZBid write-back.
18. trial.
19. real use.
20. 50-user formal use.

## 5. User Authorization Text Template

The user may copy the following text in a later message to authorize LOCAL-LAUNCHER-023:

`我明确授权 LOCAL-LAUNCHER-023 执行 runtime preflight execution。授权范围仅限：仓库状态、分支、HEAD/tag、工作区 clean、非敏感目录结构、非敏感启动说明、非敏感 package/dependency manifest、非敏感启动命令文本识别、本地端口占用检查、本地进程状态检查、服务未运行状态检查、日志目录路径识别但不读取日志正文、配置模板识别但不读取 .env/secrets/tokens/credentials、output/job/export 目录存在性识别但不读取正文、预检失败停止条件确认。禁止启动服务、停止服务、访问 endpoint、执行 curl/HTTP request、运行 Ollama、执行 ollama list、读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 registration/metadata/proof/manifest/sample 实例、触发 generation/export/write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用。预检完成后必须回报并停止，不得进入 controlled start。`

## 6. Conditions for Entering LOCAL-LAUNCHER-023

LOCAL-LAUNCHER-023 may be entered only if the user later explicitly sends authorization text for:

`LOCAL-LAUNCHER-023-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-EXECUTION-GATE`

If the user does not explicitly authorize LOCAL-LAUNCHER-023, the state is hold.

No implicit continuation, prior recommendation, or current LOCAL-LAUNCHER-022 completion authorizes LOCAL-LAUNCHER-023.

## 7. Prohibited Action Confirmation

LOCAL-LAUNCHER-022 confirms:

1. V1 page artifacts were not modified.
2. V0 artifacts were not modified.
3. backend/frontend/config/dependency files were not modified.
4. No JavaScript file was added.
5. No script was created.
6. npm/yarn/pnpm/pip was not run.
7. Tests/lint/build were not run.
8. HTML page was not opened.
9. Runtime preflight was not executed.
10. Port checks were not executed.
11. Process checks were not executed.
12. Service status checks were not executed.
13. No service was run.
14. No service was stopped.
15. No endpoint was accessed.
16. No curl / HTTP request was executed.
17. Ollama was not run.
18. Real KG was not read.
19. Real project materials were not read.
20. `.env`, secrets, tokens, credentials, keys, and private configuration were not read.
21. registration / metadata / proof / manifest / sample instances were not read.
22. output/job/export bodies were not read.
23. generation/export/write-back was not triggered.
24. output/job/export was not written.
25. trial was not entered.
26. real use was not entered.
27. 50-user formal use was not entered.
28. `LOCAL-LAUNCHER-023` was not entered.

## 8. Current Decision

`LOCAL-LAUNCHER-022 ZDOC LOCAL APP V1 RUNTIME PREFLIGHT AUTHORIZATION GATE COMPLETED / RUNTIME PREFLIGHT EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO RUNTIME PREFLIGHT EXECUTED / NO PORT OR PROCESS CHECK EXECUTED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO REAL KG OR PROJECT DATA READ / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

This decision is based only on allowed LOCAL-LAUNCHER documentation reads and this authorization boundary document. It does not rely on runtime state, port state, process state, service state, endpoint output, Ollama output, real KG, real project material, `.env`, secrets, tokens, credentials, registration, metadata, proof, manifest, sample, output, job, or export bodies.

## 9. Next Node Suggestion

If the user explicitly authorizes, the next suggested node is:

`LOCAL-LAUNCHER-023-ZDOC-LOCAL-APP-V1-RUNTIME-PREFLIGHT-EXECUTION-GATE`

If the user does not authorize, the state is hold.

LOCAL-LAUNCHER-022 does not enter LOCAL-LAUNCHER-023.

Even if LOCAL-LAUNCHER-023 is later authorized, it must still not start service.

Controlled start must require a later separate authorization gate.
