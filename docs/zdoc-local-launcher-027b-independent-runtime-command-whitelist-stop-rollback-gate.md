# LOCAL-LAUNCHER-027B Independent Runtime Command Whitelist Stop Rollback Gate

## 1. Node Metadata

| Field | Value |
| --- | --- |
| Node | `LOCAL-LAUNCHER-027B-INDEPENDENT-RUNTIME-COMMAND-WHITELIST-STOP-ROLLBACK-GATE` |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `local-launcher-027b-runtime-command-whitelist-stop-rollback-gate` |
| Baseline HEAD | `c09926f165441c788d8b35244d0c145b16e54a49` |
| Baseline Tag | `v0.1.708-local-launcher-027a-post-merge-main-baseline` |
| Previous Gates | `LOCAL-LAUNCHER-026G-INDEPENDENT-LINE-STATIC-GOVERNANCE-CLOSURE-ARCHIVE-GATE`; `LOCAL-LAUNCHER-027-INDEPENDENT-RUNTIME-READINESS-PREFLIGHT-AUDIT`; `LOCAL-LAUNCHER-027A-INDEPENDENT-RUNTIME-AUTHORIZATION-GOVERNANCE-DESIGN`; `LOCAL-LAUNCHER-027A-POST-MERGE-MAIN-BASELINE-AUDIT`; `LOCAL-LAUNCHER-027A-LOCAL-MAIN-ALIGNMENT-GATE` |
| Execution Type | command whitelist, stop, and rollback governance only |
| Write Scope | only this document |
| Runtime Policy | forbidden in 027B |
| Service Policy | no service start, stop, restart, watchdog, or background execution |
| Localhost Policy | no localhost or `127.0.0.1` access |
| Endpoint Policy | no endpoint call, no health check, no smoke |
| Ollama / Model Policy | no Ollama, no model inference, no model endpoint call |
| Browser Policy | no browser open, no browser acceptance |
| Screenshot Policy | no screenshot |
| Branch / PR Policy | publish through the 027B branch and PR only; do not push `main`; do not merge this PR in 027B |

## 2. Purpose

027B is not a runtime node.

027B is not a service start node.

027B is not a localhost access node.

027B is not an endpoint verification node.

027B is not an Ollama or model inference node.

027B only records the future runtime command whitelist policy, stop conditions, rollback rules, and failure handling rules that must exist before any later runtime smoke test is authorized.

027B is published through a branch and PR path because `main` is locked/protected. It does not directly push `main`.

## 3. Runtime Command Governance Principles

1. No Runtime Yet Principle: 027B does not authorize runtime execution.
2. Explicit Command Whitelist Principle: later nodes may execute only commands explicitly named by their own whitelist.
3. Stop Before Start Principle: stop commands and rollback rules must be designed before any start command is authorized.
4. No Watchdog First Principle: the first runtime stage must not enable watchdog, self-heal, launchd, or auto-restart.
5. No App Bypass Principle: the first runtime stage must not use `.app` launchers.
6. No Browser First Principle: the first runtime stage must not automatically open a browser.
7. No Model First Principle: the first runtime stage must not touch Ollama, model inference, `localhost:11434`, `/local-llm/preview-safe`, or `/actions/ollama/*`.
8. Single Action Principle: one node may authorize only one minimum runtime phase.
9. Observability Without Expansion Principle: if a future runtime action fails, collect only the information already authorized by that node.
10. Stop-on-Breach Principle: if a future stage observes out-of-scope runtime, PID/log anomalies, port anomalies, model-call signals, browser auto-open, or unexpected endpoint access, it must stop and report without repair expansion.

## 4. Command Classification Table

