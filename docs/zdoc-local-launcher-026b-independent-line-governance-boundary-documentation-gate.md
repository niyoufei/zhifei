# LOCAL-LAUNCHER-026B Independent Line Governance Boundary Documentation Gate

## 1. Node Metadata

| Field | Value |
| --- | --- |
| Node | `LOCAL-LAUNCHER-026B-INDEPENDENT-LINE-GOVERNANCE-BOUNDARY-DOCUMENTATION-GATE` |
| Repository | `/Users/youfeini/Desktop/文档生成系统` |
| Branch | `main` |
| Baseline HEAD | `5d8f08919d1c7b3986cb41c8245575b523d66d74` |
| Baseline Tag | `v0.1.700-system-autonomy-021b-next-phase-governance-entry-acceptance-archive-gate` |
| Previous Gates | `LOCAL-LAUNCHER-026-INDEPENDENT-LINE-PREFLIGHT-AUDIT`; `LOCAL-LAUNCHER-026A-INDEPENDENT-LINE-GOVERNANCE-ENTRY-DESIGN` |
| Execution Type | Governance boundary documentation gate; narrow documentation write only; no development |
| Runtime Policy | No runtime execution is authorized |
| Service Policy | No service start, stop, restart, preflight, health check, or background process is authorized |
| Localhost Policy | No `localhost`, `127.0.0.1`, port, HTTP, endpoint, or Web UI access is authorized |
| Model/Ollama Policy | No Ollama command, model inventory, model inference, prompt input, model pull, or model run is authorized |

## 2. Purpose

This node exists only to freeze the governance boundary for the LOCAL-LAUNCHER independent line.

This node is not a development node.

This node is not a runtime node.

This node is not a runtime preflight.

This node is not an endpoint authorization.

This node is not an Ollama or model inference authorization.

This node does not authorize service startup, Web UI startup, `localhost` access, `127.0.0.1` access, endpoint checks, port checks, script execution, `.app` launcher execution, tests, build, install, migration, formatting, generation, export, write-back, real project data reading, or real KG reading.

This node only records the canonical asset boundary, historical reference boundary, forbidden runtime boundary, future write admission rules, acceptance rules, rollback rules, and next-node entry conditions for the LOCAL-LAUNCHER independent line.

## 3. Governance Boundary Principles

1. Independent Line Principle: LOCAL-LAUNCHER must advance as an independent line and must not inherit execution authority from the SYSTEM-AUTONOMY document governance chain.
2. No Runtime Principle: no service, Web UI, background process, watchdog, endpoint, port probe, or runtime bridge may be started before a separate explicit runtime authorization node.
3. No Endpoint Principle: `localhost`, `127.0.0.1`, local ports, HTTP requests, health checks, and endpoint calls remain prohibited.
4. No Model Principle: Ollama, model inventory, model inference, prompt input, model pulls, model runs, and generated model output remain prohibited.
5. Canonical First Principle: the canonical LOCAL-LAUNCHER asset set must be selected before any static asset change is authorized.
6. Narrow Write Principle: every later writable node must declare an exact file allowlist before any edit.
7. Diff-Bounded Principle: acceptance must be based on git diff scope and static document checks, not runtime behavior or running results.
8. Stop-on-Breach Principle: if a write, command, read, or side effect crosses the authorized boundary, execution must stop and the breach must be reported before any further action.

## 4. Canonical Asset Boundary

