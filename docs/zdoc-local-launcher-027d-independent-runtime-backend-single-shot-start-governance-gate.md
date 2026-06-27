# LOCAL-LAUNCHER-027D Independent Runtime Backend Single-Shot Start Governance Gate

## 1. Node Metadata

| Field | Value |
| --- | --- |
| Node | `LOCAL-LAUNCHER-027D-INDEPENDENT-RUNTIME-BACKEND-SINGLE-SHOT-START-GOVERNANCE-GATE` |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `local-launcher-027d-backend-single-shot-start-governance-gate` |
| Baseline HEAD | `f38a7a1c6a689751dd0faaf7ca14e757893a08f6` |
| Baseline Tag | `v0.1.710-local-launcher-027c-post-merge-main-baseline` |
| Previous Gates | `LOCAL-LAUNCHER-026G-INDEPENDENT-LINE-STATIC-GOVERNANCE-CLOSURE-ARCHIVE-GATE`; `LOCAL-LAUNCHER-027-INDEPENDENT-RUNTIME-READINESS-PREFLIGHT-AUDIT`; `LOCAL-LAUNCHER-027A-INDEPENDENT-RUNTIME-AUTHORIZATION-GOVERNANCE-DESIGN`; `LOCAL-LAUNCHER-027B-INDEPENDENT-RUNTIME-COMMAND-WHITELIST-STOP-ROLLBACK-GATE`; `LOCAL-LAUNCHER-027C-INDEPENDENT-RUNTIME-STOP-ROLLBACK-DRY-GOVERNANCE-GATE`; `LOCAL-LAUNCHER-027C-LOCAL-MAIN-ALIGNMENT-GATE` |
| Execution Type | backend single-shot start governance only |
| Write Scope | only this document: `docs/zdoc-local-launcher-027d-independent-runtime-backend-single-shot-start-governance-gate.md` |
| Runtime Policy | forbidden in 027D |
| Backend Start Policy | no backend start execution in 027D |
| Frontend Policy | frontend start remains forbidden |
| Service Stop Policy | no service stop execution in 027D |
| Localhost Policy | no localhost or `127.0.0.1` access |
| Endpoint Policy | no endpoint call, no health check, no smoke test |
| Runtime/PID/Log Policy | no `.runtime`, PID, or log body read or write |
| Ollama / Model Policy | no Ollama, model endpoint, or model inference action |
| Browser Policy | no browser open or browser acceptance |
| Screenshot Policy | no screenshot |
| Branch / PR Policy | publish through the 027D branch and PR only; do not push `main`; do not merge this PR in 027D |

## 2. Purpose

027D is not an actual runtime node.

027D is not a service start execution node.

027D is not a localhost access node.

027D is not an endpoint verification node.

027D is not a `.runtime`, PID, or log reading node.

027D is not a frontend start node.

027D is not a browser acceptance node.

027D is not a watchdog node.

027D is not a `.app` start node.

027D is not an Ollama or model inference node.

027D only freezes the governance boundary for a future backend single-shot start stage.

027D is published through a branch and PR path because `main` is locked/protected. It must not directly push `main`.

## 3. Backend Single-Shot Start Governance Principles

1. Governance Only Principle: 027D designs backend start governance; it does not execute any runtime command.
2. Backend Only Principle: the earliest future runtime authorization may consider backend only and must not include frontend.
3. Single-Shot Principle: the future start candidate must be one foreground, one-time command; background, watchdog, daemon, self-heal, and launchd behavior remain forbidden.
4. No Localhost Yet Principle: 027D does not access local ports or local URLs.
5. No Health Check Yet Principle: 027D does not execute `/health` or any endpoint check.
6. Stop Dependency Principle: any future backend start must inherit the 027C stop / rollback rules before execution.
7. No Frontend First Principle: frontend may only follow controlled backend start and stop proof.
8. No Browser First Principle: browser acceptance may only follow controlled frontend start and stop proof.
9. No Model First Principle: Ollama and model inference must remain in a later independent model gate.
10. Stop-on-Breach Principle: any sign of unauthorized start, port access, endpoint call, browser open, frontend launch, watchdog, `.app`, or model activity blocks the future node.

## 4. Backend Start Candidate Classification

