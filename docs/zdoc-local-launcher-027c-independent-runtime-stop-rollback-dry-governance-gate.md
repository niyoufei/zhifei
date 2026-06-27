# LOCAL-LAUNCHER-027C Independent Runtime Stop Rollback Dry Governance Gate

## 1. Node Metadata

| Field | Value |
| --- | --- |
| Node | `LOCAL-LAUNCHER-027C-INDEPENDENT-RUNTIME-STOP-ROLLBACK-DRY-GOVERNANCE-GATE` |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `local-launcher-027c-runtime-stop-rollback-dry-governance-gate` |
| Baseline HEAD | `864070ded8df41e60bfd7e43b29d192c392ad7fb` |
| Baseline Tag | `v0.1.709-local-launcher-027b-post-merge-main-baseline` |
| Previous Gates | `LOCAL-LAUNCHER-026G-INDEPENDENT-LINE-STATIC-GOVERNANCE-CLOSURE-ARCHIVE-GATE`; `LOCAL-LAUNCHER-027-INDEPENDENT-RUNTIME-READINESS-PREFLIGHT-AUDIT`; `LOCAL-LAUNCHER-027A-INDEPENDENT-RUNTIME-AUTHORIZATION-GOVERNANCE-DESIGN`; `LOCAL-LAUNCHER-027B-INDEPENDENT-RUNTIME-COMMAND-WHITELIST-STOP-ROLLBACK-GATE`; `LOCAL-LAUNCHER-027B-LOCAL-MAIN-ALIGNMENT-GATE` |
| Execution Type | runtime stop / rollback dry governance only |
| Write Scope | only this document: `docs/zdoc-local-launcher-027c-independent-runtime-stop-rollback-dry-governance-gate.md` |
| Runtime Policy | forbidden in 027C |
| Service Start Policy | no service start command is authorized |
| Service Stop Policy | no service stop command is executed or authorized for execution |
| Localhost Policy | no localhost or `127.0.0.1` access |
| Endpoint Policy | no endpoint call, no health check, no smoke test |
| Runtime/PID/Log Policy | no `.runtime`, PID, or log body read or write |
| Ollama / Model Policy | no Ollama, model endpoint, or model inference action |
| Browser Policy | no browser open or browser acceptance |
| Screenshot Policy | no screenshot |
| Branch / PR Policy | publish through the 027C branch and PR only; do not push `main`; do not merge this PR in 027C |

## 2. Purpose

027C is not a runtime node.

027C is not a service start node.

027C is not a service stop execution node.

027C is not a localhost access node.

027C is not an endpoint verification node.

027C is not a `.runtime`, PID, or log reading node.

027C is not an Ollama or model inference node.

027C only freezes future stop / rollback dry governance that must exist before any later runtime action is considered.

027C is published through a branch and PR path because `main` is locked/protected. It must not directly push `main`.

## 3. Stop / Rollback Dry Governance Principles

1. Dry Governance Only Principle: 027C only designs stop and rollback governance; it does not execute runtime commands.
2. Stop Before Start Principle: future service start authorization must be preceded by explicit stop and rollback rules.
3. No Stop Execution Yet Principle: 027C does not execute `scripts/stop_web_ui_background.sh` or any other stop command.
4. No Runtime Touch Yet Principle: 027C does not read or write `.runtime`, PID files, or log files.
5. No Port Probe Yet Principle: 027C does not run `lsof`, `curl`, browser probes, health checks, or any localhost observation command.
6. No Watchdog First Principle: watchdog remains disabled and unauthorised until a separate late-stage watchdog gate exists.
7. No App Bypass Principle: `.app` launchers must not be used as stop or start entries because they hide command flow.
8. Single Failure Path Principle: each future failure type must map to one pre-approved handling path.
9. Stop Failure B0 Principle: if a future authorized stop command fails, the node must enter B0 blocking status.
10. No Expansion on Failure Principle: a failure must not broaden command scope, read scope, endpoint scope, or write scope.

## 4. Future Stop Command Classification

