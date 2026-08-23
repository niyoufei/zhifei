# LOCAL-LAUNCHER-027A Independent Runtime Authorization Governance Design

## 1. Node Metadata

| Field | Value |
| --- | --- |
| Node | `LOCAL-LAUNCHER-027A-INDEPENDENT-RUNTIME-AUTHORIZATION-GOVERNANCE-DESIGN` |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `main` |
| Baseline HEAD | `7fda74e843c655eaec2db509309266a30b599abb` |
| Baseline Tag | `v0.1.706-local-launcher-026g-static-governance-closure-archive-gate` |
| Previous Gates | `LOCAL-LAUNCHER-026G-INDEPENDENT-LINE-STATIC-GOVERNANCE-CLOSURE-ARCHIVE-GATE`; `LOCAL-LAUNCHER-027-INDEPENDENT-RUNTIME-READINESS-PREFLIGHT-AUDIT` |
| Execution Type | runtime authorization governance design only |
| Write Scope | only this document: `docs/zdoc-local-launcher-027a-independent-runtime-authorization-governance-design.md` |
| Runtime Policy | forbidden in 027A |
| Service Policy | no service start, stop, restart, watchdog, or background execution |
| Localhost Policy | no localhost or `127.0.0.1` access |
| Endpoint Policy | no endpoint call, no health check, no smoke |
| Ollama / Model Policy | no Ollama, no model inference, no model endpoint call |
| Browser Policy | no browser open, no browser acceptance |
| Screenshot Policy | no screenshot |

The 026G archive records LOCAL-LAUNCHER as `pause / archived / no-runtime` and states that no runtime, endpoint, localhost, Ollama, model inference, browser, screenshot, service startup, port probe, health check, script execution, `.app` execution, test, build, install, or live acceptance authority can be inferred from that archive.

## 2. Purpose

This node is not a development node.

This node is not a runtime node.

This node is not service start authorization.

This node is not localhost access authorization.

This node is not endpoint verification authorization.

This node is not Ollama or model inference authorization.

This node only designs the governance framework for future runtime authorization. Any later runtime action must be placed in a separate independent node with an explicit command whitelist, forbidden command list, stop conditions, rollback method, writable scope, runtime scope, and acceptance method.

027A converts the 027 read-only audit facts into a bounded authorization model. It does not prove service health, port availability, process state, log state, model availability, endpoint correctness, or browser behavior.

## 3. Runtime Authorization Principles

1. Static Closure Inheritance Principle: the 026G `pause / archived / no-runtime` status continues to constrain 027A and all future LOCAL-LAUNCHER runtime work until a later independent gate explicitly changes it.
2. Explicit Runtime Grant Principle: any runtime action not explicitly authorized in a node remains forbidden, even if the command exists in scripts, README, RUNBOOK, `.app` launchers, or code.
3. One-Step Runtime Principle: each future node may authorize only one minimum runtime action. A single node must not combine service start, browser access, endpoint checks, watchdog, and model calls.
4. Stop-Before-Start Principle: future runtime authorization must define stop and rollback rules before any start command is allowed.
5. No-Watchdog-First Principle: the first runtime authorization must not enable watchdog, self-heal, launchd, or automatic restart chains.
6. No-App-Bypass Principle: the first runtime authorization must not use `.app` launchers because they hide command details and can bypass command-line control.
7. No-Model-First Principle: the first runtime authorization must not touch Ollama, `localhost:11434`, `/actions/ollama/*`, `/local-llm/preview-safe`, or any model inference path.
8. No-Browser-First Principle: the first runtime authorization must not automatically open a browser or use browser acceptance as a substitute for command and stop control.
9. Diff-Bounded Governance Principle: governance-node acceptance is based on diff scope, document content, and stated boundaries. Runtime results cannot replace boundary review.
10. Stop-on-Breach Principle: if a future stage observes out-of-scope runtime behavior, unexpected port ownership, PID/log/runtime anomalies, unplanned endpoint access, browser auto-open, or model-call signals, it must stop and report without broadening scope.

## 4. Runtime Entry Classification

