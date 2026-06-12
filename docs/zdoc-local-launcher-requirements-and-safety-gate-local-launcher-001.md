# ZDoc Local Launcher Requirements and Safety Gate - LOCAL-LAUNCHER-001

## 1. Node Identification

- Node: `LOCAL-LAUNCHER-001-ZDOC-LOCAL-APP-REQUIREMENTS-AND-SAFETY-GATE`
- Repository baseline: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Current mainline: `LOCAL-LAUNCHER`
- Current node nature: docs-only requirements and safety gate
- Scope: requirements and safety-boundary documentation for a future ZDoc local launcher only

LOCAL-LAUNCHER-001 is not implementation.

LOCAL-LAUNCHER-001 is not a service start, stop, endpoint access, Ollama run, trial, generation, export, or write-back node.

LOCAL-LAUNCHER-001 does not create an App, script, launcher, UI, backend change, frontend change, configuration change, runtime process, or local service.

## 2. Baseline

- HEAD: `ba8f9d455f7082c103381e4b6de411c4b326eb86`
- Tag: `v0.1.636-zdoc-sanitized-sample-metadata-registration-review-user-authorization-receipt-gate`
- Current mainline: `LOCAL-LAUNCHER`
- Current node nature: docs-only requirements and safety gate
- Preceding controller status: `MODEL-FLEET-GOVERNANCE-075` has been reviewed and approved by ChatGPT master-control, and the `MODEL-FLEET-GOVERNANCE` mainline is temporarily closed.
- Current authorization status inherited by LOCAL-LAUNCHER-001: no controlled execution authorization, no metadata-only review execution authorization, no runtime authorization, no trial authorization, and no generation/export/write-back authorization.

## 3. Purpose

LOCAL-LAUNCHER-001 exists only to define requirements and safety boundaries for a future ZDoc local startup App, one-click launcher, and local console.

`LOCAL-LAUNCHER-001 defines requirements and safety boundaries only. It does not implement, start, stop, or access any runtime service.`

This node documents:

1. The positioning of the future startup App.
2. Candidate technical routes.
3. User roles and local usage scenarios.
4. V0 safety-shell requirements.
5. V1/V2/V3/V4 evolution boundaries.
6. Allowed function boundaries.
7. Prohibited function boundaries.
8. Start, stop, status, log, port, and config boundaries.
9. Relationships with ZDoc Runtime, Model Fleet, KG, ZBid, and LOCAL-LAUNCHER governance.
10. Entry conditions for any later code implementation gate.

This node does not authorize LOCAL-LAUNCHER-002.

## 4. Local Launcher Positioning

The future ZDoc local launcher is positioned as a controlled local-deployment assistant, not as a governance bypass or execution shortcut.

| No. | Positioning item | Requirement | LOCAL-LAUNCHER-001 boundary |
| --- | --- | --- | --- |
| 1 | Local deployment scenario | The launcher is intended for local ZDoc deployments where users need a visible entry point instead of manual command-line operation. | Requirements only. No local deployment is performed. |
| 2 | Non-command-line users | The launcher should eventually help ordinary users understand system status without typing backend/frontend commands. | UI information architecture may be described only. No UI is created. |
| 3 | Administrator status checks | The launcher should eventually show administrator-facing status for repository, branch, HEAD, tag, service, model, port, config, and log paths. | Status fields may be specified only. No status probe is executed. |
| 4 | Backend/frontend startup control | The launcher may later become the controlled entry point for ZDoc backend/frontend startup after separate authorization. | No startup control is implemented in this node. |
| 5 | Preview-only entry | The launcher may later expose a preview-only entry when preview-only has been separately authorized. | V0 must show preview-only as disabled unless later authorized. |
| 6 | Logs, ports, config, and status visualization | The launcher should eventually make operational facts visible and understandable. | V0 may define placeholders only. No log, port, or config read is performed. |
| 7 | Generation/export/write-back | The launcher must not directly perform generation, export, or write-back. | These remain disabled and prohibited in V0. |
| 8 | Real KG | The launcher must not directly read real KG or protected KG tree bodies. | No real KG read is authorized. |
| 9 | Real project materials | The launcher must not directly read real project files, tender materials, business data, or user privacy data. | No real project material read is authorized. |
| 10 | Governance chain | The launcher must not bypass ChatGPT master-control, Model Fleet governance, ZDoc Runtime gates, KG governance, ZBid authorization, or future LOCAL-LAUNCHER gates. | Governance chain remains binding. |

