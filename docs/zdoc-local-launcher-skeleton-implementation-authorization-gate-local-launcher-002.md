# ZDoc Local Launcher Skeleton Implementation Authorization Gate - LOCAL-LAUNCHER-002

## 1. Node Identification

- Node: `LOCAL-LAUNCHER-002-ZDOC-LOCAL-APP-SKELETON-IMPLEMENTATION-AUTHORIZATION-GATE`
- Repository baseline: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Current mainline: `LOCAL-LAUNCHER`
- Current node nature: docs-only skeleton implementation authorization gate
- Scope: documentation of future V0 skeleton implementation authorization boundaries only

LOCAL-LAUNCHER-002 is not code implementation.

LOCAL-LAUNCHER-002 is not App creation, script creation, UI file creation, backend modification, frontend modification, dependency modification, config modification, service start, endpoint access, Ollama run, trial, generation, export, or write-back.

LOCAL-LAUNCHER-002 does not authorize LOCAL-LAUNCHER-003.

## 2. Baseline

- HEAD: `d58b418294fa86ec1b2a0a938bf87e07fce7e68d`
- Tag: `v0.1.637-local-launcher-zdoc-local-app-requirements-and-safety-gate`
- Current mainline: `LOCAL-LAUNCHER`
- Current node nature: docs-only skeleton implementation authorization gate
- Prior approved node: `LOCAL-LAUNCHER-001-ZDOC-LOCAL-APP-REQUIREMENTS-AND-SAFETY-GATE`
- Current authorization status: no controlled execution authorization, no metadata-only review authorization, no ZDoc service run authorization, no endpoint access authorization, no Ollama run authorization, no trial authorization, and no generation/export/write-back authorization.

## 3. Purpose

LOCAL-LAUNCHER-002 exists only to define the authorization boundary for a future V0 safety-shell skeleton implementation.

`LOCAL-LAUNCHER-002 authorizes only the documentation of a future V0 skeleton implementation boundary. It does not implement, start, stop, or access any runtime service.`

This node defines:

1. V0 skeleton implementation goal.
2. Recommended V0 technical route.
3. V0 information architecture.
4. V0 disabled action design.
5. Allowed future implementation scope for LOCAL-LAUNCHER-003.
6. Prohibited future implementation scope.
7. File and directory planning principles.
8. Quality acceptance criteria.
9. Stability and usability requirements.
10. LOCAL-LAUNCHER-003 entry conditions.

This node creates only this docs artifact.

## 4. Inheritance From LOCAL-LAUNCHER-001

LOCAL-LAUNCHER-002 reviews and inherits LOCAL-LAUNCHER-001 without expanding it into implementation.

| No. | 001 item | 002 inheritance | 002 treatment |
| --- | --- | --- | --- |
| 1 | Local launcher positioning | The launcher is a controlled local-deployment assistant for ordinary users and administrators. | Inherited as the purpose of the future V0 skeleton. |
| 2 | V0/V1/V2/V3/V4 roadmap | V0 is safety shell; V1 controlled startup; V2 preview-only; V3 small-scope trial; V4 50-user operation. | Inherited as staged roadmap only. |
| 3 | V0 safety shell scope | V0 displays placeholders, disabled operations, and safety indicators. | Inherited as maximum V0 scope. |
| 4 | Technical route options | Python/Tkinter, PySide, Tauri, Electron, Web local console, and hybrid routes were identified. | Refined into a V0 recommendation in this node. |
| 5 | Allowed function boundary | Docs-only design, status placeholder design, disabled button design, log/port/config placeholder design, no-write/no-runtime indicators. | Inherited as 002 drafting scope only. |
| 6 | Prohibited function boundary | No service start/stop, endpoint, Ollama, trial, generation/export/write-back, real KG, real project, backend/frontend changes, scripts, or App creation. | Reaffirmed as mandatory stop boundary. |
| 7 | Start/stop/status/logs/ports/config boundary | 001 defines boundaries only and does not perform checks or writes. | Inherited for V0 skeleton acceptance. |
| 8 | Relationship with other mainlines | Launcher does not replace Model Fleet, ZDoc Runtime, ZBid, KG, or LOCAL-LAUNCHER governance. | Inherited as governance relationship. |
| 9 | Quality and stability requirements | Understandable, visible, explainable, traceable, recoverable, permission-controlled, and misoperation-blocking. | Inherited as future V0 quality bar. |
| 10 | Future code implementation gate | 001 identified 002 as the next authorization gate, not implementation. | 002 identifies 003 entry conditions, not implementation. |