| Entry | Type | Static Evidence | Runtime Capability | Initial Authorization Status | Future Authorization Requirement | Control Rule |
| --- | --- | --- | --- | --- | --- | --- |
| `scripts/run_web_ui.sh` | runtime-entry | Defines `BACKEND_PORT=8010`, `WEB_PORT=8501`, `.runtime/docgen` PID files, `uvicorn`, `streamlit`, `curl`, `lsof`, and `open` references. | Can start backend and frontend, write PID/log files, probe ports, health check, and open browser. | forbidden / not authorized | Must wait for R1 command whitelist and later isolated backend/frontend stages. | Do not use as first runtime command because it combines multiple runtime actions. |
| `scripts/start_web_ui_background.sh` | background-entry | Delegates to `./scripts/run_web_ui.sh --background` and writes `logs/webui_control.log`. | Can start background runtime through the combined launcher. | forbidden / not authorized | May only be considered after stop/rollback and single-shot foreground behavior are proven. | Keep disabled in initial runtime stages. |
| `scripts/web_ui_watchdog.sh` | watchdog-entry | Checks backend/web ports and restarts `run_web_ui.sh --background` when listeners are missing. | Can auto-restart services and extend runtime beyond a single action. | forbidden / not authorized | Only a late-stage service-management gate may consider it. | Never enable before stop/rollback is verified. |
| `scripts/stop_web_ui_background.sh` | stop-entry | Reads PID files under `.runtime/docgen`, inspects process command/cwd, uses port fallback. | Can stop backend, frontend, and watchdog processes if verified as this project. | forbidden / not authorized in 027A | Must be white-listed before any future start command. | Future use must be explicit and must not read PID/log bodies before authorized. |
| `文档生成系统.app` | desktop-bypass-entry | Shell launcher delegates to `scripts/start_web_ui_background.sh` through Terminal/osascript. | Can trigger background start without the user seeing exact command flow. | forbidden / not authorized | Only after command-line flow and rollback are proven. | No `.app` use in first runtime authorization. |
| `施组专家系统.app` | desktop-bypass-entry | Shell launcher contains `127.0.0.1:8501`, `_stcore/health`, `127.0.0.1:8010/health`, `curl`, `start_web_ui_background.sh`, `stop_web_ui_background.sh`, and `open`. | Can health-check, start, stop, open browser, and open logs. | forbidden / not authorized | Only a dedicated desktop-launcher gate may authorize it. | Treat as a bypass surface, not as a safe first entry. |
| `app.py` | frontend-runtime | Imports Streamlit, defaults backend base URL to `http://127.0.0.1:8010`, contains health and Ollama preview UI calls. | Can issue frontend-originated backend and model-related requests when running. | forbidden / not authorized | Frontend stage must follow backend start/stop validation. | Do not start until backend control is established. |
| `backend/app/main.py` | backend-runtime | Defines `app = FastAPI()`, includes routers, and exposes `/health`. | Can serve backend endpoints when uvicorn starts it. | forbidden / not authorized | Earliest possible runtime target after R1, limited to one backend start action. | Future backend start must be single-shot and stop-aware. |
| README / RUNBOOK startup instructions | documentation-reference | README and RUNBOOK contain `uvicorn`, `curl`, `lsof`, `127.0.0.1:8000`, Web UI, and launchd instructions. | Can be misread as current runtime authorization. | forbidden / not authorized | Future docs alignment may be separate from runtime execution. | Documentation examples do not grant runtime authority. |
| `/health` | endpoint-reference | Exposed by `backend/app/main.py`; README/RUNBOOK reference health checks. | Can verify service availability when a service is running. | forbidden / not authorized | R3 only, after R2 backend start and stop control. | No health check before explicit endpoint gate. |
| `/local-llm/preview-safe` | model-endpoint-reference | `backend/app/main.py` includes `local_llm_preview_safe_router`; router defines the safe endpoint path. | Can enter local LLM preview safe endpoint flow. | forbidden / not authorized | R6 or a later model-specific gate only. | No model endpoint access during service start or browser stages. |
| `/actions/ollama/*` | model-endpoint-reference | `app.py` and `backend/app/routers/actions_bridge.py` reference Ollama preview, review, section draft, and smoke endpoints. | Can enter Ollama or model-related preview/smoke flows if enabled and running. | forbidden / not authorized | R6 only, with separate model command, port, and no-write controls. | Keep entirely out of R1 through R5. |

## 5. Authorization Stage Design

No stage below is executed by 027A. All listed commands are policy candidates only, and only a future node may authorize them.