The future launcher is therefore a controlled shell around already-authorized local operations, not a source of new authorization.

## 5. Version Roadmap

| Version | Goal | Allowed functions | Prohibited functions | Entry conditions | Stop conditions |
| --- | --- | --- | --- | --- | --- |
| V0 safety shell | Create a visible local console shell that communicates status categories and disabled operations. | Requirements-backed UI skeleton design, placeholder fields, disabled buttons, no-write indicators, no-runtime indicators, and safety labels. | Service start/stop, endpoint access, Ollama, trial, generation, export, write-back, real KG read, real project read, backend/frontend/config changes, scripts, and real App creation unless separately authorized. | ChatGPT master-control approval of LOCAL-LAUNCHER-001 and explicit LOCAL-LAUNCHER-002 authorization. | Any request to run service, access endpoint, run Ollama, read protected data, trigger trial/generation/export/write-back, or modify unapproved files. |
| V1 controlled startup | Add separately authorized and auditable startup/shutdown controls for known local ZDoc services. | Start/stop controls only for explicitly named services, bounded process checks, clear logs, rollback path, and no-data operation. | Unbounded process execution, endpoint probing beyond authorization, real KG/project reads, generation/export/write-back, trial, and silent background changes. | Separate V1 implementation gate after V0 review; exact services, commands, ports, logs, and stop behavior must be authorized. | Startup failure, unknown process, dirty repo state, port conflict outside authorization, or any need to read protected data. |
| V2 preview-only trial | Expose a preview-only entry for a bounded trial path after preview-only authorization. | Preview-only status display, preview-only route entry if separately authorized, no-write safeguards, and audit messages. | Generation, export, write-back, ZBid write-back, real KG read, real project read, production use, and non-preview trial. | Approved preview-only governance gate, approved runtime boundary, approved no-write proof, and explicit user authorization. | Preview attempts to write output/job/export, read protected data, enter generation/export/write-back, or exceed preview-only scope. |
| V3 small-scope trial | Support a small controlled user trial with operational visibility and stronger recovery controls. | Authorized limited user access, service health display, bounded logs, support diagnostics, and audit trail. | 50-user production use, unapproved data sources, unapproved write-back, direct KG/project reads, and governance bypass. | V2 evidence review, explicit small-scope trial authorization, rollback plan, access control, and issue-response protocol. | Any safety breach, data-boundary breach, audit gap, uncontrolled service behavior, or user count/scope expansion. |
| V4 50-user production operation | Support formal local deployment operations for up to 50 users after production authorization. | Operational dashboard, role-aware controls, service lifecycle management, incident recovery, version checks, and production audit. | Unapproved model/data/runtime expansion, uncontrolled write-back, hidden service changes, and governance bypass. | V3 acceptance, production readiness review, 50-user authorization, monitoring plan, backup plan, support ownership, and rollback gate. | Production safety issue, compliance gap, unsupported runtime state, uncontrolled write path, or governance breach. |

Recommended technical direction after this node: V0 may start from a lightweight local console or a Tauri/Electron skeleton, but no technical route is implemented in LOCAL-LAUNCHER-001. Specific implementation is reserved for `LOCAL-LAUNCHER-002-ZDOC-LOCAL-APP-SKELETON-IMPLEMENTATION-AUTHORIZATION-GATE`.

## 6. V0 Safety Shell Scope

V0 is limited to a safety shell. V0 is a visible boundary surface that communicates what is known, unknown, allowed, disabled, and prohibited.

### V0 Allowed Safety-Shell Items