| Path | Classification | Current Role | Future Write Policy | Preconditions | Rationale |
| --- | --- | --- | --- | --- | --- |
| `local_launcher/` | canonical | Current normalized LOCAL-LAUNCHER asset root containing static console versions | Writable only in a later explicit static asset boundary node | Exact file allowlist, no runtime permission, no service or endpoint command | The underscore path is the preferred canonical root for future static LOCAL-LAUNCHER governance. |
| `local_launcher/v1/` | canonical | Current canonical static V1 console candidate | Writable only for static asset boundary or static documentation changes | 026C or later must authorize exact files; all runtime flags must remain disabled | Existing README states that V1 is professional static console only and not runtime preflight. |
| `local_launcher/v1/README.md` | canonical | Static console boundary description | Writable only for boundary clarification | Exact allowlist and diff-bounded acceptance | It documents no service, no endpoint, no Ollama, no test, no trial, no generation/export/write-back. |
| `local_launcher/v1/launcher-state.json` | canonical | Static disabled-state snapshot | Writable only to preserve or strengthen disabled governance state | Exact allowlist; values must not enable service, endpoint, Ollama, generation, export, write-back, trial, or controlled execution | It is the clearest machine-readable static permission matrix for the canonical candidate. |
| `local-launcher-v1/` | historical-reference | Historical `LOCAL-LAUNCHER-017-R1` professional static UI skeleton | Not writable by default | A later migration or archive node must explicitly decide whether to migrate, freeze, or supersede it | Double-writing both launcher roots would create ambiguity. |
| `local-launcher-v1/README.md` | historical-reference | Historical no-op/mock/disabled boundary description | Read-only unless a migration/archive node authorizes it | Exact migration/archival objective and allowlist | It is useful evidence but must not become a second active line. |
| `local-launcher-v1/app.js` | historical-reference | Historical pure frontend no-op panel switching and mock config display | Read-only unless a migration/archive node authorizes it | Exact migration/archival objective and allowlist | It contains no-op UI behavior, but future canonical work should not extend this path by default. |
| `docs/zdoc-local-launcher-v1-runtime-independent-boundary-and-risk-authorization-gate-local-launcher-025.md` | read-only-reference | Runtime boundary and risk authorization reference from LOCAL-LAUNCHER-025 | No direct modification | Any correction must be a separate governance node, not 026B/026C asset work | It establishes no runtime, no endpoint, no Ollama, no model inference, and no automatic next-stage execution. |
| `docs/zdoc-system-autonomy-021a-next-phase-governance-entry-gate.md` | read-only-reference | SYSTEM-AUTONOMY next-phase entry candidate that identifies LOCAL-LAUNCHER as a separate line | No direct modification | SYSTEM-AUTONOMY-specific authorization only | It confirms LOCAL-LAUNCHER must not be entered automatically from SYSTEM-AUTONOMY. |
| `docs/zdoc-system-autonomy-021b-next-phase-governance-entry-acceptance-archive-gate.md` | read-only-reference | SYSTEM-AUTONOMY acceptance/archive closeout | No direct modification | SYSTEM-AUTONOMY-specific authorization only | It freezes the pause of SYSTEM-AUTONOMY and prevents inheritance into LOCAL-LAUNCHER. |
| `scripts/run_web_ui.sh` | forbidden-runtime | Real Web UI launcher that can start backend and Streamlit, write logs/PIDs, and open local URLs | Not writable in LOCAL-LAUNCHER static governance nodes | Separate service/runtime authorization gate only | It is an executable runtime entry and is outside static governance. |
| `scripts/start_web_ui_background.sh` | forbidden-runtime | Background startup wrapper delegating to `run_web_ui.sh --background` | Not writable in LOCAL-LAUNCHER static governance nodes | Separate service/runtime authorization gate only | It writes control logs and triggers the real startup path. |
| `文档生成系统.app/` | forbidden-runtime | Desktop app launcher capable of invoking background startup through Terminal/osascript | Not writable in LOCAL-LAUNCHER static governance nodes | Separate desktop/runtime authorization gate only | It can bypass normal command-line review and trigger service startup. |
| `施组专家系统.app/` | forbidden-runtime | Quick launcher with local URLs, health checks, retry behavior, and script delegation | Not writable in LOCAL-LAUNCHER static governance nodes | Separate desktop/runtime authorization gate only | It contains `127.0.0.1` URLs, health checks, script calls, wrapper creation, and log writes. |

## 5. Runtime Isolation Boundary

### Forbidden Execution Objects