| Stage | Entry Condition | Allowed Commands | Forbidden Commands | Writable Scope | Runtime Scope | Stop Condition | Rollback Rule | Acceptance Method | Blocking Rule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R0: Governance Design | Current 027A baseline matches `7fda74e843c655eaec2db509309266a30b599abb`; worktree clean. | Static read commands and write to this document only. | Service start, localhost, endpoint, `.app`, curl, lsof, open, streamlit, uvicorn, ollama, tests, build, install. | This 027A document only. | None. | Stop on baseline mismatch or out-of-scope diff. | Revert only the 027A document if needed; do not touch runtime artifacts. | Diff scope, `git diff --check`, clean post-commit state. | Any non-target file diff blocks completion. |
| R1: Command Whitelist + Stop/Rollback Gate | 027A completed and accepted. | Governance-document edits only; exact future command whitelist design. | Service start, localhost, endpoint, curl, lsof, open, streamlit, uvicorn, ollama, tests, build, install. | A future 027B governance document only. | None. | Stop if whitelist includes combined start, watchdog, `.app`, model, or browser in first runtime action. | Remove unsafe commands from the whitelist before proceeding. | Static diff review only. | Any executable runtime action blocks R1. |
| R2: Single-Shot Backend Start Authorization | R1 accepted; stop command and rollback procedure pre-approved. | A future node may allow exactly one backend start command selected by R1. | Frontend start, browser open, watchdog, `.app`, Ollama/model, endpoint smoke beyond start readiness. | Future runtime report only if explicitly allowed. | Backend only. | Stop if unexpected process, port, PID/log anomaly, auto-open, or model signal appears. | Run the pre-approved stop procedure; report result; do not repair broadly. | Command transcript and bounded runtime report. | Missing stop path or unexpected runtime behavior blocks R2. |
| R3: Backend Health Check Authorization | R2 start succeeded and stop/rollback is demonstrably available. | A future node may allow one minimum health check selected by R1/R3. | Browser, frontend, watchdog, `.app`, model endpoint, broad API smoke. | Future health-check report only if explicitly allowed. | Backend `/health` only. | Stop if health check accesses any other endpoint or needs unplanned command. | Stop backend using the pre-approved stop path if health check fails. | Health response evidence and stop evidence. | Any endpoint expansion blocks R3. |
| R4: Frontend Start Authorization | Backend start, health, stop, and rollback have been validated in prior nodes. | A future node may allow one controlled frontend start command. | Automatic browser open, watchdog, `.app`, Ollama/model, generation/export/write-back. | Future frontend-start report only if explicitly allowed. | Frontend only, bound to pre-approved backend. | Stop if browser opens, unexpected endpoint calls occur, or frontend starts background chains. | Stop frontend first, then backend if needed, using approved procedures. | Process/command evidence and no-browser evidence. | Any auto-open or watchdog behavior blocks R4. |
| R5: Browser Manual Acceptance Authorization | Frontend start/stop is controlled and no auto-open is present. | A future node may allow a single browser acceptance action. | Ollama/model, generation/export/write-back, broad endpoint testing, `.app` launchers. | Future browser acceptance report only if explicitly allowed. | Browser access to the approved UI only. | Stop if browser triggers model, export, write-back, or unplanned endpoint flows. | Close browser/session and stop services using approved procedures. | Manual acceptance notes tied to the exact allowed UI path. | Any model or write path blocks R5. |
| R6: Model/Ollama Authorization | Service start, stop, health, frontend, and browser boundaries are proven; separate model gate approved. | A future node may allow minimum model/Ollama commands and endpoint calls named by that node. | Model downloads, pulls, external providers, generation/export/write-back unless explicitly scoped. | Future model smoke report only if explicitly allowed. | Ollama/model path only as defined by the model gate. | Stop if missing local model requires download/pull, if external provider is needed, or if write path appears. | Stop model service if that was authorized; otherwise stop app services and report. | Model availability and no-write evidence. | Any model installation, pull, or write-back requirement blocks R6. |

Recommended next stage after 027A is `LOCAL-LAUNCHER-027B-INDEPENDENT-RUNTIME-COMMAND-WHITELIST-STOP-ROLLBACK-GATE`.

## 6. Initial Future Command Policy

