# LOCAL-LAUNCHER-012 ZDOC Local App V1 Controlled Start Implementation Authorization Gate

## 1. Node Identification

- Node: `LOCAL-LAUNCHER-012-ZDOC-LOCAL-APP-V1-CONTROLLED-START-IMPLEMENTATION-AUTHORIZATION-GATE`
- Scope: docs-only V1 controlled start implementation authorization gate.
- Target artifact: `docs/zdoc-local-launcher-v1-controlled-start-implementation-authorization-gate-local-launcher-012.md`
- Execution boundary: no code implementation, no V0 artifact modification, no service start/stop, no endpoint access, no Ollama, no tests, no trial, and no generation/export/write-back.

## 2. Baseline

- HEAD: `91d266d1bfafe0ad7e3e6fb1648efef177af18f9`
- Tag: `v0.1.647-local-launcher-zdoc-local-app-v1-controlled-start-readiness-gate`
- Current branch line: `LOCAL-LAUNCHER`
- Current node nature: docs-only V1 controlled start implementation authorization gate
- Starting branch confirmation: `main`
- Starting worktree status: clean

The required baseline matched before this document was created.

## 3. Purpose

LOCAL-LAUNCHER-012 defines only the implementation authorization boundary for a possible future V1 controlled start. It does not implement, run, open, start, stop, access, or repair any runtime component.

This node only defines future V1 implementation boundaries, file scope, runtime preconditions, prohibited actions, audit requirements, and the next-node path.

Binding purpose limits:

1. LOCAL-LAUNCHER-012 authorizes only a future implementation-boundary document.
2. LOCAL-LAUNCHER-012 does not implement code.
3. LOCAL-LAUNCHER-012 does not start ZDoc service.
4. LOCAL-LAUNCHER-012 does not stop ZDoc service.
5. LOCAL-LAUNCHER-012 does not access endpoint.
6. LOCAL-LAUNCHER-012 does not run Ollama.
7. LOCAL-LAUNCHER-012 does not run tests.
8. LOCAL-LAUNCHER-012 does not enter trial.
9. LOCAL-LAUNCHER-012 does not trigger generation/export/write-back.
10. LOCAL-LAUNCHER-012 does not read real KG.
11. LOCAL-LAUNCHER-012 does not read real project materials.
12. LOCAL-LAUNCHER-012 stops after completion.
13. Real code implementation must require a separate `LOCAL-LAUNCHER-013` gate.
14. Real service startup must require a separate `ZDOC-RUNTIME` or later runtime preflight/execution gate.

## 4. Inheritance From LOCAL-LAUNCHER-011

LOCAL-LAUNCHER-012 inherits LOCAL-LAUNCHER-011 without expanding it into implementation or runtime behavior.

Inherited 011 controls:

1. V0 closure inheritance: LOCAL-LAUNCHER-001 through LOCAL-LAUNCHER-010 are complete, and the V0 Chinese safety shell is accepted only as a static safety shell.
2. V1 controlled start definition: future V1 may define controlled backend/frontend startup, service status, log path display, port status, stop controls, and audit display only if separately authorized.
3. V1 readiness preconditions: master-control review, explicit user authorization, clean repository, V0 acceptance, exact commands, ports, logs, config, and endpoint boundaries must be defined in later nodes.
4. V1 allowed future capability boundary: possible future backend/frontend startup, process status, port status, log path display, controlled stop, service status, abnormal-state display, and no-write status display require later authorization.
5. V1 prohibited default boundary: Ollama, model calls, real KG/project reads, registration/metadata/proof/manifest/sample reads, generation, export, write-back, ZBid write-back, trial, real use, 50-user use, output/job/export writes, and unauthorized endpoints remain prohibited.
6. V1 risk register: port conflict, unclosed service, accidental endpoint access, log leakage, misleading UI, button misfire, residual process, config path exposure, duplicate process, preview-only confusion, Model Fleet boundary confusion, and ZBid boundary confusion remain active risks.
7. V1 UI evolution proposal: Chinese UI, safety prompts, service status area, pre-start checks, stop area, log area, port area, and disabled write/model/data prompts may be considered only in future implementation.
8. Future implementation gate recommendation: LOCAL-LAUNCHER-012 should be an authorization gate, not a runtime gate.
9. No-service-run, no-endpoint, no-Ollama, no-trial, and no-generation/export/write-back boundaries remain binding.

## 5. V1 Implementation Authorization Object

The future V1 implementation authorization object is limited to a V1 controlled-start UI and status skeleton.

The authorization object includes only future boundary definition for:

1. V1 controlled-start UI skeleton.
2. V1 static or semi-static status display skeleton.
3. Startup-precondition display areas.
4. Service-status placeholder areas.
5. Port-status placeholder areas.
6. Log-path placeholder areas.
7. Stop-service placeholder areas.
8. Visible safety and no-write indicators.