| Command / Family | Current 027B Status | Future Earliest Stage | Allowed Conditions | Forbidden Conditions | Stop / Rollback Dependency | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `scripts/run_web_ui.sh` | forbidden / not authorized | R5 or later, only if decomposed controls are proven | Only after backend start, stop, health, frontend no-browser behavior, and exact flags are separately governed | Forbidden in 027B and any first runtime action | Requires approved backend and frontend stop rules | It combines backend, frontend, PID/log writes, port probes, optional watchdog, and browser open behavior. |
| `scripts/start_web_ui_background.sh` | forbidden / not authorized | After R5 and only in a background-specific gate | Only after foreground lifecycle is proven and background behavior is explicitly accepted | Forbidden before foreground stop/rollback evidence | Requires background stop and orphan-process rollback | It delegates to `run_web_ui.sh --background` and writes control logs. |
| `scripts/web_ui_watchdog.sh` | forbidden / not authorized | After browser acceptance and service lifecycle governance | Only in a late watchdog-management gate | Forbidden in first runtime stages | Requires verified stop and anti-restart rollback | Watchdog can restart services and defeat single-shot control. |
| `scripts/stop_web_ui_background.sh` | forbidden / not authorized | R1 design; executable only in a later stop gate | Future use must name PID/log read scope and exact process-match rules | Forbidden in 027B | It is the prerequisite stop candidate for later start | Stop capability must be governed before service start. |
| `uvicorn` | forbidden / not authorized | R2 | One exact backend single-shot command after stop rule is accepted | Forbidden with frontend, browser, watchdog, model, or broad endpoint smoke | Requires pre-approved stop action | It is the most direct backend runtime entry. |
| `streamlit` | forbidden / not authorized | R5 | One exact frontend single-shot command with browser auto-open disabled | Forbidden before backend lifecycle is controlled | Requires frontend stop action | Frontend must follow backend start/stop proof. |
| `curl` | forbidden / not authorized | R3 | One exact health check after backend start and stop are controlled | Forbidden for broad API smoke, model endpoints, or localhost exploration | Requires backend stop on failed check | Endpoint access must be isolated from startup. |
| `lsof` | forbidden / not authorized | R3/R4 if explicitly named | Only exact port/process observation named by a future node | Forbidden as general port exploration | Requires no-kill observation policy | Port observation can expose or affect process handling if broadened. |
| `open` | forbidden / not authorized | R6 | Only a separately authorized browser acceptance action | Forbidden with service start or health check | Requires service stop and browser close rule | Browser launch must not be bundled with runtime start. |
| `.app` launcher | forbidden / not authorized | Dedicated desktop launcher gate after R6 | Only after command-line lifecycle and stop/rollback are proven | Forbidden in early runtime stages | Requires launcher-specific stop and failure handling | `.app` hides command flow and can trigger Terminal, scripts, logs, and browser. |
| `ollama` | forbidden / not authorized | R8 | Only in a separate model gate with no-download/no-pull rules | Forbidden before service, endpoint, browser, and boundary audits | Requires model-service stop rule if used | Model runtime is high-risk and last-stage only. |
| `ollama serve` | forbidden / not authorized | R8 | Only if a model gate explicitly authorizes it | Forbidden in 027B and early stages | Requires explicit model service rollback | It starts a model service. |
| `pytest` | forbidden / not authorized | Separate validation gate only | Only with a no-runtime test scope and explicit cache policy | Forbidden in 027B | Requires cleanup policy for generated artifacts | Tests can create caches or touch runtime-like paths. |
| `npm test` | forbidden / not authorized | Separate validation gate only | Only with exact package scope and no install/build/watch | Forbidden in 027B | Requires artifact cleanup policy | Frontend tooling can build, watch, or install. |
| `build / install` | forbidden / not authorized | Separate tooling gate only | Only after dependency and artifact scope are authorized | Forbidden in 027B | Requires rollback for generated files | Build/install can modify dependencies or artifacts. |
| `gh pr merge` | forbidden / not authorized | PR merge gate only | Only after PR readiness audit and explicit merge authorization | Forbidden in 027B | Requires main protection and post-merge audit plan | 027B may create PR, not merge it. |
| `git push main` | forbidden / not authorized | Never in this node; main remains protected | None in 027B | Forbidden because main is locked/protected | Requires separate controlled merge path | 027B must publish through branch and PR. |

## 5. Future Runtime Stage Whitelist

No future stage below is executed by 027B. Each stage requires a new independent authorization node.