LOCAL-LAUNCHER-002 also inherits the 074/075 hold boundaries: no controlled execution, no metadata-only review execution, no service, no endpoint, no Ollama, no test, no generation/export/write-back, no trial, no real KG read, no real project material read, and no instance read.

## 5. V0 Skeleton Implementation Goal

The future V0 skeleton should create a local launcher safety shell, not a working runtime controller.

| No. | Goal item | V0 skeleton requirement | Current 002 status |
| --- | --- | --- | --- |
| 1 | Safety shell | Provide a visible local launcher frame that communicates what is disabled and why. | Defined only. |
| 2 | Ordinary-user status | Show ordinary users that the system is not currently startable from V0. | Defined only. |
| 3 | Administrator status | Show repository path, branch, HEAD, tag, config placeholder, port placeholder, log placeholder, backend status placeholder, frontend status placeholder, and service status placeholder. | Defined only. |
| 4 | Disabled actions | Startup, shutdown, open page, model run, generation, export, write-back, KG read, project read, and output/job/export viewing actions default to disabled. | Defined only. |
| 5 | No service start | V0 skeleton must not start ZDoc, backend, frontend, API server, local console server, or support process. | Binding. |
| 6 | No endpoint access | V0 skeleton must not open, fetch, curl, browse, or probe any endpoint. | Binding. |
| 7 | No Ollama | V0 skeleton must not run Ollama or any model command. | Binding. |
| 8 | No trial | V0 skeleton must not enter preview-only trial, real use, small-scope trial, or 50-user use. | Binding. |
| 9 | No real KG | V0 skeleton must not read real KG or protected KG tree bodies. | Binding. |
| 10 | No real project material | V0 skeleton must not read real project, tender, business, or privacy data. | Binding. |
| 11 | No generation/export/write-back | V0 skeleton must not trigger generation, export, write-back, ZBid write-back, or output/job/export writes. | Binding. |

The V0 skeleton goal is therefore a static, reversible, low-risk safety shell.

## 6. Recommended Technical Route For V0

V0 should prioritize a light, low-coupling, rollback-friendly implementation route. It should not embed business logic, bind directly to ZDoc Runtime, call backend/frontend, call Ollama, open endpoints, or perform live checks. It should show only status placeholders and disabled actions, while preserving a path toward V1 controlled startup.

| Route | Fit for V0 | Advantages | Risks | Recommendation |
| --- | --- | --- | --- | --- |
| Python/Tkinter | Good for minimal local shell | Low dependency burden, simple local window, easy rollback, enough for disabled controls and placeholders. | Limited visual polish, packaging limitations, possible pressure to add command execution too early. | Acceptable if 003 explicitly authorizes Python files and no external commands. |
| PySide | Good for richer local shell | Better desktop UI capability and clearer layout options than Tkinter. | Larger dependency/package surface, packaging and signing decisions required. | Acceptable if 003 explicitly authorizes dependency handling. |
| Tauri | Strong long-term path | Small desktop shell footprint, clear bridge boundaries, good upgrade path toward V1/V4. | Requires frontend/runtime decisions and dependency changes; bridge can become unsafe if over-scoped. | Preferred long-term candidate, but 003 must separately authorize files and dependencies. |
| Electron | Strong UI path | Mature desktop App ecosystem and easy static UI rendering. | Larger dependency surface and packaging burden; risk of overbuilding. | Suitable only if 003 explicitly authorizes dependency and package changes. |
| Web local console | Weak for V0 unless static-only | Familiar dashboard pattern and easy future integration. | A local web server would be runtime behavior; endpoint/open-browser behavior is prohibited. | Not recommended for V0 unless implemented as a purely static mock without server. |
| Pure documented mock page | Safest non-runtime route | No service, no endpoint, no external command, easy review. | Not a real launcher skeleton and may delay implementation learning. | Acceptable as fallback if 003 stays docs/static-only. |