| No. | V0 item | Allowed in V0 | Limit |
| --- | --- | --- | --- |
| 1 | Repository path display | Yes | Display the configured repository path only. |
| 2 | Branch display | Yes | Display branch value only after separately authorized implementation logic. |
| 3 | HEAD/tag display | Yes | Display known baseline or authorized git status only. |
| 4 | Service status placeholder | Yes | Placeholder only until service-status probing is separately authorized. |
| 5 | Port status placeholder | Yes | Placeholder only; no port access in LOCAL-LAUNCHER-001. |
| 6 | Config status placeholder | Yes | Placeholder only; no config read or write in LOCAL-LAUNCHER-001. |
| 7 | Log path placeholder | Yes | Placeholder path label only; no runtime log body read. |
| 8 | Model status placeholder | Yes | Placeholder only; no Ollama command or model probe. |
| 9 | Disabled operation states | Yes | Preview-only, generation, export, and write-back must show disabled until authorized. |
| 10 | Buttons designed but disabled | Yes | Button concepts may be documented; default behavior must be disabled. |

### V0 Prohibited Safety-Shell Items

| No. | V0 prohibited item | Prohibited in V0 | Trigger handling |
| --- | --- | --- | --- |
| 1 | Start service | Yes | Stop before implementation or runtime action. |
| 2 | Stop service | Yes | Stop before implementation or runtime action. |
| 3 | Access endpoint | Yes | Stop before HTTP request, endpoint probe, or curl. |
| 4 | Run Ollama | Yes | Stop before any Ollama command. |
| 5 | Enter trial | Yes | Stop before trial or real use. |
| 6 | Trigger generation | Yes | Stop before generation path. |
| 7 | Trigger export | Yes | Stop before export path. |
| 8 | Trigger write-back | Yes | Stop before write-back path. |
| 9 | Read real KG | Yes | Stop before protected KG read. |
| 10 | Read real project materials | Yes | Stop before real project, tender, business, or privacy data read. |

V0 must be no-run, no-endpoint, no-Ollama, no-trial, no-generation, no-export, no-write-back, no-real-KG, and no-real-project by default.

## 7. Technical Route Options

| Route | Advantages | Risks | Suitable stage | Suitable for V0 | Suitable for later 50-user deployment |
| --- | --- | --- | --- | --- | --- |
| macOS local script shell | Smallest implementation surface, fast to create, easy to inspect, low dependency burden. | Too command-like for ordinary users, weak UI, easy to over-expand into unsafe runtime scripts, weaker packaging for 50 users. | Early internal diagnostics or administrator-only prototypes. | Possible only as a restricted support layer, not as the main user-facing V0 unless separately authorized. | Weak fit unless wrapped by a governed UI and deployment process. |
| Python/Tkinter or PySide local GUI | Simple local GUI, Python-friendly, can show status fields and disabled controls quickly. | Packaging and signing can be uneven, UI polish may be limited, direct process calls must be tightly controlled. | V0/V1 prototype where Python runtime is acceptable. | Suitable for V0 safety shell if it remains disabled/no-runtime. | Medium fit; needs packaging, update, and support hardening. |
| Electron/Tauri desktop App | Strong desktop-App experience, better packaging path, browser UI ecosystem, clearer user-facing console. | Larger surface, dependency and signing work, risk of adding runtime bridges too early. | V0 shell through V4 operations if governance and packaging are controlled. | Suitable for V0 skeleton after separate authorization. | Strong fit for 50-user deployment if updates, logs, permissions, and crash recovery are governed. |
| Web local console | Reuses frontend patterns, easy to show operational dashboard, familiar browser access. | Requires a local server or hosted static strategy; server startup itself is runtime behavior and must be authorized. | V1+ after controlled startup is allowed; V0 only as static design if separately authorized. | Limited fit for V0 unless no server is started. | Good fit if combined with controlled local service and access controls. |
| Hybrid approach | Combines a desktop shell with a local web console or scripts under strict gates. | Highest coordination risk; can blur App, service, script, endpoint, and config boundaries. | Later staged rollout after V0 proves safety shell and V1 proves startup control. | Not preferred for initial V0 except as a documented future option. | Strong potential for V4 if each bridge is explicitly authorized and audited. |