| Command / Command Family | Current 027A Status | Future Possible Status | Earliest Stage | Preconditions | Reason |
| --- | --- | --- | --- | --- | --- |
| `scripts/run_web_ui.sh` | forbidden / not authorized | possibly restricted or replaced | R4 or later | R1 whitelist; backend stop verified; frontend scope explicit; no browser/open behavior. | Combines backend, frontend, port checks, PID/log writes, optional watchdog, and browser open. |
| `scripts/start_web_ui_background.sh` | forbidden / not authorized | late-stage only | R4 or later | Background behavior and stop/rollback proven. | Delegates to combined background start and writes control logs. |
| `scripts/web_ui_watchdog.sh` | forbidden / not authorized | late service-management only | after R5 | Stop/rollback and service lifecycle governance proven. | Auto-restart can defeat single-shot runtime control. |
| `scripts/stop_web_ui_background.sh` | forbidden / not authorized | whitelist candidate | R1 design, executable only before R2 start | Exact PID/log boundaries and allowed stop semantics documented. | Stop must be authorized before any start command. |
| `curl` | forbidden / not authorized | minimum health check only | R3 | Backend already started under R2 and endpoint is exact. | Endpoint access must be separate from start. |
| `lsof` | forbidden / not authorized | minimum port/process observation only | R1 design, executable only in a later runtime stage | Observation scope and no-kill policy explicit. | Port probing is runtime observation and can reveal or affect process handling. |
| `open` | forbidden / not authorized | browser acceptance only | R5 | Frontend start/stop proven and browser action independently approved. | Browser launch must not be bundled with service start. |
| `uvicorn` | forbidden / not authorized | single backend start candidate | R2 | R1 whitelist and stop/rollback accepted. | Most direct backend start path if selected by future gate. |
| `streamlit` | forbidden / not authorized | controlled frontend start candidate | R4 | Backend lifecycle proven and auto-open disabled. | Frontend must follow backend control. |
| `ollama` | forbidden / not authorized | model gate only | R6 | Local model, port, stop, no-download, and no-write controls defined. | Model runtime is high-risk and must be last. |
| `pytest` | forbidden / not authorized | possible non-runtime validation only if separately authorized | separate future node | Test target and no-runtime side-effect policy explicit. | Tests can create caches or touch runtime-like paths. |
| `npm test` | forbidden / not authorized | possible non-runtime validation only if separately authorized | separate future node | Package scope and no-build/no-watch policy explicit. | Frontend test tooling may install, build, or watch. |
| `.app` launcher | forbidden / not authorized | desktop launcher gate only | after command-line lifecycle proven | Exact launcher behavior, stop path, and no-bypass rules accepted. | `.app` hides command flow and can open Terminal, browser, logs, or services. |

## 7. Port and Endpoint Governance

| Port / Endpoint | Static Source | Runtime Meaning | Current Authorization | Future Authorization Stage | Required Control |
| --- | --- | --- | --- | --- | --- |
| `8010` | `scripts/run_web_ui.sh`; `.app` launcher health URL; `app.py` backend base URL. | Web UI backend port. | forbidden / not authorized | R2 for start, R3 for health. | Exact owner, command, stop path, and no-cross-system check. |
| `8501` | `scripts/run_web_ui.sh`; README Web UI; `.app` launcher. | Streamlit frontend port. | forbidden / not authorized | R4. | No auto-open, no watchdog, explicit stop path. |
| `8000` | README and RUNBOOK manual backend examples. | Older/manual backend endpoint examples. | forbidden / not authorized | Not in initial LOCAL-LAUNCHER runtime path unless a future gate selects it. | Must not be inferred from docs; requires explicit port selection. |
| `11434` | `app.py` Ollama preview defaults and model docs. | Local Ollama service port. | forbidden / not authorized | R6 only. | No access before model gate; no model pull/download. |
| `/health` | `backend/app/main.py`, README, RUNBOOK, `.app` launchers. | Backend service health endpoint. | forbidden / not authorized | R3. | Exact single endpoint, exact command, no broad smoke. |
| `/local-llm/preview-safe` | `local_llm_preview_safe_router` and safe endpoint source. | Isolated local LLM preview endpoint. | forbidden / not authorized | R6 or later model gate. | No-write, no-generation, no-export, no-model-install controls required. |
| `/actions/ollama/*` | `app.py` and `backend/app/routers/actions_bridge.py`. | Ollama preview/review/draft/smoke action family. | forbidden / not authorized | R6 only. | Separate model authorization, no write-back unless independently scoped. |
| localhost / `127.0.0.1` | Scripts, README/RUNBOOK, app code, `.app` launchers. | Local service access surface. | forbidden / not authorized | Stage-specific only. | Every host/port/action must be explicitly named by the future node. |