Recommended V0 route for LOCAL-LAUNCHER-003, if separately authorized:

1. Prefer a static desktop safety-shell skeleton with no runtime bridge.
2. Use either Python/Tkinter for the smallest reversible shell, or Tauri for a cleaner long-term App path.
3. Keep all actions disabled by default.
4. Keep all status values static or placeholder-only unless 003 explicitly authorizes a bounded read.
5. Do not add dependencies, create code files, or modify package files unless 003 explicitly authorizes them.

This recommendation is not implementation authorization.

## 7. V0 Information Architecture

The future V0 UI should be organized as a safety dashboard. It should make disabled state obvious and avoid any appearance that runtime actions are available.

| No. | UI area | Display item | V0 status |
| --- | --- | --- | --- |
| 1 | Header | System title: `ZDoc Local Launcher V0 Safety Shell` | Static text. |
| 2 | Repository | Current repository path | Static configured value or placeholder. |
| 3 | Repository | Current branch | Static baseline or placeholder. |
| 4 | Repository | Current HEAD | Static baseline or placeholder. |
| 5 | Repository | Current tag | Static baseline or placeholder. |
| 6 | Runtime | ZDoc backend status | Placeholder: unknown / not checked. |
| 7 | Runtime | ZDoc frontend status | Placeholder: unknown / not checked. |
| 8 | Runtime | Endpoint status | Placeholder: disabled / not accessed. |
| 9 | Runtime | Ollama status | Placeholder: disabled / not run. |
| 10 | Preview | Preview-only status | Placeholder: disabled pending authorization. |
| 11 | Write paths | Generation status | Disabled. |
| 12 | Write paths | Export status | Disabled. |
| 13 | Write paths | Write-back status | Disabled. |
| 14 | Operations | Log path | Placeholder only; no log read. |
| 15 | Operations | Config status | Placeholder only; no config read/write. |
| 16 | Operations | Port status | Placeholder only; no port access. |
| 17 | Safety | Safety boundary提示 | Display no-service, no-endpoint, no-Ollama, no-trial, no-generation/export/write-back. |
| 18 | Completion | Stop-after-completion提示 | Display that the current node stops after reporting and does not enter the next node. |

The information architecture must not include hidden startup hooks, hidden endpoint probes, background model checks, background config writes, or background data reads.

## 8. V0 Disabled Action Design

Every action in V0 that could affect runtime, data, model, endpoint, trial, or write paths must be visible but disabled by default.

| No. | Display label | Default status | Reason | Future enablement gate |
| --- | --- | --- | --- | --- |
| 1 | Start ZDoc | Disabled | No service run authorization. | A later V1 controlled-start gate with exact commands and stop path. |
| 2 | Stop ZDoc | Disabled | No service stop authorization and no known started process under launcher control. | A later V1 controlled-stop gate with exact process ownership. |
| 3 | Open preview-only | Disabled | No preview-only trial authorization in V0. | A later V2 preview-only gate. |
| 4 | Run Ollama | Disabled | No Ollama or model command authorization. | A later model/runtime gate explicitly allowing bounded model checks. |
| 5 | Generate document | Disabled | Generation is prohibited. | A later generation authorization gate, if ever approved. |
| 6 | Export document | Disabled | Export is prohibited. | A later export authorization gate, if ever approved. |
| 7 | Write back to ZBid | Disabled | ZBid write-back is prohibited. | A later ZBID-INTEGRATION write-back gate. |
| 8 | Read KG | Disabled | Real KG and protected KG tree reads are prohibited. | A later KG-GOVERNANCE read authorization gate. |
| 9 | Read project materials | Disabled | Real project, tender, business, and privacy data reads are prohibited. | A later project-data authorization gate. |
| 10 | View real output/job/export | Disabled | Output/job/export body reads and writes are prohibited. | A later output/job/export inspection gate with redaction rules. |