- `scripts/run_web_ui.sh`
- `scripts/start_web_ui_background.sh`
- `scripts/create_desktop_launcher.sh`
- `scripts/install_web_ui_launchd.sh`
- `scripts/web_ui_watchdog.sh`
- `文档生成系统.app/`
- `施组专家系统.app/`
- Any `.app` launcher
- `uvicorn`
- `streamlit`
- `ollama`
- `ollama serve`
- Any service startup, stop, restart, watchdog, launchd, background, preflight, health-check, or model invocation command

### Forbidden Access Objects

- `localhost`
- `127.0.0.1`
- Any local port
- Any endpoint
- Any Web UI URL
- Any health URL
- Any HTTP or browser access path
- Any runtime status URL

### Forbidden Touch Objects

- `runtime`
- `.runtime/`
- PID files
- log files and log bodies
- `output/`
- `job`
- `export`
- endpoint code or endpoint behavior
- Ollama state
- model inventory
- model inference
- prompt input
- secrets, tokens, credentials, and local key files
- real KG
- real project data
- generated result files

### Forbidden Command Families

- Service startup commands
- Background or long-running commands
- Port probing commands
- HTTP request commands
- Browser opening commands
- `.app` launcher commands
- Ollama commands
- Model inference commands
- Test commands
- Build commands
- Install or dependency update commands
- Migration commands
- Formatting or fix commands
- Generation, export, write-back, or database mutation commands

### Allowed Static Reading Objects

- `local_launcher/v1/README.md`
- `local_launcher/v1/launcher-state.json`
- Other static files under `local_launcher/v1/` when explicitly allowed by a later node
- Historical static files under `local-launcher-v1/` as read-only reference
- 025, 021A, and 021B governance documents as read-only reference
- README or RUNBOOK static text only when a later node needs citation of forbidden runtime instructions; these files must not be executed or modified without explicit authorization

### Conditions Required to Lift Restrictions

Restrictions may be lifted only by a later, explicit, single-purpose node that states:

1. Exact node name and objective.
2. Exact repository, branch, baseline HEAD, and baseline tag.
3. Exact command allowlist.
4. Exact file read/write allowlist.
5. Explicit service, endpoint, port, model, and data boundary.
6. Stop conditions.
7. Rollback and cleanup requirements.
8. Acceptance criteria.
9. Whether commit, tag, and push are allowed.

Absent all of those conditions, every runtime restriction remains active.

## 6. 026C Entry Conditions

| Field | Value |
| --- | --- |
| 026C Recommended Node Name | `LOCAL-LAUNCHER-026C-INDEPENDENT-LINE-CANONICAL-STATIC-ASSET-BOUNDARY-GATE` |
| 026C Entry Status | Allowed only after this 026B document is committed, tagged, pushed, and clean |
| Required Preconditions | Clean worktree; current branch `main`; 026B tag on latest accepted HEAD; exact writable file allowlist; explicit no-runtime policy; explicit no-service and no-localhost policy |
| Allowed Write Scope Recommendation | Prefer a single governance/static-boundary document, or a narrowly authorized update to `local_launcher/v1/README.md` and/or `local_launcher/v1/launcher-state.json` only |
| Forbidden Scope Recommendation | `scripts/`, `.app` bundles, `.runtime/`, backend/frontend runtime code, endpoint code, model/Ollama files, README, RUNBOOK, historical SYSTEM-AUTONOMY docs, and historical LOCAL-LAUNCHER docs unless explicitly listed |
| Acceptance Recommendation | `git diff --name-only`, targeted `git diff -- <allowed files>`, `git diff --check`, and `git status --short --branch`; no tests and no runtime validation |
| Rollback Recommendation | If any unauthorized file appears in diff, stop immediately and report the file list and diff scope before attempting correction |
| Still Forbidden Actions | Starting services; accessing `localhost`; accessing `127.0.0.1`; touching runtime/endpoint/Ollama/model inference; modifying scripts or `.app`; running tests, build, install, model calls, endpoint calls, or port probes |

026C may clarify canonical static asset boundaries, but it must still not develop runtime behavior.

026C must not start services.

026C must not access `localhost`.

026C must not touch runtime, endpoint, Ollama, or model inference.