## 8. Stop / Rollback Governance

Runtime start must not be authorized before stop and rollback are designed because the repository contains background, watchdog, `.app`, PID, log, and browser-open paths. A start action without a bounded stop action can leave services running, can cause watchdog restart loops, or can make later evidence ambiguous.

PID, log, and runtime files may become future observation objects in a separately authorized runtime stage. This 027A node does not read `.runtime/`, PID, log, output, job, export, real project data, secrets, tokens, or credentials bodies.

The future stop command must be white-listed before any start command. If the selected stop path requires reading PID files or checking process ownership, the future node must define the exact read scope, command scope, and failure behavior.

Watchdog must remain disabled in the first runtime authorization. Any self-heal, launchd, auto-restart, or background-respawn path must be treated as a late service-management concern, not as part of initial readiness.

`.app` launchers must remain disabled in the first runtime authorization because they can wrap commands through Terminal/osascript, call background scripts, perform health checks, open logs, and open browser URLs.

If a future runtime attempt fails, the operator must stop, run only the pre-approved stop/rollback action, report the exact failure, and avoid broad fixes, dependency changes, script rewrites, or endpoint expansion.

## 9. Model / Ollama Governance

Ollama and model inference are not authorized in 027A.

`localhost:11434` must not be accessed in 027A.

`/actions/ollama/*` must not be called in 027A.

`/local-llm/preview-safe` must not be called in 027A.

Model authorization must come after service start, stop, health check, frontend start, and browser acceptance have each been governed by separate earlier stages.

Any model authorization must use a separate independent node that defines allowed command(s), allowed endpoint(s), model availability checks, no-download/no-pull rules, no-write rules, timeout limits, rollback rules, and blocking conditions.

## 10. 027B Entry Conditions

| Item | Recommendation |
| --- | --- |
| 027B Entry Status | allowed only if 027A is committed, tagged, pushed, and clean. |
| Required Preconditions | 027A document accepted; tag `v0.1.707-local-launcher-027a-runtime-authorization-governance-design` points to the 027A commit; worktree clean; no runtime action occurred in 027A. |
| Allowed Write Scope Recommendation | One new 027B governance document that defines future command whitelist, stop/rollback mechanism, first runtime smoke entry conditions, and acceptance gates. |
| Forbidden Scope Recommendation | No scripts, `.app`, README, RUNBOOK, local launcher static assets, historical docs, runtime code, `.runtime`, PID, log, output, job, export, secrets, tokens, credentials. |
| Acceptance Recommendation | `git diff --name-only` limited to the 027B document; `git diff --check` pass; no service start; no localhost; no curl/lsof/open; no `.app`; no tests/build/install. |
| Rollback Recommendation | If 027B over-scopes commands, revise or remove only the 027B document before commit. Do not perform runtime cleanup unless separately authorized. |
| Still Forbidden Actions | service start, endpoint access, localhost, curl, lsof, open, `.app`, startup scripts, watchdog, stop scripts, Streamlit, uvicorn, Ollama, model inference, tests, build, install. |

027B should be a writable governance-document node only. It must not start services, access localhost, execute curl/lsof/open, touch Ollama or model inference, or perform health checks. Its purpose is to produce a future executable command whitelist, stop/rollback mechanism, and first runtime smoke-test admission criteria.

Recommended next node: `LOCAL-LAUNCHER-027B-INDEPENDENT-RUNTIME-COMMAND-WHITELIST-STOP-ROLLBACK-GATE`.

## 11. Risk Register

