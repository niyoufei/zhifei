# LOCAL-LAUNCHER-002 ZDoc Local App Code Implementation Authorization Gate

## 1. Node

- Node: `LOCAL-LAUNCHER-002-ZDOC-LOCAL-APP-CODE-IMPLEMENTATION-AUTHORIZATION-GATE`
- Node type: docs-only / code-implementation-authorization-gate.
- Scope: record whether later local App / launcher code implementation may start, the draft implementation boundary, forbidden scope, blocking conditions, report format, and user authorization text template.
- This node is not a code implementation node.
- This node does not authorize entry into `LOCAL-LAUNCHER-003`.

## 2. Start State

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Start HEAD: `4ffee826471c9185258e7922a81131d976eb465b`
- Start tag at HEAD: none.
- Prior `LOCAL-LAUNCHER-001` docs commit: `80ef4250656471cef8ce6bf90dce93f32af23017`
- Prior `LOCAL-LAUNCHER-001` tag: `v0.1.625-local-launcher-zdoc-local-app-requirements-and-safety-gate`
- Prior `LOCAL-LAUNCHER-001` tag target: `80ef4250656471cef8ce6bf90dce93f32af23017`
- Worktree preflight: `git status --short` was clean.
- Target docs file preflight: `docs/zdoc-local-launcher-v1-code-implementation-authorization-gate-local-launcher-002.md` did not exist.
- Target tag preflight: `v0.1.626-local-launcher-zdoc-local-app-code-implementation-authorization-gate` did not exist locally.

## 3. Prior Review Conclusion

`LOCAL-LAUNCHER-001 可审核通过`

The prior gate is accepted as the requirement and safety basis for this authorization boundary.

## 4. `LOCAL-LAUNCHER-001` Docs Summary

`LOCAL-LAUNCHER-001` defines the local App / local launcher as a future local control surface for operating the ZDoc local workflow on the user's Mac. It is not the ZDoc generation engine, not a KG reader, not an Ollama model runner, and not a trial or production usage surface.

The 001 route keeps the launcher local-only and audit-first. A later implementation may present state and allowed actions, but it must not auto-run services. Any command execution must be mediated by a small allowlisted command layer after a separate gate authorizes code work.

The 001 boundary allows only explicitly approved future controls such as local service status summaries, configured port and process summaries, selected non-sensitive log summaries, safe configuration readiness summaries, visible warnings, and structured status reports.

The 001 boundary forbids ZDoc generation/export/write-back, real KG reads, real project material reads, real bidding document reads, secret reads, registration/metadata/proof/manifest/sample instance reads, output/job/export body reads, full log body reads, endpoint access, HTTP requests, Ollama model inference, prompt input to a model, trial, real use, and 50-person formal use.

The 001 gate states that no launcher code, scripts, App package, dependency changes, or runtime controls may be created until a later implementation gate defines exact files, form factor, dependencies, commands, UI scope, test scope, verification scope, and prohibitions.

## 5. Later Code Implementation Goal

A later `LOCAL-LAUNCHER-003` may be authorized to implement a minimal local App / launcher code skeleton inside the existing safety boundary.

The implementation goal would be limited to a visible local operator surface that can show static or mock readiness state and provide a constrained shell for later controls. It must preserve auditability, explicit user action, and separation from generation, export, write-back, KG access, project-data access, endpoint probing, service startup, Ollama execution, trial, and production use.

## 6. Draft Allowed Scope For Later `LOCAL-LAUNCHER-003`

If separately authorized, `LOCAL-LAUNCHER-003` may allow only the following draft scope:

- Implement a minimal local App / launcher code skeleton inside the existing repository conventions.
- Implement static UI or a local startup-control shell only.
- Use non-sensitive configuration templates or mock configuration only.
- Add only the exact files named by the later 003 authorization.
- Keep all actions local to the user's Mac.
- Display safety copy and visible disabled states for unapproved runtime actions.
- Keep service controls, endpoint probes, generation, export, write-back, model inference, and real data access disabled or absent unless a later separate gate authorizes them.
- Complete with a report and stop for ChatGPT total-controller review.

## 7. Draft Forbidden Scope For Later `LOCAL-LAUNCHER-003`

Unless a later gate explicitly changes the boundary, `LOCAL-LAUNCHER-003` must not:

- Modify V0 surfaces.
- Modify V1 surfaces outside the exact files named by the later 003 authorization.
- Modify backend, frontend, config, dependency, or runtime surfaces outside the exact 003 allowlist.
- Install npm, yarn, pnpm, pip, or other dependencies.
- Create a real packaged App.
- Start, restart, or stop ZDoc services.
- Start, restart, or stop Ollama server.
- Execute any Ollama command.
- Run model inference.
- Input prompts to a model.
- Access endpoints.
- Execute `curl` or other HTTP requests.
- Read real KG.
- Read real project materials.
- Read real bidding documents.
- Read `.env`, secrets, tokens, credentials, private keys, cookies, or account material.
- Read registration, metadata, proof, manifest, or sample instances.
- Read output/job/export bodies.
- Read log bodies.
- Trigger generation, export, or write-back.
- Write output/job/export.
- Enter trial.
- Enter real use or 50-person formal use.
- Auto-enter any later node.

## 8. Blocking Conditions For Later `LOCAL-LAUNCHER-003`

`LOCAL-LAUNCHER-003` must be blocked if any of the following conditions exists:

- The user has not provided explicit text authorizing `LOCAL-LAUNCHER-003`.
- The later authorization does not name exact files allowed for creation or modification.
- The later authorization would require real KG, real project materials, real bidding documents, secrets, output/job/export bodies, or log bodies.
- The later authorization would require endpoint access, HTTP requests, ZDoc service startup, Ollama server actions, any Ollama command, model inference, or prompt input to a model.
- The later authorization would require generation, export, write-back, trial, real use, or 50-person formal use.
- The repository is not at the expected branch, HEAD, or tag baseline required by the later gate.
- The worktree is not clean before the later gate begins.
- The target 003 artifact or implementation files already exist and the gate does not authorize how to handle them.
- The later gate conflicts with the 001 or 002 safety boundary.

## 9. Later Code Implementation Report Format

A later `LOCAL-LAUNCHER-003` report must include:

1. Whether `LOCAL-LAUNCHER-003` completed or was blocked.
2. Start HEAD / tag.
3. End HEAD.
4. `git status --short` clean status.
5. Actual modified files.
6. Actual added files.
7. Whether only the authorized files were changed.
8. Whether V0/V1/backend/frontend/config/dependency surfaces were changed.
9. Whether JS/TS/Python/Shell scripts were added.
10. Whether a real App package was created.
11. Whether npm/yarn/pnpm/pip install commands were run.
12. Whether tests/lint/build were run.
13. Whether any HTML page was opened.
14. Whether ZDoc service was started, restarted, or stopped.
15. Whether Ollama server was started, restarted, or stopped.
16. Whether any Ollama command was executed.
17. Whether any endpoint was accessed.
18. Whether any `curl` or HTTP request was executed.
19. Whether model inference was executed.
20. Whether any prompt was input to a model.
21. Whether real KG was read.
22. Whether real project materials were read.
23. Whether real bidding documents were read.
24. Whether `.env` / secrets / tokens / credentials were read.
25. Whether registration / metadata / proof / manifest / sample instances were read.
26. Whether output/job/export body content was read.
27. Whether log body content was read.
28. Whether generation/export/write-back was triggered.
29. Whether output/job/export was written.
30. Whether trial was entered.
31. Whether real use or 50-person formal use was entered.
32. Current decision.
33. Next-node recommendation.
34. Verification commands and results, limited to the later authorization.
35. Commit hash, if a commit was authorized and created.
36. Remote tag status, if a tag was authorized and pushed.
37. Whether the next node was entered.

## 10. User Authorization Text Template

The user may authorize the later implementation gate only with an explicit message like:

```text
我现在明确授权执行：

LOCAL-LAUNCHER-003-ZDOC-LOCAL-APP-MINIMAL-CODE-SKELETON-IMPLEMENTATION

仅允许在 001/002 记录的安全边界内实现本地 App / 启动器最小代码骨架。

允许范围：
1. 仅创建或修改本授权中明确列出的文件；
2. 仅实现静态 UI 或本地启动控制壳层；
3. 仅读取非敏感配置模板或 mock 配置；
4. 不接入真实 KG；
5. 不读取真实项目资料；
6. 不访问 endpoint；
7. 不启动服务；
8. 不运行 Ollama；
9. 不触发 generation/export/write-back；
10. 不进入 trial 或真实使用；
11. 完成后回报并停止，等待 ChatGPT 总控师审核。

禁止范围：
1. 不得修改未列入 allowlist 的 V0/V1/backend/frontend/config/dependency 文件；
2. 不得安装依赖；
3. 不得创建真正 App 包；
4. 不得启动、重启、停止 ZDoc 或 Ollama；
5. 不得执行 endpoint / curl / HTTP request；
6. 不得读取真实 KG、真实项目资料、真实招标文件、secrets、output/job/export 正文或日志正文；
7. 不得触发 generation/export/write-back；
8. 不得进入 LOCAL-LAUNCHER-004。
```

Without an explicit user authorization text for `LOCAL-LAUNCHER-003`, no code implementation may start.

## 11. Current Node Execution Negatives

During this node:

- Code implemented: no.
- Script created: no.
- App created: no.
- Service started: no.
- Service restarted: no.
- Service stopped: no.
- Endpoint accessed: no.
- HTTP request executed: no.
- `curl` executed: no.
- Ollama server started, restarted, or stopped: no.
- Any Ollama command executed: no.
- Model inference executed: no.
- Prompt input to model: no.
- Real KG read: no.
- Real project data read: no.
- Real bidding documents read: no.
- `.env` / secrets / tokens / credentials read: no.
- Registration / metadata / proof / manifest / sample instances read: no.
- Output/job/export body read: no.
- Log body read: no.
- Generation/export/write-back triggered: no.
- Output/job/export written: no.
- Trial entered: no.
- Real use or 50-person formal use entered: no.
- `LOCAL-LAUNCHER-003` entered: no.

## 12. Current Decision

`LOCAL-LAUNCHER-002 ZDOC LOCAL APP CODE IMPLEMENTATION AUTHORIZATION GATE COMPLETED / CODE IMPLEMENTATION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO CODE IMPLEMENTED / NO SCRIPT CREATED / NO APP CREATED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED / STOPPED BEFORE LOCAL-LAUNCHER-003`

## 13. Stop

Stop after this node and report for ChatGPT total-controller review. Do not enter `LOCAL-LAUNCHER-003`.