Recommendation for future nodes: V0 may choose either a lightweight local console or a Tauri/Electron skeleton, but LOCAL-LAUNCHER-001 does not decide implementation details and does not create code. The exact route must be authorized in LOCAL-LAUNCHER-002.

## 8. Allowed Function Boundary

| No. | Function | Allowed now | Limit | Separate later authorization required |
| --- | --- | --- | --- | --- |
| 1 | Docs-only requirements drafting | Yes | Only this target docs file may be created. | No for LOCAL-LAUNCHER-001; yes for later edits. |
| 2 | UI information architecture design | Yes | Textual design only; no UI file or App creation. | Yes before implementation. |
| 3 | Status display design | Yes | Define fields and disabled states only; no live status probe. | Yes before live status checks. |
| 4 | Disabled button design | Yes | Buttons may be specified as disabled by default; no button implementation. | Yes before interactive controls. |
| 5 | Log path design | Yes | Define placeholder labels and future boundaries; no log body read. | Yes before reading runtime logs. |
| 6 | Port check design | Yes | Define future check semantics; no port access or endpoint request. | Yes before port probing. |
| 7 | Config check design | Yes | Define future config validation boundary; no config read/write now. | Yes before config access. |
| 8 | No-write indicator design | Yes | Define indicators that generation/export/write-back/output/job/export writes are disabled. | Yes before any write path. |
| 9 | No-runtime indicator design | Yes | Define indicators that service, endpoint, Ollama, and trial are disabled. | Yes before runtime actions. |
| 10 | Future implementation gate definition | Yes | Define entry conditions for LOCAL-LAUNCHER-002 only. | Yes; LOCAL-LAUNCHER-002 must be separately authorized. |

No allowed function in LOCAL-LAUNCHER-001 may be converted into implementation, runtime execution, endpoint access, model probing, data reading, generation, export, write-back, or trial.

## 9. Prohibited Function Boundary

| No. | Function | Prohibited now | Trigger handling | Must stop |
| --- | --- | --- | --- | --- |
| 1 | Service start | Yes | Stop before command, script, App action, or process launch. | Yes |
| 2 | Service stop | Yes | Stop before command, script, App action, or process termination. | Yes |
| 3 | Endpoint access | Yes | Stop before endpoint probe, HTTP request, browser access, or curl. | Yes |
| 4 | Ollama command | Yes | Stop before any Ollama command, model list, model probe, or runtime call. | Yes |
| 5 | Generation/export/write-back | Yes | Stop before generation, export, write-back, ZBid write-back, output/job/export write, or related trigger. | Yes |
| 6 | Trial | Yes | Stop before preview-only trial, real use, small-scope trial, or 50-user production use unless a later gate authorizes it. | Yes |
| 7 | Real KG read | Yes | Stop before reading `知识图谱/**`, `AI知识图谱大全/**`, or protected KG material. | Yes |
| 8 | Real project file read | Yes | Stop before reading real project, tender, business, privacy, or user data. | Yes |
| 9 | Registration/metadata/proof/manifest/sample read | Yes | Stop before reading registration instances, metadata field instances, proof instances, actual manifest bodies, sample bodies, sample file-name instances, or sample path instances. | Yes |
| 10 | Output/job/export write | Yes | Stop before writing output, job, export, or generated artifacts. | Yes |
| 11 | Backend modification | Yes | Stop before reading or modifying backend source for implementation. | Yes |
| 12 | Frontend modification | Yes | Stop before reading or modifying frontend source for implementation. | Yes |
| 13 | Script creation | Yes | Stop before creating shell, Python, Node, automation, or helper scripts. | Yes |
| 14 | App creation | Yes | Stop before creating desktop App, web App, UI, launcher, packaged binary, or installer. | Yes |

Stop means no fallback probe, no substitute read, no runtime check, no service check, no endpoint check, no Ollama substitute, no test substitute, no output/job/export write, no trial, and no continuation into the next node.