| Command / Object | Current 027C Status | Future Earliest Stage | Allowed Preconditions | Forbidden Conditions | Evidence Source | Control Rule |
| --- | --- | --- | --- | --- | --- | --- |
| `scripts/stop_web_ui_background.sh` | forbidden / not authorized | Dedicated stop verification gate after 027C is merged | A future node names exact PID/log read scope, process ownership checks, fallback behavior, and B0 handling | Any execution in 027C; broad PID/log reads; broad port probing; kill actions outside verified project ownership | `scripts/stop_web_ui_background.sh` reads `.runtime/docgen` PID files, old log PID files, process command/cwd, and fallback ports | Stop script must be whitelisted before start, and stop failure is B0 |
| `scripts/run_web_ui.sh` | read-only-reference / not authorized | Backend/frontend lifecycle stages after stop rule acceptance | A future node decomposes backend, frontend, browser, PID/log, and watchdog behaviors into separate actions | Any combined start, background start, health check, browser open, curl/lsof/open, or watchdog in one stage | `scripts/run_web_ui.sh` starts uvicorn and Streamlit, writes PID/log files, uses `curl`, `lsof`, and `open` | Combined launcher must not be first runtime command |
| `scripts/start_web_ui_background.sh` | read-only-reference / not authorized | Background-specific stage after foreground lifecycle is proven | Foreground start/stop accepted; background logs and watchdog policy defined | Any background start before foreground stop/rollback proof | Script delegates to `run_web_ui.sh --background` and writes `logs/webui_control.log` | Background start remains later-stage only |
| `scripts/web_ui_watchdog.sh` | read-only-reference / not authorized | Late watchdog-management gate | Stop/rollback, service ownership, and anti-restart controls accepted | Any auto-restart, self-heal, long-running loop, or watchdog before browser/runtime lifecycle proof | Script loops on backend/frontend listener checks and restarts Web UI | Watchdog is forbidden until explicitly authorized |
| PID files | forbidden / not authorized | Stop verification gate | Exact file names, read method, redaction, and ownership use are named | PID body read in 027C; manual PID writes; unscoped PID cleanup | `webui_backend.pid`, `streamlit.pid`, and `webui_watchdog.pid` are referenced by scripts | PID files are future evidence objects only |
| `.runtime/docgen` | forbidden / not authorized | Stop/readiness observation gate after explicit read authorization | Exact directory and files are listed; no write except authorized runtime side effects | Any read/write in 027C; broad directory scan; cleanup action | Runtime directory is configured by `ZF_RUNTIME_DIR` defaults in scripts | Runtime directory remains untouched |
| logs | forbidden / not authorized | Log observation gate after redaction rules | Exact paths, max read length, and secret redaction are defined | Any log body read in 027C; log cleanup; broad search in log directories | Scripts write `logs/webui_backend.*`, `logs/streamlit.*`, `logs/webui_watchdog.*`, and `logs/webui_control.log` | Logs require separate read approval |
| backend process | forbidden / not authorized | Backend single-shot start and stop stages | Exact backend command and stop command are approved | Starting, stopping, probing, or health-checking backend in 027C | `backend/app/main.py` defines FastAPI app and `/health`; scripts use uvicorn | Backend lifecycle must be isolated |
| frontend process | forbidden / not authorized | Frontend single-shot start after backend lifecycle proof | Exact Streamlit command, no-browser behavior, and frontend stop rule are approved | Starting Streamlit, opening browser, or probing frontend in 027C | `app.py` is Streamlit frontend; scripts use port `8501` | Frontend follows backend, never precedes it |
| watchdog process | forbidden / not authorized | Watchdog-management gate after service lifecycle proof | Auto-restart policy, stop behavior, and failure handling are explicitly approved | Any watchdog start, restart, listener loop, or self-heal in 027C | `scripts/web_ui_watchdog.sh` and `ZF_ENABLE_SELF_HEAL` show restart behavior | Watchdog remains disabled |
| `.app` launcher | forbidden / not authorized | Dedicated desktop launcher gate | Command-line lifecycle and stop/rollback are proven first | Any `.app` execution or hidden Terminal/osascript path in 027C | 027A/027B classify `.app` as a bypass surface; static V1 state is no-runtime | `.app` cannot bypass CLI gates |
| `curl` / `lsof` / `open` | forbidden / not authorized | Exact endpoint, port, or browser gates only | A future node names one command, one target, and one evidence purpose | General probing, health checks, browser open, port ownership checks in 027C | Scripts and docs reference these commands | Each command requires independent authorization |
| localhost / `127.0.0.1` | forbidden / not authorized | Stage-specific runtime gate | Exact host, port, endpoint, and command are approved | Any access, smoke, health, browser, curl, or port check in 027C | Scripts, README, RUNBOOK, `app.py`, and backend references include local URLs | No broad localhost authority exists |

