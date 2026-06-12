# LOCAL-LAUNCHER-013 ZDOC Local App V1 Controlled Start UI Skeleton Implementation Gate

## 1. Node Identification

- Node: `LOCAL-LAUNCHER-013-ZDOC-LOCAL-APP-V1-CONTROLLED-START-UI-SKELETON-IMPLEMENTATION-GATE`
- Scope: V1 controlled start UI skeleton implementation gate.
- Target artifact: `docs/zdoc-local-launcher-v1-controlled-start-ui-skeleton-implementation-gate-local-launcher-013.md`
- Execution boundary: static UI skeleton only; no service run, no service stop, no endpoint access, no Ollama, no tests, no trial, and no generation/export/write-back.

## 2. Baseline

- HEAD: `83d0a03705e4c7d629d4146c107069126864496f`
- Tag: `v0.1.648-local-launcher-zdoc-local-app-v1-controlled-start-implementation-authorization-gate`
- Current branch line: `LOCAL-LAUNCHER`
- Current node nature: V1 controlled start UI skeleton implementation gate
- Starting branch confirmation: `main`
- Starting worktree status: clean

The required baseline matched before these files were created.

## 3. Implementation Scope

LOCAL-LAUNCHER-013 creates only a V1 static UI skeleton under `local_launcher/v1/` and this documentation artifact.

Allowed and completed scope:

1. Create V1 static UI skeleton files under `local_launcher/v1/`.
2. Preserve Chinese interface.
3. Add startup-precheck, service status, port status, log path, stop-service, exception, prohibited-capability, and next-authorization areas.
4. Keep all real action buttons disabled.
5. Keep all runtime, endpoint, port, log, config, model, trial, generation, export, write-back, real KG, and real project permissions disabled.
6. Create this LOCAL-LAUNCHER-013 documentation artifact.

This implementation is not a working launcher and not runtime preflight.

## 4. Created Files

Only the following files were created:

1. `local_launcher/v1/README.md`
2. `local_launcher/v1/index.html`
3. `local_launcher/v1/styles.css`
4. `local_launcher/v1/launcher-state.json`
5. `docs/zdoc-local-launcher-v1-controlled-start-ui-skeleton-implementation-gate-local-launcher-013.md`

No existing file was modified by this node.

## 5. V1 UI Skeleton Summary

`local_launcher/v1/index.html` is a static Chinese UI page titled `ZDoc 本地启动器 V1 受控启动骨架`.

The page displays:

1. current version: `V1 受控启动 UI 骨架`;
2. current status: `仅界面骨架 / 未授权启动`;
3. safety prompt stating no service, no interface access, no Ollama, and no generation/export/write-back;
4. repository, branch, HEAD/tag, backend, frontend, port, log, and config placeholders;
5. startup-precheck area;
6. service-status area;
7. stop-service placeholder area;
8. exception prompt area;
9. prohibited-capability prompt area;
10. next-authorization prompt.

The UI contains no executable startup command and no runtime bridge.

## 6. Disabled Actions Preservation

All real action buttons in the V1 UI skeleton are disabled:

1. Start ZDoc backend.
2. Start ZDoc frontend.
3. Stop ZDoc backend.
4. Stop ZDoc frontend.
5. Check port.
6. View logs.
7. Health check.
8. Open preview-only.
9. Run Ollama.
10. Generate document.
11. Export document.
12. Write back to ZBid.
13. Read KG.
14. Load project materials.

Each disabled action explains that it is disabled in the V1 UI skeleton and requires later separate authorization.

## 7. Runtime Separation Confirmation

V1 UI skeleton and runtime preflight remain separated.

LOCAL-LAUNCHER-013 does not create a runtime preflight, controlled start execution path, service manager, command bridge, process ownership layer, endpoint checker, log reader, port checker, config reader, or App package.

Any future runtime behavior must require a separate `ZDOC-RUNTIME` or `LOCAL-LAUNCHER-RUNTIME-PREFLIGHT` node with exact commands, ownership, ports, logs, stop behavior, rollback behavior, protected-data boundary, and failure stop conditions.

## 8. No Service Confirmation

No service was started, stopped, restarted, probed, or inspected.

No backend, frontend, API server, local console server, model runtime, or support process was started or stopped.

The V1 UI skeleton includes only disabled controls and static placeholders.

## 9. No Endpoint Confirmation