Disabled controls must not be clickable, must not trigger background actions, and must not open files, URLs, processes, commands, or dialogs that read protected data.

## 9. Allowed Future Implementation Scope For LOCAL-LAUNCHER-003

If LOCAL-LAUNCHER-003 is later explicitly authorized, the minimum allowed implementation scope may include only the following V0 skeleton items:

| No. | Future 003 item | Default allowed only if 003 explicitly authorizes it | Limit |
| --- | --- | --- | --- |
| 1 | Create V0 launcher skeleton | Yes | Static shell only; no runtime bridge. |
| 2 | Create static UI | Yes | Display-only UI; no service actions. |
| 3 | Display static status placeholders | Yes | Unknown/disabled placeholders only. |
| 4 | Display disabled buttons | Yes | Buttons disabled by default and non-operational. |
| 5 | Display safety boundary text | Yes | No hidden action behind text or controls. |
| 6 | Display local repository path config placeholder | Yes | Placeholder or configured literal only; no config file read unless authorized. |
| 7 | Display log path config placeholder | Yes | Placeholder only; no runtime log body read. |
| 8 | Avoid service calls | Required | No service start/stop. |
| 9 | Avoid endpoint calls | Required | No endpoint, curl, HTTP, browser open, or localhost probe. |
| 10 | Avoid external commands | Required | No shell command, git command, Ollama command, or runtime command from the App unless separately authorized. |
| 11 | Avoid real data reads | Required | No KG, project, registration, metadata, proof, manifest, sample, output/job/export body, or user data reads. |

LOCAL-LAUNCHER-002 does not authorize LOCAL-LAUNCHER-003 to read code directories, create code files, modify dependency files, modify config files, run commands, run tests, start services, or access endpoints.

Whether LOCAL-LAUNCHER-003 may read code directories, create files, modify dependency files, or use a specific technical route must be separately and explicitly authorized in the 003 instruction.

## 10. Prohibited Future Implementation Scope

Even if LOCAL-LAUNCHER-003 is later authorized, the following actions remain prohibited by default unless a later named gate explicitly changes the boundary:

| No. | Prohibited future action | Default status in 003 | Trigger handling |
| --- | --- | --- | --- |
| 1 | Start service | Prohibited | Stop before command, process launch, App hook, or script. |
| 2 | Stop service | Prohibited | Stop before command, process termination, App hook, or script. |
| 3 | Access endpoint | Prohibited | Stop before HTTP request, browser open, endpoint probe, or localhost access. |
| 4 | Execute curl | Prohibited | Stop before curl or equivalent HTTP command. |
| 5 | Run Ollama | Prohibited | Stop before Ollama, model list, model probe, or model execution. |
| 6 | Call model | Prohibited | Stop before local or remote model call. |
| 7 | Read KG | Prohibited | Stop before real KG or protected KG tree read. |
| 8 | Read project materials | Prohibited | Stop before real project, tender, business, or privacy data read. |
| 9 | Read registration/metadata/proof/manifest/sample instances | Prohibited | Stop before instance body, path, filename, or value read. |
| 10 | Trigger generation/export/write-back | Prohibited | Stop before write path or output-producing action. |
| 11 | Write output/job/export | Prohibited | Stop before writing generated, job, output, or export artifacts. |
| 12 | Enter trial | Prohibited | Stop before preview-only trial, real use, small-scope trial, or production use. |
| 13 | Real use | Prohibited | Stop before using the launcher with real workflow or real data. |
| 14 | 50-user production use | Prohibited | Stop before production deployment or multi-user operation. |
| 15 | ZBid write-back | Prohibited | Stop before any ZBid update or write-back path. |

Prohibited means no fallback implementation, no mock command, no hidden call, no background probe, no test substitute, and no continuation into runtime behavior.

## 11. File And Directory Planning Principles

LOCAL-LAUNCHER-002 defines planning principles only. It does not create directories or files beyond this docs artifact.