The authorization object does not include:

1. real service startup;
2. real service stop;
3. endpoint access;
4. Ollama run;
5. model call;
6. trial;
7. generation/export/write-back;
8. real KG read;
9. real project material read;
10. ZBid write-back;
11. 50-user formal deployment;
12. backend/frontend/config/dependency modification.

## 6. Future LOCAL-LAUNCHER-013 Allowed Implementation Scope

If LOCAL-LAUNCHER-013 is separately authorized later, the minimum allowed implementation scope should be limited to:

1. Create a V1 static or semi-static UI skeleton under `local_launcher/v1/`.
2. Preserve Chinese interface.
3. Add a pre-start check area.
4. Add a service status area.
5. Add a port status area.
6. Add a log path area.
7. Add a stop-service placeholder area.
8. Preserve generation/export/write-back disabled prompts.
9. Preserve Ollama disabled prompts.
10. Preserve real KG and real project material disabled prompts.
11. Display a message that startup requires future authorization.
12. Keep all real start/stop/access actions disabled or mock-disabled.
13. Add a LOCAL-LAUNCHER-013 documentation artifact that records the implementation boundary and no-runtime result.

Mandatory 013 limits:

1. LOCAL-LAUNCHER-013 must not run service.
2. LOCAL-LAUNCHER-013 must not access endpoint.
3. LOCAL-LAUNCHER-013 must not run Ollama.
4. LOCAL-LAUNCHER-013 must not run tests unless a later 013 instruction explicitly authorizes a narrow static check.
5. LOCAL-LAUNCHER-013 must not enter trial.
6. LOCAL-LAUNCHER-013 must not trigger generation/export/write-back.

## 7. Future LOCAL-LAUNCHER-013 Prohibited Implementation Scope

Even if LOCAL-LAUNCHER-013 is later authorized, the following remain prohibited by default:

1. Create real startup script.
2. Create real stop script.
3. Execute backend startup command.
4. Execute frontend startup command.
5. Execute port listener command.
6. Access endpoint.
7. Execute `curl`.
8. Run Ollama.
9. Run tests.
10. Call model.
11. Trigger generation/export/write-back.
12. Write output/job/export.
13. Read real KG.
14. Read real project materials.
15. Read registration/metadata/proof/manifest/sample instances.
16. Modify backend/frontend/config/dependency.
17. Enter trial.
18. Enter real use.
19. Enter 50-user formal deployment.
20. Create a runtime bridge.
21. Create a real App package.

Prohibited means no fallback command, no substitute probe, no hidden background action, no browser access, no runtime inspection, and no continuation into service behavior.

## 8. Future File and Directory Boundary

Future LOCAL-LAUNCHER-013, if separately authorized, should only allow adding these files:

```text
local_launcher/v1/README.md
local_launcher/v1/index.html
local_launcher/v1/styles.css
local_launcher/v1/launcher-state.json
docs/zdoc-local-launcher-v1-controlled-start-ui-skeleton-implementation-gate-local-launcher-013.md
```

Future 013 file boundary:

1. Do not modify V0 artifacts.
2. Do not modify backend.
3. Do not modify frontend.
4. Do not modify config.
5. Do not modify dependency files.
6. Do not create executable startup scripts.
7. Do not create a real App package.
8. Do not create a runtime bridge.
9. Do not create output/job/export artifacts.
10. Do not read protected real data or instance content.

LOCAL-LAUNCHER-012 does not create these files. It only defines the future file boundary.

## 9. V1 Runtime Preflight Separation

V1 UI skeleton and runtime preflight must remain separate.

Binding separation rules:

1. LOCAL-LAUNCHER-013, even if it implements UI, must not start service.
2. Any future service startup must require a separate `ZDOC-RUNTIME` or `LOCAL-LAUNCHER-RUNTIME-PREFLIGHT` node.
3. Service startup command must be separately authorized.
4. Service stop command must be separately authorized.
5. Endpoint health check must be separately authorized.
6. Log read must be separately authorized.
7. Port check must be separately authorized.
8. Any runtime behavior must have an independent audit report.
9. Any runtime node must define exact commands, working directories, ownership, ports, logs, stop behavior, rollback behavior, protected-data boundary, and failure stop conditions.

LOCAL-LAUNCHER UI nodes cannot silently become runtime nodes.

## 10. V1 Implementation Risk Controls