No endpoint was accessed.

The V1 UI skeleton contains no endpoint URL, no network request, no automatic redirect, no fetch call, no form submission, and no browser-opening behavior.

## 10. No Ollama Confirmation

Ollama was not run.

No Ollama command, model list, model probe, model runtime call, or model status check was executed or embedded.

## 11. No Trial Confirmation

No trial was entered.

The V1 UI skeleton does not enter preview-only trial, real use, small-scope trial, or 50-user production use.

## 12. No Generation/Export/Write-back Confirmation

No generation was triggered.

No export was triggered.

No write-back was triggered.

No output, job, export, generated artifact, or ZBid write-back path was written.

## 13. JSON Permission Preservation

`local_launcher/v1/launcher-state.json` is a static placeholder state file.

The following permission fields are all `false`:

1. `service_start_allowed`
2. `service_stop_allowed`
3. `port_check_allowed`
4. `log_read_allowed`
5. `config_read_allowed`
6. `endpoint_access_allowed`
7. `health_check_allowed`
8. `ollama_allowed`
9. `trial_allowed`
10. `generation_allowed`
11. `export_allowed`
12. `write_back_allowed`
13. `real_kg_read_allowed`
14. `real_project_data_read_allowed`
15. `controlled_execution_allowed`

The JSON contains no real path, real project material, real KG content, registration, metadata, proof, manifest, sample, output, job, or export content.

## 14. Quality Acceptance Check

LOCAL-LAUNCHER-013 acceptance state:

| No. | Check item | Result |
| --- | --- | --- |
| 1 | Only authorized 5 files created | Pass |
| 2 | V0 artifacts modified | No |
| 3 | Backend modified | No |
| 4 | Frontend modified | No |
| 5 | Config modified | No |
| 6 | Dependency files modified | No |
| 7 | Executable startup script created | No |
| 8 | Executable stop script created | No |
| 9 | Real App package created | No |
| 10 | Runtime bridge created | No |
| 11 | HTML is static Chinese UI | Pass |
| 12 | All real action buttons are disabled | Pass |
| 13 | JSON runtime permissions are all false | Pass |
| 14 | README states V1 UI skeleton only | Pass |
| 15 | Docs record no-runtime, no-service, no-endpoint, no-Ollama, and no-trial | Pass |

## 15. Future Runtime Preflight Boundary

Future runtime preflight is not authorized by this node.

If a future node proposes runtime preflight or controlled start execution, it must separately define:

1. exact service startup command;
2. exact service stop command;
3. exact working directory;
4. exact process ownership;
5. exact port list and check method;
6. exact log path whitelist;
7. exact config read scope;
8. exact endpoint health check scope;
9. exact no-Ollama boundary or separately authorized model-runtime boundary;
10. exact no-trial, no-generation, no-export, and no-write-back boundary;
11. exact failure stop conditions;
12. exact audit report format.

LOCAL-LAUNCHER-013 does not enter any future runtime node.

## 16. Decision

`LOCAL-LAUNCHER-013 ZDOC LOCAL APP V1 CONTROLLED START UI SKELETON IMPLEMENTATION GATE COMPLETED / V1 STATIC UI SKELETON CREATED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

This decision is based only on the allowed LOCAL-LAUNCHER prior documents and allowed V0 static files. It does not rely on backend/frontend source, runtime state, endpoint output, Ollama output, real KG, real project material, registration, metadata, proof, manifest, sample, output, job, or export bodies.

## 17. Next Node Boundary

LOCAL-LAUNCHER-013 stops after these files are created, checked, committed, tagged, pushed, and reported.

LOCAL-LAUNCHER-013 must not enter `LOCAL-LAUNCHER-014`.

LOCAL-LAUNCHER-013 must not run service.

LOCAL-LAUNCHER-013 must not stop service.

LOCAL-LAUNCHER-013 must not open the page.

LOCAL-LAUNCHER-013 must not access endpoints, execute HTTP requests, run Ollama, run tests, enter trial, trigger generation, trigger export, trigger write-back, read real KG, read real project materials, or write output/job/export.

Recommended next node only after ChatGPT master-control review and explicit later authorization:

`LOCAL-LAUNCHER-014-ZDOC-LOCAL-APP-V1-CONTROLLED-START-UI-SKELETON-STATIC-AUDIT-GATE`

This recommendation is not authorization. Codex must stop and wait.