| No. | Principle | Requirement for future 003 |
| --- | --- | --- |
| 1 | Decouple from backend/frontend | Launcher files should be separate from existing backend and frontend runtime chains. |
| 2 | Centralize V0 files | V0 files should live in an independent launcher directory or another directory explicitly named by 003. |
| 3 | Do not pollute ZDoc Runtime | V0 must not change runtime startup behavior, service imports, routers, handlers, or execution flow. |
| 4 | Do not modify backend run chain | Backend source, startup files, API server, and routes remain untouched unless 003 explicitly authorizes a bounded read/change. |
| 5 | Do not modify frontend run chain | Frontend source, build config, routes, and existing UI remain untouched unless 003 explicitly authorizes a bounded read/change. |
| 6 | Do not modify generation chain | Generation code, prompts, job flow, and output creation remain untouched. |
| 7 | Do not modify export chain | Export code, files, and artifacts remain untouched. |
| 8 | Do not modify ZBid write-back chain | ZBid integration and write-back behavior remain untouched. |
| 9 | Dependencies require separate authorization | Any package, lockfile, environment, installer, or build dependency change must be authorized in 003. |
| 10 | Scripted startup requires separate authorization | Any shell, Python, Node, launchd, Automator, AppleScript, service manager, or helper startup script must be separately authorized. |

The future file plan must make rollback simple: removing the V0 skeleton directory should not alter existing ZDoc runtime behavior.

## 12. Quality Acceptance Criteria

If LOCAL-LAUNCHER-003 later implements V0, acceptance must include every criterion below:

| No. | Criterion | Acceptance requirement |
| --- | --- | --- |
| 1 | Authorized file scope only | The working tree shows only files authorized by 003. |
| 2 | No service start | No backend, frontend, API server, local console server, model runtime, or support process starts. |
| 3 | No endpoint access | No HTTP request, curl, browser open, localhost access, or endpoint probe occurs. |
| 4 | No Ollama | No Ollama command, model listing, model probe, or model call occurs. |
| 5 | No generation/export/write-back | No write path or output-producing action occurs. |
| 6 | No output/job/export write | No output, job, export, or generated artifact is written. |
| 7 | Buttons disabled by default | All dangerous controls are visible only as disabled, non-operational controls. |
| 8 | Clear status display | Path, branch, HEAD, tag, service placeholder, endpoint placeholder, Ollama placeholder, log placeholder, config placeholder, and port placeholder are understandable. |
| 9 | Clear safety boundary | The UI states no-service, no-endpoint, no-Ollama, no-trial, and no-generation/export/write-back. |
| 10 | Clear error hints | Any unavailable or unknown state is explained without suggesting unsafe action. |
| 11 | Rollback-friendly | V0 can be removed without changing backend, frontend, runtime, generation, export, or ZBid behavior. |
| 12 | Existing mainlines unaffected | Model Fleet, ZDoc Runtime, KG, ZBid, and LOCAL-LAUNCHER governance remain intact. |
| 13 | Backend/frontend unaffected | Existing backend/frontend files and behavior are unchanged unless 003 explicitly authorizes otherwise. |
| 14 | Audit report provided | Completion report states files changed, checks run, prohibited actions not taken, and no-next-node-entry confirmation. |

No future V0 implementation should be considered complete if any criterion is missing.

## 13. Stability And Usability Requirements

The future V0 design must satisfy the following stability and usability requirements:

| No. | Requirement | V0 interpretation |
| --- | --- | --- |
| 1 | Ordinary users understand current non-startable state | The UI should make it obvious that V0 does not start the system. |
| 2 | Administrators see path and version state | Repository path, branch, HEAD, and tag should be visible or clearly marked as placeholders. |
| 3 | Disabled buttons do not mislead | Disabled actions must explain why they are disabled and what future gate may enable them. |
| 4 | Page/window has no background actions | Opening the shell must not start services, access endpoints, read logs, read config, or run commands. |
| 5 | Abnormal state has clear prompt | Unknown, missing, blocked, or unsupported states should be shown without unsafe recovery steps. |
| 6 | V1 can later attach start/stop | V0 layout should leave room for future authorized controlled-start and controlled-stop controls. |
| 7 | V2 can later attach preview-only | V0 layout should leave room for future preview-only status and entry if authorized. |
| 8 | V3 can support small-scope trial | V0 design should not block later role/status/audit additions. |
| 9 | V4 can extend to operations monitoring | V0 structure should be compatible with future operations status, incidents, logs, and support views. |
| 10 | V0 remains stable, light, and rollback-friendly | V0 should avoid deep coupling, business logic, runtime bridges, and irreversible changes. |