026C must not modify `scripts/` or `.app` bundles.

026C must not execute tests, build, install, or model calls.

## 7. Risk Register

| Risk ID | Risk Description | Level | Evidence | Control Rule | Blocking Status |
| --- | --- | --- | --- | --- | --- |
| R-026B-01 | Two local launcher directories coexist: `local_launcher/` and `local-launcher-v1/` | B2 | Current tree contains both roots with V1 static assets | Treat `local_launcher/v1/` as canonical candidate and `local-launcher-v1/` as historical-reference until a migration/archive node decides otherwise | Not blocking 026C if write scope is explicit |
| R-026B-02 | Startup scripts contain real service entry points | B1 | `scripts/run_web_ui.sh` can start uvicorn and Streamlit and write runtime files; `scripts/start_web_ui_background.sh` delegates to it | Classify startup scripts as forbidden-runtime; no static governance node may execute or modify them | Blocking for runtime work; not blocking static governance |
| R-026B-03 | `.app` launchers can bypass command-line review and trigger runtime behavior | B1 | Desktop app launchers call background scripts, local URLs, health checks, and wrapper logic | Classify `.app` bundles as forbidden-runtime and require a separate desktop/runtime gate | Blocking for desktop/runtime work; not blocking static governance |
| R-026B-04 | README or documents contain `localhost` and `127.0.0.1` access instructions | B1 | README and RUNBOOK include local uvicorn, curl, smoke, and Web UI URL examples | Treat these as static text references only; do not execute, validate, or expand them in LOCAL-LAUNCHER static governance nodes | Not blocking static governance if no access occurs |
| R-026B-05 | Historical runtime, endpoint, and Ollama documents may be misread as current authorization | B2 | LOCAL-LAUNCHER and KG/model governance history contains runtime, endpoint, Ollama, and model stages | Require each new node to restate that historical docs are read-only reference and not execution authority | Not blocking if boundaries are restated |
| R-026B-06 | SYSTEM-AUTONOMY and LOCAL-LAUNCHER independent-line boundaries may be confused | B2 | 021A and 021B say LOCAL-LAUNCHER must not be entered automatically from SYSTEM-AUTONOMY | Treat 021A/021B as read-only closeout references and require LOCAL-LAUNCHER-specific node names and scopes | Not blocking if independent-line naming and scope remain explicit |

## 8. Acceptance Criteria

This node is accepted only if all of the following are true:

1. Only this target document is added or updated: `docs/zdoc-local-launcher-026b-independent-line-governance-boundary-documentation-gate.md`.
2. `git diff --name-only` shows only the target document before staging.
3. `git diff --check` passes.
4. No service is started.
5. No `localhost` or `127.0.0.1` access occurs.
6. No runtime, endpoint, Ollama, model inference, prompt, port, PID, log body, output, job, export, real project data, or real KG is touched.
7. No tests, build, install, dependency update, migration, formatting, generation, export, or write-back commands are run.
8. No `scripts/`, `.app`, README, RUNBOOK, 021A, 021B, 025, runtime code, endpoint code, model code, or configuration file is modified.
9. Commit is created with message `docs: add local launcher 026b governance boundary gate`.
10. Tag `v0.1.701-local-launcher-026b-governance-boundary-documentation-gate` points to the new commit.
11. `main` and the tag are pushed.
12. Final worktree and staging area are clean.

## 9. Final Conclusion

026B is a governance boundary documentation gate for the LOCAL-LAUNCHER independent line.

026B does not authorize runtime work.

026B does not authorize endpoint access.

026B does not authorize Ollama or model inference.

026B does not authorize service startup.

026B allows entry into 026C only as a static canonical asset boundary gate:

`LOCAL-LAUNCHER-026C-INDEPENDENT-LINE-CANONICAL-STATIC-ASSET-BOUNDARY-GATE`

026C must remain non-runtime, non-endpoint, non-Ollama, non-model-inference, non-service, no-localhost, no-test, no-build, and no-install unless a future explicit node separately authorizes a narrower exception.
