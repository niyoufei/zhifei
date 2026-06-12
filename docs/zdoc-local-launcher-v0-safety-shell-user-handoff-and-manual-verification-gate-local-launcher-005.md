# ZDoc Local Launcher V0 Safety Shell User Handoff and Manual Verification Gate - LOCAL-LAUNCHER-005

## 1. Node Identification

- Node: `LOCAL-LAUNCHER-005-ZDOC-LOCAL-APP-V0-SAFETY-SHELL-USER-HANDOFF-AND-MANUAL-VERIFICATION-GATE`
- Current branch: `main`
- Current mainline: `LOCAL-LAUNCHER`
- Current node nature: docs-only user handoff and manual verification gate
- Scope: user handoff and manual verification documentation for the V0 safety shell only

LOCAL-LAUNCHER-005 is docs-only.

LOCAL-LAUNCHER-005 does not modify V0 artifacts.

## 2. Baseline

- HEAD: `610e5a014f7ed7da1e93d3a18729120f6eb2f13d`
- Tag: `v0.1.640-local-launcher-zdoc-local-app-v0-safety-shell-static-artifact-audit-gate`
- Current mainline: `LOCAL-LAUNCHER`
- Current node nature: docs-only user handoff and manual verification gate
- Starting branch confirmation: `main`
- Starting worktree status: clean

The required baseline matched before this document was created.

## 3. Purpose

This node prepares only the user-facing handoff and manual verification material for the V0 safety shell.

`LOCAL-LAUNCHER-005 prepares only user handoff and manual verification documentation for the V0 safety shell. It does not run, open, start, stop, access, or repair any runtime component.`

This node does not open the HTML page, run services, access endpoints, run Ollama, enter trial, trigger generation/export/write-back, or repair any file.

## 4. V0 Delivery Summary

The current V0 delivery contains:

1. `local_launcher/v0/index.html`
2. `local_launcher/v0/styles.css`
3. `local_launcher/v0/launcher-state.json`
4. `local_launcher/v0/README.md`
5. `docs/zdoc-local-launcher-v0-safety-shell-skeleton-implementation-gate-local-launcher-003.md`
6. `docs/zdoc-local-launcher-v0-safety-shell-static-artifact-audit-gate-local-launcher-004.md`

V0 is a static safety shell. It is not a startable system.

V0 exists to show the future launcher structure, visible status placeholders, disabled actions, and safety boundary text. It does not provide startup, shutdown, preview, model, generation, export, write-back, KG, project-file, output, job, or export operations.

## 5. User-Facing Meaning of V0

For ordinary users, V0 means:

1. V0 is only a safety shell.
2. V0 shows the planned interface structure for a future one-click launcher.
3. All buttons in V0 are disabled by default.
4. V0 will not start ZDoc.
5. V0 will not access any endpoint.
6. V0 will not run Ollama or any model command.
7. V0 will not generate, export, or write back documents.
8. V0 will not read real KG content or real project materials.
9. V0 is used only to check whether the layout, status hints, disabled controls, and safety boundaries are clear.

For administrators, V0 means:

1. Repository, branch, HEAD/tag, backend, frontend, endpoint, Ollama, preview-only, log, config, and port areas are placeholders.
2. The page is not connected to a service.
3. The page does not perform live checks.
4. Future controlled startup belongs to V1 or later, after separate authorization.

## 6. Manual Safe Viewing Guidance

Manual viewing target:

`local_launcher/v0/index.html`

Safe viewing rules:

1. View only as a static file.
2. Do not start any service.
3. Do not use any endpoint.
4. Do not run any command.
5. Do not run Ollama.
6. Do not enter trial.
7. Do not trigger generation/export/write-back.
8. Observe only whether the interface is clear.
9. Do not treat V0 as a real launcher.

This LOCAL-LAUNCHER-005 node does not open `local_launcher/v0/index.html`. It only documents the manual viewing guidance.

If manual viewing is later performed by a human reviewer, the reviewer should confirm only the static page appearance and text clarity. The reviewer should not attempt to enable disabled buttons, launch services, connect to endpoints, use project data, or perform a trial workflow.

## 7. Manual Verification Checklist

Use this checklist for human review of the static V0 shell:

| No. | Verification item | Expected result |
| --- | --- | --- |
| 1 | Page title is clear | `ZDoc Local Launcher V0 Safety Shell` is visible. |
| 2 | Safety status is clear | `Safety Shell Only` is visible. |
| 3 | Repository placeholders are visible | Repository path, branch, and HEAD/tag placeholders are visible. |
| 4 | Runtime placeholders are visible | Backend, frontend, endpoint, Ollama, and preview-only placeholders are visible. |
| 5 | Write-path statuses are clear | Generation, export, and write-back are shown as Disabled. |
| 6 | All action buttons are disabled | No action button appears usable. |
| 7 | Disabled reason is clear | Each action explains it is disabled in V0 safety shell. |
| 8 | Safety boundary is prominent | No-service, no-endpoint, no-Ollama, no-trial, and no-write messages are easy to see. |
| 9 | Logs, ports, and config are placeholders | Log path, port, and configuration areas do not show live values. |
| 10 | No real data is shown | No real KG, project, output, job, export, registration, metadata, proof, manifest, or sample content appears. |
| 11 | No endpoint URL is shown | No network address or endpoint URL is visible. |
| 12 | No runtime action is available | The page provides no usable start, stop, model, preview, generation, export, or write-back behavior. |
| 13 | Ordinary-user meaning is clear | A non-technical user can understand that V0 cannot start the system. |
| 14 | Administrator boundary is clear | An administrator can understand that only a future V1 gate may attach controlled startup. |

## 8. Issue Reporting Template

Use the following template if a human reviewer finds an issue. Do not include real business data, real KG content, real project material, personal information, sample body, registration instance, metadata value, proof body, manifest body, output body, job body, or export body.

```text
Reviewer:
Review time:
Viewing method:
Page displayed normally: yes/no
Any button not disabled: yes/no
Misleading startup hint found: yes/no
Endpoint or network-access hint found: yes/no
Real path, real data, or sensitive information found: yes/no
Unclear interface area:
Suggested correction:
Correction gate required: yes/no
Notes without real data:
```

If a correction is needed, the follow-up should be a separately authorized correction gate. LOCAL-LAUNCHER-005 does not repair V0 artifacts.

## 9. V0 Acceptance Criteria

V0 may be accepted for the safety-shell stage only if all criteria below are met:

1. Static files exist.
2. The page can be understood by a human reviewer.
3. Buttons are disabled by default.
4. Status items are clear.
5. Prohibited boundaries are clear.
6. No runtime behavior is available.
7. No endpoint is accessed or exposed as a usable target.
8. No Ollama action is available.
9. No generation/export/write-back action is available.
10. No trial path is available.
11. No real KG is displayed or read.
12. No real project material is displayed or read.
13. No output/job/export content is displayed, read, or written.
14. The shell can serve as a design base for a future separately authorized V1 controlled-start gate.

Acceptance of V0 does not authorize V1 startup.

## 10. V0 Limitation Statement

V0 cannot:

1. One-click start ZDoc.
2. One-click stop ZDoc.
3. Open preview-only.
4. Call a model.
5. Read KG.
6. Select a project.
7. Generate a document.
8. Export a document.
9. Write back to ZBid.
10. Support multi-user operation.

V0 also cannot perform service checks, endpoint checks, port checks, log reads, config reads, config writes, project reads, KG reads, output reads, job reads, export reads, or any production operation.

## 11. Future V1 Readiness Notes

If a future V1 node is proposed, it requires separate explicit authorization before any implementation or runtime action.

Future V1 authorization must separately define:

1. Controlled startup.
2. Controlled stop.
3. Status checks.
4. Log reads.
5. Port checks.
6. Config checks.
7. Preview-only entry.
8. Preflight before running.
9. Shutdown after running.
10. Continued prohibition on generation/export/write-back unless a later gate separately authorizes them.

Future V1 must also define exact files, exact commands, process ownership, working directory, environment, ports, log boundaries, rollback behavior, stop behavior, protected-data boundaries, verification commands, and completion-and-stop reporting.

## 12. Decision

`LOCAL-LAUNCHER-005 ZDOC LOCAL APP V0 SAFETY SHELL USER HANDOFF AND MANUAL VERIFICATION GATE COMPLETED / DOCS-ONLY / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA RUN / NO TRIAL EXECUTED / NO GENERATION EXPORT WRITE-BACK TRIGGERED`

## 13. Next Node Boundary

LOCAL-LAUNCHER-005 must stop after this document is created, checked, committed, tagged, pushed, and reported.

LOCAL-LAUNCHER-005 must not enter `LOCAL-LAUNCHER-006`.

LOCAL-LAUNCHER-005 must not run service.

LOCAL-LAUNCHER-005 must not open the page.

LOCAL-LAUNCHER-005 must not modify V0 artifacts.

LOCAL-LAUNCHER-005 must not access endpoints, execute `curl`, send HTTP requests, run Ollama, run tests, enter trial, trigger generation, trigger export, trigger write-back, read real KG, read real project materials, or write output/job/export.

Recommended next node only after ChatGPT master-control review and explicit later authorization:

`LOCAL-LAUNCHER-006`

This recommendation is not authorization. Codex must stop and wait.