## 5. Dry Stop / Rollback Scenario Matrix

| Scenario | Future Trigger | Future Allowed Observation | Future Stop Action | Future Rollback Action | Current 027C Authorization | Blocking Rule |
| --- | --- | --- | --- | --- | --- | --- |
| Backend startup fails | Future backend start command exits non-zero or readiness times out | Only the exact exit code and output authorized by that future node | Run the pre-approved backend stop command if it was authorized | Report failure and restore only allowed runtime artifacts if a future node permits it | Not authorized | Missing or failed stop path is B0 |
| Frontend startup fails | Future Streamlit command fails or does not become ready | Exact frontend command result named by the future node | Run approved frontend stop, then backend stop if chained and authorized | Do not open browser or inspect logs unless separately authorized | Not authorized | Frontend failure blocks browser stage |
| Backend started but health check fails | Future `/health` check returns failure or timeout | Only the exact health result from an authorized endpoint gate | Run pre-approved backend stop | Do not broaden endpoint testing | Not authorized | Health failure blocks frontend start |
| Frontend started but browser acceptance is not authorized | Future frontend stage completes before browser gate | No browser observation; only command/process evidence approved by that stage | Stop frontend with approved stop rule | Keep browser unopened and report pending gate | Not authorized | Browser remains blocked until explicit gate |
| PID file exists but process status is unknown | Future stop gate sees PID evidence | Exact PID file read if authorized | Stop only if process identity matches approved rules | Report unknown ownership without killing unrelated processes | Not authorized | Unknown ownership is B0 or B1 per future gate |
| Log exists but read is not authorized | Future failure mentions a log path | File path may be recorded only if future node allows it | No stop based on log contents | Do not read log body; request log-read authorization | Not authorized | Log body read without authorization blocks node |
| Port is suspected occupied | Future command reports port conflict | Exact command output from authorized command only | Run approved stop only for verified project process | Do not run broad `lsof` or kill commands unless named | Not authorized | Port uncertainty blocks runtime continuation |
| Watchdog unexpectedly exists | Future observation detects watchdog PID or loop | Only exact authorized process evidence | Stop watchdog only if a future watchdog stop command is approved | Disable further runtime stage and report B0/B1 | Not authorized | Watchdog presence blocks single-shot runtime |
| `.app` is accidentally triggered | User or system opens app outside node scope | Record that boundary was breached; do not inspect app runtime | Use only pre-approved stop path if services were started and stop is authorized | Stop current node and require incident audit | Not authorized | App bypass is B0 unless proven no runtime effect |
| Ollama / model endpoint is triggered | Future UI/backend path touches model or `localhost:11434` | Only future model gate evidence if authorized | Stop app services if approved; no model command expansion | No model pull/download; no external provider fallback | Not authorized | Model trigger blocks non-model runtime gates |
| Stop script execution fails | Future authorized stop command exits non-zero | Exact exit code and allowed output | No additional stop command unless pre-approved | Enter B0 and request human-controlled remediation | Not authorized | Stop failure is B0 |
| Git state is not clean | Future node sees uncommitted changes | `git status --short --branch` only if allowed | No runtime action | Restore by Git workflow only if separately authorized | Not authorized | Dirty worktree blocks runtime authorization |

## 6. Future Runtime Object Access Rules