The future V0 skeleton should be boring by design: visible, inert, bounded, and easy to remove.

## 14. Future LOCAL-LAUNCHER-003 Entry Conditions

LOCAL-LAUNCHER-003 may start only if every entry condition below is satisfied:

| No. | Entry condition | Required status |
| --- | --- | --- |
| 1 | 002 review | LOCAL-LAUNCHER-002 has been reviewed and approved by ChatGPT master-control. |
| 2 | Explicit user authorization | The user explicitly authorizes entry into 003. |
| 3 | Exact node name | The instruction names `LOCAL-LAUNCHER-003`. |
| 4 | File scope | The instruction lists exact files and directories that 003 may create or modify. |
| 5 | Technical route | The instruction states the allowed V0 technical route. |
| 6 | No service | The instruction prohibits service start unless separately and explicitly authorized. |
| 7 | No endpoint | The instruction prohibits endpoint access, HTTP request, curl, browser open, and localhost probe. |
| 8 | No Ollama | The instruction prohibits Ollama and model commands. |
| 9 | No generation/export/write-back | The instruction prohibits generation, export, write-back, and output/job/export writes. |
| 10 | No trial | The instruction prohibits preview-only trial, real use, small-scope trial, and 50-user production use. |
| 11 | No real KG | The instruction prohibits real KG and protected KG tree reads. |
| 12 | No real project materials | The instruction prohibits real project, tender, business, privacy, and user data reads. |
| 13 | Completion and stop | The instruction requires a completion report and immediate stop without entering the next node. |

If any entry condition is absent, ambiguous, contradicted, or expands into prohibited action, Codex must stop before 003.

## 15. Decision

`LOCAL-LAUNCHER-002 ZDOC LOCAL APP SKELETON IMPLEMENTATION AUTHORIZATION GATE COMPLETED / DOCS-ONLY / NO CODE IMPLEMENTED / NO APP CREATED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO TRIAL EXECUTED`

This decision is based only on docs-only review of:

1. `docs/zdoc-local-launcher-requirements-and-safety-gate-local-launcher-001.md`
2. `docs/zdoc-sanitized-sample-metadata-instance-registration-metadata-only-review-user-authorization-receipt-gate-model-fleet-governance-075.md`
3. `docs/zdoc-sanitized-sample-metadata-instance-registration-metadata-only-review-user-authorization-hold-gate-model-fleet-governance-074.md`

No 073-070 governance documents were read for this node because 001, 075, and 074 were sufficient to confirm the current no-execution, no-trial, no-service, no-endpoint, no-Ollama, and no-generation/export/write-back boundary.

LOCAL-LAUNCHER-002 created only this docs artifact.

## 16. Next Node Boundary

LOCAL-LAUNCHER-002 must stop after this document is created, checked, committed, tagged, pushed, and reported.

LOCAL-LAUNCHER-002 must not enter `LOCAL-LAUNCHER-003`.

LOCAL-LAUNCHER-002 must not implement any launcher code.

LOCAL-LAUNCHER-002 must not create any script, App, UI file, backend change, frontend change, dependency change, config change, service process, endpoint access, Ollama command, trial path, generation path, export path, or write-back path.

Recommended next node only after ChatGPT master-control review and explicit user authorization:

`LOCAL-LAUNCHER-003-ZDOC-LOCAL-APP-V0-SAFETY-SHELL-SKELETON-IMPLEMENTATION-GATE`

This recommendation is not authorization. Codex must stop and wait.