| No. | Risk | Control | Verification | Stop condition |
| --- | --- | --- | --- | --- |
| 1 | User may think V1 can directly start services. | UI and README must state `UI skeleton only` and startup requires later authorization. | Static text review in 013. | Any wording implies current startup ability. |
| 2 | Button may be accidentally enabled. | All real action buttons must be disabled or mock-disabled. | Static HTML/state review in 013. | Any real action button is enabled. |
| 3 | UI may guide user to access endpoint. | No endpoint URL or access instruction may be added by default. | Static grep or documented review in 013. | Endpoint appears without explicit authorization. |
| 4 | Future startup command integration may lack preflight. | Runtime preflight must be separate from UI skeleton. | 013 docs must defer startup to runtime preflight. | Startup command is embedded in UI skeleton. |
| 5 | Service may remain after attempted startup. | UI skeleton must not start service; future runtime gate must define stop path. | No service command in 013. | Any process ownership or stop path is unclear in a runtime request. |
| 6 | Port conflict may be hidden. | Port status must remain placeholder until separately authorized check. | 013 shows placeholder only. | Port listener check is needed in 013. |
| 7 | Logs may leak sensitive paths or content. | Log area must show path placeholder only unless later whitelisted. | 013 static review. | Log body, protected path, or sensitive content is required. |
| 8 | Real KG or project materials may be read by mistake. | UI and state must preserve no-real-KG and no-real-project prompts. | 013 static review. | Any real data read is requested. |
| 9 | Generation/export/write-back boundary may be confused. | Write-path status must remain disabled and visually distinct. | 013 static review. | Any write-path action is enabled or implied. |
| 10 | ZBid write-back boundary may be confused with local startup. | ZBid write-back must remain disabled and separately gated. | 013 static review. | Any ZBid write-back path is added. |

## 11. V1 Implementation Acceptance Criteria

Future LOCAL-LAUNCHER-013 implementation, if separately authorized, should be accepted only if all criteria below pass:

1. Only authorized files are added.
2. V0 artifacts are not modified.
3. Backend/frontend/config/dependency files are not modified.
4. No service is run.
5. No endpoint is accessed.
6. Ollama is not run.
7. Generation/export/write-back are not triggered.
8. Trial is not entered.
9. All real action buttons are disabled.
10. UI is clear Chinese.
11. Pre-start checks are placeholder or explanation only.
12. Log, port, and service status areas are placeholders only.
13. README states V1 UI skeleton only.
14. Docs record no-runtime.
15. Completion requires stop after report.

Any missing criterion blocks acceptance and requires a correction or reauthorization path, not runtime fallback.

## 12. Recommended Next Node

Recommended next node, only after ChatGPT master-control review and explicit user authorization:

`LOCAL-LAUNCHER-013-ZDOC-LOCAL-APP-V1-CONTROLLED-START-UI-SKELETON-IMPLEMENTATION-GATE`

Required constraints for that future node:

1. LOCAL-LAUNCHER-013 can only create a UI skeleton.
2. LOCAL-LAUNCHER-013 must not start service.
3. LOCAL-LAUNCHER-013 must not access endpoint.
4. LOCAL-LAUNCHER-013 must not run Ollama.
5. LOCAL-LAUNCHER-013 must not run tests.
6. LOCAL-LAUNCHER-013 must not enter trial.
7. LOCAL-LAUNCHER-013 must not trigger generation/export/write-back.
8. LOCAL-LAUNCHER-013 must not read real KG or real project materials.
9. LOCAL-LAUNCHER-013 must stop after completion.

This recommendation is not authorization. LOCAL-LAUNCHER-012 does not enter LOCAL-LAUNCHER-013.

## 13. Decision

`LOCAL-LAUNCHER-012 ZDOC LOCAL APP V1 CONTROLLED START IMPLEMENTATION AUTHORIZATION GATE COMPLETED / DOCS-ONLY / NO CODE IMPLEMENTED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

This decision is based only on the allowed LOCAL-LAUNCHER prior documents and allowed V0 static files. It does not rely on backend/frontend source, runtime state, endpoint output, Ollama output, real KG, real project material, registration, metadata, proof, manifest, sample, output, job, or export bodies.

## 14. Next Node Boundary

LOCAL-LAUNCHER-012 stops after this document is created, checked, committed, tagged, pushed, and reported.

LOCAL-LAUNCHER-012 must not enter `LOCAL-LAUNCHER-013`.

LOCAL-LAUNCHER-012 must not implement code.

LOCAL-LAUNCHER-012 must not run service.

LOCAL-LAUNCHER-012 must not open the page.

LOCAL-LAUNCHER-012 must not modify V0 artifacts.

LOCAL-LAUNCHER-012 must not access endpoints, execute `curl`, send HTTP requests, run Ollama, run tests, enter trial, trigger generation, trigger export, trigger write-back, read real KG, read real project materials, or write output/job/export.

Recommended next node only after ChatGPT master-control review and explicit later authorization:

`LOCAL-LAUNCHER-013-ZDOC-LOCAL-APP-V1-CONTROLLED-START-UI-SKELETON-IMPLEMENTATION-GATE`

This recommendation is not authorization. Codex must stop and wait.