## 10. Start / Stop / Status / Logs / Ports / Config Boundary

### Start Boundary

LOCAL-LAUNCHER-001 may define startup requirements only.

It does not start ZDoc, backend, frontend, API server, local web console, desktop App, model runtime, KG process, ZBid process, or any support process.

Any future start action must specify exact command, process owner, working directory, environment variables, ports, logs, rollback behavior, and stop conditions in a separately authorized implementation gate.

### Stop Boundary

LOCAL-LAUNCHER-001 may define shutdown requirements only.

It does not stop any service, kill any process, close any port, terminate any model runtime, or change any live state.

Any future stop action must be auditable, reversible where possible, and scoped to explicitly named processes only.

### Status Check Boundary

LOCAL-LAUNCHER-001 may define status categories only: repository, branch, HEAD/tag, service placeholder, port placeholder, config placeholder, log placeholder, model placeholder, preview-only disabled, generation disabled, export disabled, and write-back disabled.

It does not perform live service checks, process checks, endpoint checks, HTTP requests, model checks, port checks, log reads, or protected data reads.

### Logs Boundary

LOCAL-LAUNCHER-001 may define future log visibility requirements: log path label, last update timestamp, error summary, startup trace, shutdown trace, and recovery hint.

It does not read runtime logs, `/tmp` logs, output/job/export logs, backend logs, frontend logs, model logs, KG logs, ZBid logs, or user data.

Future log access must separate operational metadata from protected content and must stop before exposing sample, manifest, registration, metadata, proof, real KG, real project, tender, business, or privacy data.

### Ports Boundary

LOCAL-LAUNCHER-001 may define future port visibility requirements: intended backend port, intended frontend port, occupied/free/unknown status, conflict warning, and resolution guidance.

It does not access ports, connect to localhost, send HTTP requests, run curl, open a browser, or inspect live network listeners.

Future port checks must be separately authorized and must avoid endpoint behavior unless endpoint access is explicitly allowed.

### Config Boundary

LOCAL-LAUNCHER-001 may define future config visibility requirements: config presence, schema version, environment profile, required key status, missing-value warning, and write-disabled indicator.

It does not read, write, create, delete, normalize, migrate, or validate real config files.

Future config access must specify exact config files, allowed fields, redaction rules, no-secret exposure requirements, and write permissions.

## 11. Relationship With Other Mainlines

| Mainline | Relationship | Binding boundary |
| --- | --- | --- |
| `MODEL-FLEET-GOVERNANCE` | LOCAL-LAUNCHER inherits the current no-controlled-execution and no-metadata-only-review-execution status after 075. | Launcher does not override Model Fleet governance and cannot authorize model/runtime actions by itself. |
| `ZDOC-RUNTIME` | Future launcher versions may display or control ZDoc runtime only after a ZDoc Runtime gate authorizes exact runtime behavior. | V0 triggers no runtime behavior. |
| `ZBID-INTEGRATION` | Future launcher versions may show ZBid disabled or authorized status only after ZBid gates define write-back boundaries. | Launcher does not perform ZBid write-back. |
| `KG-GOVERNANCE` | Future launcher versions must respect KG read/write boundaries and protected tree restrictions. | Launcher does not read real KG or protected KG bodies. |
| `LOCAL-LAUNCHER` | LOCAL-LAUNCHER is the staged governance line for launcher requirements, safety shell, implementation, trial, and operations. | Each version requires a named gate and explicit authorization. |

The launcher does not replace the governance chain.

The launcher does not bypass authorization.

The launcher can only carry functions that have already been authorized by the relevant governance node.

Launcher V0 does not trigger any runtime behavior.

## 12. Quality and Stability Requirements

Future launcher versions must satisfy the following quality and stability requirements before they can move from design to wider use:

| No. | Requirement | Meaning | Required evidence in later gates |
| --- | --- | --- | --- |
| 1 | Single-click understandable | A non-command-line user can understand what a control does before pressing it. | UI review and disabled-state proof. |
| 2 | Visible status | Repository, branch, version, service, model, port, config, logs, and operation permissions are visible or explicitly unknown. | Status design and bounded check plan. |
| 3 | Explainable errors | Failures must show concise reason, next safe action, and support path. | Error-state design and recovery examples. |
| 4 | Locatable logs | Operational logs must be discoverable without exposing protected content. | Log boundary and redaction plan. |
| 5 | Traceable operations | Startup, shutdown, config checks, and user actions must be auditable. | Audit trail design. |
| 6 | Stoppable service | Any later service start must have a reliable and visible stop path. | Stop-control test plan in a later authorized node. |
| 7 | Recoverable exception | Crashes, port conflicts, missing config, and model unavailability must have safe recovery states. | Recovery matrix. |
| 8 | Validatable config | Config must be checked without exposing secrets or changing values unless authorized. | Config schema and redaction plan. |
| 9 | Controllable permissions | User role, administrator role, and disabled states must prevent unauthorized operations. | Role/permission matrix. |
| 10 | Misoperation blocking | Dangerous operations must be disabled, guarded, confirmed, and audited as appropriate. | Safety-control acceptance criteria. |

No future launcher version may trade away these requirements for convenience or command-line parity.

## 13. Future Code Implementation Gate

Code implementation may start only after ChatGPT master-control reviews LOCAL-LAUNCHER-001 and the user provides a separate explicit authorization for:

`LOCAL-LAUNCHER-002-ZDOC-LOCAL-APP-SKELETON-IMPLEMENTATION-AUTHORIZATION-GATE`

LOCAL-LAUNCHER-002 must not be inferred from LOCAL-LAUNCHER-001 completion.

LOCAL-LAUNCHER-002 must define at minimum:

1. Exact target files allowed for creation or modification.
2. Exact technical route for V0.
3. Whether any dependencies may be added.
4. Whether any repository source files may be read.
5. Whether any commands may be run.
6. Whether tests may be run.
7. Whether any local service may be started.
8. Whether any endpoint may be accessed.
9. Whether any Ollama command may be run.
10. Whether any config file may be read or written.
11. Whether any logs may be read.
12. Required no-trial, no-generation, no-export, no-write-back, no-real-KG, and no-real-project boundaries.
13. Required completion-and-stop report.

Without that separate authorization package, Codex must stop after LOCAL-LAUNCHER-001 and must not implement, scaffold, or preview any launcher.

## 14. Decision

`LOCAL-LAUNCHER-001 ZDOC LOCAL APP REQUIREMENTS AND SAFETY GATE COMPLETED / DOCS-ONLY / NO CODE IMPLEMENTED / NO APP CREATED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO TRIAL EXECUTED`

This decision is based only on docs-only review of:

1. `docs/zdoc-sanitized-sample-metadata-instance-registration-metadata-only-review-user-authorization-receipt-gate-model-fleet-governance-075.md`
2. `docs/zdoc-sanitized-sample-metadata-instance-registration-metadata-only-review-user-authorization-hold-gate-model-fleet-governance-074.md`

No 073-070 governance documents were read for this node because 075 and 074 were sufficient to confirm the current no-execution, no-trial, no-generation/export/write-back boundary.

LOCAL-LAUNCHER-001 created only this docs artifact.

## 15. Next Node Boundary

LOCAL-LAUNCHER-001 must stop after this document is created, checked, committed, tagged, pushed, and reported.

LOCAL-LAUNCHER-001 must not enter `LOCAL-LAUNCHER-002`.

LOCAL-LAUNCHER-001 must not implement any launcher code.

LOCAL-LAUNCHER-001 must not create any script, App, UI, backend change, frontend change, config change, service process, endpoint access, Ollama command, trial path, generation path, export path, or write-back path.

Recommended next node only after ChatGPT master-control review and explicit user authorization:

`LOCAL-LAUNCHER-002-ZDOC-LOCAL-APP-SKELETON-IMPLEMENTATION-AUTHORIZATION-GATE`

This recommendation is not authorization. Codex must stop and wait.