| Candidate | Current 027D Status | Future Earliest Stage | Required Preconditions | Forbidden Conditions | Evidence Source | Control Rule |
| --- | --- | --- | --- | --- | --- | --- |
| `uvicorn backend.app.main:app` | forbidden / not authorized | 027E authorization gate if separately approved | Exact command, cwd, env whitelist, port, timeout, stop rule, and rollback rule are defined | Any execution in 027D; frontend/browser/watchdog/model bundled with it | README/RUNBOOK show manual uvicorn examples; `backend/app/main.py` defines FastAPI app | Candidate only; executable only in a future explicit backend gate |
| `scripts/run_web_ui.sh` | read-only-reference / not authorized | Not earlier than backend/frontend decomposed lifecycle stages | Backend, frontend, PID/log, port, health, browser, and watchdog behaviors are separately governed | Any first backend runtime command using this combined launcher | Script starts backend and frontend, writes PID/log files, uses `curl`, `lsof`, `open`, and can start watchdog | Combined launcher cannot be 027E single-shot backend command |
| `scripts/start_web_ui_background.sh` | read-only-reference / not authorized | Background-specific gate after foreground lifecycle proof | Foreground backend/frontend lifecycle and stop rules are accepted | Any background start, log write, watchdog, or long-running behavior in early stages | Script delegates to `run_web_ui.sh --background` and writes `logs/webui_control.log` | Background entry remains forbidden |
| `scripts/web_ui_watchdog.sh` | read-only-reference / not authorized | Late watchdog-management gate | Service lifecycle, stop behavior, and anti-restart controls are accepted | Any watchdog loop, listener probe, restart, or self-heal in 027D/027E | Script checks ports and restarts Web UI when listeners are missing | Watchdog is forbidden until a dedicated gate |
| `scripts/stop_web_ui_background.sh` | read-only-reference / not authorized | Stop verification gate before or with future runtime gate | Exact PID/log/process ownership read scope and B0 failure rule are authorized | Stop execution in 027D; broad PID/log/port probing | Script reads PID files and verifies backend/frontend processes before kill | Stop dependency must be defined before start |
| `app.py` | read-only-reference / not authorized | Frontend stage after backend lifecycle proof | Backend lifecycle accepted; frontend command exact; browser/model boundaries set | Starting Streamlit or triggering frontend calls in 027D/027E | Streamlit app references backend provider/config/model surfaces | Frontend remains later-stage only |
| `backend/app/main.py` | read-only-reference / not authorized | Backend single-shot start candidate source for 027E | Future node names exact backend entry, port, cwd, and env | Endpoint, health, model, config mutation, or runtime execution in 027D | Defines `app = FastAPI()` and `/health`; includes model-adjacent routers | Static source only in 027D |
| FastAPI app | read-only-reference / not authorized | 027E if explicitly authorized | `backend.app.main:app` target is selected and bounded | Any live ASGI process in 027D | `backend/app/main.py` creates `app = FastAPI()` | App object is a future runtime target, not current authorization |
| port `8010` | forbidden / not authorized | Future backend start or health gate | Exact port selection and no-cross-system rule are defined | Port probe, health check, browser, curl, lsof, or listener check in 027D | `scripts/run_web_ui.sh` defaults `BACKEND_PORT=8010`; `app.py` defaults backend URL to `127.0.0.1:8010` | Port remains a future parameter only |
| old port `8000` | forbidden / not authorized | Separate legacy/manual backend gate if chosen | Future node explicitly selects legacy README/RUNBOOK path | Inferring authorization from docs | README/RUNBOOK show `uvicorn ... --port 8000` and curl examples | Documentation examples do not authorize runtime |
| `/health` | forbidden / not authorized | Separate health-check gate after backend start proof | Backend start and stop are controlled first | Any endpoint call or localhost access in 027D/027E unless explicitly scoped | `backend/app/main.py`, README, and RUNBOOK reference `/health` | Health check must not be bundled with start by default |
| `.runtime/docgen` | forbidden / not authorized | Runtime observation or stop verification gate | Exact file list, read-only method, and reason are authorized | Read/write in 027D; broad directory scan; cleanup | Scripts default runtime dir to `.runtime/docgen` | Runtime state remains untouched |
| PID files | forbidden / not authorized | Stop verification gate | Exact PID names and process ownership rules are authorized | PID body read, manual write, broad cleanup | Scripts reference `webui_backend.pid`, `streamlit.pid`, and `webui_watchdog.pid` | PID access follows stop governance |
| logs | forbidden / not authorized | Log-read gate after redaction rules | Exact log paths, line/window limit, and secret redaction are defined | Log body read or cleanup in 027D | Scripts write backend, Streamlit, watchdog, and control logs | Logs are future evidence only |

## 5. Future Backend Single-Shot Start Boundary

Recommended next node: `LOCAL-LAUNCHER-027E-INDEPENDENT-RUNTIME-BACKEND-SINGLE-SHOT-START-AUTHORIZATION-GATE`.