| Runtime Object | Current 027C Access | Future Earliest Stage | Read Preconditions | Write Preconditions | Forbidden Until | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `.runtime/docgen` | forbidden | Runtime observation or stop verification gate | Exact file list, read-only method, and reason are authorized | Only an authorized runtime command may create/update it | A future node names it | Runtime state can affect or reveal live process state |
| `webui_backend.pid` | forbidden | Backend stop verification gate | Exact backend PID read is needed for approved stop | No manual write; only authorized backend command side effect | Backend stop gate | PID values can point outside the project |
| `streamlit.pid` | forbidden | Frontend stop verification gate | Exact frontend PID read is needed for approved stop | No manual write; only authorized frontend command side effect | Frontend stop gate | PID values require ownership validation |
| `webui_watchdog.pid` | forbidden | Watchdog stop/management gate | Exact watchdog PID read is needed and watchdog scope is approved | No manual write; only authorized watchdog command side effect | Watchdog gate | Watchdog can restart services unexpectedly |
| backend log | forbidden | Backend failure observation gate | Exact backend log path, line/window limit, and secret redaction are approved | Only authorized backend command side effect | Log-read gate | Logs can contain runtime or sensitive data |
| frontend log | forbidden | Frontend failure observation gate | Exact frontend log path, line/window limit, and secret redaction are approved | Only authorized frontend command side effect | Log-read gate | Frontend logs can expose endpoint/model behavior |
| watchdog log | forbidden | Watchdog management gate | Exact watchdog log path and read limit are approved | Only authorized watchdog command side effect | Watchdog gate | Watchdog logs imply lifecycle activity |
| `logs/` | forbidden | Scoped log observation gate | Exact files and max read scope are named | No manual writes or cleanup unless separately authorized | Log governance gate | Broad log access can leak secrets or stale runtime evidence |
| output / job / export | forbidden | Not part of 027C runtime governance | No read unless a separate artifact gate authorizes it | No write | Separate product artifact gate | These are generation/export domains, not launcher lifecycle evidence |
| secrets / tokens / credentials | forbidden | Never in launcher dry governance | No read | No write | Dedicated secret-handling gate only | Secret exposure is outside this workflow |

## 7. Stop / Rollback Acceptance Design

Future stop / rollback acceptance must satisfy all of the following before any runtime start stage can be accepted:

- Stop command must be explicitly whitelisted by exact command text.
- Stop execution must confirm a prior runtime start node was authorized.
- Stop execution may read only the status objects named by the same future node.
- Stop failure must enter B0 and must not trigger ad hoc repair commands.
- No unauthorized command may be used to compensate for a stop failure.
- Watchdog must not be automatically enabled as a recovery mechanism.
- Browser must not be automatically opened for stop or rollback acceptance.
- Model or Ollama commands must not be called during stop / rollback acceptance.
- Business code must not be modified as runtime recovery.
- `.app` bundles and scripts must not be modified as runtime recovery.
- Acceptance must record command, scope, exit code, allowed observations, and forbidden observations.
- Acceptance must prove that the future node preserved its write scope and did not broaden runtime access.

## 8. 027D Entry Conditions

Recommended next node: `LOCAL-LAUNCHER-027D-INDEPENDENT-RUNTIME-BACKEND-SINGLE-SHOT-START-GOVERNANCE-GATE`.

| Item | Recommendation |
| --- | --- |
| 027D Entry Status | Not allowed until the 027C PR is merged and the post-merge baseline is accepted. |
| Required Preconditions | 027C document merged to `main`; post-merge main baseline and local alignment complete; stop / rollback dry rules accepted; worktree clean; `main` remains protected. |
| Allowed Write Scope Recommendation | One future 027D governance or minimal runtime report document, as separately authorized by the total-control node. |
| Forbidden Scope Recommendation | No frontend, browser, watchdog, `.app`, Ollama, model inference, output/job/export, secrets, scripts edits, README edits, RUNBOOK edits, or broad runtime object access. |
| Acceptance Recommendation | If 027D remains governance-only, diff scope and boundary acceptance are enough. If backend single-shot start is explicitly authorized, acceptance must include one exact backend command, exact stop rule, exit code, bounded observation, and no expansion. |
| Rollback Recommendation | Inherit 027C stop / rollback rules. If backend start fails or stop fails, enter B0 according to the future node. |
| Still Forbidden Actions | Frontend start, browser open, watchdog, `.app`, Ollama, model inference, model endpoint, broad endpoint smoke, tests, builds, installs, dependency updates, script rewrites. |

027D is still a governance node or a minimum runtime-authorization precondition node, depending on a future total-control decision.

027D must not default to starting services.

If a future node authorizes backend single-shot start, it must authorize only one minimum backend start action.

027D must still forbid frontend, browser, watchdog, `.app`, Ollama, and model inference unless a later independent gate says otherwise.

027D must inherit the 027C stop / rollback rules before any runtime command is considered.

## 9. Risk Register