| Stage | Entry Conditions | Allowed Commands | Forbidden Commands | Writable Scope | Runtime Scope | Stop Condition | Rollback Rule | Acceptance Method | Blocking Rule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1: Stop / Rollback Dry Governance | 027B merged and post-merge baseline accepted. | Governance-document edits only. | Service start, localhost, endpoint, curl, lsof, open, uvicorn, streamlit, Ollama, tests, build, install. | One future governance document. | None. | Stop if any executable runtime command appears. | Revise only the governance document. | Diff scope and static review. | Any runtime action blocks R1. |
| R2: Backend Single-Shot Start | R1 defines exact stop/rollback and command whitelist. | One exact backend start command selected by the future node. | Background, watchdog, frontend, browser, health check expansion, Ollama/model. | Future runtime report only if authorized. | Backend process only. | Stop on unexpected process, PID/log anomaly, port mismatch, browser open, or model signal. | Run the pre-approved backend stop action. | Command transcript plus bounded observation. | Missing stop path or unexpected side effect blocks R2. |
| R3: Backend Health Check | R2 start is successful and stoppable. | One exact health check command. | Broad smoke, frontend, browser, model endpoint, export/write-back. | Future health report only if authorized. | `/health` only. | Stop if any other endpoint is touched or command broadens. | Stop backend using pre-approved stop action. | Health response evidence and stop readiness. | Any endpoint expansion blocks R3. |
| R4: Backend Stop Verification | R2/R3 prove backend start and health boundaries. | One exact backend stop command and bounded verification command. | Frontend, browser, watchdog, model, broad port scan. | Future stop report only if authorized. | Backend stop only. | Stop if process ownership cannot be verified. | Report B0 if stop fails; do not repair broadly. | Proof that backend stopped or B0 reported. | Failed stop blocks later runtime. |
| R5: Frontend Single-Shot Start | Backend start/health/stop lifecycle is accepted. | One exact frontend start command with browser auto-open disabled. | `open`, `.app`, watchdog, model, generation/export/write-back. | Future frontend report only if authorized. | Frontend process only. | Stop on browser open, unexpected endpoint flow, or background chain. | Run pre-approved frontend stop, then backend stop if needed. | No-browser and bounded-process evidence. | Auto-open or watchdog blocks R5. |
| R6: Browser Manual Acceptance | Frontend start/stop is controlled. | One browser acceptance action named by the future node. | Ollama/model, export/write-back, broad endpoint testing, `.app` launchers. | Future browser report only if authorized. | Browser access to the approved UI only. | Stop if model, export, write-back, or unplanned endpoint is triggered. | Close browser/session and stop services. | Manual acceptance tied to exact allowed path. | Any model/write path blocks R6. |
| R7: Ollama / Model Boundary Audit | Service and browser boundaries are accepted. | Static or read-only model boundary audit only. | Model service start, model call, model pull/download, endpoint call. | Future model-boundary doc only. | None or static boundary only. | Stop if any model execution is needed. | Do not run model; report boundary gap. | Static model risk audit. | Any execution requirement blocks R7. |
| R8: Ollama / Model Controlled Test | R7 accepted and separate model gate approved. | One exact model/Ollama command or endpoint if named by that future node. | Model download, pull, external provider, generation/export/write-back unless explicitly allowed. | Future model report only if authorized. | Model path only. | Stop on missing local model, need for download/pull, external provider, or write path. | Stop model service if authorized; otherwise stop app services and report. | No-write, no-download, no-export evidence. | Any installation, pull, or write-back requirement blocks R8. |

## 6. Stop / Rollback Rule Design

Stop and rollback must exist before start because the repository contains combined backend/frontend scripts, background mode, watchdog restart logic, PID files, logs, browser-open behavior, and `.app` launchers. Without a bounded stop path, a future runtime action can leave services running or make evidence ambiguous.

Future stop commands must be white-listed before any start command. The future whitelist must name exact command text, allowed environment variables, expected PID/log file reads if any, and failure behavior.

PID, log, and runtime files are currently forbidden. A later node may authorize reading `.runtime/docgen` only after it specifies exact files, read-only method, redaction rules, and stop/rollback purpose. A later node may authorize reading logs only after it defines exact log paths, maximum read scope, and secret-redaction handling.

The stop script may be executable only after a future stop/rollback gate defines PID ownership checks, process command checks, fallback port checks, and failure behavior. It must not be used in 027B.

Watchdog is disabled for the first runtime authorization because automatic restart can hide failure, defeat stop verification, and create long-running side effects. `.app` is disabled for the first runtime authorization because it can wrap commands through Terminal or osascript and can open logs, scripts, or browser paths outside the visible CLI flow.

If startup fails in a future stage, the operator must first run only the authorized stop/rollback action and report the exact failure. The operator must not edit scripts, install dependencies, run tests, broaden endpoint access, or inspect unapproved runtime files.

If stop fails, the future stage becomes B0 blocked. If git state, branch protection, PR state, or baseline state is abnormal, runtime work must not continue.

## 7. Port / Endpoint Authorization Matrix