027D does not execute this future stage. If 027E is authorized by a later objective, it may authorize at most:

- one backend single-shot start command;
- no frontend;
- no browser;
- no watchdog;
- no `.app`;
- no Ollama;
- no model inference;
- no automatic `open`;
- no background daemon or long-running supervisor beyond the single backend process;
- no expansion to health check unless 027E explicitly includes a separately bounded health observation.

Future 027E must define:

| Required Design Item | Required Content |
| --- | --- |
| Entry Conditions | Accepted 027D PR, clean worktree, correct main baseline, stop / rollback rule inherited from 027C |
| Exact Allowed Command | One exact backend command, including executable, module, host, port, cwd, and env whitelist |
| Exact Forbidden Commands | frontend, browser, watchdog, `.app`, `run_web_ui.sh`, background start, Ollama/model, broad endpoint, tests/build/install |
| Runtime Scope | Backend process only, with one named port and no frontend |
| Writable Scope | Only the future runtime report or exact runtime artifacts if explicitly allowed by 027E |
| PID / Log Policy | Explicitly say whether PID/log reads are allowed; if allowed, list exact files and limits |
| Stop Condition | Any unexpected process, port, frontend, browser, endpoint, model, dirty git state, timeout, or missing stop path |
| Rollback Rule | Run only the pre-approved stop command; if stop fails, B0 |
| Timeout Rule | Bounded wait duration; no indefinite background process or watchdog loop |
| Acceptance Method | Command transcript, exit code, bounded observation, no health check unless separately authorized |
| Blocking Rule | Missing precondition or boundary breach blocks runtime and prevents 027E completion |

## 6. Backend Start Failure Matrix

| Failure Scenario | Future Detection Scope | Future Allowed Response | Future Forbidden Response | Current 027D Authorization | Blocking Rule |
| --- | --- | --- | --- | --- | --- |
| import error | Only future command stderr/stdout if 027E allows it | Stop backend if started; report exact import failure | Edit code, install packages, run tests, broaden command | Not authorized | Blocks 027E until separate fix gate |
| missing dependency | Future command output only | Report dependency gap; stop if process exists | `pip install`, dependency update, build/install commands | Not authorized | Blocks runtime; requires separate dependency gate |
| port already in use | Only output from the exact authorized backend command unless a port probe is separately allowed | Stop only verified project process if future stop rule allows it | `lsof`, kill, curl, broad port exploration without authorization | Not authorized | Blocks runtime if ownership cannot be proven |
| backend exits immediately | Exit code and allowed output from 027E | Report failure and run approved stop/cleanup if applicable | Restart loop, watchdog, background retry, code changes | Not authorized | Blocks frontend/health stages |
| backend hangs | Future timeout rule only | Stop using pre-approved command and report timeout | Increase scope, run browser, run health checks, inspect logs without approval | Not authorized | Timeout is blocking |
| PID unknown | Exact PID policy from future node | Proceed only if PID observation is not required, or report missing PID | Read runtime directory broadly or create PID manually | Not authorized | Blocks stop verification if PID is required |
| log unavailable | Exact log policy from future node | Report log unavailable if log read was authorized | Search logs broadly, create logs, inspect unrelated logs | Not authorized | Blocks log-based acceptance |
| `.runtime` unavailable | Exact runtime policy from future node | Report unavailable runtime object if required | Create or repair `.runtime` unless command side effect is authorized | Not authorized | Blocks runtime-object acceptance |
| unexpected frontend start | Future process/output observation if allowed | Stop according to approved frontend/backend rollback | Continue, open browser, accept frontend as okay | Not authorized | B0/B1 boundary breach |
| unexpected browser open | Operator observation or future bounded evidence | Stop node and report breach | Continue browser acceptance or click UI | Not authorized | Browser breach blocks stage |
| unexpected model/Ollama call | Future bounded evidence only if authorized | Stop app services if approved; report B0 | Run model diagnostics, pull/download model, call endpoint | Not authorized | Model breach is B0 |
| stop command unavailable | Future stop dependency check | Do not start backend; report missing stop path | Start anyway or invent stop command | Not authorized | Blocks backend start |
| working tree dirty | `git status --short --branch` if future node allows it | Stop before runtime; report dirty tree | Reset/checkout/clean without separate authorization | Not authorized | Dirty tree blocks runtime |
| Git branch not main | Future branch check | Stop before runtime; report wrong branch | Switch/reset during runtime node unless authorized | Not authorized | Wrong branch blocks runtime |

## 7. Backend Start Acceptance Design