| Risk ID | Risk Description | Level | Evidence | Control Rule | Blocking Status |
| --- | --- | --- | --- | --- | --- |
| R-027C-001 | 027C is misread as stop execution authorization. | B1 | 027C follows the 027B stop/rollback whitelist gate. | State dry governance only in metadata, purpose, principles, acceptance, and conclusion. | Blocks stop execution in 027C. |
| R-027C-002 | Stop script is executed prematurely. | B0 | `scripts/stop_web_ui_background.sh` can read PID files and kill verified processes. | Stop script remains forbidden until a future stop execution gate. | Blocks runtime continuation if breached. |
| R-027C-003 | Runtime, PID, or log files are read prematurely. | B1 | Scripts reference `.runtime/docgen`, PID files, and `logs/`. | Runtime objects require exact future read scope. | Blocks observation beyond static evidence. |
| R-027C-004 | Watchdog is enabled before lifecycle control. | B1 | `web_ui_watchdog.sh` auto-restarts missing listeners. | No-watchdog-first rule. | Blocks watchdog use. |
| R-027C-005 | `.app` is used as start or stop entry. | B1 | Prior gates classify `.app` as a bypass; static state says service start/stop are false. | `.app` remains forbidden until desktop launcher gate. | Blocks `.app` use. |
| R-027C-006 | Stop failure causes unauthorized repair expansion. | B0 | Stop script has PID and port fallback logic that can invite broader troubleshooting. | Stop failure is B0; no new commands after failure. | Blocks continuation after failed stop. |
| R-027C-007 | Port conflict is probed with `curl` or `lsof` in this node. | B1 | Scripts and README/RUNBOOK reference local ports and probing commands. | Port probes require a future exact command gate. | Blocks runtime observation in 027C. |
| R-027C-008 | Backend and frontend stop boundaries are confused. | B1 | `run_web_ui.sh` and stop script manage both backend and frontend paths. | Backend and frontend lifecycle gates remain separate. | Blocks combined lifecycle actions. |
| R-027C-009 | Ollama or model endpoint is triggered accidentally. | B0 | `app.py` and backend routers include model/provider and local LLM surfaces. | Model actions require a separate late-stage model gate. | Blocks non-model runtime gates. |
| R-027C-010 | 027D is misread as automatic runtime start. | B1 | 027D is proposed after stop/rollback governance. | 027D must be separately authorized and may remain governance-only. | Blocks automatic 027D runtime. |
| R-027C-011 | Main lock causes accidental direct main push attempt. | B2 | `main` is locked/protected and 027C must use branch/PR. | Publish only release branch and PR; no `main` push. | Not blocking branch PR path. |

## 10. Acceptance Criteria

- Only the target document is added or updated.
- `git diff --name-only` shows only `docs/zdoc-local-launcher-027c-independent-runtime-stop-rollback-dry-governance-gate.md`.
- `git diff --check` passes.
- No service is started.
- No service is stopped.
- No localhost or `127.0.0.1` is accessed.
- No `curl`, `lsof`, or `open` command is executed.
- No `.app` launcher is run.
- No startup script is run.
- No stop script is run.
- No `.runtime`, PID, or log body is touched.
- No endpoint, Ollama, or model inference action is performed.
- No tests, builds, installs, dependency updates, migrations, formatters, or generated-output commands are run.
- No scripts, `.app`, README, RUNBOOK, local launcher static assets, historical governance documents, runtime code, backend code, frontend code, or configuration files are modified.
- Only the 027C publishing branch may be pushed.
- `main` is not pushed.
- No final mainline tag is created in 027C.
- A PR is created successfully, or manual PR information is output.

## 11. Final Conclusion

027C is complete when this document is the only file change, it passes diff validation, it is committed on `local-launcher-027c-runtime-stop-rollback-dry-governance-gate`, the branch is pushed, and a PR is created or manual PR information is provided.

027C allows entry into 027C PR merge readiness audit only after the branch/PR publication is complete.

027D is a future governance node or minimum backend single-shot start precondition node. Its exact nature must be decided by a separate total-control objective.

027D must continue to forbid frontend, browser, watchdog, `.app`, Ollama, model inference, broad endpoint smoke, tests, builds, installs, dependency updates, and script rewrites unless a later independent node explicitly authorizes them.

This node does not authorize any runtime, service start, service stop execution, endpoint, localhost, Ollama, model inference, browser, screenshot, script execution, `.app`, watchdog, background process, port probe, health check, test, build, install, or live acceptance capability.

027C must not be considered complete on the mainline until its PR is merged to `main` and a later post-merge baseline gate accepts that state.

PR merge is not authorized in 027C. PR merge readiness audit may be entered after this PR is published. 027D must not be entered before the 027C PR is merged.