| Risk ID | Risk Description | Level | Evidence | Control Rule | Blocking Status |
| --- | --- | --- | --- | --- | --- |
| R-001 | 多启动入口导致越权启动。 | B1 | `run_web_ui.sh`, background script, launchd scripts, README/RUNBOOK, and `.app` launchers all describe start paths. | Future nodes must authorize exactly one command at a time. | Not blocking 027A; blocks runtime execution until R1/R2. |
| R-002 | `.app` 绕过命令行触发运行态。 | B1 | `.app` launchers delegate to background scripts, health checks, Terminal/osascript, and browser/log open paths. | `.app` remains forbidden until a dedicated desktop-launcher gate. | Not blocking 027A; blocks `.app` use. |
| R-003 | watchdog 自动重启导致停止不可控。 | B1 | `web_ui_watchdog.sh` restarts Web UI when listeners are missing. | No-watchdog-first rule; disable until lifecycle management gate. | Not blocking 027A; blocks watchdog. |
| R-004 | PID/log/runtime 写入链未经当前授权。 | B1 | `run_web_ui.sh` and stop script reference `.runtime/docgen`, PID files, and `logs/`. | Do not read/write bodies in governance nodes; define future observation scope. | Not blocking 027A; blocks runtime file touch. |
| R-005 | 旧 README/RUNBOOK 启动说明被误读为当前授权。 | B2 | README/RUNBOOK contain uvicorn, curl, lsof, Web UI, and launchd examples. | Documentation examples are non-authorization until a node grants them. | Not blocking 027A. |
| R-006 | endpoint/localhost 说明被误读为当前授权。 | B2 | Static references include `127.0.0.1:8000`, `8010`, `8501`, `/health`, and Web UI URLs. | Future endpoint access requires a separate endpoint stage. | Not blocking 027A. |
| R-007 | Ollama / model inference 入口被误触发。 | B1 | `app.py`, actions bridge, and local LLM router reference Ollama/model endpoints and `localhost:11434`. | No-model-first; model authorization only in R6 or later. | Not blocking 027A; blocks model actions. |
| R-008 | stop/rollback 未固化前直接启动服务。 | B1 | Stop script exists but its PID/log/process behavior has not been authorized for current runtime use. | Stop-before-start: R1 must define stop/rollback first. | Not blocking 027A; blocks R2 until R1. |
| R-009 | 浏览器自动打开导致越过端口授权。 | B1 | `run_web_ui.sh` and `.app` launcher can call `open` and open Web UI URLs. | No-browser-first; browser only in R5. | Not blocking 027A; blocks auto-open. |
| R-010 | 027B 被误解为可运行节点。 | B2 | 027B is proposed after a runtime-readiness governance path. | 027B must be explicitly docs/governance only. | Not blocking 027A; must be stated in handoff. |

## 12. Acceptance Criteria

This node is accepted only if all of the following are true:

- Only the target document is added or updated.
- `git diff --name-only` shows only `docs/zdoc-local-launcher-027a-independent-runtime-authorization-governance-design.md`.
- `git diff --check` passes.
- No service is started.
- No localhost or `127.0.0.1` is accessed.
- No `curl`, `lsof`, or `open` command is executed.
- No `.app` launcher is run.
- No startup script is run.
- No `.runtime`, PID, or log body is touched.
- No endpoint, Ollama, or model inference action is performed.
- No test, build, install, dependency update, migration, formatter, or generated-output command is run.
- No scripts, `.app`, README, RUNBOOK, local launcher static assets, historical governance documents, runtime code, backend code, frontend code, or configuration files are modified.
- After commit and tag, the worktree is clean.
- Tag `v0.1.707-local-launcher-027a-runtime-authorization-governance-design` points to the new commit.

## 13. Final Conclusion

027A is complete when this governance design document is the only diff, passes diff validation, is committed with the required commit message, is tagged with `v0.1.707-local-launcher-027a-runtime-authorization-governance-design`, is pushed with `main` and the tag, and the worktree is clean.

027A allows entry into 027B only as a governance-document node.

027B must remain non-runtime. It must not start services, access localhost, run curl/lsof/open, run `.app`, run startup scripts, touch `.runtime`/PID/log bodies, call endpoints, touch Ollama/model inference, run browser acceptance, take screenshots, or run tests/build/install.

The next recommended node is `LOCAL-LAUNCHER-027B-INDEPENDENT-RUNTIME-COMMAND-WHITELIST-STOP-ROLLBACK-GATE`.

This node does not authorize any runtime, endpoint, localhost, Ollama, model inference, browser, screenshot, service start, service stop, watchdog, background process, port probe, health check, test, build, install, or live acceptance capability.