027D does not accept or validate runtime results.

A future backend start node must record the exact command, working directory, environment variable whitelist, intended port, exit code or process state, and PID observation strategy if PID observation is authorized.

Future health check must be a separate stage unless the future 027E objective explicitly includes one narrowly bounded health command and acceptance rule.

Future localhost access must be separately authorized by exact host, port, endpoint, and command.

Future log read must be separately authorized, or the future start node must explicitly whitelist the exact log files, read windows, and redaction rules.

Future stop must have a pre-approved command and failure rule before backend start execution.

Future failures must not be repaired by installing dependencies, editing code, changing scripts, running tests, expanding endpoints, probing ports, or reading unapproved runtime objects.

Future tests, builds, installs, dependency updates, formatters, migrations, and generated-output commands require separate authorization.

## 8. File / Object Governance

| Object | Current 027D Status | Future Earliest Stage | Read Policy | Write Policy | Rationale |
| --- | --- | --- | --- | --- | --- |
| backend code | read-only-reference | Future implementation or backend runtime gate | Static read only in 027D | No writes in 027D | Backend code defines runtime target and endpoints |
| frontend code | read-only-reference | Frontend governance/runtime gate | Static read only in 027D | No writes in 027D | Frontend can call backend/model surfaces when running |
| `scripts/` | read-only-reference | Separate script implementation or runtime gate | Static read only in 027D | No writes in 027D | Scripts combine start, stop, PID/log, ports, browser, and watchdog |
| `.app` | forbidden / not authorized | Dedicated desktop launcher gate | No execution; static classification only if authorized | No writes in 027D | `.app` can hide command flow and bypass CLI gates |
| `.runtime/docgen` | forbidden / not authorized | Runtime observation or stop verification gate | No read in 027D | No write in 027D | Runtime state can reveal or alter live process status |
| PID files | forbidden / not authorized | Stop verification gate | No PID body read in 027D | No manual writes | PID values require ownership validation |
| logs | forbidden / not authorized | Log-read gate | No log body read in 027D | No log writes or cleanup | Logs may contain runtime data or secrets |
| `requirements.txt` | read-only-reference | Dependency governance gate | Static read only in 027D | No writes in 027D | Dependency fixes are outside runtime governance |
| secrets / tokens / credentials | forbidden | Dedicated secret-handling gate only | No read | No write | Secret exposure is outside launcher governance |
| local launcher static assets | read-only-reference | Separate static launcher gate | Static read only if authorized | No writes in 027D | Static V1 state remains no-runtime |
| docs governance files | read-only-reference except target document | Current 027D target doc only | Prior docs may be read as evidence | Only target 027D document may be written | Governance chain must stay append-only by gate |

## 9. 027E Entry Conditions

Recommended next node: `LOCAL-LAUNCHER-027E-INDEPENDENT-RUNTIME-BACKEND-SINGLE-SHOT-START-AUTHORIZATION-GATE`.

| Item | Recommendation |
| --- | --- |
| 027E Entry Status | Not allowed until the 027D PR is merged and post-merge main baseline is accepted. |
| Required Preconditions | 027D document merged to `main`; post-merge baseline and local alignment complete; worktree clean; `main` remains protected; 027C stop / rollback rules inherited. |
| Allowed Write Scope Recommendation | One future runtime authorization report or governance document, as separately specified by the total-control objective. |
| Allowed Runtime Scope Recommendation | At most one backend single-shot start command, no frontend, no browser, no watchdog, no `.app`, no model path. |
| Forbidden Scope Recommendation | Frontend, browser, watchdog, `.app`, Ollama, model inference, broad endpoint smoke, tests, builds, installs, dependency updates, script rewrites, broad runtime/PID/log reads. |
| Acceptance Recommendation | Exact command transcript, cwd, env whitelist, port, timeout, exit code/process state, and approved stop readiness. |
| Rollback Recommendation | Use only the stop / rollback path inherited from 027C and approved by 027E; failed stop is B0. |
| Still Forbidden Actions | Automatic health check, automatic browser open, frontend start, watchdog, `.app`, Ollama/model, dependency repair, test/build/install, script edits, broad port probing. |

027E may become the first actual backend single-shot runtime authorization only if a later total-control objective explicitly says so.

027D itself does not execute or authorize any runtime action.

## 10. Risk Register