| Port / Endpoint | Current Status | Future Earliest Stage | Required Preconditions | Forbidden Until | Notes |
| --- | --- | --- | --- | --- | --- |
| `8010` | forbidden / not authorized | R2 for backend start, R3 for health | Exact backend command, stop rule, no-cross-system policy | R2 node explicitly authorizes it | `run_web_ui.sh` and app defaults reference this backend port. |
| `8501` | forbidden / not authorized | R5 | Backend lifecycle accepted, frontend command exact, browser auto-open disabled | R5 node explicitly authorizes it | Streamlit UI port appears in scripts and README. |
| `8000` | forbidden / not authorized | Separate legacy/backend gate only | Explicit choice to use legacy README/RUNBOOK path | A future node names it | README/RUNBOOK examples do not authorize current runtime. |
| `11434` | forbidden / not authorized | R7 audit then R8 test | Model boundary audit, no-download/no-pull policy, stop rule | R8 node explicitly authorizes it | Ollama default appears in `app.py`; no access in 027B. |
| `/health` | forbidden / not authorized | R3 | Backend start is controlled and stoppable | R3 node explicitly authorizes it | Must be one exact health check only. |
| `/local-llm/preview-safe` | forbidden / not authorized | R8 or later | Model gate, no-write policy, no-download/no-pull policy | Model gate explicitly authorizes it | It is model-adjacent even if named safe. |
| `/actions/ollama/*` | forbidden / not authorized | R8 or later | Model gate and endpoint-specific no-write rules | Model gate explicitly authorizes it | Includes preview/review/draft/smoke surfaces. |
| localhost | forbidden / not authorized | Stage-specific | Exact host, port, endpoint, and command in a future node | A future node names each access | No broad localhost exploration. |
| `127.0.0.1` | forbidden / not authorized | Stage-specific | Exact host, port, endpoint, and command in a future node | A future node names each access | No port probing in 027B. |

## 8. File / Runtime Object Governance

| Object | Current 027B Status | Future Earliest Stage | Read Policy | Write Policy | Rationale |
| --- | --- | --- | --- | --- | --- |
| `.runtime/docgen` | forbidden / not authorized | R1 design, executable read only in later runtime stage | No body read in 027B; future exact-file read only | No writes except future runtime command side effects if authorized | Contains PID/runtime state and can reveal or mutate execution state. |
| PID files | forbidden / not authorized | R4 stop verification | Future exact PID file read only if stop rule requires it | No manual writes | PID evidence must be tied to a controlled stop rule. |
| logs | forbidden / not authorized | After stop/rollback policy defines redaction and path limits | No log body read in 027B | No writes except future command side effects if authorized | Logs may contain runtime data or secrets. |
| output / job / export | forbidden / not authorized | Not in local launcher runtime preflight | No read in 027B | No write | These are generation/export artifacts outside this gate. |
| secrets / tokens / credentials | forbidden / not authorized | Never unless a separate secret-handling gate exists | No read | No write | Secret exposure is out of scope. |
| `scripts/` | read-only evidence only | Separate implementation gate | Static read only in governance nodes | No modification in 027B | Startup and stop scripts are high-impact runtime surfaces. |
| `.app` | read-only evidence only if separately allowed | Dedicated desktop launcher gate | No execution; static classification only | No modification in 027B | App launchers bypass command-line visibility. |
| `local_launcher/v1` | read-only evidence only | Separate static launcher gate | Static read only | No modification in 027B | Current V1 state is no-runtime. |
| backend files | read-only evidence only | Backend runtime or implementation gate | Static read only | No modification in 027B | Backend code exposes endpoints and model-adjacent routes. |
| frontend files | read-only evidence only | Frontend runtime or implementation gate | Static read only | No modification in 027B | Frontend can call backend and model preview actions when running. |

## 9. 027C Entry Conditions

Recommended next node: `LOCAL-LAUNCHER-027C-INDEPENDENT-RUNTIME-STOP-ROLLBACK-DRY-GOVERNANCE-GATE`.

| Item | Recommendation |
| --- | --- |
| 027C Entry Status | Allowed only after 027B PR is merged and post-merge baseline is accepted. |
| Required Preconditions | 027B document merged to `main`; worktree clean; main protected; no runtime occurred in 027B. |
| Allowed Write Scope Recommendation | One 027C governance document defining dry stop/rollback preconditions and evidence shape. |
| Forbidden Scope Recommendation | No scripts, `.app`, README, RUNBOOK, local launcher assets, runtime code, `.runtime`, PID, log, output, job, export, secrets, tokens, credentials. |
| Acceptance Recommendation | Diff limited to the 027C document; no service start; no localhost; no curl/lsof/open; no tests/build/install. |
| Rollback Recommendation | If 027C over-scopes, revise only the 027C document before commit. |
| Still Forbidden Actions | Service start, localhost, endpoint, curl, lsof, open, `.app`, startup scripts, watchdog, stop scripts, Streamlit, uvicorn, Ollama, model inference, tests, build, install. |