| Risk ID | Risk Description | Level | Evidence | Control Rule | Blocking Status |
| --- | --- | --- | --- | --- | --- |
| R-027D-001 | 027D is misread as actual backend start authorization. | B1 | Node name references backend single-shot start. | State governance-only boundary in metadata, purpose, acceptance, and conclusion. | Blocks runtime in 027D. |
| R-027D-002 | Backend start expands into full `run_web_ui.sh` chain. | B1 | `run_web_ui.sh` starts backend/frontend, uses PID/log, curl/lsof/open, and can start watchdog. | Future 027E may choose only one backend command; combined launcher forbidden. | Blocks combined launcher. |
| R-027D-003 | Frontend is started accidentally. | B1 | `run_web_ui.sh` and `app.py` define Streamlit frontend path. | Frontend must wait for a later gate. | Blocks frontend. |
| R-027D-004 | Watchdog is enabled accidentally. | B1 | `web_ui_watchdog.sh` restarts missing listeners; self-heal can launch it. | No-watchdog-first rule. | Blocks watchdog. |
| R-027D-005 | `.app` is triggered accidentally. | B1 | Prior gates classify `.app` as command-flow bypass. | `.app` remains forbidden until desktop launcher gate. | Blocks `.app`. |
| R-027D-006 | localhost or endpoint is accessed. | B1 | README/RUNBOOK/scripts reference local ports and `/health`. | Endpoint and localhost require separate exact authorization. | Blocks endpoint/localhost. |
| R-027D-007 | PID/log/runtime is read or written. | B1 | Scripts reference `.runtime/docgen`, PID files, and logs. | Runtime objects require future explicit read/write scope. | Blocks runtime object access. |
| R-027D-008 | Port conflict is probed with `curl` or `lsof`. | B1 | Scripts and docs include `curl` and `lsof` examples. | Port observation requires a future exact command gate. | Blocks port probing. |
| R-027D-009 | Import/dependency error leads to install or code modification. | B1 | `requirements.txt` and README installation guidance exist. | Dependency repair is a separate gate. | Blocks repair expansion. |
| R-027D-010 | Ollama/model endpoint is triggered. | B0 | `app.py` and backend routers expose model-related surfaces. | Model authorization is a later independent gate. | Blocks non-model runtime. |
| R-027D-011 | 027E is misread as automatic runtime node. | B2 | 027E is proposed after backend start governance. | 027E requires a new explicit objective and may remain governance-only. | Blocks automatic 027E execution. |
| R-027D-012 | Main lock causes accidental direct main push. | B2 | Main is locked/protected. | Publish only release branch and PR. | Not blocking branch PR path. |

## 11. Acceptance Criteria

- Only the target document is added or updated.
- `git diff --name-only` shows only `docs/zdoc-local-launcher-027d-independent-runtime-backend-single-shot-start-governance-gate.md`.
- `git diff --check` passes.
- No service is started.
- No service is stopped.
- No localhost or `127.0.0.1` is accessed.
- No `curl`, `lsof`, or `open` command is executed.
- No `.app` launcher is run.
- No startup script is run.
- No stop script is run.
- No `uvicorn` or `streamlit` command is run.
- No `.runtime`, PID, or log body is touched.
- No endpoint, Ollama, or model inference action is performed.
- No tests, builds, installs, dependency updates, migrations, formatters, or generated-output commands are run.
- No scripts, `.app`, README, RUNBOOK, local launcher static assets, historical governance documents, runtime code, backend code, frontend code, or configuration files are modified.
- Only the 027D publishing branch may be pushed.
- `main` is not pushed.
- No final mainline tag is created in 027D.
- A PR is created successfully, or manual PR information is output.

## 12. Final Conclusion

027D is complete when this document is the only file change, it passes diff validation, it is committed on `local-launcher-027d-backend-single-shot-start-governance-gate`, the branch is pushed, and a PR is created or manual PR information is provided.

027D allows entry into 027D PR merge readiness audit only after the branch/PR publication is complete.

027E is a future backend single-shot start authorization gate or governance precondition, depending on a later total-control objective.

027E must continue to forbid frontend, browser, watchdog, `.app`, Ollama, model inference, broad endpoint smoke, tests, builds, installs, dependency updates, script rewrites, broad PID/log/runtime reads, and repair expansion unless a later independent node explicitly authorizes them.

This node does not authorize any runtime, backend start execution, frontend, service stop execution, endpoint, localhost, Ollama, model inference, browser, screenshot, script execution, `.app`, watchdog, background process, port probe, health check, test, build, install, dependency update, or live acceptance capability.

027D must not be considered complete on the mainline until its PR is merged to `main` and a later post-merge baseline gate accepts that state.

PR merge is not authorized in 027D. PR merge readiness audit may be entered after this PR is published. 027E must not be entered before the 027D PR is merged.