027C is still a governance-document node. It must not start services, access localhost, execute curl/lsof/open, touch Ollama or model inference, or perform health checks. Its purpose is to make stop/rollback dry governance an executable precondition for a later runtime stage.

## 10. Risk Register

| Risk ID | Risk Description | Level | Evidence | Control Rule | Blocking Status |
| --- | --- | --- | --- | --- | --- |
| R-001 | 027B is misread as runtime authorization. | B1 | 027B follows runtime readiness and command whitelist gates. | State no runtime authorization in metadata, purpose, acceptance, and conclusion. | Blocks runtime, not this document. |
| R-002 | Multiple startup entries cause unauthorized start. | B1 | `run_web_ui.sh`, background script, README/RUNBOOK, and launchers describe start paths. | Future nodes may authorize one command only. | Blocks runtime until whitelist stage. |
| R-003 | `.app` bypass triggers runtime. | B1 | App launchers can wrap scripts and browser/log actions. | `.app` remains forbidden until dedicated gate. | Blocks `.app` use. |
| R-004 | Watchdog auto-restart makes stop uncontrollable. | B1 | `web_ui_watchdog.sh` restarts when listeners are missing. | No-watchdog-first principle. | Blocks watchdog use. |
| R-005 | Service start happens before stop/rollback verification. | B1 | Stop script exists but is not currently authorized for execution. | Stop-before-start rule. | Blocks R2 until R1/R4 controls exist. |
| R-006 | PID/log/runtime write chain escapes control. | B1 | Scripts reference `.runtime/docgen`, PID files, and logs. | Authorize exact read/write surfaces only in later runtime nodes. | Blocks runtime file touch. |
| R-007 | localhost/endpoint is triggered accidentally. | B1 | Scripts and docs reference `127.0.0.1`, `localhost`, and `/health`. | Endpoint access requires separate stage. | Blocks endpoint access. |
| R-008 | Ollama/model inference is triggered accidentally. | B1 | `app.py` and backend routes reference Ollama/model paths. | Model-first prohibition; R7/R8 separation. | Blocks model actions. |
| R-009 | Port conflict or old service residue distorts evidence. | B1 | Scripts contain port-owner and lsof logic for `8010` and `8501`. | Future observation must be exact and stop-aware. | Blocks broad port probing. |
| R-010 | Main locked means direct main publish is unavailable. | B2 | Main is protected/locked; prior 027A used PR path. | 027B must use branch and PR only. | Not blocking branch PR path. |
| R-011 | 027C is misread as smoke test. | B2 | 027C is a future stop/rollback dry governance gate. | State 027C remains governance-only. | Blocks runtime in 027C. |

## 11. Acceptance Criteria

- Only the target document is added or updated.
- `git diff --name-only` shows only `docs/zdoc-local-launcher-027b-independent-runtime-command-whitelist-stop-rollback-gate.md`.
- `git diff --check` passes.
- No service is started.
- No localhost or `127.0.0.1` is accessed.
- No `curl`, `lsof`, or `open` command is executed.
- No `.app` launcher is run.
- No startup script is run.
- No `.runtime`, PID, or log body is touched.
- No endpoint, Ollama, or model inference action is performed.
- No tests, builds, installs, dependency updates, migrations, formatters, or generated-output commands are run.
- No scripts, `.app`, README, RUNBOOK, local launcher static assets, historical governance documents, runtime code, backend code, frontend code, or configuration files are modified.
- Only the 027B publishing branch may be pushed.
- `main` is not pushed.
- No final mainline tag is created in 027B.
- A PR is created successfully, or manual PR information is output.

## 12. Final Conclusion

027B is complete when this document is the only file change, it passes diff validation, it is committed on `local-launcher-027b-runtime-command-whitelist-stop-rollback-gate`, the branch is pushed, and a PR is created or manual PR information is provided.

After 027B PR publication, entry to `LOCAL-LAUNCHER-027C-INDEPENDENT-RUNTIME-STOP-ROLLBACK-DRY-GOVERNANCE-GATE` is allowed only after the 027B PR is merged and post-merge baseline is accepted.

027C is still a governance-document node. It must not start services, access localhost, execute curl/lsof/open, run `.app`, run startup scripts, touch `.runtime`/PID/log bodies, call endpoints, touch Ollama/model inference, run browser acceptance, take screenshots, or run tests/build/install.

This node does not authorize any runtime, endpoint, localhost, Ollama, model inference, browser, screenshot, service start, service stop, watchdog, background process, port probe, health check, test, build, install, script execution, or `.app` launcher execution.

027B must not be considered complete on the mainline until its PR is merged to `main` and a later post-merge baseline gate accepts that state.
